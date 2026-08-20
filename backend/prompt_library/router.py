"""prompt_library/router.py —— 个人指令库 REST 接口

路由前缀 /prompt-library：
- GET    /list          列表（支持 category / output_type / keyword / tag / owner_name 筛选）
- GET    /meta          筛选维度（已有的一级/二级/形态/标签）
- GET    /{pid}         详情
- POST   /             新建 {title, content, category_1, category_2, output_type, note, tags}
- POST   /batch-create  批量新建（导入外部提示词：items:[{title,content,category,output_type,style,tool,tags,note,owner_name}]）
- PUT    /{pid}        更新
- DELETE /{pid}        删除
- POST   /import-text  批量导入 txt（body: {items:[{filename, content}]}）
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import io
from datetime import datetime

from prompt_library import service


router = APIRouter(prefix='/api/prompt-library', tags=['prompt_library'])


class PromptIn(BaseModel):
    title: str
    content: str = ''
    category: str = '其他'
    output_type: str = '文本'
    note: str = ''
    tags: str = ''
    scope: str = 'prompt'
    owner_name: Optional[str] = None


class BatchPromptItem(BaseModel):
    title: str
    content: str = ''
    category: str = '其他'
    output_type: str = '文本'
    style: str = '通用风格'
    tool: str = '通用工具'
    tags: str = ''
    note: str = ''
    owner_name: Optional[str] = None


class BatchCreateIn(BaseModel):
    items: List[BatchPromptItem]


@router.get('/list')
def list_prompts(category: str = '全部', output_type: str = '全部',
                 keyword: str = '', tag: str = '', scope: str = '全部', owner: str = ''):
    return service.list_prompts(category, output_type, keyword or None, tag or None, scope, owner or None)


@router.get('/meta')
def get_meta():
    return service.meta()


@router.get('/{pid}')
def get_prompt(pid: int):
    row = service.get_prompt(pid)
    if not row:
        raise HTTPException(404, '记录不存在')
    return row


@router.post('/')
def create(req: PromptIn):
    try:
        return service.create_prompt(req.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.put('/{pid}')
def update(pid: int, req: PromptIn):
    try:
        return service.update_prompt(pid, req.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post('/batch-create')
def batch_create(req: BatchCreateIn):
    stats = service.batch_create_prompts([it.model_dump() for it in req.items])
    return stats


@router.delete('/{pid}')
def delete(pid: int):
    service.delete_prompt(pid)
    return {'ok': True}


class SetCoverIn(BaseModel):
    image: str


@router.post('/{pid}/set_cover')
def set_cover(pid: int, req: SetCoverIn):
    """把指定图片设为首图（移到 images 数组首位，持久化）。"""
    try:
        return service.set_first_image(pid, req.image)
    except ValueError as e:
        raise HTTPException(400, str(e))


class ReorderIn(BaseModel):
    order: List[int]


@router.post('/reorder')
def reorder(req: ReorderIn):
    service.reorder_prompts(req.order)
    return {'ok': True}


@router.post('/{pid}/images')
async def upload_images(pid: int, files: List[UploadFile] = File(...)):
    """上传生图模版图：保存到 data/prompt_images/，追加到记录的 images 数组。"""
    try:
        data = [{'filename': f.filename or 'image', 'content': await f.read()} for f in files]
        return service.add_images(pid, data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f'上传失败：{e}')


@router.delete('/{pid}/images/{filename}')
def remove_image(pid: int, filename: str):
    """删除单张模版图。"""
    try:
        return service.delete_image(pid, filename)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get('/asset/{rel_path:path}')
def get_asset(rel_path: str):
    """预览模版图：返回图片文件流（限制在 data/prompt_images 内）。"""
    try:
        fp = service.get_image_file(rel_path)
        return FileResponse(str(fp))
    except ValueError as e:
        raise HTTPException(400, str(e))


# ---------- skills 附件（压缩包存库；md/txt/docx 读取填正文） ----------
@router.get('/{pid}/attachments')
def list_attachments(pid: int):
    return service.list_attachments(pid)


@router.post('/{pid}/attachments')
async def upload_attachments(pid: int, files: List[UploadFile] = File(...)):
    """上传附件（仅压缩类扩展名）：保存到 data/prompt_attachments/{pid}/。"""
    try:
        data = [{'filename': f.filename or 'archive', 'content': await f.read()} for f in files]
        return service.add_attachments(pid, data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f'上传失败：{e}')


@router.get('/{pid}/attachments/{aid}/download')
def download_attachment(pid: int, aid: int):
    """下载附件：返回原文件流（限制在 data/prompt_attachments/{pid}/ 内）。"""
    try:
        fp, rec = service.get_attachment_file(pid, aid)
        return FileResponse(str(fp), filename=rec['filename'])
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete('/{pid}/attachments/{aid}')
def remove_attachment(pid: int, aid: int):
    try:
        return service.delete_attachment(pid, aid)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post('/read-docx')
async def read_docx(file: UploadFile = File(...)):
    """docx → 纯文本（python-docx），前端读取后填入提示词正文。"""
    try:
        data = await file.read()
        if not data:
            raise ValueError('空文件')
        text = service.extract_docx_text(data)
        return {'text': text}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(400, f'docx 解析失败：{e}')


@router.post('/skills/upload')
async def upload_skill(
    title: str = Form(...),
    note: str = Form(''),
    file: UploadFile = File(...),
):
    """上传 skill 压缩包（zip/7z/rar/tar 系），固定解压到 data/skills/{名称}_{短码}/，并建一条 skills 分类记录。"""
    try:
        data = await file.read()
        return service.upload_skill(
            title=title, archive_bytes=data,
            filename=file.filename or 'archive', note=note)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f'上传失败：{e}')


class ExportIn(BaseModel):
    ids: Optional[List[int]] = None
    scope: Optional[str] = None


class BatchDeleteIn(BaseModel):
    ids: List[int]


@router.post('/export')
def export_prompts(req: ExportIn):
    """导出选中记录为自包含 ZIP（含全字段 + 图片 + skills 文件夹）。不传 ids 导出全部；传 scope 则只导出该归属。"""
    try:
        data, stats = service.export_records(req.ids, req.scope)
    except Exception as e:
        raise HTTPException(500, f'导出失败：{e}')
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    return StreamingResponse(
        io.BytesIO(data),
        media_type='application/zip',
        headers={'Content-Disposition': f'attachment; filename="prompt_library_{ts}.zip"'},
    )


@router.post('/import')
async def import_prompts(file: UploadFile = File(...)):
    """导入本工具导出的新格式 .zip（每提示词一文件夹）。只新增、不更新、不删除。"""
    try:
        data = await file.read()
        stats = service.import_records(data, file.filename or 'import')
        return stats
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f'导入失败：{e}')


@router.post('/batch-delete')
def batch_delete_prompts(req: BatchDeleteIn):
    """批量删除（同时移除磁盘图片 / skills 文件夹）。"""
    try:
        return service.batch_delete(req.ids)
    except Exception as e:
        raise HTTPException(500, f'删除失败：{e}')


@router.post('/{pid}/open-folder')
def open_folder(pid: int):
    """打开 skill 记录对应的本地文件夹（仅限数据根内）。"""
    try:
        service.open_skill_folder(pid)
        return {'ok': True}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f'打开失败：{e}')


