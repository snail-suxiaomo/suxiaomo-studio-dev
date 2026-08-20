-- ============ AI 密钥库 key_vault：与各厂家的 API 密钥/平台信息集中管理 ============
-- 与「模型配置 model_config」是两套东西：
--   model_config 只关心「用哪个模型、什么参数」，不再散落明文 key；
--   key_vault 是「平台/账号/密钥/额度/过期」的主库，模型配置可引用它（key_vault_id）。
-- 注意：本表含敏感字段（api_key / secret_key），导出 Excel 会带明文，请在本地妥善保管。

CREATE TABLE IF NOT EXISTS key_vault (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,                -- 编号
  name         TEXT    NOT NULL,                                -- 条目名称：如「DeepSeek 主号」（一条平台可有多套 key）
  provider     TEXT    NOT NULL DEFAULT '自定义',                -- 平台/厂商：DeepSeek / Kimi / 即梦 / 可灵 / 阿里百炼 / 腾讯云 …
  category     TEXT    NOT NULL DEFAULT '文本大模型',            -- 归类：文本大模型 / 图像生成 / 视频生成 / 语音合成 / 翻译 / 其他
  base_url     TEXT,                                            -- 模型对接链接（接口地址）
  api_key      TEXT,                                            -- API Key（核心密钥字段）
  secret_key   TEXT,                                            -- 部分平台额外需要的 Secret Key（即梦/可灵/腾讯云等）
  account      TEXT,                                            -- 登录账号（邮箱/手机号，便于找回或区分多账号）
  dev_url      TEXT,                                            -- 开发者平台网站（如 https://platform.deepseek.com/usage）
  sort_order   INTEGER NOT NULL DEFAULT 0,                      -- 排序权重（越大越靠前）
  created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
  updated_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);
