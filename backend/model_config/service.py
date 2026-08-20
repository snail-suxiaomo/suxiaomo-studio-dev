"""model_config/service.py —— 模型配置表的读写（py 直接写 SQL，不依赖引擎）"""
import json
import time
import urllib.request
import urllib.error

from common import db
from . import providers


def _enrich(row: dict) -> dict:
    """把 model_config 行与厂商/档案信息合并，方便前端直接展示。"""
    d = dict(row)
    d["provider"] = providers.get_provider(d.get("provider_key") or d.get("provider") or "custom")
    profile = providers.get_profile(d["model_profile_id"]) if d.get("model_profile_id") else None
    d["profile"] = profile
    # 能力（视觉/文件）以模型档案为准：内置模型的真实能力由模板定义，
    # 覆盖旧配置行可能残留的错误开关值（如早期把 DeepSeek/Kimi 误标成不支持文件）。
    if profile:
        d["supports_vision"] = int(profile.get("supports_vision", 0) or 0)
        d["supports_files"] = int(profile.get("supports_files", 0) or 0)
    return d


def list_configs():
    conn = db.get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM model_config ORDER BY sort_order DESC, id ASC"
        ).fetchall()
        return [_enrich(r) for r in rows]
    finally:
        conn.close()


def get_config(cid):
    conn = db.get_conn()
    try:
        row = conn.execute("SELECT * FROM model_config WHERE id = ?", (cid,)).fetchone()
        return _enrich(row) if row else None
    finally:
        conn.close()


def _guess_profile(row: dict):
    """旧数据迁移：根据 base_url / model_name 猜测 provider_key 与 model_profile_id。"""
    base_url = (row.get("base_url") or "").lower()
    model_name = (row.get("model_name") or "").lower()

    # 先按 base_url 猜厂商
    provider_key = "custom"
    if "deepseek" in base_url:
        provider_key = "deepseek"
    elif "moonshot" in base_url or "kimi" in base_url:
        provider_key = "kimi"
    elif "bigmodel" in base_url or "zhipu" in base_url:
        provider_key = "zhipu"
    elif "tencentmaas" in base_url or "tokenhub" in base_url:
        provider_key = "hy3"
    elif "minimax" in base_url:
        provider_key = "minimax"
    elif "11434" in base_url or "ollama" in base_url:
        provider_key = "ollama"

    # 再按 model_name 在档案里找最匹配的一行
    profiles = providers.list_profiles(provider_key)
    profile_id = None
    for p in profiles:
        if p.get("model_name", "").lower() == model_name:
            profile_id = p["id"]
            break
        if p.get("model_key", "").lower() in model_name:
            profile_id = p["id"]
            break
    if profile_id is None and profiles:
        # 兜底：取该厂商第一个档案
        profile_id = profiles[0]["id"]

    return provider_key, profile_id


def migrate_old_rows():
    """把没有 provider_key 的旧配置自动认领厂商和档案（幂等）。"""
    conn = db.get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM model_config WHERE provider_key IS NULL OR provider_key = ''"
        ).fetchall()
        for r in rows:
            provider_key, profile_id = _guess_profile(dict(r))
            mode = "expert" if r["thinking_enabled"] else "fast"
            conn.execute(
                "UPDATE model_config SET provider_key = ?, model_profile_id = ?, mode = ? WHERE id = ?",
                (provider_key, profile_id, mode, r["id"]),
            )
        conn.commit()
    finally:
        conn.close()
    # 顺带把缺失/无效的 reasoning_effort 补上默认值
    ensure_reasoning_effort_defaults()
    # 顺带保证默认模型唯一（is_active=1 只保留 id 最小一条）
    ensure_single_default()


def ensure_single_default():
    """默认模型唯一性自检（幂等）：
    1. 建部分唯一索引（已有库补建，防止后续写入多条默认）；
    2. 若现存多条 is_active=1，只保留 id 最小一条，其余清 0。
    """
    conn = db.get_conn()
    try:
        # 先清理历史多条默认（否则带数据建唯一索引会失败）
        defaults = conn.execute(
            "SELECT id FROM model_config WHERE is_active = 1 ORDER BY id"
        ).fetchall()
        if len(defaults) > 1:
            keep_id = defaults[0]["id"]
            conn.execute("UPDATE model_config SET is_active=0 WHERE is_active=1 AND id<>?", (keep_id,))
            conn.commit()
            print(f"[model_config] 默认模型多条，已只保留 id={keep_id}")
        # 再建部分唯一索引（已有库补建，防止后续写入多条默认）
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_model_config_single_default "
            "ON model_config (is_active) WHERE is_active = 1"
        )
        conn.commit()
    finally:
        conn.close()


def ensure_reasoning_effort_defaults():
    """给已有 model_config 行补合理的默认 reasoning_effort（幂等、只填缺失或无效值）。"""
    conn = db.get_conn()
    try:
        rows = conn.execute(
            "SELECT id, provider_key, model_profile_id, mode, thinking_enabled, reasoning_effort FROM model_config"
        ).fetchall()
        updated = 0
        for r in rows:
            provider_key = r["provider_key"] or "custom"
            profile = providers.get_profile(r["model_profile_id"]) if r["model_profile_id"] else None
            eff_map = profile.get("effort_mapping") or {} if profile else {}
            stored = r["reasoning_effort"]

            if provider_key == "custom" or not profile:
                # 自定义模型：按 UI 约定只接受 low/medium/high，缺省给 medium
                target = "medium"
                valid_keys = {"low", "medium", "high"}
            else:
                mode_cfg = providers._find_mode(profile, r["mode"])
                target = mode_cfg.get("effort") or (list(eff_map.keys())[0] if eff_map else "medium")
                valid_keys = set(eff_map.keys()) if eff_map else set()

            if not stored or (valid_keys and stored not in valid_keys):
                conn.execute(
                    "UPDATE model_config SET reasoning_effort = ? WHERE id = ?",
                    (target, r["id"]),
                )
                updated += 1
        conn.commit()
        if updated:
            print(f"[model_config] 已为 {updated} 条配置补全默认 reasoning_effort")
    finally:
        conn.close()


def create_config(d: dict):
    conn = db.get_conn()
    try:
        max_order = conn.execute(
            "SELECT MAX(sort_order) AS m FROM model_config").fetchone()["m"] or 0
        sort_order = int(d.get("sort_order", max_order + 10))
        provider_key = d.get("provider_key") or d.get("provider") or "custom"
        profile_id = d.get("model_profile_id")
        mode = d.get("mode")

        key_vault_id = d.get("key_vault_id")

        # 新建即为默认（is_active=1）时，先取消其他条目的默认标记（保证全局唯一默认）
        if int(bool(d.get("is_active", 0))):
            conn.execute("UPDATE model_config SET is_active=0")

        # 内置模型：用模板推导实际字段
        derived = providers.derive_config(provider_key, profile_id, mode, overrides=d)
        cur = conn.execute(
            """INSERT INTO model_config
               (name, provider, base_url, api_key, secret_key, model_name, temperature, timeout_sec,
                is_active, thinking_enabled, reasoning_effort, max_tokens, supports_vision,
                supports_files, sort_order, reasoning_format, provider_key, model_profile_id, mode,
                key_vault_id)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (d["name"], provider_key, d.get("base_url") or derived["base_url"],
             d.get("api_key", ""), d.get("secret_key", ""),
             derived["model_name"],
             float(derived["temperature"]), int(d.get("timeout_sec", 300)),
             int(bool(d.get("is_active", 0))),
             int(derived["thinking_enabled"]),
             derived["reasoning_effort"],
             int(derived["max_tokens"]),
             int(derived["supports_vision"]),
             int(derived["supports_files"]),
             sort_order,
             derived["reasoning_format"],
             provider_key, profile_id, derived["mode"],
             key_vault_id),
        )
        conn.commit()
        return get_config(cur.lastrowid)
    finally:
        conn.close()


def update_config(cid, d: dict):
    conn = db.get_conn()
    try:
        old = conn.execute(
            "SELECT api_key, secret_key, key_vault_id FROM model_config WHERE id=?", (cid,)).fetchone()
        new_key = d.get("api_key")
        if new_key is None:
            api_key = old["api_key"] if old else ""
        else:
            api_key = new_key
        new_secret = d.get("secret_key")
        if new_secret is None:
            secret_key = old["secret_key"] if old else ""
        else:
            secret_key = new_secret

        provider_key = d.get("provider_key") or d.get("provider") or "custom"
        profile_id = d.get("model_profile_id")
        mode = d.get("mode")
        key_vault_id = d.get("key_vault_id")
        if key_vault_id is None and old:
            key_vault_id = old["key_vault_id"]

        derived = providers.derive_config(provider_key, profile_id, mode, overrides=d)
        base_url = d.get("base_url") or derived["base_url"]

        # 设为本条为默认（is_active=1）时，自动取消其他条目的默认标记（保证全局唯一默认）
        if int(bool(d.get("is_active", 0))):
            conn.execute("UPDATE model_config SET is_active=0 WHERE id<>?", (cid,))

        conn.execute(
            """UPDATE model_config SET
                 name=?, provider=?, base_url=?, api_key=?, secret_key=?, model_name=?,
                 temperature=?, timeout_sec=?, is_active=?,
                 thinking_enabled=?, reasoning_effort=?, max_tokens=?,
                 supports_vision=?, supports_files=?, reasoning_format=?, updated_at=datetime('now'),
                 provider_key=?, model_profile_id=?, mode=?, key_vault_id=?
               WHERE id=?""",
            (d["name"], provider_key, base_url,
             api_key, secret_key, derived["model_name"],
             float(derived["temperature"]), int(d.get("timeout_sec", 300)),
             int(bool(d.get("is_active", 0))),
             int(derived["thinking_enabled"]),
             derived["reasoning_effort"],
             int(derived["max_tokens"]),
             int(derived["supports_vision"]),
             int(derived["supports_files"]),
             derived["reasoning_format"],
             provider_key, profile_id, derived["mode"], key_vault_id, cid),
        )
        conn.commit()
        return get_config(cid)
    finally:
        conn.close()


def refresh_from_key_vault(cid):
    """重新从该配置关联的 AI 密钥库条目拉取 base_url / api_key / secret_key 并更新。
    返回更新后的配置；若未关联密钥库或密钥库条目不存在，则返回 None。
    """
    conn = db.get_conn()
    try:
        cfg = conn.execute(
            "SELECT key_vault_id FROM model_config WHERE id=?", (cid,)
        ).fetchone()
        if not cfg or not cfg["key_vault_id"]:
            return None
        vrow = conn.execute(
            "SELECT base_url, api_key, secret_key FROM key_vault WHERE id=?",
            (cfg["key_vault_id"],)
        ).fetchone()
        if not vrow:
            return None
        conn.execute(
            """UPDATE model_config SET
                 base_url=?, api_key=?, secret_key=?, updated_at=datetime('now')
               WHERE id=?""",
            (vrow["base_url"] or "", vrow["api_key"] or "", vrow["secret_key"] or "", cid),
        )
        conn.commit()
        return get_config(cid)
    finally:
        conn.close()


def reorder(ids: list):
    """按传入 id 顺序重写 sort_order（越靠前权重越大，避免拖拽后整表重排）"""
    conn = db.get_conn()
    try:
        for idx, cid in enumerate(ids):
            conn.execute(
                "UPDATE model_config SET sort_order = ?, updated_at = datetime('now') WHERE id = ?",
                ((len(ids) - idx) * 10, cid),
            )
        conn.commit()
    finally:
        conn.close()


def delete_config(cid):
    conn = db.get_conn()
    try:
        conn.execute("DELETE FROM model_config WHERE id=?", (cid,))
        conn.commit()
    finally:
        conn.close()


def set_active(cid):
    """把某条设为启用，其余全部禁用"""
    conn = db.get_conn()
    try:
        conn.execute("UPDATE model_config SET is_active=0")
        conn.execute("UPDATE model_config SET is_active=1 WHERE id=?", (cid,))
        conn.commit()
    finally:
        conn.close()


def probe(cfg: dict):
    """对一个配置做联通测试：发一个最小 chat 请求，返回 {ok, latency_ms, message}

    cfg 字段：base_url / api_key / model_name / temperature / timeout_sec
                 + thinking_enabled / reasoning_effort / max_tokens
    连接/鉴权/超时等都作为「测试结果」返回，不抛异常（失败也是有效结论）。
    测试会如实带上「思考模式」与「max_tokens」，以便反映真实调用能否通过。
    """
    base_url = (cfg.get("base_url") or "").strip().rstrip("/")
    model_name = (cfg.get("model_name") or "").strip()
    api_key = cfg.get("api_key")
    provider_key = (cfg.get("provider_key") or cfg.get("provider") or "custom").strip().lower()
    profile_id = cfg.get("model_profile_id")
    mode = cfg.get("mode")
    timeout = int(cfg.get("timeout_sec", 300) or 300)

    if not base_url or not model_name:
        return {"ok": False, "latency_ms": 0,
                "message": "接口地址和模型名不能为空"}

    provider = providers.get_provider(provider_key)
    api_key_required = int(provider.get("api_key_required", 1) if provider else 1)
    if api_key_required and not (api_key and str(api_key).strip()):
        return {"ok": False, "latency_ms": 0,
                "message": "该厂商要求 API Key，不能为空"}

    # 推导配置并构造 payload
    derived = providers.derive_config(provider_key, profile_id, mode, overrides=cfg)
    messages = [{"role": "user", "content": "ping"}]
    options = {"thinking": bool(derived.get("thinking_enabled", 1))}
    effort = cfg.get("reasoning_effort")
    if effort:
        options["reasoning_effort"] = effort
    payload = providers.build_payload(derived, messages, options)

    url = base_url + "/chat/completions"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")

    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            obj = json.loads(resp.read().decode("utf-8"))
        msg = obj["choices"][0]["message"]
        text = msg.get("content") or msg.get("reasoning_content") or ""
        latency = int((time.time() - t0) * 1000)
        suffix = "（思考模式）" if options["thinking"] else ""
        msg_keys = sorted(msg.keys()) if isinstance(msg, dict) else []
        has_reasoning = bool(msg.get("reasoning_content"))
        return {
            "ok": True, "latency_ms": latency,
            "message": f"联通成功{suffix}，模型返回：{text[:40]}",
            "sent_payload": payload,
            "response_fields": msg_keys,
            "has_reasoning_content": has_reasoning,
        }
    except urllib.error.HTTPError as e:
        latency = int((time.time() - t0) * 1000)
        body = e.read().decode("utf-8", "ignore")
        return {"ok": False, "latency_ms": latency,
                "message": f"HTTP {e.code}: {body[:200]}",
                "sent_payload": payload}
    except Exception as e:
        latency = int((time.time() - t0) * 1000)
        return {"ok": False, "latency_ms": latency,
                "message": f"连接失败：{e}",
                "sent_payload": payload}


def test_by_id(cid):
    """取某条已存配置做联通测试"""
    row = get_config(cid)
    if not row:
        return {"ok": False, "latency_ms": 0, "message": "配置不存在"}
    cfg = dict(row)
    # 把 profile 字典铺平回 cfg，供 probe 使用
    if cfg.get("profile"):
        cfg.update(cfg["profile"])
    return probe(cfg)
