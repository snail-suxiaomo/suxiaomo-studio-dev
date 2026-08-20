-- ============ 模型配置表 model_config：大模型接入设置 ============
-- 一条记录 = 一个可切换的模型配置（如 deepseek 官方 / gpt / 本地 ollama）
-- 各管线功能(去重/精要/...)都复用 common/ai.py，由它读「默认」的那条
-- is_active 即「默认模型」标记：全局最多 1 条为 1（见下方部分唯一索引）

CREATE TABLE IF NOT EXISTS model_config (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,            -- 编号：自增主键
  name         TEXT    NOT NULL,                             -- 名称：配置名，如 "deepseek官方"（允许多条同名，id 才是真实主键）
  provider     TEXT    NOT NULL DEFAULT 'openai',           -- 类型：openai / ollama / 自定义(都走 OpenAI 兼容接口)
  base_url     TEXT    NOT NULL,                            -- 接口地址：如 https://api.deepseek.com/v1
  api_key      TEXT,                                        -- 密钥：留空表示免密钥(本地模型)
  secret_key   TEXT,                                        -- 第二密钥：少数厂商需要，无则不填
  model_name   TEXT    NOT NULL,                            -- 模型名：如 deepseek-chat
  temperature  REAL    NOT NULL DEFAULT 0.7,               -- 温度：0~1，越大越随机（思考模式下被忽略）
  timeout_sec  INTEGER NOT NULL DEFAULT 300,               -- 超时：秒
  is_active    INTEGER NOT NULL DEFAULT 0,                 -- 是否启用：1=当前使用，0=停用
  thinking_enabled INTEGER NOT NULL DEFAULT 1,             -- 思考模式：1=开启（DeepSeek V4 默认开），0=关
  reasoning_effort TEXT   NOT NULL DEFAULT 'medium',        -- 模型强度：low（低）/ medium（中）/ high（高），思考开启时映射为 reasoning_effort
  max_tokens   INTEGER NOT NULL DEFAULT 2048,              -- 最大输出 token：思考模式建议 >=2048
  supports_vision INTEGER NOT NULL DEFAULT 0,              -- 是否支持图片/视觉输入：1=支持，0=不支持
  supports_files  INTEGER NOT NULL DEFAULT 0,              -- 是否支持文件/文档上传：1=支持，0=不支持（自定义厂商由用户勾选决定）
  sort_order   INTEGER NOT NULL DEFAULT 0,                  -- 排序权重：越大越靠前（卡片拖拽排序用）
  reasoning_format TEXT NOT NULL DEFAULT 'thinking_block', -- 推理参数格式：thinking_block=发 thinking 块；top_level_effort=发顶层 reasoning_effort
  provider_key TEXT,                                         -- 厂商键：deepseek / kimi / zhipu / hy3 / minimax / ollama / custom
  model_profile_id INTEGER,                                  -- 引用的模型档案 id（自定义时为 NULL）
  mode         TEXT,                                         -- 当前选用的模式 key：fast / expert / turbo / pro 等
  created_at   TEXT    NOT NULL DEFAULT (datetime('now')),  -- 创建时间
  updated_at   TEXT    NOT NULL DEFAULT (datetime('now'))   -- 更新时间
);

-- 默认模型唯一约束：is_active=1 全局只能有一条（部分唯一索引，SQLite 3.8+ 支持）
CREATE UNIQUE INDEX IF NOT EXISTS idx_model_config_single_default
  ON model_config (is_active) WHERE is_active = 1;

-- 不再预置默认配置：由用户在页面自行添加，避免空 API Key 占位导致调用失败。
