"""common/ai_advisor.py —— 通用 AI 顾问（多轮对话）

供 08~12 等功能的「AI 顾问」Tab 调用。逻辑：
  读该功能的 generation 指令 → 清掉所有 {占位符} → 当系统提示 →
  注入项目上下文 JSON → 拼 messages（system + history + user）→ 调模型。

07-去重 有自己内联的 ai_chat（能用不碰），08~12 统一走本 helper，避免 5 份 90 行重复。
"""
import json
import re
import urllib.request
import urllib.error
from common import db, ai as ai_util

_PH_RE = re.compile(r"\{[^}]+\}")


def _read_cfg_content(function_id, cfg_type):
    """读 novel_prompt_config 里 (function_id, type) 那行的 content；无则空串。"""
    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT content FROM novel_prompt_config WHERE function_id=? AND type=?",
            (function_id, cfg_type),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return ""
    c = row["content"]
    # 兼容：content 可能是 JSON 串（旧式块结构），取 content 字段
    if isinstance(c, str) and c.strip().startswith("{"):
        try:
            obj = json.loads(c)
            if isinstance(obj, dict) and "content" in obj:
                return obj["content"] or ""
        except Exception:
            pass
    return c or ""


def chat(function_id, context, history, user_message,
         model_config_id=None, thinking_enabled=None):
    """通用 AI 顾问对话。返回 {"reply": str}；失败抛 RuntimeError。"""
    # 系统提示：优先 generation（讲清角色），清理所有 {占位符}（聊天用不到）
    system_prompt = _read_cfg_content(function_id, "generation") \
        or _read_cfg_content(function_id, "ai_content") \
        or "你是该流程的 AI 助手。"
    if not isinstance(system_prompt, str):
        system_prompt = str(system_prompt)
    system_prompt = _PH_RE.sub("", system_prompt)

    # 注入上下文（前端已带「## 当前上下文」结构化数据）
    ctx_json = json.dumps(context, ensure_ascii=False, indent=2)
    system_prompt += "\n\n## 当前项目上下文\n" + ctx_json

    # 拼 messages：system + history + 当前提问
    messages = [{"role": "system", "content": system_prompt}]
    for h in (history or []):
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": user_message})

    if model_config_id:
        conn = db.get_conn()
        try:
            cfg_row = conn.execute(
                "SELECT * FROM model_config WHERE id=?", (model_config_id,)
            ).fetchone()
        finally:
            conn.close()
        if not cfg_row:
            raise RuntimeError(f"模型配置 ID={model_config_id} 不存在")
        thinking = bool(thinking_enabled) if thinking_enabled is not None \
            else bool(int(cfg_row["thinking_enabled"] or 0))
        return {"reply": _direct_chat(dict(cfg_row), messages, thinking)}
    else:
        reply = ai_util.chat(
            prompt=user_message,
            system_prompt=system_prompt,
            temperature=0.3,
            func_key=function_id,
            cfg_type="ai_content",
            thinking=bool(thinking_enabled) if thinking_enabled is not None else None,
        )
        return {"reply": reply}


def _direct_chat(cfg, messages, thinking, temperature=0.3):
    """直接按模型配置调 API（不经过 ai.chat 的层级查找）。"""
    payload = {
        "model": cfg["model_name"],
        "messages": messages,
        "max_tokens": int(cfg.get("max_tokens", 2048) or 2048),
    }
    if thinking:
        payload["thinking"] = {"type": "enabled"}
        payload["reasoning_effort"] = cfg.get("reasoning_effort", "high")
    else:
        payload["temperature"] = temperature

    url = cfg["base_url"].rstrip("/") + "/chat/completions"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if cfg.get("api_key"):
        req.add_header("Authorization", f"Bearer {cfg['api_key']}")

    try:
        with urllib.request.urlopen(req, timeout=cfg.get("timeout_sec", 300)) as resp:
            obj = json.loads(resp.read().decode("utf-8"))
        msg = obj["choices"][0]["message"]
        return msg.get("content") or msg.get("reasoning_content") or ""
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        raise RuntimeError(f"模型接口错误 {e.code}: {body[:300]}")
    except Exception as e:
        raise RuntimeError(f"调用模型失败：{e}")
