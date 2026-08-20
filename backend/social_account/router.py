"""social_account/router.py —— 自媒体账号汇总接口

路由前缀 /api/social-accounts（与前端 api()/fetch('/api/...') 一致）：
- GET    /api/social-accounts           列表
- POST   /api/social-accounts           新建
- GET    /api/social-accounts/template  下载导入模板（必须在 /{pid} 之前定义）
- POST   /api/social-accounts/export     导出 Excel（纯文本）
- POST   /api/social-accounts/export-bundle  导出图片资源（自包含 zip）
- POST   /api/social-accounts/import     导入 Excel（纯文本）
- POST   /api/social-accounts/import-bundle  导入图片资源（zip，可还原图片）
- POST   /api/social-accounts/upload-image  上传二维码/封面图（临时 uuid，保存时定名）
- POST   /api/social-accounts/reorder    排序
- PUT    /api/social-accounts/{pid}      更新
- DELETE /api/social-accounts/{pid}      删除
"""

import io
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from social_account import service

router = APIRouter(tags=['social_account'])


class AccountIn(BaseModel):
    platform: str = ''
    account_name: str = ''
    account_id: str = ''
    user_id: str = ''
    homepage_url: str = ''
    bio: str = ''
    gender: str = ''
    birthday: str = ''
    location: str = ''
    likes_count: int = 0
    mutual_count: int = 0
    following_count: int = 0
    followers_count: int = 0
    qr_image: str = ''
    cover_image: str = ''


class ExportIn(BaseModel):
    ids: Optional[List[int]] = None


class ReorderIn(BaseModel):
    ids: List[int]


@router.get('/api/social-accounts')
def list_accounts():
    return service.list_accounts()


@router.post('/api/social-accounts')
def create_account(req: AccountIn):
    try:
        return service.create_account(req.dict())
    except Exception as e:
        raise HTTPException(500, f'新增失败：{e}')


@router.get('/api/social-accounts/template')
def export_template():
    try:
        data = service.export_template()
    except Exception as e:
        raise HTTPException(500, f'模板生成失败：{e}')
    headers = {'Content-Disposition': 'attachment; filename="social_accounts_template.xlsx"'}
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.post('/api/social-accounts/export')
def export_accounts(req: ExportIn):
    try:
        data = service.export_excel(req.ids)
    except Exception as e:
        raise HTTPException(500, f'导出失败：{e}')
    headers = {'Content-Disposition': 'attachment; filename="social_accounts.xlsx"'}
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.post('/api/social-accounts/import')
async def import_excel(file: UploadFile = File(...), mode: str = Form('skip')):
    data = await file.read()
    try:
        return service.import_excel(data, mode)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f'导入失败：{e}')


@router.post('/api/social-accounts/export-bundle')
def export_bundle_accounts(req: ExportIn):
    try:
        data = service.export_bundle(req.ids)
    except Exception as e:
        raise HTTPException(500, f'导出失败：{e}')
    stamp = datetime.now().strftime('%Y%m%d_%H%M')
    headers = {
        'Content-Disposition': f'attachment; filename="social_accounts_bundle_{stamp}.zip"'
    }
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/zip",
        headers=headers,
    )


@router.post('/api/social-accounts/import-bundle')
async def import_bundle_accounts(file: UploadFile = File(...), mode: str = Form('skip')):
    data = await file.read()
    try:
        return service.import_bundle(data, mode)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f'导入失败：{e}')


@router.post('/api/social-accounts/upload-image')
async def upload_image(file: UploadFile = File(...)):
    data = await file.read()
    try:
        rel = service.save_image(data, file.filename or 'image.png')
        return {"path": rel}
    except Exception as e:
        raise HTTPException(500, f'上传失败：{e}')


@router.get('/api/social-accounts/asset/{rel_path:path}')
def get_asset(rel_path: str):
    """预览二维码/封面图：限制在 data/social_images 内。"""
    try:
        fp = service.get_image_file(rel_path)
        return FileResponse(str(fp))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post('/api/social-accounts/reorder')
def reorder(req: ReorderIn):
    try:
        return service.reorder(req.ids)
    except Exception as e:
        raise HTTPException(500, f'排序失败：{e}')


@router.put('/api/social-accounts/{pid}')
def update_account(pid: int, req: AccountIn):
    try:
        return service.update_account(pid, req.dict())
    except Exception as e:
        raise HTTPException(500, f'更新失败：{e}')


@router.delete('/api/social-accounts/{pid}')
def delete_account(pid: int):
    try:
        return service.delete_account(pid)
    except Exception as e:
        raise HTTPException(500, f'删除失败：{e}')
