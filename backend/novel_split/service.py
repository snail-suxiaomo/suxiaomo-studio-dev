"""novel_split/service.py —— 上传拆分的实际干活（无引擎）

职责：解码上传文件 → 调 splitter 切章 → 把 第N章.md 写到 projects/<项目>/00-拆分/
→ 写一份「00-小说拆分报告.md」。schema 在 data/schema/novel_project.sql 之外，
本功能只操作文件系统 + sqlite 读项目名。
"""

from pathlib import Path
from datetime import datetime

from common import db
from . import splitter
from novel_memory import service as mem_service


def get_project(pid):
    conn = db.get_conn()
    try:
        return conn.execute(
            "SELECT * FROM novel_project WHERE id = ?", (pid,)
        ).fetchone()
    finally:
        conn.close()


def do_split(project_id, project_name: str, text: str):
    """切章并落盘。返回 {format, chapters, out_dir}"""
    result = splitter.split_text(text)
    if result["format"] is None:
        raise RuntimeError("未检测到「章/回/卷/集/节」章节标记，无法拆分")

    out_dir: Path = db.PROJECTS_DIR / project_name / "00-拆分"
    out_dir.mkdir(parents=True, exist_ok=True)

    n = 0
    for ch in result["chapters"]:
        if ch.get("type") in ("body", "extra"):
            fn = out_dir / f"第{ch['idx']}章.md"
            prefix = "> 所属：番外\n\n" if ch["type"] == "extra" else ""
            chapter_text = f"# {ch['title']}\n\n{prefix}{ch['content']}\n\n---\n"
            fn.write_text(chapter_text, encoding="utf-8")
            # 自动写入记忆库（拆分即初稿草稿）
            if project_id is not None:
                try:
                    mem_service.save_draft(project_id, "00-拆分", ch["idx"], chapter_text)
                except Exception:
                    pass
            n += 1

    return {
        "format": result["format"],
        "chapters": n,
        "out_dir": str(out_dir),
    }


def list_split_files(project_name: str):
    """列出 projects/<项目名>/00-拆分/ 下的 .md（排除报告本身），按章号数字排序。"""
    out_dir: Path = db.PROJECTS_DIR / project_name / "00-拆分"
    if not out_dir.exists():
        return []
    files = [f.name for f in out_dir.glob("*.md")
             if f.name != "00-小说拆分报告.md"]
    # 按文件名中的数字排序：第N章.md
    import re
    def _num(name):
        m = re.search(r'第(\d+)章', name)
        return int(m.group(1)) if m else 0
    return sorted(files, key=_num)


# ── 诊断与素材 ──────────────────────────────────────────


def do_diagnose(project_id: int, project_name: str, raw: bytes, filename: str) -> dict:
    """将原始文件存到 00-拆分/小说原文/（原 00-素材），执行诊断，返回诊断结果。不切章。"""
    text = splitter.decode_file(raw, filename)

    # 存原始素材到 00-拆分/小说原文/
    asset_dir: Path = db.PROJECTS_DIR / project_name / "00-拆分" / "小说原文"
    asset_dir.mkdir(parents=True, exist_ok=True)
    asset_path = asset_dir / filename
    asset_path.write_bytes(raw)

    # 读项目级配置
    cfg = get_split_config(project_id)

    # 执行诊断
    diag = splitter.diagnose(text, cfg)
    diag["source_file"] = filename
    diag["asset_path"] = str(asset_path)
    return diag


def do_split_from_asset(project_id: int, project_name: str, source_file: str,
                         diag_info: dict | None = None) -> dict:
    """从已存 00-拆分/小说原文/ 读取文件执行拆分（无需再次上传）。

    diag_info 可选：{ai_confirmed, remaining_hard, remaining_soft} 用于报告。"""
    asset_path: Path = db.PROJECTS_DIR / project_name / "00-拆分" / "小说原文" / source_file
    if not asset_path.exists():
        raise FileNotFoundError(f"源文件不存在：{asset_path}")
    raw = asset_path.read_bytes()
    text = splitter.decode_file(raw, source_file)
    result = do_split(project_id, project_name, text)
    write_report(project_name, source_file, result, diag_info)
    return result


# ── 拆分参数配置 ────────────────────────────────────────

DEFAULT_CONFIG = {"min_chars": 300, "max_chars": 8000, "noise_max_len": 20}


def get_split_config(project_id: int) -> dict:
    """读项目级拆分参数缺省值。"""
    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT min_chars, max_chars, noise_max_len FROM novel_split_config WHERE project_id = ?",
            (project_id,),
        ).fetchone()
        if row:
            return {"min_chars": row["min_chars"],
                    "max_chars": row["max_chars"],
                    "noise_max_len": row["noise_max_len"]}
        return dict(DEFAULT_CONFIG)
    finally:
        conn.close()


def save_split_config(project_id: int, min_chars: int = 300,
                      max_chars: int = 8000, noise_max_len: int = 20) -> dict:
    """保存项目级拆分参数。"""
    conn = db.get_conn()
    try:
        conn.execute(
            "INSERT INTO novel_split_config(project_id, min_chars, max_chars, noise_max_len) "
            "VALUES(?,?,?,?) ON CONFLICT(project_id) DO UPDATE "
            "SET min_chars=excluded.min_chars, max_chars=excluded.max_chars, "
            "noise_max_len=excluded.noise_max_len, updated_at=datetime('now','localtime')",
            (project_id, min_chars, max_chars, noise_max_len),
        )
        conn.commit()
        return {"min_chars": min_chars, "max_chars": max_chars, "noise_max_len": noise_max_len}
    finally:
        conn.close()


def write_report(project_name: str, source_file: str, split_result: dict,
                 diag_info: dict | None = None):
    """写 00-小说拆分报告.md（纯中文可读）

    diag_info 可选：{ai_confirmed, remaining_hard, remaining_soft} 只写有效的异常。"""
    out_dir: Path = db.PROJECTS_DIR / project_name / "00-拆分"
    report = out_dir / "00-小说拆分报告.md"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# 00-小说拆分报告 · 《{project_name}》",
        "",
        f"- 源文件：{source_file}",
        f"- 拆分格式：{split_result['format']}",
        f"- 产出章节数：{split_result['chapters']} 章",
        f"- 输出目录：{split_result['out_dir']}",
        f"- 拆分时间：{now}",
    ]
    if diag_info:
        if diag_info.get("ai_confirmed"):
            lines.append("- AI 辅助分析：✅ 已确认")
        remaining_hard = diag_info.get("remaining_hard", [])
        remaining_soft = diag_info.get("remaining_soft", [])
        if remaining_hard or remaining_soft:
            lines.append("")
            lines.append("### 诊断报告（拆分时有效异常）")
            for h in remaining_hard:
                lines.append(f"- 🔴 {h.get('type','?')}：{h.get('detail','')}")
            for s in remaining_soft:
                lines.append(f"- 🟡 {s.get('type','?')}：{s.get('detail','')}")

    lines += [
        "",
        "> 每章正文在 00-拆分/第N章.md；番外以「> 所属：番外」标注。",
    ]
    report.write_text("\n".join(lines), encoding="utf-8")
