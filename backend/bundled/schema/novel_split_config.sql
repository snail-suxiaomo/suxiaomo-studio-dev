-- novel_split_config：00-拆分 的诊断参数表（项目级，只服务于 novel_split，其他功能不碰）
-- 每一行对应一个项目的拆分阈值参数
CREATE TABLE IF NOT EXISTS novel_split_config (
    project_id   INTEGER PRIMARY KEY NOT NULL,
    min_chars    INTEGER NOT NULL DEFAULT 300,   -- 迷你章阈值（字数 < 此值警告）
    max_chars    INTEGER NOT NULL DEFAULT 8000,  -- 巨型章阈值（字数 > 此值警告）
    noise_max_len INTEGER NOT NULL DEFAULT 20,   -- 噪音行最长字数（单行 ≤ 此值且不含章节标记 → 噪音候选）
    created_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
