"""usage_intro/router.py —— 使用介绍后端接口

路由前缀 /api/usage-intro：
- GET /info  返回当前版本、数据根等基础信息（供使用介绍页展示）
"""

import os
from pathlib import Path
from fastapi import APIRouter

from common import db

router = APIRouter(prefix='/api/usage-intro', tags=['usage_intro'])


@router.get('/info')
def usage_info():
    """返回软件版本、数据目录等使用介绍页可能引用的基础信息。"""
    data_root = Path(db.DATA_ROOT).resolve().as_posix() if hasattr(db, 'DATA_ROOT') else ''
    return {
        'ok': True,
        'data_root': data_root,
        'packaged': os.environ.get('SUXIAOMO_PACKAGED') == '1',
    }
