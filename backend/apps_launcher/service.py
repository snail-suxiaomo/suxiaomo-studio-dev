"""apps_launcher/service.py —— 应用快捷方式 CRUD + 启动

不是 AI 功能，只保留 service（业务）+ router（装配）。
"""

import os
import subprocess
import sys
from pathlib import Path

from common import db


def _conn():
    return db.get_conn()


# 图标存放目录（统一数据根下的 data/app_icons，跟随 customPath 等自定义位置）
ICON_DIR = db.DATA_DIR / "app_icons"


def _resolve_lnk(path):
    """如果是 .lnk 快捷方式，解析并返回目标路径；否则原样返回。"""
    if not str(path).lower().endswith('.lnk'):
        return path
    try:
        import win32com.client
        shell = win32com.client.Dispatch('WScript.Shell')
        lnk = shell.CreateShortcut(str(path))
        return lnk.TargetPath or path
    except Exception:
        return path


def extract_icon(exe_path, app_id):
    """从 exe/lnk 目标抽取第 0 个图标存成 PNG，返回相对可访问路径（如 /api/apps_launcher/icon/{id}）或 None。

    依赖 pywin32（Windows）。抽不到（无图标 / 非 Windows / 库缺失）时返回 None，前端回退首字母色块。
    """
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    try:
        import win32ui
        import win32gui
        import win32con
        from PIL import Image
    except Exception:
        return None
    exe = str(_resolve_lnk(exe_path))
    if not Path(exe).exists():
        return None
    large, small = win32gui.ExtractIconEx(exe, 0)
    if not large and not small:
        return None
    hicon = large[0] if large else small[0]
    try:
        # 渲染到内存位图（32x32 足够清晰，前端显示 ~38px）
        hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
        hbmp = win32ui.CreateBitmap()
        hbmp.CreateCompatibleBitmap(hdc, 32, 32)
        mem_dc = win32gui.CreateCompatibleDC(0)
        win32gui.SelectObject(mem_dc, hbmp.GetHandle())
        # 刷白底，避免透明/未绘制区域发黑
        white_brush = win32gui.GetStockObject(win32con.WHITE_BRUSH)
        win32gui.SelectObject(mem_dc, white_brush)
        win32gui.PatBlt(mem_dc, 0, 0, 32, 32, win32con.WHITENESS)
        win32gui.DrawIcon(mem_dc, 0, 0, hicon)
        bmpinfo = hbmp.GetInfo()
        bmpstr = hbmp.GetBitmapBits(True)
        img = Image.frombuffer(
            'RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
            bmpstr, 'raw', 'BGRX', 0, 1,
        )
        # 转 RGBA，把白底背景（我们刚刷的白色）变透明，保留图标本身
        img = img.convert('RGBA')
        px = img.load()
        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = px[x, y]
                # 接近纯白的像素设为透明
                if r > 240 and g > 240 and b > 240:
                    px[x, y] = (r, g, b, 0)
        out = ICON_DIR / f"{app_id}.png"
        img.save(out, 'PNG')
        # 清理 Windows 句柄
        try:
            win32gui.DestroyIcon(hicon)
        except Exception:
            pass
        return f"/api/apps_launcher/icon/{app_id}"
    except Exception:
        return None



# ============ 应用快捷方式 ============
def _norm_port(v):
    """规范化端口：None/空/0 → None；否则转 int 并校验范围。"""
    if v is None or v == '' or v == 0:
        return None
    try:
        p = int(v)
    except (TypeError, ValueError):
        raise ValueError('检测端口必须是数字')
    if p <= 0 or p > 65535:
        raise ValueError('检测端口超出范围（1-65535）')
    return p


def _port_listening(port, host='127.0.0.1', timeout=0.5):
    """检测本机端口是否在监听（TCP 能连上即视为服务运行中）。"""
    import socket
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def add_app(name, exe_path, args=None, note=None, category='未分类', detect_port=None):
    """新增/更新一个应用快捷方式（按 exe_path 去重）。

    detect_port：可选，web 服务型应用（TTS/ComfyUI 等 .bat 启动的 webui）的状态检测端口，
    配置后状态灯按"端口是否监听"判定，不再依赖窗口检测。
    """
    if not name:
        raise ValueError('应用名不能为空')
    if not exe_path:
        raise ValueError('可执行文件路径不能为空')
    rp = Path(exe_path)
    if not rp.exists():
        raise ValueError(f'可执行文件不存在：{rp}')
    if not category:
        category = '未分类'
    detect_port = _norm_port(detect_port)
    conn = _conn()
    try:
        max_row = conn.execute(
            "SELECT MAX(sort_order) as m FROM app_launchers"
        ).fetchone()
        next_order = (max_row['m'] or 0) + 10
        conn.execute(
            "INSERT INTO app_launchers(name, exe_path, args, note, sort_order, category, detect_port) VALUES(?,?,?,?,?,?,?) "
            "ON CONFLICT(exe_path) DO UPDATE SET name=excluded.name, args=excluded.args, note=excluded.note, category=excluded.category, detect_port=excluded.detect_port",
            (name, str(rp), args, note, next_order, category, detect_port),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM app_launchers WHERE exe_path=?", (str(rp),)
        ).fetchone()
        d = dict(row)
        # 抽取 exe 图标（失败不影响主流程）
        icon_url = extract_icon(str(rp), d['id'])
        if icon_url:
            conn.execute(
                "UPDATE app_launchers SET icon_path=? WHERE id=?",
                (icon_url, d['id']),
            )
            conn.commit()
            d['icon_path'] = icon_url
        return d
    finally:
        conn.close()


def list_apps():
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT * FROM app_launchers ORDER BY sort_order ASC, id ASC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_app(app_id):
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT icon_path FROM app_launchers WHERE id=?", (app_id,)
        ).fetchone()
        conn.execute("DELETE FROM app_launchers WHERE id=?", (app_id,))
        conn.commit()
        # 清图标文件
        if row and row['icon_path']:
            try:
                p = ICON_DIR / f"{app_id}.png"
                if p.exists():
                    p.unlink()
            except Exception:
                pass
    finally:
        conn.close()


def get_icon(app_id):
    """读取图标 PNG 二进制（供 /icon/{id} 返回）。不存在返回 None。"""
    p = ICON_DIR / f"{app_id}.png"
    if not p.exists():
        return None
    return p.read_bytes()


def update_app(app_id, name=None, exe_path=None, category=None, note=None, args=None, detect_port=None):
    """修改应用元信息（含 exe_path）。若 exe_path 变更且文件存在，自动重新抽取图标。
    detect_port 传 None 表示保持原值；传 0/'' 表示清除；传数字表示设置。"""
    if name is not None and not name.strip():
        raise ValueError('应用名不能为空')
    new_exe = None
    if exe_path is not None:
        new_exe = Path(exe_path)
        if not new_exe.exists():
            raise ValueError(f'可执行文件不存在：{new_exe}')
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT * FROM app_launchers WHERE id=?", (app_id,)
        ).fetchone()
        if not row:
            raise ValueError('应用不存在')
        d = dict(row)
        new_name = name.strip() if name is not None else d['name']
        new_category = category if category is not None else d['category']
        new_note = note if note is not None else d['note']
        new_args = args if args is not None else d['args']
        if detect_port is None:
            new_port = d.get('detect_port')
        else:
            new_port = _norm_port(detect_port)  # 0/'' 也会被归一为 None（即清除）
        exe_changed = False
        if new_exe is not None and str(new_exe) != d['exe_path']:
            # 检查新路径是否被其他应用占用
            dup = conn.execute(
                "SELECT id FROM app_launchers WHERE exe_path=? AND id != ?",
                (str(new_exe), app_id),
            ).fetchone()
            if dup:
                raise ValueError(f'该可执行文件路径已被其他应用占用（id={dup["id"]}）')
            exe_changed = True
            # 删掉旧图标（如果存在）
            if d.get('icon_path'):
                try:
                    old_icon = ICON_DIR / f"{app_id}.png"
                    if old_icon.exists():
                        old_icon.unlink()
                except Exception:
                    pass
            d['exe_path'] = str(new_exe)
            d['icon_path'] = None
        conn.execute(
            "UPDATE app_launchers SET name=?, exe_path=?, category=?, note=?, args=?, detect_port=? WHERE id=?",
            (new_name, d['exe_path'], new_category, new_note, new_args, new_port, app_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM app_launchers WHERE id=?", (app_id,)
        ).fetchone()
        d = dict(row)
        # 若还没有图标（含路径变更后旧图标被清），尝试自动补抽
        if not d.get('icon_path') and d.get('exe_path'):
            icon_url = extract_icon(d['exe_path'], app_id)
            if icon_url:
                conn.execute(
                    "UPDATE app_launchers SET icon_path=? WHERE id=?",
                    (icon_url, app_id),
                )
                conn.commit()
                d['icon_path'] = icon_url
        return d
    finally:
        conn.close()


def update_order(id_list):
    """按传入 id 顺序重写 sort_order（id_list 为排好序的 id 数组）。"""
    if not id_list:
        return True
    conn = _conn()
    try:
        for idx, app_id in enumerate(id_list):
            conn.execute(
                "UPDATE app_launchers SET sort_order = ? WHERE id = ?",
                ((idx + 1) * 10, app_id),
            )
        conn.commit()
        return True
    finally:
        conn.close()


# ============ 启动 ============
def _match_keys(real_exe):
    """从配置的 exe 路径提取检测关键字。

    返回 (exe文件名小写, 词根, 所在目录小写, 是否脚本, 脚本名stem)。
    词根 = 去掉 Launcher/Start/Bootstrapper 等壳后缀后的主词（用于 launcher 型应用：
    配置 DingtalkLauncher.exe 但真实窗口进程是 DingTalk.exe；配置 AndrowsLauncher.exe
    但真实窗口进程是 AndrowsStore.exe）。
    """
    p = Path(real_exe)
    stem = p.stem.lower()
    suffix = p.suffix.lower()
    is_script = suffix in ('.bat', '.cmd')
    root = stem
    for suf in ('launcher', 'bootstrapper', 'starter', 'start', 'upd'):
        if root.endswith(suf) and len(root) - len(suf) >= 4:
            root = root[: -len(suf)]
            break
    return p.name.lower(), root, str(p.parent).lower().rstrip('\\'), is_script, stem


def _find_running_hwnds(exe_path):
    """查找目标应用的可见窗口句柄列表。匹配规则（命中任一即算）：
      1) 进程名 == 配置 exe 文件名（普通应用）
      2) 进程名以"词根"开头（launcher 壳型：DingtalkLauncher→DingTalk.exe、AndrowsLauncher→AndrowsStore.exe）
      3) 进程 exe 路径以配置 exe 所在目录为前缀（同目录/子目录下的主程序；服务进程读不到路径会 AccessDenied，跳过不影响）
      4) .bat/.cmd 脚本：可见窗口标题包含脚本文件名（cmd 控制台标题一般是 'cmd.exe - 启动webui.bat'）
    """
    try:
        import win32gui
        import win32process
        import psutil
    except Exception:
        return []
    real_exe = _resolve_lnk(exe_path)
    exe_name, root, exe_dir, is_script, stem = _match_keys(real_exe)
    found = []

    def enum_cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
        except Exception:
            return
        # 脚本型：按窗口标题匹配
        if is_script:
            try:
                title = win32gui.GetWindowText(hwnd) or ''
            except Exception:
                title = ''
            if stem and stem in title.lower():
                found.append(hwnd)
            return
        try:
            proc = psutil.Process(pid)
            proc_name = (proc.name() or '').lower()
        except Exception:
            return
        if proc_name == exe_name:
            found.append(hwnd)
            return
        if root and len(root) >= 4 and proc_name.startswith(root):
            found.append(hwnd)
            return
        try:
            proc_path = (proc.exe() or '').lower()
            if exe_dir and proc_path.startswith(exe_dir):
                found.append(hwnd)
        except Exception:
            pass

    try:
        win32gui.EnumWindows(enum_cb, None)
    except Exception:
        pass
    return found


def _force_foreground(hwnd):
    """把窗口强行提到最前（盖过当前任何窗口，含浏览器）。

    关键点：Windows 会拒绝"非前台线程"调用 SetForegroundWindow（只闪任务栏）。
    解法：用 AttachThreadInput 把本线程临时 attach 到当前前台窗口线程，再置顶，最后 Detach。
    """
    try:
        import win32gui
        import win32con
        import win32api

        # 恢复最小化
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        # 先尝试直接置顶（多数情况够用）
        win32gui.SetForegroundWindow(hwnd)

        # 若被系统拒绝（前台线程不是我们），用 AttachThreadInput 绕过
        fg = win32gui.GetForegroundWindow()
        if fg and fg != hwnd:
            my_thread = win32api.GetCurrentThreadId()
            try:
                fg_thread, _ = win32gui.GetWindowThreadProcessId(fg)
                target_thread, _ = win32gui.GetWindowThreadProcessId(hwnd)
                if fg_thread and fg_thread != my_thread:
                    win32gui.AttachThreadInput(fg_thread, my_thread, True)
                    try:
                        win32gui.SetForegroundWindow(hwnd)
                    finally:
                        win32gui.AttachThreadInput(fg_thread, my_thread, False)
            except Exception:
                pass
    except Exception:
        pass


def is_running(app_id):
    """查询应用是否在运行。优先按 detect_port（web 服务型）判定，否则走窗口检测。"""
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT * FROM app_launchers WHERE id=?", (app_id,)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        raise ValueError('应用不存在')
    if row['detect_port']:
        running = _port_listening(row['detect_port'])
    else:
        running = len(_find_running_hwnds(str(row['exe_path']))) > 0
    return {'id': app_id, 'running': running}


def launch_app(app_id, force_new=False):
    """启动/切换到应用。

    - force_new=False（默认）：若该程序已在运行，则直接把已有窗口置顶（不重复启动）；
      若没运行，正常启动后再置顶。
    - force_new=True：忽略已运行判断，强制新开一个实例（多开）。
    返回 dict：{"action": "activate"/"launch", "name": ...}
    """
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT * FROM app_launchers WHERE id=?", (app_id,)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        raise ValueError('应用不存在')
    exe = Path(row['exe_path'])
    if not exe.exists():
        raise ValueError(f'可执行文件不存在：{exe}')
    name = row['name']
    args = (row['args'] or '').strip()

    # 去重：未强制新开 && 已在运行 -> 直接置顶
    if not force_new:
        running = _find_running_hwnds(str(exe))
        if running:
            # 置顶第一个可见窗口（通常主窗口）
            _force_foreground(running[0])
            return {'action': 'activate', 'name': name}

    # 启动新实例
    # 第 1 优先：explorer.exe 打开（最贴近"双击"，对 Electron / 中文空格路径最可靠）
    # 第 2 兜底：ShellExecute（Windows 官方启动动词）
    # 第 3 兜底：os.startfile / 直接 Popen
    launched = False
    try:
        subprocess.Popen(['explorer.exe', str(exe)])
        launched = True
    except Exception:
        pass
    if not launched:
        try:
            import win32api
            import win32con
            win32api.ShellExecute(0, 'open', str(exe), args if args else '', str(exe.parent), win32con.SW_SHOWNORMAL)
            launched = True
        except Exception:
            pass
    if not launched:
        try:
            if args:
                subprocess.Popen([str(exe)] + args.split(), shell=False)
            else:
                os.startfile(str(exe))
        except Exception:
            subprocess.Popen([str(exe)] + (args.split() if args else []))

    # 稍等程序起来，尝试把窗口提到前台（盖过当前窗口）
    import time
    time.sleep(1.2)
    running = _find_running_hwnds(str(exe))
    if running:
        _force_foreground(running[0])
    return {'action': 'launch', 'name': name}
