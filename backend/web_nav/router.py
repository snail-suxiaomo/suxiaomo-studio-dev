"""web_nav/router.py —— 网址导航 REST 接口
路由前缀 /web-nav：
- GET    /list          列表（支持 category / keyword / tag 筛选）
- GET    /meta          筛选维度（已有的分类/标签）
- GET    /{nid}         详情
- POST   /             新建 {title, url, category, note, tags}
- PUT    /{nid}        更新
- DELETE /{nid}        删除
- POST   /{nid}/images 上传图标/截图（多文件）
- DELETE /{nid}/images/{filename} 删除单张
- GET    /asset/{rel_path:path} 预览图片
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List

from web_nav import service


router = APIRouter(prefix='/api/web-nav', tags=['web_nav'])


class WebNavIn(BaseModel):
    title: str
    url: Optional[str] = None
    category: str = '其他'
    note: str = ''
    tags: str = ''


@router.get('/list')
def list_items(category: str = '全部', keyword: str = '', tag: str = ''):
    return service.list_items(category, keyword or None, tag or None)


@router.get('/meta')
def get_meta():
    return service.meta()


@router.get('/{nid}')
def get_item(nid: int):
    row = service.get_item(nid)
    if not row:
        raise HTTPException(404, '记录不存在')
    return row


@router.post('/')
def create(req: WebNavIn):
    try:
        return service.create_item(req.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.put('/{nid}')
def update(nid: int, req: WebNavIn):
    try:
        return service.update_item(nid, req.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete('/{nid}')
def delete(nid: int):
    service.delete_item(nid)
    return {'ok': True}


@router.post('/{nid}/images')
async def upload_images(nid: int, files: List[UploadFile] = File(...)):
    """上传图标/截图：保存到 data/web_nav_images/，追加到记录的 images 数组。"""
    try:
        data = [{'filename': f.filename or 'image', 'content': await f.read()} for f in files]
        return service.add_images(nid, data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f'上传失败：{e}')


@router.delete('/{nid}/images/{filename}')
def remove_image(nid: int, filename: str):
    """删除单张图标/截图。"""
    try:
        return service.delete_image(nid, filename)
    except ValueError as e:
        raise HTTPException(400, str(e))


class CoverReq(BaseModel):
    cover_image: Optional[str] = None


@router.put('/{nid}/cover')
def set_cover(nid: int, req: CoverReq):
    """设置封面图（传入相对路径）或取消封面（传空字符串/null）。"""
    try:
        return service.set_cover(nid, req.cover_image)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post('/{nid}/cover-crop')
async def upload_cover_crop(nid: int, file: UploadFile = File(...)):
    """上传裁剪后的封面图（16:9），保存为独立封面文件并设为 cover_image。"""
    try:
        content = await file.read()
        if not content:
            raise ValueError('文件为空')
        return service.set_cover_crop(nid, content)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f'上传失败：{e}')


@router.get('/asset/{rel_path:path}')
def get_asset(rel_path: str):
    """预览图片：返回图片文件流（限制在 data/web_nav_images 内）。"""
    try:
        fp = service.get_image_file(rel_path)
        return FileResponse(str(fp))
    except ValueError as e:
        raise HTTPException(400, str(e))


class ReorderIn(BaseModel):
    ids: List[int]


@router.post('/reorder')
def reorder(req: ReorderIn):
    """批量保存卡片顺序（拖拽排序后调用）。"""
    service.reorder(req.ids)
    return {'ok': True}
