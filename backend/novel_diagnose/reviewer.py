"""03-小说诊断 AI 审核（读 ai_content 当审核 prompt，temperature=0）

ai_content 模板使用占位符：
  {user_prompt}  ← 注入本次实际使用的 generation 指令（含真实梗概/图谱事实）
  {ai_output}    ← 注入 AI 生成的诊断报告
审核员返回首行 PASS / FAIL。
"""
from common import ai
from ai_rule import service as airule_service


def review(generation_prompt: str, ai_output: str) -> dict:
    """返回 {"ok": bool, "passed": bool|None, "raw": str}"""
    ai_content = airule_service.resolve_rule_content('小说改写', "03-诊断", 'review')
    if not ai_content:
        return {"ok": True, "passed": True, "raw": "（无 ai_content 配置，跳过审核）"}

    prompt = (
        ai_content
        .replace("{user_prompt}", generation_prompt)
        .replace("{ai_output}", ai_output)
    )
    try:
        raw = ai.chat(prompt, airule=('小说改写', '03-诊断', 'review'))
    except Exception as e:  # 审核失败不阻断主流程，仅标记
        return {"ok": False, "passed": None, "raw": f"审核调用失败：{e}"}

    passed = raw.strip().upper().startswith("PASS")
    return {"ok": True, "passed": passed, "raw": raw}
