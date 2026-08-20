-- 网址导航（原常用网站快捷链接）
-- 与 free_resources（免费资源）平级、独立表，专收「常用网站快捷链接」：
--   网址、分类、备注、标签、可选图标/截图。
-- 图片真实文件存 data/web_nav_images/，库只存相对路径数组（JSON 字符串）。
-- 分类 category / tags 为普通文本字段，前端用 datalist 给建议值，同时允许自由输入新值（支持自建，无需改表）。
CREATE TABLE IF NOT EXISTS web_nav (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  title        TEXT    NOT NULL,                              -- 网站名
  url          TEXT,                                         -- 网址（直接打开）
  category     TEXT    NOT NULL DEFAULT '其他',             -- 分类（如 工具/社区/素材/文档/其他）
  note         TEXT,                                         -- 备注
  tags         TEXT    NOT NULL DEFAULT '',                 -- 自由标签，逗号分隔
  images       TEXT    NOT NULL DEFAULT '[]',               -- 图标/截图路径数组（JSON 字符串），真实文件存 data/web_nav_images/
  cover_image  TEXT,                                         -- 封面图路径（不填则默认取 images[0]）
  created_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
