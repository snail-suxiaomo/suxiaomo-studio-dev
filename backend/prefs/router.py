"""prefs/router.py —— 用户偏好 REST 接口

路由前缀 /api/prefs：
- GET /api/prefs/{pref_key}    读偏好（按当前登录用户）
- PUT /api/prefs/{pref_key}    写偏好（body: {"value": ...}，upsert）
- DELETE /api/prefs/{pref_key} 删偏好（幂等）
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Optional

from login.router import get_current_user
from prefs import service


router = APIRouter(prefix='/api/prefs', tags=['prefs'])


class PrefIn(BaseModel):
    value: Any = None


def _user_key(user) -> str:
    return str(user.get('username') or user.get('id') or 'anonymous')


@router.get('/{pref_key}')
def api_get_pref(pref_key: str, user=Depends(get_current_user)):
    value = service.get_pref(_user_key(user), pref_key)
    return {'key': pref_key, 'value': value}


@router.put('/{pref_key}')
def api_set_pref(pref_key: str, req: PrefIn, user=Depends(get_current_user)):
    service.set_pref(_user_key(user), pref_key, req.value)
    return {'ok': True, 'key': pref_key}


@router.delete('/{pref_key}')
def api_del_pref(pref_key: str, user=Depends(get_current_user)):
    service.del_pref(_user_key(user), pref_key)
    return {'ok': True, 'key': pref_key}
