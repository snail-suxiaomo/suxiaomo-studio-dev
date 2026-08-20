-- ============ 用户表 users：保存登录账号 ============
-- 初始管理员由首次启动插一条数据行，不从 .env 读
CREATE TABLE IF NOT EXISTS users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,  -- 编号：自增主键，每个用户唯一
  username      TEXT    NOT NULL UNIQUE,             -- 用户名：登录名，不能重复
  password_hash TEXT    NOT NULL,                    -- 密码：只存 bcrypt 加密串，绝不存明文
  display_name  TEXT,                                -- 昵称：展示用，可空
  created_at    TEXT    NOT NULL DEFAULT (datetime('now')),  -- 创建时间
  updated_at    TEXT    NOT NULL DEFAULT (datetime('now'))   -- 更新时间
);
