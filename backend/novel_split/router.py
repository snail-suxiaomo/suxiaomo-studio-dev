"""novel_split/router.py —— /api/novel_split/* 路由

新增接口：
  POST /import  → 存素材 + 诊断（不切章，返回诊断报告）
  POST /diagnose → 仅诊断已有素材
  GET  /config   → 读拆分参数
  PUT  /config   → 写拆分参数
  原 POST /upload 保留不动（用作诊断确认后真正的拆分）
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from pydantic import BaseModel
import json
import urllib.request
import urllib.error

from common import db, ai as ai_util
from novel_project import service as proj_service
from ai_rule import service as airule_service
from . import service

router = APIRouter(prefix="/api/novel_split", tags=["novel_split"])


def _get_project(project_id: int):
    proj = proj_service.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="项目不存在")
    return proj


# ── 原接口（保留） ──────────────────────────────────────

@router.get("/files")
def list_files(project_id: int):
    proj = _get_project(project_id)
    return service.list_split_files(proj["name"])


@router.post("/upload")
async def upload(project_id: int = Form(...), file: UploadFile = File(...)):
    """上传 → 直接拆分落盘（诊断已确认后使用）"""
    proj = _get_project(project_id)
    try:
        raw = await file.read()
        text = service.splitter.decode_file(raw, file.filename)
        result = service.do_split(proj["id"], proj["name"], text)
        service.write_report(proj["name"], file.filename, result)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


# ── 新增：导入即诊断 ────────────────────────────────────

@router.post("/import")
async def import_diagnose(project_id: int = Form(...), file: UploadFile = File(...)):
    """导入小说文件 → 存 00-拆分/小说原文/ + 执行诊断（不切章）"""
    proj = _get_project(project_id)
    try:
        raw = await file.read()
        diag = service.do_diagnose(proj["id"], proj["name"], raw, file.filename)
        return diag
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── 新增：从素材执行拆分（真正两步分离，无需二次上传） ──

@router.post("/split")
async def split_from_asset(project_id: int = Form(...), source_file: str = Form(...),
                           ai_confirmed: int = Form(0),
                           remaining_hard: str = Form("[]"),
                           remaining_soft: str = Form("[]")):
    """从已导入的 00-拆分/小说原文/ 读取文件执行拆分。

    额外参数（用于报告）：
      ai_confirmed    : 1=用户已 AI 确认，0=未确认
      remaining_hard  : 拆分时仍存在的硬异常 JSON 数组
      remaining_soft  : 拆分时仍存在的软警告 JSON 数组"""
    proj = _get_project(project_id)
    try:
        diag_info = {
            "ai_confirmed": bool(ai_confirmed),
            "remaining_hard": json.loads(remaining_hard),
            "remaining_soft": json.loads(remaining_soft),
        }
        result = service.do_split_from_asset(proj["id"], proj["name"], source_file, diag_info)
        return result
    except (RuntimeError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/config")
def get_config(project_id: int):
    _get_project(project_id)
    return service.get_split_config(project_id)


@router.put("/config")
def update_config(project_id: int, body: dict):
    """保存拆分参数，body: {min_chars, max_chars, noise_max_len (可选)}"""
    _get_project(project_id)
    mc = body.get("min_chars", 300)
    xc = body.get("max_chars", 8000)
    nl = body.get("noise_max_len", 20)  # 保留兼容，前端已不再发此字段
    return service.save_split_config(project_id, mc, xc, nl)


# ── AI 辅助分析 ─────────────────────────────────────────

class AiAnalyzeBody(BaseModel):
    diagnosis: dict
    user_message: str
    model_config_id: int | None = None      # 可选：临时切换模型（不保存到 DB）
    thinking_enabled: int | None = None     # 可选：临时切换思考开关（0/1）


@router.post("/ai_analyze")
def ai_analyze(project_id: int = Query(...), body: AiAnalyzeBody = None):
    """AI 聊天分析：读 00-拆分 ai_content 指令 + diagnosis → 返回 AI 建议

    支持可选 model_config_id / thinking_enabled 临时切换（不保存到 DB）。"""
    _get_project(project_id)

    # 读 AI调用规则/小说改写 的 00-拆分 ai_content（role=review）作为系统提示
    system_prompt = airule_service.resolve_rule_content('小说改写', '00-拆分', 'review') or "你是一个小说拆分诊断助手。"

    # 注入诊断数据到系统提示
    import json
    diag_json = json.dumps(body.diagnosis, ensure_ascii=False, indent=2)
    system_prompt = system_prompt.replace("{diagnosis}", diag_json)

    # 如果传了 model_config_id 则按 ID 查模型配置直接调用，不经过块级查找
    if body.model_config_id:
        conn = db.get_conn()
        try:
            cfg_row = conn.execute(
                "SELECT * FROM model_config WHERE id = ?",
                (body.model_config_id,),
            ).fetchone()
        finally:
            conn.close()
        if not cfg_row:
            raise HTTPException(status_code=400, detail=f"模型配置 ID={body.model_config_id} 不存在")

        # 构造 payload 直接调模型（绕过 ai.chat 的层级查找）
        thinking = body.thinking_enabled if body.thinking_enabled is not None \
            else int(cfg_row["thinking_enabled"] or 0)
        try:
            reply = _direct_chat(
                cfg=dict(cfg_row),
                prompt=body.user_message,
                system_prompt=system_prompt,
                thinking=thinking,
                temperature=0.3,
            )
            return {"reply": reply}
        except RuntimeError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        # 默认：用 00-拆分 ai_content 块级配置
        try:
            reply = ai_util.chat(
                prompt=body.user_message,
                system_prompt=system_prompt,
                temperature=0.3,
                airule=('小说改写', '00-拆分', 'review'),
                thinking=bool(body.thinking_enabled) if body.thinking_enabled is not None else None,
            )
            return {"reply": reply}
        except RuntimeError as e:
            raise HTTPException(status_code=400, detail=str(e))


def _direct_chat(cfg: dict, prompt: str, system_prompt: str | None = None,
                 thinking: bool = True, temperature: float = 0.3) -> str:
    """直接按模型配置调 API（不经过 ai.chat 的层级查找）。"""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

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
