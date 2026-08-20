"""06-改写 主流程（逐章 per-chapter）。"""
import re
from common import ai, db
from ai_rule import service as airule_service
from . import validator, reviewer
from novel_memory import service as mem_service

SPLIT_DIR = "00-拆分"
OUT_DIR = "06-改写"
REPORT_NAME = "06-小说改写报告.md"
CONFIG_NAME = "项目配置.md"
SUMMARY_DIR = "05-小说总表"
SUMMARY_NAME = "05-小说总表.md"
FUNCTION_ID = "06-改写"
MEMORY_DEPTH = 2


def _chap_num(name):
    m = re.search(r"第(\d+)章", name)
    return int(m.group(1)) if m else 0


def _parse_title_body(text):
    title = ""
    body_lines = []
    in_body = False
    for ln in text.split("\n"):
        if ln.startswith("# "):
            title = ln[2:].strip()
            in_body = True
            continue
        if not in_body:
            continue
        if ln.strip() == "---":
            continue
        body_lines.append(ln)
    return title, "\n".join(body_lines).strip()


def _read_split_chapters(proj):
    d = proj / SPLIT_DIR
    if not d.exists():
        return []
    files = sorted(d.glob("第*章*.md"), key=lambda p: _chap_num(p.name))
    out = []
    for f in files:
        idx = _chap_num(f.name)
        text = f.read_text(encoding="utf-8")
        title, body = _parse_title_body(text)
        out.append({"idx": idx, "title": title, "body": body})
    return out


def _read_memory(proj, idx):
    """前 MEMORY_DEPTH 章改写正文（上下文衔接）。"""
    parts = []
    for k in range(max(1, idx - MEMORY_DEPTH), idx):
        p = proj / OUT_DIR / f"第{k}章.md"
        if p.exists():
            parts.append(p.read_text(encoding="utf-8"))
    return "\n\n".join(parts)


def _read_output(proj, idx):
    p = proj / OUT_DIR / f"第{idx}章.md"
    return p.read_text(encoding="utf-8") if p.exists() else None


def _get_chapter(project_id, idx):
    conn = db.get_conn()
    row = conn.execute("SELECT id, name FROM novel_project WHERE id=?", (project_id,)).fetchone()
    conn.close()
    if not row:
        raise ValueError("项目不存在")
    proj = db.PROJECTS_DIR / row["name"]
    chapters = _read_split_chapters(proj)
    chap = next((c for c in chapters if c["idx"] == idx), None)
    if not chap:
        raise ValueError(f"未找到 00-拆分 第{idx}章")
    return row["name"], proj, chap


def _build_prompt(proj, chap, idx):
    cfg_path = proj / CONFIG_NAME
    config = cfg_path.read_text(encoding="utf-8") if cfg_path.exists() else ""

    sum_path = proj / SUMMARY_DIR / SUMMARY_NAME
    context_summary = sum_path.read_text(encoding="utf-8") if sum_path.exists() else ""

    memory = _read_memory(proj, idx)

    generation = airule_service.resolve_rule_content('小说改写', FUNCTION_ID, 'generate')
    if not generation:
        raise ValueError(f"未配置 {FUNCTION_ID} 的 generation 指令")

    prompt = generation
    prompt = prompt.replace("{content}", chap["body"])
    prompt = prompt.replace("{config}", config)
    prompt = prompt.replace("{context_总表}", context_summary)
    prompt = prompt.replace("{idx}", str(idx))
    prompt = prompt.replace("{title}", chap["title"])
    prompt = prompt.replace("{记忆_前情}", memory)
    return prompt


# ---------- 核心执行（三步可独立调用） ----------

def generate_chapter(project_id, chapter_idx):
    """仅生成单章改写并落盘。"""
    try:
        pname, proj, chap = _get_chapter(project_id, chapter_idx)
        prompt = _build_prompt(proj, chap, chapter_idx)
    except ValueError as e:
        return {"ok": False, "chapter_idx": chapter_idx, "stage": "input", "error": str(e)}
    except Exception as e:
        return {"ok": False, "chapter_idx": chapter_idx, "stage": "input", "error": str(e)}

    try:
        raw = ai.chat(prompt, airule=('小说改写', '06-改写', 'generate'))
    except Exception as e:
        return {"ok": False, "chapter_idx": chapter_idx, "stage": "generate", "error": f"AI 生成调用失败：{e}"}

    out = proj / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / f"第{chapter_idx}章.md"
    report_path.write_text(raw, encoding="utf-8")

    # 自动写入记忆库（draft 草稿）
    try:
        mem_service.save_draft(project_id, "06-改写", chapter_idx, raw)
    except Exception:
        pass

    return {
        "ok": True,
        "chapter_idx": chapter_idx,
        "title": chap["title"],
        "stage": "generate",
        "result_text": raw,
        "report_path": str(report_path),
    }


def validate_chapter(project_id, chapter_idx):
    """仅对 06-改写/第N章.md 做格式校验。"""
    try:
        pname, proj, chap = _get_chapter(project_id, chapter_idx)
    except ValueError as e:
        return {"ok": False, "chapter_idx": chapter_idx, "stage": "input", "error": str(e)}
    except Exception as e:
        return {"ok": False, "chapter_idx": chapter_idx, "stage": "input", "error": str(e)}

    raw = _read_output(proj, chapter_idx)
    if raw is None:
        return {"ok": False, "chapter_idx": chapter_idx, "stage": "validate", "error": f"找不到 {OUT_DIR}/第{chapter_idx}章.md，请先生成"}

    v = validator.validate(raw)
    return {
        "ok": True,
        "chapter_idx": chapter_idx,
        "stage": "validate",
        "validation": v,
    }


def review_chapter(project_id, chapter_idx):
    """仅对 06-改写/第N章.md 做 AI 审核。"""
    try:
        pname, proj, chap = _get_chapter(project_id, chapter_idx)
    except ValueError as e:
        return {"ok": False, "chapter_idx": chapter_idx, "stage": "input", "error": str(e)}
    except Exception as e:
        return {"ok": False, "chapter_idx": chapter_idx, "stage": "input", "error": str(e)}

    raw = _read_output(proj, chapter_idx)
    if raw is None:
        return {"ok": False, "chapter_idx": chapter_idx, "stage": "review", "error": f"找不到 {OUT_DIR}/第{chapter_idx}章.md，请先生成"}

    try:
        prompt = _build_prompt(proj, chap, chapter_idx)
    except Exception as e:
        prompt = ""

    r = reviewer.review(prompt, raw)
    return {
        "ok": True,
        "chapter_idx": chapter_idx,
        "stage": "review",
        "review": r,
    }


def run(project_id, chapter_idx, user_prompt=""):
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
        "validation": v.get("validation", {}),
        "review": rev.get("review", {}),
        "report_path": r.get("report_path"),
        "result_text": r.get("result_text", ""),
    }


def run_all(project_id, user_prompt=""):
    try:
        conn = db.get_conn()
        row = conn.execute("SELECT id, name FROM novel_project WHERE id=?", (project_id,)).fetchone()
        conn.close()
        if not row:
            return {"ok": False, "stage": "input", "error": "项目不存在"}
        pid, pname = row["id"], row["name"]
        proj = db.PROJECTS_DIR / pname
        chapters = _read_split_chapters(proj)
        if not chapters:
            return {"ok": False, "stage": "input", "error": "缺少 00-拆分 章节，请先上传拆分"}
    except Exception as e:
        return {"ok": False, "stage": "input", "error": str(e)}
    results = [run(project_id, c["idx"], user_prompt) for c in chapters]
    out = proj / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / REPORT_NAME
    report_path.write_text(
        "\n\n---\n\n".join(r.get("result_text", "") for r in results if r.get("ok")),
        encoding="utf-8",
    )
    return {"ok": True, "stage": "done", "count": len(results),
            "results": results, "report_path": str(report_path)}


def list_chapters(project_id):
    try:
        conn = db.get_conn()
        row = conn.execute("SELECT id, name FROM novel_project WHERE id=?", (project_id,)).fetchone()
        conn.close()
        if not row:
            return []
        proj = db.PROJECTS_DIR / row["name"]
        chapters = _read_split_chapters(proj)
        out = []
        for c in chapters:
            p = proj / OUT_DIR / f"第{c['idx']}章.md"
            out.append({"idx": c["idx"], "title": c["title"], "rewritten": p.exists()})
        return out
    except Exception:
        return []
