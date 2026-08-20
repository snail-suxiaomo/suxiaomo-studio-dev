import { build } from 'vite'

await build({
  configFile: 'F:/suxiaomo-studio/frontend/vite.config.js',
  build: {
    outDir: 'dist3',
    emptyOutDir: false,
  },
})
