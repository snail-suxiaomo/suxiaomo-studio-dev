-- 文件空间：用户钉在侧边栏的常用目录书签
-- 只存「链接」，不扫描内容、不索引全盘
CREATE TABLE IF NOT EXISTS filespace_roots (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  name        TEXT    NOT NULL,                                       -- 书签显示名（如「F盘·小说项目」）
  path        TEXT    NOT NULL UNIQUE,                                -- 目录绝对路径（Windows 风格，如 D:\MyProjects）
  note        TEXT,                                                   -- 备注（可选）
  sort_order  INTEGER NOT NULL DEFAULT 0,                             -- 拖拽排序权重，越小越靠前
  category    TEXT    NOT NULL DEFAULT '未分类',                      -- 书签分类（下载/文件/文件夹/其它…）
  cover_path  TEXT,                                                   -- 自定义封面图片绝对路径（NULL=用默认调色板纯色块）
  pinned_tags TEXT,                                                   -- 固定标签：常用文件夹名 JSON 数组（如 ["03-人物","13-成品"]），NULL=未生成
  created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))  -- 创建时间
);
