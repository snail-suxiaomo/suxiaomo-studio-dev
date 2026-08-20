"""app.py —— 入口：只做装配，不写业务

- 注册 login 路由
- 开 CORS（前端开发用，后续可收紧）
- 启动时跑 init_db() 建表 + 种子管理员

功能打包（按勾选过滤）：
- 开发态（SUXIAOMO_PACKAGED 未设置）：全量注册所有 router（与历史行为一致，
  不受 build_features.json 影响，避免「打包后残留的勾选」污染 dev）。
- 打包态（SUXIAOMO_PACKAGED=1）：仅注册 build_features.json 中启用的功能模块，
  未勾选功能不注册 router → 对应后端接口完全不存在。
"""

import os
import sys
import json
import importlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from common import db

# 关键：在所有业务模块 import 之前先把表建好（data/schema 下的建表 SQL）。
db.init_db()

PACKAGED = os.environ.get('SUXIAOMO_PACKAGED') == '1'
_HERE = os.path.dirname(os.path.abspath(__file__))


def _load_build_features():
    bf = os.path.join(_HERE, 'build_features.json')
    if not os.path.exists(bf):
        return None
    try:
        with open(bf, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def _include_spec(spec):
    """按 spec 动态导入模块并注册其 router（含 extraRouters）。

    注意：backend 各功能包通常不会在 __init__.py 里导出 router，
    因此直接 import 子模块 "{module}.router"，而不是 getattr(包, 'router')。
    """
    try:
        mod = importlib.import_module(f"{spec['module']}.router")
        app.include_router(mod.router)
        for ex in spec.get('extraRouters', []):
            ex_mod = importlib.import_module(f"{spec['module']}.{ex}")
            app.include_router(ex_mod.router)
    except Exception as e:
        print(f"[packaging] 注册后端模块 {spec.get('module')} 失败: {e}", file=sys.stderr)


# 开发态全量注册所需的 spec 列表（与历史行为一致；不读取 build_features.json）
_DEV_SPECS = [
    {'module': 'login', 'routerAttr': 'router', 'extraRouters': [], 'service': 'login', 'startup': 'ensure_seed_admin'},
    {'module': 'model_config', 'routerAttr': 'router', 'extraRouters': ['media_router'], 'service': 'model_config', 'startup': 'migrate_old_rows'},
    {'module': 'chat', 'routerAttr': 'router', 'extraRouters': [], 'service': None, 'startup': None},
    {'module': 'novel_project', 'routerAttr': 'router', 'extraRouters': [], 'service': None, 'startup': None},
    {'module': 'novel_split', 'routerAttr': 'router', 'extraRouters': [], 'service': None, 'startup': None},
    {'module': 'novel_synopsis', 'routerAttr': 'router', 'extraRouters': [], 'service': None, 'startup': None},
    {'module': 'novel_graph', 'routerAttr': 'router', 'extraRouters': [], 'service': None, 'startup': None},
    {'module': 'novel_diagnose', 'routerAttr': 'router', 'extraRouters': [], 'service': None, 'startup': None},
    {'module': 'novel_strategy', 'routerAttr': 'router', 'extraRouters': [], 'service': None, 'startup': None},
    {'module': 'novel_summary_table', 'routerAttr': 'router', 'extraRouters': [], 'service': None, 'startup': None},
    {'module': 'novel_rewrite', 'routerAttr': 'router', 'extraRouters': [], 'service': None, 'startup': None},
    {'module': 'novel_memory', 'routerAttr': 'router', 'extraRouters': [], 'service': None, 'startup': None},
    {'module': 'filespace', 'routerAttr': 'router', 'extraRouters': [], 'service': 'filespace', 'startup': 'migrate_cover_paths'},
    {'module': 'apps_launcher', 'routerAttr': 'router', 'extraRouters': [], 'service': None, 'startup': None},
    {'module': 'prompt_library', 'routerAttr': 'router', 'extraRouters': [], 'service': None, 'startup': None},
    {'module': 'free_resources', 'routerAttr': 'router', 'extraRouters': [], 'service': None, 'startup': None},
    {'module': 'web_nav', 'routerAttr': 'router', 'extraRouters': [], 'service': None, 'startup': None},
    {'module': 'novel_tweet', 'routerAttr': 'router', 'extraRouters': [], 'service': None, 'startup': None},
    {'module': 'daily_tasks', 'routerAttr': 'router', 'extraRouters': [], 'service': None, 'startup': None},
    {'module': 'viral_collection', 'routerAttr': 'router', 'extraRouters': [], 'service': None, 'startup': None},
    {'module': 'social_account', 'routerAttr': 'router', 'extraRouters': [], 'service': None, 'startup': None},
    {'module': 'key_vault', 'routerAttr': 'router', 'extraRouters': [], 'service': None, 'startup': None},
    {'module': 'prefs', 'routerAttr': 'router', 'extraRouters': [], 'service': None, 'startup': None},
]

app = FastAPI(title="suxiaomo-studio")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if PACKAGED:
    # 打包态：仅注册 build_features.json 中启用的功能（登录始终兜底注册）
    _bf = _load_build_features()
    _specs = (_bf or {}).get('backend', []) if _bf else []
    # 登录是核心，确保一定注册
    if not any(s.get('module') == 'login' for s in _specs):
        _specs = [{'module': 'login', 'routerAttr': 'router', 'extraRouters': [], 'service': 'login', 'startup': 'ensure_seed_admin'}] + _specs
    # prefs 是公共基础设施（提示词库/爆款收集前端调用 /api/prefs/*），确保一定注册
    if not any(s.get('module') == 'prefs' for s in _specs):
        _specs = _specs + [{'module': 'prefs', 'routerAttr': 'router', 'extraRouters': [], 'service': None, 'startup': None}]
    for _spec in _specs:
        _include_spec(_spec)
else:
    # 开发态：全量注册（与历史行为一致）
    from login import router as login_router
    from login import service as login_service
    from model_config import router as mc_router
    from model_config import service as mc_service
    from model_config import media_router as media_router
    from chat import router as chat_router
    from novel_project import router as proj_router
    from novel_split import router as split_router
    from novel_synopsis import router as synopsis_router
    from novel_graph import router as graph_router
    from novel_diagnose import router as diagnose_router
    from novel_strategy import router as strategy_router
    from novel_summary_table import router as summary_router
    from novel_rewrite import router as rewrite_router
    from novel_memory import router as memory_router
    from filespace import router as fs_router
    from filespace import service as fs_service
    from apps_launcher import router as apps_router
    from prompt_library import router as pl_router
    from free_resources import router as fr_router
    from web_nav import router as wn_router
    from novel_tweet import router as nt_router
    from daily_tasks import router as dt_router
    from viral_collection import router as vc_router
    from social_account import router as sa_router
    from ai_rule import router as airouter
    from key_vault import router as kv_router
    from prefs import router as prefs_router
    from usage_intro import router as usage_intro_router
    from manju_generate import router as manju_router
    from build_release import router as build_router

    app.include_router(login_router.router)
    app.include_router(mc_router.router)
    app.include_router(media_router.router)
    app.include_router(chat_router.router)
    app.include_router(proj_router.router)
    app.include_router(split_router.router)
    app.include_router(synopsis_router.router)
    app.include_router(graph_router.router)
    app.include_router(diagnose_router.router)
    app.include_router(strategy_router.router)
    app.include_router(summary_router.router)
    app.include_router(rewrite_router.router)
    app.include_router(memory_router.router)
    app.include_router(fs_router.router)
    app.include_router(apps_router.router)
    app.include_router(pl_router.router)
    app.include_router(fr_router.router)
    app.include_router(wn_router.router)
    app.include_router(nt_router.router)
    app.include_router(dt_router.router)
    app.include_router(vc_router.router)
    app.include_router(sa_router.router)
    app.include_router(kv_router.router)
    app.include_router(prefs_router.router)
    app.include_router(airouter.router)
    app.include_router(usage_intro_router.router)
    app.include_router(manju_router.router)
    app.include_router(build_router.router)

    # 日志查看：仅开发态注册（打包态不携带该模块，避免无 UI 的活接口暴露）
    from logs import router as logs_router
    from logs import router as logs_installer
    app.include_router(logs_router.router)
    logs_installer.install_error_logging(app)


@app.on_event("startup")
def startup():
    db.init_db()  # 跑 data/schema 下所有建表 SQL（只建不存在的表）
    if PACKAGED:
        # 打包态：仅对启用功能跑服务迁移（按 build_features.json 的 backend specs）
        _bf = _load_build_features()
        _specs = (_bf or {}).get('backend', []) if _bf else []
        for _spec in _specs:
            _svc = _spec.get('service')
            _fn = _spec.get('startup')
            if _svc and _fn:
                try:
                    _svc_mod = importlib.import_module(f"{_svc}.service")
                    getattr(_svc_mod, _fn)()
                except Exception as e:
                    print(f"[packaging] 启动迁移 {_svc}.{_fn} 失败: {e}", file=sys.stderr)
    else:
        # 开发态：全量迁移（与历史行为一致）
        login_service.ensure_seed_admin()  # users 为空则插 admin/admin
        mc_service.migrate_old_rows()      # 旧模型配置自动认领厂商/档案（幂等）
        fs_service.migrate_cover_paths()   # 封面路径统一为相对 DATA_DIR（幂等，复制 workspace 可移植）


@app.get("/api/health")
def health():
    return {"ok": True, "msg": "suxiaomo-studio 后端已启动"}
