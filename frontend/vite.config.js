import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { readFileSync } from 'fs'
import { resolve } from 'path'

// 取桌面壳 package.json 的版本作为整个应用的版本号（打包版与开发版统一）
const desktopPkg = JSON.parse(readFileSync(resolve(__dirname, '../desktop/package.json'), 'utf-8'))

// 前端开发服务器把 /api 代理到后端。后端端口由桌面壳在启动时确定（可能被占用而让路到临时端口），
// 并通过环境变量 SUXIAOMO_BACKEND_PORT_DEV 注入；未注入时回退到默认 9100。
const backendProxyTarget = process.env.SUXIAOMO_BACKEND_PORT_DEV
  ? `http://127.0.0.1:${process.env.SUXIAOMO_BACKEND_PORT_DEV}`
  : 'http://127.0.0.1:9100'
export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(desktopPkg.version),
  },
  plugins: [vue({
    template: {
      compilerOptions: {
        // <webview> 是 Electron 提供的内置标签（爆款收集页内嵌浏览抖音用），
        // 告诉编译器它不是 Vue 组件，避免「Failed to resolve component」告警
        isCustomElement: (tag) => tag === 'webview',
      },
    },
  })],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: backendProxyTarget,
        changeOrigin: true
      }
    }
  }
})
