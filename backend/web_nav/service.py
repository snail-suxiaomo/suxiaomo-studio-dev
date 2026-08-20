"""web_nav/service.py —— 网址导航 CRUD

与 free_resources（免费资源）平级、独立表。这里专收「常用网站快捷链接」：
网址、分类、备注、标签、可选图标/截图。
真实图片文件落 data/web_nav_images/，库只存相对路径数组（JSON 字符串），沿用 prompt_library 的落盘 + 防穿越取流模式。
分类字段（category / tags）均为普通文本，支持「预设 + 用户自建」——前端用 datalist 给建议值，但允许自由输入新值，无需改表。
"""

import io
import json
import time
from pathlib import Path

from common import db
from PIL import Image


def _conn():
    return db.get_conn()


def _ensure_columns():
    """启动时检查并补齐表字段（兼容旧库）。"""
    conn = _conn()
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(web_nav)").fetchall()]
        if 'cover_image' not in cols:
            conn.execute("ALTER TABLE web_nav ADD COLUMN cover_image TEXT")
            conn.commit()
        if 'sort_order' not in cols:
            conn.execute("ALTER TABLE web_nav ADD COLUMN sort_order INTEGER")
            conn.commit()
    finally:
        conn.close()


# 图标/截图：真实文件落 data/web_nav_images/，库只存相对路径数组（JSON 字符串）
IMAGES_DIR_NAME = 'web_nav_images'
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


def list_items(category='全部', keyword=None, tag=None):
    sql = "SELECT * FROM web_nav WHERE 1=1"
    params = []
    if category and category != '全部':
        sql += " AND category=?"
        params.append(category)
    if tag:
        sql += " AND tags LIKE ?"
        params.append(f'%{tag}%')
    if keyword:
        like = f'%{keyword}%'
        sql += " AND (title LIKE ? OR url LIKE ? OR note LIKE ? OR tags LIKE ?)"
        params.extend([like, like, like, like])
    sql += " ORDER BY COALESCE(sort_order, 99999999), updated_at DESC, id DESC"
    conn = _conn()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_item(nid):
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM web_nav WHERE id=?", (nid,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_item(data):
    title = (data.get('title') or '').strip()
    if not title:
        raise ValueError('标题不能为空')
    url = (data.get('url') or '').strip() or None
    category = (data.get('category') or '其他').strip() or '其他'
    note = data.get('note') or ''
    tags = (data.get('tags') or '').strip()
    conn = _conn()
    try:
        cur = conn.execute(
            "INSERT INTO web_nav(title, url, category, note, tags, images) "
            "VALUES(?,?,?,?,?,?)",
            (title, url, category, note, tags, '[]'),
        )
        conn.commit()
        return get_item(cur.lastrowid)
    finally:
        conn.close()


def update_item(nid, data):
    existing = get_item(nid)
    if not existing:
        raise ValueError('记录不存在')
    title = (data.get('title') or '').strip()
    if not title:
        raise ValueError('标题不能为空')
    url = data['url'] if data.get('url') is not None else existing['url']
    category = (data.get('category') or existing['category']).strip() or '其他'
    note = data['note'] if data.get('note') is not None else existing['note']
    tags = (data.get('tags') or '').strip()
    cover_image = data.get('cover_image')
    if cover_image is None:
        cover_image = existing.get('cover_image')
    conn = _conn()
    try:
        conn.execute(
            "UPDATE web_nav SET title=?, url=?, category=?, note=?, tags=?, cover_image=?, "
            "updated_at=(datetime('now','localtime')) WHERE id=?",
            (title, url, category, note, tags, cover_image, nid),
        )
        conn.commit()
        return get_item(nid)
    finally:
        conn.close()


def delete_item(nid):
    rec = get_item(nid)
    conn = _conn()
    try:
        conn.execute("DELETE FROM web_nav WHERE id=?", (nid,))
        conn.commit()
    finally:
        conn.close()
    if rec:
        # 清理该记录关联的所有图片文件（images 数组 + 独立封面）
        d = _images_dir()
        for rel in _parse_images(rec.get('images')):
            try:
                fp = d / Path(rel).name
                if fp.exists():
                    fp.unlink()
            except OSError:
                pass
        cover = rec.get('cover_image')
        if cover:
            try:
                fp = d / Path(cover).name
                if fp.exists():
                    fp.unlink()
            except OSError:
                pass


def add_images(nid, files):
    """files: list of {filename, content(bytes)}；原样保存到 data/web_nav_images/，追加到 images 数组。

    普通截图不裁剪，保留完整内容供详情查看；仅封面图走 set_cover_crop() 做 16:9 裁剪。
    """
    rec = get_item(nid)
    if not rec:
        raise ValueError('记录不存在')
    arr = _parse_images(rec.get('images'))
    d = _images_dir()
    first_new = None
    for f in files:
        ext = Path(f.get('filename') or '').suffix.lower()
        if ext not in ALLOWED_IMG_EXT:
            raise ValueError(f'不支持的图片格式：{ext or "(无扩展名)"}')
        if not ext:
            ext = '.jpg'
        content = f.get('content') or b''
        name = f"{nid}_{len(arr)}{ext}"
        (d / name).write_bytes(content)
        rel = f"{IMAGES_DIR_NAME}/{name}"
        arr.append(rel)
        if first_new is None:
            first_new = rel
    conn = _conn()
    try:
        cover = rec.get('cover_image')
        if not cover and first_new:
            cover = first_new
        conn.execute(
            "UPDATE web_nav SET images=?, cover_image=?, updated_at=(datetime('now','localtime')) WHERE id=?",
            (_dump_images(arr), cover, nid),
        )
        conn.commit()
        return get_item(nid)
    finally:
        conn.close()


def delete_image(nid, filename):
    """删除单张图标/截图（从数组移除 + 删磁盘文件）。filename 为纯文件名（不含目录）。"""
    rec = get_item(nid)
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
        cover = rec.get('cover_image')
        if cover == rel:
            cover = arr[0] if arr else None
        conn.execute(
            "UPDATE web_nav SET images=?, cover_image=?, updated_at=(datetime('now','localtime')) WHERE id=?",
            (_dump_images(arr), cover, nid),
        )
        conn.commit()
        return get_item(nid)
    finally:
        conn.close()


def set_cover(nid, rel_path):
    """设置封面图：rel_path 必须是该记录 images 数组中的某一项，或空字符串/None 表示取消。"""
    rec = get_item(nid)
    if not rec:
        raise ValueError('记录不存在')
    arr = _parse_images(rec.get('images'))
    if rel_path and rel_path not in arr:
        raise ValueError('封面图不在当前图片列表中')
    conn = _conn()
    try:
        conn.execute(
            "UPDATE web_nav SET cover_image=?, updated_at=(datetime('now','localtime')) WHERE id=?",
            (rel_path or None, nid),
        )
        conn.commit()
        return get_item(nid)
    finally:
        conn.close()


def set_cover_crop(nid, content: bytes):
    """接收前端裁剪后的 16:9 图片 bytes，保存为 web_nav_images/{nid}_cover_{ts}.jpg 并设为封面。

    文件名带时间戳，避免浏览器因同名文件缓存而显示旧封面；旧封面文件会被清理。
    该封面文件不进入 images 数组，避免影响详情中完整图片的查看；删除记录时同步清理。
    """
    rec = get_item(nid)
    if not rec:
        raise ValueError('记录不存在')
    d = _images_dir()
    # 统一转 JPEG
    img = Image.open(io.BytesIO(content))
    img = img.convert('RGB')
    name = f"{nid}_cover_{int(time.time())}.jpg"
    rel = f"{IMAGES_DIR_NAME}/{name}"
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=90)
    (d / name).write_bytes(buf.getvalue())
    # 清理旧封面文件
    old_cover = rec.get('cover_image')
    if old_cover:
        try:
            old_fp = d / Path(old_cover).name
            if old_fp.exists() and old_fp.name != name:
                old_fp.unlink()
        except OSError:
            pass
    conn = _conn()
    try:
        conn.execute(
            "UPDATE web_nav SET cover_image=?, updated_at=(datetime('now','localtime')) WHERE id=?",
            (rel, nid),
        )
        conn.commit()
        return get_item(nid)
    finally:
        conn.close()


def reorder(ids):
    """按传入的 id 顺序批量更新 sort_order（0,1,2,…），实现手动拖拽排序持久化。"""
    conn = _conn()
    try:
        for i, nid in enumerate(ids):
            conn.execute(
                "UPDATE web_nav SET sort_order=? WHERE id=?",
                (i, int(nid)),
            )
        conn.commit()
    finally:
        conn.close()


def get_image_file(rel_path):
    """返回图片绝对路径，限制在 data/web_nav_images 内（防目录穿越）。"""
    p = (db.DATA_DIR / rel_path).resolve()
    base = _images_dir().resolve()
    if p != base and base not in p.parents:
        raise ValueError('非法路径')
    if not p.is_file():
        raise ValueError('图片不存在')
    return p


# 默认分类顺序：前端筛选栏与新建下拉共用
DEFAULT_CATEGORIES = ['AI', '漫剧', '工具', '文档', '素材', '其他']


def meta():
    """返回分类/标签供前端筛选与下拉使用。分类始终包含 DEFAULT_CATEGORIES，用户自建分类追加。"""
    conn = _conn()
    try:
        user_cats = set(r[0] for r in conn.execute(
            "SELECT DISTINCT category FROM web_nav WHERE category IS NOT NULL AND category<>''"
        ).fetchall())
        # 默认分类固定顺序；用户自建按字母序追加
        cats = [c for c in DEFAULT_CATEGORIES if c in user_cats or True]
        custom = sorted(user_cats - set(DEFAULT_CATEGORIES))
        cats = DEFAULT_CATEGORIES + custom

        tags = set()
        for r in conn.execute(
                "SELECT DISTINCT tags FROM web_nav WHERE tags IS NOT NULL AND tags<>''").fetchall():
            for t in (r[0] or '').split(','):
                t = t.strip()
                if t:
                    tags.add(t)
        return {
            'categories': cats,
            'all_tags': sorted(tags),
        }
    finally:
        conn.close()


_ensure_columns()
