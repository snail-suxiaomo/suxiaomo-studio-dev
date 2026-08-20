"""novel_project/router.py —— /api/novel_project/* 路由（只接线，逻辑在 service）"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from . import service

router = APIRouter(prefix="/api/novel_project", tags=["novel_project"])


class ProjIn(BaseModel):
    name: str
    description: Optional[str] = None


@router.get("")
def list_projects():
    return [dict(r) for r in service.list_projects()]


@router.post("")
def create_project(req: ProjIn):
    try:
        row = service.create_project(req.name, req.description)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return dict(row)


@router.delete("/{pid}")
def delete_project(pid: int):
    if not service.get_project(pid):
        raise HTTPException(status_code=404, detail="项目不存在")
    service.delete_project(pid)
    return {"ok": True}


@router.put("/{pid}/archive")
def archive(pid: int):
    if not service.get_project(pid):
        raise HTTPException(status_code=404, detail="项目不存在")
    service.set_status(pid, "archived")
    return {"ok": True}


@router.put("/{pid}/activate")
def activate(pid: int):
    if not service.get_project(pid):
        raise HTTPException(status_code=404, detail="项目不存在")
    service.set_status(pid, "active")
    return {"ok": True}
