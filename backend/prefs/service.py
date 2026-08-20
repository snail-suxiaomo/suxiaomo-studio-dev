"""prefs —— 用户偏好存储（通用）

职责：按「用户名 + 偏好键」存取 JSON 值，落库到用户数据根 app.db 的 user_prefs 表。
用途：跨会话/跨设备记住用户选择（如 AI 规则上次选中的规则快照）。
"""

from common import db


def get_pref(user_key: str, pref_key: str):
    """读取偏好，返回存储的 JSON 值（dict/list/str/number）或 None。"""
    if not user_key or not pref_key:
        return None
    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT pref_value FROM user_prefs WHERE user_key=? AND pref_key=?",
            (user_key, pref_key),
        ).fetchone()
    finally:
        conn.close()
    if not row or row["pref_value"] is None:
        return None
    import json
    try:
        return json.loads(row["pref_value"])
    except (ValueError, TypeError):
        return None


def set_pref(user_key: str, pref_key: str, value) -> None:
    """写入偏好（upsert）。value 为可 JSON 序列化的值。"""
    if not user_key or not pref_key:
        return
    import json
    text = json.dumps(value, ensure_ascii=False)
    conn = db.get_conn()
    try:
        conn.execute(
            """INSERT INTO user_prefs(user_key, pref_key, pref_value, updated_at)
               VALUES(?,?,?,datetime('now'))
               ON CONFLICT(user_key, pref_key)
               DO UPDATE SET pref_value=excluded.pref_value, updated_at=datetime('now')""",
            (user_key, pref_key, text),
        )
        conn.commit()
    finally:
        conn.close()


def del_pref(user_key: str, pref_key: str) -> None:
    """删除偏好（幂等）。"""
    if not user_key or not pref_key:
        return
    conn = db.get_conn()
    try:
        conn.execute(
            "DELETE FROM user_prefs WHERE user_key=? AND pref_key=?",
            (user_key, pref_key),
        )
        conn.commit()
    finally:
        conn.close()
