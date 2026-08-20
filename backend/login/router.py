"""login/router.py —— 登录的接线员（只管路由，不写业务逻辑）

接口：
  POST /api/auth/register   开放注册（无角色分级）
  POST /api/auth/login      校验密码发令牌
  GET  /api/auth/me        当前用户（需带 Bearer 令牌）
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel

from common import security, crypto_pwd
from . import service

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterReq(BaseModel):
    username: str
    password: str
    display_name: str | None = None


class LoginReq(BaseModel):
    username: str
    password: str


class RememberSaveReq(BaseModel):
    username: str
    password: str | None = None             # 明文密码（可选）；不记密码则为 null，由后端加密存储
    remember_password: bool = False
    auto_login: bool = False


class ProfileUpdateReq(BaseModel):
    username: str | None = None             # 改账号名（可选）
    password: str | None = None             # 改密码（可选，传明文，后端 bcrypt 加密）
    display_name: str | None = None         # 改昵称（可选；传空串清空，传 null 不修改）


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str | None = None


def _user_out(u) -> dict:
    return {"id": u["id"], "username": u["username"], "display_name": u["display_name"]}


def get_current_user(authorization: str = Header(None)):
    """从请求头取 Bearer 令牌，解析出当前用户；无/无效则 401"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录或令牌缺失")
    token = authorization[7:]
    try:
        payload = security.decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")
    user = service.get_user_by_id(int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


@router.post("/register")
def register(req: RegisterReq):
    user, err = service.register(req.username, req.password, req.display_name)
    if err:
        raise HTTPException(status_code=400, detail=err)
    token = service.create_token(user)
    return {"access_token": token, "token_type": "bearer", "user": _user_out(user)}


@router.post("/login")
def login(req: LoginReq):
    user = service.authenticate(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = service.create_token(user)
    return {"access_token": token, "token_type": "bearer", "user": _user_out(user)}


@router.get("/me")
def me(user=Depends(get_current_user)):
    return _user_out(user)


@router.put("/profile")
def update_profile(req: ProfileUpdateReq, user=Depends(get_current_user)):
    """修改当前登录用户的账号名 / 密码 / 昵称（需鉴权）"""
    updated, err = service.update_profile(
        user["id"], req.username, req.password, req.display_name
    )
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"user": _user_out(updated)}


# ─────────────────────────────────────────────────────────────
# 记住的账号：多账号下拉 / 记住密码 / 自动登录（仅客户端便利数据，不校验登录态）
# ─────────────────────────────────────────────────────────────

@router.get("/remembered-accounts")
def api_list_remembered():
    """记住的账号列表（不含密码密文），供登录页下拉展示"""
    return service.list_remembered_accounts()


@router.get("/remembered-accounts/{username}")
def api_get_remembered(username: str):
    """取单条记住的账号（含加密密文），供自动填充 / 自动登录时解密"""
    row = service.get_remembered_account(username)
    if not row:
        raise HTTPException(status_code=404, detail="未找到记住的账号")
    # 后端解密密文，直接返回明文供前端回填（密钥只在后端，前端拿不到）
    plain = crypto_pwd.decrypt_pwd(row["encrypted_password"]) if row["encrypted_password"] else ""
    return {
        "username": row["username"],
        "password": plain,
        "remember_password": bool(row["remember_password"]),
        "auto_login": bool(row["auto_login"]),
        "last_login_at": row["last_login_at"],
    }


@router.post("/remembered-accounts")
def api_save_remembered(req: RememberSaveReq):
    """保存 / 更新一条记住的账号（upsert）。auto_login=True 时其他账号自动置 0。"""
    if not req.username:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    service.upsert_remembered_account(
        req.username,
        req.password,
        req.remember_password,
        req.auto_login,
    )
    return {"ok": True}


@router.delete("/remembered-accounts/{username}")
def api_delete_remembered(username: str):
    """删除一条记住的账号（下拉里的「删除此账号」）"""
    service.delete_remembered_account(username)
    return {"ok": True}


# ─────────────────────────────────────────────────────────────
# 用户管理：查看所有用户、修改任意用户资料、删除用户
# 当前系统未区分角色/授权，登录用户均可调用（后续按角色再细化）
# ─────────────────────────────────────────────────────────────

class AdminUserUpdateReq(BaseModel):
    username: str | None = None
    password: str | None = None
    display_name: str | None = None


@router.get("/users")
def api_list_users(user=Depends(get_current_user)):
    return service.list_users()


@router.put("/users/{uid}")
def api_admin_update_user(uid: int, req: AdminUserUpdateReq, user=Depends(get_current_user)):
    updated, err = service.admin_update_user(
        uid, req.username, req.password, req.display_name
    )
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"user": _user_out(updated)}


@router.delete("/users/{uid}")
def api_delete_user(uid: int, user=Depends(get_current_user)):
    if not service.delete_user(uid):
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"ok": True}
