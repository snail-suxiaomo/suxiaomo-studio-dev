"""chat/service.py —— AI 聊天 + 会话持久化

- ask()：调模型（复用 common/ai.chat）。带上 session_id 时自动落库（用户消息+助手消息）、
  并从 DB 重建历史上下文，让「重开旧会话继续聊」模型也能听懂前因。
- 会话/消息 CRUD：create/list/get/rename/delete + 附件落盘与读取。
"""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import uuid

from common import db
from common import ai

# 附件根目录：数据目录/chat_attachments/{session_id}/
# 真实文件落磁盘，DB 只存相对路径元信息；随数据目录走，打包绝不带走。
ATTACH_DIR = db.DATA_DIR / "chat_attachments"


def _row_to_dict(row):
    return dict(row)


# ---------------- 会话 CRUD ----------------
def create_session(model_config_id=None, title="新会话"):
    conn = db.get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO chat_session(title, model_config_id) VALUES(?, ?)",
            (title, model_config_id),
        )
        conn.commit()
        sid = cur.lastrowid
        row = conn.execute("SELECT * FROM chat_session WHERE id=?", (sid,)).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def list_sessions(model_config_id=None):
    conn = db.get_conn()
    try:
        if model_config_id:
            rows = conn.execute(
                "SELECT * FROM chat_session WHERE model_config_id=? ORDER BY updated_at DESC, id DESC",
                (model_config_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM chat_session ORDER BY updated_at DESC, id DESC"
            ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_session(session_id):
    conn = db.get_conn()
    try:
        row = conn.execute("SELECT * FROM chat_session WHERE id=?", (session_id,)).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def list_messages(session_id):
    conn = db.get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM chat_message WHERE session_id=? ORDER BY id ASC", (session_id,)
        ).fetchall()
        out = []
        for r in rows:
            d = _row_to_dict(r)
            d["images"] = json.loads(d["images"] or "[]")
            d["texts"] = json.loads(d["texts"] or "[]")
            out.append(d)
        return out
    finally:
        conn.close()


def rename_session(session_id, title):
    conn = db.get_conn()
    try:
        conn.execute(
            "UPDATE chat_session SET title=?, updated_at=datetime('now','localtime') WHERE id=?",
            (title, session_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_session(session_id):
    conn = db.get_conn()
    try:
        conn.execute("DELETE FROM chat_message WHERE session_id=?", (session_id,))
        conn.execute("DELETE FROM chat_session WHERE id=?", (session_id,))
        conn.commit()
    finally:
        conn.close()
    d = ATTACH_DIR / str(session_id)
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)


def open_session_folder(session_id):
    """打开该会话的附件目录（没有则先创建空目录）。"""
    d = ATTACH_DIR / str(session_id)
    d.mkdir(parents=True, exist_ok=True)
    path = str(d.resolve())
    if sys.platform == 'win32':
        os.startfile(path)
    elif sys.platform == 'darwin':
        subprocess.Popen(['open', path])
    else:
        subprocess.Popen(['xdg-open', path])
    return {"ok": True, "path": path}


# ---------------- 附件 ----------------
def _save_attachment(session_id, upload_file, kind):
    """把上传文件存到磁盘，返回元信息 dict（DB 只存这个）。"""
    ATTACH_DIR.mkdir(parents=True, exist_ok=True)
    sess_dir = ATTACH_DIR / str(session_id)
    sess_dir.mkdir(parents=True, exist_ok=True)
    raw = upload_file.file.read()
    upload_file.file.close()
    ext = os.path.splitext(upload_file.filename)[1] or ""
    stored = uuid.uuid4().hex + ext
    with open(sess_dir / stored, "wb") as f:
        f.write(raw)
    return {
        "type": kind,
        "name": upload_file.filename,
        "stored": stored,
        "rel": f"chat_attachments/{session_id}/{stored}",
        "mime": upload_file.content_type or "application/octet-stream",
        "size": len(raw),
    }


class _SavedFile:
    """给 ai._build_messages 用的 UploadFile 替身：从已落盘文件读字节。"""

    def __init__(self, path, filename, content_type):
        self.path = str(path)
        self.filename = filename
        self.content_type = content_type

    @property
    def file(self):
        return open(self.path, "rb")


def attachment_path(session_id, filename):
    """解析附件绝对路径（防目录穿越）。不存在返回 None。"""
    base = (ATTACH_DIR / str(session_id)).resolve()
    path = (base / filename).resolve()
    if not str(path).startswith(str(base)):
        return None
    return path if path.exists() else None


# ---------------- 历史上下文 ----------------
def _history(session_id, before_message_id=None):
    """读历史消息（文本），拼成 [{role, content}]。可排除某条之后的。"""
    conn = db.get_conn()
    try:
        if before_message_id:
            rows = conn.execute(
                "SELECT role, content FROM chat_message WHERE session_id=? AND id<? ORDER BY id ASC",
                (session_id, before_message_id),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT role, content FROM chat_message WHERE session_id=? ORDER BY id ASC",
                (session_id,),
            ).fetchall()
        return [{"role": r["role"], "content": r["content"] or ""} for r in rows]
    finally:
        conn.close()


# ---------------- 发消息（可选落库） ----------------
def ask(prompt, system_prompt=None, images=None, texts=None, model_config_id=None,
        thinking=None, reasoning_effort=None, session_id=None):
    """把提示词交给模型，拿到回复。带 session_id 时落库 + 重建历史上下文。"""
    if not session_id:
        # 旧行为：无会话，不持久化、不带历史
        reply = ai.chat(prompt, system_prompt=system_prompt, images=images, texts=texts,
                        model_config_id=model_config_id, thinking=thinking,
                        reasoning_effort=reasoning_effort, with_reasoning=True)
        if isinstance(reply, dict):
            return {"reply": reply.get("content", ""), "reasoning": reply.get("reasoning", ""), "error": None}
        return {"reply": reply, "reasoning": "", "error": None}

    # 1) 落盘用户消息（含附件）
    user_imgs_meta, user_texts_meta = [], []
    send_images = send_texts = None
    if images:
        send_images = []
        for f in images:
            meta = _save_attachment(session_id, f, "image")
            user_imgs_meta.append(meta)
            send_images.append(_SavedFile(ATTACH_DIR / str(session_id) / meta["stored"], meta["name"], meta["mime"]))
    if texts:
        send_texts = []
        for f in texts:
            meta = _save_attachment(session_id, f, "text")
            user_texts_meta.append(meta)
            send_texts.append(_SavedFile(ATTACH_DIR / str(session_id) / meta["stored"], meta["name"], meta["mime"]))

    conn = db.get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO chat_message(session_id, role, content, images, texts) VALUES(?, 'user', ?, ?, ?)",
            (session_id, prompt or "（仅附件）",
             json.dumps(user_imgs_meta, ensure_ascii=False),
             json.dumps(user_texts_meta, ensure_ascii=False)),
        )
        conn.commit()
        user_msg_id = cur.lastrowid
    finally:
        conn.close()

    # 2) 历史上下文（该用户消息之前的所有消息）
    history = _history(session_id, before_message_id=user_msg_id)

    # 3) 调模型
    try:
        reply = ai.chat(prompt, system_prompt=system_prompt, images=send_images, texts=send_texts,
                        model_config_id=model_config_id, thinking=thinking,
                        reasoning_effort=reasoning_effort, with_reasoning=True, history=history)
    except Exception as e:
        # 落库一条出错占位，历史里能看到这次失败
        conn = db.get_conn()
        try:
            conn.execute(
                "INSERT INTO chat_message(session_id, role, content, is_error) VALUES(?, 'assistant', ?, 1)",
                (session_id, f"调用失败：{e}"),
            )
            conn.execute("UPDATE chat_session SET updated_at=datetime('now','localtime') WHERE id=?", (session_id,))
            conn.commit()
        finally:
            conn.close()
        return {"reply": None, "reasoning": "", "error": str(e)}

    if isinstance(reply, dict):
        content, reasoning = reply.get("content", ""), reply.get("reasoning", "")
    else:
        content, reasoning = reply, ""

    # 4) 落库助手消息 + 首条自动标题
    conn = db.get_conn()
    try:
        conn.execute(
            "INSERT INTO chat_message(session_id, role, content, reasoning) VALUES(?, 'assistant', ?, ?)",
            (session_id, content, reasoning),
        )
        row = conn.execute("SELECT title FROM chat_session WHERE id=?", (session_id,)).fetchone()
        if row and (row["title"] == "新会话" or not row["title"]):
            t = (prompt or "（仅附件）").strip().replace("\n", " ")
            t = t[:30] if t else "新会话"
            conn.execute("UPDATE chat_session SET title=?, updated_at=datetime('now','localtime') WHERE id=?", (t, session_id))
        else:
            conn.execute("UPDATE chat_session SET updated_at=datetime('now','localtime') WHERE id=?", (session_id,))
        conn.commit()
    finally:
        conn.close()

    return {"reply": content, "reasoning": reasoning, "error": None}
