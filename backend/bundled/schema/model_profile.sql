-- ============ 模型档案表 model_profile：每个厂商下各型号的能力模板 ============
-- 一条记录 = 一个具体模型（如 kimi-k2.6 / deepseek-v4-pro）的能力参数模板。
-- model_config 新增记录时可引用本表，自动带出该模型支持的参数域、默认值与锁定项。

CREATE TABLE IF NOT EXISTS model_profile (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  provider_key       TEXT    NOT NULL,                        -- 所属厂商键
  model_key          TEXT    NOT NULL,                        -- 模型键：如 k2.6 / v4-pro / glm-5
  display_name       TEXT    NOT NULL,                        -- 显示名：如 Kimi K2.6 / DeepSeek V4 Pro
  model_name         TEXT    NOT NULL,                        -- 实际 API 模型名：如 kimi-k2.6
  modes              TEXT    NOT NULL DEFAULT '[]',          -- JSON：该模型支持的快速/专家等模式 [{key, name, thinking, effort, notes}]
  default_mode       TEXT    NOT NULL DEFAULT 'expert',      -- 默认选中的模式 key
  supports_vision    INTEGER NOT NULL DEFAULT 0,             -- 是否支持图片/视觉输入
  supports_files     INTEGER NOT NULL DEFAULT 0,             -- 是否支持文件/文档上传（文本文件走 text 附件）
  temperature        REAL    NOT NULL DEFAULT 0.7,           -- 非思考模式下的默认温度
  temperature_locked INTEGER NOT NULL DEFAULT 0,             -- 温度是否锁定不可改：1=锁定，0=可编辑
  max_tokens         INTEGER NOT NULL DEFAULT 2048,          -- 默认最大输出长度
  reasoning_format   TEXT    NOT NULL DEFAULT 'thinking_block', -- 思考开启时如何发推理参数
  effort_mapping     TEXT    NOT NULL DEFAULT '{}',          -- JSON：low/medium/high 映射到厂商真实值
  max_tokens_field   TEXT    NOT NULL DEFAULT 'max_tokens',  -- 该厂商用的输出长度字段名
  capability         TEXT    NOT NULL DEFAULT 'chat',        -- 能力类型：chat(文本/代码) / image(生图) / video(生视频)
  param_schema       TEXT,                                    -- JSON：生图/生视频模型的额外参数描述（前端渲染表单用），chat 为 NULL
  notes              TEXT,                                    -- 给前端的说明/限制提示
  sort_order         INTEGER NOT NULL DEFAULT 0,              -- 同厂商内排序
  created_at         TEXT    NOT NULL DEFAULT (datetime('now')),
  UNIQUE(provider_key, model_key)
);

-- 内置模型档案（只插不存在者）
-- 说明：
--   thinking=true  对应用户口中的「专家/深度思考」模式
--   thinking=false 对应用户口中的「快速」模式
--   effort_mapping 把前端低/中/高映射成各家真实字符串
-- 能力说明（多模态 / 文件）：
--   DeepSeek：不支持图片，但支持文件/文档上传
--   Kimi K2.6/K3：多模态，支持图片与文件
--   Kimi K2.7 Code：代码模型，不支持图片，支持文件
--   GLM 5/5.1/5.2：多模态，支持图片与文件；GLM 4.6 仅快速，支持图片不支持文件
INSERT OR IGNORE INTO model_profile
(provider_key, model_key, display_name, model_name, modes, default_mode,
 supports_vision, supports_files, temperature, temperature_locked, max_tokens,
 reasoning_format, effort_mapping, max_tokens_field, notes, sort_order)
VALUES
-- DeepSeek
('deepseek', 'v4-pro',  'DeepSeek V4 Pro',  'deepseek-v4-pro',  '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"适用于大部分情况"},{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"研究级智能模型，思考更深"}]', 'expert',
 0, 1, 0.7, 0, 8192, 'thinking_block', '{"low":"low","medium":"medium","high":"max"}', 'max_tokens',
 'V4 Pro 支持 thinking 块；思考模式下 temperature 被忽略但仍可传入。支持文件/文档上传。', 10),
('deepseek', 'v4-flash','DeepSeek V4 Flash','deepseek-v4-flash','[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"轻量快速"},{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"深度推理"}]', 'fast',
 0, 1, 0.7, 0, 8192, 'thinking_block', '{"low":"low","medium":"medium","high":"max"}', 'max_tokens',
 'V4 Flash 快速模式性价比高。支持文件/文档上传。', 20),

-- Kimi：temperature 固定为 1，官方禁止显式传入；k2.6 不支持 reasoning_effort，只支持 thinking 块
('kimi', 'k3',   'Kimi K3',   'kimi-k3',   '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"适用于大部分情况"},{"key":"expert","name":"专家","thinking":true,"effort":"max","notes":"研究级智能模型"}]', 'expert',
 1, 1, 1.0, 1, 131072, 'top_level_effort', '{"low":"low","medium":"high","high":"max"}', 'max_completion_tokens',
 'Kimi K3 推理常驻；快速模式仍按官方默认 max 推理，但尽量轻量。温度固定为 1，不可修改。支持图片与文件。', 10),
('kimi', 'k2.6', 'Kimi K2.6', 'kimi-k2.6', '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"适用于大部分情况"},{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"研究级智能模型"}]', 'expert',
 1, 1, 1.0, 1, 8192, 'thinking_block', '{"low":"low","medium":"medium","high":"high"}', 'max_tokens',
 'Kimi K2.6 官方禁止显式传 temperature；只支持 thinking 块，不支持顶层 reasoning_effort。温度固定为 1。支持图片与文件。', 20),
('kimi', 'k2.7-code', 'Kimi K2.7 Code', 'kimi-k2.7-code', '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"适用于大部分情况"},{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"代码深度推理"}]', 'expert',
 0, 1, 1.0, 1, 8192, 'thinking_block', '{"low":"low","medium":"medium","high":"high"}', 'max_tokens',
 'K2.7 Code 思考常驻，传 disabled 会报错；温度固定为 1。不支持图片，仅支持文件/文档上传。', 30),

-- 智谱 GLM
('zhipu', 'glm-5.2', 'GLM 5.2', 'glm-5.2', '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"适用于大部分情况"},{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"研究级智能模型"}]', 'expert',
 1, 1, 0.7, 0, 8192, 'thinking_block', '{"low":"1","medium":"4","high":"7"}', 'max_tokens',
 'GLM 5.2 思考支持 7 档 effort（1~7）；temperature 取值 [0,1] 两位小数。支持图片与文件。', 10),
('zhipu', 'glm-5.1', 'GLM 5.1', 'glm-5.1', '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"适用于大部分情况"},{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"深度推理"}]', 'expert',
 1, 1, 0.7, 0, 8192, 'thinking_block', '{"low":"low","medium":"medium","high":"high"}', 'max_tokens',
 'GLM 5.1 支持思考模式与图片/文件。', 20),
('zhipu', 'glm-5',   'GLM 5',   'glm-5',   '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"适用于大部分情况"},{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"深度推理"}]', 'expert',
 1, 1, 0.7, 0, 8192, 'thinking_block', '{"low":"low","medium":"medium","high":"high"}', 'max_tokens',
 'GLM 5 旗舰版，支持图片/文件。', 30),
('zhipu', 'glm-4.6', 'GLM 4.6', 'glm-4.6', '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"适用于大部分情况"}]', 'fast',
 1, 0, 0.7, 0, 4096, 'thinking_block', '{"low":"low","medium":"medium","high":"high"}', 'max_tokens',
 'GLM 4.6 不支持深度思考，仅快速模式。支持图片，不支持文件。', 40),

-- Hy3
('hy3', 'hy3', 'Hy3', 'hy3', '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"适用于大部分情况"},{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"研究级智能模型"}]', 'expert',
 0, 0, 0.7, 0, 8192, 'top_level_effort', '{"low":"low","medium":"medium","high":"max"}', 'max_tokens',
 'Hy3 用顶层 reasoning_effort 区分快慢思考；temperature 可编辑。', 10),

-- MiniMax
('minimax', 'm3',   'MiniMax M3',   'MiniMax-M3',   '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"适用于大部分情况"},{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"深度推理"}]', 'expert',
 0, 0, 1.0, 0, 8192, 'thinking_block', '{"low":"low","medium":"medium","high":"high"}', 'max_completion_tokens',
 'MiniMax M3 思考可控；M2.x 系列思考不可关。建议 temperature=1。', 10),
('minimax', 'm2.7', 'MiniMax M2.7', 'MiniMax-M2.7', '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"思考不可关，按默认推理"},{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"深度推理"}]', 'expert',
 0, 0, 1.0, 0, 8192, 'thinking_block', '{"low":"low","medium":"medium","high":"high"}', 'max_completion_tokens',
 'M2.7 思考不可关，选择快速模式仍可能返回 reasoning_content。', 20),
('minimax', 'm2.5', 'MiniMax M2.5', 'MiniMax-M2.5', '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"思考不可关，按默认推理"},{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"深度推理"}]', 'expert',
 0, 0, 1.0, 0, 8192, 'thinking_block', '{"low":"low","medium":"medium","high":"high"}', 'max_completion_tokens',
 'M2.5 思考不可关，选择快速模式仍可能返回 reasoning_content。', 30),

-- Ollama：具体模型由用户填，这里只给一个通用模板
('ollama', 'custom', 'Ollama 本地模型', '', '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"本地轻量推理"},{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"本地深度推理（模型需支持）"}]', 'fast',
 0, 0, 0.7, 0, 4096, 'thinking_block', '{"low":"low","medium":"medium","high":"high"}', 'max_tokens',
 'Ollama OpenAI 兼容接口；具体模型名在配置时填写。API Key 可空。', 10),

-- 自定义：完全手填，作为兜底
('custom', 'custom', '自定义模型', '', '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"非思考模式"},{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"思考模式"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{"low":"low","medium":"medium","high":"high"}', 'max_tokens',
  '第三方中转站或文档未覆盖的新模型；所有参数可手工调整。', 10),

-- ===== 本轮新增 chat 厂商（豆包-Seed / 通义千问 / CodeQwen）=====
-- 豆包 Seed（火山方舟）：thinking 用 thinking:{type:enabled/disabled}，与系统 thinking_block 完全匹配
('doubao-seed', 'seed-1-6', '豆包 Seed 1.6', 'doubao-seed-1-6-250615',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"适用于大部分情况"},{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"深度思考"}]', 'expert',
 1, 1, 1.0, 0, 4096, 'thinking_block', '{"low":"low","medium":"medium","high":"high"}', 'max_tokens',
 '豆包 Seed 1.6 支持思考/非思考；支持图片与文件输入。', 10),
('doubao-seed', 'seed-1-6-flash', '豆包 Seed 1.6 Flash', 'doubao-seed-1-6-flash-250828',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"轻量快速"},{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"深度推理"}]', 'fast',
 1, 1, 1.0, 0, 4096, 'thinking_block', '{"low":"low","medium":"medium","high":"high"}', 'max_tokens',
 'Seed 1.6 Flash 极速版；支持图片与文件输入。', 20),
('doubao-seed', 'seed-1-6-thinking', '豆包 Seed 1.6 Thinking', 'doubao-seed-1-6-thinking-250615',
 '[{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"思考常开不可关"}]', 'expert',
 1, 1, 1.0, 0, 4096, 'thinking_block', '{"low":"low","medium":"medium","high":"high"}', 'max_tokens',
 'Seed 1.6 Thinking 思考加强版，仅专家模式。支持图片与文件输入。', 30),

-- 通义千问（百炼）：思考用 enable_thinking 顶层布尔（build_payload 已支持第三种格式）
('qwen', 'plus', '通义千问 Plus', 'qwen-plus',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"非思考模式"},{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"深度思考"}]', 'fast',
 0, 0, 0.7, 0, 2000, 'enable_thinking', '{}', 'max_tokens',
 '通义千问 Plus，混合思考（默认关）。enable_thinking 顶层布尔控制。', 10),
('qwen', 'max', '通义千问 Max', 'qwen-max',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"非思考模式"},{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"深度思考"}]', 'fast',
 0, 0, 0.7, 0, 2000, 'enable_thinking', '{}', 'max_tokens',
 '通义千问 Max，混合思考（默认关）。', 20),
('qwen', 'turbo', '通义千问 Turbo', 'qwen-turbo',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"非思考模式"},{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"深度思考"}]', 'fast',
 0, 0, 0.7, 0, 2000, 'enable_thinking', '{}', 'max_tokens',
 '通义千问 Turbo，低成本。', 30),
('qwen', 'plus-thinking', '通义千问 Plus Thinking', 'qwen-plus-thinking',
 '[{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"思考专用，不可关"}]', 'expert',
 0, 0, 0.7, 0, 4096, 'enable_thinking', '{}', 'max_tokens',
 '通义千问 Plus Thinking 思考专用模型，强制开启思考。', 40),
('qwen', 'vl-max', '通义千问 VL Max', 'qwen-vl-max',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"非思考模式"},{"key":"expert","name":"专家","thinking":true,"effort":"high","notes":"深度思考"}]', 'fast',
 1, 0, 0.7, 0, 2000, 'enable_thinking', '{}', 'max_tokens',
 '通义千问 VL Max 视觉模型，支持图片输入与思考。', 50),

-- CodeQwen（百炼代码模型）：非思考，用 thinking_block（thinking=false 不发布尔参数）
('codeqwen', 'qwen3-coder', 'Qwen3-Coder', 'qwen3-coder',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"代码模型，非思考"}]', 'fast',
 0, 0, 0.7, 0, 8192, 'thinking_block', '{"low":"low","medium":"medium","high":"high"}', 'max_tokens',
 '通义千问代码模型 Qwen3-Coder，非思考代码生成。', 10),
('codeqwen', 'qwen-coder-turbo', 'Qwen-Coder-Turbo', 'qwen-coder-turbo',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"代码模型，非思考"}]', 'fast',
 0, 0, 0.7, 0, 8192, 'thinking_block', '{"low":"low","medium":"medium","high":"high"}', 'max_tokens',
 '通义千问代码模型 Turbo 版，低成本。', 20),

-- Flux Art：第三方中转聚合平台，生图+生视频（capability 由迁移脚本设置，这里只插基础行）
-- 模型 ID 取自官方真实列表（含豆包/谷歌/GPT/Grok/Midjourney/通义/可灵/Wan/HappyHorse 等）
-- 注意：capability/param_schema 不在此处写出（兼容老库缺列），由 db._migrate 统一补齐

-- ===== 生图模型（image） =====
('flux_art', 'gpt-image-2', 'GPT Image 2', 'gpt-image-2',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', 'OpenAI GPT Image 2，新一代现象级图像模型。', 10),
('flux_art', 'grok-imagine', 'Grok Imagine', 'grok-imagine-image',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', 'Grok Imagine，快速生成高质量海报/壁纸。', 15),
('flux_art', 'grok-imagine-pro', 'Grok Imagine Pro', 'grok-imagine-image-pro',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', 'Grok Imagine Pro，增强版图像生成。', 20),
('flux_art', 'mj-imagine', 'Midjourney Imagine', 'mj_imagine',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', 'Midjourney Imagine，原生画质逼近商业摄影。', 25),
('flux_art', 'mj-blend', 'Midjourney Blend', 'mj_blend',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', 'Midjourney Blend，图像融合。', 30),
('flux_art', 'seedream-4-5', 'Seedream 4.5', 'doubao-seedream-4-5-251128',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '豆包 Seedream 4.5。', 35),
('flux_art', 'seedream-5-0', 'Seedream 5.0', 'doubao-seedream-5-0-260128',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '豆包 Seedream 5.0，默认已验证可跑通。', 40),
('flux_art', 'seedream-5-0-pro', 'Seedream 5.0 Pro', 'doubao-seedream-5-0-pro-260628',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '豆包 Seedream 5.0 Pro 增强版。', 45),
('flux_art', 'gemini-2-5-flash-image', 'Gemini 2.5 Flash Image', 'gemini-2.5-flash-image',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', 'Google Gemini 2.5 Flash 图像版。', 50),
('flux_art', 'gemini-3-pro-image', 'Gemini 3 Pro Image', 'gemini-3-pro-image-preview',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', 'Google Gemini 3 Pro 图像版。', 55),
('flux_art', 'gemini-3-1-flash-image', 'Gemini 3.1 Flash Image', 'gemini-3.1-flash-image-preview',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', 'Google Gemini 3.1 Flash 图像版。', 60),
('flux_art', 'gemini-3-1-flash-lite-image', 'Gemini 3.1 Flash Lite Image', 'gemini-3.1-flash-lite-image',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', 'Google Gemini 3.1 Flash Lite 图像版。', 65),
('flux_art', 'qwen-image-2-0', '通义万相 2.0', 'qwen-image-2.0',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '阿里通义万相 2.0。', 70),
('flux_art', 'qwen-image-2-0-pro', '通义万相 2.0 Pro', 'qwen-image-2.0-pro',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '阿里通义万相 2.0 Pro。', 75),
('flux_art', 'qwen-image-max', '通义万相 Max', 'qwen-image-max',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '阿里通义万相 Max。', 80),
('flux_art', 'kling-image-v1', '可灵图生图 V1', 'kling-v1-image',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '可灵图像生成 V1。', 85),
('flux_art', 'kling-image-v2', '可灵图生图 V2', 'kling-v2-image',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '可灵图像生成 V2。', 90),
('flux_art', 'kling-image-v2-1', '可灵图生图 V2.1', 'kling-v2-1-image',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '可灵图像生成 V2.1。', 95),
('flux_art', 'kling-image-v3', '可灵图生图 V3', 'kling-v3-image',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '可灵图像生成 V3。', 100),
('flux_art', 'kling-image-v3-omni', '可灵图生图 V3 Omni', 'kling-v3-omni-image',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '可灵图像生成 V3 Omni。', 105),
('flux_art', 'kling-image-o1', '可灵图生图 O1', 'kling-image-o1',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '可灵图像生成 O1。', 110),
('flux_art', 'wan-2-7-image', 'Wan 2.7 图像', 'wan2.7-image',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '阿里 Wan 2.7 图像生成。', 115),
('flux_art', 'wan-2-7-image-pro', 'Wan 2.7 图像 Pro', 'wan2.7-image-pro',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '阿里 Wan 2.7 图像生成 Pro。', 120),
('flux_art', 'z-image-turbo', 'Z Image Turbo', 'z-image-turbo',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生图模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', 'Z Image Turbo。', 125),

-- ===== 生视频模型（video） =====
('flux_art', 'seedance-1-0-pro', 'Seedance 1.0 Pro', 'doubao-seedance-1-0-pro-250528',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '豆包 Seedance 1.0 Pro。', 130),
('flux_art', 'seedance-1-0-pro-fast', 'Seedance 1.0 Pro Fast', 'doubao-seedance-1-0-pro-fast-251015',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '豆包 Seedance 1.0 Pro 快速版。', 135),
('flux_art', 'seedance-1-5-pro', 'Seedance 1.5 Pro', 'doubao-seedance-1-5-pro-251215',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '豆包 Seedance 1.5 Pro。', 140),
('flux_art', 'seedance-2-0', 'Seedance 2.0', 'doubao-seedance-2-0-260128',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '豆包 Seedance 2.0。', 145),
('flux_art', 'seedance-2-0-fast', 'Seedance 2.0 Fast', 'doubao-seedance-2-0-fast-260128',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '豆包 Seedance 2.0 快速版。', 150),
('flux_art', 'seedance-2-0-mini', 'Seedance 2.0 Mini', 'doubao-seedance-2-0-mini-260615',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '豆包 Seedance 2.0 Mini。', 155),
('flux_art', 'grok-video-3', 'Grok Video 3', 'grok-video-3',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', 'Grok Video 3。', 160),
('flux_art', 'kling-video-v1', '可灵视频 V1', 'kling-v1',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '可灵视频生成 V1。', 165),
('flux_art', 'kling-video-v1-5', '可灵视频 V1.5', 'kling-v1-5',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '可灵视频生成 V1.5。', 170),
('flux_art', 'kling-video-v2-1', '可灵视频 V2.1', 'kling-v2-1',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '可灵视频生成 V2.1。', 175),
('flux_art', 'kling-video-v2-1-master', '可灵视频 V2.1 Master', 'kling-v2-1-master',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '可灵视频生成 V2.1 Master。', 180),
('flux_art', 'kling-video-v2-6', '可灵视频 V2.6', 'kling-v2-6',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '可灵视频生成 V2.6。', 185),
('flux_art', 'kling-video-v3', '可灵视频 V3', 'kling-v3',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '可灵视频生成 V3。', 190),
('flux_art', 'kling-video-v3-omni', '可灵视频 V3 Omni', 'kling-v3-omni',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '可灵视频生成 V3 Omni。', 195),
('flux_art', 'kling-video-o1', '可灵视频 O1', 'kling-video-o1',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', '可灵视频生成 O1。', 200),
('flux_art', 'happyhorse-1-1', 'HappyHorse 1.1', 'happyhorse-1.1',
 '[{"key":"fast","name":"快速","thinking":false,"effort":"low","notes":"生视频模型"}]', 'fast',
 0, 0, 0.7, 0, 2048, 'thinking_block', '{}', 'max_tokens', 'HappyHorse 1.1 视频生成。', 205);
