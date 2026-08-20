"""ai_rule/router.py —— AI 调用规则 REST 接口

路由前缀 /api/ai-rules：
- GET    /                 自建规则列表（menu / function_key / role / enabled 可选；全空=全量）
- POST   /                 新建自建规则（source='db'）
- GET    /references       默认参考规则（读 workspace/AI调用规则/*.md，只读展示）
- POST   /copy-reference   把一条参考规则复制为自建规则（body: {ref_path}）
- PUT    /{rid}            编辑自建规则
- POST   /{rid}/reset      单条重置（从来源文件重新读入覆盖）
- DELETE /{rid}            删除自建规则
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List


router = APIRouter(prefix='/api/ai-rules', tags=['ai_rules'])

from ai_rule import service


class AiRuleIn(BaseModel):
    menu: str = '通用'
    function_key: str = '通用'
    role: str = 'system'
    name: str = ''
    content: str = ''
    model_config_id: Optional[int] = None
    thinking: str = 'follow'
    strength: Optional[str] = None
    enabled: int = 1


class AiRuleUpdate(BaseModel):
    menu: Optional[str] = None
    function_key: Optional[str] = None
    role: Optional[str] = None
    name: Optional[str] = None
    content: Optional[str] = None
    model_config_id: Optional[int] = None
    thinking: Optional[str] = None
    strength: Optional[str] = None
    enabled: Optional[int] = None


class CopyRefIn(BaseModel):
    ref_path: str


class SetActiveIn(BaseModel):
    menu: str
    function_key: str
    role: str
    rid: Optional[int] = None
    ref_path: Optional[str] = None


@router.get('/')
def list_ai_rules(menu: str = '', function_key: str = '', role: str = '', enabled: Optional[int] = None):
    return service.list_ai_rules(
        menu or None, function_key or None, role or None, enabled)


@router.post('/')
def create_ai_rule(req: AiRuleIn):
    try:
        return service.create_ai_rule(req.dict(exclude_unset=False))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get('/references')
def list_references():
    return service.list_reference_rules()


@router.post('/copy-reference')
def copy_reference(req: CopyRefIn):
    try:
        return service.copy_reference_to_db(req.ref_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put('/{rid}')
def update_ai_rule(rid: int, req: AiRuleUpdate):
    try:
        return service.update_ai_rule(rid, req.dict(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post('/{rid}/reset')
def reset_rule(rid: int):
    try:
        return service.reset_rule(rid)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete('/{rid}')
def delete_ai_rule(rid: int):
    try:
        service.delete_ai_rule(rid)
        return {'ok': True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post('/set-active')
def set_active(req: SetActiveIn):
    """把某条规则（或参考规则）设为指定 scope+role 下唯一启用的规则。"""
    try:
        return service.set_active_rule(
            req.menu, req.function_key, req.role, req.rid, req.ref_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
