"""login/service.py —— 登录的业务逻辑（py 直接写 SQL 操作 users 表）

不做任何「通用引擎」的事：只管自己的用户表，自己拼 SQL。
"""

import re

from common import db, security, crypto_pwd

# 账号规则：字母开头，仅含英文与数字，长度 2-20
ACCOUNT_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9]{1,19}$')


def get_user_by_username(username):
    conn = db.get_conn()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
    finally:
        conn.close()


def get_user_by_id(uid):
    conn = db.get_conn()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE id = ?", (uid,)
        ).fetchone()
    finally:
        conn.close()


def register(username, password, display_name=None):
    """注册新用户；账号格式非法或重复返回 (None, 错误信息)"""
    if not ACCOUNT_RE.match(username or ''):
        return None, "账号须为字母开头、仅含英文与数字，长度 2-20"
    conn = db.get_conn()
    try:
        if conn.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone():
            return None, "账号已存在"
        h = security.hash_password(password)
        conn.execute(
            "INSERT INTO users(username, password_hash, display_name) VALUES(?, ?, ?)",
            (username, h, display_name or username),
        )
        conn.commit()
        return get_user_by_username(username), None
    finally:
        conn.close()


def authenticate(username, password):
    """校验用户名+密码；不对返回 None"""
    u = get_user_by_username(username)
    if not u or not security.verify_password(password, u["password_hash"]):
        return None
    return u


def create_token(user) -> str:
    return security.create_token(user)


def ensure_seed_admin():
    """首次启动、users 为空时，插一条管理员（admin / admin），可在 SQL 工具里改"""
    conn = db.get_conn()
    try:
        cnt = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        if cnt == 0:
            h = security.hash_password("admin")
            conn.execute(
                "INSERT INTO users(username, password_hash, display_name) VALUES(?, ?, ?)",
                ("admin", h, "管理员"),
            )
            conn.commit()
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────
# 记住的账号（多账号下拉 / 记住密码 / 自动登录）
# 密码只存 safeStorage 加密后的密文，绝不存明文。
# ─────────────────────────────────────────────────────────────

def list_remembered_accounts():
    """返回记住的账号列表（不含密码密文），按最后登录时间倒序"""
    conn = db.get_conn()
    try:
        rows = conn.execute(
            "SELECT id, username, remember_password, auto_login, last_login_at "
            "FROM remembered_accounts ORDER BY last_login_at IS NULL, last_login_at DESC, id DESC"
        ).fetchall()
        return [
            {
                "id": r["id"],
                "username": r["username"],
                "remember_password": bool(r["remember_password"]),
                "auto_login": bool(r["auto_login"]),
                "last_login_at": r["last_login_at"],
            }
            for r in rows
        ]
    finally:
        conn.close()


def get_remembered_account(username):
    """按用户名取一条（含密文），不存在返回 None"""
    conn = db.get_conn()
    try:
        return conn.execute(
            "SELECT * FROM remembered_accounts WHERE username = ?", (username,)
        ).fetchone()
    finally:
        conn.close()


def upsert_remembered_account(username, password, remember_password, auto_login):
    """保存 / 更新一条记住的账号。

    - password 为明文，由后端用 crypto_pwd 加密后存储（不依赖前端 / Electron safeStorage）。
    - remember_password=True 才写入密文；否则密文置 NULL（只记住用户名）。
    - auto_login=True 时，先把所有账号 auto_login 置 0，再只把本条置 1（保证全局唯一）。
    - 同时更新 last_login_at / updated_at。
    """
    # 明文密码由后端加密存储（跨环境稳定，重启 / 换端口不受影响）
    encrypted_password = crypto_pwd.encrypt_pwd(password) if remember_password else None
    conn = db.get_conn()
    try:
        existing = conn.execute(
            "SELECT id FROM remembered_accounts WHERE username = ?", (username,)
        ).fetchone()
        if auto_login:
            conn.execute("UPDATE remembered_accounts SET auto_login = 0")
        if existing:
            conn.execute(
                "UPDATE remembered_accounts SET "
                "encrypted_password = ?, remember_password = ?, auto_login = ?, "
                "last_login_at = datetime('now','localtime'), updated_at = datetime('now','localtime') "
                "WHERE username = ?",
                (
                    encrypted_password if remember_password else None,
                    1 if remember_password else 0,
                    1 if auto_login else 0,
                    username,
                ),
            )
        else:
            conn.execute(
                "INSERT INTO remembered_accounts "
                "(username, encrypted_password, remember_password, auto_login, last_login_at, updated_at) "
                "VALUES (?, ?, ?, ?, datetime('now','localtime'), datetime('now','localtime'))",
                (
                    username,
                    encrypted_password if remember_password else None,
                    1 if remember_password else 0,
                    1 if auto_login else 0,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def delete_remembered_account(username):
    """删除一条记住的账号"""
    conn = db.get_conn()
    try:
        conn.execute(
            "DELETE FROM remembered_accounts WHERE username = ?", (username,)
        )
        conn.commit()
    finally:
        conn.close()


def update_profile(uid, new_username=None, new_password=None, new_display_name=None):
    """修改当前用户的账号名 / 密码 / 昵称。

    - 改账号名：校验格式 + 不与他人冲突（排除自己），并级联更新
      remembered_accounts.username（本机记住的登录记录）。
    - 改密码：bcrypt 重新加密。
    - display_name 传 None 表示不修改；传空串则清空昵称。
    """
    if new_username is not None and not ACCOUNT_RE.match(new_username):
        return None, "账号须为字母开头、仅含英文与数字，长度 2-20"
    conn = db.get_conn()
    try:
        u = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        if not u:
            return None, "用户不存在"
        old_username = u["username"]
        target_username = new_username or old_username
        if new_username and new_username != old_username:
            if conn.execute(
                "SELECT id FROM users WHERE username = ? AND id <> ?",
                (new_username, uid),
            ).fetchone():
                return None, "该账号名已被占用"
            # 同步本机记住的账号记录，避免登录页残留旧名
            conn.execute(
                "UPDATE remembered_accounts SET username = ? WHERE username = ?",
                (new_username, old_username),
            )
        pwd_hash = security.hash_password(new_password) if new_password else None
        conn.execute(
            "UPDATE users SET username = ?, password_hash = COALESCE(?, password_hash), "
            "display_name = ? WHERE id = ?",
            (
                target_username,
                pwd_hash,
                new_display_name if new_display_name is not None else u["display_name"],
                uid,
            ),
        )
        conn.commit()
        return conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone(), None
    finally:
        conn.close()


def list_users():
    """返回所有用户（不含密码哈希），供用户管理页"""
    conn = db.get_conn()
    try:
        rows = conn.execute(
            "SELECT id, username, display_name, created_at FROM users ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def admin_update_user(uid, new_username=None, new_password=None, new_display_name=None):
    """管理员修改任意用户的账号名 / 密码 / 昵称（当前未分角色，登录即可调用）。

    复用 update_profile 的校验与级联更新逻辑。
    """
    return update_profile(uid, new_username, new_password, new_display_name)


def delete_user(uid):
    """删除用户及其本机记住记录；成功返回 True，不存在返回 False"""
    conn = db.get_conn()
    try:
        u = conn.execute("SELECT username FROM users WHERE id = ?", (uid,)).fetchone()
        if not u:
            return False
        username = u["username"]
        conn.execute("DELETE FROM remembered_accounts WHERE username = ?", (username,))
        conn.execute("DELETE FROM users WHERE id = ?", (uid,))
        conn.commit()
        return True
    finally:
        conn.close()
