"""novel_tweet/service.py —— 小说推文 CRUD

两张表：
- novel_tweet_campaign（推广活动：以推文关键词为基准，如「错嫁的小萤」）
- novel_tweet_platform（第三方推广平台：清风助手等，一个活动对应多个平台）

首页按 novel_platform 分类；推广活动与第三方平台一起保存（platforms 数组整体协调：
带 id 的更新、不带 id 的新增、客户端未发来的删除）。
"""

from common import db

DEFAULT_PLATFORMS = ['番茄', '知乎', '七猫', '盐言', '书旗', 'QQ阅读', '起点', '其他']

# 账号名 -> 字段 key 映射（用于账号级回填统计）
ACCOUNT_NAME_TO_KEY = {'抖音': 'douyin', '快手': 'kuaishou', 'B站': 'bilibili', '视频号': 'shipinhao', '其他平台': 'other'}


def _calc_backfill(platforms):
    """统计某推广下所有（平台×账号）的回填情况：返回 (已回填账号数, 总发布账号数)。

    账号级回填字段（douyin/kuaishou/..._is_published_backfill）存在即以它为准；
    仅当该字段缺失（旧数据无此列）才回退到平台级 is_published_backfill。
    注意：账号级字段为 0(未回填) 是有意义的真实值，不能当作“缺失”回退。
    """
    done = total = 0
    for p in platforms:
        accs = [a.strip() for a in (p.get('publish_accounts') or '').split(',') if a.strip()]
        for a in accs:
            key = ACCOUNT_NAME_TO_KEY.get(a)
            if not key:
                continue
            total += 1
            bf = p.get(f'{key}_is_published_backfill')
            if bf is None:  # 仅字段缺失时回退平台级；0/1 均直接使用
                bf = p.get('is_published_backfill')
            if bf:
                done += 1
    return done, total


def _conn():
    return db.get_conn()


# ---------- 列表 / 筛选维度 ----------

def list_campaigns(category='全部', keyword=None):
    where = ""
    params = []
    if category and category != '全部':
        where += " AND c.novel_platform=?"
        params.append(category)
    if keyword:
        like = f'%{keyword}%'
        where += (" AND (c.name LIKE ? OR c.novel_platform LIKE ? OR c.original_novel_name LIKE ? "
                  "OR c.original_promotion_link LIKE ? OR c.original_promotion_copy LIKE ? "
                  "OR c.optimized_copy LIKE ?)")
        params.extend([like, like, like, like, like, like])
    order = " ORDER BY COALESCE(c.sort_order, 99999999), c.updated_at DESC, c.id DESC"
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT c.* FROM novel_tweet_campaign c WHERE 1=1" + where + order, params
        ).fetchall()
        # 一次性拉取全部第三方平台，按 campaign_id 分组到内存聚合，消除列表 N+1 查询
        pls = conn.execute(
            "SELECT campaign_id, publish_accounts, is_published_backfill, "
            "douyin_is_published_backfill, bilibili_is_published_backfill, "
            "kuaishou_is_published_backfill, other_is_published_backfill, shipinhao_is_published_backfill, "
            "platform_name FROM novel_tweet_platform"
        ).fetchall()
        grouped = {}
        for p in pls:
            grouped.setdefault(p['campaign_id'], []).append(dict(p))
        result = []
        for r in rows:
            d = dict(r)
            camp_pls = grouped.get(d['id'], [])
            done, total = _calc_backfill(camp_pls)
            d['backfill_done'] = done
            d['backfill_total'] = total
            d['platform_count'] = len(camp_pls)
            d['has_platform'] = 1 if camp_pls else 0
            # 聚合发布账号（按账号去重，避免跨平台整串去重吞掉账号）与第三方平台名
            acc_seen, acc_list = set(), []
            names = []
            for p in camp_pls:
                for a in (p.get('publish_accounts') or '').split(','):
                    a = a.strip()
                    if a and a not in acc_seen:
                        acc_seen.add(a)
                        acc_list.append(a)
                nm = (p.get('platform_name') or '').strip()
                if nm and nm not in names:
                    names.append(nm)
            d['publish_accounts'] = ','.join(acc_list)
            d['platform_names'] = ','.join(names)
            result.append(d)
        return result
    finally:
        conn.close()


def meta():
    conn = _conn()
    try:
        user_cats = set(r[0] for r in conn.execute(
            "SELECT DISTINCT novel_platform FROM novel_tweet_campaign "
            "WHERE novel_platform IS NOT NULL AND novel_platform<>''"
        ).fetchall())
        # 默认平台始终显示；用户自建平台追加到末尾并去重
        custom = sorted(user_cats - set(DEFAULT_PLATFORMS))
        cats = list(dict.fromkeys([*DEFAULT_PLATFORMS, *custom]))
        return {'categories': cats}
    finally:
        conn.close()


# ---------- 详情 ----------

def get_campaign(cid):
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT * FROM novel_tweet_campaign WHERE id=?", (cid,)).fetchone()
        if not row:
            return None
        rec = dict(row)
        pls = conn.execute(
            "SELECT * FROM novel_tweet_platform WHERE campaign_id=? "
            "ORDER BY COALESCE(sort_order, 99999999), id ASC", (cid,)).fetchall()
        rec['platforms'] = [dict(p) for p in pls]
        return rec
    finally:
        conn.close()


# ---------- 写入：推广活动 + 第三方平台 ----------

PLATFORM_FIELDS = [
    'platform_name', 'application_date', 'publish_date', 'is_published_backfill',
    'douyin_is_published_backfill', 'bilibili_is_published_backfill',
    'kuaishou_is_published_backfill', 'other_is_published_backfill', 'shipinhao_is_published_backfill',
    'publish_accounts', 'publish_work_link', 'deadline_earnings',
    # 抖音账号 6 项（名称、ID、作品发布日期、作品链接、收益、备注）
    'douyin_account_id', 'douyin_name', 'douyin_publish_date', 'douyin_link', 'douyin_earnings', 'douyin_remark',
    # B站账号 6 项
    'bilibili_id', 'bilibili_name', 'bilibili_publish_date', 'bilibili_link', 'bilibili_earnings', 'bilibili_remark',
    # 快手账号 6 项
    'kuaishou_id', 'kuaishou_name', 'kuaishou_publish_date', 'kuaishou_link', 'kuaishou_earnings', 'kuaishou_remark',
    # 其他平台账号 6 项
    'other_name', 'other_id', 'other_publish_date', 'other_link', 'other_earnings', 'other_remark',
    # 视频号账号 6 项
    'shipinhao_name', 'shipinhao_id', 'shipinhao_publish_date', 'shipinhao_link', 'shipinhao_earnings', 'shipinhao_remark',
]


def _platform_clean(p):
    out = {}
    for f in PLATFORM_FIELDS:
        v = p.get(f, '')
        if f == 'is_published_backfill' or f.endswith('_is_published_backfill'):
            out[f] = 1 if v else 0
        else:
            out[f] = '' if v is None else str(v)
    return out


def create_campaign(data):
    name = (data.get('name') or '').strip()
    if not name:
        raise ValueError('推文名称不能为空')
    novel_platform = (data.get('novel_platform') or '其他').strip() or '其他'
    platform_type = data.get('platform_type') or 'web'
    if platform_type not in ('web', 'app', 'mini_program'):
        platform_type = 'web'
    conn = _conn()
    try:
        cur = conn.execute(
            "INSERT INTO novel_tweet_campaign"
            "(name, novel_platform, platform_type, original_novel_name, original_promotion_link, "
            "original_promotion_copy, optimized_copy) VALUES(?,?,?,?,?,?,?)",
            (name, novel_platform, platform_type,
             data.get('original_novel_name', '') or '',
             data.get('original_promotion_link', '') or '',
             data.get('original_promotion_copy', '') or '',
             data.get('optimized_copy', '') or ''))
        cid = cur.lastrowid
        _save_platforms(conn, cid, data.get('platforms', []))
        conn.commit()
        return get_campaign(cid)
    finally:
        conn.close()


def update_campaign(cid, data):
    existing = get_campaign(cid)
    if not existing:
        raise ValueError('推广活动不存在')
    name = (data.get('name') or '').strip()
    if not name:
        raise ValueError('推文名称不能为空')
    novel_platform = (data.get('novel_platform') or existing['novel_platform']).strip() or '其他'
    platform_type = data.get('platform_type') or existing['platform_type']
    if platform_type not in ('web', 'app', 'mini_program'):
        platform_type = existing['platform_type']
    conn = _conn()
    try:
        conn.execute(
            "UPDATE novel_tweet_campaign SET name=?, novel_platform=?, platform_type=?, "
            "original_novel_name=?, original_promotion_link=?, original_promotion_copy=?, "
            "optimized_copy=?, updated_at=(datetime('now','localtime')) WHERE id=?",
            (name, novel_platform, platform_type,
             data.get('original_novel_name', '') or '',
             data.get('original_promotion_link', '') or '',
             data.get('original_promotion_copy', '') or '',
             data.get('optimized_copy', '') or '',
             cid))
        _save_platforms(conn, cid, data.get('platforms', []), existing_platforms=existing['platforms'])
        conn.commit()
        return get_campaign(cid)
    finally:
        conn.close()


def _save_platforms(conn, cid, platforms, existing_platforms=None):
    """协调第三方平台：带 id 更新、不带 id 新增；客户端未发来的（带 id 的）删除。"""
    platforms = platforms or []
    incoming_ids = set()
    for i, p in enumerate(platforms):
        clean = _platform_clean(p)
        sort_order = (i + 1) * 10
        pid = p.get('id')
        if pid:
            incoming_ids.add(int(pid))
            conn.execute(
                "UPDATE novel_tweet_platform SET platform_name=?, application_date=?, publish_date=?, "
                "is_published_backfill=?, douyin_is_published_backfill=?, bilibili_is_published_backfill=?, "
                "kuaishou_is_published_backfill=?, other_is_published_backfill=?, shipinhao_is_published_backfill=?, "
                "publish_accounts=?, publish_work_link=?, "
                "deadline_earnings=?, "
                "douyin_account_id=?, douyin_name=?, douyin_publish_date=?, douyin_link=?, douyin_earnings=?, douyin_remark=?, "
                "bilibili_id=?, bilibili_name=?, bilibili_publish_date=?, bilibili_link=?, bilibili_earnings=?, bilibili_remark=?, "
                "kuaishou_id=?, kuaishou_name=?, kuaishou_publish_date=?, kuaishou_link=?, kuaishou_earnings=?, kuaishou_remark=?, "
                "other_name=?, other_id=?, other_publish_date=?, other_link=?, other_earnings=?, other_remark=?, "
                "shipinhao_name=?, shipinhao_id=?, shipinhao_publish_date=?, shipinhao_link=?, shipinhao_earnings=?, shipinhao_remark=?, "
                "sort_order=?, updated_at=(datetime('now','localtime')) WHERE id=?",
                (clean['platform_name'], clean['application_date'], clean['publish_date'], clean['is_published_backfill'],
                 clean['douyin_is_published_backfill'], clean['bilibili_is_published_backfill'],
                 clean['kuaishou_is_published_backfill'], clean['other_is_published_backfill'], clean['shipinhao_is_published_backfill'],
                 clean['publish_accounts'], clean['publish_work_link'], clean['deadline_earnings'],
                 clean['douyin_account_id'], clean['douyin_name'], clean['douyin_publish_date'], clean['douyin_link'],
                 clean['douyin_earnings'], clean['douyin_remark'],
                 clean['bilibili_id'], clean['bilibili_name'], clean['bilibili_publish_date'], clean['bilibili_link'],
                 clean['bilibili_earnings'], clean['bilibili_remark'],
                 clean['kuaishou_id'], clean['kuaishou_name'], clean['kuaishou_publish_date'], clean['kuaishou_link'],
                 clean['kuaishou_earnings'], clean['kuaishou_remark'],
                 clean['other_name'], clean['other_id'], clean['other_publish_date'], clean['other_link'],
                 clean['other_earnings'], clean['other_remark'],
                 clean['shipinhao_name'], clean['shipinhao_id'], clean['shipinhao_publish_date'], clean['shipinhao_link'],
                 clean['shipinhao_earnings'], clean['shipinhao_remark'],
                 sort_order, int(pid)))
        else:
            cur = conn.execute(
                "INSERT INTO novel_tweet_platform"
                "(campaign_id, platform_name, application_date, publish_date, is_published_backfill, "
                "douyin_is_published_backfill, bilibili_is_published_backfill, "
                "kuaishou_is_published_backfill, other_is_published_backfill, shipinhao_is_published_backfill, "
                "publish_accounts, publish_work_link, deadline_earnings, "
                "douyin_account_id, douyin_name, douyin_publish_date, douyin_link, douyin_earnings, douyin_remark, "
                "bilibili_id, bilibili_name, bilibili_publish_date, bilibili_link, bilibili_earnings, bilibili_remark, "
                "kuaishou_id, kuaishou_name, kuaishou_publish_date, kuaishou_link, kuaishou_earnings, kuaishou_remark, "
                "other_name, other_id, other_publish_date, other_link, other_earnings, other_remark, "
                "shipinhao_name, shipinhao_id, shipinhao_publish_date, shipinhao_link, shipinhao_earnings, shipinhao_remark, sort_order) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, clean['platform_name'], clean['application_date'], clean['publish_date'], clean['is_published_backfill'],
                 clean['douyin_is_published_backfill'], clean['bilibili_is_published_backfill'],
                 clean['kuaishou_is_published_backfill'], clean['other_is_published_backfill'], clean['shipinhao_is_published_backfill'],
                 clean['publish_accounts'], clean['publish_work_link'], clean['deadline_earnings'],
                 clean['douyin_account_id'], clean['douyin_name'], clean['douyin_publish_date'], clean['douyin_link'],
                 clean['douyin_earnings'], clean['douyin_remark'],
                 clean['bilibili_id'], clean['bilibili_name'], clean['bilibili_publish_date'], clean['bilibili_link'],
                 clean['bilibili_earnings'], clean['bilibili_remark'],
                 clean['kuaishou_id'], clean['kuaishou_name'], clean['kuaishou_publish_date'], clean['kuaishou_link'],
                 clean['kuaishou_earnings'], clean['kuaishou_remark'],
                 clean['other_name'], clean['other_id'], clean['other_publish_date'], clean['other_link'],
                 clean['other_earnings'], clean['other_remark'],
                 clean['shipinhao_name'], clean['shipinhao_id'], clean['shipinhao_publish_date'], clean['shipinhao_link'],
                 clean['shipinhao_earnings'], clean['shipinhao_remark'], sort_order))
            incoming_ids.add(cur.lastrowid)
    # 删除客户端未发来的平台
    if existing_platforms is not None:
        existing_ids = {int(p['id']) for p in existing_platforms}
        for del_id in (existing_ids - incoming_ids):
            conn.execute("DELETE FROM novel_tweet_platform WHERE id=?", (del_id,))


def delete_campaign(cid):
    conn = _conn()
    try:
        conn.execute("DELETE FROM novel_tweet_platform WHERE campaign_id=?", (cid,))
        conn.execute("DELETE FROM novel_tweet_campaign WHERE id=?", (cid,))
        conn.commit()
    finally:
        conn.close()


def reorder(ids):
    conn = _conn()
    try:
        for i, cid in enumerate(ids):
            conn.execute(
                "UPDATE novel_tweet_campaign SET sort_order=? WHERE id=?",
                (i, int(cid)))
        conn.commit()
    finally:
        conn.close()
