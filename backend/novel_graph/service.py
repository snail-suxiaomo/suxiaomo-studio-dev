"""novel_graph/service.py —— 02-图谱主流程（无引擎）

流程：合并 01-梗概/全部章 → 读已有 02-图谱报告（增量参考）
→ 拼 generation（替换 {content} 与 {context_旧报告}）→ 调 ai.chat 生成
→ 可单独执行 validator 格式校验 / reviewer AI 审核 → 写 02-小说图谱报告.md（整本单一报告，非逐章）。
"""
import re
from pathlib import Path
from datetime import datetime

from common import db
from common import ai
from ai_rule import service as airule_service
from . import validator, reviewer
from novel_memory import service as mem_service

FUNCTION_ID = "02-图谱"
SYNOPSIS_DIR = "01-梗概"
OUTPUT_DIR = "02-图谱"
REPORT_NAME = "02-小说图谱报告.md"

NO_OLD_REPORT = "（暂无：本次为首次构建或从零重建，无需参考旧报告）"


# ---------- 基础读写 ----------

def _get_project_name(project_id):
    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT name FROM novel_project WHERE id = ?", (project_id,)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        raise RuntimeError(f"项目 id={project_id} 不存在")
    return row["name"]


def _load_generation():
    return airule_service.resolve_rule_content('小说改写', FUNCTION_ID, 'generate')


def _merge_synopsis(project_name):
    """合并 01-梗概 下所有章正文，返回合并文本（无则 None）"""
    d = db.PROJECTS_DIR / project_name / SYNOPSIS_DIR
    if not d.exists():
        return None
    parts = []
    for f in sorted(d.glob("第*章*.md")):
        m = re.match(r"第(\d+)章", f.stem)
        if not m:
            continue
        text = f.read_text(encoding="utf-8")
        body = []
        started = False
        for ln in text.split("\n"):
            if ln.startswith("# "):
                started = True
                continue
            if started:
                body.append(ln)
        parts.append(f"## 第{m.group(1)}章 梗概\n" + "\n".join(body).strip())
    return "\n\n".join(parts) if parts else None


def _read_old_report(project_name):
    p = db.PROJECTS_DIR / project_name / OUTPUT_DIR / REPORT_NAME
    return p.read_text(encoding="utf-8") if p.exists() else None


def _read_report(project_name):
    """读取当前报告正文（无则 None）。"""
    p = db.PROJECTS_DIR / project_name / OUTPUT_DIR / REPORT_NAME
    return p.read_text(encoding="utf-8") if p.exists() else None


def _write_report(project_name, output):
    out_dir = db.PROJECTS_DIR / project_name / OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / REPORT_NAME).write_text(output + "\n", encoding="utf-8")


# ---------- 核心执行（三步可独立调用） ----------

def generate_report(project_id):
    """仅生成整本图谱报告并落盘。"""
    try:
        project_name = _get_project_name(project_id)

        merged = _merge_synopsis(project_name)
        if not merged:
            return _fail("generate", "未找到 01-梗概 产物，请先完成「小说梗概」")

        old_report = _read_old_report(project_name)
        generation = _load_generation()
        if not generation:
            return _fail("generate", "未配置 02-图谱 的 generation 指令")

        user_prompt = (
            generation
            .replace("{content}", merged)
            .replace("{context_旧报告}", old_report or NO_OLD_REPORT)
        )

        try:
            output = ai.chat(user_prompt, airule=('小说改写', '02-图谱', 'generate'))
        except RuntimeError as e:
            return _fail("generate", str(e))

        _write_report(project_name, output)

        # 自动写入记忆库（整本单一报告，记到 chapter_idx=0）
        try:
            mem_service.save_draft(project_id, "02-图谱", 0, output)
        except Exception:
            pass

        return {
            "ok": True,
            "stage": "generate",
            "incremental": bool(old_report),
            "output": output,
        }
    except Exception as e:
        return _fail("unknown", str(e))


def validate_report(project_id):
    """仅对 02-小说图谱报告.md 做格式校验。"""
    try:
        project_name = _get_project_name(project_id)
        output = _read_report(project_name)
        if output is None:
            return _fail("validate", f"找不到 {OUTPUT_DIR}/{REPORT_NAME}，请先生成")
        format_ok, format_errors = validator.validate(output)
        return {
            "ok": True,
            "stage": "validate",
            "format_ok": format_ok,
            "format_errors": format_errors,
        }
    except Exception as e:
        return _fail("unknown", str(e))


def review_report(project_id):
    """仅对 02-小说图谱报告.md 做 AI 审核。"""
    try:
        project_name = _get_project_name(project_id)
        output = _read_report(project_name)
        if output is None:
            return _fail("review", f"找不到 {OUTPUT_DIR}/{REPORT_NAME}，请先生成")
        generation = _load_generation()
        review_passed, review_detail = reviewer.review(generation or "", output)
        return {
            "ok": True,
            "stage": "review",
            "review_passed": review_passed,
            "review_detail": review_detail,
        }
    except Exception as e:
        return _fail("unknown", str(e))


def run(project_id):
    """向后兼容：整本生成一次图谱报告（若已有旧报告则增量更新），并自动校验+审核。"""
    r = generate_report(project_id)
    if not r.get("ok"):
        return r
    v = validate_report(project_id)
    rev = review_report(project_id)
    return {
        "ok": True,
        "incremental": r.get("incremental", False),
        "format_ok": v.get("format_ok", False),
        "format_errors": v.get("format_errors", []),
        "review_passed": rev.get("review_passed", False),
        "review_detail": rev.get("review_detail", ""),
        "output": r.get("output", ""),
    }


def _fail(stage, error):
    return {"ok": False, "stage": stage, "error": error}
