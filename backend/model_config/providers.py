"""model_config/providers.py —— 模型厂商/模型档案能力模板

把「哪家厂商有哪些模型、每个模型支持什么参数」做成一份数据库字典，
前后端共享。新增模型时优先改这里，而不是去改 ai.py 的 if-else。
"""
import json
from typing import Optional

from common import db


def list_providers():
    """返回所有厂商（按 sort_order 升序）"""
    conn = db.get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM model_provider ORDER BY sort_order ASC, key ASC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_provider(key: str):
    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM model_provider WHERE key = ?", (key,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_profiles(provider_key: Optional[str] = None):
    """返回模型档案列表；可限定厂商"""
    conn = db.get_conn()
    try:
        if provider_key:
            rows = conn.execute(
                "SELECT * FROM model_profile WHERE provider_key = ? ORDER BY sort_order ASC, id ASC",
                (provider_key,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM model_profile ORDER BY provider_key ASC, sort_order ASC, id ASC"
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["modes"] = json.loads(d.get("modes") or "[]")
            d["effort_mapping"] = json.loads(d.get("effort_mapping") or "{}")
            out.append(d)
        return out
    finally:
        conn.close()


def get_profile(profile_id: int):
    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM model_profile WHERE id = ?", (profile_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["modes"] = json.loads(d.get("modes") or "[]")
        d["effort_mapping"] = json.loads(d.get("effort_mapping") or "{}")
        return d
    finally:
        conn.close()


def _find_mode(profile: dict, mode_key: Optional[str]):
    """在 profile.modes 里找到对应模式；找不到返回第一个"""
    modes = profile.get("modes") or []
    if not modes:
        return {"thinking": False, "effort": "medium"}
    if mode_key:
        for m in modes:
            if m.get("key") == mode_key:
                return m
    return modes[0]


def derive_config(provider_key: str, profile_id: Optional[int], mode: Optional[str],
                  overrides: Optional[dict] = None) -> dict:
    """根据厂商/模型档案/模式，推导出一套完整配置（用于 ai.py 发请求）。

    返回值包含：
      provider_key, model_name, base_url, reasoning_format, thinking_enabled,
      reasoning_effort, temperature, max_tokens, max_tokens_field,
      supports_vision, supports_files, api_key_required, notes
    """
    overrides = overrides or {}
    provider = get_provider(provider_key) if provider_key else None
    profile = get_profile(profile_id) if profile_id else None

    # 自定义 / 无档案：从 overrides 里取所有字段
    if provider_key == "custom" or not profile:
        return {
            "provider_key": provider_key or "custom",
            "model_name": overrides.get("model_name", ""),
            "base_url": overrides.get("base_url", provider.get("base_url", "") if provider else ""),
            "reasoning_format": overrides.get("reasoning_format", "thinking_block"),
            "thinking_enabled": int(bool(overrides.get("thinking_enabled", 1))),
            "reasoning_effort": overrides.get("reasoning_effort", "medium"),
            "temperature": float(overrides.get("temperature", 0.7) or 0.7),
            "temperature_locked": 0,
            "max_tokens": int(overrides.get("max_tokens", 2048) or 2048),
            "max_tokens_field": overrides.get("max_tokens_field", "max_tokens"),
            "supports_vision": int(bool(overrides.get("supports_vision", 0))),
            "supports_files": int(bool(overrides.get("supports_files", 0))),
            "api_key_required": int(provider.get("api_key_required", 1) if provider else 1),
            "notes": overrides.get("notes", ""),
            "mode": mode or overrides.get("mode", "fast"),
        }

    # 内置模型：以模板为基准，但思考开关/强度允许用户在「模型配置」页显式覆盖
    mode_cfg = _find_mode(profile, mode)
    eff_map = profile.get("effort_mapping") or {}
    effort = overrides.get("reasoning_effort") or mode_cfg.get("effort") or "medium"
    mapped_effort = eff_map.get(effort, effort)

    # thinking_enabled：若调用方显式传入（含 0/False），优先用；否则跟随模式模板推导
    if overrides.get("thinking_enabled") is not None:
        thinking = int(bool(overrides.get("thinking_enabled")))
    else:
        thinking = int(bool(mode_cfg.get("thinking", False)))
    temp_locked = int(profile.get("temperature_locked", 0) or 0)
    temperature = float(profile.get("temperature", 1.0) or 1.0)
    if not temp_locked and not thinking:
        # 温度可编辑且非思考模式：允许用 overrides.temperature
        temperature = float(overrides.get("temperature", temperature) or temperature)

    return {
        "provider_key": provider_key,
        "model_name": profile.get("model_name", ""),
        "base_url": overrides.get("base_url", provider.get("base_url", "") if provider else ""),
        "reasoning_format": profile.get("reasoning_format", "thinking_block"),
        "thinking_enabled": thinking,
        "reasoning_effort": effort,
        "mapped_reasoning_effort": mapped_effort,
        "temperature": temperature,
        "temperature_locked": temp_locked,
        "max_tokens": int(overrides.get("max_tokens", profile.get("max_tokens", 2048)) or 2048),
        "max_tokens_field": profile.get("max_tokens_field", "max_tokens"),
        "supports_vision": int(profile.get("supports_vision", 0) or 0),
        "supports_files": int(profile.get("supports_files", 0) or 0),
        "api_key_required": int(provider.get("api_key_required", 1) if provider else 1),
        "notes": profile.get("notes", ""),
        "mode": mode_cfg.get("key", profile.get("default_mode", "fast")),
        "mode_name": mode_cfg.get("name", ""),
    }


def build_payload(model_row: dict, messages: list, options: Optional[dict] = None) -> dict:
    """根据 model_config 行（或其推导结果）构造 OpenAI 兼容请求 payload。

    options 可覆盖：thinking(bool), reasoning_effort(str), temperature(float), max_tokens(int)
    """
    options = options or {}

    # 优先用已经推导好的字段；否则从 model_row 旧字段兼容读取
    provider_key = model_row.get("provider_key") or model_row.get("provider") or "custom"
    profile_id = model_row.get("model_profile_id")
    mode = model_row.get("mode")

    # 如果 model_row 已经有完整推导字段（如 derive_config 返回值），直接用
    if "mapped_reasoning_effort" in model_row:
        derived = model_row
    else:
        derived = derive_config(provider_key, profile_id, mode, overrides=model_row)

    thinking = options.get("thinking")
    if thinking is None:
        thinking = bool(derived.get("thinking_enabled", 1))
    thinking = bool(thinking)

    effort = options.get("reasoning_effort") or derived.get("reasoning_effort") or "medium"
    mapped_effort = derived.get("mapped_reasoning_effort") or effort
    temperature = options.get("temperature") if "temperature" in options else derived.get("temperature")
    max_tokens = options.get("max_tokens") if "max_tokens" in options else derived.get("max_tokens", 2048)

    model_name = derived.get("model_name") or model_row.get("model_name", "")
    max_tokens_field = derived.get("max_tokens_field", "max_tokens")

    payload = {
        "model": model_name,
        "messages": messages,
        max_tokens_field: int(max_tokens or 2048),
    }

    if thinking:
        fmt = derived.get("reasoning_format", "thinking_block")
        if fmt == "top_level_effort":
            payload["reasoning_effort"] = mapped_effort
        elif fmt == "enable_thinking":
            # 通义千问/CodeQwen（百炼）：顶层布尔开关，控制思考开/关，无需 reasoning_effort
            payload["enable_thinking"] = True
        else:
            payload["thinking"] = {"type": "enabled"}
            payload["reasoning_effort"] = mapped_effort
    else:
        # 非思考模式：只有温度未锁定时才发 temperature
        if not derived.get("temperature_locked"):
            if temperature is not None:
                payload["temperature"] = float(temperature)
        # enable_thinking 关闭模式需显式发 false（顶层布尔），避免沿用厂商默认开思考
        if derived.get("reasoning_format") == "enable_thinking":
            payload["enable_thinking"] = False

    return payload
