"""03-小说诊断 主流程（整本单一报告，无逐章）

输入：
  - 01-梗概/ 全部章合并  → 注入 {content}
  - 02-图谱/02-小说图谱报告.md → 注入 {context_图谱}
输出：
  - 03-诊断/03-小说诊断报告.md（整本单一报告）
"""
from pathlib import Path

from common import db, ai
from ai_rule import service as airule_service
from . import validator, reviewer
from novel_memory import service as mem_service

OUT_DIR = "03-诊断"
REPORT_NAME = "03-小说诊断报告.md"
FUNCTION_ID = "03-诊断"


def _proj_dir(project_id: int) -> Path:
    conn = db.get_conn()
    row = conn.execute(
        "SELECT name FROM novel_project WHERE id=?", (project_id,)
    ).fetchone()
    conn.close()
    if not row:
        raise ValueError(f"项目不存在：id={project_id}")
    return db.PROJECTS_DIR / row["name"]


def _merge_synopsis(proj_dir: Path) -> str:
    """合并 01-梗概 全部章为一份文本（无则空串）"""
    syn_dir = proj_dir / "01-梗概"
    if not syn_dir.exists():
        return ""
    parts = []
    for f in sorted(syn_dir.glob("第*.md")):
        parts.append(f.read_text(encoding="utf-8").strip())
    return "\n\n".join(parts)


def _read_graph(proj_dir: Path) -> str:
    """读取 02-图谱 报告（无则空串）"""
    g = proj_dir / "02-图谱" / "02-小说图谱报告.md"
    if g.exists():
        return g.read_text(encoding="utf-8").strip()
    return ""


def _read_report(proj_dir: Path) -> str:
    p = proj_dir / OUT_DIR / REPORT_NAME
    return p.read_text(encoding="utf-8") if p.exists() else None


def _write_report(proj_dir: Path, output: str):
    out = proj_dir / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    (out / REPORT_NAME).write_text(output, encoding="utf-8")


# ---------- 核心执行（三步可独立调用） ----------

def _build_prompt(proj_dir: Path):
    content = _merge_synopsis(proj_dir)
    context_graph = _read_graph(proj_dir)

    if not content:
        return None, {"ok": False, "stage": "input", "error": "未找到 01-梗概 产物，请先完成小说梗概"}

    generation = airule_service.resolve_rule_content('小说改写', FUNCTION_ID, 'generate')
    if not generation:
        return None, {"ok": False, "stage": "prompt", "error": "未找到 03-诊断 的 generation 指令"}

    prompt = (
        generation
        .replace("{content}", content)
        .replace("{context_图谱}", context_graph)
    )
    return prompt, context_graph


def generate_report(project_id: int):
    """仅生成整本诊断报告并落盘。"""
    try:
        proj_dir = _proj_dir(project_id)
    except ValueError as e:
        return {"ok": False, "stage": "project", "error": str(e)}

    prompt, err = _build_prompt(proj_dir)
    if prompt is None:
        return err

    try:
        output = ai.chat(prompt, airule=('小说改写', FUNCTION_ID, 'generate'))
    except Exception as e:
        return {"ok": False, "stage": "generate", "error": str(e)}

    _write_report(proj_dir, output)

    # 自动写入记忆库（整本单一报告，记到 chapter_idx=0）
    try:
        mem_service.save_draft(project_id, "03-诊断", 0, output)
    except Exception:
        pass

    return {
        "ok": True,
        "stage": "generate",
        "result_text": output,
        "missing_upstream": (not _read_graph(proj_dir)),
    }


def validate_report(project_id: int):
    """仅对 03-小说诊断报告.md 做格式校验。"""
    try:
        proj_dir = _proj_dir(project_id)
    except ValueError as e:
        return {"ok": False, "stage": "project", "error": str(e)}

    output = _read_report(proj_dir)
    if output is None:
        return {"ok": False, "stage": "validate", "error": f"找不到 {OUT_DIR}/{REPORT_NAME}，请先生成"}

    v = validator.validate(output)
    return {
        "ok": True,
        "stage": "validate",
        "validation": v,
    }


def review_report(project_id: int):
    """仅对 03-小说诊断报告.md 做 AI 审核。"""
    try:
        proj_dir = _proj_dir(project_id)
    except ValueError as e:
        return {"ok": False, "stage": "project", "error": str(e)}

    output = _read_report(proj_dir)
    if output is None:
        return {"ok": False, "stage": "review", "error": f"找不到 {OUT_DIR}/{REPORT_NAME}，请先生成"}

    prompt, _ = _build_prompt(proj_dir)
    generation = prompt if prompt else ""
    r = reviewer.review(generation, output)
    return {
        "ok": True,
        "stage": "review",
        "review": r,
    }


def run(project_id: int) -> dict:
    """向后兼容：生成 + 校验 + 审核一次性跑完。"""
    try:
        proj_dir = _proj_dir(project_id)
    except ValueError as e:
        return {"ok": False, "stage": "project", "error": str(e)}

    prompt, err = _build_prompt(proj_dir)
    if prompt is None:
        return err

    try:
        output = ai.chat(prompt, airule=('小说改写', FUNCTION_ID, 'generate'))
    except Exception as e:
        return {"ok": False, "stage": "generate", "error": str(e)}

    v = validator.validate(output)
    r = reviewer.review(prompt, output)

    _write_report(proj_dir, output)

    try:
        mem_service.save_draft(project_id, "03-诊断", 0, output)
    except Exception:
        pass

    return {
        "ok": True,
        "stage": "done",
        "result_text": output,
        "validation": v,
        "review": r,
        "missing_upstream": (not _read_graph(proj_dir)),
    }
