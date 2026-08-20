"""daily_tasks/service.py —— 每日任务 CRUD + 按登录日期完成状态

- daily_tasks：任务模板（名称 / 所属用户 / 操作软件 / 任务详情 / 登录账号 / 操作账号(多) / 账号统计 / 必做事情 / 日期）
- daily_task_completions：按「任务 + 日期」记录是否完成（每日登录重新判断，隔日自动重置）
"""

import json
from datetime import date

from common import db


def _conn():
    return db.get_conn()


def _today():
    return date.today().isoformat()


def _parse_accounts(v):
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if not v:
        return []
    try:
        a = json.loads(v)
        if isinstance(a, list):
            return [str(x).strip() for x in a if str(x).strip()]
    except Exception:
        pass
    # 兜底：逗号分隔
    return [x.strip() for x in str(v).split(',') if x.strip()]


def _dump_accounts(arr):
    return json.dumps(arr, ensure_ascii=False)


def _coerce_points(v):
    """积分数量：必须是非负整数。"""
    try:
        return max(0, int(v or 0))
    except Exception:
        return 0


def _coerce_mode(v):
    """清零方式：仅允许 cumulative / daily，其余回退到 cumulative。"""
    v = (v or 'cumulative')
    return v if v in ('cumulative', 'daily') else 'cumulative'


def _today_completed(conn, today):
    rows = conn.execute(
        "SELECT task_id FROM daily_task_completions WHERE comp_date=?", (today,)
    ).fetchall()
    return {r[0] for r in rows}


def list_items(owner=None, keyword=None, status='active'):
    sql = "SELECT * FROM daily_tasks WHERE 1=1"
    params = []
    if status and status != 'all':
        if status == 'active':
            sql += " AND (status IS NULL OR status='active')"
        else:
            sql += " AND status=?"
            params.append(status)
    if owner:
        sql += " AND owner LIKE ?"
        params.append(f'%{owner}%')
    if keyword:
        like = f'%{keyword}%'
        sql += (" AND (name LIKE ? OR detail LIKE ? OR software LIKE ? "
                "OR login_account LIKE ? OR must_do LIKE ? OR owner LIKE ?)")
        params.extend([like, like, like, like, like, like])
    sql += " ORDER BY sort_order ASC, id ASC"
    today = _today()
    conn = _conn()
    try:
        rows = conn.execute(sql, params).fetchall()
        items = [dict(r) for r in rows]
        done = _today_completed(conn, today)
        for it in items:
            it['operation_accounts'] = _parse_accounts(it['operation_accounts'])
            it['completed_today'] = it['id'] in done
        return items
    finally:
        conn.close()


def get_item(tid):
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM daily_tasks WHERE id=?", (tid,)).fetchone()
        if not row:
            return None
        it = dict(row)
        it['operation_accounts'] = _parse_accounts(it.get('operation_accounts'))
        it['completed_today'] = it['id'] in _today_completed(conn, _today())
        return it
    finally:
        conn.close()


def create_item(data):
    name = (data.get('name') or '').strip()
    if not name:
        raise ValueError('任务名称不能为空')
    detail = (data.get('detail') or '每日签到领积分').strip() or '每日签到领积分'
    owner = (data.get('owner') or '').strip() or None
    software = (data.get('software') or '').strip() or None
    login_account = (data.get('login_account') or '').strip() or None
    accounts = _parse_accounts(data.get('operation_accounts') or [])
    must_do = (data.get('must_do') or '').strip() or None
    link = (data.get('link') or '').strip() or None
    points = _coerce_points(data.get('points'))
    points_mode = _coerce_mode(data.get('points_mode'))
    conn = _conn()
    try:
        if conn.execute("SELECT 1 FROM daily_tasks WHERE name=?", (name,)).fetchone():
            raise ValueError('任务名称已存在')
        cur = conn.execute("SELECT COALESCE(MAX(sort_order),0)+1 FROM daily_tasks")
        sort_order = cur.fetchone()[0]
        cur = conn.execute(
            "INSERT INTO daily_tasks(name, owner, software, detail, login_account, operation_accounts, "
            "must_do, link, points, points_mode, task_date, sort_order, status) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (name, owner, software, detail, login_account, _dump_accounts(accounts),
             must_do, link, points, points_mode, (data.get('task_date') or None), sort_order, 'active'),
        )
        conn.commit()
        return get_item(cur.lastrowid)
    finally:
        conn.close()


def update_item(tid, data):
    existing = get_item(tid)
    if not existing:
        raise ValueError('任务不存在')
    name = (data.get('name') or '').strip()
    if not name:
        raise ValueError('任务名称不能为空')
    detail = (data.get('detail') or existing['detail']).strip() or existing['detail']
    owner = data.get('owner') if data.get('owner') is not None else existing.get('owner')
    owner = (owner or '').strip() or None
    software = data.get('software') if data.get('software') is not None else existing.get('software')
    software = (software or '').strip() or None
    login_account = data.get('login_account') if data.get('login_account') is not None else existing.get('login_account')
    login_account = (login_account or '').strip() or None
    accounts = _parse_accounts(data.get('operation_accounts') if data.get('operation_accounts') is not None else existing.get('operation_accounts'))
    must_do = data.get('must_do') if data.get('must_do') is not None else existing.get('must_do')
    must_do = (must_do or '').strip() or None
    link = data.get('link') if data.get('link') is not None else existing.get('link')
    link = (link or '').strip() or None
    task_date = (data.get('task_date') or None)
    points = _coerce_points(data.get('points') if data.get('points') is not None else existing.get('points'))
    points_mode = _coerce_mode(data.get('points_mode') if data.get('points_mode') is not None else existing.get('points_mode'))
    conn = _conn()
    try:
        if conn.execute("SELECT 1 FROM daily_tasks WHERE name=? AND id!=?", (name, tid)).fetchone():
            raise ValueError('任务名称已存在')
        conn.execute(
            "UPDATE daily_tasks SET name=?, owner=?, software=?, detail=?, login_account=?, "
            "operation_accounts=?, must_do=?, link=?, points=?, points_mode=?, task_date=?, "
            "updated_at=(datetime('now','localtime')) WHERE id=?",
            (name, owner, software, detail, login_account, _dump_accounts(accounts),
             must_do, link, points, points_mode, task_date, tid),
        )
        conn.commit()
        return get_item(tid)
    finally:
        conn.close()


def delete_item(tid):
    conn = _conn()
    try:
        conn.execute("DELETE FROM daily_tasks WHERE id=?", (tid,))
        conn.execute("DELETE FROM daily_task_completions WHERE task_id=?", (tid,))
        conn.commit()
    finally:
        conn.close()


def toggle_complete(tid, done):
    today = _today()
    conn = _conn()
    try:
        if done:
            conn.execute(
                "INSERT OR IGNORE INTO daily_task_completions(task_id, comp_date) VALUES(?,?)",
                (tid, today))
        else:
            conn.execute(
                "DELETE FROM daily_task_completions WHERE task_id=? AND comp_date=?",
                (tid, today))
        conn.commit()
        return done
    finally:
        conn.close()


def bulk_complete_all():
    """一键「全部完成」：仅对【激活中】且【未逾期】的任务生效。
    排除：已暂停(status='paused')、已逾期(task_date < 今天)。
    逾期/暂停任务需用户单独手动操作，避免误把过期或搁置的任务标记为完成。"""
    today = _today()
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT id FROM daily_tasks "
            "WHERE (status IS NULL OR status='active') "
            "AND (task_date IS NULL OR task_date >= ?)",
            (today,)
        ).fetchall()
        for r in rows:
            conn.execute(
                "INSERT OR IGNORE INTO daily_task_completions(task_id, comp_date) VALUES(?,?)",
                (r[0], today))
        conn.commit()
    finally:
        conn.close()


def bulk_reset_today():
    """清空今天的全部完成记录（重置今日）。隔日自动失效，此接口用于手动重置。"""
    today = _today()
    conn = _conn()
    try:
        conn.execute("DELETE FROM daily_task_completions WHERE comp_date=?", (today,))
        conn.commit()
    finally:
        conn.close()


def points_summary():
    """积分汇总（展示用，全部从现有完成记录推导，无需额外余额表）。

    - today_claimable：今日未完成任务的积分数之和（累加型与每日清空型均可今日领取）
    - cumulative_total：历史上所有 cumulative 任务完成记录对应的积分累计（永久不清零）
    - daily_today：今日已完成的 daily 任务积分之和（当日有效，隔日随完成记录清空而消失）
    """
    today = _today()
    conn = _conn()
    try:
        today_done = _today_completed(conn, today)
        # 今日可领 = 激活中、未逾期、且今日未完成的任务的积分之和
        claimable = conn.execute(
            "SELECT COALESCE(SUM(points),0) FROM daily_tasks "
            "WHERE (status IS NULL OR status='active') "
            "AND (task_date IS NULL OR task_date >= ?) "
            "AND id NOT IN (SELECT task_id FROM daily_task_completions WHERE comp_date=?)",
            (today, today),
        ).fetchone()[0]
        # 累计积分（永久）= 所有 cumulative 完成记录 × 对应任务积分
        cum = conn.execute(
            "SELECT COALESCE(SUM(t.points),0) FROM daily_task_completions c "
            "JOIN daily_tasks t ON t.id=c.task_id "
            "WHERE t.points_mode='cumulative'",
        ).fetchone()[0]
        # 今日已领（每日清空型）= 今天完成的 daily 任务积分
        daily_today = conn.execute(
            "SELECT COALESCE(SUM(t.points),0) FROM daily_task_completions c "
            "JOIN daily_tasks t ON t.id=c.task_id "
            "WHERE c.comp_date=? AND t.points_mode='daily'",
            (today,),
        ).fetchone()[0]
        return {
            'today_claimable': int(claimable),
            'cumulative_total': int(cum),
            'daily_today': int(daily_today),
            'today_done': len(today_done),
        }
    finally:
        conn.close()


def set_status(tid, status):
    """切换任务状态：active 激活 / paused 暂停（软隐藏，数据保留，可随时恢复）。"""
    if status not in ('active', 'paused'):
        raise ValueError('状态只能是 active 或 paused')
    conn = _conn()
    try:
        row = conn.execute("SELECT 1 FROM daily_tasks WHERE id=?", (tid,)).fetchone()
        if not row:
            raise ValueError('任务不存在')
        conn.execute(
            "UPDATE daily_tasks SET status=?, updated_at=(datetime('now','localtime')) WHERE id=?",
            (status, tid))
        conn.commit()
    finally:
        conn.close()


def reorder_items(order_ids):
    """按给定 id 顺序重排 sort_order（0..n-1）。忽略不存在的 id，缺失的追加到末尾。"""
    if not order_ids:
        return
    conn = _conn()
    try:
        existing = {r[0] for r in conn.execute("SELECT id FROM daily_tasks").fetchall()}
        ordered = [i for i in order_ids if i in existing]
        for i in existing:
            if i not in ordered:
                ordered.append(i)
        for idx, tid in enumerate(ordered):
            conn.execute("UPDATE daily_tasks SET sort_order=? WHERE id=?", (idx, tid))
        conn.commit()
    finally:
        conn.close()


def ensure_columns():
    """兼容旧库（无实际新列迁移需求，保留钩子）。表不存在时跳过，由 init_db() 的 schema SQL 负责建表。"""
    conn = _conn()
    try:
        # 表尚未建好（首次启动、import 早于 init_db）时直接跳过，避免 ALTER 报错拖垮整个进程
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='daily_tasks'"
        ).fetchone()
        if not row:
            return
        cols = {r[1] for r in conn.execute("PRAGMA table_info(daily_tasks)").fetchall()}
        adds = {
            'link': "ALTER TABLE daily_tasks ADD COLUMN link TEXT",
            'status': "ALTER TABLE daily_tasks ADD COLUMN status TEXT NOT NULL DEFAULT 'active'",
            'points': "ALTER TABLE daily_tasks ADD COLUMN points INTEGER NOT NULL DEFAULT 0",
            'points_mode': "ALTER TABLE daily_tasks ADD COLUMN points_mode TEXT NOT NULL DEFAULT 'cumulative'",
        }
        for col, ddl in adds.items():
            if col not in cols:
                conn.execute(ddl)
        conn.commit()
    finally:
        conn.close()


def drop_required_accounts():
    """一次性迁移：移除已废弃的 required_accounts 列（账号进度功能已删除）。
    用确定性的建表语句重建（排除该列），再搬回数据，保证类型/约束/数据完整。"""
    conn = _conn()
    try:
        names = {r[1] for r in conn.execute("PRAGMA table_info(daily_tasks)").fetchall()}
        if 'required_accounts' not in names:
            return
        create_sql = (
            "CREATE TABLE daily_tasks (\n"
            "  id                 INTEGER PRIMARY KEY AUTOINCREMENT,\n"
            "  name               TEXT    NOT NULL,\n"
            "  owner              TEXT,\n"
            "  software           TEXT,\n"
            "  detail             TEXT    NOT NULL DEFAULT '每日签到领积分',\n"
            "  login_account      TEXT,\n"
            "  operation_accounts TEXT    NOT NULL DEFAULT '[]',\n"
            "  must_do            TEXT,\n"
            "  link               TEXT,\n"
            "  points             INTEGER NOT NULL DEFAULT 0,\n"
            "  points_mode        TEXT    NOT NULL DEFAULT 'cumulative',\n"
            "  task_date          TEXT,\n"
            "  status             TEXT    NOT NULL DEFAULT 'active',\n"
            "  sort_order         INTEGER NOT NULL DEFAULT 0,\n"
            "  created_at         TEXT    NOT NULL DEFAULT (datetime('now','localtime')),\n"
            "  updated_at         TEXT    NOT NULL DEFAULT (datetime('now','localtime'))\n"
            ")"
        )
        col_list = ("id, name, owner, software, detail, login_account, operation_accounts, "
                    "must_do, link, task_date, status, sort_order, created_at, updated_at")
        conn.execute("ALTER TABLE daily_tasks RENAME TO daily_tasks_old")
        conn.execute(create_sql)
        conn.execute(f"INSERT INTO daily_tasks ({col_list}) SELECT {col_list} FROM daily_tasks_old")
        conn.execute("DROP TABLE daily_tasks_old")
        conn.commit()
    finally:
        conn.close()


# 先处理旧库遗留字段（required_accounts 重建），再补新列，保证两条迁移路径互不干扰
drop_required_accounts()
ensure_columns()
