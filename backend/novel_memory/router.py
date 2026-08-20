"""novel_memory/router.py —— /api/novel_memory/* 路由（只接线，逻辑在 service）"""
from fastapi import APIRouter
from pydantic import BaseModel

from . import service

router = APIRouter(prefix="/api/novel_memory", tags=["novel_memory"])


class CreateIn(BaseModel):
    project_id: int
    function_id: str
    chapter_idx: int
    summary: str = ""
    status: str = "draft"
    key_data: dict | None = None


class UpdateIn(BaseModel):
    summary: str | None = None
    status: str | None = None
    key_data: dict | None = None


@router.get("")
def api_list(project_id: int, function_id: str | None = None, chapter_idx: int | None = None):
    """列出某项目的记忆（可按功能/章节过滤）"""
    return service.list_memory(project_id, function_id, chapter_idx)


@router.post("")
def api_create(req: CreateIn):
    """手动新增一条记忆"""
    return service.create_memory(
        req.project_id, req.function_id, req.chapter_idx,
        req.summary, req.status, req.key_data,
    )


@router.patch("/{memory_id}")
def api_update(memory_id: int, req: UpdateIn):
    """修改一条记忆（摘要 / 状态 / 结构化数据）"""
    return service.update_memory(memory_id, req.summary, req.status, req.key_data)


@router.delete("/{memory_id}")
def api_delete(memory_id: int):
    """删除一条记忆"""
    service.delete_memory(memory_id)
    return {"ok": True}
