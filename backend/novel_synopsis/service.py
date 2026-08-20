"""novel_synopsis/service.py —— 01-梗概主流程（无引擎）

流程：读 00-拆分/第N章.md → 拼 generation 提示词 → 调 ai.chat 生成
→ 可单独执行 validator 格式校验 → 可单独执行 reviewer AI 审核 → 写 01-梗概/第N章.md → 可选写报告。
"""
import re
from pathlib import Path
from datetime import datetime

from common import db
from common import ai
from ai_rule import service as airule_service
from . import validator, reviewer
from novel_memory import service as mem_service

FUNCTION_ID = "01-梗概"
SPLIT_DIR = "00-拆分"
OUTPUT_DIR = "01-梗概"


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


def _read_chapter(project_name, idx):
    """解析 00-拆分/第N章.md → {idx, title, content}"""
    path = db.PROJECTS_DIR / project_name / SPLIT_DIR / f"第{idx}章.md"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    title = ""
    content_lines = []
    in_body = False
    for ln in text.split("\n"):
        if ln.startswith("# "):
            title = ln[2:].strip()
            in_body = True
            continue
        if ln.strip() == "---":
            continue
        if in_body:
            content_lines.append(ln)
    content = "\n".join(content_lines).strip()
    # 去掉番外标注（> 所属：番外\n\n）
    content = content.replace("> 所属：番外\n\n", "").strip()
    return {"idx": idx, "title": title, "content": content}


def _read_output(project_name, idx):
    """读取 01-梗概/第N章.md 的 output 正文（去掉标题行）。"""
    path = db.PROJECTS_DIR / project_name / OUTPUT_DIR / f"第{idx}章.md"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    # 跳过标题行 # 第N章 · 《项目名》梗概
    body_lines = []
    started = False
    for ln in lines:
        if not started:
            if ln.startswith("# "):
                started = True
            continue
        body_lines.append(ln)
    return "\n".join(body_lines).strip()


def _write_output(project_name, idx, output):
    out_dir = db.PROJECTS_DIR / project_name / OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"第{idx}章.md").write_text(
        f"# 第{idx}章 · 《{project_name}》梗概\n\n{output}\n",
        encoding="utf-8",
    )


def list_chapters(project_id):
    """列出 00-拆分 下所有可处理的章（按章号升序）"""
    project_name = _get_project_name(project_id)
    d = db.PROJECTS_DIR / project_name / SPLIT_DIR
    chapters = []
    if d.exists():
        for f in sorted(d.glob("第*章*.md")):
            m = re.match(r"第(\d+)章", f.stem)
            if m:
                ch = _read_chapter(project_name, int(m.group(1)))
                if ch:
                    chapters.append(ch)
    return chapters


# ---------- 核心执行（三步可独立调用） ----------

def _prepare_prompt(project_name, chapter_idx):
    ch = _read_chapter(project_name, chapter_idx)
    if not ch:
        return None, _fail(chapter_idx, "generate", f"找不到 {SPLIT_DIR}/第{chapter_idx}章.md")
    generation = _load_generation()
    if not generation:
        return None, _fail(chapter_idx, "generate", "未配置 01-梗概 的 generation 指令")
    user_prompt = (
        generation
        .replace("{idx}", str(ch["idx"]))
        .replace("{title}", ch["title"])
        .replace("{content}", ch["content"])
    )
    return user_prompt, ch


def generate_chapter(project_id, chapter_idx):
    """仅生成单章梗概并落盘，不自动校验/审核。"""
    try:
        project_name = _get_project_name(project_id)
        user_prompt, ch_or_fail = _prepare_prompt(project_name, chapter_idx)
        if user_prompt is None:
            return ch_or_fail
        ch = ch_or_fail

        try:
            output = ai.chat(user_prompt, airule=('小说改写', FUNCTION_ID, 'generate'))
        except RuntimeError as e:
            return _fail(chapter_idx, "generate", str(e))

        _write_output(project_name, chapter_idx, output)

        # 自动写入记忆库（draft 草稿；失败不影响主流程）
        try:
            mem_service.save_draft(project_id, "01-梗概", chapter_idx, output)
        except Exception:
            pass

        return {
            "ok": True,
            "chapter_idx": chapter_idx,
            "title": ch["title"],
            "stage": "generate",
            "output": output,
        }
    except Exception as e:
        return _fail(chapter_idx, "unknown", str(e))


def validate_chapter(project_id, chapter_idx):
    """仅对 01-梗概/第N章.md 做格式校验。"""
    try:
        project_name = _get_project_name(project_id)
        output = _read_output(project_name, chapter_idx)
        if output is None:
            return _fail(chapter_idx, "validate", f"找不到 01-梗概/第{chapter_idx}章.md，请先生成")
        format_ok, format_errors = validator.validate(output)
        return {
            "ok": True,
            "chapter_idx": chapter_idx,
            "stage": "validate",
            "format_ok": format_ok,
            "format_errors": format_errors,
        }
    except Exception as e:
        return _fail(chapter_idx, "unknown", str(e))


def review_chapter(project_id, chapter_idx):
    """仅对 01-梗概/第N章.md 做 AI 审核。"""
    try:
        project_name = _get_project_name(project_id)
        user_prompt, ch_or_fail = _prepare_prompt(project_name, chapter_idx)
        if user_prompt is None:
            return ch_or_fail
        ch = ch_or_fail

        output = _read_output(project_name, chapter_idx)
        if output is None:
            return _fail(chapter_idx, "review", f"找不到 01-梗概/第{chapter_idx}章.md，请先生成")
        review_passed, review_detail = reviewer.review(user_prompt, output)
        return {
            "ok": True,
            "chapter_idx": chapter_idx,
            "title": ch["title"],
            "stage": "review",
            "review_passed": review_passed,
            "review_detail": review_detail,
        }
    except Exception as e:
        return _fail(chapter_idx, "unknown", str(e))


def run_chapter(project_id, chapter_idx):
    """向后兼容：生成 + 校验 + 审核一次性跑完。"""
    r = generate_chapter(project_id, chapter_idx)
    if not r.get("ok"):
        return r
    v = validate_chapter(project_id, chapter_idx)
    rev = review_chapter(project_id, chapter_idx)
    return {
        "ok": True,
        "chapter_idx": chapter_idx,
        "title": r.get("title"),
        "format_ok": v.get("format_ok", False),
        "format_errors": v.get("format_errors", []),
        "review_passed": rev.get("review_passed", False),
        "review_detail": rev.get("review_detail", ""),
        "output": r.get("output", ""),
    }


def run_all(project_id):
    """处理全部章，返回 {results, report_path}"""
    chapters = list_chapters(project_id)
    if not chapters:
        raise RuntimeError(f"该项目在 {SPLIT_DIR} 下没有可处理的章节")
    results = [run_chapter(project_id, ch["idx"]) for ch in chapters]
    report_path = _write_report(project_id, results)
    return {"results": results, "report_path": report_path}


# ---------- 报告 ----------

def _write_report(project_id, results):
    project_name = _get_project_name(project_id)
    out_dir = db.PROJECTS_DIR / project_name / OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# 01-小说梗概报告 · 《{project_name}》",
        "",
        f"- 生成时间：{now}",
        f"- 处理章节数：{len(results)}",
        "",
        "| 章号 | 标题 | 格式校验 | AI审核 | 备注 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in results:
        if not r.get("ok"):
            lines.append(f"| 第{r.get('chapter_idx')}章 | - | - | - | ❌ {r.get('error','')} |")
            continue
        fmt = "✅" if r.get("format_ok") else "⚠️"
        rev = "✅" if r.get("review_passed") else "⚠️"
        note = ""
        if not r.get("format_ok", True):
            note = "；".join(r.get("format_errors", []))
        elif not r.get("review_passed", True):
            note = "AI审核未通过"
        lines.append(f"| 第{r.get('chapter_idx')}章 | {r.get('title','')} | {fmt} | {rev} | {note} |")
    lines.append("")
    lines.append("> 每章梗概在 01-梗概/第N章.md；格式校验/AI审核未通过的章，产物仍已落盘，可手动修订。")
    report = out_dir / "01-小说梗概报告.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    return str(report)


def _fail(chapter_idx, stage, error):
    return {
        "ok": False,
        "chapter_idx": chapter_idx,
        "stage": stage,
        "error": error,
    }
