// 共享 store：ConfirmDialog 挂载时把自己的 open 方法注册到这里。
// useConfirm 直接调用该引用，避免依赖 Vue 内部实例（exposed / proxy）访问的时序问题，
// 这是之前「删除按钮点了没反应」的根因之一。
export const confirmStore = {
  open: null,
}
