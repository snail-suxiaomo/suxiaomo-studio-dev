"""05-小说总表 格式校验（纯 Python，不读 py_format 文本执行）。

对齐 novel_prompt_config 中 05-总表 的 py_format：
- 包含文本：总集数：
- 字段枚举：节奏=(开场钩子|铺垫|升级|高潮|反转|收束|过场)
- 总字数最少：50
"""
import re

REQUIRED_TEXTS = ["总集数："]
RHYTHM_ENUM = ["开场钩子", "铺垫", "升级", "高潮", "反转", "收束", "过场"]
MIN_CHARS = 50


def validate(text):
    text = text or ""
    errors = []

    for t in REQUIRED_TEXTS:
        if t not in text:
            errors.append(f"缺少必要文本：{t}")

    # 节奏 枚举（每行 节奏：X，X 后可能跟 | 或行尾）
    rhythms = re.findall(r"节奏：([^|\n]+)", text)
    bad = [r.strip() for r in rhythms if r.strip() not in RHYTHM_ENUM]
    if bad:
        errors.append("节奏 取值不合法（须为 开场钩子/铺垫/升级/高潮/反转/收束/过场）：" + " / ".join(bad))

    n = len(text.strip())
    if n < MIN_CHARS:
        errors.append(f"总字数不足（{n}/{MIN_CHARS}）")

    return {"ok": len(errors) == 0, "errors": errors}
