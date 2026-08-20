"""filespace/router.py —— 文件空间 REST 接口

路由前缀 /filespace：
- GET  /roots        列书签
- POST /roots        加书签 {name, path, note?}
- DELETE /roots/{id} 删书签
- GET  /list?path=   列目录一层
- GET  /text?path=   读文本预览
- GET  /image?path=  读图片 base64 预览
- GET  /stream?path= 流式返回（视频/大文件，支持 range）
- GET  /open?path=   调本机默认程序打开
- POST /cover        上传封面图片 {root_id} （multipart/form-data）
- DELETE /cover/{id} 清除封面，恢复默认色块
- GET  /cover/{id}   读取封面 base64
"""

import mimetypes
import os
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from filespace import service
from common import db


# Windows 下标准 open() / FileResponse 打开文件时不带 FILE_SHARE_DELETE，
# 会导致视频缩略图在浏览器请求 /stream 期间无法被重命名。
# 这里用 CreateFileW 显式带上 FILE_SHARE_DELETE，让重命名/删除可以并发进行。
if sys.platform == 'win32':
    import msvcrt
    import ctypes
    from ctypes import wintypes

    _GENERIC_READ = 0x80000000
    _FILE_SHARE_READ = 0x00000001
    _FILE_SHARE_WRITE = 0x00000002
    _FILE_SHARE_DELETE = 0x00000004
    _OPEN_EXISTING = 3

    def _open_file_shared_delete(path: Path):
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateFileW(
            ctypes.c_wchar_p(str(path)),
            _GENERIC_READ,
            _FILE_SHARE_READ | _FILE_SHARE_WRITE | _FILE_SHARE_DELETE,
            None,
            _OPEN_EXISTING,
            0,
            None,
        )
        if handle == -1:
            err = ctypes.get_last_error()
            raise OSError(err, f'无法打开文件：{path}')
        return handle


# 记录当前进程还在打开中的文件流句柄，供重命名前主动释放用。
# key: 规范化绝对路径；value: 该路径当前活跃的 file 对象集合。
_active_streams: dict[str, set] = {}


def _register_stream(path: str, f):
    """登记一个尚未关闭的文件流句柄。"""
    key = str(Path(path).resolve())
    _active_streams.setdefault(key, set()).add(f)


def _unregister_stream(path: str, f):
    """注销一个已关闭的文件流句柄。"""
    key = str(Path(path).resolve())
    s = _active_streams.get(key)
    if s:
        s.discard(f)
        if not s:
            _active_streams.pop(key, None)


def close_streams_for(path: str):
    """强制关闭当前进程内指定路径的所有活跃流句柄（供重命名/删除前调用）。"""
    key = str(Path(path).resolve())
    s = _active_streams.pop(key, set())
    for f in list(s):
        try:
            f.close()
        except Exception:
            pass


def _file_chunks(path: str, f, chunk_size=256 * 1024, total: int | None = None):
    _register_stream(path, f)
    remaining = total
    try:
        while True:
            read_size = chunk_size if remaining is None else min(chunk_size, remaining)
            if read_size <= 0:
                break
            chunk = f.read(read_size)
            if not chunk:
                break
            yield chunk
            if remaining is not None:
                remaining -= len(chunk)
    finally:
        try:
            f.close()
        except Exception:
            pass
        _unregister_stream(path, f)


def _parse_range(range_header: str, size: int):
    """解析 HTTP Range 头，返回 (start, end, length) 或 None。"""
    if not range_header or not range_header.startswith('bytes='):
        return None
    try:
        unit, ranges = range_header.split('=', 1)
        if unit != 'bytes' or ',' in ranges:
            return None
        start_str, end_str = ranges.split('-', 1)
        if start_str == '':
            # suffix range: bytes=-500
            length = int(end_str) if end_str else size
            start = max(0, size - length)
            end = size - 1
        else:
            start = int(start_str)
            if end_str == '':
                end = size - 1
            else:
                end = int(end_str)
        if start < 0 or start >= size or end < start:
            return None
        end = min(end, size - 1)
        return start, end, end - start + 1
    except Exception:
        return None


def stream_response_shared(path: str, range_header: str | None = None):
    """流式返回文件；Windows 下使用 FILE_SHARE_DELETE 打开，避免自身占锁导致重命名失败。

    支持 Range 请求：浏览器 <video preload="metadata"> 通常只请求前 1-2MB，
    支持 Range 后可大幅减少文件持锁时间和数据读取量。
    """
    rp = Path(path)
    if not rp.is_file():
        raise ValueError('不是文件')
    size = rp.stat().st_size
    media_type = mimetypes.guess_type(str(rp))[0] or 'application/octet-stream'
    rng = _parse_range(range_header, size)

    if sys.platform == 'win32':
        handle = _open_file_shared_delete(rp)
        fd = msvcrt.open_osfhandle(handle, os.O_RDONLY)
        f = os.fdopen(fd, 'rb')
    else:
        f = open(rp, 'rb')

    if rng is None:
        return StreamingResponse(
            _file_chunks(str(rp), f),
            media_type=media_type,
            headers={'Content-Length': str(size), 'Accept-Ranges': 'bytes'},
        )

    start, end, length = rng
    f.seek(start)
    headers = {
        'Content-Type': media_type,
        'Content-Length': str(length),
        'Content-Range': f'bytes {start}-{end}/{size}',
        'Accept-Ranges': 'bytes',
    }
    return StreamingResponse(
        _file_chunks(str(rp), f, chunk_size=64 * 1024, total=length),
        status_code=206,
        media_type=media_type,
        headers=headers,
    )

router = APIRouter(prefix='/api/filespace', tags=['filespace'])


class RootIn(BaseModel):
    name: str
    path: str
    note: str | None = None
    category: str = '未分类'


class RootUpdateIn(BaseModel):
    name: str | None = None
    category: str | None = None
    note: str | None = None
    path: str | None = None


class OrderIn(BaseModel):
    ids: list[int]


class TextSaveIn(BaseModel):
    path: str
    content: str


class RenameIn(BaseModel):
    old_path: str
    new_name: str


@router.get('/roots')
def get_roots():
    return service.list_roots()


@router.post('/roots')
def post_root(req: RootIn):
    try:
        return service.add_root(req.name, req.path, req.note, req.category)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete('/roots/{root_id}')
def del_root(root_id: int):
    service.delete_root(root_id)
    return {'ok': True}


@router.put('/roots/{root_id}')
def put_root(root_id: int, req: RootUpdateIn):
    try:
        return service.update_root(root_id, req.name, req.category, req.note, req.path)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post('/roots/reorder')
def reorder_roots(req: OrderIn):
    try:
        service.update_order(req.ids)
        return {'ok': True}
    except ValueError as e:
        raise HTTPException(400, str(e))


class TagsIn(BaseModel):
    tags: dict = {}


class GenTagsIn(BaseModel):
    folder_path: str


@router.post('/roots/{root_id}/generate-tags')
def gen_root_tags(root_id: int, req: GenTagsIn):
    """为某个文件夹生成/覆盖快捷入口：扫描 folder_path 的直接子文件夹。任意层级均可（folder_path 须在书签根目录内）。"""
    try:
        return service.generate_tags(root_id, req.folder_path)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.put('/roots/{root_id}/tags')
def put_root_tags(root_id: int, req: TagsIn):
    """整体覆盖快捷入口 map（{路径: [子文件夹名]}），供单个入口/分支移除、清空后回写。"""
    try:
        return service.set_tags(root_id, req.tags)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get('/list')
def get_list(path: str = Query(...)):
    try:
        return service.list_dir(path)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get('/text')
def get_text(path: str = Query(...)):
    try:
        t = service.read_text(path)
        return {'text': t}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post('/save_text')
def post_save_text(req: TextSaveIn):
    try:
        service.save_text(req.path, req.content)
        return {'ok': True}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get('/image')
def get_image(path: str = Query(...)):
    try:
        b64 = service.read_image_b64(path)
        if b64 is None:
            raise HTTPException(413, '文件过大，请用系统程序打开')
        return {'data': b64}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get('/stream')
def stream_file(path: str = Query(...), request: 'Request' = None):
    try:
        rp = service.resolve(path)
        range_header = request.headers.get('range') if request else None
        return stream_response_shared(str(rp), range_header=range_header)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post('/rename')
def post_rename(req: RenameIn):
    try:
        return service.rename(req.old_path, req.new_name)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get('/open')
def open_file(path: str = Query(...)):
    try:
        service.open_path(path)
        return {'ok': True}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get('/open_parent')
def open_parent(path: str = Query(...)):
    """打开文件所在文件夹并选中该文件。"""
    try:
        service.open_parent(path)
        return {'ok': True}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete('/delete')
def delete_path(path: str = Query(...)):
    """删除指定文件或目录（前端必须二次确认）。"""
    try:
        service.delete_path(path)
        return {'ok': True}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get('/search')
def search_files(path: str = Query(...), q: str = Query(...), recursive: int = Query(1)):
    """业务分类标签搜索：在当前目录及直接子目录（深度由 recursive 决定）按关键词搜索。"""
    try:
        return service.search_dir(path, q, max_depth=recursive if recursive else 1)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ============ 封面 ============
# 上传的封面图片存到统一数据根下的 data/covers/ 下，DB 只存路径，跟随自定义位置
COVERS_DIR = db.DATA_DIR / 'covers'
ALLOWED_COVER_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}


@router.post('/cover')
async def upload_cover(root_id: int = Form(...), file: UploadFile = File(...)):
    """上传封面图片：保存到 data/covers/{root_id}_{原名}，写库 cover_path。"""
    ext = Path(file.filename or '').suffix.lower()
    if ext not in ALLOWED_COVER_EXT:
        raise HTTPException(400, f'不支持的图片格式：{ext}，仅支持 {sorted(ALLOWED_COVER_EXT)}')
    try:
        COVERS_DIR.mkdir(parents=True, exist_ok=True)
        # 用 root_id 前缀避免重名覆盖；保留原扩展名
        save_name = f"{root_id}_{file.filename}"
        save_path = COVERS_DIR / save_name
        content = await file.read()
        save_path.write_bytes(content)
        return service.set_cover(root_id, str(save_path))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f'封面上传失败：{e}')


@router.delete('/cover/{root_id}')
def clear_cover(root_id: int):
    """清除封面，恢复默认色块。"""
    try:
        return service.set_cover(root_id, None)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get('/cover/{root_id}')
def get_cover(root_id: int):
    """读取封面 base64。无封面返回 {data: null}，前端用默认色块。"""
    try:
        b64 = service.read_cover_b64(root_id)
        return {'data': b64}
    except ValueError as e:
        raise HTTPException(400, str(e))
