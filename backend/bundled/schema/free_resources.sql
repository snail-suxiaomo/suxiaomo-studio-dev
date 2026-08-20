-- 免费资源（原羊毛 / 免费生图生视频站）
-- 与 web_nav（网址导航）平级、独立表，专收「免费生图 / 生视频站」类富工具卡：
--   含网址、平台、操作步骤、免费额度、相关提示词、截图。
-- 截图真实文件存 data/free_resources_images/，库只存相对路径数组（JSON 字符串）。
-- 分类 category / tags 为普通文本字段，前端用 datalist 给建议值，同时允许自由输入新值（支持自建，无需改表）。
CREATE TABLE IF NOT EXISTS free_resources (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  title        TEXT    NOT NULL,                              -- 网站 / 工具名
  url          TEXT,                                         -- 网址（详情里"去网站"）
  category     TEXT    NOT NULL DEFAULT '其他',             -- 分类（生图/生视频/去水印/剪辑/配音/其他，支持自建）
  platform     TEXT,                                         -- 平台（如 即梦/可灵/MJ）
  status       TEXT    NOT NULL DEFAULT 'available',        -- 状态：available 可用 / daily 每日领积分 / expired 已失效
  steps        TEXT,                                         -- 操作步骤（自由文本，对应操作步骤图）
  quota        TEXT,                                         -- 免费额度 / 限制说明
  prompt_ref   TEXT,                                         -- 相关提示词（自由文本）
  note         TEXT,                                         -- 备注
  tags         TEXT    NOT NULL DEFAULT '',                 -- 自由标签，逗号分隔
  region       TEXT,                                         -- 国内外（国内/国外）
  register_way TEXT,                                         -- 注册方式（手机号/邮箱/Google…）
  need_vpn     TEXT,                                         -- 需梯子（是/否）
  support_model TEXT,                                         -- 支持模型（如 2.0/Fast/Standard）
  verified_at  TEXT,                                         -- 验证日期（YYYY-MM-DD）
  rating       TEXT,                                         -- 评级（1-5）
  cost_15s_points TEXT,                                       -- 每15秒积分消耗
  cost_15s_amount  TEXT,                                       -- 每15秒金额消耗
  images       TEXT    NOT NULL DEFAULT '[]',               -- 操作步骤图路径数组（JSON 字符串），真实文件存 data/free_resources_images/
  sort_order   INTEGER NOT NULL DEFAULT 0,                  -- 拖拽排序权重
  created_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
