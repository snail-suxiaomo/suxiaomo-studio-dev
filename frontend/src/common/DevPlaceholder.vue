<!--
  通用占位页：当功能由「本地系统」转向「外部智能体/平台」时使用。
  设计：明确告诉用户本地不做、推荐去外部智能体（Codex / WorkBuddy），
  并列出理由（存储/积分/模型能力），用户一看就明白下一步去哪。
-->
<template>
  <div class="page dev-placeholder">
    <div class="big-word">建议使用 Codex / WorkBuddy</div>
    <div class="sub-tip">{{ tip }}</div>
    <ul class="reason-list">
      <li>本地存储与算力有限，长记忆/素材库在智能体侧更完善</li>
      <li>本地调用 API 积分成本高，智能体平台付费更划算</li>
      <li>智能体 skill 模型（生图/生视频/长上下文）比本地更强</li>
    </ul>
  </div>
</template>

<script setup>
defineProps({
  tip: {
    type: String,
    default: '本地暂不实现，建议在 Codex 或 WorkBuddy 智能体中使用对应能力',
  },
})
</script>

<style scoped>
.dev-placeholder {
  width: 100%;
  height: 100%;
  max-width: none;
  margin: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 0 32px;
}
.big-word {
  font-size: 52px;
  font-weight: 800;
  letter-spacing: 4px;
  background: linear-gradient(135deg, #ff7a3a, #7b5cff);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  text-align: center;
}
.sub-tip {
  font-size: 15px;
  color: #8a90b0;
  text-align: center;
  max-width: 560px;
}
.reason-list {
  margin: 8px 0 0 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13.5px;
  color: var(--sx-text, #4b5563);
  text-align: center;
}
.reason-list li::before {
  content: '· ';
  color: var(--sx-accent, #7b5cff);
  font-weight: 700;
}
</style>