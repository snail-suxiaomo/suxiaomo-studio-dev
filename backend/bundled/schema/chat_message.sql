-- 聊天消息表：每条用户/助手消息一行
-- images / texts 存 JSON 数组，记录附件的元信息（相对路径 + 文件名 + 类型 + 大小），
-- 真实文件落在 数据目录/chat_attachments/{session_id}/ 下，DB 不存二进制，避免库膨胀。
CREATE TABLE IF NOT EXISTS chat_message (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id  INTEGER NOT NULL,                        -- 所属会话
  role        TEXT    NOT NULL,                        -- user / assistant / system
  content     TEXT    NOT NULL DEFAULT '',              -- 文本正文
  reasoning    TEXT,                                    -- 思考过程（可空，Kimi/DeepSeek 等思考模型才有）
  images      TEXT    NOT NULL DEFAULT '[]',           -- JSON 图片附件元信息数组
  texts       TEXT    NOT NULL DEFAULT '[]',            -- JSON 文本附件元信息数组
  token_usage TEXT,                                    -- 可选用量统计（可空）
  is_error    INTEGER NOT NULL DEFAULT 0,              -- 1=该条为出错占位
  created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_chat_message_session ON chat_message(session_id, id);
