"""ai_rule/reviewer.py —— 规则审查

职责：
1. review_imported_rule：审查从 workspace/AI调用规则/ 文件解析出的规则项是否合规
   （必填项、枚举值），供 service 的 seed / 重置流程调用。
2. can_delete：判断某条规则是否允许删除（内置规则受保护）。
"""


def review_imported_rule(rule: dict) -> tuple:
    """审查从文件导入的规则项。

    返回 (ok: bool, errors: list[str])。仅做必填与枚举校验，不做 DB 存在性检查。
    """
    errors = []
    if not (rule.get('menu') or '').strip():
        errors.append('菜单不能为空')
    if not (rule.get('function_key') or '').strip():
        errors.append('function_key 不能为空')
    if not (rule.get('role') or '').strip():
        errors.append('role 不能为空')
    if not rule.get('name') or not str(rule.get('name')).strip():
        errors.append('name 不能为空')
    # thinking 合法值是模型相关的（follow/fast/expert 或模型自定义 modes key），只做基础校验
    if rule.get('thinking') is None or not str(rule.get('thinking', '')).strip():
        errors.append('thinking 不能为空')
    return (len(errors) == 0, errors)


def can_delete(rule: dict) -> tuple:
    """判断规则是否可删除。返回 (ok: bool, reason: str)。"""
    if rule.get('is_builtin'):
        return (False, '内置默认规则不可删除（可编辑后沿用）')
    return (True, '')
