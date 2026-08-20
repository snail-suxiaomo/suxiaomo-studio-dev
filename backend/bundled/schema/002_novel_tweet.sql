-- 小说推文：推广活动（以推文关键词为基准，如「错嫁的小萤」）
-- 分类维度 = novel_platform（知乎 / 番茄小说 等），支持用户自建。
CREATE TABLE IF NOT EXISTS novel_tweet_campaign (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,                          -- 推文名称（自起关键词，如「错嫁的小萤」）
  novel_platform TEXT NOT NULL DEFAULT '其他',  -- 小说平台（知乎/番茄等），用作首页分类
  platform_type TEXT NOT NULL DEFAULT 'web',    -- 网页版 web / APP版 app
  original_novel_name TEXT NOT NULL DEFAULT '',  -- 原小说名称
  original_promotion_link TEXT NOT NULL DEFAULT '', -- 原小说推广链接（可复制/直接打开）
  original_promotion_copy TEXT NOT NULL DEFAULT '', -- 原小说推广文案（可编辑/预览）
  optimized_copy TEXT NOT NULL DEFAULT '',       -- 推广文案优化
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now','localtime')),
  updated_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 小说推文：第三方推广平台（清风助手等）
-- 一个推广活动对应多个平台；平台下挂发布账号汇总与回填信息。
CREATE TABLE IF NOT EXISTS novel_tweet_platform (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  campaign_id INTEGER NOT NULL,
  platform_name TEXT NOT NULL DEFAULT '',       -- 第三方平台名称（如清风助手）
  application_date TEXT NOT NULL DEFAULT '',     -- 申请日期
  publish_date TEXT NOT NULL DEFAULT '',         -- 作品发布日期
  is_published_backfill INTEGER NOT NULL DEFAULT 0, -- 是否发布回填 0/1
  publish_accounts TEXT NOT NULL DEFAULT '',    -- 发布账号汇总：抖音/快手/B站/视频号/其他平台（单选）
  publish_work_link TEXT NOT NULL DEFAULT '',   -- 发布作品链接
  deadline_earnings TEXT NOT NULL DEFAULT '',   -- 截止日期收益
  douyin_account_id TEXT NOT NULL DEFAULT '',   -- 抖音账号ID
  douyin_name TEXT NOT NULL DEFAULT '',         -- 抖音名称
  bilibili_id TEXT NOT NULL DEFAULT '',         -- B站账号ID
  bilibili_name TEXT NOT NULL DEFAULT '',       -- B站名称
  kuaishou_id TEXT NOT NULL DEFAULT '',         -- 快手账号ID
  kuaishou_name TEXT NOT NULL DEFAULT '',       -- 快手名称
  other_name TEXT NOT NULL DEFAULT '',          -- 其他平台账号名称
  other_id TEXT NOT NULL DEFAULT '',            -- 其他平台账号ID
  other_link TEXT NOT NULL DEFAULT '',          -- 其他平台作品链接
  other_earnings TEXT NOT NULL DEFAULT '',      -- 其他平台收益
  other_remark TEXT NOT NULL DEFAULT '',        -- 其他平台备注
  shipinhao_name TEXT NOT NULL DEFAULT '',      -- 视频号账号名称
  shipinhao_id TEXT NOT NULL DEFAULT '',        -- 视频号账号ID
  shipinhao_link TEXT NOT NULL DEFAULT '',      -- 视频号作品链接
  shipinhao_earnings TEXT NOT NULL DEFAULT '',  -- 视频号收益
  shipinhao_remark TEXT NOT NULL DEFAULT '',    -- 视频号备注
  douyin_publish_date TEXT NOT NULL DEFAULT '',   -- 抖音作品发布日期
  bilibili_publish_date TEXT NOT NULL DEFAULT '',  -- B站作品发布日期
  kuaishou_publish_date TEXT NOT NULL DEFAULT '',  -- 快手作品发布日期
  other_publish_date TEXT NOT NULL DEFAULT '',     -- 其他平台作品发布日期
  shipinhao_publish_date TEXT NOT NULL DEFAULT '', -- 视频号作品发布日期
  douyin_is_published_backfill INTEGER NOT NULL DEFAULT 0,   -- 抖音是否发布回填 0/1
  bilibili_is_published_backfill INTEGER NOT NULL DEFAULT 0, -- B站是否发布回填 0/1
  kuaishou_is_published_backfill INTEGER NOT NULL DEFAULT 0, -- 快手是否发布回填 0/1
  other_is_published_backfill INTEGER NOT NULL DEFAULT 0,   -- 其他平台是否发布回填 0/1
  shipinhao_is_published_backfill INTEGER NOT NULL DEFAULT 0, -- 视频号是否发布回填 0/1
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now','localtime')),
  updated_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_nt_platform_campaign ON novel_tweet_platform(campaign_id);
