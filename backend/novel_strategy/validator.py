"""04-小说策略 格式校验（纯 Python，不读 py_format 文本执行）。

对齐 novel_prompt_config 中 04-策略 的 py_format：
- 包含文本：综合评级 / 视觉风格 / 取舍策略
- 包含标记：<<<CONFIG_START>>> / <<<CONFIG_END>>>
- 配置块 5 字段必含：单集时长 / 总集数 / 视觉风格 / 视觉风格Prompt / 取舍策略
- 枚举：单集时长=(1 分钟|1.5 分钟|3 分钟|5 分钟|自定义)
- 枚举：取舍策略=([A]|[B]|A 激进|B 标准)
- 总字数最少：200
"""
import re

REQUIRED_TEXTS = [
    "综合评级",
    "视觉风格",
    "取舍策略",
    "<<<CONFIG_START>>>",
    "<<<CONFIG_END>>>",
    "单集时长",
    "总集数",
    "视觉风格Prompt",
]

DURATION_ENUM = ["1 分钟", "1.5 分钟", "3 分钟", "5 分钟", "自定义"]
STRATEGY_ENUM = [r"\[A\] 激进", r"\[B\] 标准", "A 激进", "B 标准", r"\[A\]", r"\[B\]"]

MIN_CHARS = 200


def validate(text):
    text = text or ""
    errors = []

    # 1) 必要文本
    for t in REQUIRED_TEXTS:
        if t not in text:
            errors.append(f"缺少必要文本：{t}")

    # 2) 单集时长 枚举
    if not re.search(r"单集时长[:：]\s*(1 分钟|1\.5 分钟|3 分钟|5 分钟|自定义)", text):
        errors.append("单集时长 取值不合法（须为 1 / 1.5 / 3 / 5 分钟 或 自定义）")

    # 3) 取舍策略 枚举
    if not re.search(r"取舍策略[:：]\s*(\[A\] 激进|\[B\] 标准|A 激进|B 标准|\[A\]|\[B\])", text):
        errors.append("取舍策略 取值不合法（须为 [A]激进 / [B]标准）")

    # 4) 字数下限
    n = len(text.strip())
    if n < MIN_CHARS:
        errors.append(f"总字数不足（{n}/{MIN_CHARS}）")

    return {"ok": len(errors) == 0, "errors": errors}
