"""key_vault/router.py —— AI 密钥库 HTTP 接口（独立于 model_config）"""
import io

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from typing import Optional, List

from key_vault import service

router = APIRouter(prefix='/api/key-vault', tags=['key-vault'])


class VaultIn(BaseModel):
    name: str
    provider: str
    category: str
    base_url: str
    api_key: str
    secret_key: Optional[str] = ''
    account: str
    dev_url: str
    sort_order: Optional[int] = 0

    @field_validator('name', 'provider', 'category', 'base_url', 'api_key', 'account', 'dev_url', mode='before')
    @classmethod
    def _strip_and_require(cls, v):
        if v is None:
            v = ''
        v = str(v).strip()
        if not v:
            raise ValueError('该字段不能为空')
        return v


@router.get('/list')
def list_vaults(category: str = '全部', keyword: str = ''):
    return service.list_vaults(category or '全部', keyword or None)


@router.get('/{vid}')
def get_vault(vid: int):
    v = service.get_vault(vid)
    if not v:
        raise HTTPException(404, '密钥条目不存在')
    return v


@router.post('/')
def create_vault(req: VaultIn):
    try:
        return service.create_vault(req.dict())
    except Exception as e:
        raise HTTPException(500, f'创建失败：{e}')


@router.put('/{vid}')
def update_vault(vid: int, req: VaultIn):
    try:
        v = service.update_vault(vid, req.dict())
        if not v:
            raise HTTPException(404, '密钥条目不存在')
        return v
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f'更新失败：{e}')


@router.delete('/{vid}')
def delete_vault(vid: int):
    try:
        return service.delete_vault(vid)
    except Exception as e:
        raise HTTPException(500, f'删除失败：{e}')


class BatchDeleteIn(BaseModel):
    ids: List[int]


@router.post('/batch-delete')
def batch_delete(req: BatchDeleteIn):
    try:
        return service.batch_delete(req.ids)
    except Exception as e:
        raise HTTPException(500, f'删除失败：{e}')


class ReorderIn(BaseModel):
    ids: List[int]


@router.post('/reorder')
def reorder(req: ReorderIn):
    service.reorder(req.ids)
    return {'ok': True}


class ExportIn(BaseModel):
    ids: Optional[List[int]] = None


@router.post('/export')
def export_vaults(req: ExportIn):
    """导出 xlsx（含 api_key / secret_key 明文）。"""
    try:
        data = service.export_excel(req.ids)
        return StreamingResponse(
            io.BytesIO(data),
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': 'attachment; filename="ai_key_vault.xlsx"'})
    except Exception as e:
        raise HTTPException(500, f'导出失败：{e}')


@router.post('/import')
async def import_vaults(file: UploadFile = File(...)):
    """从 xlsx 导入。唯一键为 (name, provider, account)，存在则更新，否则新建。"""
    try:
        data = await file.read()
        stats = service.import_excel(data)
        return stats
    except Exception as e:
        raise HTTPException(500, f'导入失败：{e}')
