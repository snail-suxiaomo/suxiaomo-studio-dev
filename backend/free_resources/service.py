"""free_resources/service.py —— 免费资源（原羊毛）CRUD

与 web_nav（网址导航）平级、独立表。这里专收「免费生图 / 生视频站」类富工具卡：
含网址、平台、操作步骤、免费额度、相关提示词、截图。
截图真实文件落 data/free_resources_images/，库只存相对路径数组（JSON 字符串），沿用 prompt_library 的落盘 + 防穿越取流模式。
分类字段（category / tags）均为普通文本，支持「预设 + 用户自建」——前端用 datalist 给建议值，但允许自由输入新值，无需改表。
"""

import json
from pathlib import Path

from common import db

# 免费资源默认分类（前端筛选栏与 datalist 共用，用户也可自建新分类自动同步）
DEFAULT_CATS = ['生图', '生视频', '去水印', '剪辑', '配音', '其他']


def _conn():
    return db.get_conn()


# 截图：真实文件落 data/free_resources_images/，库只存相对路径数组（JSON 字符串）
IMAGES_DIR_NAME = 'free_resources_images'
ALLOWED_IMG_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}


def _images_dir():
    d = db.DATA_DIR / IMAGES_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def _parse_images(v):
    if isinstance(v, list):
        return v
    if not v:
        return []
    try:
        a = json.loads(v)
        return a if isinstance(a, list) else []
    except Exception:
        return []


def _dump_images(arr):
    return json.dumps(arr, ensure_ascii=False)


def list_items(category='全部', keyword=None, tag=None, status=None):
    sql = "SELECT * FROM free_resources WHERE 1=1"
    params = []
    if category and category != '全部':
        sql += " AND category=?"
        params.append(category)
    if status and status != '全部':
        sql += " AND status=?"
        params.append(status)
    if tag:
        sql += " AND tags LIKE ?"
        params.append(f'%{tag}%')
    if keyword:
        like = f'%{keyword}%'
        sql += (" AND (title LIKE ? OR url LIKE ? OR platform LIKE ? OR steps LIKE ? "
                "OR quota LIKE ? OR prompt_ref LIKE ? OR note LIKE ? OR tags LIKE ?)")
        params.extend([like, like, like, like, like, like, like, like])
    sql += " ORDER BY sort_order ASC, id ASC"
    conn = _conn()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_item(rid):
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM free_resources WHERE id=?", (rid,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_item(data):
    title = (data.get('title') or '').strip()
    if not title:
        raise ValueError('标题不能为空')
    url = (data.get('url') or '').strip() or None
    category = (data.get('category') or '其他').strip() or '其他'
    platform = (data.get('platform') or '').strip() or None
    steps = data.get('steps') or ''
    quota = data.get('quota') or ''
    prompt_ref = data.get('prompt_ref') or ''
    note = data.get('note') or ''
    tags = (data.get('tags') or '').strip()
    status = data.get('status') or 'available'
    region = (data.get('region') or '').strip() or None
    register_way = (data.get('register_way') or '').strip() or None
    need_vpn = (data.get('need_vpn') or '').strip() or None
    quality = (data.get('quality') or '').strip() or None
    support_model = (data.get('support_model') or '').strip() or None
    verified_at = (data.get('verified_at') or '').strip() or None
    rating = (data.get('rating') or '').strip() or None
    cost_15s_points = (data.get('cost_15s_points') or '').strip() or None
    cost_15s_amount = (data.get('cost_15s_amount') or '').strip() or None
    conn = _conn()
    try:
        # 新条目排到列表末尾
        cur = conn.execute("SELECT COALESCE(MAX(sort_order),0)+1 FROM free_resources")
        sort_order = cur.fetchone()[0]
        cur = conn.execute(
            "INSERT INTO free_resources(title, url, category, platform, steps, quota, prompt_ref, note, tags, status, "
            "region, register_way, need_vpn, quality, support_model, verified_at, rating, cost_15s_points, cost_15s_amount, "
            "sort_order, images) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (title, url, category, platform, steps, quota, prompt_ref, note, tags, status,
             region, register_way, need_vpn, quality, support_model, verified_at, rating, cost_15s_points, cost_15s_amount,
             sort_order, '[]'),
        )
        conn.commit()
        return get_item(cur.lastrowid)
    finally:
        conn.close()


def update_item(rid, data):
    existing = get_item(rid)
    if not existing:
        raise ValueError('记录不存在')
    title = (data.get('title') or '').strip()
    if not title:
        raise ValueError('标题不能为空')
    url = data['url'] if data.get('url') is not None else existing['url']
    category = (data.get('category') or existing['category']).strip() or '其他'
    platform = data['platform'] if data.get('platform') is not None else existing['platform']
    steps = data['steps'] if data.get('steps') is not None else existing['steps']
    quota = data['quota'] if data.get('quota') is not None else existing['quota']
    prompt_ref = data['prompt_ref'] if data.get('prompt_ref') is not None else existing['prompt_ref']
    note = data['note'] if data.get('note') is not None else existing['note']
    tags = (data.get('tags') or '').strip()
    status = data['status'] if data.get('status') is not None else existing.get('status', 'available')
    region = data['region'] if data.get('region') is not None else existing.get('region')
    register_way = data['register_way'] if data.get('register_way') is not None else existing.get('register_way')
    need_vpn = data['need_vpn'] if data.get('need_vpn') is not None else existing.get('need_vpn')
    quality = data['quality'] if data.get('quality') is not None else existing.get('quality')
    support_model = data['support_model'] if data.get('support_model') is not None else existing.get('support_model')
    verified_at = data['verified_at'] if data.get('verified_at') is not None else existing.get('verified_at')
    rating = data['rating'] if data.get('rating') is not None else existing.get('rating')
    cost_15s_points = data['cost_15s_points'] if data.get('cost_15s_points') is not None else existing.get('cost_15s_points')
    cost_15s_amount = data['cost_15s_amount'] if data.get('cost_15s_amount') is not None else existing.get('cost_15s_amount')
    conn = _conn()
    try:
        conn.execute(
            "UPDATE free_resources SET title=?, url=?, category=?, platform=?, steps=?, quota=?, prompt_ref=?, note=?, tags=?, "
            "status=?, region=?, register_way=?, need_vpn=?, quality=?, support_model=?, verified_at=?, rating=?, "
            "cost_15s_points=?, cost_15s_amount=?, updated_at=(datetime('now','localtime')) WHERE id=?",
            (title, url, category, platform, steps, quota, prompt_ref, note, tags,
             status, region, register_way, need_vpn, quality, support_model, verified_at, rating,
             cost_15s_points, cost_15s_amount, rid),
        )
        conn.commit()
        return get_item(rid)
    finally:
        conn.close()


def delete_item(rid):
    conn = _conn()
    try:
        conn.execute("DELETE FROM free_resources WHERE id=?", (rid,))
        conn.commit()
    finally:
        conn.close()


def add_images(rid, files):
    """files: list of {filename, content(bytes)}；保存到 data/free_resources_images/，追加到 images 数组。"""
    rec = get_item(rid)
    if not rec:
        raise ValueError('记录不存在')
    arr = _parse_images(rec.get('images'))
    d = _images_dir()
    for f in files:
        ext = Path(f.get('filename') or '').suffix.lower()
        if ext not in ALLOWED_IMG_EXT:
            raise ValueError(f'不支持的图片格式：{ext or "(无扩展名)"}')
        name = f"{rid}_{len(arr)}" + ext
        (d / name).write_bytes(f.get('content') or b'')
        arr.append(f"{IMAGES_DIR_NAME}/{name}")
    conn = _conn()
    try:
        conn.execute(
            "UPDATE free_resources SET images=?, updated_at=(datetime('now','localtime')) WHERE id=?",
            (_dump_images(arr), rid),
        )
        conn.commit()
        return get_item(rid)
    finally:
        conn.close()


def delete_image(rid, filename):
    """删除单张截图（从数组移除 + 删磁盘文件）。filename 为纯文件名（不含目录）。"""
    rec = get_item(rid)
    if not rec:
        raise ValueError('记录不存在')
    arr = _parse_images(rec.get('images'))
    rel = f"{IMAGES_DIR_NAME}/{filename}"
    if rel not in arr:
        raise ValueError('图片不存在')
    arr.remove(rel)
    fp = _images_dir() / filename
    if fp.exists():
        try:
            fp.unlink()
        except OSError:
            pass
    conn = _conn()
    try:
        conn.execute(
            "UPDATE free_resources SET images=?, updated_at=(datetime('now','localtime')) WHERE id=?",
            (_dump_images(arr), rid),
        )
        conn.commit()
        return get_item(rid)
    finally:
        conn.close()


def get_image_file(rel_path):
    """返回图片绝对路径，限制在 data/free_resources_images 内（防目录穿越）。"""
    p = (db.DATA_DIR / rel_path).resolve()
    base = _images_dir().resolve()
    if p != base and base not in p.parents:
        raise ValueError('非法路径')
    if not p.is_file():
        raise ValueError('图片不存在')
    return p


def meta():
    """返回已有的分类/标签；默认分类始终包含，用户自建分类自动追加。"""
    conn = _conn()
    try:
        cats = [r[0] for r in conn.execute(
            "SELECT DISTINCT category FROM free_resources WHERE category IS NOT NULL AND category<>'' "
            "ORDER BY category").fetchall()]
        # 默认分类 + 库内自建分类（去重保序）
        all_cats = list(DEFAULT_CATS)
        for c in cats:
            if c not in all_cats:
                all_cats.append(c)
        tags = set()
        for r in conn.execute(
                "SELECT DISTINCT tags FROM free_resources WHERE tags IS NOT NULL AND tags<>''").fetchall():
            for t in (r[0] or '').split(','):
                t = t.strip()
                if t:
                    tags.add(t)
        # 状态计数（全局总览，供前端统计条；只有 可用/已失效 两种）
        counts = {'available': 0, 'expired': 0}
        for st, c in conn.execute(
                "SELECT COALESCE(status,'available'), COUNT(*) FROM free_resources "
                "GROUP BY COALESCE(status,'available')").fetchall():
            # 历史 daily 状态已并入 available
            key = st if st in counts else 'available'
            counts[key] += c
        counts['total'] = counts['available'] + counts['expired']
        return {
            'categories': all_cats,
            'all_tags': sorted(tags),
            'counts': counts,
        }
    finally:
        conn.close()


def _ensure_columns():
    """启动时确保表存在并补齐新字段（兼容旧库 / 空库首次启动）。"""
    conn = _conn()
    try:
        # 空库首次启动时 schema 目录可能未提供建表 SQL，这里自包含建表，
        # 保证 import 阶段不再因「no such table」崩溃
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS free_resources (
              id           INTEGER PRIMARY KEY AUTOINCREMENT,
              title        TEXT    NOT NULL,
              url          TEXT,
              category     TEXT    NOT NULL DEFAULT '其他',
              platform     TEXT,
              steps        TEXT,
              quota        TEXT,
              prompt_ref   TEXT,
              note         TEXT,
              tags         TEXT    NOT NULL DEFAULT '',
              images       TEXT    NOT NULL DEFAULT '[]',
              created_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
              updated_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
              status TEXT DEFAULT 'available',
              region TEXT,
              register_way TEXT,
              need_vpn TEXT,
              support_model TEXT,
              verified_at TEXT,
              rating TEXT,
              cost_15s_points TEXT,
              cost_15s_amount TEXT,
              sort_order INTEGER DEFAULT 0,
              quality TEXT
            )
            """
        )
        cols = [r[1] for r in conn.execute("PRAGMA table_info(free_resources)").fetchall()]
        adds = {
            'status': "ALTER TABLE free_resources ADD COLUMN status TEXT DEFAULT 'available'",
            'region': "ALTER TABLE free_resources ADD COLUMN region TEXT",
            'register_way': "ALTER TABLE free_resources ADD COLUMN register_way TEXT",
            'need_vpn': "ALTER TABLE free_resources ADD COLUMN need_vpn TEXT",
            'quality': "ALTER TABLE free_resources ADD COLUMN quality TEXT",
            'support_model': "ALTER TABLE free_resources ADD COLUMN support_model TEXT",
            'verified_at': "ALTER TABLE free_resources ADD COLUMN verified_at TEXT",
            'rating': "ALTER TABLE free_resources ADD COLUMN rating TEXT",
            'cost_15s_points': "ALTER TABLE free_resources ADD COLUMN cost_15s_points TEXT",
            'cost_15s_amount': "ALTER TABLE free_resources ADD COLUMN cost_15s_amount TEXT",
            'sort_order': "ALTER TABLE free_resources ADD COLUMN sort_order INTEGER DEFAULT 0",
        }
        for col, ddl in adds.items():
            if col not in cols:
                conn.execute(ddl)
        # 旧数据补 sort_order，保持原 id 顺序（新数据在 create 时已置为末尾）
        conn.execute("UPDATE free_resources SET sort_order = id WHERE sort_order IS NULL")
        # 历史 daily 状态已弃用，并入 available
        conn.execute("UPDATE free_resources SET status='available' WHERE status='daily'")
        conn.commit()
    finally:
        conn.close()


def reorder(ids):
    """保存拖拽顺序：ids 为新的完整顺序（记录 id 列表）。"""
    conn = _conn()
    try:
        for i, rid in enumerate(ids):
            conn.execute("UPDATE free_resources SET sort_order=? WHERE id=?", (i, rid))
        conn.commit()
        return {'ok': True}
    finally:
        conn.close()


_ensure_columns()
