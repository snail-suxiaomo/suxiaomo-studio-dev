"""filespace/security.py —— 路径规范化与文件分类（非 AI 功能，这里只做安全 helper）

职责：
- resolve_path: 规范化用户输入的路径，处理相对路径/..，返回绝对 Path
  （自由导航模式下允许进入父目录/跨盘，所以我们不限制子树，只做规范化防注入）
- classify: 按扩展名归类文件类型，供前端决定预览方式
- PREVIEW_LIMIT: 文本/图片预览大小上限（字节），超过则提示用系统程序打开
"""

from pathlib import Path

PREVIEW_LIMIT = 50 * 1024 * 1024  # 50MB

_IMAGE = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg'}
_VIDEO = {'mp4', 'webm', 'mov', 'mkv', 'avi'}
_AUDIO = {'mp3', 'wav', 'ogg', 'flac', 'm4a'}
_TEXT = {
    # 文档
    'md', 'txt', 'rtf',
    # 代码/脚本
    'json', 'js', 'ts', 'jsx', 'tsx', 'vue', 'py', 'rb', 'php', 'go', 'java',
    'c', 'cpp', 'h', 'hpp', 'cs', 'swift', 'kt', 'rs', 'sh', 'bash', 'zsh',
    'ps1', 'bat', 'cmd', 'vbs', 'lua', 'perl', 'pl', 'pm',
    # 样式/标记
    'css', 'scss', 'sass', 'less', 'html', 'htm', 'xml', 'xhtml', 'yaml', 'yml',
    'toml', 'ini', 'conf', 'cfg', 'config', 'properties',
    # 数据/日志
    'csv', 'tsv', 'log', 'sql',
}
_PDF = {'pdf'}
_OFFICE = {'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}


def classify(name: str) -> str:
    """按扩展名返回文件类型：dir/image/video/audio/text/pdf/office/other"""
    ext = Path(name).suffix.lower().lstrip('.')
    if ext in _IMAGE:
        return 'image'
    if ext in _VIDEO:
        return 'video'
    if ext in _AUDIO:
        return 'audio'
    if ext in _TEXT:
        return 'text'
    if ext in _PDF:
        return 'pdf'
    if ext in _OFFICE:
        return 'office'
    return 'other'


def resolve_path(raw: str) -> Path:
    """规范化路径；空或非绝对路径抛 ValueError"""
    if not raw:
        raise ValueError('路径为空')
    p = Path(raw)
    if not p.is_absolute():
        raise ValueError('请提供绝对路径（如 F:\\suxiaomo-studio）')
    return p.resolve()
