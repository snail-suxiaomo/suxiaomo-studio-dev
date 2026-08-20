-- ============ AI 调用规则表 ai_rules ============
-- 仅存「自建规则」（用户实际使用的规则）。
-- 默认参考规则来自 workspace/AI调用规则/*.md，系统只读展示，不进本表。
-- 各功能按 menu + function_key + role 引用；模型/思考/强度绑定在规则上。
-- 思考/强度语义（与「模型配置」页的「思考模式 / 思考强度」控件对齐）：
--   thinking : follow(跟随模型配置) / enabled(强制开启思考) / disabled(强制关闭思考)
--   strength : follow(跟随模型配置) / low(低) / medium(中) / high(高) / ultra(超高)
--              NULL=跟随模型配置
--   model_config_id : 引用 model_config.id，NULL=跟随启用中的模型
--   source   : db(自建) / file(旧版残留，迁移后应无)
-- ref_path : 本条自建规则复制自哪个参考文件（相对 AI调用规则/ 的路径）；
--            非空时支持「单条重置」（从文件重新读入覆盖）；纯新建为 NULL。
-- 三键唯一标识一条规则：menu + function_key + role（同名规则由 name 区分，id 为真实主键）

CREATE TABLE IF NOT EXISTS ai_rules (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  menu            TEXT    NOT NULL DEFAULT '通用',      -- 所属菜单/功能模块：提示词库 / 漫剧创作 / 聊天 / 工具箱 ...
  function_key    TEXT    NOT NULL DEFAULT '',          -- 具体功能：导入外部提示词 / 06-改写 / ...
  role            TEXT    NOT NULL DEFAULT 'system',    -- organize(整理)/generate(生成)/system(系统提示)/split(拆分)/review(审核)/format(格式约定)/optimize(优化)
  name            TEXT    NOT NULL,                     -- 可读名（如 默认-整理文本为多条提示词）
  content         TEXT    NOT NULL DEFAULT '',          -- 正文（system_prompt 或格式约定，按 role 区分用途）
  model_config_id INTEGER,                              -- 引用模型配置；NULL=跟随启用中的模型
  thinking        TEXT    NOT NULL DEFAULT 'follow',    -- follow / enabled / disabled
  strength        TEXT,                                 -- follow / low / medium / high / ultra；NULL=跟随模型配置
  enabled         INTEGER NOT NULL DEFAULT 1,           -- 1=启用（调用方只列 enabled）
  is_builtin      INTEGER NOT NULL DEFAULT 0,           -- 1=来自参考规则（仍可删，因已是自建）
  source          TEXT    NOT NULL DEFAULT 'db',        -- db(自建) / file(旧版残留)
  ref_path        TEXT,                                 -- 来源参考文件路径（相对 AI调用规则/）；NULL=纯新建
  sort_order      INTEGER NOT NULL DEFAULT 0,
  result_count    TEXT,                                 -- single(单条) / multi(多条)；NULL=未声明（前端按 role 兜底）
  created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_ai_rules_scope_fn ON ai_rules(menu, function_key);
CREATE INDEX IF NOT EXISTS idx_ai_rules_enabled ON ai_rules(enabled);
