"""04-小说策略 路由。"""
from fastapi import APIRouter, Request
from pydantic import BaseModel

from . import service

router = APIRouter(prefix="/api/novel_strategy", tags=["novel_strategy"])


class RunReq(BaseModel):
    project_id: int
    user_prompt: str = ""


@router.post("/generate")
def generate(req: RunReq):
    """仅生成 04-小说策略报告"""
    return service.generate_report(req.project_id)


@router.post("/validate")
def validate(req: RunReq):
    """仅对 04-小说策略报告做格式校验"""
    return service.validate_report(req.project_id)


@router.post("/review")
def review(req: RunReq):
    """仅对 04-小说策略报告做 AI 审核"""
    return service.review_report(req.project_id)


@router.post("/run")
def run(req: RunReq):
    """向后兼容：生成 + 校验 + 审核一次性跑完"""
    return service.run(req.project_id, req.user_prompt)
