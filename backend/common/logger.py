"""common/logger.py —— 极简错误日志落盘（只记报错，不记普通信息）

设计（按需求只记录报错）：
- 两个 RollingFileHandler：{项目根}/logs/backend-error.log、{项目根}/logs/frontend-error.log
- ERROR 级别以上才落盘；每条带 ISO 时间戳 + level
- 保留最近 5 份滚动备份（每份 1MB）
- 不记录请求体 / 文件内容（按需求仅记录报错摘要）
- 日志目录 = 项目根目录/logs（backend 上两级目录，dev 为 <项目根>/logs），不放在 data/ 或前后端内部，
  避免打包时随 extraResources 一起打进 exe（别人不需要、且避免泄露项目信息）
- 打包态（SUXIAOMO_PACKAGED=1，由 desktop/main.js 注入）不落盘，仅返回空 logger
"""

import logging
import os
import pathlib
from logging.handlers import RotatingFileHandler

# 打包态不写本地日志：别人不需要该功能，且避免泄露项目信息。
# SUXIAOMO_PACKAGED 由 desktop/main.js 在打包态 spawn 后端时注入环境变量。
_PACKAGED = os.environ.get('SUXIAOMO_PACKAGED', '') == '1'

# 日志目录 = 项目根目录/logs（backend 上两级目录；dev 为 <PROJECT_ROOT>/logs）
LOGS_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / 'logs'


def _make_logger(name, filename):
    lg = logging.getLogger(name)
    lg.setLevel(logging.ERROR)
    lg.propagate = False  # 不污染 root / 第三方 logger
    if _PACKAGED:
        # 打包态：不落盘（无 handler），调用方无感知，只是不写文件
        return lg
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    if not lg.handlers:
        fh = RotatingFileHandler(
            LOGS_DIR / filename,
            maxBytes=1 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8',
        )
        fh.setLevel(logging.ERROR)
        fh.setFormatter(
            logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        )
        lg.addHandler(fh)
    return lg


_backend_lg = _make_logger('wb_backend_error', 'backend-error.log')
_frontend_lg = _make_logger('wb_frontend_error', 'frontend-error.log')


def log_backend_error(message, exc=None):
    """后端业务/接口报错落盘（不含请求体）。exc 为可选异常对象。"""
    if exc is not None:
        message = f'{message}\n{exc}' if message else repr(exc)
    # 截断单条，避免一条异常把日志撑爆
    _backend_lg.error(str(message)[:8000])


def log_frontend_error(message, context=None):
    """前端通过 /api/log 上报的报错落盘。context 为可选字典（已在前端脱敏）。"""
    if context:
        extra = ' | '.join(f'{k}={v}' for k, v in context.items() if v)
        if extra:
            message = f'{message} [{extra}]'
    _frontend_lg.error(str(message)[:8000])
