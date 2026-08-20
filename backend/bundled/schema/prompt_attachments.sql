-- ============ 提示词附件表 prompt_attachments ============
-- 仅 skills 分类提示词使用：存压缩包（zip/7z/rar/tar 等）原文件，供下载复用。
-- md/txt/docx 不落库：读取内容直接填入 prompt_library.content。
-- 真实文件存 data/prompt_attachments/{prompt_id}/，本表只存元数据 + 相对路径。

CREATE TABLE IF NOT EXISTS prompt_attachments (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  prompt_id   INTEGER NOT NULL,                       -- 关联 prompt_library.id
  filename    TEXT    NOT NULL,                       -- 原始文件名（含扩展名）
  filetype    TEXT    NOT NULL DEFAULT '',            -- 小写扩展名（如 zip / 7z / rar）
  filesize    INTEGER NOT NULL DEFAULT 0,             -- 字节数
  filepath    TEXT    NOT NULL,                       -- 相对 data/prompt_attachments/ 的路径
  created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_pa_prompt ON prompt_attachments(prompt_id);
