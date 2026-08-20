-- ============ 模型厂商表 model_provider：内置大模型厂商元数据 ============
-- 每个厂商一条记录，作为 model_profile 的外键分组。
-- key 使用小写英文，前后端统一认这个 key。

CREATE TABLE IF NOT EXISTS model_provider (
  key              TEXT    PRIMARY KEY,                       -- 厂商键：deepseek / kimi / zhipu / hy3 / minimax / ollama / custom
  name             TEXT    NOT NULL,                          -- 显示名：如 DeepSeek / Moonshot Kimi / 智谱 GLM
  base_url         TEXT    NOT NULL,                          -- 默认接口地址
  api_key_required INTEGER NOT NULL DEFAULT 1,               -- 是否必须填 API Key：1=必填，0=可空（如 ollama 本地）
  sort_order       INTEGER NOT NULL DEFAULT 0,                -- 排序权重
  created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- 内置厂商种子（只插不存在者，避免覆盖用户自定义）
INSERT OR IGNORE INTO model_provider (key, name, base_url, api_key_required, sort_order) VALUES
('deepseek', 'DeepSeek', 'https://api.deepseek.com/v1', 1, 10),
('kimi',     'Moonshot Kimi', 'https://api.moonshot.cn/v1', 1, 20),
('zhipu',    '智谱 GLM', 'https://open.bigmodel.cn/api/paas/v4', 1, 30),
('hy3',      'Hy3', 'https://tokenhub.tencentmaas.com/v1', 1, 40),
('minimax',  'MiniMax', 'https://api.minimax.io/v1', 1, 50),
('ollama',   'Ollama 本地', 'http://localhost:11434/v1', 0, 60),
('custom',   '自定义/OpenAI 兼容', '', 1, 999),
('doubao-seed', '豆包 Seed（火山方舟）', 'https://ark.cn-beijing.volces.com/api/v3', 1, 80),
('qwen',      '通义千问（百炼）', 'https://dashscope.aliyuncs.com/compatible-mode/v1', 1, 90),
('codeqwen',  '通义千问代码（百炼）', 'https://dashscope.aliyuncs.com/compatible-mode/v1', 1, 100),
('flux_art', 'Flux Art', 'https://open-api.flux-art.ai', 1, 70);
