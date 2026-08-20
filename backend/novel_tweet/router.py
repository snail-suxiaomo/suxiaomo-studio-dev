"""novel_tweet/router.py —— 小说推文 REST 接口
路由前缀 /novel-tweet：
- GET    /list                   列表（支持 novel_platform 分类 / keyword 搜索）
- GET    /meta                  筛选维度（已有的小说平台分类）
- GET    /{cid}                 详情（含 platforms 数组）
- POST   /                      新建（含嵌套 platforms 数组）
- PUT    /{cid}                 更新（含嵌套 platforms 数组，整体协调）
- DELETE /{cid}                 删除（级联删除平台）
- POST   /reorder               批量保存卡片顺序（拖拽排序后调用）
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from novel_tweet import service


router = APIRouter(prefix='/api/novel-tweet', tags=['novel_tweet'])


class PlatformIn(BaseModel):
    id: Optional[int] = None
    platform_name: str = ''
    application_date: str = ''
    publish_date: str = ''
    is_published_backfill: bool = False
    publish_accounts: str = ''
    publish_work_link: str = ''
    deadline_earnings: str = ''
    # 抖音账号 6 项（名称、ID、作品发布日期、作品链接、收益、备注）
    douyin_account_id: str = ''
    douyin_name: str = ''
    douyin_publish_date: str = ''
    douyin_link: str = ''
    douyin_earnings: str = ''
    douyin_remark: str = ''
    # B站账号 6 项
    bilibili_id: str = ''
    bilibili_name: str = ''
    bilibili_publish_date: str = ''
    bilibili_link: str = ''
    bilibili_earnings: str = ''
    bilibili_remark: str = ''
    # 快手账号 6 项
    kuaishou_id: str = ''
    kuaishou_name: str = ''
    kuaishou_publish_date: str = ''
    kuaishou_link: str = ''
    kuaishou_earnings: str = ''
    kuaishou_remark: str = ''
    # 其他平台账号 6 项
    other_name: str = ''
    other_id: str = ''
    other_publish_date: str = ''
    other_link: str = ''
    other_earnings: str = ''
    other_remark: str = ''
    # 视频号账号 6 项
    shipinhao_name: str = ''
    shipinhao_id: str = ''
    shipinhao_publish_date: str = ''
    shipinhao_link: str = ''
    shipinhao_earnings: str = ''
    shipinhao_remark: str = ''
    # 账号级是否发布回填（每个账号独立）
    douyin_is_published_backfill: bool = False
    bilibili_is_published_backfill: bool = False
    kuaishou_is_published_backfill: bool = False
    other_is_published_backfill: bool = False
    shipinhao_is_published_backfill: bool = False


class CampaignIn(BaseModel):
    name: str
    novel_platform: str = '其他'
    platform_type: str = 'web'
    original_novel_name: str = ''
    original_promotion_link: str = ''
    original_promotion_copy: str = ''
    optimized_copy: str = ''
    platforms: List[PlatformIn] = []


@router.get('/list')
def list_items(category: str = '全部', keyword: str = ''):
    return service.list_campaigns(category, keyword or None)


@router.get('/meta')
def get_meta():
    return service.meta()


@router.get('/{cid}')
def get_item(cid: int):
    row = service.get_campaign(cid)
    if not row:
        raise HTTPException(404, '推广活动不存在')
    return row


@router.post('/')
def create(req: CampaignIn):
    try:
        return service.create_campaign(req.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.put('/{cid}')
def update(cid: int, req: CampaignIn):
    try:
        return service.update_campaign(cid, req.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete('/{cid}')
def delete(cid: int):
    service.delete_campaign(cid)
    return {'ok': True}


class ReorderIn(BaseModel):
    ids: List[int]


@router.post('/reorder')
def reorder(req: ReorderIn):
    service.reorder(req.ids)
    return {'ok': True}
