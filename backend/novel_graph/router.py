"""novel_graph/router.py —— 02-图谱的 HTTP 接口（整本单一报告，仅 run）"""
from fastapi import APIRouter
from pydantic import BaseModel

from . import service

router = APIRouter(prefix="/api/novel_graph", tags=["novel_graph"])


class RunReq(BaseModel):
    project_id: int


@router.post("/generate")
def api_generate(req: RunReq):
    """仅生成整本图谱报告"""
    return service.generate_report(req.project_id)


@router.post("/validate")
def api_validate(req: RunReq):
    """仅对整本图谱报告做格式校验"""
    return service.validate_report(req.project_id)


@router.post("/review")
def api_review(req: RunReq):
    """仅对整本图谱报告做 AI 审核"""
    return service.review_report(req.project_id)


@router.post("/run")
def api_run(req: RunReq):
    """向后兼容：整本生成一次图谱报告（含校验+审核）"""
    return service.run(req.project_id)
