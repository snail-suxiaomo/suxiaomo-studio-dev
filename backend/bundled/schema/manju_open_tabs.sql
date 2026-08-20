-- ============ 漫剧生成·打开的标签表 manju_open_tabs ============
-- 用途：漫剧生成各子功能（生图/音色/生视频/其他）内置浏览器打开的 webview 标签持久化。
-- 一条记录 = 一个打开的标签；只有用户点 × 关闭才会删除（重启/切子功能/清缓存都不丢）。
-- client_id 为前端生成的标签唯一 id（t<时间戳>-<随机>）；site_id 关联 manju_sites.id（删除网站时级联清 tab）。
CREATE TABLE IF NOT EXISTS manju_open_tabs (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  client_id    TEXT NOT NULL UNIQUE,
  category     TEXT NOT NULL,
  site_id      INTEGER,
  name         TEXT NOT NULL,
  tag          TEXT NOT NULL DEFAULT '',
  url          TEXT NOT NULL DEFAULT '',
  sort_order   INTEGER NOT NULL DEFAULT 0,
  created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at   TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
