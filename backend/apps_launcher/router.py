"""apps_launcher/router.py —— 应用启动器 REST 接口

路由前缀 /apps_launcher：
- GET  /apps_launcher/apps        列应用
- POST /apps_launcher/apps        加应用 {name, exe_path, args?, note?, category?}
- PUT  /apps_launcher/apps/{id}   改应用
- DELETE /apps_launcher/apps/{id} 删应用
- POST /apps_launcher/apps/reorder 排序
- POST /apps_launcher/launch/{id}  启动应用
"""

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from apps_launcher import service

router = APIRouter(prefix='/api/apps_launcher', tags=['apps_launcher'])


class AppIn(BaseModel):
    name: str
    exe_path: str
    args: str | None = None
    note: str | None = None
    category: str = '未分类'
    detect_port: int | None = None


class AppUpdateIn(BaseModel):
    name: str | None = None
    exe_path: str | None = None
    category: str | None = None
    note: str | None = None
    args: str | None = None
    detect_port: int | None = None


class OrderIn(BaseModel):
    ids: list[int]


@router.get('/apps')
def get_apps():
    return service.list_apps()


@router.post('/apps')
def post_app(req: AppIn):
    try:
        return service.add_app(req.name, req.exe_path, req.args, req.note, req.category, req.detect_port)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.put('/apps/{app_id}')
def put_app(app_id: int, req: AppUpdateIn):
    try:
        return service.update_app(app_id, req.name, req.exe_path, req.category, req.note, req.args, req.detect_port)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete('/apps/{app_id}')
def del_app(app_id: int):
    service.delete_app(app_id)
    return {'ok': True}


@router.post('/apps/reorder')
def reorder_apps(req: OrderIn):
    try:
        service.update_order(req.ids)
        return {'ok': True}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get('/icon/{app_id}')
def icon(app_id: int):
    data = service.get_icon(app_id)
    if not data:
        raise HTTPException(404, 'icon not found')
    return Response(content=data, media_type='image/png')


@router.post('/launch/{app_id}')
def launch(app_id: int, force_new: bool = False):
    try:
        result = service.launch_app(app_id, force_new=force_new)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get('/status/{app_id}')
def status(app_id: int):
    try:
        return service.is_running(app_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
