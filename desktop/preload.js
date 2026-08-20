/**
 * 预加载脚本（contextIsolation: true 下唯一安全向渲染进程暴露 API 的方式）
 * 仅暴露必要的原生能力，不开放任意 Node API。
 */
const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  // 由主进程发起原生文件拖拽（拖到桌面 / 剪映 / 其他软件）
  startFileDrag: (filePath) => ipcRenderer.send('fs:start-drag', filePath),

  // 打开原生文件夹选择对话框，返回选中的路径（取消则返回空字符串）
  selectFolder: () => ipcRenderer.invoke('settings:select-folder'),

  // 获取当前实际使用的数据目录（由主进程在启动时确定）
  getDataDir: () => ipcRenderer.invoke('settings:get-data-dir'),

  // 用系统文件管理器打开当前数据目录
  openDataDir: () => ipcRenderer.invoke('settings:open-data-dir'),

  // 读取 / 保存桌面版设置（由主进程读写 settings.json）
  loadSettings: () => ipcRenderer.invoke('settings:load'),
  saveSettings: (settings) => ipcRenderer.invoke('settings:save', settings),

  // 重启整个应用（设置路径等需要重启生效时使用）
  restartApp: () => ipcRenderer.invoke('app:restart'),

  // 凭据加密 / 解密：主进程用 safeStorage（OS 级）处理，渲染进程只拿到密文 / 明文
  encryptPassword: (plain) => ipcRenderer.invoke('safe-storage:encrypt', plain),
  decryptPassword: (b64) => ipcRenderer.invoke('safe-storage:decrypt', b64),

  // 清除缓存：scope = 'http'（仅 HTTP 磁盘缓存）/ 'all'（HTTP 缓存 + 本地存储）
  clearCache: (scope) => ipcRenderer.invoke('app:clear-cache', scope),

  // 爆款收集：截当前窗口（可指定区域，用于只截内嵌浏览器那一块），返回 dataURL
  capturePage: (rect) => ipcRenderer.invoke('viral:capture-page', rect),
  // 爆款收集：截整块屏幕（兜底），返回 dataURL
  captureScreen: () => ipcRenderer.invoke('viral:capture-screen'),
  // 爆款收集：主进程通知渲染进程，让 webview 在当前页打开 http(s) 链接（替代新窗口）
  onOpenInSameWebview: (cb) => ipcRenderer.on('viral:open-in-same-webview', cb),
  offOpenInSameWebview: (cb) => ipcRenderer.off('viral:open-in-same-webview', cb),

  // 爆款收集·方案 C（独立浏览器窗口）
  // 主窗口/任意处请求打开独立浏览器窗口；传入初始 url
  openBrowserWindow: (url) => ipcRenderer.invoke('viral:open-browser-window', url),
  // 爆款收集：用系统默认浏览器（外部 Chrome/Edge 等）打开官方搜索/链接页（如搜原著）
  openExternal: (url) => ipcRenderer.invoke('viral:open-external', url),
  // 浏览器窗口把截到的图发回主窗口暂存区
  sendTrayScreenshot: (dataUrl) => ipcRenderer.send('viral:browser-screenshot', dataUrl),
  // 主窗口监听浏览器窗口发来的截图，追加进暂存区
  onTrayAdd: (cb) => ipcRenderer.on('viral:tray-add', cb),
  offTrayAdd: (cb) => ipcRenderer.off('viral:tray-add', cb),
})
