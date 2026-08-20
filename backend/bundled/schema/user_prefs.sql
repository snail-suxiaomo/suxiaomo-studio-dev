-- ============ 用户偏好表 user_prefs：跨设备/跨会话记住用户选择 ============
-- 用途：AI 规则「记住上次选择」等场景。值存 JSON 字符串（如规则完整身份快照）。
-- 存在用户数据根的 app.db（随 workspace 迁移/备份）。

CREATE TABLE IF NOT EXISTS user_prefs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  user_key    TEXT    NOT NULL,                          -- 当前登录用户名（如 admin）
  pref_key    TEXT    NOT NULL,                          -- 偏好键（如 ai_rule.提示词库）
  pref_value  TEXT,                                      -- 值：JSON 字符串
  updated_at  TEXT    NOT NULL DEFAULT (datetime('now')),
  UNIQUE (user_key, pref_key)
);
