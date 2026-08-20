/**
 * suxiaomo-studio 桌面启动器（Electron 壳）
 *
 * 设计原则（来自用户约束）：
 * 1. 不改动既有的「浏览器版」前后端代码，只在外面套一层壳。
 * 2. 所有文件在项目目录下，不写 C 盘、不引外部路径。
 * 3. 沿用最初的启动方式：后端=venv 里的 uvicorn(9100)。
 *
 * 两种运行模式：
 * - 开发态 `npm start`：起后端(9100) + 前端 vite dev(5173)，窗口加载 5173（与浏览器版一致）。
 * - 打包态（electron-builder 产物）：起后端(默认 9200，避开开发版 9100) + 本地静态服务(5180) 加载 frontend/dist，
 *   并把 /api 反向代理到 9200，窗口加载 5180（不再依赖 vite dev，更接近成品）。
 *
 * 关键改进：启动即弹加载窗 + 失败弹错误框 + 写 boot.log，避免「双击没反应」。
 */

// 保险：清除可能导致 Electron 以纯 Node 模式运行的环境变量
delete process.env.ELECTRON_RUN_AS_NODE

const { app, BrowserWindow, dialog, Menu, ipcMain, nativeImage, shell, desktopCapturer, screen, protocol } = require('electron')

// 开发版与打包版使用不同的应用名，使单实例锁互不干扰：
// 用户可以同时运行一个开发版和一个打包版，便于对照测试；
// 同一模式（如两个打包版）仍受单实例锁保护，避免同一份数据被双写。
const isPackaged = app.isPackaged
if (!isPackaged) {
  app.name = 'suxiaomo-studio-desktop-dev'
}

const path = require('path')

// 固定浏览器存储根：开发态用 -dev，打包态用默认名。
// 显式 setPath 可避免 relaunch 时因 app.name 设置时机导致 userData 临时漂移，
// 进而导致 localStorage（记住账号/自动登录/主题等）丢失。
const USER_DATA_DIR = isPackaged
  ? path.join(app.getPath('appData'), 'suxiaomo-studio-desktop')
  : path.join(app.getPath('appData'), 'suxiaomo-studio-desktop-dev')
try {
  app.setPath('userData', USER_DATA_DIR)
} catch (e) { /* ignore */ }

const { spawn } = require('child_process')
const http = require('http')
const net = require('net')
const fs = require('fs')

// 精准禁用 GPU 缓存（避开 GPU cache creation failed）而不是整硬件加速
// 整硬件加速在高 DPI 下会让窗口文字严重模糊
try {
  app.commandLine.appendSwitch('disable-gpu-shader-disk-cache')
  app.commandLine.appendSwitch('disable-features', 'CalculateNativeWinOcclusion')
  // 开发态彻底禁用 HTTP 缓存：让每次加载都从 vite 取最新代码，避免「改了 CSS 却一直显示旧样式」
  app.commandLine.appendSwitch('disable-http-cache')
} catch (e) { /* 非 Electron 环境跳过 */ }

const RES = process.resourcesPath

// 开发态根目录 = main.js 所在 desktop/ 目录的上一级（项目根）
// 打包态 ROOT_DEV 不用（走 RES），但保留变量避免 isPackaged 分支报错
const ROOT_DEV = path.resolve(__dirname, '..')
const BACKEND_DIR = isPackaged
  ? path.join(RES, 'backend')
  : path.join(ROOT_DEV, 'backend')

// 后端启动命令：
// - 开发态：用开发 venv 的 python.exe -m uvicorn（不直接用 uvicorn.exe，因为部分 venv 里 pip 生成的启动器会静默失败）
// - 打包态：用首启自动建的 runtime-venv 里的 python.exe -m uvicorn（venv 由 ensureRuntimeVenv 创建）
const PYTHON_BIN = isPackaged
  ? path.join(BACKEND_DIR, 'runtime-venv', 'Scripts', 'python.exe')
  : path.join(BACKEND_DIR, 'venv', 'Scripts', 'python.exe')
const NPM_BIN = 'npm' // dev 态用系统 PATH 里的 npm 即可

const FRONTEND_DIST = isPackaged
  ? path.join(RES, 'frontend-dist')
  : path.join(ROOT_DEV, 'frontend', 'dist')

const APP_TITLE = '苏小沫工作台'
const ICON_PATH = isPackaged
  ? path.join(RES, 'frontend-dist', 'logo.png')
  : path.join(ROOT_DEV, 'frontend', 'public', 'logo.png')

// 首选（默认）端口：保留用户习惯的端口号；若被占用则自动让路到临时空闲端口，绝不强杀占用者。
const PREFERRED_BACKEND_PORT = isPackaged
  ? Number(process.env.SUXIAOMO_BACKEND_PORT || 9200)
  : 9100
const PREFERRED_FRONTEND_PORT = 5173 // vite dev（仅开发版使用）
const PREFERRED_STATIC_PORT = 5180 // 打包态静态服务（仅打包版使用）
// 运行时实际使用的端口（由 pickPort 在启动时计算；被占用时与首选不同）
let actualBackendPort = PREFERRED_BACKEND_PORT
let actualFrontendPort = PREFERRED_FRONTEND_PORT
let actualStaticPort = PREFERRED_STATIC_PORT

// 统一数据根（DATA_ROOT）：开发版 / 浏览器版 / 打包版 三版共用同一个根目录。
// 默认 = 项目根下的 workspace/
// 打包版：优先复用本机已有的开发版 workspace（与开发版共享同一套数据）；
//         若该目录不存在，则落到 exe 同级的 workspace（随 exe 携带，可写）。
// schema 建表 SQL / seed 种子：运行时落在数据根下的 data/{schema,seed}，
// 由后端首启从应用包内复制；这里只负责告诉后端「应用包内的源在哪」。
// 开发态源 = backend/bundled/{schema,seed}；打包态源 = resources/backend/bundled/{schema,seed}。
const exeDir = isPackaged ? path.dirname(app.getPath('exe')) : ''
// 打包态 workspace 默认在 exe 同级；开发态在项目根下
const WORKSPACE_DEFAULT = isPackaged
  ? path.join(exeDir, 'workspace')
  : path.join(ROOT_DEV, 'workspace')
const PKG_SCHEMA_DIR = isPackaged ? path.join(RES, 'backend', 'bundled', 'schema') : ''
const PKG_SEED_DIR = isPackaged ? path.join(RES, 'backend', 'bundled', 'seed') : ''

// 开发版日志目录：项目根目录/logs（不进前后端、不进包，打包态不写日志）。
// 与后端/前端错误日志同目录，便于开发版「日志查看」统一读取。只记录报错（见 errLog）。
const LOG_DIR = isPackaged ? '' : path.join(ROOT_DEV, 'logs')
const LOG_PATH = LOG_DIR ? path.join(LOG_DIR, 'electron-error.log') : null

let backendProc = null
let frontendProc = null
let staticServer = null
let mainWindow = null
let loadingWindow = null
let browserWindows = [] // 爆款收集·方案 C：独立浏览器窗口（可多个），常驻直到用户关闭
let lastBackendErr = ''
let backendReady = false
let currentDataDir = ''   // 当前实际使用的数据目录，供前端显示
let currentProjectsDir = ''

// 配置文件固定放在开发根 / exe 同级，便于用户查找与迁移
const SETTINGS_FILE = isPackaged
  ? path.join(exeDir, 'settings.json')
  : path.join(ROOT_DEV, 'settings.json')

// 读取用户设置（主题与数据路径）
function loadSettings() {
  try {
    if (fs.existsSync(SETTINGS_FILE)) {
      return JSON.parse(fs.readFileSync(SETTINGS_FILE, 'utf-8'))
    }
  } catch (e) {
    errLog('读取 settings.json 失败:', e.message)
  }
  return {}
}

// 保存用户设置
function saveSettings(settings) {
  try {
    fs.writeFileSync(SETTINGS_FILE, JSON.stringify(settings, null, 2), 'utf-8')
  } catch (e) {
    errLog('保存 settings.json 失败:', e.message)
  }
}

function log(...args) {
  // 普通启动信息：只写到 stdout（不落盘），避免噪声混进错误日志
  const line = `[${new Date().toISOString()}] ${args.map(String).join(' ')}\n`
  process.stdout.write(line)
}

// 仅用于报错：追加到 electron-error.log（与后端/前端错误日志同目录），同时打到 stderr 便于控制台可见。
// 打包态 LOG_PATH 为 null，不落盘（别人不需要此功能），仅打 stderr。
function errLog(...args) {
  const line = `[${new Date().toISOString()}] ERROR ${args.map(String).join(' ')}\n`
  if (LOG_PATH) {
    try {
      fs.appendFileSync(LOG_PATH, line)
    } catch (e) {
      /* 日志写不了就忽略 */
    }
  }
  process.stderr.write(line)
}

function showError(title, detail) {
  errLog('ERROR:', title, detail)
  try {
    const extra = LOG_PATH ? `\n\n日志文件: ${LOG_PATH}` : ''
    dialog.showErrorBox(title, detail + extra)
  } catch (e) {
    /* ignore */
  }
}

// 清理占用端口的残留进程（复用 start_backend.bat 的逻辑）
function killPort(port) {
  try {
    const out = require('child_process')
      .execSync(
        `netstat -aon 2>nul | findstr /i ":${port}" | findstr /i "LISTENING"`,
        { windowsHide: true }
      )
      .toString()
    const pids = [
      ...new Set(
        out
          .split('\n')
          .map((l) => l.trim().split(/\s+/).pop())
          .filter(Boolean)
      ),
    ]
    for (const pid of pids) {
      try {
        require('child_process').execSync(`taskkill /F /PID ${pid}`, {
          windowsHide: true,
        })
        log('killed stale pid', pid, 'on port', port)
      } catch (e) {
        /* 忽略已退出 */
      }
    }
  } catch (e) {
    /* 端口空闲时 netstat 无输出，正常 */
  }
}

// 选一个空闲端口：优先用 preferred；若被占用（通常是别的程序在监听），
// 则交给操作系统分配一个保证空闲的临时端口。原则：自己让路，绝不强杀占用者。
function pickPort(preferred) {
  return new Promise((resolve) => {
    const tryListen = (p, cb) => {
      const srv = net.createServer()
      srv.once('error', () => {
        const fallback = net.createServer()
        fallback.listen(0, '127.0.0.1', () => {
          const port = fallback.address().port
          fallback.close(() => cb(port))
        })
      })
      srv.listen(p, '127.0.0.1', () => {
        const port = srv.address().port
        srv.close(() => cb(port))
      })
    }
    tryListen(preferred, (port) => {
      if (port !== preferred) {
        log('[port] 首选端口', preferred, '被占用，已让路到临时端口', port)
      }
      resolve(port)
    })
  })
}

function waitForPort(port, timeoutMs = 40000) {
  return new Promise((resolve, reject) => {
    const start = Date.now()
    const tryOnce = () => {
      const sock = require('net').connect(port, '127.0.0.1')
      sock.once('connect', () => {
        sock.destroy()
        resolve()
      })
      sock.once('error', () => {
        sock.destroy()
        if (Date.now() - start > timeoutMs) {
          reject(new Error(`等待端口 ${port} 超时（${timeoutMs / 1000}s）`))
        } else {
          setTimeout(tryOnce, 500)
        }
      })
    }
    tryOnce()
  })
}

// 打包态：首次启动时用包内自带的 _python 创建干净的运行时 venv（runtime-venv），
// 并从本地 wheels 离线安装所有依赖。之后每次启动检测到 .installed 标记文件存在则跳过。
// 用 .installed 而非 pyvenv.cfg 作为"已就绪"标志——pyvenv.cfg 只表示 venv 创建了，不代表 pip install 成功过。
// 彻底消除开发机路径残留，不再需要 patchVenvForPortable 补丁。
// 关键：完全异步（用 spawn 不用 spawnSync），否则 50+ 秒会卡死主线程让 UI 显示"未响应"
function ensureRuntimeVenv() {
  return new Promise((resolve) => {
    if (!isPackaged) return resolve()

    const pyDir = path.join(BACKEND_DIR, '_python')
    const pyExe = path.join(pyDir, 'python.exe')
    const runtimeVenv = path.join(BACKEND_DIR, 'runtime-venv')
    const venvMarker = path.join(runtimeVenv, 'pyvenv.cfg')
    const installedMarker = path.join(runtimeVenv, '.installed')

    // venv 已创建 + 依赖已装完 → 直接用
    if (fs.existsSync(installedMarker)) {
      log('[portable] 运行环境已就绪（.installed 标记），跳过')
      return resolve()
    }

    // 检查 _python 是否就位
    if (!fs.existsSync(pyExe)) {
      errLog('[portable] 未找到包内 Python:', pyExe, '→ 后端可能无法启动')
      return resolve()
    }

    // venv 不存在 → 需要创建
    if (!fs.existsSync(venvMarker)) {
      log('[portable] 首次启动：正在创建运行环境…')
      const sp = require('child_process').spawn
      const createVenv = sp(pyExe, ['-m', 'venv', runtimeVenv], {
        cwd: BACKEND_DIR,
        windowsHide: true,
      })
      let createOut = ''
      createVenv.stdout.on('data', (d) => { createOut += d.toString() })
      createVenv.stderr.on('data', (d) => { createOut += d.toString() })
      createVenv.on('error', (e) => {
        errLog('[portable] 创建 venv 异常:', e.message)
        resolve()
      })
      createVenv.on('exit', (code) => {
        if (code !== 0) {
          errLog('[portable] 创建 venv 失败（退出码', code, '）：', createOut.trim().slice(-1500))
          return resolve()
        }
        log('[portable] venv 已创建:', runtimeVenv)
        installDeps(resolve)
      })
    } else {
      // venv 已存在但未标记 .installed（说明之前创建后装包失败/中断）
      log('[portable] 检测到 venv 已存在但未标记完成，继续尝试装依赖…')
      installDeps(resolve)
    }

    function installDeps(done) {
      const pipExe = path.join(runtimeVenv, 'Scripts', 'pip.exe')
      const wheelsDir = path.join(BACKEND_DIR, 'wheels')
      const reqFile = path.join(BACKEND_DIR, 'requirements.txt')

      if (!fs.existsSync(pipExe)) {
        errLog('[portable] venv 中未找到 pip.exe，无法安装依赖')
        return done()
      }

      // 尝试 A：本地 wheels 离线安装
      if (fs.existsSync(wheelsDir) && fs.existsSync(reqFile)) {
        log('[portable] 正在从本地 wheels 安装依赖…')
        const sp = require('child_process').spawn
        const pip = sp(pipExe, ['install', '--no-index', '--find-links', wheelsDir, '-r', reqFile], {
          cwd: BACKEND_DIR,
          windowsHide: true,
        })
        let pipOut = ''
        pip.stdout.on('data', (d) => {
          const s = d.toString()
          pipOut += s
          process.stdout.write('[pip] ' + s)
        })
        pip.stderr.on('data', (d) => {
          const s = d.toString()
          pipOut += s
          process.stderr.write('[pip] ' + s)
        })
        pip.on('error', (e) => {
          errLog('[portable] 离线安装异常:', e.message)
          done()
        })
        pip.on('exit', (code) => {
          if (code === 0) {
            log('[portable] ✅ 依赖安装完成（离线）')
            try { fs.writeFileSync(installedMarker, new Date().toISOString()) } catch (_) {}
            return done()
          }
          errLog('[portable] 离线安装失败（退出码', code, '），尝试联网安装…')
          // 尝试 B：联网
          if (!fs.existsSync(reqFile)) return done()
          log('[portable] 正在从 PyPI 联网安装依赖…（需网络）')
          const pipOnline = sp(pipExe, ['install', '-r', reqFile], {
            cwd: BACKEND_DIR,
            windowsHide: true,
          })
          pipOnline.stdout.on('data', (d) => process.stdout.write('[pip] ' + d.toString()))
          pipOnline.stderr.on('data', (d) => process.stderr.write('[pip] ' + d.toString()))
          pipOnline.on('error', (e) => {
            errLog('[portable] 联网安装异常:', e.message)
            done()
          })
          pipOnline.on('exit', (code2) => {
            if (code2 === 0) {
              log('[portable] ✅ 依赖安装完成（联网）')
              try { fs.writeFileSync(installedMarker, new Date().toISOString()) } catch (_) {}
            } else {
              errLog('[portable] ⚠️ 依赖安装未完成，后端启动可能报错')
            }
            done()
          })
        })
      } else if (fs.existsSync(reqFile)) {
        log('[portable] wheels 缺失，直接联网安装…')
        const sp = require('child_process').spawn
        const pipOnline = sp(pipExe, ['install', '-r', reqFile], {
          cwd: BACKEND_DIR,
          windowsHide: true,
        })
        pipOnline.stdout.on('data', (d) => process.stdout.write('[pip] ' + d.toString()))
        pipOnline.stderr.on('data', (d) => process.stderr.write('[pip] ' + d.toString()))
        pipOnline.on('error', (e) => { errLog('[portable] 联网异常:', e.message); done() })
        pipOnline.on('exit', () => {
          try { fs.writeFileSync(installedMarker, new Date().toISOString()) } catch (_) {}
          done()
        })
      } else {
        log('[portable] 跳过依赖安装（无 requirements.txt）')
        try { fs.writeFileSync(installedMarker, new Date().toISOString()) } catch (_) {}
        done()
      }
    }
  })
}

// 计算本次启动使用的「统一数据根」：
// - 自定义路径：用户指定的目录即数据根（内含 app.db / data\ / projects\）
// - 打包版：优先复用本机已存在的 workspace（与开发版共享数据），
//          否则落到 exe 同级的 workspace（随 exe 携带、可写）
// - 开发版：项目根下的 workspace\
function resolveDataRoot(settings) {
  if (settings.pathMode === 'custom' && settings.customPath) {
    return path.resolve(settings.customPath)
  }
  if (isPackaged) {
    return fs.existsSync(WORKSPACE_DEFAULT) ? WORKSPACE_DEFAULT : path.join(exeDir, 'workspace')
  }
  return path.join(ROOT_DEV, 'workspace')
}

// 判断目录是否「看起来是苏小沫的数据根」：含 app.db 或 data\ 或 projects\ 任一即视为有效
function isDataRootValid(dir) {
  if (!dir || !fs.existsSync(dir)) return false
  return (
    fs.existsSync(path.join(dir, 'app.db')) ||
    fs.existsSync(path.join(dir, 'data')) ||
    fs.existsSync(path.join(dir, 'projects'))
  )
}

// 数据根引导：分两种场景
// 场景 A：target 目录有效（含旧数据）→ 升级/复用，弹窗让用户选「继续用 / 备份后重来 / 退出」
// 场景 B：target 目录不存在 → 全新安装，直接在 target 新建空 workspace（不弹窗）
// 场景 C：target 目录存在但是空的/无效 → 真正"数据丢失"，弹窗让用户选「选别的 / 新建空 / 退出」
// 返回最终使用的数据根目录；返回 null 表示用户选择退出。
function guideDataRoot(settings) {
  const target = resolveDataRoot(settings)

  // 场景 A：升级/复用（target 是有效的旧数据根）
  if (isDataRootValid(target)) {
    log('[guide] 检测到已有数据根:', target)
    const { response } = dialog.showMessageBoxSync({
      type: 'question',
      title: '检测到已有数据',
      message: `当前文件夹下已存在工作数据：\n${target}\n\n这些数据可能是从旧版本（如 v1.0.6）复制过来的，或是之前使用过程中产生的。\n\n请选择如何处理：`,
      detail:
        `✅ 继续使用现有数据\n` +
        `   — 保留所有历史项目、设置、笔记等，首次打开就能看到旧内容。\n\n` +
        `📦 备份现有数据并新建空白工作区\n` +
        `   — 把现有数据重命名为 workspace.bak-<时间戳>/ 保留，然后在当前位置新建一个空的 workspace/。\n` +
        `   — 适合想全新开始的场景，旧数据仍可手动恢复。\n\n` +
        `🚪 退出软件\n` +
        `   — 不做任何改动，让你先手动处理。`,
      buttons: ['继续使用现有数据', '备份后新建', '退出软件'],
      defaultId: 0,
      cancelId: 2,
      noLink: true,
    })
    if (response === 2) return null
    if (response === 1) {
      // 备份现有数据并新建
      const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
      const backup = target + '.bak-' + stamp
      try {
        fs.renameSync(target, backup)
        log('[guide] 已备份旧数据到:', backup)
      } catch (e) {
        errLog('[guide] 备份失败:', e.message)
        dialog.showErrorBox('备份失败', '无法重命名旧数据文件夹：\n' + e.message + '\n\n请关闭可能占用该文件夹的程序后重试。')
        return null
      }
      fs.mkdirSync(target, { recursive: true })
    }
    // response === 0 直接用现有数据
    return target
  }

  // 场景 B：全新安装（target 不存在）→ 直接新建，无需打扰
  if (!fs.existsSync(target)) {
    log('[guide] 全新安装，在 target 新建空数据根:', target)
    try {
      fs.mkdirSync(target, { recursive: true })
    } catch (e) {
      errLog('[guide] 创建数据根失败:', e.message)
      dialog.showErrorBox('创建数据文件夹失败', e.message)
      return null
    }
    return target
  }

  // 场景 C：target 存在但不是有效数据根（被移动 / 重命名 / 损坏）
  log('[guide] 数据根失效（target 存在但无效）:', target)
  const { response } = dialog.showMessageBoxSync({
    type: 'warning',
    title: '未找到有效数据',
    message: `当前数据文件夹无效：\n${target}\n\n该文件夹可能已被移动、重命名，或不包含完整数据（缺 app.db / data / projects）。`,
    detail:
      `📂 选择已有的数据文件夹\n` +
      `   — 从硬盘上挑选你之前备份过的 workspace 文件夹。\n\n` +
      `📁 在当前位置新建空数据文件夹\n` +
      `   — 直接创建新的空 workspace/，从零开始（现有无效文件夹会被保留，不会被删除）。\n\n` +
      `🚪 退出软件\n` +
      `   — 不做任何改动，让你先确认数据是否真的丢了。`,
    buttons: ['选择已有的数据文件夹', '在当前位置新建空数据文件夹', '退出软件'],
    defaultId: 0,
    cancelId: 2,
    noLink: true,
  })
  if (response === 2) return null
  if (response === 0) {
    const picked = dialog.showOpenDialogSync({
      title: '选择已有的数据文件夹（含 app.db / data / projects）',
      properties: ['openDirectory', 'createDirectory'],
    })
    if (!picked || !picked[0]) return null
    const dir = picked[0]
    if (!isDataRootValid(dir)) {
      dialog.showErrorBox('所选文件夹无效', '该文件夹不含 app.db / data / projects，请选择有效的数据文件夹。')
      return null
    }
    saveSettings({ ...loadSettings(), pathMode: 'custom', customPath: dir })
    return dir
  }
  // response === 1：在当前位置新建空数据根（保留旧文件夹不动）
  try {
    fs.mkdirSync(target, { recursive: true })
  } catch (e) {
    errLog('[guide] 创建数据根失败:', e.message)
    dialog.showErrorBox('创建失败', e.message)
    return null
  }
  return target
}

// 打包态首次启动：若旧版把数据放在系统 userData（早期方案），且新数据根还为空，
// 则一次性把旧数据复制进新数据根（非破坏、不删旧文件），避免「升级后历史数据消失」。
// 注：从开发版 {data,projects} 的旧数据迁移由后端 db.py 统一处理。
function migrateLegacyData(dataRoot) {
  if (!isPackaged) return
  const legacyDb = path.join(app.getPath('userData'), 'data', 'app.db')
  const newDb = path.join(dataRoot, 'app.db')
  if (!fs.existsSync(legacyDb) || fs.existsSync(newDb)) return
  try {
    fs.mkdirSync(dataRoot, { recursive: true })
    const legacyData = path.join(app.getPath('userData'), 'data')
    const legacyProjects = path.join(app.getPath('userData'), 'projects')
    if (fs.existsSync(legacyData)) {
      fs.cpSync(legacyData, path.join(dataRoot, 'data'), { recursive: true })
    }
    if (fs.existsSync(legacyProjects)) {
      fs.cpSync(legacyProjects, path.join(dataRoot, 'projects'), { recursive: true })
    }
    // 旧 userData 布局里 app.db 在 data\ 下，需上移到数据根
    const movedDb = path.join(dataRoot, 'data', 'app.db')
    if (fs.existsSync(movedDb)) fs.renameSync(movedDb, newDb)
    log('[migrate] 已从旧 userData 迁移到数据根:', dataRoot)
  } catch (e) {
    errLog('[migrate] 旧数据迁移失败（不影响启动）:', e.message)
  }
}

function startBackend(port) {
  ensureRuntimeVenv()
  const settings = loadSettings()
  // 数据根失效引导（被移动 / 重命名 / 不存在）→ 可能要求用户选择或退出
  let dataRoot = resolveDataRoot(settings)
  if (!isDataRootValid(dataRoot)) {
    dataRoot = guideDataRoot(settings)
    if (!dataRoot) {
      // 用户选择退出软件
      cleanup()
      app.quit()
      return false
    }
  }
  migrateLegacyData(dataRoot)
  log('startBackend cwd=', BACKEND_DIR)
  log('python bin exists=', fs.existsSync(PYTHON_BIN))
  backendReady = false

  const env = { ...process.env }

  // 确保数据根及子目录存在
  try {
    fs.mkdirSync(dataRoot, { recursive: true })
    fs.mkdirSync(path.join(dataRoot, 'data'), { recursive: true })
    fs.mkdirSync(path.join(dataRoot, 'projects'), { recursive: true })
  } catch (e) {
    log('mkdir data root failed:', e.message)
  }

  currentDataDir = dataRoot
  currentProjectsDir = path.join(dataRoot, 'projects')
  env.SUXIAOMO_DATA_DIR = dataRoot
  env.SUXIAOMO_PROJECTS_DIR = currentProjectsDir
  // 应用包内的 schema / seed 源位置（后端首启复制到数据根/data/{schema,seed}）
  env.SUXIAOMO_SCHEMA_DIR = isPackaged ? PKG_SCHEMA_DIR : path.join(ROOT_DEV, 'backend', 'bundled', 'schema')
  env.SUXIAOMO_SEED_DIR = isPackaged ? PKG_SEED_DIR : path.join(ROOT_DEV, 'backend', 'bundled', 'seed')
  env.SUXIAOMO_LEGACY_DIR = ROOT_DEV   // 旧数据位置（ROOT_DEV），供后端 db.py 一次性迁移
  if (isPackaged) {
    env.SUXIAOMO_PACKAGED = '1' // 标记打包态，供后端隐藏「一键打包」按钮
  }
  log('data root=', dataRoot, '| projects dir=', currentProjectsDir, '| schema dir=', env.SUXIAOMO_SCHEMA_DIR, '| seed dir=', env.SUXIAOMO_SEED_DIR)

  backendProc = spawn(
    PYTHON_BIN,
    ['-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', String(port)],
    { cwd: BACKEND_DIR, windowsHide: true, env }
  )
  backendProc.stdout.on('data', (d) => {
    const s = d.toString()
    process.stdout.write(`[backend] ${s}`)
    log('[backend]', s.trim())
  })
  backendProc.stderr.on('data', (d) => {
    const s = d.toString()
    lastBackendErr += s
    process.stderr.write(`[backend] ${s}`)
    errLog('[backend-err]', s.trim())
  })
  backendProc.on('error', (e) => {
    errLog('backend spawn error:', e.message)
    lastBackendErr += '\n[spawn error] ' + e.message
  })
  // 后端进程提前退出（多半是建库/端口冲突）→ 立即报错，不再干等 40s 超时
  backendProc.on('exit', (code, signal) => {
    log('backend process exited; code=', code, 'signal=', signal, 'ready=', backendReady)
    if (!backendReady && code !== 0) {
      showError(
        '后端启动失败',
        `后端进程以退出码 ${code} 退出（signal=${signal || '-'}）。\n\n后端输出：\n${lastBackendErr.slice(-2500)}`
      )
      cleanup()
      app.quit()
    }
  })
  return true
}

function startFrontend(port, backendPort) {
  // 把后端实际端口注入环境变量，让 vite 的 /api 代理指向正确的后端（端口让路后仍透明）
  const env = { ...process.env, SUXIAOMO_BACKEND_PORT_DEV: String(backendPort) }
  frontendProc = spawn(NPM_BIN, ['run', 'dev', '--', '--port', String(port)], {
    cwd: path.join(ROOT_DEV, 'frontend'),
    windowsHide: true,
    shell: true,
    env,
  })
  frontendProc.stdout.on('data', (d) =>
    process.stdout.write(`[frontend] ${d}`)
  )
  frontendProc.stderr.on('data', (d) =>
    process.stderr.write(`[frontend] ${d}`)
  )
}

// ---- 打包态：本地静态服务 + /api 反向代理 ----
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
  '.map': 'application/json',
}

function proxyApi(req, res) {
  const headers = { ...req.headers }
  delete headers.host
  delete headers.connection
  const options = {
    host: '127.0.0.1',
    port: actualBackendPort,
    method: req.method,
    path: req.url,
    headers,
  }
  const p = http.request(options, (backendRes) => {
    res.writeHead(backendRes.statusCode, backendRes.headers)
    backendRes.pipe(res)
    backendRes.on('error', () => {
      if (!res.destroyed) res.destroy()
    })
  })
  p.on('error', () => {
    // 响应已结束或销毁后不要再写，避免 ERR_STREAM_WRITE_AFTER_END 弹窗
    if (res.writableEnded || res.destroyed) return
    if (!res.headersSent) {
      res.writeHead(502, { 'Content-Type': 'text/plain; charset=utf-8' })
      res.end('Bad Gateway: 后端未就绪')
    } else {
      // headers 已发送且正在流式传输，无法返回 502 body，只能中断连接
      res.destroy()
    }
  })
  req.pipe(p)
}

function serveStaticFile(req, res) {
  let urlPath = decodeURIComponent(req.url.split('?')[0])
  if (urlPath === '/') urlPath = '/index.html'
  let filePath = path.join(FRONTEND_DIST, urlPath)
  if (!filePath.startsWith(FRONTEND_DIST)) {
    res.writeHead(403)
    res.end('Forbidden')
    return
  }
  fs.stat(filePath, (err, stat) => {
    if (err || stat.isDirectory()) {
      filePath = path.join(FRONTEND_DIST, 'index.html')
    }
    fs.readFile(filePath, (e2, data) => {
      if (e2) {
        res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' })
        res.end('Not Found')
        return
      }
      const ext = path.extname(filePath).toLowerCase()
      res.writeHead(200, {
        'Content-Type': MIME[ext] || 'application/octet-stream',
      })
      res.end(data)
    })
  })
}

function startStaticServer(port) {
  log('startStaticServer on', port, 'root=', FRONTEND_DIST)
  staticServer = http.createServer((req, res) => {
    if (req.url.startsWith('/api')) return proxyApi(req, res)
    return serveStaticFile(req, res)
  })
  staticServer.on('error', (e) => errLog('static server error:', e.message))
  staticServer.listen(port, '127.0.0.1')
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    title: APP_TITLE,
    icon: ICON_PATH,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, 'preload.js'),
      // 爆款收集：页面内用 <webview> 内嵌抖音等站点浏览，需要显式开启
      webviewTag: true,
    },
  })
  const target = isPackaged
    ? `http://127.0.0.1:${actualStaticPort}`
    : `http://127.0.0.1:${actualFrontendPort}`
  log('loadURL', target)
  mainWindow.loadURL(target)
  mainWindow.setTitle(APP_TITLE)
  if (!isPackaged) {
    // 开发态：把前端渲染进程的 console.error / 警告实时打印到 npm 终端，方便定位白屏/崩溃
    mainWindow.webContents.on('console-message', (event, level, message) => {
      if (level >= 2) errLog('[renderer]', message)
    })
    // 开发态：在窗口内支持刷新快捷键（桌面版没有浏览器地址栏，否则无法硬刷新）
    // F5 / Ctrl+R = 普通刷新；Ctrl+Shift+R = 忽略缓存强刷（改了 CSS/JS 后用来强制看新代码）
    mainWindow.webContents.on('before-input-event', (event, input) => {
      const isReload = input.key === 'F5' || (input.control && input.key.toLowerCase() === 'r')
      if (!isReload) return
      event.preventDefault()
      if (input.shift) mainWindow.webContents.reloadIgnoringCache()
      else mainWindow.webContents.reload()
    })
  }
  mainWindow.on('closed', () => {
    mainWindow = null
  })
  mainWindow.on('crashed', () => errLog('mainWindow renderer crashed'))
}

// 原生文件拖出：渲染进程（如文件空间缩略图）发起 dragstart 时，
// 由主进程接管为系统级文件拖拽，可拖到桌面 / 剪映 / 其他软件。
ipcMain.on('fs:start-drag', (e, filePath) => {
  try {
    const win = BrowserWindow.fromWebContents(e.sender) || mainWindow
    if (!win) return
    win.webContents.startDrag({
      file: filePath,
      icon: nativeImage.createFromPath(ICON_PATH),
    })
  } catch (err) {
    errLog('startDrag failed:', err && err.message)
  }
})

// 设置页：打开原生文件夹选择对话框
ipcMain.handle('settings:select-folder', async (e) => {
  const win = BrowserWindow.fromWebContents(e.sender) || mainWindow
  const r = await dialog.showOpenDialog(win, {
    properties: ['openDirectory'],
    title: '选择数据存储目录',
  })
  return r.canceled ? '' : r.filePaths[0]
})

// 设置页：获取当前实际数据目录（由主进程在启动后端时确定）
ipcMain.handle('settings:get-data-dir', () => currentDataDir)
// 设置页「打开数据目录」按钮：用系统文件管理器打开当前数据根
ipcMain.handle('settings:open-data-dir', () => {
  if (currentDataDir && fs.existsSync(currentDataDir)) {
    shell.openPath(currentDataDir)
  }
})

// 设置页：读取 / 保存 settings.json
ipcMain.handle('settings:load', () => loadSettings())
ipcMain.handle('settings:save', (e, settings) => {
  saveSettings(settings)
  return true
})

// ── 凭据加密：用 Electron safeStorage（OS 级，Windows=DPAPI / macOS=Keychain / Linux=libsecret）──
// 渲染进程把明文密码交给主进程加密后存数据库（只存密文，绝不存明文）；
// 自动登录 / 自动填充时再把密文取回主进程解密。密钥由操作系统管理，跨端口 / 重启不受影响。
ipcMain.handle('safe-storage:encrypt', async (e, plainText) => {
  try {
    const { safeStorage } = require('electron')
    if (!safeStorage.isEncryptionAvailable()) {
      return { ok: false, error: '当前系统不可用凭据加密（safeStorage 不可用）' }
    }
    const buf = await safeStorage.encryptStringAsync(String(plainText ?? ''))
    return { ok: true, data: buf.toString('base64') }
  } catch (err) {
    return { ok: false, error: String(err && err.message || err) }
  }
})

ipcMain.handle('safe-storage:decrypt', async (e, b64) => {
  try {
    const { safeStorage } = require('electron')
    if (!safeStorage.isEncryptionAvailable()) {
      return { ok: false, error: '当前系统不可用凭据加密（safeStorage 不可用）' }
    }
    const buf = Buffer.from(String(b64 || ''), 'base64')
    const res = await safeStorage.decryptStringAsync(buf)
    // decryptStringAsync 返回 { result, shouldReEncrypt }
    const text = typeof res === 'string' ? res : (res && res.result)
    return { ok: true, data: text }
  } catch (err) {
    return { ok: false, error: String(err && err.message || err) }
  }
})

// ── 爆款收集：原生截屏 / 外部浏览器 ─────────────────────────────
// 截当前应用窗口（含页面内 <webview> 里加载的抖音等站点），可传 rect 只截某个区域。
// rect: { x, y, width, height }，单位为渲染进程的 CSS 像素；不传则整窗。
ipcMain.handle('viral:capture-page', async (e, rect) => {
  try {
    const win = BrowserWindow.fromWebContents(e.sender) || mainWindow
    if (!win) return ''
    let img
    if (rect && rect.width > 0 && rect.height > 0) {
      img = await win.webContents.capturePage({
        x: Math.round(rect.x || 0),
        y: Math.round(rect.y || 0),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
      })
    } else {
      img = await win.webContents.capturePage()
    }
    return img.toDataURL()
  } catch (err) {
    errLog('[viral] capture-page failed:', err && err.message)
    return ''
  }
})

// ── 爆款收集·方案 C：独立浏览器大窗口 ────────────────────────────
// 从主窗口（或任意渲染进程）请求打开一个独立、可自由缩放、关闭前一直常驻的浏览器窗口，
// 让抖音/快手/B站等站点获得正常桌面视口，彻底解决内嵌侧栏「内容显示不全」的问题。
// 窗口加载同一份前端、路由 /viral-browser，与主窗口共享登录态（默认 partition）。
function createBrowserWindow(url) {
  const win = new BrowserWindow({
    width: 1140,
    height: 820,
    minWidth: 480,
    minHeight: 360,
    title: '爆款浏览器',
    icon: ICON_PATH,
    show: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, 'preload.js'),
      webviewTag: true,
    },
  })
  const start = url || 'https://www.douyin.com/'
  const target = isPackaged
    ? `http://127.0.0.1:${actualStaticPort}/viral-browser?url=${encodeURIComponent(start)}`
    : `http://127.0.0.1:${actualFrontendPort}/viral-browser?url=${encodeURIComponent(start)}`
  log('[browser-window] loadURL', target)
  win.loadURL(target)
  browserWindows.push(win)
  win.on('closed', () => {
    browserWindows = browserWindows.filter((w) => w !== win)
  })
  return win
}

ipcMain.handle('viral:open-browser-window', (e, url) => {
  try {
    createBrowserWindow(url)
    return { ok: true }
  } catch (err) {
    errLog('[browser-window] open failed:', err && err.message)
    return { ok: false, error: String((err && err.message) || err) }
  }
})

// 爆款收集：用系统默认浏览器（外部 Chrome/Edge 等）打开官方搜索/链接页（如搜原著小说）
ipcMain.handle('viral:open-external', (e, url) => {
  try {
    if (!/^https?:\/\//i.test(url || '')) return { ok: false, error: '仅支持 http(s) 链接' }
    shell.openExternal(url)
    log('[open-external]', url)
    return { ok: true }
  } catch (err) {
    errLog('[open-external] failed:', err && err.message)
    return { ok: false, error: String((err && err.message) || err) }
  }
})

// 浏览器窗口截到的图 → 转发给主窗口，主窗口追加进「爆款收集」暂存区
ipcMain.on('viral:browser-screenshot', (e, dataUrl) => {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('viral:tray-add', dataUrl)
  }
})

// 截整块屏幕（兜底：当 webview 内容被站点反截屏、或用户想截外部浏览器窗口时用）
ipcMain.handle('viral:capture-screen', async () => {
  try {
    const primary = screen.getPrimaryDisplay()
    const { width, height } = primary.size
    const scale = primary.scaleFactor || 1
    const sources = await desktopCapturer.getSources({
      types: ['screen'],
      thumbnailSize: { width: Math.round(width * scale), height: Math.round(height * scale) },
    })
    if (!sources.length) return ''
    return sources[0].thumbnail.toDataURL()
  } catch (err) {
    errLog('[viral] capture-screen failed:', err && err.message)
    return ''
  }
})

// 防止内嵌浏览器（及任何 webContents）跳转到私有协议（如 bitbrowser://）
// 导致 Windows 弹出「找不到能打开此链接的应用」。只放行 http/https，
// 其余协议静默拦截；外部打开交给用户复制链接。
// 注：必须在窗口创建前注册，对所有后续 webContents 生效。
app.on('web-contents-created', (event, contents) => {
  const isHttp = (u) => /^https?:\/\//i.test(u || '')

  // 0) 对 <webview> 反检测：覆盖自动化特征、用真实 Chrome UA，降低被站点识别成 Electron 的概率
  try {
    if (contents.getType && contents.getType() === 'webview') {
      const realUA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
      contents.setUserAgent(realUA)
      contents.on('dom-ready', () => {
        contents.executeJavaScript(`
          (() => {
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN','zh','en'] });
            if (window.chrome && window.chrome.runtime) { try { delete window.chrome.runtime } catch(e){} }
            console.log('[anti-detect] injected')
          })()
        `).catch(() => {})
      })
    }
  } catch (e) { /* ignore */ }

  // 1) window.open / target=_blank：私有协议一律拒绝；http(s) 则让宿主窗口的 webview 在同一页打开
  //    （抖音点作者名等会触发新窗口，我们要在当前 webview 内跳转，而不是弹独立窗口）
  try {
    contents.setWindowOpenHandler((details) => {
      if (!isHttp(details.url)) {
        log('[protocol-block] blocked window.open to', details.url)
        return { action: 'deny' }
      }
      // 内嵌 webview（爆款收集抖音）内触发的新窗口：让其在同一 webview 内跳转
      if (contents.getType && contents.getType() === 'webview') {
        const win = contents.getOwnerBrowserWindow ? contents.getOwnerBrowserWindow() : null
        if (win && win.webContents) {
          win.webContents.send('viral:open-in-same-webview', details.url)
          log('[window-open] redirect to same webview:', details.url)
        }
        return { action: 'deny' }
      }
      // 主窗口内的普通外部链接（如 AI 密钥库「打开」按钮）：在系统默认浏览器打开
      try {
        shell.openExternal(details.url)
        log('[window-open] openExternal:', details.url)
      } catch (e) {
        log('[window-open] openExternal failed:', details.url, e && e.message)
      }
      return { action: 'deny' }
    })
  } catch (e) { /* ignore */ }

  // 2) 主框架与 iframe 的常规导航 / 重定向（Electron 30+ 用 will-frame-navigate）
  const blockIfPrivate = (e, url) => {
    if (!isHttp(url)) {
      try { e.preventDefault() } catch (_) {}
      log('[protocol-block] blocked navigation to', url)
    }
  }
  contents.on('will-navigate', blockIfPrivate)
  contents.on('will-redirect', blockIfPrivate)
  contents.on('new-window', (e, url) => blockIfPrivate(e, url))
  try {
    contents.on('will-frame-navigate', (e) => {
      if (!isHttp(e?.url)) {
        try { e.preventDefault() } catch (_) {}
        log('[protocol-block] blocked frame navigation to', e?.url)
      }
    })
  } catch (e) { /* Electron 低版本可能没有该事件 */ }
  try {
    contents.on('will-frame-redirect', (e) => {
      if (!isHttp(e?.url)) {
        try { e.preventDefault() } catch (_) {}
        log('[protocol-block] blocked frame redirect to', e?.url)
      }
    })
  } catch (e) { /* ignore */ }
})

// 设置页：用户点击「立即重启」后安全重启应用（cleanup 会杀后端/前端进程与端口）
ipcMain.handle('app:restart', () => {
  log('[app] 用户请求重启应用')
  app.relaunch()
  app.quit()
})

// 清除缓存：scope 可为 'http'（仅 HTTP 磁盘缓存，解决样式不更新）或 'all'（HTTP 缓存 + 本地存储）
// 注意：业务数据在 app.db（SQLite），不在此处清除范围，清缓存不会删作品。
ipcMain.handle('app:clear-cache', async (e, scope) => {
  const { session } = require('electron')
  const s = session.defaultSession
  try {
    if (scope === 'http' || scope === 'all') {
      await s.clearCache()
      log('[cache] 已清除 HTTP 磁盘缓存 (scope=' + scope + ')')
    }
    if (scope === 'all') {
      await s.clearStorageData({
        storages: ['localStorage', 'indexedDB', 'websql', 'cookies', 'cacheStorage', 'serviceWorker'],
      })
      log('[cache] 已清除本地存储 (localStorage/IndexedDB/cookies 等)')
    }
    return { ok: true }
  } catch (err) {
    errLog('[cache] 清除失败:', err && err.message ? err.message : err)
    return { ok: false, error: err && err.message ? err.message : String(err) }
  }
})

// 发布版本（后台异步）：
// 前端点「开始打包」后，由后端（backend/build_release/router.py）直接 Popen spawn build.js，
// 带 SUXIAOMO_BUILD_FROM_APP=1 使其跳过杀进程，应用不掉线；前端轮询 /api/build/status 看进度。
// 因此主进程不再需要退出应用去跑打包，以下旧 handler 已废弃移除（保留注释说明历史）。
// 若仍收到旧调用，仅记录、绝不退出应用。
ipcMain.on('app:build-and-quit', (e, payload) => {
  log('[build] 收到旧式 build-and-quit 调用（已废弃），打包改由后端后台处理，应用不退出。')
})

// 启动阶段状态：主进程通过 ipc 推送到加载页
let bootStage = { stage: 'init', text: '正在初始化...', detail: '' }
function setBootStage(stage, text, detail = '') {
  bootStage = { stage, text, detail }
  log('[boot]', stage, text, detail)
  if (loadingWindow && !loadingWindow.isDestroyed()) {
    loadingWindow.webContents.send('boot:stage', bootStage)
  }
}

function showLoading() {
  // 用 data URL 内联加载页——避免 asar 打包后 loadFile 找不到文件导致黑屏
  const html = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"/><style>
    *{box-sizing:border-box}html,body{height:100%;margin:0;background:#1b1b2f;color:#e6e6f0;
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;overflow:hidden}
    body{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:24px 28px}
    .brand{font-size:20px;font-weight:600;letter-spacing:.5px}
    .brand .dot{display:inline-block;width:8px;height:8px;background:#8b8bf6;border-radius:50%;margin-left:8px;vertical-align:middle;animation:pulse 1.6s ease-in-out infinite}
    @keyframes pulse{0%,100%{opacity:.4;transform:scale(.8)}50%{opacity:1;transform:scale(1.1)}}
    .stage{margin-top:18px;font-size:14px;text-align:center;min-height:20px}
    .detail{margin-top:6px;font-size:11px;color:#9aa0c0;text-align:center;min-height:14px;word-break:break-all;max-width:400px}
    .progress{margin-top:18px;width:280px;height:4px;background:#2e3454;border-radius:2px;overflow:hidden}
    .progress .bar{height:100%;background:linear-gradient(90deg,#8b8bf6,#a4a4f7);width:0%;transition:width .4s ease}
    .progress.done .bar{background:linear-gradient(90deg,#5ddb9a,#4ed190);width:100%!important}
    .progress.error .bar{background:#ff8a8a}
    .stages{margin-top:16px;font-size:11px;color:#9aa0c0;display:flex;gap:16px}
    .stages span{opacity:.35;transition:opacity .3s}
    .stages span.active{opacity:1;color:#8b8bf6}
    .stages span.done{opacity:.7;color:#5ddb9a}
    button.cancel{margin-top:18px;background:transparent;border:1px solid #2e3454;color:#9aa0c0;padding:5px 16px;border-radius:6px;font-size:11px;cursor:pointer;transition:all .15s}
    button.cancel:hover{border-color:#ff8a8a;color:#ff8a8a}
  </style></head><body>
    <div class="brand">苏小沫工作台<span class="dot"></span></div>
    <div class="stage" id="stage">正在初始化...</div>
    <div class="detail" id="detail"></div>
    <div class="progress" id="progress"><div class="bar" id="bar"></div></div>
    <div class="stages"><span data-stage="init">初始化</span><span data-stage="venv">依赖</span><span data-stage="backend">后端</span><span data-stage="frontend">前端</span><span data-stage="done">完成</span></div>
    <button class="cancel" id="cancelBtn">取消启动</button>
    <script>var m={init:0,venv:1,backend:2,frontend:3,done:4,error:4};
    function u(s){var d=document;d.getElementById('stage').textContent=s.text||'';d.getElementById('detail').textContent=s.detail||'';
    var i=m[s.stage]||0;var ss=d.querySelectorAll('.stages span');
    ss.forEach(function(e,k){e.classList.remove('active','done');if(k<i)e.classList.add('done');else if(k===i)e.classList.add('active')});
    d.getElementById('bar').style.width=((i+1)/5*100)+'%';
    d.getElementById('progress').classList.remove('done','error');
    if(s.stage==='done')d.getElementById('progress').classList.add('done');
    if(s.stage==='error')d.getElementById('progress').classList.add('error');}
    if(window.electronAPI){window.electronAPI.onStage(u);document.getElementById('cancelBtn').onclick=function(){window.electronAPI.cancel()}}
    </script></body></html>`
  loadingWindow = new BrowserWindow({
    width: 460,
    height: 240,
    frame: false,
    resizable: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'loading-preload.js'),
    },
  })
  loadingWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(html))
}

// 加载页可点「取消」中止启动（用于卡在某个阶段时给用户退出路径）
ipcMain.handle('boot:cancel', () => {
  log('[boot] 用户取消启动')
  cleanup()
  app.quit()
  return true
})

function cleanup() {
  if (loadingWindow && !loadingWindow.isDestroyed()) {
    loadingWindow.destroy()
    loadingWindow = null
  }
  if (staticServer) {
    try {
      staticServer.close()
    } catch (e) {
      /* ignore */
    }
    staticServer = null
  }
  for (const p of [backendProc, frontendProc]) {
    if (p) {
      try {
        p.kill('SIGTERM')
      } catch (e) {
        /* ignore */
      }
    }
  }
  // 关闭所有独立浏览器窗口（方案 C）
  for (const w of browserWindows) {
    try {
      if (!w.isDestroyed()) w.destroy()
    } catch (e) {
      /* ignore */
    }
  }
  browserWindows = []
  // 不再强杀占用端口的进程：退出时仅结束自身子进程，避免误伤其他程序。
}

// 启动前滚动旧日志：electron-error.log -> .1 -> .2 -> ... -> .5（丢弃 .5），保留最近 5 份
function rotateErrorLog() {
  if (!LOG_PATH) return
  try {
    if (!fs.existsSync(LOG_PATH)) return
    for (let i = 5; i >= 1; i--) {
      const src = i === 1 ? LOG_PATH : `${LOG_PATH}.${i - 1}`
      const dst = `${LOG_PATH}.${i}`
      if (fs.existsSync(src)) {
        try {
          fs.renameSync(src, dst)
        } catch (e) {
          /* 上一份不存在则跳过 */
        }
      }
    }
  } catch (e) {
    /* 忽略 */
  }
}

async function boot() {
  try {
    if (LOG_PATH) {
      fs.mkdirSync(path.dirname(LOG_PATH), { recursive: true })
      rotateErrorLog() // 保留旧日志副本，不再直接清空
    }
  } catch (e) {}
  log('boot start; isPackaged=', isPackaged, 'RES=', RES)
  showLoading()
  setBootStage('init', '正在初始化...', '准备启动本地服务')

  // 不再强杀占用端口的进程：端口被占用时由 pickPort 自动让路到空闲端口。

  // 启动后端：先 ensureRuntimeVenv（打包态首次启动时可能要装 50+ 秒）
  setBootStage('venv', '正在准备运行环境...', isPackaged ? '首次启动需安装 Python 依赖，请耐心等待' : '')
  // 注意：ensureRuntimeVenv 现在是异步函数，await 期间主线程不会被阻塞
  if (isPackaged) {
    await ensureRuntimeVenv()
  }
  setBootStage('backend', '正在启动后端...', `端口 ${actualBackendPort}`)

  actualBackendPort = await pickPort(PREFERRED_BACKEND_PORT)
  if (!startBackend(actualBackendPort)) return
  log('waiting for backend', actualBackendPort)
  try {
    await waitForPort(actualBackendPort)
    backendReady = true
    log('backend port ready')
  } catch (e) {
    setBootStage('error', '后端启动失败', e.message)
    showError(
      '后端启动失败',
      `${e.message}\n\n后端输出：\n${lastBackendErr.slice(-1500)}`
    )
    cleanup()
    app.quit()
    return
  }

  setBootStage('frontend', '正在启动前端...', isPackaged ? `本地静态服务 ${actualStaticPort}` : `vite 开发服务 ${actualFrontendPort}`)
  try {
    if (isPackaged) {
      actualStaticPort = await pickPort(PREFERRED_STATIC_PORT)
      startStaticServer(actualStaticPort)
      log('waiting for static', actualStaticPort)
      await waitForPort(actualStaticPort)
    } else {
      actualFrontendPort = await pickPort(PREFERRED_FRONTEND_PORT)
      startFrontend(actualFrontendPort, actualBackendPort)
      log('waiting for frontend', actualFrontendPort)
      await waitForPort(actualFrontendPort)
    }
  } catch (e) {
    setBootStage('error', '前端启动失败', e.message)
    showError('前端启动失败', e.message)
    cleanup()
    app.quit()
    return
  }

  setBootStage('done', '启动完成', '正在打开主窗口...')
  // 先建主窗口，再销毁加载窗：避免「加载窗已关、主窗未建」的空窗期触发 window-all-closed 误退
  createWindow()
  if (loadingWindow && !loadingWindow.isDestroyed()) {
    loadingWindow.destroy()
  }
  loadingWindow = null
}

// 单实例锁：防止同一模式双开两个客户端抢写同一份 userData 数据库。
// 开发版与打包版已用不同 app.name 区分，允许同时各运行一个（便于对照测试），
// 但同一模式仍不能双开。
const gotLock = app.requestSingleInstanceLock()
if (!gotLock) {
  // 已有实例在跑 → 啥也不做直接退出（second-instance 事件会叫醒旧窗口）
  log('[boot] 已有实例在运行，本次启动退出')
  app.quit()
} else {
  app.on('second-instance', () => {
    // 用户再次双击 exe 时 → 把已有窗口叫醒到最前面
    if (mainWindow && !mainWindow.isDestroyed()) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.show()
      mainWindow.focus()
    } else if (loadingWindow && !loadingWindow.isDestroyed()) {
      // 主窗口还没建好（还在启动流程中）→ 至少把加载窗叫到前面
      loadingWindow.show()
      loadingWindow.focus()
    } else {
      // 主窗口和加载窗都没了（异常状态）→ 提示用户
      dialog.showMessageBoxSync({
        type: 'info',
        title: '软件已在运行',
        message: '苏小沫工作台已在运行中。\n\n请检查任务栏/系统托盘，或结束现有进程后再试。',
      })
    }
  })
}

app.whenReady().then(() => {
  Menu.setApplicationMenu(null) // 隐藏默认英文菜单，保持窗口简洁

  // 兜底：如果某些私有协议（如 bitbrowser://）突破了 will-navigate 拦截，
  // 注册一个内部 no-op 处理器，避免 Windows 弹出「找不到能打开此链接的应用」。
  // 这个注册只影响本应用内部的网络栈，不会修改系统默认协议关联。
  const noopProtocols = ['bitbrowser']
  for (const scheme of noopProtocols) {
    try {
      if (!protocol.isProtocolRegistered(scheme)) {
        protocol.registerStringProtocol(scheme, (request, callback) => {
          log('[protocol-noop] ignored', request.url)
          callback('') // 返回空内容，不弹系统窗
        })
      }
    } catch (e) {
      errLog('[protocol-noop] register failed:', scheme, e.message)
    }
  }

  return boot()
})
app.on('window-all-closed', () => {
  log('window-all-closed fired; mainWindow=', !!mainWindow)
  cleanup()
  if (process.platform !== 'darwin') app.quit()
})
app.on('before-quit', cleanup)
