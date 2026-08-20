-- ============ 配置表 config：替代 .env，开关都存成行 ============
-- 你能在 SQL 工具里直接改这些行（如把 jwt_expire_hours 改成 48）
CREATE TABLE IF NOT EXISTS config (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,  -- 编号：自增主键
  key         TEXT    NOT NULL UNIQUE,             -- 配置名：如 jwt_expire_hours，不重复
  value       TEXT,                                -- 配置值
  description TEXT                                 -- 说明：这行是干嘛的
);

-- 首次启动、表里没数据时插入默认（你之后在 SQL 工具里改）
INSERT INTO config (key, value, description)
  SELECT 'jwt_expire_hours', '24', '登录令牌有效期(小时)'
  WHERE NOT EXISTS (SELECT 1 FROM config WHERE key = 'jwt_expire_hours');

-- JWT 签名密钥：首次随机生成后也存进 config(key=jwt_secret)，不进 .env、不进代码
-- 下面这行由后端 ensure_seed 在首次启动时随机写入，这里不写死
