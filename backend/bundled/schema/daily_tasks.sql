-- 每日任务：每日需执行的操作（签到领积分、必做事情等）
-- 按「任务 + 日期」记录完成状态，登录当天查看当日完成，隔日自动重置。
CREATE TABLE IF NOT EXISTS daily_tasks (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  name               TEXT    NOT NULL,                              -- 任务名称
  owner              TEXT,                                          -- 所属用户
  software           TEXT,                                          -- 操作软件
  detail             TEXT    NOT NULL DEFAULT '每日签到领积分',    -- 人物详细 / 任务详情
  login_account      TEXT,                                          -- 登录账号
  operation_accounts TEXT    NOT NULL DEFAULT '[]',               -- 操作账号（手机号/邮箱，JSON 数组）
  must_do            TEXT,                                          -- 必做事情（如：制作1个视频消耗免费积分）
  link               TEXT,                                          -- 网站链接（任务相关页面 / 后台地址等）
  points             INTEGER NOT NULL DEFAULT 0,                   -- 完成任务可获得的积分数
  points_mode        TEXT    NOT NULL DEFAULT 'cumulative',        -- 积分归属方式：cumulative 累加永久可用 / daily 每日领取当日清空
  task_date          TEXT,                                          -- 日期（YYYY-MM-DD）
  status             TEXT    NOT NULL DEFAULT 'active',           -- 状态：active 激活 / paused 暂停（软隐藏，可恢复）
  sort_order         INTEGER NOT NULL DEFAULT 0,                  -- 拖拽排序权重
  created_at         TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at         TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 每日完成记录：按「任务 + 日期」记录是否已完成（按登录日期重置）
CREATE TABLE IF NOT EXISTS daily_task_completions (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id      INTEGER NOT NULL,
  comp_date    TEXT    NOT NULL,                                    -- 完成日期 YYYY-MM-DD
  completed_at TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
  UNIQUE(task_id, comp_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_task_completions_date ON daily_task_completions(comp_date);
