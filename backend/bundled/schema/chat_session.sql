-- 聊天会话表：一个会话 = 一段可重开的对话
-- 数据全部落在用户数据目录（开发态为项目内 workspace/，打包态为 exe 同级 workspace/），
-- 构建分发包时本表为空，绝不携带任何本地聊天记录。
CREATE TABLE IF NOT EXISTS chat_session (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,   -- 会话 id
  title           TEXT    NOT NULL DEFAULT '新会话',    -- 会话标题（首条用户消息自动生成）
  model_config_id INTEGER,                              -- 绑定的模型配置 id（列表里显示用的哪家模型）
  created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_chat_session_updated ON chat_session(updated_at DESC);
