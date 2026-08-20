"""manju_generate/router.py —— 漫剧生成后端接口（独立模块）

路由前缀 /api/manju-generate：
- GET  /info              返回分类列表（含首次种子数据落库）
- GET  /sites?category=   列出某分类下的网站配置（生图/音色/生视频）
- POST /sites             新增网站配置 {category, name, tag, url}
- PUT  /sites/{id}        更新 {category?, name?, tag?, url?, sort_order?}
- DELETE /sites/{id}      删除某条配置

网站配置（名称 + 标签 + 网址）持久化在后端数据库 manju_sites 表，
前端生图/音色/生视频内置浏览器标签页打开这些站点，登录态由 Electron webview
的 persist partition 缓存（清除缓存才丢失）。
"""

import sqlite3
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from common import db

router = APIRouter(prefix='/api/manju-generate', tags=['manju_generate'])

CATEGORIES = ['去重', '剧本', '资产', '分镜', '生图', '音色', '生视频', '其他']


# ---------------------------------------------------------------------------
# 表与种子（幂等；首启访问即建表，避免依赖 schema 复制时机）
# ---------------------------------------------------------------------------
def _ensure_table():
    conn = db.get_conn()
    try:
        conn.execute(
            '''CREATE TABLE IF NOT EXISTS manju_sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                name TEXT NOT NULL,
                tag TEXT NOT NULL DEFAULT '',
                url TEXT NOT NULL DEFAULT '',
                sort_order INTEGER NOT NULL DEFAULT 0,
                is_default INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            )'''
        )
        conn.commit()
    finally:
        conn.close()


def _seed():
    """首次启动（表为空）才落种子数据。用户删除的默认项不会复活 —— 需要时用 /reset-defaults 补回。"""
    conn = db.get_conn()
    try:
        count = conn.execute("SELECT COUNT(*) AS c FROM manju_sites").fetchone()["c"]
        if count > 0:
            return
        seeds = [
            # 去重/剧本/资产/分镜：默认 AI 对话入口
            ('去重', 'DeepSeek', 'AI对话', 'https://chat.deepseek.com/'),
            ('剧本', 'Kimi', 'AI对话', 'https://kimi.moonshot.cn/'),
            ('资产', 'ChatGPT', 'AI对话', 'https://chat.openai.com/'),
            ('分镜', 'WorkBuddy', 'AI对话', 'https://www.workbuddy.cn/'),
            # 生图：软件名-标签（人物/场景/道具）自定义结构
            ('生图', '椒图AI-人物', '人物', 'https://'),
            ('生图', '椒图AI-场景', '场景', 'https://'),
            ('生图', '椒图AI-道具', '道具', 'https://'),
            ('生图', 'Flux art-人物', '人物', 'https://'),
            ('生图', 'Flux art-场景', '场景', 'https://'),
            ('生图', 'Flux art-道具', '道具', 'https://'),
            # 生视频：常用平台
            ('生视频', '即梦', '视频', 'https://jimeng.jianying.com'),
            ('生视频', '小云雀', '视频', 'https://'),
            ('生视频', 'Liblib', '视频', 'https://www.liblib.art'),
            ('生视频', '可灵', '视频', 'https://klingai.kuaishou.com'),
            ('生视频', 'ComfyUI', '视频', 'http://127.0.0.1:8188'),
            # 音色：默认只保留剪映 + TTS（其余由用户自定义添加）
            ('音色', '配音-剪映', '配音', 'https://'),
            ('音色', '配音-TTS', 'TTS', 'https://'),
        ]
        if seeds:
            conn.executemany(
                "INSERT INTO manju_sites (category, name, tag, url, sort_order, is_default) VALUES (?,?,?,?,0,1)",
                seeds,
            )
            conn.commit()
    finally:
        conn.close()


def _row_to_dict(r):
    return {
        'id': r['id'],
        'category': r['category'],
        'name': r['name'],
        'tag': r['tag'],
        'url': r['url'],
        'sort_order': r['sort_order'],
        'is_default': r['is_default'],
    }


# ---------------------------------------------------------------------------
# 接口
# ---------------------------------------------------------------------------
@router.get('/info')
def info():
    _ensure_table()
    _seed()
    return {'ok': True, 'categories': CATEGORIES}


@router.get('/sites')
def list_sites(category: str = ''):
    _ensure_table()
    _seed()
    conn = db.get_conn()
    try:
        if category:
            if category not in CATEGORIES:
                raise HTTPException(400, '无效的分类')
            rows = conn.execute(
                "SELECT * FROM manju_sites WHERE category=? ORDER BY sort_order, id",
                (category,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM manju_sites ORDER BY category, sort_order, id"
            ).fetchall()
        return {'ok': True, 'sites': [_row_to_dict(r) for r in rows]}
    finally:
        conn.close()


class SiteIn(BaseModel):
    category: str
    name: str
    tag: str = ''
    url: str = ''


@router.post('/sites')
def create_site(s: SiteIn):
    _ensure_table()
    if s.category not in CATEGORIES:
        raise HTTPException(400, '无效的分类')
    if not s.name or not s.name.strip():
        raise HTTPException(400, '名称不能为空')
    conn = db.get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO manju_sites (category, name, tag, url, sort_order) "
            "VALUES (?,?,?,?, (SELECT COALESCE(MAX(sort_order),0)+10 FROM manju_sites WHERE category=?))",
            (s.category, s.name.strip(), s.tag, s.url, s.category),
        )
        conn.commit()
        rid = cur.lastrowid
        row = conn.execute("SELECT * FROM manju_sites WHERE id=?", (rid,)).fetchone()
        return {'ok': True, 'site': _row_to_dict(row)}
    finally:
        conn.close()


class SiteUpdate(BaseModel):
    category: str = None
    name: str = None
    tag: str = None
    url: str = None
    sort_order: int = None


@router.put('/sites/{sid}')
def update_site(sid: int, s: SiteUpdate):
    _ensure_table()
    conn = db.get_conn()
    try:
        cur = conn.execute("SELECT * FROM manju_sites WHERE id=?", (sid,)).fetchone()
        if not cur:
            raise HTTPException(404, '站点不存在')
        if s.category is not None and s.category not in CATEGORIES:
            raise HTTPException(400, '无效的分类')
        name = s.name if s.name is not None else cur['name']
        tag = s.tag if s.tag is not None else cur['tag']
        url = s.url if s.url is not None else cur['url']
        category = s.category if s.category is not None else cur['category']
        sort_order = s.sort_order if s.sort_order is not None else cur['sort_order']
        conn.execute(
            "UPDATE manju_sites SET category=?, name=?, tag=?, url=?, sort_order=?, updated_at=? WHERE id=?",
            (category, name, tag, url, sort_order, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), sid),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM manju_sites WHERE id=?", (sid,)).fetchone()
        return {'ok': True, 'site': _row_to_dict(row)}
    finally:
        conn.close()


@router.delete('/sites/{sid}')
def delete_site(sid: int):
    _ensure_table()
    conn = db.get_conn()
    try:
        conn.execute("DELETE FROM manju_sites WHERE id=?", (sid,))
        # 同步删除引用此 site 的所有 open tab
        conn.execute("DELETE FROM manju_open_tabs WHERE site_id=?", (sid,))
        conn.commit()
        return {'ok': True}
    finally:
        conn.close()


@router.post('/reset-defaults')
def reset_defaults():
    """恢复默认站点：仅补回当前缺失的默认项（不删用户自建、不重复插入已存在的）。"""
    _ensure_table()
    conn = db.get_conn()
    try:
        existing = {
            (r['category'], r['name'])
            for r in conn.execute("SELECT category, name FROM manju_sites").fetchall()
        }
        seeds = [
            ('去重', 'DeepSeek', 'AI对话', 'https://chat.deepseek.com/'),
            ('剧本', 'Kimi', 'AI对话', 'https://kimi.moonshot.cn/'),
            ('资产', 'ChatGPT', 'AI对话', 'https://chat.openai.com/'),
            ('分镜', 'WorkBuddy', 'AI对话', 'https://www.workbuddy.cn/'),
            ('生图', '椒图AI-人物', '人物', 'https://'),
            ('生图', '椒图AI-场景', '场景', 'https://'),
            ('生图', '椒图AI-道具', '道具', 'https://'),
            ('生图', 'Flux art-人物', '人物', 'https://'),
            ('生图', 'Flux art-场景', '场景', 'https://'),
            ('生图', 'Flux art-道具', '道具', 'https://'),
            ('生视频', '即梦', '视频', 'https://jimeng.jianying.com'),
            ('生视频', '小云雀', '视频', 'https://'),
            ('生视频', 'Liblib', '视频', 'https://www.liblib.art'),
            ('生视频', '可灵', '视频', 'https://klingai.kuaishou.com'),
            ('生视频', 'ComfyUI', '视频', 'http://127.0.0.1:8188'),
            ('音色', '配音-剪映', '配音', 'https://'),
            ('音色', '配音-TTS', 'TTS', 'https://'),
        ]
        new = [s for s in seeds if (s[0], s[1]) not in existing]
        if new:
            conn.executemany(
                "INSERT INTO manju_sites (category, name, tag, url, sort_order, is_default) VALUES (?,?,?,?,0,1)",
                new,
            )
            conn.commit()
        return {'ok': True, 'added': len(new)}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 已打开标签（持久化到后端数据库，跨会话/跨重启/跨 localStorage 清理都保留）
# ---------------------------------------------------------------------------
def _tab_row_to_dict(r):
    return {
        'client_id': r['client_id'],
        'category': r['category'],
        'site_id': r['site_id'],
        'name': r['name'],
        'tag': r['tag'],
        'url': r['url'],
        'sort_order': r['sort_order'],
    }


@router.get('/tabs')
def list_tabs():
    _ensure_table()
    conn = db.get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM manju_open_tabs ORDER BY sort_order, id"
        ).fetchall()
        return {'ok': True, 'tabs': [_tab_row_to_dict(r) for r in rows]}
    finally:
        conn.close()


class TabIn(BaseModel):
    client_id: str
    category: str
    site_id: int = None
    name: str
    tag: str = ''
    url: str
    sort_order: int = 0


@router.post('/tabs')
def upsert_tab(t: TabIn):
    _ensure_table()
    if not t.client_id or not t.name or not t.name.strip():
        raise HTTPException(400, '参数不完整')
    conn = db.get_conn()
    try:
        conn.execute(
            '''INSERT INTO manju_open_tabs (client_id, category, site_id, name, tag, url, sort_order, updated_at)
               VALUES (?,?,?,?,?,?,?, datetime('now','localtime'))
               ON CONFLICT(client_id) DO UPDATE SET
                 category=excluded.category,
                 site_id=excluded.site_id,
                 name=excluded.name,
                 tag=excluded.tag,
                 url=excluded.url,
                 sort_order=excluded.sort_order,
                 updated_at=datetime('now','localtime')''',
            (t.client_id, t.category, t.site_id, t.name.strip(), t.tag, t.url, t.sort_order),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM manju_open_tabs WHERE client_id=?", (t.client_id,)
        ).fetchone()
        return {'ok': True, 'tab': _tab_row_to_dict(row)}
    finally:
        conn.close()


@router.delete('/tabs/{client_id}')
def delete_tab(client_id: str):
    _ensure_table()
    conn = db.get_conn()
    try:
        conn.execute("DELETE FROM manju_open_tabs WHERE client_id=?", (client_id,))
        conn.commit()
        return {'ok': True}
    finally:
        conn.close()
