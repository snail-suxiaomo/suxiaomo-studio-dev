-- 应用启动器：常用软件快捷方式
-- 只存「可执行文件路径 + 启动参数」，点击即在本机启动对应程序
CREATE TABLE IF NOT EXISTS app_launchers (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  name        TEXT    NOT NULL,                                       -- 显示名（如「微信」）
  exe_path    TEXT    NOT NULL UNIQUE,                                -- 可执行文件绝对路径（Windows 如 C:\...\wechat.exe）
  args        TEXT,                                                   -- 启动参数（可选，空格分隔）
  category    TEXT    NOT NULL DEFAULT '未分类',                      -- 分类（社交/工具/开发/其它…）
  note        TEXT,                                                   -- 备注（可选）
  sort_order  INTEGER NOT NULL DEFAULT 0,                             -- 拖拽排序权重，越小越靠前
  icon_path   TEXT,                                                   -- 提取的 exe 图标路径（data/app_icons/{id}.png），无则 NULL
  created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))  -- 创建时间
);
