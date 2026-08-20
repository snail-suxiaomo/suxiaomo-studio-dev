// chat/ai-api.js —— 调后端 /api/chat/* 的薄封装
import { api, apiUpload } from '../common/http.js'

// opts: { modelConfigId?, thinking?, reasoningEffort?, sessionId? }
export function askApi(prompt, system_prompt, images = [], texts = [], opts = {}) {
  const { modelConfigId = null, thinking = null, reasoningEffort = null, sessionId = null } = opts
  if (!images.length && !texts.length) {
    return api('/chat/ask', 'POST', {
      prompt,
      system_prompt,
      model_config_id: modelConfigId,
      thinking,
      reasoning_effort: reasoningEffort,
      session_id: sessionId,
    })
  }
  const form = new FormData()
  form.append('prompt', prompt || '')
  if (system_prompt) form.append('system_prompt', system_prompt)
  images.forEach(f => form.append('images', f))
  texts.forEach(f => form.append('texts', f))
  if (modelConfigId != null) form.append('model_config_id', String(modelConfigId))
  if (thinking != null) form.append('thinking', thinking ? 'true' : 'false')
  if (reasoningEffort != null) form.append('reasoning_effort', reasoningEffort)
  if (sessionId != null) form.append('session_id', String(sessionId))
  return apiUpload('/chat/ask-files', form)
}
