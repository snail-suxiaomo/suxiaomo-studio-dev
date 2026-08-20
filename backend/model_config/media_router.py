"""model_config/media_router.py —— 媒体生成（生图/生视频）REST 接口"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path

from common import db
from . import media_gen

router = APIRouter(prefix="/api/media", tags=["media_gen"])


class GenIn(BaseModel):
    prompt: str
    params: dict = {}


@router.post("/generate/{config_id}")
def generate(config_id: int, req: GenIn):
    """提交一次生图/生视频任务（config 必须是 capability=image/video 的 Flux Art 配置）"""
    try:
        return media_gen.submit(config_id, req.prompt, req.params)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/task/{task_id}")
def task_status(task_id: int):
    """查询任务状态；进行中会自动轮询 Flux Art 直到终态，成功则带本地结果文件名。"""
    t = media_gen.get_task(task_id)
    if not t:
        raise HTTPException(status_code=404, detail="任务不存在")
    return t


@router.get("/file/{filename}")
def media_file(filename: str):
    """提供本地生成结果的静态文件（防目录穿越：只取 basename）。"""
    name = Path(filename).name
    path = db.DATA_DIR / "media" / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(str(path))
