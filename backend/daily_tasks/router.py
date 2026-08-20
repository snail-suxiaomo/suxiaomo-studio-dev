"""daily_tasks/router.py —— 每日任务 REST 接口
路由前缀 /api/daily-tasks：
- GET    /list                列表（支持 owner / keyword 筛选，附今日完成状态）
- GET    /{tid}               详情
- POST   /                    新建
- PUT    /{tid}               更新
- DELETE /{tid}               删除
- POST   /{tid}/toggle        切换今日完成状态 {done: bool}
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional, List

from daily_tasks import service


router = APIRouter(prefix='/api/daily-tasks', tags=['daily_tasks'])


class DailyTaskIn(BaseModel):
    name: str
    owner: Optional[str] = None
    software: Optional[str] = None
    detail: str = '每日签到领积分'
    login_account: Optional[str] = None
    operation_accounts: List[str] = []
    must_do: Optional[str] = None
    link: Optional[str] = None
    points: int = 0
    points_mode: str = 'cumulative'
    task_date: Optional[str] = None

    @field_validator('operation_accounts', mode='before')
    @classmethod
    def _coerce_accounts(cls, v):
        """统一把任意输入规范成字符串列表（剔除空项）。"""
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            try:
                import json
                a = json.loads(v)
                if isinstance(a, list):
                    return [str(x).strip() for x in a if str(x).strip()]
            except Exception:
                pass
            return [x.strip() for x in v.split(',') if x.strip()]
        return []

    @field_validator('points', mode='before')
    @classmethod
    def _coerce_points(cls, v):
        try:
            return max(0, int(v or 0))
        except Exception:
            return 0

    @field_validator('points_mode', mode='before')
    @classmethod
    def _coerce_mode(cls, v):
        v = (v or 'cumulative')
        return v if v in ('cumulative', 'daily') else 'cumulative'


class ToggleIn(BaseModel):
    done: bool


class ReorderIn(BaseModel):
    order: List[int]


class BulkIn(BaseModel):
    action: str  # 'complete_all' | 'reset_today'


class StatusIn(BaseModel):
    id: int


@router.get('/list')
def list_items(owner: str = '', keyword: str = '', status: str = 'active'):
    return service.list_items(owner or None, keyword or None, status or 'active')


@router.get('/{tid}')
def get_item(tid: int):
    row = service.get_item(tid)
    if not row:
        raise HTTPException(404, '任务不存在')
    return row


@router.get('/points-summary')
def points_summary():
    return service.points_summary()


@router.post('/')
def create(req: DailyTaskIn):
    try:
        return service.create_item(req.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.put('/{tid}')
def update(tid: int, req: DailyTaskIn):
    try:
        return service.update_item(tid, req.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete('/{tid}')
def delete(tid: int):
    service.delete_item(tid)
    return {'ok': True}


@router.post('/{tid}/toggle')
def toggle(tid: int, req: ToggleIn):
    try:
        return {'task_id': tid, 'done': service.toggle_complete(tid, req.done)}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post('/reorder')
def reorder(req: ReorderIn):
    service.reorder_items(req.order)
    return {'ok': True}


@router.post('/bulk')
def bulk(req: BulkIn):
    if req.action == 'complete_all':
        service.bulk_complete_all()
    elif req.action == 'reset_today':
        service.bulk_reset_today()
    else:
        raise HTTPException(400, '未知操作')
    return {'ok': True}


@router.post('/pause')
def pause(req: StatusIn):
    try:
        service.set_status(req.id, 'paused')
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {'ok': True}


@router.post('/resume')
def resume(req: StatusIn):
    try:
        service.set_status(req.id, 'active')
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {'ok': True}
