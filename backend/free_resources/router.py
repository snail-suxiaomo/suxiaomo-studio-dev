"""free_resources/router.py —— 免费资源 REST 接口
路由前缀 /free-resources：
- GET    /list          列表（支持 category / keyword / tag 筛选）
- GET    /meta          筛选维度（已有的分类/标签）
- GET    /{rid}         详情
- POST   /             新建 {title, url, category, platform, steps, quota, prompt_ref, note, tags}
- PUT    /{rid}        更新
- DELETE /{rid}        删除
- POST   /{rid}/images 上传截图（多文件）
- DELETE /{rid}/images/{filename} 删除单张
- GET    /asset/{rel_path:path} 预览截图
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
from typing import Optional, List

from free_resources import service


router = APIRouter(prefix='/api/free-resources', tags=['free_resources'])


class FreeResourceIn(BaseModel):
    title: str
    url: Optional[str] = None
    category: str = '其他'
    platform: Optional[str] = None
    steps: str = ''
    quota: str = ''
    prompt_ref: str = ''
    note: str = ''
    tags: str = ''
    status: str = 'available'
    region: Optional[str] = None
    register_way: Optional[str] = None
    need_vpn: Optional[str] = None
    quality: Optional[str] = None
    support_model: Optional[str] = None
    verified_at: Optional[str] = None
    rating: Optional[str] = None
    cost_15s_points: Optional[str] = None
    cost_15s_amount: Optional[str] = None

    @field_validator('*', mode='before')
    @classmethod
    def _coerce_number_to_str(cls, v):
        """本模型所有字段都是文本型；前端 <input type="number"> 会回传数字（如 rating=5），
        pydantic 严格模式会直接 422。这里统一把数字转成字符串，避免因输入控件类型导致保存失败。
        5.0 这类整数值浮点会规范成 "5"，不留小数尾巴。"""
        if isinstance(v, bool):
            return v
        if isinstance(v, int):
            return str(v)
        if isinstance(v, float):
            return str(int(v)) if v.is_integer() else str(v)
        return v


class ReorderIn(BaseModel):
    ids: List[int]


@router.get('/list')
def list_items(category: str = '全部', keyword: str = '', tag: str = '', status: str = ''):
    return service.list_items(category, keyword or None, tag or None, status or None)


@router.get('/meta')
def get_meta():
    return service.meta()


@router.post('/reorder')
def reorder(req: ReorderIn):
    try:
        return service.reorder(req.ids)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get('/{rid}')
def get_item(rid: int):
    row = service.get_item(rid)
    if not row:
        raise HTTPException(404, '记录不存在')
    return row


@router.post('/')
def create(req: FreeResourceIn):
    try:
        return service.create_item(req.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.put('/{rid}')
def update(rid: int, req: FreeResourceIn):
    try:
        return service.update_item(rid, req.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete('/{rid}')
def delete(rid: int):
    service.delete_item(rid)
    return {'ok': True}


@router.post('/{rid}/images')
async def upload_images(rid: int, files: List[UploadFile] = File(...)):
    """上传截图：保存到 data/free_resources_images/，追加到记录的 images 数组。"""
    try:
        data = [{'filename': f.filename or 'image', 'content': await f.read()} for f in files]
        return service.add_images(rid, data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f'上传失败：{e}')


@router.delete('/{rid}/images/{filename}')
def remove_image(rid: int, filename: str):
    """删除单张截图。"""
    try:
        return service.delete_image(rid, filename)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get('/asset/{rel_path:path}')
def get_asset(rel_path: str):
    """预览截图：返回图片文件流（限制在 data/free_resources_images 内）。"""
    try:
        fp = service.get_image_file(rel_path)
        return FileResponse(str(fp))
    except ValueError as e:
        raise HTTPException(400, str(e))
