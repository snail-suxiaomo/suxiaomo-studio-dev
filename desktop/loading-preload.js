const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  // 接收主进程推送的启动阶段更新
  onStage: (cb) => {
    ipcRenderer.on('boot:stage', (_e, payload) => cb(payload))
  },
  // 用户点取消按钮
  cancel: () => ipcRenderer.invoke('boot:cancel'),
})