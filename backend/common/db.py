"""common/db.py —— 极简数据库小帮手（不是引擎）

职责只有三件，不拥有任何表结构：
1. get_conn()     给一个连「统一数据根」下 app.db 的 sqlite3 连接
2. init_db()      跑 schema（数据根/data/schema）下所有建表 SQL（只建不存在的表），再跑一次性迁移
3. get_config/set_config  读写 config 表里的配置行

统一数据根（DATA_ROOT）：
- 开发态 / 浏览器版 / 打包态 三版共用同一个根目录，默认在项目根的 workspace/：
      <项目根>/workspace/
          ├── app.db            ← 单一数据库（所有表）
          ├── data/             ← 图片 / 附件 / 封面等二进制
          └── projects/         ← 各小说项目产物（00-拆分 … 12-分镜）
- 可用环境变量 SUXIAOMO_DATA_DIR 整体覆盖该根目录（指向任意位置）。
- 首次启动：若数据根内没有 app.db，但旧位置（项目根 data/ + projects/）存在真实数据，
  则一次性把旧数据复制进数据根（幂等：已有 app.db 或旧位置无数据则跳过）。
- schema 建表 SQL / seed 种子：运行时落在数据根下的 data/schema（data/seed），首启若缺失
  则从应用包内（backend/bundled/{schema,seed}，由 SUXIAOMO_SCHEMA_DIR/SUXIAOMO_SEED_DIR 覆盖）
  复制进来，使数据根完全自包含、可整体复制迁移。
"""

import os
import shutil
import sqlite3
import sys
import uuid
from pathlib import Path

# 本文件位于 backend/common/db.py → 上两级是项目根 <PROJECT_ROOT>
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 统一数据根：三版共用。可用 SUXIAOMO_DATA_DIR 整体覆盖。
DATA_ROOT = Path(os.environ.get("SUXIAOMO_DATA_DIR") or (BASE_DIR / "workspace"))
DB_PATH = DATA_ROOT / "app.db"
DATA_DIR = DATA_ROOT / "data"
# 项目产物目录：默认数据根下的 projects\，可用 SUXIAOMO_PROJECTS_DIR 单独覆盖。
PROJECTS_DIR = Path(os.environ.get("SUXIAOMO_PROJECTS_DIR") or (DATA_ROOT / "projects"))
# schema 建表 SQL：运行时落在「数据根/data/schema」，首启若缺失则从应用包内复制。
# 应用包内源位置可由 SUXIAOMO_SCHEMA_DIR 覆盖（开发态=backend/bundled/schema，
# 打包态=resources/backend/bundled/schema），未设置时回退到 BASE_DIR/backend/bundled/schema。
CANONICAL_SCHEMA_DIR = Path(os.environ.get("SUXIAOMO_SCHEMA_DIR") or (BASE_DIR / "backend" / "bundled" / "schema"))
SCHEMA_DIR = DATA_ROOT / "data" / "schema"
# seed 种子 JSON：运行时落在「数据根/data/seed」，首启若缺失则从应用包内复制。
# 应用包内源位置可由 SUXIAOMO_SEED_DIR 覆盖（开发态=backend/bundled/seed，
# 打包态=resources/backend/bundled/seed），未设置时回退到 BASE_DIR/backend/bundled/seed。
CANONICAL_SEED_DIR = Path(os.environ.get("SUXIAOMO_SEED_DIR") or (BASE_DIR / "backend" / "bundled" / "seed"))
SEED_DIR = DATA_ROOT / "data" / "seed"

# 旧版数据位置（仅用于一次性迁移，日常不再使用）。可用 SUXIAOMO_LEGACY_DIR 覆盖，
# 以便打包态也能找到开发版旧数据（开发版默认 = 项目根）。
LEGACY_ROOT = Path(os.environ.get("SUXIAOMO_LEGACY_DIR") or (BASE_DIR.parent))
LEGACY_DATA_DIR = LEGACY_ROOT / "data"
LEGACY_PROJECTS_DIR = LEGACY_ROOT / "projects"


def _migrate_legacy_to_root():
    """首次迁移：若数据根内尚无 app.db，但旧位置存在真实数据，则复制进数据根。
    幂等：数据根已有 app.db 或旧位置无数据则直接跳过；复制不删旧文件。"""
    if DB_PATH.exists():
        return
    legacy_db = LEGACY_DATA_DIR / "app.db"
    if not legacy_db.exists() and not LEGACY_PROJECTS_DIR.exists():
        return  # 纯新用户，无旧数据可迁
    try:
        # 1) 数据库文件
        if legacy_db.exists():
            shutil.copy2(legacy_db, DB_PATH)
        # 2) 旧 data\ 下除 app.db 与 schema 外的所有内容 → DATA_DIR
        if LEGACY_DATA_DIR.exists():
            for name in os.listdir(LEGACY_DATA_DIR):
                if name in ("app.db", "schema"):
                    continue
                s = LEGACY_DATA_DIR / name
                d = DATA_DIR / name
                if s.is_dir():
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
        # 3) 旧 projects\ → PROJECTS_DIR
        if LEGACY_PROJECTS_DIR.exists():
            for name in os.listdir(LEGACY_PROJECTS_DIR):
                s = LEGACY_PROJECTS_DIR / name
                d = PROJECTS_DIR / name
                if s.is_dir():
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
        print(f"[db] 已将旧数据迁移至统一数据根: {DATA_ROOT}", file=sys.stderr)
    except Exception as e:
        print(f"[db] 旧数据迁移失败（不影响新建）: {e}", file=sys.stderr)


def _ensure_data_root():
    """确保统一数据根存在（首启创建）并执行一次性旧数据迁移。"""
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    _migrate_legacy_to_root()


def get_conn():
    """返回一个连到「统一数据根/app.db」的 sqlite3 连接（Row 工厂，按列名取数）"""
    _ensure_data_root()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn, name):
    """表是否存在（用于防御空库时跳过迁移）"""
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def _migrate():
    """一次性迁移：给已存在的表补缺失字段（幂等，靠 PRAGMA 检查，不删不改旧数据）
    - model_config：思考模式 / token 相关列
    - novel_function：每功能思考开关 thinking_enabled
    """
    conn = get_conn()
    try:
        # model_config
        if not _table_exists(conn, "model_config"):
            return  # schema 文件会负责建表，迁移无需执行
        # 放宽 name 唯一约束：同名模型允许并存（id 才是真实主键），避免新增第二条配置时
        # 因 name 撞库被 UNIQUE 拦截，导致「AI 助手下拉只显示一条模型」的假象。
        # 注意：SQLite 禁止 DROP 由 UNIQUE 隐式创建的索引，故用「改名→按 PRAGMA 动态重建
        # 不带 UNIQUE 的新表→搬数据→删旧表」的方式，既去掉约束又不动任何数据。幂等。
        try:
            has_name_unique = False
            for ix in conn.execute("PRAGMA index_list(model_config)").fetchall():
                if (ix["origin"] == "u" or ix["unique"]) and not ix["partial"]:
                    cols = [r["name"] for r in conn.execute(
                        f"PRAGMA index_info({ix['name']})").fetchall()]
                    if cols == ["name"]:
                        has_name_unique = True
                        break
            if has_name_unique:
                cols_info = conn.execute("PRAGMA table_info(model_config)").fetchall()
                col_defs, col_names = [], []
                for c in cols_info:
                    n = c["name"]
                    col_names.append(n)
                    p = [n, (c["type"] or "TEXT")]
                    if c["pk"]:
                        p.append("PRIMARY KEY")
                        if n == "id":
                            p.append("AUTOINCREMENT")
                    elif c["notnull"]:
                        p.append("NOT NULL")
                    if c["dflt_value"] is not None:
                        # PRAGMA table_info 会把 DEFAULT (datetime('now')) 的括号丢掉，
                        # 直接拼回 DEFAULT datetime('now') 会报 "near '(': syntax error"。
                        # SQLite 要求表达式默认值必须带括号；统一包成 DEFAULT (...) 即可兼容字面量/函数。
                        p.append("DEFAULT (" + c["dflt_value"] + ")")
                    col_defs.append(" ".join(p))
                conn.execute("DROP TABLE IF EXISTS model_config_old")
                conn.execute("ALTER TABLE model_config RENAME TO model_config_old")
                conn.execute("CREATE TABLE model_config (" + ", ".join(col_defs) + ")")
                conn.execute(
                    f"INSERT INTO model_config ({', '.join(col_names)}) "
                    f"SELECT {', '.join(col_names)} FROM model_config_old"
                )
                conn.execute("DROP TABLE model_config_old")
        except Exception as e:
            print(f"[db] 放宽 model_config.name 唯一约束失败（可忽略）: {e}", file=sys.stderr)
            try:
                conn.rollback()
            except Exception:
                pass
        existing = {r[1] for r in conn.execute(
            "PRAGMA table_info(model_config)").fetchall()}
        wanted = {
            "thinking_enabled": "INTEGER NOT NULL DEFAULT 1",
            "reasoning_effort": "TEXT NOT NULL DEFAULT 'medium'",
            "max_tokens": "INTEGER NOT NULL DEFAULT 2048",
            "supports_vision": "INTEGER NOT NULL DEFAULT 0",
            "supports_files": "INTEGER NOT NULL DEFAULT 0",
            "sort_order": "INTEGER NOT NULL DEFAULT 0",
            "reasoning_format": "TEXT NOT NULL DEFAULT 'thinking_block'",
            "provider_key": "TEXT",
            "model_profile_id": "INTEGER",
            "mode": "TEXT",
            "key_vault_id": "INTEGER",
            "secret_key": "TEXT",
        }
        for col, ddl in wanted.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE model_config ADD COLUMN {col} {ddl}")
        # model_profile：强制对齐内置模型能力（视觉/文件）模板，修复早期错误种子
        # 模型档案为只读模板（前端不可编辑），此处幂等强制对齐，保证现有库也随之修正
        if _table_exists(conn, "model_profile"):
            _PROFILE_CAPS = [
                # (provider_key, model_key, supports_vision, supports_files)
                ("deepseek", "v4-pro", 0, 1),
                ("deepseek", "v4-flash", 0, 1),
                ("kimi", "k3", 1, 1),
                ("kimi", "k2.6", 1, 1),
                ("kimi", "k2.7-code", 0, 1),
            ]
            for pk, mk, vis, files in _PROFILE_CAPS:
                conn.execute(
                    "UPDATE model_profile SET supports_vision=?, supports_files=? "
                    "WHERE provider_key=? AND model_key=?",
                    (vis, files, pk, mk),
                )
        # 媒体生成能力：生图/生视频（Flux Art）需要 capability / param_schema 两列。
        # 老库 model_profile 可能没有这两列（CREATE TABLE IF NOT EXISTS 对已有表不补列），
        # 这里幂等 ALTER；随后把 flux_art 四条档案的能力从默认 chat 改成 image/video。
        if _table_exists(conn, "model_profile"):
            pcols = {r[1] for r in conn.execute(
                "PRAGMA table_info(model_profile)").fetchall()}
            if "capability" not in pcols:
                conn.execute(
                    "ALTER TABLE model_profile ADD COLUMN capability TEXT NOT NULL DEFAULT 'chat'")
            if "param_schema" not in pcols:
                conn.execute(
                    "ALTER TABLE model_profile ADD COLUMN param_schema TEXT")
            # 种子 Flux Art 厂商与代表模型（每次启动幂等补种，兼容「runtime schema 副本已存在、
            # bundled 改动未被同步」的情况；INSERT OR IGNORE 保证只插一次）
            conn.execute(
                "INSERT OR IGNORE INTO model_provider "
                "(key, name, base_url, api_key_required, sort_order) "
                "VALUES('flux_art', 'Flux Art', 'https://open-api.flux-art.ai', 1, 70)"
            )
            _IMAGE_SCHEMA = ('{"aspect_ratio":{"type":"enum","options":["1:1","16:9","9:16","4:3","3:4"],"default":"1:1"},'
                             '"mode":{"type":"enum","options":["generate","edit"],"default":"generate"}}')
            _VIDEO_SCHEMA = ('{"video_mode":{"type":"enum","options":["t2v","i2v_first","multimodal_ref","v2v_edit"],"default":"t2v"},'
                             '"duration":{"type":"int","default":5},'
                             '"resolution":{"type":"enum","options":["480p","720p","1080p"],"default":"720p"},'
                             '"ratio":{"type":"enum","options":["16:9","9:16"],"default":"16:9"}}')
            _FLUX_SEED = [
                # 生图模型
                ("flux_art", "gpt-image-2", "GPT Image 2", "gpt-image-2",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', "image", _IMAGE_SCHEMA),
                ("flux_art", "grok-imagine", "Grok Imagine", "grok-imagine-image",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', "image", _IMAGE_SCHEMA),
                ("flux_art", "grok-imagine-pro", "Grok Imagine Pro", "grok-imagine-image-pro",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', "image", _IMAGE_SCHEMA),
                ("flux_art", "mj-imagine", "Midjourney Imagine", "mj_imagine",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', "image", _IMAGE_SCHEMA),
                ("flux_art", "mj-blend", "Midjourney Blend", "mj_blend",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', "image", _IMAGE_SCHEMA),
                ("flux_art", "seedream-4-5", "Seedream 4.5", "doubao-seedream-4-5-251128",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', "image", _IMAGE_SCHEMA),
                ("flux_art", "seedream-5-0", "Seedream 5.0", "doubao-seedream-5-0-260128",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', "image", _IMAGE_SCHEMA),
                ("flux_art", "seedream-5-0-pro", "Seedream 5.0 Pro", "doubao-seedream-5-0-pro-260628",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', "image", _IMAGE_SCHEMA),
                ("flux_art", "gemini-2-5-flash-image", "Gemini 2.5 Flash Image", "gemini-2.5-flash-image",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', "image", _IMAGE_SCHEMA),
                ("flux_art", "gemini-3-pro-image", "Gemini 3 Pro Image", "gemini-3-pro-image-preview",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', "image", _IMAGE_SCHEMA),
                ("flux_art", "gemini-3-1-flash-image", "Gemini 3.1 Flash Image", "gemini-3.1-flash-image-preview",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', "image", _IMAGE_SCHEMA),
                ("flux_art", "gemini-3-1-flash-lite-image", "Gemini 3.1 Flash Lite Image", "gemini-3.1-flash-lite-image",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', "image", _IMAGE_SCHEMA),
                ("flux_art", "qwen-image-2-0", "通义万相 2.0", "qwen-image-2.0",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', "image", _IMAGE_SCHEMA),
                ("flux_art", "qwen-image-2-0-pro", "通义万相 2.0 Pro", "qwen-image-2.0-pro",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', "image", _IMAGE_SCHEMA),
                ("flux_art", "qwen-image-max", "通义万相 Max", "qwen-image-max",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', "image", _IMAGE_SCHEMA),
                ("flux_art", "kling-image-v1", "可灵图生图 V1", "kling-v1-image",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', "image", _IMAGE_SCHEMA),
                ("flux_art", "kling-image-v2", "可灵图生图 V2", "kling-v2-image",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', "image", _IMAGE_SCHEMA),
                ("flux_art", "kling-image-v2-1", "可灵图生图 V2.1", "kling-v2-1-image",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', "image", _IMAGE_SCHEMA),
                ("flux_art", "kling-image-v3", "可灵图生图 V3", "kling-v3-image",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', "image", _IMAGE_SCHEMA),
                ("flux_art", "kling-image-v3-omni", "可灵图生图 V3 Omni", "kling-v3-omni-image",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', "image", _IMAGE_SCHEMA),
                ("flux_art", "kling-image-o1", "可灵图生图 O1", "kling-image-o1",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', "image", _IMAGE_SCHEMA),
                ("flux_art", "wan-2-7-image", "Wan 2.7 图像", "wan2.7-image",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', "image", _IMAGE_SCHEMA),
                ("flux_art", "wan-2-7-image-pro", "Wan 2.7 图像 Pro", "wan2.7-image-pro",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', "image", _IMAGE_SCHEMA),
                ("flux_art", "z-image-turbo", "Z Image Turbo", "z-image-turbo",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', "image", _IMAGE_SCHEMA),
                # 生视频模型
                ("flux_art", "seedance-1-0-pro", "Seedance 1.0 Pro", "doubao-seedance-1-0-pro-250528",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', "video", _VIDEO_SCHEMA),
                ("flux_art", "seedance-1-0-pro-fast", "Seedance 1.0 Pro Fast", "doubao-seedance-1-0-pro-fast-251015",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', "video", _VIDEO_SCHEMA),
                ("flux_art", "seedance-1-5-pro", "Seedance 1.5 Pro", "doubao-seedance-1-5-pro-251215",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', "video", _VIDEO_SCHEMA),
                ("flux_art", "seedance-2-0", "Seedance 2.0", "doubao-seedance-2-0-260128",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', "video", _VIDEO_SCHEMA),
                ("flux_art", "seedance-2-0-fast", "Seedance 2.0 Fast", "doubao-seedance-2-0-fast-260128",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', "video", _VIDEO_SCHEMA),
                ("flux_art", "seedance-2-0-mini", "Seedance 2.0 Mini", "doubao-seedance-2-0-mini-260615",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', "video", _VIDEO_SCHEMA),
                ("flux_art", "grok-video-3", "Grok Video 3", "grok-video-3",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', "video", _VIDEO_SCHEMA),
                ("flux_art", "kling-video-v1", "可灵视频 V1", "kling-v1",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', "video", _VIDEO_SCHEMA),
                ("flux_art", "kling-video-v1-5", "可灵视频 V1.5", "kling-v1-5",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', "video", _VIDEO_SCHEMA),
                ("flux_art", "kling-video-v2-1", "可灵视频 V2.1", "kling-v2-1",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', "video", _VIDEO_SCHEMA),
                ("flux_art", "kling-video-v2-1-master", "可灵视频 V2.1 Master", "kling-v2-1-master",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', "video", _VIDEO_SCHEMA),
                ("flux_art", "kling-video-v2-6", "可灵视频 V2.6", "kling-v2-6",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', "video", _VIDEO_SCHEMA),
                ("flux_art", "kling-video-v3", "可灵视频 V3", "kling-v3",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', "video", _VIDEO_SCHEMA),
                ("flux_art", "kling-video-v3-omni", "可灵视频 V3 Omni", "kling-v3-omni",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', "video", _VIDEO_SCHEMA),
                ("flux_art", "kling-video-o1", "可灵视频 O1", "kling-video-o1",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', "video", _VIDEO_SCHEMA),
                ("flux_art", "happyhorse-1-1", "HappyHorse 1.1", "happyhorse-1.1",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', "video", _VIDEO_SCHEMA),
            ]
            for fpk, fmk, dn, mn, modes, cap, schema in _FLUX_SEED:
                conn.execute(
                    "INSERT OR IGNORE INTO model_profile "
                    "(provider_key, model_key, display_name, model_name, modes, default_mode, "
                    "supports_vision, supports_files, temperature, temperature_locked, max_tokens, "
                    "reasoning_format, effort_mapping, max_tokens_field, notes, sort_order) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (fpk, fmk, dn, mn, modes, "fast", 0, 0, 0.7, 0, 2048,
                     "thinking_block", "{}", "max_tokens", None, 10),
                )
            _FLUX_CAPS = [
                # 生图
                ("flux_art", "gpt-image-2", "image", _IMAGE_SCHEMA),
                ("flux_art", "grok-imagine", "image", _IMAGE_SCHEMA),
                ("flux_art", "grok-imagine-pro", "image", _IMAGE_SCHEMA),
                ("flux_art", "mj-imagine", "image", _IMAGE_SCHEMA),
                ("flux_art", "mj-blend", "image", _IMAGE_SCHEMA),
                ("flux_art", "seedream-4-5", "image", _IMAGE_SCHEMA),
                ("flux_art", "seedream-5-0", "image", _IMAGE_SCHEMA),
                ("flux_art", "seedream-5-0-pro", "image", _IMAGE_SCHEMA),
                ("flux_art", "gemini-2-5-flash-image", "image", _IMAGE_SCHEMA),
                ("flux_art", "gemini-3-pro-image", "image", _IMAGE_SCHEMA),
                ("flux_art", "gemini-3-1-flash-image", "image", _IMAGE_SCHEMA),
                ("flux_art", "gemini-3-1-flash-lite-image", "image", _IMAGE_SCHEMA),
                ("flux_art", "qwen-image-2-0", "image", _IMAGE_SCHEMA),
                ("flux_art", "qwen-image-2-0-pro", "image", _IMAGE_SCHEMA),
                ("flux_art", "qwen-image-max", "image", _IMAGE_SCHEMA),
                ("flux_art", "kling-image-v1", "image", _IMAGE_SCHEMA),
                ("flux_art", "kling-image-v2", "image", _IMAGE_SCHEMA),
                ("flux_art", "kling-image-v2-1", "image", _IMAGE_SCHEMA),
                ("flux_art", "kling-image-v3", "image", _IMAGE_SCHEMA),
                ("flux_art", "kling-image-v3-omni", "image", _IMAGE_SCHEMA),
                ("flux_art", "kling-image-o1", "image", _IMAGE_SCHEMA),
                ("flux_art", "wan-2-7-image", "image", _IMAGE_SCHEMA),
                ("flux_art", "wan-2-7-image-pro", "image", _IMAGE_SCHEMA),
                ("flux_art", "z-image-turbo", "image", _IMAGE_SCHEMA),
                # 生视频
                ("flux_art", "seedance-1-0-pro", "video", _VIDEO_SCHEMA),
                ("flux_art", "seedance-1-0-pro-fast", "video", _VIDEO_SCHEMA),
                ("flux_art", "seedance-1-5-pro", "video", _VIDEO_SCHEMA),
                ("flux_art", "seedance-2-0", "video", _VIDEO_SCHEMA),
                ("flux_art", "seedance-2-0-fast", "video", _VIDEO_SCHEMA),
                ("flux_art", "seedance-2-0-mini", "video", _VIDEO_SCHEMA),
                ("flux_art", "grok-video-3", "video", _VIDEO_SCHEMA),
                ("flux_art", "kling-video-v1", "video", _VIDEO_SCHEMA),
                ("flux_art", "kling-video-v1-5", "video", _VIDEO_SCHEMA),
                ("flux_art", "kling-video-v2-1", "video", _VIDEO_SCHEMA),
                ("flux_art", "kling-video-v2-1-master", "video", _VIDEO_SCHEMA),
                ("flux_art", "kling-video-v2-6", "video", _VIDEO_SCHEMA),
                ("flux_art", "kling-video-v3", "video", _VIDEO_SCHEMA),
                ("flux_art", "kling-video-v3-omni", "video", _VIDEO_SCHEMA),
                ("flux_art", "kling-video-o1", "video", _VIDEO_SCHEMA),
                ("flux_art", "happyhorse-1-1", "video", _VIDEO_SCHEMA),
            ]
            for fpk, fmk, cap, schema in _FLUX_CAPS:
                conn.execute(
                    "UPDATE model_profile SET capability=?, param_schema=? "
                    "WHERE provider_key=? AND model_key=? AND (capability IS NULL OR capability='chat')",
                    (cap, schema, fpk, fmk),
                )
        # 本轮新增 chat 厂商（豆包-Seed / 通义千问 / CodeQwen）：runtime schema 副本已存在、
        # bundled 改动不被同步，故在迁移里幂等补种（INSERT OR IGNORE 只插一次）
        if _table_exists(conn, "model_profile"):
            for _pk, _name, _url, _order in [
                ('doubao-seed', '豆包 Seed（火山方舟）', 'https://ark.cn-beijing.volces.com/api/v3', 80),
                ('qwen', '通义千问（百炼）', 'https://dashscope.aliyuncs.com/compatible-mode/v1', 90),
                ('codeqwen', '通义千问代码（百炼）', 'https://dashscope.aliyuncs.com/compatible-mode/v1', 100),
            ]:
                conn.execute(
                    "INSERT OR IGNORE INTO model_provider "
                    "(key, name, base_url, api_key_required, sort_order) VALUES(?,?,?,1,?)",
                    (_pk, _name, _url, _order),
                )
            _NEW_PROFILE_SEED = [
                ("doubao-seed", "seed-1-6", "豆包 Seed 1.6", "doubao-seed-1-6-250615",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"适用于大部分情况"},{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"深度思考"}]',
                 "expert", 1, 1, 1.0, 0, 4096, "thinking_block", '{"low":"low","medium":"medium","high":"high"}', "max_tokens",
                 "豆包 Seed 1.6 支持思考/非思考；支持图片与文件输入。", 10),
                ("doubao-seed", "seed-1-6-flash", "豆包 Seed 1.6 Flash", "doubao-seed-1-6-flash-250828",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"轻量快速"},{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"深度推理"}]',
                 "fast", 1, 1, 1.0, 0, 4096, "thinking_block", '{"low":"low","medium":"medium","high":"high"}', "max_tokens",
                 "Seed 1.6 Flash 极速版；支持图片与文件输入。", 20),
                ("doubao-seed", "seed-1-6-thinking", "豆包 Seed 1.6 Thinking", "doubao-seed-1-6-thinking-250615",
                 '[{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"思考常开不可关"}]',
                 "expert", 1, 1, 1.0, 0, 4096, "thinking_block", '{"low":"low","medium":"medium","high":"high"}', "max_tokens",
                 "Seed 1.6 Thinking 思考加强版，仅专家模式。支持图片与文件输入。", 30),
                ("qwen", "plus", "通义千问 Plus", "qwen-plus",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"非思考模式"},{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"深度思考"}]',
                 "fast", 0, 0, 0.7, 0, 2000, "enable_thinking", "{}", "max_tokens",
                 "通义千问 Plus，混合思考（默认关）。enable_thinking 顶层布尔控制。", 10),
                ("qwen", "max", "通义千问 Max", "qwen-max",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"非思考模式"},{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"深度思考"}]',
                 "fast", 0, 0, 0.7, 0, 2000, "enable_thinking", "{}", "max_tokens",
                 "通义千问 Max，混合思考（默认关）。", 20),
                ("qwen", "turbo", "通义千问 Turbo", "qwen-turbo",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"非思考模式"},{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"深度思考"}]',
                 "fast", 0, 0, 0.7, 0, 2000, "enable_thinking", "{}", "max_tokens",
                 "通义千问 Turbo，低成本。", 30),
                ("qwen", "plus-thinking", "通义千问 Plus Thinking", "qwen-plus-thinking",
                 '[{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"思考专用，不可关"}]',
                 "expert", 0, 0, 0.7, 0, 4096, "enable_thinking", "{}", "max_tokens",
                 "通义千问 Plus Thinking 思考专用模型，强制开启思考。", 40),
                ("qwen", "vl-max", "通义千问 VL Max", "qwen-vl-max",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"非思考模式"},{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"深度思考"}]',
                 "fast", 1, 0, 0.7, 0, 2000, "enable_thinking", "{}", "max_tokens",
                 "通义千问 VL Max 视觉模型，支持图片输入与思考。", 50),
                ("codeqwen", "qwen3-coder", "Qwen3-Coder", "qwen3-coder",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"代码模型，非思考"}]',
                 "fast", 0, 0, 0.7, 0, 8192, "thinking_block", '{"low":"low","medium":"medium","high":"high"}', "max_tokens",
                 "通义千问代码模型 Qwen3-Coder，非思考代码生成。", 10),
                ("codeqwen", "qwen-coder-turbo", "Qwen-Coder-Turbo", "qwen-coder-turbo",
                 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"代码模型，非思考"}]',
                 "fast", 0, 0, 0.7, 0, 8192, "thinking_block", '{"low":"low","medium":"medium","high":"high"}', "max_tokens",
                 "通义千问代码模型 Turbo 版，低成本。", 20),
            ]
            for _pk, _mk, _dn, _mn, _modes, _dm, _vis, _files, _temp, _tlock, _mt, _rf, _emap, _mtf, _notes, _so in _NEW_PROFILE_SEED:
                conn.execute(
                    "INSERT OR IGNORE INTO model_profile "
                    "(provider_key, model_key, display_name, model_name, modes, default_mode, "
                    "supports_vision, supports_files, temperature, temperature_locked, max_tokens, "
                    "reasoning_format, effort_mapping, max_tokens_field, notes, sort_order) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (_pk, _mk, _dn, _mn, _modes, _dm, _vis, _files, _temp, _tlock, _mt, _rf, _emap, _mtf, _notes, _so),
                )
        # 旧 model_config 数据按 id 顺序补默认排序，避免全部挤在 0
        if "sort_order" in existing:
            has_zero = conn.execute(
                "SELECT 1 FROM model_config WHERE sort_order = 0 LIMIT 1").fetchone()
            if has_zero:
                for idx, row in enumerate(conn.execute(
                    "SELECT id FROM model_config ORDER BY id ASC").fetchall()):
                    conn.execute(
                        "UPDATE model_config SET sort_order = ? WHERE id = ?",
                        ((idx + 1) * 10, row["id"]))
        # 规范化旧 strength 值：max -> high；其他非法值 -> medium
        conn.execute(
            "UPDATE model_config SET reasoning_effort = 'high' WHERE reasoning_effort = 'max'"
        )
        conn.execute(
            "UPDATE model_config SET reasoning_effort = 'medium' WHERE reasoning_effort NOT IN ('low', 'medium', 'high')"
        )
        # 超时默认统一为 300 秒（2026-08-19）：把旧默认 60 的模型配置批量改为 300
        conn.execute("UPDATE model_config SET timeout_sec = 300 WHERE timeout_sec = 60")
        # novel_function
        if not _table_exists(conn, "novel_function"):
            conn.commit()
            return
        fexist = {r[1] for r in conn.execute(
            "PRAGMA table_info(novel_function)").fetchall()}
        if "thinking_enabled" not in fexist:
            conn.execute(
                "ALTER TABLE novel_function ADD COLUMN thinking_enabled INTEGER NOT NULL DEFAULT 1")
        # 按功能选模型（NULL=跟随全局启用那条）
        if "model_config_id" not in fexist:
            conn.execute(
                "ALTER TABLE novel_function ADD COLUMN model_config_id INTEGER")
        # 按功能推理强度（low/medium/high，仅思考开启时生效；NULL 不该出现，NOT NULL DEFAULT 'medium'）
        if "reasoning_effort" not in fexist:
            conn.execute(
                "ALTER TABLE novel_function ADD COLUMN reasoning_effort TEXT NOT NULL DEFAULT 'medium'")
        # novel_prompt_config：块级模型 + 块级思考（NULL=跟随功能级）
        if not _table_exists(conn, "novel_prompt_config"):
            conn.commit()
            return
        pexist = {r[1] for r in conn.execute(
            "PRAGMA table_info(novel_prompt_config)").fetchall()}
        if "model_config_id" not in pexist:
            conn.execute(
                "ALTER TABLE novel_prompt_config ADD COLUMN model_config_id INTEGER")
        if "thinking_enabled" not in pexist:
            conn.execute(
                "ALTER TABLE novel_prompt_config ADD COLUMN thinking_enabled INTEGER")
        # 块级推理强度（NULL=跟随功能级）
        if "reasoning_effort" not in pexist:
            conn.execute(
                "ALTER TABLE novel_prompt_config ADD COLUMN reasoning_effort TEXT")
        # filespace_roots：拖拽排序字段
        if not _table_exists(conn, "filespace_roots"):
            conn.commit()
            return
        fsexist = {r[1] for r in conn.execute(
            "PRAGMA table_info(filespace_roots)").fetchall()}
        if "sort_order" not in fsexist:
            conn.execute(
                "ALTER TABLE filespace_roots ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")
            # 旧数据按 id 顺序补一个默认排序，避免全部挤在 0
            for idx, row in enumerate(conn.execute(
                "SELECT id FROM filespace_roots ORDER BY id ASC").fetchall()):
                conn.execute(
                    "UPDATE filespace_roots SET sort_order = ? WHERE id = ?",
                    ((idx + 1) * 10, row["id"]))
        if "category" not in fsexist:
            conn.execute(
                "ALTER TABLE filespace_roots ADD COLUMN category TEXT NOT NULL DEFAULT '未分类'")
        if "cover_path" not in fsexist:
            conn.execute(
                "ALTER TABLE filespace_roots ADD COLUMN cover_path TEXT")
        if "pinned_tags" not in fsexist:
            conn.execute(
                "ALTER TABLE filespace_roots ADD COLUMN pinned_tags TEXT")
        # app_launchers：图标路径字段
        if not _table_exists(conn, "app_launchers"):
            conn.commit()
            return
        aexist = {r[1] for r in conn.execute(
            "PRAGMA table_info(app_launchers)").fetchall()}
        if "icon_path" not in aexist:
            conn.execute(
                "ALTER TABLE app_launchers ADD COLUMN icon_path TEXT")
        # app_launchers：web 服务型应用的状态检测端口（如 TTS/ComfyUI 的 webui 端口）
        if "detect_port" not in aexist:
            conn.execute(
                "ALTER TABLE app_launchers ADD COLUMN detect_port INTEGER")
        # novel_tweet_platform：各发布账号独立字段（名称/ID/作品链接/收益/备注）
        if _table_exists(conn, "novel_tweet_platform"):
            ntpexist = {r[1] for r in conn.execute(
                "PRAGMA table_info(novel_tweet_platform)").fetchall()}
            ntp_new_cols = {
                "douyin_link": "TEXT NOT NULL DEFAULT ''",
                "douyin_earnings": "TEXT NOT NULL DEFAULT ''",
                "douyin_remark": "TEXT NOT NULL DEFAULT ''",
                "bilibili_link": "TEXT NOT NULL DEFAULT ''",
                "bilibili_earnings": "TEXT NOT NULL DEFAULT ''",
                "bilibili_remark": "TEXT NOT NULL DEFAULT ''",
                "kuaishou_link": "TEXT NOT NULL DEFAULT ''",
                "kuaishou_earnings": "TEXT NOT NULL DEFAULT ''",
                "kuaishou_remark": "TEXT NOT NULL DEFAULT ''",
                "other_name": "TEXT NOT NULL DEFAULT ''",
                "other_id": "TEXT NOT NULL DEFAULT ''",
                "other_link": "TEXT NOT NULL DEFAULT ''",
                "other_earnings": "TEXT NOT NULL DEFAULT ''",
                "other_remark": "TEXT NOT NULL DEFAULT ''",
                "shipinhao_name": "TEXT NOT NULL DEFAULT ''",
                "shipinhao_id": "TEXT NOT NULL DEFAULT ''",
                "shipinhao_link": "TEXT NOT NULL DEFAULT ''",
                "shipinhao_earnings": "TEXT NOT NULL DEFAULT ''",
                "shipinhao_remark": "TEXT NOT NULL DEFAULT ''",
                "publish_date": "TEXT NOT NULL DEFAULT ''",
                "douyin_publish_date": "TEXT NOT NULL DEFAULT ''",
                "bilibili_publish_date": "TEXT NOT NULL DEFAULT ''",
                "kuaishou_publish_date": "TEXT NOT NULL DEFAULT ''",
                "other_publish_date": "TEXT NOT NULL DEFAULT ''",
                "shipinhao_publish_date": "TEXT NOT NULL DEFAULT ''",
                "douyin_is_published_backfill": "INTEGER NOT NULL DEFAULT 0",
                "bilibili_is_published_backfill": "INTEGER NOT NULL DEFAULT 0",
                "kuaishou_is_published_backfill": "INTEGER NOT NULL DEFAULT 0",
                "other_is_published_backfill": "INTEGER NOT NULL DEFAULT 0",
                "shipinhao_is_published_backfill": "INTEGER NOT NULL DEFAULT 0",
            }
            for col, ddl in ntp_new_cols.items():
                if col not in ntpexist:
                    conn.execute(f"ALTER TABLE novel_tweet_platform ADD COLUMN {col} {ddl}")
        # prompt_library：生图模版图路径数组（JSON 字符串）
        if _table_exists(conn, "prompt_library"):
            plexist = {r[1] for r in conn.execute(
                "PRAGMA table_info(prompt_library)").fetchall()}
            if "images" not in plexist:
                conn.execute(
                    "ALTER TABLE prompt_library ADD COLUMN images TEXT NOT NULL DEFAULT '[]'")
            # 单一分类字段：从旧的 category_1 迁移，后续 UI 不再区分一级/二级
            if "category" not in plexist:
                conn.execute(
                    "ALTER TABLE prompt_library ADD COLUMN category TEXT NOT NULL DEFAULT '其他'")
                conn.execute(
                    "UPDATE prompt_library SET category = category_1 WHERE category_1 IS NOT NULL AND category_1 <> ''")
            # 卡片拖拽排序字段
            if "sort_order" not in plexist:
                conn.execute(
                    "ALTER TABLE prompt_library ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")
                # 旧数据按 id 顺序补默认排序，避免全部挤在 0
                for idx, row in enumerate(conn.execute(
                        "SELECT id FROM prompt_library ORDER BY id ASC").fetchall()):
                    conn.execute(
                        "UPDATE prompt_library SET sort_order = ? WHERE id = ?",
                        ((idx + 1) * 10, row["id"]))
            # 归属 scope：prompt(漫剧相关纯文本) / instruction(skills + 非漫剧大类提示词)
            if "scope" not in plexist:
                conn.execute(
                    "ALTER TABLE prompt_library ADD COLUMN scope TEXT NOT NULL DEFAULT 'prompt'")
                # 旧 skills 记录统一归类为「指令」，使其在提示词库页(只看 prompt)不再出现
                conn.execute(
                    "UPDATE prompt_library SET scope='instruction' WHERE category='skills'")
            # owner_name 展示归属（纯展示，不参与匹配）；新增列默认 '苏小沫'
            if "owner_name" not in plexist:
                conn.execute(
                    "ALTER TABLE prompt_library ADD COLUMN owner_name TEXT NOT NULL DEFAULT '苏小沫'")
            # uid 稳定唯一键：命名空间序号（owner_id-seq，如 OEM-7F3A-0001），导入导出精确匹配。
            # - 仅作者环境（suxiaomo-studio-dev / suxiaomo-studio-workspace）把旧随机 uuid（无 '-'）
            #   重编为 OEM-7F3A-NNNN，保证出厂库 uid 稳定、可再分发、v2 重导能跳过、不重复新增。
            # - 已是 前缀-数字 的（导入得到的 / 已重编的）保持不动；绝不改动其它字段。
            # - 接收方环境不重编（其库无随机 uuid 或已带各自前缀），避免与导入得到的 OEM 行撞号。
            if "uid" not in plexist:
                conn.execute("ALTER TABLE prompt_library ADD COLUMN uid TEXT")
            _dp = str(DATA_DIR).replace("\\", "/")
            if ("suxiaomo-studio-dev" in _dp) or ("suxiaomo-studio-workspace" in _dp):
                try:
                    idx = 0
                    for r in conn.execute(
                            "SELECT id, uid FROM prompt_library ORDER BY id ASC").fetchall():
                        u = r["uid"] or ""
                        if "-" not in u:
                            idx += 1
                            conn.execute(
                                "UPDATE prompt_library SET uid = ? WHERE id = ?",
                                (f"OEM-7F3A-{idx:04d}", r["id"]))
                except Exception as e:
                    print(f"[db] 重编 prompt_library.uid 失败（可忽略）: {e}", file=sys.stderr)
            # app_kv：每安装实例独立的键值存储（存 owner_id / owner_name）
            if not _table_exists(conn, "app_kv"):
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS app_kv (k TEXT PRIMARY KEY, v TEXT)")
            conn.commit()
        # key_vault：移除 UI 已弃用的 6 个字段（与前端表单/列表对齐）
        if _table_exists(conn, "key_vault"):
            kvexist = {r[1] for r in conn.execute(
                "PRAGMA table_info(key_vault)").fetchall()}
            drop_cols = ["doc_url", "quota", "expire_at", "status", "tags", "note"]
            for col in drop_cols:
                if col in kvexist:
                    try:
                        conn.execute(f"ALTER TABLE key_vault DROP COLUMN {col}")
                        print(f"[db] 已删除 key_vault.{col}", file=sys.stderr)
                    except Exception as e:
                        print(f"[db] 删除 key_vault.{col} 失败（可忽略）: {e}", file=sys.stderr)

        # app_releases：发布版本记录表。CREATE TABLE IF NOT EXISTS 幂等，作为 schema 增量同步的兜底，
        # 防止某些情况下 init_db() 的 schema SQL 未覆盖到本表时漏建（不影响已有库）。
        if not _table_exists(conn, "app_releases"):
            conn.execute(
                "CREATE TABLE IF NOT EXISTS app_releases ("
                " id INTEGER PRIMARY KEY AUTOINCREMENT,"
                " version TEXT NOT NULL,"
                " release_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),"
                " features_json TEXT NOT NULL DEFAULT '[]',"
                " path TEXT,"
                " created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))"
                ")"
            )
        # viral_collection：个人主页字段 + 小说标签字段（新增，幂等 ALTER）
        if not _table_exists(conn, "viral_collection"):
            conn.commit()
            return
        vexist = {r[1] for r in conn.execute(
            "PRAGMA table_info(viral_collection)").fetchall()}
        v_new_cols = {
            "following": "TEXT NOT NULL DEFAULT ''",
            "followers": "TEXT NOT NULL DEFAULT ''",
            "works_count": "TEXT NOT NULL DEFAULT ''",
            "bio": "TEXT NOT NULL DEFAULT ''",
            "homepage_link": "TEXT NOT NULL DEFAULT ''",
            "novel_tags": "TEXT NOT NULL DEFAULT ''",
            "comment_count": "TEXT NOT NULL DEFAULT ''",
            "share_count": "TEXT NOT NULL DEFAULT ''",
        }
        for col, ddl in v_new_cols.items():
            if col not in vexist:
                conn.execute(f"ALTER TABLE viral_collection ADD COLUMN {col} {ddl}")
        conn.commit()

        # manju_sites：is_default 标记（区分系统默认 / 用户自建，幂等 ALTER）
        if not _table_exists(conn, "manju_sites"):
            conn.commit()
            return
        mexist = {r[1] for r in conn.execute(
            "PRAGMA table_info(manju_sites)").fetchall()}
        if "is_default" not in mexist:
            conn.execute(
                "ALTER TABLE manju_sites ADD COLUMN is_default INTEGER NOT NULL DEFAULT 0")
            conn.commit()
    finally:
        conn.close()


def _ensure_runtime_schema():
    """确保运行时 schema 存在于数据根下：缺失则从应用包内复制（幂等）。
    若数据根已存在 schema 目录，则增量补拷应用包内新增的 *.sql（同名不覆盖，避免冲掉用户改动）。
    这样后续往 bundled/schema 新增建表 SQL，老数据根在下次启动时也能自动建表。"""
    if not SCHEMA_DIR.exists():
        if CANONICAL_SCHEMA_DIR.exists():
            shutil.copytree(CANONICAL_SCHEMA_DIR, SCHEMA_DIR)
            print(f"[db] 已将 schema 复制到数据根: {SCHEMA_DIR}", file=sys.stderr)
        return
    # 增量同步：仅补拷数据根下尚不存在的新建表 SQL
    if CANONICAL_SCHEMA_DIR.exists():
        for f in CANONICAL_SCHEMA_DIR.glob("*.sql"):
            dst = SCHEMA_DIR / f.name
            if not dst.exists():
                shutil.copy2(f, dst)
                print(f"[db] 已同步新增 schema: {f.name}", file=sys.stderr)


def _ensure_runtime_seed():
    """确保运行时 seed 存在于数据根下：缺失则从应用包内复制（幂等）。"""
    if not SEED_DIR.exists() and CANONICAL_SEED_DIR.exists():
        shutil.copytree(CANONICAL_SEED_DIR, SEED_DIR)
        print(f"[db] 已将 seed 复制到数据根: {SEED_DIR}", file=sys.stderr)



def init_db():
    """跑 schema 下所有 *.sql（只建不存在的表，幂等），再跑一次性迁移"""
    _ensure_data_root()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    _ensure_runtime_schema()
    _ensure_runtime_seed()
    conn = get_conn()
    try:
        for sql_file in sorted(SCHEMA_DIR.glob("*.sql")):
            conn.executescript(sql_file.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()
    _migrate()


def get_config(key, default=None):
    """读 config 表里某行的值；没有则返回 default"""
    conn = get_conn()
    try:
        row = conn.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default
    finally:
        conn.close()


def set_config(key, value, description=None):
    """写 config 表里某行（没有就插，有就更新值）"""
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO config(key, value, description) VALUES(?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value), description),
        )
        conn.commit()
    finally:
        conn.close()
