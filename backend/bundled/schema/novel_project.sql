-- ============ 小说项目表 novel_project：记录每个小说项目的基本信息 ============
-- 这是「项目管理」功能的数据底座；每个小说是一本，产物文件存在 projects/<name>/ 下
CREATE TABLE IF NOT EXISTS novel_project (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,  -- 编号：自增主键
  name          TEXT    NOT NULL UNIQUE,             -- 项目名：如《错嫁的小萤》，不能重复
  description   TEXT,                                -- 简介：这本小说大概讲啥
  status        TEXT    NOT NULL DEFAULT 'active',  -- 状态：active 进行中 / archived 已归档
  created_at    TEXT    NOT NULL DEFAULT (datetime('now')),  -- 创建时间
  updated_at    TEXT    NOT NULL DEFAULT (datetime('now'))   -- 更新时间
);
