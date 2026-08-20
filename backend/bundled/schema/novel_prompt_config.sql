-- ============================================================
-- 小说转短剧 · 指令配置（每个功能含三块，全中文、编剧可直接编辑）
-- 作用：存 AI 生成指令 / 格式校验规则 / AI 审核指令，运行时由对应功能 py 读取
-- 不做通用解释器：generation 直接给 AI；ai_content 给 AI 做审核；
--            py_format 保留可编辑、作为该功能的格式规则约定（真正硬校验由各功能 py 实现）
-- 纯建表，只跑一次（IF NOT EXISTS），不迁移
-- ============================================================
CREATE TABLE IF NOT EXISTS novel_prompt_config (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  function_id   TEXT    NOT NULL,                              -- 功能编号，如 "01-梗概"（指向 novel_function.function_id）
  type          TEXT    NOT NULL,                              -- 指令类型：generation=AI生成指令 / py_format=格式校验规则(中文DSL) / ai_content=AI审核指令
  content       TEXT    NOT NULL DEFAULT '',                   -- 指令正文（纯中文，可编辑）
  model_config_id INTEGER,                                   -- 块级模型绑定（NULL=跟随功能级 novel_function.model_config_id）
  thinking_enabled INTEGER,                                  -- 块级思考开关（NULL=跟随功能级 thinking_enabled）；非 NULL 时覆盖功能级
  reasoning_effort TEXT,                                     -- 块级推理强度（NULL=跟随功能级）；非 NULL 时覆盖功能级；仅思考开启时生效
  updated_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
  UNIQUE(function_id, type)                                   -- 同一功能同类型仅一条
);
