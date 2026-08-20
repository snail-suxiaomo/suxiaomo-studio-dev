"""common/ai.py —— 调大模型的公共小工具（不是引擎）

职责：给一段提示词 → 按 model_config 表里的「启用中」配置
→ 调 OpenAI 兼容接口 → 返回文本。
各功能(去重/精要/...)都复用它；它不含任何 if function_id 分支。
"""
import base64
import json
import re
import threading
import time
import urllib.request
import urllib.error

from common import db
from model_config import providers

# 429 限流重试：部分模型服务的组织并发上限为 1，瞬时并发会返回
# "max organization concurrency: 1, please try again after 1 seconds"。
# 这里在连接阶段自动退避重试，让单点「生成/审核」在并发窗口过去后自愈。
AI_MAX_429_RETRIES = 4  # 在首次请求之外，最多再重试 4 次（共 5 次尝试）


def _retry_after_sec(body):
    """从 429 响应体里解析服务端建议的等待秒数（如 'after 1 seconds'）。"""
    if not body:
        return None
    try:
        m = re.search(r"after\s+([\d.]+)\s*second", body, re.IGNORECASE)
        if m:
            return float(m.group(1))
    except Exception:
        pass
    return None


def _backoff_wait(attempt, body):
    """第 attempt 次重试（从 1 开始）的等待秒数：取『服务端建议』与『指数退避』的较大值，上限 10s。"""
    server = _retry_after_sec(body) or 0
    exp = 1.0 * (2 ** (attempt - 1))  # 1s, 2s, 4s, 8s ...
    return min(max(server, exp), 10.0)


# 全局串行锁：部分模型组织的并发上限为 1（HTTP 429 明确报
# "max organization concurrency: 1"）。若我们的多次调用并发打过去必然会 429。
# 这里用一把全局锁，保证任意时刻只有 1 个模型请求（含其流式响应）在飞，
# 从根上满足「并发=1」的硬性约束；429 重试作为叠加的韧性层。
_ai_gate = threading.Lock()


def _block_cfg(func_key, cfg_type):
    """读 novel_prompt_config 里 (function_id, type) 那行的块级配置
    （model_config_id / thinking_enabled / reasoning_effort）；行不存在或列为 NULL 都返回 None。"""
    if not func_key or not cfg_type:
        return None
    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT model_config_id, thinking_enabled, reasoning_effort FROM novel_prompt_config "
            "WHERE function_id = ? AND type = ?",
            (func_key, cfg_type),
        ).fetchone()
        if not row:
            return None
        return {
            "model_config_id": row["model_config_id"],
            "thinking_enabled": row["thinking_enabled"],
            "reasoning_effort": row["reasoning_effort"],
        }
    finally:
        conn.close()


# ── ai_rules 分支（小说改写等新功能走这里，不影响老的 novel_prompt_config）──

def _airule_cfg(menu, func, role):
    """读 ai_rules 表 (menu, function_key, role) 那行的 model_config_id/thinking/strength。
    用于让新功能（如小说改写）从「AI 调用规则」取指令配置，而不依赖 novel_prompt_config。"""
    if not menu or not func or not role:
        return None
    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT model_config_id, thinking, strength FROM ai_rules "
            "WHERE menu=? AND function_key=? AND role=? AND enabled=1",
            (menu, func, role),
        ).fetchone()
        if not row:
            return None
        return {
            "model_config_id": row["model_config_id"],
            "thinking": row["thinking"],
            "strength": row["strength"],
        }
    finally:
        conn.close()


def _first_chat_config():
    """返回一个适合文本对话的 model_config 行：优先取 is_active=1 且 capability='chat' 的配置；
    没有则取 capability='chat'（或自定义无档案）的第一条。避免把图片/视频模型当作文本模型调用。"""
    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT mc.* FROM model_config mc "
            "LEFT JOIN model_profile mp ON mc.model_profile_id = mp.id "
            "WHERE mc.is_active = 1 AND (mp.capability = 'chat' OR mp.capability IS NULL)"
        ).fetchone()
        if row:
            return row
        row = conn.execute(
            "SELECT mc.* FROM model_config mc "
            "LEFT JOIN model_profile mp ON mc.model_profile_id = mp.id "
            "WHERE mp.capability = 'chat' OR mp.capability IS NULL "
            "ORDER BY mc.sort_order ASC, mc.id ASC LIMIT 1"
        ).fetchone()
        return row
    finally:
        conn.close()


def _airule_model(menu, func, role):
    """从 ai_rules 解析模型配置（优先级：规则自带 model_config_id → 对话能力默认配置）。"""
    ac = _airule_cfg(menu, func, role)
    mc_id = ac.get("model_config_id") if ac else None
    if mc_id:
        conn = db.get_conn()
        try:
            cfg = conn.execute("SELECT * FROM model_config WHERE id=?", (mc_id,)).fetchone()
        finally:
            conn.close()
        if cfg:
            return cfg
    return _first_chat_config()


def _airule_thinking(menu, func, role):
    """思考开关：expert→True, fast→False, follow→None(跟随模型配置)。"""
    ac = _airule_cfg(menu, func, role)
    if not ac:
        return None
    t = (ac.get("thinking") or "follow")
    if t == "expert":
        return True
    if t == "fast":
        return False
    return None


def _airule_strength(menu, func, role):
    """思考强度：follow→None(跟随模型配置)，否则 low/medium/high。"""
    ac = _airule_cfg(menu, func, role)
    if not ac:
        return None
    s = ac.get("strength")
    if not s or s == "follow":
        return None
    return s


def get_active_config(func_key=None, cfg_type=None):
    """读模型配置，解析优先级：
      1) 块级（novel_prompt_config 里 function_id+cfg_type 行的 model_config_id，非 NULL 即用）
      2) 功能级（novel_function.model_config_id，非 NULL 即用）
      3) 全局（is_active=1 的那条）
    实现「按功能分别选模型」+「三块分别选模型」。
    """
    conn = db.get_conn()
    try:
        # 1) 块级
        if func_key and cfg_type:
            bc = _block_cfg(func_key, cfg_type)
            if bc and bc["model_config_id"]:
                cfg = conn.execute(
                    "SELECT * FROM model_config WHERE id = ?",
                    (bc["model_config_id"],),
                ).fetchone()
                if cfg:
                    return cfg
        # 2) 功能级
        if func_key:
            fr = conn.execute(
                "SELECT model_config_id FROM novel_function WHERE function_id = ?",
                (func_key,),
            ).fetchone()
            if fr and fr["model_config_id"]:
                cfg = conn.execute(
                    "SELECT * FROM model_config WHERE id = ?",
                    (fr["model_config_id"],),
                ).fetchone()
                if cfg:
                    return cfg
        # 3) 全局：优先 is_active=1 的 chat 能力配置，避免把图片/视频模型当作文本模型
        row = conn.execute(
            "SELECT mc.* FROM model_config mc "
            "LEFT JOIN model_profile mp ON mc.model_profile_id = mp.id "
            "WHERE mc.is_active = 1 AND (mp.capability = 'chat' OR mp.capability IS NULL)"
        ).fetchone()
        if row:
            return row
        return _first_chat_config()
    finally:
        conn.close()


def get_func_thinking(func_key=None, cfg_type=None):
    """读思考开关，解析优先级：
      1) 块级（novel_prompt_config 行 thinking_enabled，非 NULL 即用）
      2) 功能级（novel_function.thinking_enabled）
      3) 全局（model_config.thinking_enabled）
    返回 1/0。
    """
    # 1) 块级
    if func_key and cfg_type:
        bc = _block_cfg(func_key, cfg_type)
        if bc and bc["thinking_enabled"] is not None:
            return int(bc["thinking_enabled"] or 0)
    # 2) 功能级
    if func_key:
        conn = db.get_conn()
        try:
            row = conn.execute(
                "SELECT thinking_enabled FROM novel_function WHERE function_id = ?",
                (func_key,),
            ).fetchone()
        finally:
            conn.close()
        if row:
            return int(row["thinking_enabled"] or 0)
    # 3) 全局
    conn = db.get_conn()
    try:
        cfg = conn.execute(
            "SELECT thinking_enabled FROM model_config WHERE is_active = 1"
        ).fetchone()
    finally:
        conn.close()
    return int((cfg["thinking_enabled"] if cfg else 1) or 0)


def get_func_effort(func_key=None, cfg_type=None):
    """读推理强度，解析优先级（与 get_func_thinking 对称）：
      1) 块级（novel_prompt_config 行 reasoning_effort，非 NULL 即用）
      2) 功能级（novel_function.reasoning_effort，非 NULL/空 即用）
      3) 全局（model_config.reasoning_effort）
    返回 'low' / 'medium' / 'high' 之一。仅思考开启时该值才被 build_payload 使用。
    """
    # 1) 块级
    if func_key and cfg_type:
        bc = _block_cfg(func_key, cfg_type)
        if bc and bc.get("reasoning_effort"):
            return bc["reasoning_effort"]
    # 2) 功能级
    if func_key:
        conn = db.get_conn()
        try:
            row = conn.execute(
                "SELECT reasoning_effort FROM novel_function WHERE function_id = ?",
                (func_key,),
            ).fetchone()
        finally:
            conn.close()
        if row and row["reasoning_effort"]:
            return row["reasoning_effort"]
    # 3) 全局
    conn = db.get_conn()
    try:
        cfg = conn.execute(
            "SELECT reasoning_effort FROM model_config WHERE is_active = 1"
        ).fetchone()
    finally:
        conn.close()
    return cfg["reasoning_effort"] if (cfg and cfg["reasoning_effort"]) else "medium"


def _resolve_cfg(model_config_id=None, func_key=None, cfg_type=None, airule=None):
    """根据优先级拿到 model_config 行，并把它转成带推导字段的 dict。
    airule=(menu, func, role)：若传了则优先从 ai_rules 取模型配置（小说改写等新功能用）。"""
    if model_config_id:
        conn = db.get_conn()
        try:
            cfg = conn.execute(
                "SELECT * FROM model_config WHERE id = ?", (model_config_id,)
            ).fetchone()
        finally:
            conn.close()
        if not cfg:
            raise RuntimeError(f"指定的模型配置（id={model_config_id}）不存在，请检查「模型配置」")
    elif airule:
        cfg = _airule_model(*airule)
    else:
        cfg = get_active_config(func_key, cfg_type)
    if not cfg:
        raise RuntimeError("没有默认模型配置，请先到「AI模型配置」设为默认一条")
    cfg = dict(cfg)

    # 如果有厂商/档案信息，做能力推导
    provider_key = cfg.get("provider_key") or cfg.get("provider")
    profile_id = cfg.get("model_profile_id")
    mode = cfg.get("mode")
    if provider_key and profile_id:
        derived = providers.derive_config(provider_key, profile_id, mode, overrides=cfg)
        cfg.update(derived)
    else:
        # 旧数据兼容：按旧字段保留行为
        cfg["provider_key"] = provider_key or "custom"
        cfg["temperature_locked"] = 0
        cfg["max_tokens_field"] = cfg.get("max_tokens_field", "max_tokens")
        cfg["supports_files"] = int(cfg.get("supports_files") or 0)
    return cfg


def _build_messages(prompt, system_prompt=None, images=None, texts=None):
    """构造 messages 数组，支持纯文本 / 多模态内容数组。"""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    if images or texts:
        content = []
        text_parts = [prompt] if prompt else []
        for f in texts or []:
            try:
                raw = f.file.read()
                text_parts.append(f"\n\n--- {f.filename} ---\n{raw.decode('utf-8', errors='ignore')}")
            finally:
                f.file.close()
        content.append({"type": "text", "text": "\n\n".join(text_parts)})
        for f in images or []:
            try:
                raw = f.file.read()
                mime = f.content_type or "image/png"
                b64 = base64.b64encode(raw).decode("ascii")
                content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
            finally:
                f.file.close()
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": prompt})
    return messages


def chat(prompt, system_prompt=None, temperature=None, thinking=None, func_key=None, cfg_type=None, with_reasoning=False, images=None, texts=None, model_config_id=None, reasoning_effort=None, history=None, airule=None):
    """最简单的对话：给提示词，返回模型文本。失败抛异常，调用方自己处理。

    prompt        : 用户/功能给的提示词
    system_prompt : 可选系统设定（如“你是一个严谨的编辑”）
    temperature   : 可选，覆盖配置里的温度（思考模式下该参数被模型忽略）
    thinking      : 可选，显式开/关思考（True/False）。优先级最高
    func_key      : 可选，功能编号（如 "09-剧本"）。
    cfg_type      : 可选，指令块类型（generation / py_format / ai_content）。
                    与 func_key 一起决定「该功能+该块」绑定的模型与思考开关，
                    实现「三块分别选模型 + 分别开关思考」。
    with_reasoning : 可选，True 时返回 dict {content, reasoning}（同时带回思考过程），
                    默认 False 返回纯字符串（向后兼容所有旧调用方）。
    images        : 可选，UploadFile 列表，作为 image_url 传入多模态模型。
    texts         : 可选，UploadFile 列表，内容会追加到 prompt 中一起发送。

    思考模式解析优先级：
      1) thinking(bool) 显式传 → 直接用
      2) cfg_type + func_key 传了 → 读该块级 thinking_enabled
      3) func_key 传了 → 读该功能的 thinking_enabled（功能级）
      4) 都没传 → 用 model_config 全局 thinking_enabled
    """
    cfg = _resolve_cfg(model_config_id, func_key, cfg_type, airule=airule)

    # 图片能力校验
    if images and not int(cfg.get("supports_vision", 0) or 0):
        raise RuntimeError(
            f"当前模型「{cfg.get('name') or cfg.get('model_name')}」未开启「支持图片/视觉」能力，"
            "请到「模型配置」中勾选该选项，或切换到支持图片的模型。"
        )

    current_turn = _build_messages(prompt, system_prompt, images, texts)
    if history:
        # history：历史消息列表（[{role, content}]），拼到当前轮之前，让重开会话可续聊
        msgs = []
        if current_turn and current_turn[0].get("role") == "system":
            msgs.append(current_turn[0])
            msgs.extend(history)
            msgs.extend(current_turn[1:])
        else:
            msgs = list(history) + current_turn
    else:
        msgs = current_turn

    # 思考模式解析（优先级：显式 > 块级 > 功能级 > 全局配置）
    if thinking is None:
        if airule:
            ath = _airule_thinking(*airule)
            thinking = ath if ath is not None else int(cfg.get("thinking_enabled", 1) or 0)
        elif func_key:
            ft = get_func_thinking(func_key, cfg_type)
            thinking = ft if ft is not None else int(cfg.get("thinking_enabled", 1) or 0)
        else:
            thinking = int(cfg.get("thinking_enabled", 1) or 0)
    thinking = bool(thinking)

    # 模型强度解析（优先级：显式 > 块级 > 功能级 > 全局配置）
    if not reasoning_effort:
        if airule:
            ars = _airule_strength(*airule)
            reasoning_effort = ars if ars else cfg.get("reasoning_effort") or "medium"
        elif func_key:
            reasoning_effort = get_func_effort(func_key, cfg_type)
        if not reasoning_effort:
            reasoning_effort = cfg.get("reasoning_effort") or "medium"

    options = {
        "thinking": thinking,
        "reasoning_effort": reasoning_effort,
    }
    if temperature is not None:
        options["temperature"] = temperature

    payload = providers.build_payload(cfg, msgs, options)
    url = cfg["base_url"].rstrip("/") + "/chat/completions"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if cfg.get("api_key"):
        req.add_header("Authorization", f"Bearer {cfg['api_key']}")

    attempt = 0
    with _ai_gate:
        while True:
            try:
                with urllib.request.urlopen(req, timeout=cfg.get("timeout_sec", 300)) as resp:
                    obj = json.loads(resp.read().decode("utf-8"))
                msg = obj["choices"][0]["message"]
                content = msg.get("content") or ""
                reasoning = msg.get("reasoning_content") or ""
                if with_reasoning:
                    return {"content": content, "reasoning": reasoning}
                return content or reasoning or ""
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < AI_MAX_429_RETRIES:
                    attempt += 1
                    body = e.read().decode("utf-8", "ignore")
                    time.sleep(_backoff_wait(attempt, body))
                    continue
                body = e.read().decode("utf-8", "ignore")
                raise RuntimeError(f"模型接口错误 {e.code}: {body[:300]}")
            except Exception as e:
                raise RuntimeError(f"调用模型失败：{e}")


def chat_stream(prompt, system_prompt=None, temperature=None, thinking=None, func_key=None, cfg_type=None, model_config_id=None, reasoning_effort=None, airule=None):
    """流式版 chat：逐块 yield {'type':'reasoning'|'content','delta':str}。

    - 若模型接口返回 SSE（data: ... 流），逐 delta 实时吐出；
    - 若接口不认 stream（仅回单条 JSON），读完整体解析后一次性 yield 一条 content；
    - 失败时抛 RuntimeError（由调用方捕获后转成 SSE error 事件）。
    """
    cfg = _resolve_cfg(model_config_id, func_key, cfg_type, airule=airule)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    if thinking is None:
        if airule:
            ath = _airule_thinking(*airule)
            thinking = ath if ath is not None else int(cfg.get("thinking_enabled", 1) or 0)
        elif func_key:
            ft = get_func_thinking(func_key, cfg_type)
            thinking = ft if ft is not None else int(cfg.get("thinking_enabled", 1) or 0)
        else:
            thinking = int(cfg.get("thinking_enabled", 1) or 0)
    thinking = bool(thinking)

    # 模型强度解析（优先级：显式 > 块级 > 功能级 > 全局配置）
    if not reasoning_effort:
        if airule:
            ars = _airule_strength(*airule)
            reasoning_effort = ars if ars else cfg.get("reasoning_effort") or "medium"
        elif func_key:
            reasoning_effort = get_func_effort(func_key, cfg_type)
        if not reasoning_effort:
            reasoning_effort = cfg.get("reasoning_effort") or "medium"

    options = {
        "thinking": thinking,
        "reasoning_effort": reasoning_effort,
    }
    if temperature is not None:
        options["temperature"] = temperature

    payload = providers.build_payload(cfg, messages, options)
    payload["stream"] = True
    url = cfg["base_url"].rstrip("/") + "/chat/completions"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if cfg.get("api_key"):
        req.add_header("Authorization", f"Bearer {cfg['api_key']}")

    # 连接阶段先重试（429 限流发生在建连时），连上后再流式消费
    with _ai_gate:
        attempt = 0
        resp = None
        while attempt < AI_MAX_429_RETRIES + 1:
            try:
                resp = urllib.request.urlopen(req, timeout=cfg.get("timeout_sec", 300))
                break
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < AI_MAX_429_RETRIES:
                    attempt += 1
                    body = e.read().decode("utf-8", "ignore")
                    time.sleep(_backoff_wait(attempt, body))
                    continue
                body = e.read().decode("utf-8", "ignore")
                raise RuntimeError(f"模型接口错误 {e.code}: {body[:300]}")
            except Exception as e:
                raise RuntimeError(f"调用模型失败：{e}")

        if resp is None:
            raise RuntimeError("模型接口连接失败（重试耗尽）")

        try:
            with resp:
                chunk = resp.read(4096)
                if not chunk:
                    return
                is_sse = b"data:" in chunk[:512]
                if is_sse:
                    buf = chunk
                    while True:
                        while b"\n\n" in buf:
                            block, buf = buf.split(b"\n\n", 1)
                            for line in block.split(b"\n"):
                                line = line.strip()
                                if line.startswith(b"data:"):
                                    txt = line[5:].strip()
                                    if txt == b"[DONE]":
                                        return
                                    try:
                                        obj = json.loads(txt)
                                    except Exception:
                                        continue
                                    delta = obj.get("choices", [{}])[0].get("delta", {})
                                    rc = delta.get("reasoning_content") or ""
                                    ct = delta.get("content") or ""
                                    if rc:
                                        yield {"type": "reasoning", "delta": rc}
                                    if ct:
                                        yield {"type": "content", "delta": ct}
                        chunk = resp.read(4096)
                        if not chunk:
                            break
                        buf += chunk
                    return
                # 单条 JSON：读完整体解析后一次性吐出
                full = chunk + resp.read()
                try:
                    obj = json.loads(full.decode("utf-8"))
                except Exception:
                    return
                msg = obj["choices"][0]["message"]
                ct = msg.get("content") or ""
                rc = msg.get("reasoning_content") or ""
                if rc:
                    yield {"type": "reasoning", "delta": rc}
                if ct:
                    yield {"type": "content", "delta": ct}
        except Exception as e:
            raise RuntimeError(f"调用模型失败：{e}")
