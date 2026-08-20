"""ai_rule/validator.py —— 请求体校验

职责：校验 HTTP 接口入参（新建/编辑规则的字段合法性）。
仅做字段级校验，不涉及数据库查询。
"""


def validate_payload(data: dict) -> bool:
    """校验规则新建/编辑的请求体，非法时抛 ValueError。"""
    if not isinstance(data, dict):
        raise ValueError('请求体必须是 JSON 对象')

    name = (data.get('name') or '').strip()
    if not name:
        raise ValueError('规则名称不能为空')

    thinking = data.get('thinking')
    # thinking 合法值是「模型相关的」（跟随所选模型 profile.modes 里的 key，如 fast/expert），
    # 这里只做基础校验：必须是非空字符串（follow 恒合法）。
    if thinking is not None and (not isinstance(thinking, str) or not thinking.strip()):
        raise ValueError('thinking 必须是非空字符串（如 follow / fast / expert）')

    strength = data.get('strength')
    if strength is not None and strength != '':
        if strength not in ('follow', 'low', 'medium', 'high'):
            raise ValueError('strength 必须为 follow / low / medium / high')

    menu = (data.get('menu') or '').strip()
    if not menu:
        raise ValueError('菜单不能为空')

    function_key = (data.get('function_key') or '').strip()
    if not function_key:
        raise ValueError('function_key（具体功能）不能为空')

    role = (data.get('role') or '').strip()
    if not role:
        raise ValueError('role（规则角色）不能为空')

    return True


def validate_update(data: dict) -> bool:
    """校验「编辑规则」请求体（仅校验请求中出现的字段，其余沿用原值）。

    编辑接口用 exclude_unset 只传改动字段，故不可要求 name/menu 等全量存在。
    """
    if not isinstance(data, dict):
        raise ValueError('请求体必须是 JSON 对象')

    if 'name' in data and not (data.get('name') or '').strip():
        raise ValueError('规则名称不能为空')

    if 'thinking' in data and data['thinking'] is not None:
        if not isinstance(data['thinking'], str) or not data['thinking'].strip():
            raise ValueError('thinking 必须是非空字符串（如 follow / fast / expert）')

    if 'strength' in data and data['strength'] is not None and data['strength'] != '':
        if data['strength'] not in ('follow', 'low', 'medium', 'high'):
            raise ValueError('strength 必须为 follow / low / medium / high')

    if 'menu' in data and not (data.get('menu') or '').strip():
        raise ValueError('菜单不能为空')

    if 'function_key' in data and not (data.get('function_key') or '').strip():
        raise ValueError('function_key（具体功能）不能为空')

    if 'role' in data and not (data.get('role') or '').strip():
        raise ValueError('role（规则角色）不能为空')

    return True
