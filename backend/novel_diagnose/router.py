"""03-小说诊断 路由"""
from fastapi import APIRouter
from pydantic import BaseModel

from . import service

router = APIRouter(prefix="/api/novel_diagnose", tags=["novel_diagnose"])


class DiagnoseReq(BaseModel):
    project_id: int


@router.post("/generate")
def generate(req: DiagnoseReq):
    """仅生成整本诊断报告"""
    return service.generate_report(req.project_id)


@router.post("/validate")
def validate(req: DiagnoseReq):
    """仅对整本诊断报告做格式校验"""
    return service.validate_report(req.project_id)


@router.post("/review")
def review(req: DiagnoseReq):
    """仅对整本诊断报告做 AI 审核"""
    return service.review_report(req.project_id)


@router.post("/run")
def run(req: DiagnoseReq):
    """向后兼容：生成 + 校验 + 审核一次性跑完"""
    return service.run(req.project_id)
