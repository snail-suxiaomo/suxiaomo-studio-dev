"""06-改写 格式校验（纯 Python，不读 py_format 文本执行）。

对齐 novel_prompt_config 中 06-改写 的 py_format：
- 包含文本：# 第（标题行） / ---（分隔） / 溯源（溯源段） / C级注入（溯源段字段）
- 总字数最少：300
- 总字数最多：2500
"""
import re

REQUIRED_TEXTS = ["# 第", "---", "溯源", "C级注入"]
MIN_CHARS = 300
MAX_CHARS = 2500


def validate(text):
    text = text or ""
    errors = []

    for t in REQUIRED_TEXTS:
        if t not in text:
            errors.append(f"缺少必要文本：{t}")

    n = len(text.strip())
    if n < MIN_CHARS:
        errors.append(f"总字数不足（{n}/{MIN_CHARS}）")
    if n > MAX_CHARS:
        errors.append(f"总字数超出上限（{n}/{MAX_CHARS}）")

    return {"ok": len(errors) == 0, "errors": errors}
