"""05-小说总表 主流程。"""
import re
from common import ai, db
from ai_rule import service as airule_service
from . import validator, reviewer
from novel_memory import service as mem_service

OUT_DIR = "05-小说总表"
REPORT_NAME = "05-小说总表.md"
CONFIG_NAME = "项目配置.md"
FUNCTION_ID = "05-总表"


def _chap_num(name):
    m = re.search(r"第(\d+)章", name)
    return int(m.group(1)) if m else 0


def _read_chapters(proj):
    """合并 00-拆分 全部章为正文（{idx}=0 起始由 generation 约定）。"""
    d = proj / "00-拆分"
    if not d.exists():
        return None
    files = sorted(d.glob("第*章*.md"), key=lambda p: _chap_num(p.name))
    if not files:
        return None
    return "\n\n".join(f.read_text(encoding="utf-8") for f in files)


def _read_report(proj):
    p = proj / OUT_DIR / REPORT_NAME
    return p.read_text(encoding="utf-8") if p.exists() else None


def _build_inputs(proj):
    # 1) 全章合并
    content = _read_chapters(proj)
    if not content:
        return None, {"ok": False, "stage": "input", "error": "缺少 00-拆分 章节，请先上传拆分"}

    # 2) 项目配置.md（{config}）
    cfg_path = proj / CONFIG_NAME
    if not cfg_path.exists():
        return None, {"ok": False, "stage": "input", "error": "缺少 项目配置.md，请先执行 04-小说策略"}
    config = cfg_path.read_text(encoding="utf-8")

    # 3) 04-小说策略报告（{context_策略}）
    strat = proj / "04-小说策略" / "04-小说策略报告.md"
    if not strat.exists():
        return None, {"ok": False, "stage": "input", "error": "缺少 04-小说策略报告，请先执行 04-小说策略"}
    context_strategy = strat.read_text(encoding="utf-8")

    # 4) 03-小说诊断报告（{context_诊断}）
    diag = proj / "03-诊断" / "03-小说诊断报告.md"
    if not diag.exists():
        return None, {"ok": False, "stage": "input", "error": "缺少 03-小说诊断报告，请先执行 03-小说诊断"}
    context_diag = diag.read_text(encoding="utf-8")

    # 5) generation + 占位符注入
    generation = airule_service.resolve_rule_content('小说改写', FUNCTION_ID, 'generate')
    if not generation:
        return None, {"ok": False, "stage": "prompt", "error": f"未配置 {FUNCTION_ID} 的 generation 指令"}
    prompt = generation
    prompt = prompt.replace("{content}", content)
    prompt = prompt.replace("{config}", config)
    prompt = prompt.replace("{context_策略}", context_strategy)
    prompt = prompt.replace("{context_诊断}", context_diag)
    prompt = prompt.replace("{idx}", "0")
    return prompt, None


# ---------- 核心执行（三步可独立调用） ----------

def generate_report(project_id):
    """仅生成 05-小说总表 并落盘。"""
    try:
        conn = db.get_conn()
        row = conn.execute("SELECT id, name FROM novel_project WHERE id=?", (project_id,)).fetchone()
        conn.close()
        if not row:
            return {"ok": False, "stage": "input", "error": "项目不存在"}
        pid, pname = row["id"], row["name"]
        proj = db.PROJECTS_DIR / pname

        prompt, err = _build_inputs(proj)
        if prompt is None:
            return err

        try:
            raw = ai.chat(prompt, airule=('小说改写', '05-总表', 'generate'))
        except Exception as e:
            return {"ok": False, "stage": "generate", "error": f"AI 生成调用失败：{e}"}

        out = proj / OUT_DIR
        out.mkdir(parents=True, exist_ok=True)
        report_path = out / REPORT_NAME
        report_path.write_text(raw, encoding="utf-8")

        # 自动写入记忆库（整本单一报告，记到 chapter_idx=0）
        try:
            mem_service.save_draft(project_id, "05-总表", 0, raw)
        except Exception:
            pass

        return {
            "ok": True,
            "stage": "generate",
            "result_text": raw,
            "report_path": str(report_path),
        }
    except Exception as e:
        return {"ok": False, "stage": "unknown", "error": str(e)}


def validate_report(project_id):
    """仅对 05-小说总表.md 做格式校验。"""
    try:
        conn = db.get_conn()
        row = conn.execute("SELECT id, name FROM novel_project WHERE id=?", (project_id,)).fetchone()
        conn.close()
        if not row:
            return {"ok": False, "stage": "input", "error": "项目不存在"}
        proj = db.PROJECTS_DIR / row["name"]
        raw = _read_report(proj)
        if raw is None:
            return {"ok": False, "stage": "validate", "error": f"找不到 {OUT_DIR}/{REPORT_NAME}，请先生成"}
        v = validator.validate(raw)
        return {
            "ok": True,
            "stage": "validate",
            "validation": v,
        }
    except Exception as e:
        return {"ok": False, "stage": "unknown", "error": str(e)}


def review_report(project_id):
    """仅对 05-小说总表.md 做 AI 审核。"""
    try:
        conn = db.get_conn()
        row = conn.execute("SELECT id, name FROM novel_project WHERE id=?", (project_id,)).fetchone()
        conn.close()
        if not row:
            return {"ok": False, "stage": "input", "error": "项目不存在"}
        proj = db.PROJECTS_DIR / row["name"]
        raw = _read_report(proj)
        if raw is None:
            return {"ok": False, "stage": "review", "error": f"找不到 {OUT_DIR}/{REPORT_NAME}，请先生成"}
        r = reviewer.review("", raw)
        return {
            "ok": True,
            "stage": "review",
            "review": r,
        }
    except Exception as e:
        return {"ok": False, "stage": "unknown", "error": str(e)}


def run(project_id, user_prompt=""):
    """向后兼容：生成 + 校验 + 审核一次性跑完。"""
    try:
        conn = db.get_conn()
        row = conn.execute("SELECT id, name FROM novel_project WHERE id=?", (project_id,)).fetchone()
        conn.close()
        if not row:
            return {"ok": False, "stage": "input", "error": "项目不存在"}
        pid, pname = row["id"], row["name"]
        proj = db.PROJECTS_DIR / pname

        prompt, err = _build_inputs(proj)
        if prompt is None:
            return err
    except Exception as e:
        return {"ok": False, "stage": "input", "error": str(e)}

    try:
        raw = ai.chat(prompt, airule=('小说改写', '05-总表', 'generate'))
    except Exception as e:
        return {"ok": False, "stage": "generate", "error": f"AI 生成调用失败：{e}"}

    v = validator.validate(raw)
    r = reviewer.review(user_prompt, raw)

    out = proj / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / REPORT_NAME
    report_path.write_text(raw, encoding="utf-8")

    # 自动写入记忆库（整本单一报告，记到 chapter_idx=0）
    try:
        mem_service.save_draft(project_id, "05-总表", 0, raw)
    except Exception:
        pass

    # 6) 回写总集数到 项目配置.md（让 {config} 真正闭环）
    written_back = False
    m = re.search(r"总集数：\s*(\d+)", raw)
    total = m.group(1) if m else None
    if m and (proj / CONFIG_NAME).exists():
        cfg_path = proj / CONFIG_NAME
        cfg_text = cfg_path.read_text(encoding="utf-8")
        new_cfg = re.sub(r"总集数[:：].*", f"总集数: {total}", cfg_text, count=1)
        cfg_path.write_text(new_cfg, encoding="utf-8")
        written_back = True

    return {
        "ok": True,
        "stage": "done",
        "validation": v,
        "review": r,
        "report_path": str(report_path),
        "total_episodes": total,
        "config_written_back": written_back,
        "result_text": raw,
    }
