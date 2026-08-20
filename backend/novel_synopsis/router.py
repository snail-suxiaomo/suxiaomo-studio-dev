"""novel_synopsis/router.py —— 01-梗概的 HTTP 接口"""
from fastapi import APIRouter
from pydantic import BaseModel

from . import service

router = APIRouter(prefix="/api/novel_synopsis", tags=["novel_synopsis"])


class RunReq(BaseModel):
    project_id: int
    chapter_idx: int = None  # run_all 时可为空；run 单章必填


@router.get("/chapters")
def api_chapters(project_id: int):
    """列出某项目 00-拆分 下可处理的章节"""
    return service.list_chapters(project_id)


@router.post("/generate")
def api_generate(req: RunReq):
    """仅生成单章梗概"""
    if req.chapter_idx is None:
        return {"ok": False, "error": "chapter_idx 必填"}
    return service.generate_chapter(req.project_id, req.chapter_idx)


@router.post("/validate")
def api_validate(req: RunReq):
    """仅对单章已生成的梗概做格式校验"""
    if req.chapter_idx is None:
        return {"ok": False, "error": "chapter_idx 必填"}
    return service.validate_chapter(req.project_id, req.chapter_idx)


@router.post("/review")
def api_review(req: RunReq):
    """仅对单章已生成的梗概做 AI 审核"""
    if req.chapter_idx is None:
        return {"ok": False, "error": "chapter_idx 必填"}
    return service.review_chapter(req.project_id, req.chapter_idx)


@router.post("/run")
def api_run(req: RunReq):
    """向后兼容：生成 + 校验 + 审核一次性跑完"""
    if req.chapter_idx is None:
        return {"ok": False, "error": "chapter_idx 必填"}
    return service.run_chapter(req.project_id, req.chapter_idx)


@router.post("/run_all")
def api_run_all(req: RunReq):
    """生成全部章梗概（含校验+审核）"""
    return service.run_all(req.project_id)
