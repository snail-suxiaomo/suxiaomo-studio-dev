"""novel_memory/service.py —— 直接写 SQL 操作 project_memory 表（无引擎）

职责：
- save_draft：供 13 个功能在生成完每章后调用，自动把摘要存为 draft（upsert，不覆盖已确认的）
- list_memory：按项目(+功能/章节)列出记忆
- create_memory / update_memory / delete_memory：界面手动增改删

schema 在 data/schema/novel_memory.sql，本文件只负责读写字，不拥有表结构。
"""
import json
from common import db


def _dump(obj):
    """把 dict/None 转成可存 TEXT 的形式（dict→JSON 串，None→None）"""
    if obj is None:
        return None
    if isinstance(obj, str):
        return obj
    return json.dumps(obj, ensure_ascii=False)


def _load(text):
    """读出来时把 JSON 串还原成 dict（空/None→None）"""
    if not text:
        return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


# ---------- 自动写入（13 功能调用） ----------

def save_draft(project_id, function_id, chapter_idx, summary, key_data=None):
    """功能生成完某章后自动调用：确保存在一条该章该功能的 draft 且摘要最新。

    - 无记录 → 插入 draft
    - 已有 draft → 覆盖 summary（保留该记录的 id / status）
    - 已 confirmed → 不覆盖（尊重人工确认，自动写入跳过）
    """
    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT id, status FROM project_memory "
            "WHERE project_id=? AND function_id=? AND chapter_idx=? "
            "ORDER BY id DESC LIMIT 1",
            (project_id, function_id, chapter_idx),
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO project_memory"
                "(project_id, function_id, chapter_idx, summary, key_data, status) "
                "VALUES(?, ?, ?, ?, ?, 'draft')",
                (project_id, function_id, chapter_idx, summary or "", _dump(key_data)),
            )
        elif row["status"] == "draft":
            conn.execute(
                "UPDATE project_memory "
                "SET summary=?, key_data=?, updated_at=datetime('now','localtime') "
                "WHERE id=?",
                (summary or "", _dump(key_data), row["id"]),
            )
        # 已 confirmed 则保留，不覆盖
        conn.commit()
    finally:
        conn.close()


# ---------- 界面手动增改查删 ----------

def list_memory(project_id, function_id=None, chapter_idx=None):
    """列出某项目的记忆（可按功能/章节过滤），按章号、id 升序"""
    conn = db.get_conn()
    try:
        sql = "SELECT * FROM project_memory WHERE project_id=?"
        args = [project_id]
        if function_id:
            sql += " AND function_id=?"
            args.append(function_id)
        if chapter_idx is not None:
            sql += " AND chapter_idx=?"
            args.append(chapter_idx)
        sql += " ORDER BY chapter_idx ASC, id ASC"
        rows = conn.execute(sql, args).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def create_memory(project_id, function_id, chapter_idx, summary, status="draft", key_data=None):
    """手动新增一条记忆（允许同章多条）"""
    if status not in ("draft", "confirmed"):
        raise ValueError("status 只能是 draft 或 confirmed")
    conn = db.get_conn()
    try:
        conn.execute(
            "INSERT INTO project_memory"
            "(project_id, function_id, chapter_idx, summary, key_data, status) "
            "VALUES(?, ?, ?, ?, ?, ?)",
            (project_id, function_id, chapter_idx, summary or "", _dump(key_data), status),
        )
        conn.commit()
        rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return get_memory(rid)
    finally:
        conn.close()


def get_memory(memory_id):
    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM project_memory WHERE id=?", (memory_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def update_memory(memory_id, summary=None, status=None, key_data=None):
    """修改一条记忆（摘要 / 状态 / 结构化数据）"""
    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM project_memory WHERE id=?", (memory_id,)
        ).fetchone()
        if not row:
            raise RuntimeError("记忆不存在")
        if summary is not None:
            conn.execute(
                "UPDATE project_memory SET summary=? WHERE id=?", (summary, memory_id)
            )
        if status is not None:
            if status not in ("draft", "confirmed"):
                raise ValueError("status 只能是 draft 或 confirmed")
            conn.execute(
                "UPDATE project_memory SET status=? WHERE id=?", (status, memory_id)
            )
        if key_data is not None:
            conn.execute(
                "UPDATE project_memory SET key_data=? WHERE id=?",
                (_dump(key_data), memory_id),
            )
        conn.execute(
            "UPDATE project_memory SET updated_at=datetime('now','localtime') WHERE id=?",
            (memory_id,),
        )
        conn.commit()
        return get_memory(memory_id)
    finally:
        conn.close()


def delete_memory(memory_id):
    conn = db.get_conn()
    try:
        conn.execute("DELETE FROM project_memory WHERE id=?", (memory_id,))
        conn.commit()
    finally:
        conn.close()


def _row_to_dict(r):
    return {
        "id": r["id"],
        "project_id": r["project_id"],
        "function_id": r["function_id"],
        "chapter_idx": r["chapter_idx"],
        "summary": r["summary"],
        "key_data": _load(r["key_data"]),
        "status": r["status"],
        "created_at": r["created_at"],
        "updated_at": r["updated_at"],
    }
