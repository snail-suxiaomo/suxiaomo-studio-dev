"""record_release.py —— 由 build.js 在打包成功末尾调用，写一条发布记录到 app_releases。

仅开发版打包会走到这里（「发布版本」页 dev-only），故 backend/venv 的 Python 必然存在。
数据库位置由环境变量 SUXIAOMO_DATA_DIR 决定（build.js 透传当前真实数据根），
缺省回退到 <root>/workspace，与 common.db 完全一致，避免写进空的默认库。
"""
import argparse
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from common.db import get_conn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--features", default="[]")
    ap.add_argument("--path", default="")
    args = ap.parse_args()

    try:
        conn = get_conn()
        try:
            # 防御：若 app_releases 表尚未建（极端情况下 init_db 未覆盖到），这里兜底建表，
            # 与 common/db.py 中 _migrate() 的建表 DDL 保持一致。
            conn.execute(
                "CREATE TABLE IF NOT EXISTS app_releases ("
                " id INTEGER PRIMARY KEY AUTOINCREMENT,"
                " version TEXT NOT NULL,"
                " release_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),"
                " features_json TEXT NOT NULL DEFAULT '[]',"
                " path TEXT,"
                " created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))"
                ")"
            )
            conn.execute(
                "INSERT INTO app_releases(version, features_json, path) VALUES(?, ?, ?)",
                (args.version, args.features, args.path or None),
            )
            conn.commit()
        finally:
            conn.close()
        print(f"[record_release] 已写入发布记录: {args.version}")
        return 0
    except Exception as e:
        print(f"[record_release] 写入失败（不影响产物）: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
