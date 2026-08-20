"""04-小说策略 主流程：读 03-诊断 → 拼 generation → AI 生成 → 可单独校验/审核 → 落盘。"""
import re
from common import db, ai
from ai_rule import service as airule_service
from . import validator, reviewer
from novel_memory import service as mem_service

OUT_DIR = "04-小说策略"
REPORT_NAME = "04-小说策略报告.md"
CONFIG_NAME = "项目配置.md"
FUNCTION_ID = "04-策略"

# 风格库（本工作台尚未建「风格配置」功能，先用内置默认库注入 {style_library}）
DEFAULT_STYLE_LIBRARY = """- 全局[写实] 国风写实：自然光为主，暖灰与黛青色调，宣纸与木石质感，适合古风正剧
- 全局[都市] 现代都市：硬光与霓虹冷暖对比，蓝灰都市色，玻璃金属质感，适合职场甜宠
- 全局[甜宠] 甜宠明亮：柔光高调，粉橘马卡龙色，绒布与甜点质感，适合轻喜甜剧
- 全局[悬疑] 悬疑暗调：低照度侧光，青蓝与墨黑，潮湿石墙质感，适合悬疑推理
- 全局[古装] 古装华丽：烛光金调，朱红鎏金色，绸缎织锦质感，适合宫斗权谋
（当前未单独配置风格库，以上为内置默认；后续可在「风格配置」中增删查改）"""


def _get_project(pid):
    conn = db.get_conn()
    row = conn.execute(
        "SELECT id, name FROM novel_project WHERE id=?", (pid,)
    ).fetchone()
    conn.close()
    return row


def _read_report(proj):
    p = proj / OUT_DIR / REPORT_NAME
    return p.read_text(encoding="utf-8") if p.exists() else None


def _build_inputs(proj):
    # 输入：03-诊断 报告
    diag = proj / "03-诊断" / "03-小说诊断报告.md"
    if not diag.exists():
        return None, {"ok": False, "stage": "input",
                "error": "缺少 03-诊断 报告，请先执行 03-小说诊断"}
    content = diag.read_text(encoding="utf-8")

    # 书名 / 风格库
    book = proj.name
    style_library = DEFAULT_STYLE_LIBRARY

    generation = airule_service.resolve_rule_content('小说改写', FUNCTION_ID, 'generate')
    if not generation:
        return None, {"ok": False, "stage": "prompt",
                "error": "未配置 04-策略 的 generation 指令"}

    prompt = (generation
               .replace("{content}", content)
               .replace("{style_library}", style_library)
               .replace("{书名}", book)
               .replace("{config}", ""))  # 防御性：本阶段尚无 config
    return prompt, None


# ---------- 核心执行（三步可独立调用） ----------

def generate_report(project_id):
    """仅生成 04-小说策略报告 并落盘。"""
    try:
        row = _get_project(project_id)
        if not row:
            return {"ok": False, "stage": "input", "error": "项目不存在"}
        pid, pname = row["id"], row["name"]
        proj = db.PROJECTS_DIR / pname

        prompt, err = _build_inputs(proj)
        if prompt is None:
            return err

        try:
            raw = ai.chat(prompt, airule=('小说改写', FUNCTION_ID, 'generate'))
        except Exception as e:
            return {"ok": False, "stage": "generate", "error": f"AI 生成调用失败：{e}"}

        # 落盘：策略报告
        out = proj / OUT_DIR
        out.mkdir(parents=True, exist_ok=True)
        report_path = out / REPORT_NAME
        report_path.write_text(raw, encoding="utf-8")

        # 自动写入记忆库（整本单一报告，记到 chapter_idx=0）
        try:
            mem_service.save_draft(project_id, "04-策略", 0, raw)
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
    """仅对 04-小说策略报告.md 做格式校验。"""
    try:
        row = _get_project(project_id)
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
    """仅对 04-小说策略报告.md 做 AI 审核。"""
    try:
        row = _get_project(project_id)
        if not row:
            return {"ok": False, "stage": "input", "error": "项目不存在"}
        proj = db.PROJECTS_DIR / row["name"]
        raw = _read_report(proj)
        if raw is None:
            return {"ok": False, "stage": "review", "error": f"找不到 {OUT_DIR}/{REPORT_NAME}，请先生成"}
        prompt, _ = _build_inputs(proj)
        r = reviewer.review(prompt or "", raw)
        return {
            "ok": True,
            "stage": "review",
            "review": r,
        }
    except Exception as e:
        return {"ok": False, "stage": "unknown", "error": str(e)}


def run(project_id, user_prompt=""):
    """向后兼容：执行 04-小说策略，并自动校验+审核。"""
    r = generate_report(project_id)
    if not r.get("ok"):
        return r
    proj = db.PROJECTS_DIR / _get_project(project_id)["name"]
    raw = _read_report(proj)
    v = validator.validate(raw)
    rev = reviewer.review(user_prompt or r.get("result_text", ""), raw)

    # 抽取 CONFIG 块 → 项目根目录 项目配置.md（下游 {config} 来源）
    config_path = None
    m = re.search(r"<<<CONFIG_START>>>\s*(.*?)\s*<<<CONFIG_END>>>", raw, re.S)
    if m:
        cfg_text = m.group(1).strip()
        (proj / CONFIG_NAME).write_text(cfg_text, encoding="utf-8")
        config_path = str(proj / CONFIG_NAME)

    return {
        "ok": True,
        "stage": "done",
        "validation": v,
        "review": rev,
        "report_path": str(proj / OUT_DIR / REPORT_NAME),
        "config_path": config_path,
        "result_text": raw,
    }
