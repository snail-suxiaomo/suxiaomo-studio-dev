-- ============ 记住的账号表 remembered_accounts ============
-- 用途：登录页「记住密码 / 自动登录 / 多账号下拉」的客户端便利数据。
-- 安全：密码绝不存明文，encrypted_password 是 common/crypto_pwd.py 用 XOR 流密码 +
--       数据根 data/.pwd_key（32 字节随机密钥，随 workspace 迁移）加密后的密文（Base64）。
--       密钥不进代码、不在前端，只有后端能解密；复制数据库文件看不到明文。
-- 自动登录：全局最多一个账号 auto_login=1（由后端 upsert 保证唯一）。
CREATE TABLE IF NOT EXISTS remembered_accounts (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  username           TEXT    NOT NULL UNIQUE,      -- 用户名（关联 users 表，不唯一约束由业务保证存在）
  encrypted_password TEXT,                           -- crypto_pwd 加密后的密文（Base64）；不勾记住密码则为 NULL
  remember_password  INTEGER NOT NULL DEFAULT 0,    -- 是否记住密码：1=记住（可自动填充/自动登录）0=不记
  auto_login         INTEGER NOT NULL DEFAULT 0,    -- 是否自动登录：全局唯一，1 仅一条
  last_login_at      TEXT,                          -- 最后成功登录时间（本地时区），用于下拉默认选中
  created_at         TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at         TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
