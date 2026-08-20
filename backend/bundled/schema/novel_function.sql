-- ============================================================
-- 小说转短剧 · 功能清单（13 个管线步骤）
-- 作用：侧边栏展示、各功能 py 查「中文名 / 产物目录名」用
-- 纯建表，只跑一次（IF NOT EXISTS），不迁移
-- ============================================================
CREATE TABLE IF NOT EXISTS novel_function (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,                 -- 自增主键
  function_id   TEXT    NOT NULL UNIQUE,                         -- 功能编号，如 "01-梗概"（与产物目录 01-梗概 对应）
  name          TEXT    NOT NULL,                                -- 中文显示名，如 "小说梗概"
  description   TEXT,                                            -- 功能说明（可空）
  sort_order    INTEGER NOT NULL DEFAULT 0,                     -- 侧边栏排序（取功能编号前缀数字，0~12）
  thinking_enabled INTEGER NOT NULL DEFAULT 1,                  -- 该功能的思考模式开关：1=开（走思考提质）、0=关（省 token/提速）。优先级高于 model_config 全局开关
  reasoning_effort TEXT NOT NULL DEFAULT 'medium',             -- 该功能的推理强度：low/medium/high（仅思考开启时生效）；优先级高于 model_config 全局
  model_config_id INTEGER,                                       -- 该功能绑定的模型配置 id（指向 model_config.id）；NULL=跟随全局启用那条。实现「按功能分别选模型」
  created_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
