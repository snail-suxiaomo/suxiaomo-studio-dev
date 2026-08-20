-- 个人指令库（Prompt Library）
-- 与 novel_prompt_config（系统管线配置）物理隔离，互不影响。
-- 用途：记录常用 prompt（文本 / 短剧相关 / 图片提示词 / skill 等），支持预览、编辑、保存、一键复制。
-- 分类支持「预设 + 可自建」：category_1 / category_2 / output_type / tags 都是普通文本字段，
--   前端用 datalist 提供已有值，同时允许自由输入新值，新增分类无需改表结构。
CREATE TABLE IF NOT EXISTS prompt_library (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  uid          TEXT,                                              -- 稳定唯一键（命名空间序号，如 OEM-7F3A-0001）：导入导出精确匹配
  owner_name   TEXT NOT NULL DEFAULT '苏小沫',                    -- 展示归属：苏小沫(出厂)/我(接收方自建)/小黑(第三方)，纯展示不参与匹配
  title        TEXT    NOT NULL,                                  -- 短标题
  content      TEXT    NOT NULL DEFAULT '',                       -- prompt 正文
  category     TEXT    NOT NULL DEFAULT '其他',                   -- 单一分类：skill/去重/改写/剧本/角色/场景/道具/打斗/特效/分镜/其他，支持自建
  scope        TEXT    NOT NULL DEFAULT 'prompt',                 -- 归属：prompt(漫剧相关纯文本提示词) / instruction(skills + 不属于漫剧大类的提示词)
  category_1   TEXT    NOT NULL DEFAULT '其他',                   -- 【已停用，保留兼容】原一级分类
  category_2   TEXT    NOT NULL DEFAULT '通用',                   -- 【已停用，保留兼容】原二级分类
  output_type  TEXT    NOT NULL DEFAULT '文本',                   -- 形态：文本/图片/视频/音频/其他
  note         TEXT,                                              -- 版本说明、适用场景（如「复杂版」「新版本推荐」）
  tags         TEXT    NOT NULL DEFAULT '',                       -- 自由标签，逗号分隔（即梦/苏小沫/3D 等）
  source_file  TEXT,                                              -- 原始文件名（txt 批量导入用，已停用）
  images       TEXT    NOT NULL DEFAULT '[]',                     -- 生图模版图路径数组（JSON 字符串），真实文件存 data/prompt_images/
  sort_order   INTEGER NOT NULL DEFAULT 0,                        -- 卡片拖拽排序权重，越小越靠前
  created_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
