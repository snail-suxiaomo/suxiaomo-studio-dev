"""novel_synopsis/validator.py —— 梗概的格式硬校验（纯 Python，不读 py_format 文本）

py_format 列在库里只是「格式约定参考」，真正校验在这里写死。
规则对齐 novel_prompt_config 里 01-梗概 的 py_format 描述：
  1) 必须包含 12 个字段（「字段名：内容」格式）
  2) 「钩子」取值必须在枚举内
  3) 输出总字数最少 200
"""
import re

# 12 个必含字段（与 generation 产出字段一一对应）
REQUIRED_FIELDS = [
    "序号", "标题", "字数", "时间·场景", "POV", "出场人物",
    "300字梗概", "功能", "情绪", "钩子", "伏笔", "关键道具",
]

# 钩子允许值
HOOK_ENUM = ["悬念", "反转", "情感", "信息差", "无"]

# 总字数下限
MIN_TOTAL_CHARS = 200


def validate(text):
    """返回 (ok: bool, errors: list[str])"""
    errors = []
    text = text or ""

    # 1) 字段齐全
    for field in REQUIRED_FIELDS:
        pattern = r"^" + re.escape(field) + r"："
        if not re.search(pattern, text, re.MULTILINE):
            errors.append(f"缺少字段：{field}")

    # 2) 钩子枚举
    m = re.search(r"^钩子：(.*)$", text, re.MULTILINE)
    if m:
        val = m.group(1).strip()
        if val not in HOOK_ENUM:
            errors.append(f"钩子值「{val}」不在允许范围 {HOOK_ENUM}")

    # 3) 总字数最少
    stripped = re.sub(r"\s+", "", text)
    if len(stripped) < MIN_TOTAL_CHARS:
        errors.append(f"总字数不足 {MIN_TOTAL_CHARS}（当前约 {len(stripped)}）")

    return (len(errors) == 0, errors)
