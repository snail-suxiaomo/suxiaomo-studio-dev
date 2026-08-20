// common/project-store.js —— 当前选中的小说项目（Pinia + localStorage 持久化）
import { defineStore } from 'pinia'

const KEY = 'sx_current_project'

export const useProjectStore = defineStore('project', {
  state: () => ({
    current: JSON.parse(localStorage.getItem(KEY) || 'null'),
  }),
  getters: {
    hasProject: (s) => !!s.current,
  },
  actions: {
    setCurrent(p) {
      this.current = p
      if (p) localStorage.setItem(KEY, JSON.stringify(p))
      else localStorage.removeItem(KEY)
    },
    clear() {
      this.current = null
      localStorage.removeItem(KEY)
    },
  },
})
