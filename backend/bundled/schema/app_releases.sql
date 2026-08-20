-- ============ 发布版本记录表 app_releases：每次打包成功写一条 ============
-- 记录已发布的版本号与本次纳入的功能清单，前端「发布版本」页据此提示下一个版本号。
-- 注意：此表在「统一数据根」的 app.db 里，属于开发者本机的发布记录，
--       不会被打进发布产物（build.js 的构建门禁与 extraResources 已确保不含数据）。
CREATE TABLE IF NOT EXISTS app_releases (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,                -- 编号：自增主键
  version       TEXT    NOT NULL,                                -- 版本号，如 1.0.0
  release_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime')), -- 发布时间（本地时区）
  features_json TEXT    NOT NULL DEFAULT '[]',                   -- 本次纳入的功能 key 列表（JSON 字符串）
  path          TEXT,                                            -- 发布产物目录，如 suxiaomo-studio-release/suxiaomo-studio-v1.0.0
  created_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime'))  -- 记录写入时间
);
