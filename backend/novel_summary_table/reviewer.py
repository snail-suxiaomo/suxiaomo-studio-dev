"""05-小说总表 AI 审核（读 ai_content 当审核 prompt，temperature=0）。"""
from common import ai
from ai_rule import service as airule_service

FUNCTION_ID = "05-总表"


def review(user_prompt, ai_output):
    ai_content = airule_service.resolve_rule_content('小说改写', FUNCTION_ID, 'review')
    if not ai_content:
        return {"ok": True, "raw": "", "passed": None, "note": "未配置 ai_content，跳过 AI 审核"}

    prompt = ai_content
    prompt = prompt.replace("{user_prompt}", user_prompt or "")
    prompt = prompt.replace("{ai_output}", ai_output or "")

    try:
        resp = ai.chat(prompt, airule=('小说改写', '05-总表', 'review'))
    except Exception as e:
        return {"ok": False, "raw": "", "passed": None, "error": f"AI 审核调用失败：{e}"}

    raw = (resp or "").strip()
    first = raw.splitlines()[0].strip().upper() if raw else ""
    passed = first.startswith("PASS")
    return {"ok": True, "raw": raw, "passed": passed}
