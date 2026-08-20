"""common/crypto_pwd.py —— 轻量对称加密（仅用 Python 标准库）

用途：登录页「记住密码」的本地密文存储。
- 不依赖任何第三方库（cryptography 在部分环境装不上）。
- 密钥首次运行时自动生成，存于「统一数据根/data/.pwd_key」，随用户数据迁移。
- 采用 XOR 流密码 + Base64：对本地单机软件足够（防明文一眼可见 + 防 casual 读取），
  密钥不进代码，且解密只在后端进行，前端永远拿不到密钥。
"""

import os
import base64

# 数据根定位与 common/db.py 保持一致：优先 SUXIAOMO_DATA_DIR，否则 backend/workspace
_HERE = os.path.dirname(os.path.abspath(__file__))          # .../backend/common
_BACKEND = os.path.dirname(_HERE)                            # .../backend
DATA_ROOT = os.environ.get("SUXIAOMO_DATA_DIR") or os.path.join(_BACKEND, "workspace")
KEY_PATH = os.path.join(DATA_ROOT, "data", ".pwd_key")


def _get_key() -> bytes:
    os.makedirs(os.path.dirname(KEY_PATH), exist_ok=True)
    if os.path.exists(KEY_PATH):
        with open(KEY_PATH, "rb") as f:
            return f.read()
    key = os.urandom(32)
    with open(KEY_PATH, "wb") as f:
        f.write(key)
    return key


def encrypt_pwd(plain: str):
    """明文密码 → Base64 密文；空值返回 None"""
    if not plain:
        return None
    key = _get_key()
    data = plain.encode("utf-8")
    out = bytes([data[i] ^ key[i % len(key)] for i in range(len(data))])
    return base64.b64encode(out).decode("ascii")


def decrypt_pwd(token: str):
    """Base64 密文 → 明文；空值返回空串"""
    if not token:
        return ""
    key = _get_key()
    data = base64.b64decode(token)
    out = bytes([data[i] ^ key[i % len(key)] for i in range(len(data))])
    return out.decode("utf-8")
