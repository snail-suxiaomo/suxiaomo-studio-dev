// features.js —— 功能启用状态的单一读取入口
// 数据源：features.registry.json（功能元数据）+ enabled-features.js（打包时生成的启用集合）
import registry from './features.registry.json'
import { ENABLED } from './enabled-features.js'

// 开发态：registry 里列的全部功能都启用（与 build.js 默认全开一致）。
// 生产态：以打包时生成的 ENABLED 为准（仅勾选 + 依赖子功能）。
const isDev = import.meta.env.DEV
const baseSet = isDev ? Object.keys(registry.features) : ENABLED
const enabledSet = new Set(baseSet)

export function isEnabled(key) {
  return enabledSet.has(key)
}

export function enabledKeys() {
  return [...enabledSet]
}

export { registry }
export const allFeatureKeys = Object.keys(registry.features)
export const groupOrder = registry.groups || []
