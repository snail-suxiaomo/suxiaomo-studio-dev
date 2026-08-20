-- 自媒体账号汇总表：统一管理各平台账号信息
-- 图片(二维码/封面)存 DATA_ROOT/data/social_images/，本表只存相对路径
CREATE TABLE IF NOT EXISTS social_account (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  platform        TEXT    NOT NULL DEFAULT '',   -- 平台(抖音/快手/小红书...)
  account_name    TEXT    NOT NULL DEFAULT '',   -- 账号名称
  account_id      TEXT    NOT NULL DEFAULT '',   -- 账号ID
  user_id         TEXT    NOT NULL DEFAULT '',   -- UserId
  homepage_url    TEXT    NOT NULL DEFAULT '',   -- 主页链接
  bio             TEXT    NOT NULL DEFAULT '',   -- 简介
  gender          TEXT    NOT NULL DEFAULT '',   -- 性别
  birthday        TEXT    NOT NULL DEFAULT '',   -- 生日
  location        TEXT    NOT NULL DEFAULT '',   -- 所在地
  likes_count     INTEGER NOT NULL DEFAULT 0,    -- 获赞
  mutual_count    INTEGER NOT NULL DEFAULT 0,    -- 互关
  following_count INTEGER NOT NULL DEFAULT 0,    -- 关注
  followers_count INTEGER NOT NULL DEFAULT 0,    -- 粉丝
  qr_image        TEXT    NOT NULL DEFAULT '',   -- 二维码图片相对路径
  cover_image     TEXT    NOT NULL DEFAULT '',   -- 封面图片相对路径
  sort_order      INTEGER NOT NULL DEFAULT 0,    -- 拖拽排序
  created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
