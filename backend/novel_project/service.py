"""novel_project/service.py —— 直接写 SQL 操作 novel_project 表（无引擎）

职责：项目管理（增删改查 + 归档）。schema 在 data/schema/novel_project.sql，
本文件只负责读写字，不拥有表结构。
"""

from common import db


def list_projects():
    """列出全部项目（最新在前）"""
    conn = db.get_conn()
    try:
        return conn.execute(
            "SELECT * FROM novel_project ORDER BY id DESC"
        ).fetchall()
    finally:
        conn.close()


def get_project(pid):
    conn = db.get_conn()
    try:
        return conn.execute(
            "SELECT * FROM novel_project WHERE id = ?", (pid,)
        ).fetchone()
    finally:
        conn.close()


def create_project(name, description=None):
    """新建项目；同名则报错。创建 DB 记录 + 生成全管线目录。"""
    conn = db.get_conn()
    try:
        conn.execute(
            "INSERT INTO novel_project(name, description) VALUES(?, ?)",
            (name, description),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM novel_project WHERE name = ?", (name,)
        ).fetchone()
        # 生成全管线目录（00-拆分/小说原文 到 12-分镜）
        _ensure_project_dirs(name)
        return row
    except Exception:
        raise RuntimeError(f"项目名「{name}」已存在")
    finally:
        conn.close()


def _ensure_project_dirs(project_name: str):
    """创建项目下所有管线目录，已有不覆盖。"""
    subdirs = [
        "00-拆分/小说原文",
        "01-梗概", "02-图谱", "03-诊断", "04-策略", "05-总表",
        "06-改写", "07-去重", "08-精要", "09-剧本",
        "10-资产", "11-分卷", "12-分镜",
    ]
    root = db.PROJECTS_DIR / project_name
    for d in subdirs:
        (root / d).mkdir(parents=True, exist_ok=True)


def delete_project(pid):
    """删除项目记录（注意：不删 projects/<name>/ 下的文件，留给用户决定）"""
    conn = db.get_conn()
    try:
        conn.execute("DELETE FROM novel_project WHERE id = ?", (pid,))
        conn.commit()
    finally:
        conn.close()


def set_status(pid, status):
    conn = db.get_conn()
    try:
        conn.execute(
            "UPDATE novel_project SET status = ?, updated_at = datetime('now') "
            "WHERE id = ?",
            (status, pid),
        )
        conn.commit()
    finally:
        conn.close()
