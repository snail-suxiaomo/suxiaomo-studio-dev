"""chat/router.py —— /api/chat/* 路由（需登录）"""
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from login.router import get_current_user
from . import service

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ---------------- 会话管理 ----------------
class SessionCreate(BaseModel):
    model_config_id: Optional[int] = None
    title: Optional[str] = None


class SessionRename(BaseModel):
    title: str


@router.get("/sessions")
def get_sessions(model_config_id: Optional[int] = None, user=Depends(get_current_user)):
    """会话列表（按 updated_at 倒序）。可带 model_config_id 过滤。"""
    return service.list_sessions(model_config_id)


@router.post("/sessions")
def post_session(req: SessionCreate, user=Depends(get_current_user)):
    """新建会话（立即建一条空会话，前端点完就能在列表看到）。"""
    return service.create_session(req.model_config_id, req.title or "新会话")


@router.get("/sessions/{session_id}/messages")
def get_messages(session_id: int, user=Depends(get_current_user)):
    """拉某会话的全部历史消息。"""
    return service.list_messages(session_id)


@router.patch("/sessions/{session_id}")
def patch_session(session_id: int, req: SessionRename, user=Depends(get_current_user)):
    """改名。"""
    service.rename_session(session_id, req.title)
    return {"ok": True}


@router.delete("/sessions/{session_id}")
def del_session(session_id: int, user=Depends(get_current_user)):
    """删除会话（连带删消息与附件目录）。"""
    service.delete_session(session_id)
    return {"ok": True}


@router.post("/sessions/{session_id}/open-folder")
def open_folder(session_id: int, user=Depends(get_current_user)):
    """用系统文件管理器打开该会话的附件目录。"""
    return service.open_session_folder(session_id)


@router.get("/attachments/{session_id}/{filename}")
def get_attachment(session_id: int, filename: str, user=Depends(get_current_user)):
    """读取会话附件（图片预览 / 文件下载）。防目录穿越。"""
    path = service.attachment_path(session_id, filename)
    if path is None:
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": "not found"}, status_code=404)
    return FileResponse(str(path))


# ---------------- 发消息 ----------------
class AskReq(BaseModel):
    prompt: str
    system_prompt: str | None = None
    model_config_id: Optional[int] = None
    thinking: Optional[bool] = None
    reasoning_effort: Optional[str] = None
    session_id: Optional[int] = None


@router.post("/ask")
def ask(req: AskReq, user=Depends(get_current_user)):
    """纯文本/JSON 请求（无附件）。带 session_id 则落库。"""
    try:
        result = service.ask(req.prompt, req.system_prompt,
                             model_config_id=req.model_config_id,
                             thinking=req.thinking,
                             reasoning_effort=req.reasoning_effort,
                             session_id=req.session_id)
    except Exception as e:
        return {"reply": None, "reasoning": "", "error": str(e)}
    return result


@router.post("/ask-files")
def ask_files(
    prompt: str = Form(""),
    system_prompt: Optional[str] = Form(None),
    images: List[UploadFile] = File(default_factory=list),
    texts: List[UploadFile] = File(default_factory=list),
    model_config_id: Optional[int] = Form(None),
    thinking: Optional[bool] = Form(None),
    reasoning_effort: Optional[str] = Form(None),
    session_id: Optional[int] = Form(None),
    user=Depends(get_current_user),
):
    """带图片/文本附件的多部分请求。带 session_id 则落库。"""
    try:
        result = service.ask(prompt, system_prompt, images=images, texts=texts,
                             model_config_id=model_config_id,
                             thinking=thinking,
                             reasoning_effort=reasoning_effort,
                             session_id=session_id)
    except Exception as e:
        return {"reply": None, "reasoning": "", "error": str(e)}
    return result
