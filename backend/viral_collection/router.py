"""viral_collection/router.py —— 爆款收集 REST 接口

路由前缀 /api/viral-collection：
- GET    /list                     列表（platform / category / keyword / on_hongguo 筛选）
- GET    /meta                     筛选维度（已有平台、分类）
- GET    /{iid}                    详情
- POST   /                         新建
- PUT    /{iid}                    更新
- DELETE /{iid}                    删除（连同截图目录）
- POST   /{iid}/screenshots        上传截图（多张）
- POST   /{iid}/screenshots-base64 上传截图（base64，供 app 内截屏用）
- DELETE /{iid}/screenshots/{name} 删除单张截图
- GET    /asset/{rel_path}         预览截图
- POST   /parse                    AI 解析截图 → 结构化 JSON（不落库，仅回填表单）
"""

import base64
import mimetypes
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from pydantic import BaseModel

from viral_collection import service


router = APIRouter(prefix='/api/viral-collection', tags=['viral_collection'])


class ViralIn(BaseModel):
    platform: str = ''
    category: str = '漫剧'
    title: str = ''
    link: str = ''
    drama_name: str = ''
    aliases: str = ''
    original_novel: str = ''
    username: str = ''
    douyin_id: str = ''
    following: str = ''
    followers: str = ''
    works_count: str = ''
    bio: str = ''
    homepage_link: str = ''
    likes: str = ''
    favorites: str = ''
    play_count: str = ''
    comment_count: str = ''
    share_count: str = ''
    on_hongguo: int = 0
    learn_from: str = ''
    novel_clue: str = ''
    tags: str = ''
    novel_tags: str = ''
    note: str = ''


class Base64Shots(BaseModel):
    images: List[str] = []          # data:image/png;base64,xxx 或纯 base64
    filename_prefix: str = 'shot'


@router.get('/list')
def list_items(platform: str = '', category: str = '', keyword: str = '',
               on_hongguo: Optional[int] = None):
    hg = None if on_hongguo in (None, -1) else on_hongguo
    return service.list_items(platform, category, keyword, hg)


@router.get('/meta')
def get_meta():
    """返回已有的平台、分类列表，供筛选下拉用。"""
    rows = service.list_items()
    platforms, categories = [], []
    for r in rows:
        p, c = (r.get('platform') or '').strip(), (r.get('category') or '').strip()
        if p and p not in platforms:
            platforms.append(p)
        if c and c not in categories:
            categories.append(c)
    return {'platforms': platforms, 'categories': categories, 'total': len(rows)}


class SitesIn(BaseModel):
    sites: List[dict] = []


@router.get('/search-sites')
def get_search_sites():
    """小说平台搜索站点（用户可自定义），返回 [{name, url}]，url 里 {q} 为关键词占位。"""
    return service.get_search_sites()


@router.put('/search-sites')
def save_search_sites(req: SitesIn):
    return service.save_search_sites(req.sites)


@router.get('/asset/{rel_path:path}')
def get_asset(rel_path: str):
    """预览截图：返回图片字节（限制在 data/viral_images 内）。

    这里刻意不用 FileResponse：Windows 下它打开文件时不带 FILE_SHARE_DELETE，
    缩略图一旦被浏览器加载过，后续「删除截图 / 删除条目」就会因文件占用失败，
    留下库里已清、磁盘还在的垃圾文件。截图都是小图，一次性读进内存即时释放句柄最稳。
    """
    try:
        fp = service.get_image_file(rel_path)
        data = fp.read_bytes()
        mime = mimetypes.guess_type(fp.name)[0] or 'application/octet-stream'
        return Response(content=data, media_type=mime,
                        headers={'Cache-Control': 'no-cache'})
    except ValueError as e:
        raise HTTPException(400, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.post('/parse')
async def parse(files: List[UploadFile] = File(...),
                model_config_id: Optional[int] = Form(None),
                rule_id: Optional[int] = Form(None)):
    """把多张截图丢给视觉模型，返回结构化 JSON 供表单预填（不落库）。

    prompt 优先级：rule_id 指定的 AI 规则(DB) → 菜单=爆款收集 的启用规则(DB)
    → 参考规则文件(AI调用规则/爆款收集/截图识别填表规则.md) → 内置兜底。
    """
    try:
        return service.parse_screenshots(files, model_config_id, rule_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    except Exception as e:
        raise HTTPException(500, f'解析失败：{e}')


@router.get('/{iid}')
def get_one(iid: int):
    item = service.get_item(iid)
    if not item:
        raise HTTPException(404, '记录不存在')
    return item


@router.post('/')
def create(req: ViralIn):
    try:
        return service.create_item(req.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.put('/{iid}')
def update(iid: int, req: ViralIn):
    try:
        return service.update_item(iid, req.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete('/{iid}')
def delete(iid: int):
    service.delete_item(iid)
    return {'ok': True}


@router.post('/{iid}/screenshots')
async def upload_screenshots(iid: int, files: List[UploadFile] = File(...)):
    """上传截图（表单多文件）。"""
    try:
        data = [{'filename': f.filename or 'shot.png', 'content': await f.read()} for f in files]
        return service.add_screenshots(iid, data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f'上传失败：{e}')


@router.post('/{iid}/screenshots-base64')
def upload_screenshots_base64(iid: int, req: Base64Shots):
    """上传截图（base64 数组）：给 app 内截屏 / 剪贴板粘贴用。"""
    if not req.images:
        raise HTTPException(400, '没有图片')
    data = []
    for i, s in enumerate(req.images):
        raw_b64 = s.split(',', 1)[1] if s.startswith('data:') else s
        try:
            content = base64.b64decode(raw_b64)
        except Exception:
            raise HTTPException(400, f'第 {i + 1} 张图片 base64 解析失败')
        data.append({'filename': f'{req.filename_prefix}.png', 'content': content})
    try:
        return service.add_screenshots(iid, data)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete('/{iid}/screenshots/{filename}')
def remove_screenshot(iid: int, filename: str):
    try:
        return service.delete_screenshot(iid, filename)
    except ValueError as e:
        raise HTTPException(400, str(e))
