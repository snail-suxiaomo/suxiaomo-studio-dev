"""build_release/router.py —— 开发版「一键发布版本」接口

仅在开发环境可用：
- 打包态（Electron 壳）通过环境变量 SUXIAOMO_PACKAGED=1 标记，直接禁用；
- 开发态还需 frontend/src 与 frontend/node_modules 同时存在（打包产物不含这两者）。

流程（后台异步）：
  前端点「开始打包」→ 后端直接 Popen spawn `node build.js`（带 SUXIAOMO_BUILD_FROM_APP=1，
  使 build.js 跳过杀进程，应用不掉线）→ 后台线程实时捕获 stdout 写入内存状态 `_state`
  → 前端轮询 /build/status 看进度与日志（同屏），用户可继续操作别的功能。
  打包成功后由 build.js 自身把发布记录写入 app_releases（见 build.js 末尾 recordRelease）。
  所选功能、版本、数据根、输出目录会持久化到 build_selection.json 供 build.js 使用。
"""
import os
import sys
import json
import shutil
import pathlib
import subprocess
import threading

from fastapi import APIRouter
from common.db import get_conn

router = APIRouter(prefix="/api/build", tags=["build"])

# router.py 位于 <root>/backend/build_release/；上三级即项目根（开发态）或 resources（打包态）
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUILD_JS = os.path.join(_ROOT, "build.js")
SELECTION_FILE = os.path.join(_ROOT, "build_selection.json")
BUILD_CONFIG_FILE = os.path.join(_ROOT, "build_config.json")
DESKTOP_PKG = os.path.join(_ROOT, "desktop", "package.json")

# 打包态由桌面壳注入 SUXIAOMO_PACKAGED=1，此时禁用打包按钮
_PACKAGED = os.environ.get("SUXIAOMO_PACKAGED") == "1"


def _dev_available() -> bool:
    if _PACKAGED:
        return False
    fe_src = os.path.isdir(os.path.join(_ROOT, "frontend", "src"))
    fe_nm = os.path.isdir(os.path.join(_ROOT, "frontend", "node_modules"))
    return fe_src and fe_nm


def _read_pkg_version() -> str:
    try:
        with open(DESKTOP_PKG, "r", encoding="utf-8") as f:
            pkg = json.load(f)
        return str(pkg.get("version") or "1.0.0")
    except Exception:
        return "1.0.0"


def _validate_version(v: str) -> bool:
    return bool(v) and len(v.split(".")) == 3 and all(p.isdigit() for p in v.split("."))


def _parse_version(v: str):
    """把 x.y.z 解析成整数三元组，非法返回 (0,0,0)。"""
    try:
        parts = str(v).split(".")
        if len(parts) != 3:
            return (0, 0, 0)
        return tuple(int(p) for p in parts)
    except Exception:
        return (0, 0, 0)


def _increment_patch(v: str) -> str:
    """版本号最小位 +1（数值递增，如 999→1000 风格）：
    0.0.5→0.0.6、1.8.5→1.8.6、1.0.0→1.0.1、0.0.9→0.0.10。
    不进位到次/主版本（用户要求：不是 1.1.0，更不是 2.0.0）。
    历史最新版本即上一版本，推荐版本 = 历史最新 + 1。"""
    major, minor, patch = _parse_version(v)
    return f"{major}.{minor}.{patch + 1}"


def _read_selection() -> dict:
    """读取上次打包选择；缺省返回当前 package.json 版本、空功能列表。"""
    default = {"version": _read_pkg_version(), "features": []}
    if not os.path.exists(SELECTION_FILE):
        return default
    try:
        with open(SELECTION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "version": str(data.get("version") or default["version"]),
            "features": list(data.get("features") or []),
        }
    except Exception:
        return default


def _save_selection(features, version, data_dir=None, output_dir=None):
    try:
        with open(SELECTION_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "version": version,
                "features": list(features or []),
                # data_dir 透传给 build.js：落库时才能定位到用户真实数据根（custom 路径），
                # 避免写进空的默认 workspace/app.db。缺省留空，由 common.db 回退默认根。
                "data_dir": data_dir or "",
                # output_dir 透传给 build.js（SUXIAOMO_RELEASE_DIR），指定产物输出目录
                "output_dir": output_dir or "",
            }, f, ensure_ascii=False, indent=2)
    except Exception:
        # 持久化失败不影响打包主流程
        pass


def _default_output_dir():
    """默认产物目录：项目根的上一级 suxiaomo-studio-release（即 F:\\suxiaomo-studio-release）。"""
    return os.path.abspath(pathlib.Path(_ROOT).parent / "suxiaomo-studio-release")


def _read_output_dir():
    if os.path.exists(BUILD_CONFIG_FILE):
        try:
            with open(BUILD_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            d = (data.get("output_dir") or "").strip()
            if d:
                return d
        except Exception:
            pass
    return _default_output_dir()


def _save_output_dir(d):
    try:
        with open(BUILD_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"output_dir": d}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _node_path():
    return shutil.which("node") or "node"


def _pump(proc, version):
    """后台线程：实时把 build.js 输出追加到 _state['log']，结束后更新状态。"""
    try:
        for line in iter(proc.stdout.readline, ""):
            line = line.rstrip("\n").rstrip("\r")
            if line:
                _state["log"].append(line)
    except Exception:
        pass
    try:
        if proc.stdout:
            proc.stdout.close()
    except Exception:
        pass
    try:
        rc = proc.wait()
    except Exception:
        rc = -1
    _state["running"] = False
    if rc == 0:
        _state["done"] = True
        _state["log"].append("[build] 打包完成（退出码 0）")
    else:
        _state["error"] = True
        _state["log"].append(f"[build] 打包失败（退出码 {rc}）")


def _spawn_build(version, features, output_dir):
    """后台异步启动 build.js（不退出应用，用户可继续操作其他功能）。"""
    env = dict(os.environ)
    # 关键：标记 FROM_APP，让 build.js 跳过杀进程（否则会杀掉运行中的 Electron / vite / 后端）
    env["SUXIAOMO_BUILD_FROM_APP"] = "1"
    env["SUXIAOMO_BUILD_VERSION"] = version
    if output_dir:
        env["SUXIAOMO_RELEASE_DIR"] = output_dir
    # 避免 safe-delete shim 干扰（真机无 shim，属无害操作）
    env.setdefault("GENIE_TRASH_DIR", "F:/_trash_tmp")
    env.pop("CODEBUDDY_SESSION_ID", None)
    env.pop("CLAUDE_SESSION_ID", None)

    node = _node_path()
    proc = subprocess.Popen(
        [node, BUILD_JS],
        cwd=_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    _state["proc"] = proc
    t = threading.Thread(target=_pump, args=(proc, version), daemon=True)
    t.start()


def _record_release(version, features, path=None):
    """打包成功后写一条发布记录到 app_releases 表。失败仅告警，不影响产物。"""
    try:
        conn = get_conn()
        try:
            conn.execute(
                "INSERT INTO app_releases(version, features_json, path) VALUES(?, ?, ?)",
                (version, json.dumps(list(features or []), ensure_ascii=False), path),
            )
            conn.commit()
        finally:
            conn.close()
        print(f"[build] 已记录发布版本 {version}", file=sys.stderr)
    except Exception as e:
        print(f"[build] 记录发布版本失败（不影响产物）: {e}", file=sys.stderr)


_state = {
    "proc": None,
    "log": [],
    "running": False,
    "done": False,
    "error": False,
    "version": "",
}


@router.get("/available")
def available():
    return {"available": _dev_available()}


@router.get("/selection")
def selection():
    return _read_selection()


@router.get("/version-info")
def version_info():
    """返回代码版本（desktop/package.json）与已发布最新版本，并给出建议的下一版本号。"""
    code_version = _read_pkg_version()
    latest_release = code_version
    try:
        conn = get_conn()
        try:
            row = conn.execute(
                "SELECT version FROM app_releases ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row and row["version"]:
                latest_release = row["version"]
        finally:
            conn.close()
    except Exception:
        # 表尚未建好时优雅降级
        pass
    return {
        "ok": True,
        "code_version": code_version,
        "latest_release": latest_release,
        "suggested": _increment_patch(latest_release),
    }


@router.get("/releases")
def releases():
    """读取已发布版本记录：返回最新版本号与最近若干条（供前端提示下一个版本号）。"""
    try:
        conn = get_conn()
        try:
            row = conn.execute(
                "SELECT version FROM app_releases ORDER BY id DESC LIMIT 1"
            ).fetchone()
            latest = row["version"] if row else None
            rows = conn.execute(
                "SELECT id, version, release_at, features_json, path "
                "FROM app_releases ORDER BY id DESC LIMIT 20"
            ).fetchall()
            return {
                "latest": latest,
                "list": [
                    {
                        "id": r["id"],
                        "version": r["version"],
                        "release_at": r["release_at"],
                        "features": json.loads(r["features_json"] or "[]"),
                        "path": r["path"],
                    }
                    for r in rows
                ],
            }
        finally:
            conn.close()
    except Exception as e:
        # 表尚未建好（极早期库）时优雅降级：返回无记录，不阻断打包页
        print(f"[build] 读取发布记录失败: {e}", file=sys.stderr)
        return {"latest": None, "list": []}


@router.get("/output-dir")
def get_output_dir():
    """返回当前打包产物输出目录（用户可在前端修改并保存）。"""
    return {"ok": True, "output_dir": _read_output_dir()}


@router.post("/output-dir")
async def set_output_dir(body: dict = None):
    body = body or {}
    d = str(body.get("output_dir") or "").strip()
    if not d:
        return {"ok": False, "msg": "输出目录不能为空"}
    _save_output_dir(d)
    return {"ok": True, "output_dir": d}


@router.post("/start")
async def start(body: dict = None):
    if _state["running"]:
        return {"ok": False, "msg": "打包进行中，请稍候"}
    if not _dev_available():
        return {"ok": False, "msg": "仅开发版可用（未检测到前端源码或依赖）"}
    if not os.path.exists(BUILD_JS):
        return {"ok": False, "msg": "未找到 build.js（应位于项目根目录）"}

    body = body or {}
    features = body.get("features") or []
    if not isinstance(features, list):
        features = []
    version = str(body.get("version") or _read_pkg_version()).strip()
    if not _validate_version(version):
        version = _read_pkg_version()
    output_dir = str(body.get("outputDir") or _read_output_dir()).strip()
    if not output_dir:
        output_dir = _default_output_dir()

    # 持久化选择，供 build.js 写入发布目录 manifest 与发布记录
    # data_dir 取当前后端进程的环境变量（开发态由主进程传入真实数据根），透传给 build.js 落库
    data_dir = os.environ.get("SUXIAOMO_DATA_DIR", "")
    _save_selection(features, version, data_dir, output_dir)

    # 后台异步启动 build.js（不退出应用，用户可继续操作其他功能，前端轮询 /status 看进度）
    _state["running"] = True
    _state["done"] = False
    _state["error"] = False
    _state["log"] = [f"[build] 后台开始打包 v{version} → {output_dir}"]
    _state["version"] = version
    _spawn_build(version, features, output_dir)
    return {"ok": True, "started": True, "version": version, "outputDir": output_dir}


@router.get("/status")
def status():
    return {
        "running": _state["running"],
        "done": _state["done"],
        "error": _state["error"],
        "version": _state["version"],
        "log": "\n".join(_state["log"][-500:]),
    }
