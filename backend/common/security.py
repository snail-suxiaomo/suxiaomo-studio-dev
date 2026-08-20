"""common/security.py —— 密码哈希 + JWT 的小工具（公共，各功能复用）

注意：这是「公共工具函数」，不是引擎，不含任何 if function_id 分支。
"""

import bcrypt
import jwt
import secrets
import datetime

ALGO = "HS256"


def hash_password(pw: str) -> str:
    """把明文密码转成 bcrypt 加密串"""
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(pw: str, hashed: str) -> bool:
    """校验明文密码是否匹配加密串"""
    try:
        return bcrypt.checkpw(pw.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def _secret():
    """读 JWT 签名密钥；没有就随机生成存进 config 表（不进 .env、不进代码）"""
    from common import db
    s = db.get_config("jwt_secret")
    if not s:
        s = secrets.token_hex(32)
        db.set_config("jwt_secret", s, "JWT 签名密钥（首次随机生成）")
    return s


def _expire_hours():
    """读令牌有效期（小时）。

    语义：
    - 不配置 / <=0  → 永久有效（不写 exp 声明，令牌不过期，只能手动退出失效）
    -  >0          → 有限期（小时）

    桌面应用是单用户自用，默认永久，避免 30 天一到就被踢登录。
    兼容旧默认 720（30 天）：首次读到 720 自动升级为永久，不弹窗不打扰。
    """
    from common import db
    raw = db.get_config("jwt_expire_hours")
    if raw is None:
        return None  # 默认永久
    try:
        h = int(raw)
    except Exception:
        return None
    # 旧默认 720 视为"用户从未改过"→ 升级为永久
    if h == 720:
        try:
            db.set_config("jwt_expire_hours", "0", "令牌有效期（小时），0 或不配置=永久")
        except Exception:
            pass
        return None
    return h if h > 0 else None


def create_token(user: dict) -> str:
    """给用户签发 JWT（payload 含 sub/username/iat，永久令牌不加 exp）"""
    now = datetime.datetime.utcnow()
    payload = {
        "sub": str(user["id"]),
        "username": user["username"],
        "iat": int(now.timestamp()),
    }
    expire = _expire_hours()
    if expire is not None:
        payload["exp"] = int((now + datetime.timedelta(hours=expire)).timestamp())
    return jwt.encode(payload, _secret(), algorithm=ALGO)


def decode_token(token: str) -> dict:
    """解析 JWT；失败抛异常（过期/无效）"""
    return jwt.decode(token, _secret(), algorithms=[ALGO])
