"""filespace/service.py —— 书签 CRUD + 目录浏览 + 文件读取 + 系统打开

不是 AI 功能，没有生成/校验/审核，故只保留 service（业务）+ router（装配），
路径安全在 security.py。
"""

import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from common import db
from filespace import security


# ============ Windows 下查询占用文件的进程（给重命名失败时更精确的提示） ============
if sys.platform == 'win32':
    import ctypes
    import ctypes.wintypes as wt

    _rstrtmgr = ctypes.windll.rstrtmgr
    _rstrtmgr.RmStartSession.argtypes = [ctypes.POINTER(wt.DWORD), wt.DWORD, wt.LPWSTR]
    _rstrtmgr.RmStartSession.restype = wt.DWORD
    _rstrtmgr.RmEndSession.argtypes = [wt.DWORD]
    _rstrtmgr.RmEndSession.restype = wt.DWORD
    _rstrtmgr.RmRegisterResources.argtypes = [
        wt.DWORD, wt.UINT, ctypes.POINTER(wt.LPWSTR),
        wt.UINT, ctypes.c_void_p, wt.UINT, ctypes.c_void_p
    ]
    _rstrtmgr.RmRegisterResources.restype = wt.DWORD
    _rstrtmgr.RmGetList.argtypes = [
        wt.DWORD, ctypes.POINTER(wt.UINT), ctypes.POINTER(wt.UINT),
        ctypes.c_void_p, ctypes.POINTER(wt.DWORD)
    ]
    _rstrtmgr.RmGetList.restype = wt.DWORD

    _kernel32 = ctypes.windll.kernel32
    _kernel32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    _kernel32.OpenProcess.restype = wt.HANDLE
    _kernel32.QueryFullProcessImageNameW.argtypes = [
        wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)
    ]
    _kernel32.QueryFullProcessImageNameW.restype = wt.BOOL
    _kernel32.CloseHandle.argtypes = [wt.HANDLE]
    _kernel32.CloseHandle.restype = wt.BOOL
    _PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    class _RM_UNIQUE_PROCESS(ctypes.Structure):
        _pack_ = 8
        _fields_ = [
            ('dwProcessId', wt.DWORD),
            ('ProcessStartTime', wt.FILETIME),
        ]

    class _RM_PROCESS_INFO(ctypes.Structure):
        _pack_ = 8
        _fields_ = [
            ('Process', _RM_UNIQUE_PROCESS),
            ('strAppName', wt.WCHAR * 256),
            ('strServiceShortName', wt.WCHAR * 64),
            ('ApplicationType', wt.DWORD),
            ('AppStatus', wt.ULONG),
            ('TSSessionId', wt.DWORD),
            ('bRestartable', wt.BOOL),
        ]

    def _find_locking_processes(path: str):
        """用 Windows Restart Manager 查找正在占用指定文件的进程列表。"""
        try:
            session = wt.DWORD()
            key = ctypes.create_unicode_buffer(256)
            ret = _rstrtmgr.RmStartSession(ctypes.byref(session), 0, key)
            if ret != 0:
                return []
            try:
                paths = (wt.LPWSTR * 1)(ctypes.c_wchar_p(str(path)))
                ret = _rstrtmgr.RmRegisterResources(session.value, 1, paths, 0, None, 0, None)
                if ret != 0:
                    return []
                needed = wt.UINT()
                proc_info = wt.UINT()
                reboot = wt.DWORD()
                ret = _rstrtmgr.RmGetList(
                    session.value, ctypes.byref(needed), ctypes.byref(proc_info),
                    None, ctypes.byref(reboot)
                )
                if ret != 0 and ret != 234:  # ERROR_MORE_DATA
                    return []
                names = []
                if needed.value > 0:
                    arr = (_RM_PROCESS_INFO * needed.value)()
                    proc_info.value = needed.value
                    ret = _rstrtmgr.RmGetList(
                        session.value, ctypes.byref(needed), ctypes.byref(proc_info),
                        arr, ctypes.byref(reboot)
                    )
                    if ret == 0:
                        for i in range(proc_info.value):
                            info = arr[i]
                            pid = info.Process.dwProcessId
                            # 尝试拿到占用进程的可执行文件路径，帮助用户区分是哪个 Python/Electron 实例
                            exe_path = ''
                            try:
                                hproc = _kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                                if hproc:
                                    buf = ctypes.create_unicode_buffer(1024)
                                    size = wt.DWORD(1024)
                                    if _kernel32.QueryFullProcessImageNameW(hproc, 0, buf, ctypes.byref(size)):
                                        exe_path = buf.value
                                    _kernel32.CloseHandle(hproc)
                            except Exception:
                                pass
                            if exe_path:
                                names.append(f"{info.strAppName} (PID {pid}): {exe_path}")
                            else:
                                names.append(f"{info.strAppName} (PID {pid})")
                return names
            finally:
                try:
                    _rstrtmgr.RmEndSession(session.value)
                except Exception:
                    pass
        except Exception:
            return []
else:
    def _find_locking_processes(path: str):
        return []


def _conn():
    return db.get_conn()


def _ensure_table():
    """确保 filespace_roots 表存在（空库首次启动自包含建表，不依赖缺失的 schema 目录）。"""
    conn = _conn()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS filespace_roots (
              id         INTEGER PRIMARY KEY AUTOINCREMENT,
              name       TEXT    NOT NULL,
              path       TEXT    NOT NULL UNIQUE,
              note       TEXT,
              created_at TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
              sort_order INTEGER NOT NULL DEFAULT 0,
              category TEXT NOT NULL DEFAULT '未分类',
              cover_path TEXT,
              pinned_tags TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


_ensure_table()


def _root_dict(row):
    """把一行 filespace_roots 转成前端友好的 dict（含 is_dir / default_color / pinned_tags 字典）。"""
    d = dict(row)
    d['is_dir'] = Path(d['path']).is_dir()
    d['default_color'] = default_color(d['id'])
    d['pinned_tags'] = _normalize_tags(d.get('pinned_tags'), str(Path(d['path'])))
    return d


# ============ 书签 ============
def add_root(name, path, note=None, category='未分类'):
    """新增/更新一个书签（按 path 去重）。允许目录或文件。新增时放到末尾。"""
    if not name:
        raise ValueError('书签名不能为空')
    rp = security.resolve_path(path)
    if not rp.exists():
        raise ValueError(f'路径不存在：{rp}')
    if not category:
        category = '未分类'
    conn = _conn()
    try:
        # 取当前最大排序值，新书签放最后
        max_row = conn.execute(
            "SELECT MAX(sort_order) as m FROM filespace_roots"
        ).fetchone()
        next_order = (max_row['m'] or 0) + 10
        conn.execute(
            "INSERT INTO filespace_roots(name, path, note, sort_order, category) VALUES(?,?,?,?,?) "
            "ON CONFLICT(path) DO UPDATE SET name=excluded.name, note=excluded.note, category=excluded.category",
            (name, str(rp), note, next_order, category),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM filespace_roots WHERE path=?", (str(rp),)
        ).fetchone()
        return _root_dict(row)
    finally:
        conn.close()


def list_roots():
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT * FROM filespace_roots ORDER BY sort_order ASC, id ASC"
        ).fetchall()
        out = []
        for r in rows:
            out.append(_root_dict(r))
        return out
    finally:
        conn.close()


def delete_root(root_id):
    conn = _conn()
    try:
        conn.execute("DELETE FROM filespace_roots WHERE id=?", (root_id,))
        conn.commit()
    finally:
        conn.close()


def update_root(root_id, name=None, category=None, note=None, path=None):
    """修改书签元信息（含 path）。path 传入时校验存在性 + 与其他书签的唯一冲突。"""
    if name is not None and not name.strip():
        raise ValueError('书签名不能为空')
    new_path_str = None
    if path is not None:
        rp = security.resolve_path(path)
        if not rp.exists():
            raise ValueError(f'路径不存在：{rp}')
        new_path_str = str(rp)
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT * FROM filespace_roots WHERE id=?", (root_id,)
        ).fetchone()
        if not row:
            raise ValueError('书签不存在')
        d = dict(row)
        new_name = name.strip() if name is not None else d['name']
        new_category = category if category is not None else d['category']
        new_note = note if note is not None else d['note']
        if new_path_str is not None and new_path_str != d['path']:
            dup = conn.execute(
                "SELECT id FROM filespace_roots WHERE path=? AND id != ?",
                (new_path_str, root_id),
            ).fetchone()
            if dup:
                raise ValueError(f'该路径已被其他目录占用（id={dup["id"]}）')
        else:
            new_path_str = d['path']
        conn.execute(
            "UPDATE filespace_roots SET name=?, category=?, note=?, path=? WHERE id=?",
            (new_name, new_category, new_note, new_path_str, root_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM filespace_roots WHERE id=?", (root_id,)
        ).fetchone()
        return _root_dict(row)
    finally:
        conn.close()


def update_order(id_list):
    """按传入 id 顺序重写 sort_order（id_list 为排好序的 id 数组）。"""
    if not id_list:
        return True
    conn = _conn()
    try:
        for idx, root_id in enumerate(id_list):
            conn.execute(
                "UPDATE filespace_roots SET sort_order = ? WHERE id = ?",
                ((idx + 1) * 10, root_id),
            )
        conn.commit()
        return True
    finally:
        conn.close()


# ============ 文件夹快捷入口（任意层级，持久化在 filespace_roots.pinned_tags） ============
# pinned_tags 存储结构：dict（路径 → 直接子文件夹名列表）
#   { "F:/根目录": ["子A","子B"], "F:/根目录/子A": ["更深1","更深2"], ... }
# 任意层级都能生成：在哪儿点「扫描本文件夹子目录」，就扫描那个文件夹的直接子文件夹写入该路径键。
# 不判断层级深度、不设上限；文件夹原名原样保留（含 NN- 前缀与括号）。
# 删除入口时级联清掉其下整条分支。
def _normalize_tags(raw, root_path):
    """把 DB 里的 pinned_tags 解析为 {路径: [子文件夹名]} 字典（兼容旧格式）。

    - None/空/非法 → {}
    - 旧数组格式 [a,b] → { root_path: [a,b] }
    - 旧 2 层 map {一级: [二级]}（键是相对根的一级文件夹名）→ 展开为路径键字典
    - 新格式（键已是绝对路径）→ 原样返回（值统一为列表）
    写入的键保留 root_path 原有的路径分隔符，与 generate_tags 实写的键保持一致。
    """
    original_root = root_path or ''
    norm_root = original_root.replace('\\', '/').rstrip('/')
    if not raw:
        return {}
    try:
        v = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return {}
    if isinstance(v, list):
        return {original_root: [str(x) for x in v]}
    if not isinstance(v, dict):
        return {}
    # 判断是否已是新格式（键含路径分隔符 / 或以 root_path 开头）
    is_path_map = any(
        ('/' in str(k) or '\\' in str(k) or str(k).replace('\\', '/').startswith(norm_root))
        for k in v.keys()
    )
    if is_path_map:
        out = {}
        for k, val in v.items():
            out[str(k)] = list(val) if isinstance(val, list) else []
        return out
    # 旧 2 层 map：键是一级文件夹名（相对根），展开为路径键（沿用 root 原有分隔符）
    sep = '\\' if '\\' in original_root else '/'
    out = {}
    root_children = []
    for name, subs in v.items():
        name = str(name)
        root_children.append(name)
        out[sep.join([original_root.rstrip(sep), name])] = list(subs) if isinstance(subs, list) else []
    if root_children:
        out[original_root.rstrip(sep)] = root_children
    return out


def generate_tags(root_id, folder_path):
    """生成/覆盖某个文件夹的快捷入口：扫描 folder_path 的直接子文件夹，写入 pinned_tags[folder_path]。

    任意层级都可调用（folder_path 须在书签根目录内），不设层级上限。
    """
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM filespace_roots WHERE id=?", (root_id,)).fetchone()
        if not row:
            raise ValueError('目录不存在')
        root_path = str(security.resolve_path(row['path']))
        rp = security.resolve_path(folder_path)
        # 校验 folder_path 在书签根目录内（防越权写其他目录）
        norm_root = root_path.replace('\\', '/').rstrip('/')
        norm_fp = str(rp).replace('\\', '/').rstrip('/')
        if norm_fp != norm_root and not norm_fp.startswith(norm_root + '/'):
            raise ValueError('只能为该书签目录内的文件夹生成快捷入口')
        if not rp.exists():
            raise ValueError(f'路径不存在：{rp}')
        if not rp.is_dir():
            raise ValueError('该路径不是目录，无法生成快捷入口')
        names = [c.name for c in sorted(rp.iterdir()) if c.is_dir()]
        old_map = _normalize_tags(row['pinned_tags'], root_path)
        old_map[str(rp)] = names
        conn.execute(
            "UPDATE filespace_roots SET pinned_tags=? WHERE id=?",
            (json.dumps(old_map, ensure_ascii=False), root_id),
        )
        conn.commit()
        return _root_dict(conn.execute("SELECT * FROM filespace_roots WHERE id=?", (root_id,)).fetchone())
    finally:
        conn.close()


def set_tags(root_id, tag_map):
    """整体覆盖某根目录的快捷入口 map（供单个入口/分支移除、或清空后回写）。
    tag_map 为完整 {路径: [子文件夹名]} 字典。"""
    if not isinstance(tag_map, dict):
        tag_map = {}
    norm = {}
    for k, v in tag_map.items():
        norm[str(k)] = list(v) if isinstance(v, list) else []
    conn = _conn()
    try:
        conn.execute(
            "UPDATE filespace_roots SET pinned_tags=? WHERE id=?",
            (json.dumps(norm, ensure_ascii=False), root_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM filespace_roots WHERE id=?", (root_id,)).fetchone()
        if not row:
            raise ValueError('目录不存在')
        return _root_dict(row)
    finally:
        conn.close()


# ============ 封面 ============
# 默认调色板：10 种纯色，按书签 id 循环分配
DEFAULT_PALETTE = [
    '#34c759',  # 绿
    '#6a5cff',  # 紫
    '#ff9f0a',  # 琥珀
    '#ff3b30',  # 红
    '#2bb6ff',  # 蓝
    '#ff7a59',  # 橙红
    '#4ecdc4',  # 青
    '#ff5c8a',  # 粉
    '#8b5cf6',  # 深紫
    '#36e0c8',  # 薄荷
]


def default_color(root_id):
    """按 id 取默认纯色（10 色循环）。"""
    return DEFAULT_PALETTE[root_id % len(DEFAULT_PALETTE)]


def _cover_to_rel(p: Path) -> str:
    """把封面路径转成相对 DATA_DIR 的字符串（保证 workspace 可整体复制/迁移）。
    不在 DATA_DIR 下则原样保留绝对路径，不破坏既有逻辑。"""
    try:
        return str(p.relative_to(db.DATA_DIR))
    except ValueError:
        return str(p)


def set_cover(root_id, cover_path=None):
    """设置/清空书签封面。cover_path 为本地图片绝对路径；None=恢复默认色块。
    库内只存相对 DATA_DIR 的路径，复制 workspace 到其他位置/版本后封面仍可正常解析。"""
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT * FROM filespace_roots WHERE id=?", (root_id,)
        ).fetchone()
        if not row:
            raise ValueError('书签不存在')
        if cover_path is not None:
            cp = security.resolve_path(cover_path)
            if not cp.is_file():
                raise ValueError('封面图片不存在')
            if security.classify(cp.name) != 'image':
                raise ValueError('只支持图片作为封面')
            cover_value = _cover_to_rel(cp)
        else:
            cover_value = None
        conn.execute(
            "UPDATE filespace_roots SET cover_path=? WHERE id=?",
            (cover_value, root_id),
        )
        conn.commit()
        out = dict(conn.execute(
            "SELECT * FROM filespace_roots WHERE id=?", (root_id,)
        ).fetchone())
        out['is_dir'] = Path(out['path']).is_dir()
        out['default_color'] = default_color(root_id)
        return out
    finally:
        conn.close()


def migrate_cover_paths():
    """存量修复（幂等）：将 filespace_roots.cover_path 统一为相对 DATA_DIR 的路径。
    - 已是相对路径：跳过。
    - 绝对路径且位于 DATA_DIR 下：转相对。
    - 绝对路径但不在 DATA_DIR 下（多见于把旧 workspace 复制到新版本文件夹后，
      路径仍指向旧 release 目录）：若同名文件已存在于新 covers 目录，则改写为相对新位置。
    在后端启动时调用一次即可，失败仅打日志不阻断启动。"""
    try:
        conn = _conn()
    except Exception as e:
        print('[migrate_cover_paths] 打开数据库失败:', e)
        return
    try:
        covers_dir = db.DATA_DIR / 'covers'
        rows = conn.execute(
            "SELECT id, cover_path FROM filespace_roots WHERE cover_path IS NOT NULL"
        ).fetchall()
        for r in rows:
            cp = r['cover_path']
            if not cp:
                continue
            p = Path(cp)
            if not p.is_absolute():
                continue  # 已是相对路径
            # 尝试直接转相对 DATA_DIR
            try:
                rel = str(p.relative_to(db.DATA_DIR))
                conn.execute(
                    "UPDATE filespace_roots SET cover_path=? WHERE id=?",
                    (rel, r['id']),
                )
                continue
            except ValueError:
                pass
            # 旧绝对路径失效：尝试按文件名在新 covers 目录找回（复制 workspace 场景）
            candidate = covers_dir / p.name
            if candidate.is_file():
                rel = str(candidate.relative_to(db.DATA_DIR))
                conn.execute(
                    "UPDATE filespace_roots SET cover_path=? WHERE id=?",
                    (rel, r['id']),
                )
        conn.commit()
    except Exception as e:
        print('[migrate_cover_paths] 迁移失败（已跳过）:', e)
    finally:
        conn.close()


def read_cover_b64(root_id):
    """读取书签封面图片的 base64（用于前端 <img>）。无封面返回 None。"""
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT cover_path FROM filespace_roots WHERE id=?", (root_id,)
        ).fetchone()
        if not row or not row['cover_path']:
            return None
        raw = row['cover_path']
        p = Path(raw)
        if not p.is_absolute():
            # 新格式：相对 DATA_DIR，运行时拼回绝对路径
            p = db.DATA_DIR / p
        if not p.is_file():
            # 兼容极旧绝对路径且文件已不在原处：返回 None，前端用默认色块
            return None
        if p.stat().st_size > security.PREVIEW_LIMIT:
            return None  # 太大，前端用默认色块
        b = p.read_bytes()
        ext = p.suffix.lower().lstrip('.') or 'png'
        mime = {
            'jpg': 'jpeg', 'jpeg': 'jpeg', 'png': 'png', 'gif': 'gif',
            'webp': 'webp', 'bmp': 'bmp', 'svg': 'svg+xml',
        }.get(ext, 'png')
        return "data:image/%s;base64," % mime + base64.b64encode(b).decode('ascii')
    finally:
        conn.close()


# ============ 目录浏览 ============
def list_dir(raw_path):
    """列出某目录下的一层内容（不递归）。返回 {path, parent, items[]}。"""
    rp = security.resolve_path(raw_path)
    if not rp.exists():
        raise ValueError('路径不存在')
    if not rp.is_dir():
        raise ValueError('不是目录')
    items = []
    for child in sorted(rp.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        try:
            st = child.stat()
            items.append({
                'name': child.name,
                'path': str(child),
                'is_dir': child.is_dir(),
                'type': 'dir' if child.is_dir() else security.classify(child.name),
                'size': st.st_size if not child.is_dir() else None,
                'mtime': st.st_mtime,
            })
        except (PermissionError, OSError):
            continue
    return {
        'path': str(rp),
        'parent': str(rp.parent) if rp.parent != rp else None,
        'items': items,
    }


def rename(raw_old_path, new_name):
    """重命名文件/目录（仅改最后一段名字，不能跨目录、不能含路径分隔符）。

    Windows 上文件被外部程序（播放器/资源管理器预览/杀软）以不带 FILE_SHARE_DELETE
    模式打开时，os.rename 会抛 PermissionError(WinError 5 / WinError 32)。对此做短暂重试，
    仍失败则转成友好的 ValueError（前端可见提示），而不是裸 500。
    """
    rp = security.resolve_path(raw_old_path)
    if not rp.exists():
        raise ValueError('源文件不存在')
    if not new_name or '/' in new_name or '\\' in new_name or new_name in ('.', '..'):
        raise ValueError('新名字不合法（不能含路径分隔符或 ..）')
    target = rp.parent / new_name
    if target.exists():
        raise ValueError('目标名称已存在，无法覆盖')
    # 先主动关闭当前后端进程自己还打开着的该文件流句柄，避免自己被自己锁住。
    try:
        from filespace.router import close_streams_for
        close_streams_for(str(rp))
    except Exception:
        pass
    last_err = None
    # 前端已尽量释放 <video> 句柄，后端 /stream 也使用 FILE_SHARE_DELETE 打开文件；
    # 这里再做短暂重试作为兜底，覆盖杀软/资源管理器预览等短暂持锁的情况。
    for attempt in range(12):
        try:
            rp.rename(target)
            last_err = None
            break
        except PermissionError as e:
            last_err = e
            time.sleep(0.3 + attempt * 0.15)
        except OSError as e:
            raise ValueError(f'系统错误：{e}')
    if last_err is not None:
        # 尝试定位具体是哪个进程在占用，给用户更明确的提示
        lockers = _find_locking_processes(str(rp))
        if lockers:
            # 如果占用者只有本程序自己（python/electron），提示关闭预览即可
            self_tokens = ('python', 'suxiaomo-studio', 'electron')
            only_self = all(
                any(tok in name.lower() for tok in self_tokens)
                for name in lockers
            )
            if only_self:
                raise ValueError(
                    '文件正被本程序预览占用，请关闭视频预览/灯箱后再重试。'
                    f"（占用进程：{', '.join(lockers)}）"
                )
            raise ValueError(
                '文件正被其他程序占用，请关闭后再重试。'
                f"（占用进程：{', '.join(lockers)}）"
            )
        raise ValueError('文件正被其他程序占用（如播放器/资源管理器预览），请关闭后重试')
    return {
        'old_path': str(rp),
        'new_path': str(target),
        'name': new_name,
        'is_dir': target.is_dir(),
        'type': 'dir' if target.is_dir() else security.classify(target.name),
    }


# ============ 文件读取（预览） ============
def read_text(raw_path, limit=security.PREVIEW_LIMIT):
    rp = security.resolve_path(raw_path)
    if not rp.is_file():
        raise ValueError('不是文件')
    if rp.stat().st_size > limit:
        return None  # 太大，前端改用系统打开
    return rp.read_text(encoding='utf-8', errors='replace')


def save_text(raw_path, content):
    """保存文本文件，覆盖写。仅允许保存已知文本扩展名。"""
    rp = security.resolve_path(raw_path)
    if not rp.is_file():
        raise ValueError('不是文件')
    if security.classify(rp.name) != 'text':
        raise ValueError('只允许保存文本类型文件')
    rp.write_text(content, encoding='utf-8', errors='replace')
    return True


def read_image_b64(raw_path, limit=security.PREVIEW_LIMIT):
    rp = security.resolve_path(raw_path)
    if not rp.is_file():
        raise ValueError('不是文件')
    if rp.stat().st_size > limit:
        return None
    b = rp.read_bytes()
    ext = rp.suffix.lower().lstrip('.') or 'png'
    mime = {
        'jpg': 'jpeg', 'jpeg': 'jpeg', 'png': 'png', 'gif': 'gif',
        'webp': 'webp', 'bmp': 'bmp', 'svg': 'svg+xml',
    }.get(ext, 'png')
    return "data:image/%s;base64," % mime + base64.b64encode(b).decode('ascii')


def resolve(raw_path):
    """供 router 用：规范化并校验路径存在"""
    rp = security.resolve_path(raw_path)
    if not rp.exists():
        raise ValueError('路径不存在')
    return rp


# ============ 系统打开 ============
def _unblock_file(p):
    """Windows 下静默移除文件的 Internet 区域标记（Zone.Identifier），
    避免 os.startfile 调系统程序打开时弹「安全警告」。不改变文件内容。"""
    if sys.platform != 'win32':
        return
    try:
        subprocess.run(
            ['powershell', '-NoProfile', '-NonInteractive', '-Command',
             'Unblock-File', '-LiteralPath', p],
            capture_output=True, check=False, timeout=15,
        )
    except Exception:
        pass  # 解除失败不影响后续打开


def open_path(raw_path):
    rp = security.resolve_path(raw_path)
    if not rp.exists():
        raise ValueError('路径不存在')
    p = str(rp)
    if rp.is_file():
        _unblock_file(p)
    try:
        os.startfile(p)  # Windows
    except AttributeError:
        # 非 Windows 兜底
        if sys.platform == 'darwin':
            subprocess.run(['open', p])
        else:
            subprocess.run(['xdg-open', p])
    return True


def open_parent(raw_path):
    """打开文件所在文件夹并高亮选中该文件（资源管理器）。"""
    rp = security.resolve_path(raw_path)
    if not rp.exists():
        raise ValueError('路径不存在')
    p = str(rp)
    parent = str(rp.parent)
    try:
        if sys.platform == 'win32':
            subprocess.run(['explorer', '/select,', p], check=False)
        elif sys.platform == 'darwin':
            subprocess.run(['open', '-R', p], check=False)
        else:
            # Linux 只能打开目录，无法保证选中文件
            subprocess.run(['xdg-open', parent], check=False)
    except Exception as e:
        raise ValueError(f'打开所在位置失败：{e}')
    return True


def delete_path(raw_path):
    """删除指定文件或目录（目录非空则递归删除）。操作不可逆，前端必须二次确认。"""
    rp = security.resolve_path(raw_path)
    if not rp.exists():
        raise ValueError('路径不存在')
    try:
        if rp.is_dir():
            import shutil
            shutil.rmtree(rp)
        else:
            rp.unlink()
    except PermissionError as e:
        raise ValueError(f'删除失败：文件或目录正被占用（{e}）')
    except OSError as e:
        raise ValueError(f'删除失败：{e}')
    return True


def search_dir(raw_path, q, max_depth=1, max_files=5000):
    """在当前目录及其直接子目录（深度 max_depth）内，按名称/路径关键词搜索文件/目录。

    用于文件空间「业务分类」标签快速定位（如点"人物"汇总所有人物相关素材）。
    - 当前层：匹配文件名含 q 的项
    - 直接子目录层：匹配文件名或完整路径含 q 的项（靠路径前缀，确保某分类目录下的所有文件都被命中）
    - 限制最大文件数 max_files，避免超大目录卡死
    返回结构与 list_dir.items 一致：{name, path, is_dir, type, size, mtime}
    """
    rp = security.resolve_path(raw_path)
    if not rp.exists():
        raise ValueError('路径不存在')
    if not rp.is_dir():
        raise ValueError('不是目录')
    ql = (q or '').strip().lower()
    if not ql:
        return []

    def _item(p):
        st = p.stat()
        return {
            'name': p.name,
            'path': str(p),
            'is_dir': p.is_dir(),
            'type': 'dir' if p.is_dir() else security.classify(p.name),
            'size': st.st_size if not p.is_dir() else None,
            'mtime': st.st_mtime,
        }

    results = []
    # 第一层：当前目录下直接项（仅文件名匹配）
    for child in sorted(rp.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        if len(results) >= max_files:
            break
        try:
            if ql in child.name.lower():
                results.append(_item(child))
        except (PermissionError, OSError):
            continue
    # 第二层：每个直接子目录内部（文件名或路径匹配）
    if max_depth >= 1:
        for child in sorted(rp.iterdir(), key=lambda x: x.name.lower()):
            if len(results) >= max_files:
                break
            if not child.is_dir():
                continue
            try:
                subs = sorted(child.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            except (PermissionError, OSError):
                continue
            for sub in subs:
                if len(results) >= max_files:
                    break
                try:
                    if ql in sub.name.lower() or ql in str(sub).lower():
                        results.append(_item(sub))
                except (PermissionError, OSError):
                    continue
    return results
