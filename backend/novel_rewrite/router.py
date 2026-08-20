"""06-改写 路由（逐章）。"""
from fastapi import APIRouter
from pydantic import BaseModel

from . import service

router = APIRouter(prefix="/api/novel_rewrite", tags=["novel_rewrite"])


class RunReq(BaseModel):
    project_id: int
    chapter_idx: int = 0
    user_prompt: str = ""


@router.get("/chapters")
def chapters(project_id: int):
    return service.list_chapters(project_id)


@router.post("/generate")
def generate(req: RunReq):
    """仅生成单章改写"""
    return service.generate_chapter(req.project_id, req.chapter_idx)


@router.post("/validate")
def validate(req: RunReq):
    """仅对单章已生成的改写做格式校验"""
    return service.validate_chapter(req.project_id, req.chapter_idx)


@router.post("/review")
def review(req: RunReq):
    """仅对单章已生成的改写做 AI 审核"""
    return service.review_chapter(req.project_id, req.chapter_idx)


@router.post("/run")
def run(req: RunReq):
    """向后兼容：生成 + 校验 + 审核一次性跑完"""
    return service.run(req.project_id, req.chapter_idx, req.user_prompt)


@router.post("/run_all")
def run_all(req: RunReq):
    """全部改写（每章含校验+审核）"""
    return service.run_all(req.project_id, req.user_prompt)
