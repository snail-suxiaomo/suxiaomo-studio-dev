"""novel_graph/validator.py —— 图谱报告的格式硬校验（纯 Python，不读 py_format 文本）

对齐 novel_prompt_config 里 02-图谱 的 py_format：
  1) 必须包含若干标志性文本（标题/居中分隔/编号前缀/统计行）
  2) 总字数最少 300
"""
import re

REQUIRED_TEXTS = [
    "## 人物总览",
    "## 场景分布",
    "## 伏笔追踪",
    "|:--:|",
    "本表共",
    "G-C",
    "G-S",
    "G-V",
]

MIN_TOTAL_CHARS = 300


def validate(text):
    """返回 (ok: bool, errors: list[str])"""
    errors = []
    text = text or ""
    for t in REQUIRED_TEXTS:
        if t not in text:
            errors.append(f"缺少必要文本：{t}")
    if len(re.sub(r"\s+", "", text)) < MIN_TOTAL_CHARS:
        errors.append(f"总字数不足 {MIN_TOTAL_CHARS}")
    return (len(errors) == 0, errors)
