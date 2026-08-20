"""novel_graph/reviewer.py —— 用 AI 审核图谱报告质量（读 ai_content 当审核 prompt）

ai_content 列在库里可编辑；本文件把它当「给审核员的提示词」去调 ai.chat(temperature=0, func_key='02-图谱', cfg_type='ai_content')。
解析逻辑就两行（看首行是不是 PASS/FAIL）。
"""
from common import db
from common import ai
from ai_rule import service as airule_service

FUNCTION_ID = "02-图谱"


def _load_ai_content():
    return airule_service.resolve_rule_content('小说改写', FUNCTION_ID, 'review')


def review(user_prompt, ai_output):
    """返回 (passed: bool, detail: str)"""
    ai_content = _load_ai_content()
    if not ai_content:
        return (True, "（未配置 ai_content，跳过 AI 审核）")

    review_prompt = (
        ai_content
        .replace("{user_prompt}", user_prompt)
        .replace("{ai_output}", ai_output)
    )

    try:
        resp = ai.chat(review_prompt, temperature=0, airule=('小说改写', '02-图谱', 'review'))
    except RuntimeError as e:
        return (False, f"审核调用模型失败：{e}")

    first_line = resp.strip().split("\n", 1)[0].strip().strip("`").strip().upper()
    if first_line.startswith("PASS"):
        return (True, resp.strip())
    if first_line.startswith("FAIL"):
        return (False, resp.strip())
    return (False, f"审核返回格式异常（首行非 PASS/FAIL）：\n{resp.strip()}")
