"""model_config/media_gen.py —— 媒体生成能力层（生图/生视频）

只服务 capability=image/video 的 model_config（目前对接 Flux Art）。
与 chat 路径（providers.derive_config / ai.py）完全解耦：这里不碰 messages、temperature、reasoning。

流程：
  submit    → POST Flux Art 创建异步任务（带 Idempotency-Key）→ 存 gen_task(queued)
  get_task  → 若仍进行中，主动 GET Flux Art /tasks/{id} 轮询 → 成功则下载结果到本地 media 目录
"""
import json
import time
import uuid
import urllib.request
import urllib.error
from pathlib import Path

from common import db
from . import service, providers

# Flux Art 网关（Cloudflare）会拦截 Python-urllib 默认 UA，必须带浏览器 UA 才能抵达其 API
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def _media_dir() -> Path:
    d = db.DATA_DIR / "media"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _http_json(method, url, api_key, idem_key=None, body=None, timeout=60):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("User-Agent", _UA)
    if idem_key:
        req.add_header("Idempotency-Key", idem_key)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _extract_urls(output):
    """从 Flux Art 任务的 output 里尽可能多地提取结果 URL（兼容 images[]/image/video/url/裸字符串）。"""
    urls = []
    if isinstance(output, str):
        if output.startswith("http"):
            urls.append(output)
        return urls
    if isinstance(output, dict):
        for k, v in output.items():
            if k == "url" and isinstance(v, str) and v.startswith("http"):
                urls.append(v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict) and isinstance(item.get("url"), str):
                        urls.append(item["url"])
                    elif isinstance(item, str) and item.startswith("http"):
                        urls.append(item)
            elif isinstance(v, dict):
                urls += _extract_urls(v)
    return urls


def _download(url, media_dir):
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", _UA)
    with urllib.request.urlopen(req, timeout=120) as resp:
        ctype = resp.headers.get("Content-Type", "")
        ext = ".bin"
        if "image/" in ctype:
            ext = "." + ctype.split("/")[-1].split(";")[0]
        elif "video/" in ctype:
            ext = "." + ctype.split("/")[-1].split(";")[0]
        else:
            p = url.split("?")[0]
            tail = p.rsplit("/", 1)[-1]
            if "." in tail:
                ext = "." + tail.rsplit(".", 1)[-1][:5]
        fname = f"{uuid.uuid4().hex}{ext}"
        path = media_dir / fname
        with open(path, "wb") as f:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)
        return fname


def submit(config_id, prompt, params=None):
    """提交一次生图/生视频任务。返回本地 gen_task 行（dict）。"""
    params = params or {}
    if not prompt or not prompt.strip():
        raise ValueError("提示词不能为空")
    cfg = service.get_config(config_id)
    if not cfg:
        raise ValueError("配置不存在")
    profile = cfg.get("profile")
    if not profile:
        raise ValueError("该配置未关联模型档案")
    capability = profile.get("capability") or "chat"
    if capability not in ("image", "video"):
        raise ValueError(f"该配置不是生图/生视频类型（capability={capability}）")

    api_key = cfg.get("api_key") or ""
    if not api_key and cfg.get("key_vault_id"):
        conn0 = db.get_conn()
        try:
            v = conn0.execute(
                "SELECT api_key FROM key_vault WHERE id=?", (cfg["key_vault_id"],)
            ).fetchone()
            if v:
                api_key = v["api_key"] or ""
        finally:
            conn0.close()
    if not api_key:
        raise ValueError("该配置缺少 API Key")

    base = (cfg.get("base_url") or "").strip().rstrip("/")
    if not base:
        prov = providers.get_provider(cfg.get("provider_key") or "flux_art")
        base = (prov or {}).get("base_url", "") if prov else ""
    model_name = profile.get("model_name") or cfg.get("model_name") or ""

    if capability == "image":
        endpoint = base + "/openapi/v1/images/generations"
        body = {"model": model_name, "prompt": prompt, "count": 1,
                "mode": params.get("mode") or "generate"}
        for k in ("aspect_ratio", "size", "image_urls"):
            if params.get(k) is not None:
                body[k] = params[k]
    else:
        endpoint = base + "/openapi/v1/videos/generations"
        body = {"model": model_name, "prompt": prompt,
                "video_mode": params.get("video_mode") or "t2v"}
        for k in ("image_urls", "source_video_url", "duration", "resolution", "ratio", "aspect_ratio"):
            if params.get(k) is not None:
                body[k] = params[k]

    idem = ("img-" if capability == "image" else "vid-") + uuid.uuid4().hex
    try:
        status, obj = _http_json("POST", endpoint, api_key, idem_key=idem, body=body, timeout=60)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:300]
        raise ValueError(f"Flux Art 创建任务失败 HTTP {e.code}: {detail}")
    except Exception as e:
        raise ValueError(f"Flux Art 连接失败：{e}")

    data = obj.get("data", {}) if isinstance(obj, dict) else {}
    flux_task_id = data.get("id")
    flux_status = data.get("status", "queued")

    conn = db.get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO gen_task
               (config_id, capability, model_name, prompt, params, flux_task_id, status,
                created_at, updated_at)
               VALUES(?,?,?,?,?,?,?,datetime('now'),datetime('now'))""",
            (config_id, capability, model_name, prompt,
             json.dumps(params, ensure_ascii=False), flux_task_id, flux_status),
        )
        conn.commit()
        tid = cur.lastrowid
    finally:
        conn.close()
    return get_task(tid)


def get_task(task_id):
    """读取本地任务；若仍在进行中，主动轮询 Flux Art 更新状态与结果。"""
    conn = db.get_conn()
    try:
        row = conn.execute("SELECT * FROM gen_task WHERE id=?", (task_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
    finally:
        conn.close()

    if d["status"] in ("queued", "processing") and d.get("flux_task_id"):
        _refresh(d)
        return get_task(d["id"])  # 重新读最新状态
    return d


def _refresh(d):
    """内部：调 Flux Art 查询接口，更新本地任务状态/结果。"""
    cfg = service.get_config(d["config_id"])
    api_key = (cfg or {}).get("api_key") or ""
    base = (cfg or {}).get("base_url") or ""
    if not base:
        prov = providers.get_provider((cfg or {}).get("provider_key") or "flux_art")
        base = (prov or {}).get("base_url", "") if prov else ""
    url = base.rstrip("/") + "/openapi/v1/tasks/" + d["flux_task_id"]
    try:
        status, obj = _http_json("GET", url, api_key, timeout=30)
    except Exception as e:
        conn = db.get_conn()
        try:
            conn.execute(
                "UPDATE gen_task SET error=?, updated_at=datetime('now') WHERE id=?",
                (f"轮询失败：{e}", d["id"]),
            )
            conn.commit()
        finally:
            conn.close()
        return

    task = obj.get("data", obj) if isinstance(obj, dict) else {}
    new_status = task.get("status") or d["status"]
    usage = task.get("usage") or {}
    points = usage.get("points_charged")
    output = task.get("output")
    failure = task.get("failure")
    if isinstance(failure, dict):
        error = failure.get("message") or task.get("error")
    else:
        error = task.get("error")

    local_path = None
    result_url = None
    if new_status == "succeeded" and output:
        urls = _extract_urls(output)
        if urls:
            result_url = urls[0]
            try:
                local_path = _download(urls[0], _media_dir())
            except Exception as e:
                error = f"结果下载失败：{e}"

    conn = db.get_conn()
    try:
        conn.execute(
            """UPDATE gen_task SET status=?, result_url=?, local_path=?, points_charged=?, error=?, updated_at=datetime('now')
               WHERE id=?""",
            (new_status, result_url, local_path, points, error, d["id"]),
        )
        conn.commit()
    finally:
        conn.close()
