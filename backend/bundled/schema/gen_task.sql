-- ============ 媒体生成任务表 gen_task：生图/生视频异步任务 ============
-- 一条记录 = 一次提交给 Flux Art 等媒体平台的生图/生视频任务。
-- 状态从 queued → processing → succeeded/failed/canceled，结果落本地媒体目录。

CREATE TABLE IF NOT EXISTS gen_task (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,            -- 本地任务编号
  config_id    INTEGER NOT NULL,                             -- 关联的 model_config.id
  capability   TEXT    NOT NULL,                             -- image / video
  model_name   TEXT    NOT NULL,                             -- 实际 API 模型名
  prompt       TEXT    NOT NULL,                             -- 提示词
  params       TEXT,                                        -- 额外参数 JSON（aspect_ratio/duration/...）
  flux_task_id TEXT,                                         -- 平台返回的任务 id（轮询用）
  status       TEXT    NOT NULL DEFAULT 'queued',           -- queued/processing/succeeded/failed/canceled
  result_url   TEXT,                                         -- 平台返回的结果远程地址（轮询得到）
  local_path   TEXT,                                         -- 下载到本地的文件名（media 目录下）
  points_charged INTEGER,                                    -- 本次消耗算力（来自 usage）
  error        TEXT,                                         -- 失败原因
  created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
  updated_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);
