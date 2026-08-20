"""model_config/router.py —— /api/model_config/* 路由（只管接线，逻辑在 service）"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional, List

from . import service, providers

router = APIRouter(prefix="/api/model_config", tags=["model_config"])


class CfgIn(BaseModel):
    name: str
    base_url: str
    model_name: str
    provider: str = "openai"
    provider_key: Optional[str] = None
    model_profile_id: Optional[int] = None
    mode: Optional[str] = None
    api_key: Optional[str] = None
    temperature: float = 0.7
    timeout_sec: int = 300
    is_active: int = 0
    thinking_enabled: int = 1
    reasoning_effort: str = "medium"
    max_tokens: int = 2048
    supports_vision: int = 0
    reasoning_format: str = "thinking_block"
    key_vault_id: Optional[int] = None
    secret_key: Optional[str] = None

    @field_validator('name', 'base_url', 'api_key', mode='before')
    @classmethod
    def _strip_required(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator('name', 'base_url', 'api_key')
    @classmethod
    def _not_empty(cls, v):
        if not v:
            raise ValueError('该字段不能为空')
        return v


@router.get("")
def list_cfg():
    return service.list_configs()


@router.post("")
def create_cfg(req: CfgIn):
    row = service.create_config(req.dict())
    if req.is_active:
        service.set_active(row["id"])
    return row


@router.put("/{cid}")
def update_cfg(cid: int, req: CfgIn):
    if not service.get_config(cid):
        raise HTTPException(status_code=404, detail="配置不存在")
    row = service.update_config(cid, req.dict())
    if req.is_active:
        service.set_active(cid)
    return row


@router.delete("/{cid}")
def delete_cfg(cid: int):
    service.delete_config(cid)
    return {"ok": True}


class ReorderIn(BaseModel):
    ids: List[int]


@router.post("/reorder")
def reorder_cfg(req: ReorderIn):
    service.reorder(req.ids)
    return {"ok": True}


@router.post("/{cid}/activate")
def activate(cid: int):
    if not service.get_config(cid):
        raise HTTPException(status_code=404, detail="配置不存在")
    service.set_active(cid)
    return {"ok": True}


@router.post("/test")
def test_draft(req: CfgIn):
    """测试一份未保存的草稿配置（保存前先试连通）"""
    return service.probe(req.dict())


@router.post("/{cid}/test")
def test_saved(cid: int):
    """测试一条已保存的配置"""
    return service.test_by_id(cid)


@router.post("/{cid}/refresh_key_vault")
def refresh_key_vault(cid: int):
    """从该配置关联的 AI 密钥库条目重新拉取 base_url / api_key / secret_key"""
    if not service.get_config(cid):
        raise HTTPException(status_code=404, detail="配置不存在")
    row = service.refresh_from_key_vault(cid)
    if row is None:
        raise HTTPException(status_code=400, detail="该配置未关联 AI 密钥库")
    return row


# ---------- 厂商/模型档案字典 ----------

@router.get("/providers")
def list_providers():
    """返回所有内置厂商"""
    return providers.list_providers()


@router.get("/profiles")
def list_profiles(provider_key: Optional[str] = None):
    """返回模型档案；可传 provider_key 限定某厂商"""
    return providers.list_profiles(provider_key)
