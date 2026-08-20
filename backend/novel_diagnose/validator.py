"""03-小说诊断 格式校验（纯 Python，不读 py_format 文本执行）

对齐 novel_prompt_config 中 03-诊断 的 py_format：
  包含文本：综合评级： / D1~D7
  字段格式：综合评级=[SABCD]
  总字数最少：200
"""


# 必须出现的文本锚点（七维 + 综合评级行）
REQUIRED_TEXTS = [
    "综合评级：",
    "D1", "D2", "D3", "D4", "D5", "D6", "D7",
]
MIN_CHARS = 200


def validate(text: str) -> dict:
    """返回 {"ok": bool, "problems": [str, ...]}"""
    problems = []
    if not text or not text.strip():
        return {"ok": False, "problems": ["内容为空"]}

    for anchor in REQUIRED_TEXTS:
        if anchor not in text:
            problems.append(f"缺少必要文本：{anchor}")

    # 综合评级合法取值 [S/A/B/C/D]
    import re
    m = re.search(r"综合评级[：:]\s*([SABCD])", text)
    if not m:
        problems.append("未找到合法的「综合评级：[S/A/B/C/D]」")

    total = len(text.strip())
    if total < MIN_CHARS:
        problems.append(f"总字数不足：{total} < {MIN_CHARS}")

    return {"ok": len(problems) == 0, "problems": problems}
