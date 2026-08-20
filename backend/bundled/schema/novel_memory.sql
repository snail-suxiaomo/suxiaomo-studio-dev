-- ===========================================================
-- 小说转短剧 · 项目记忆库 project_memory
-- 作用：每个功能处理完某章后，自动把摘要存为 draft 草稿；
--       编剧可在界面逐条查看、编辑、删除，或手动补充；
--       确认（confirmed）后的记忆会注入后续章节生成上下文。
-- 纯建表，只跑一次（IF NOT EXISTS），不迁移
-- ===========================================================
CREATE TABLE IF NOT EXISTS project_memory (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,        -- 编号：自增主键
  project_id    INTEGER NOT NULL,                          -- 项目ID（指向 novel_project.id）
  function_id   TEXT    NOT NULL,                          -- 功能编号，如 "01-梗概"（与产物目录对应）
  chapter_idx   INTEGER NOT NULL,                         -- 章节序号（从 1 开始）
  summary       TEXT    DEFAULT '',                       -- 记忆摘要（中文）：自动写入时为该章该功能的产出摘要
  key_data      TEXT,                                    -- 可选结构化数据（JSON 串：人物/道具/伏笔等），可空
  status        TEXT    NOT NULL DEFAULT 'draft',         -- 状态：draft 草稿（待确认）/ confirmed 已确认（注入后续）
  created_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
