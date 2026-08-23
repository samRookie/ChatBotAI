export class ApiError extends Error {
  constructor(message, status, code, data) {
    super(message || `Request failed with status ${status}`)
    this.name = 'ApiError'
    this.status = status
    this.code = code || (status === 429 || status === 503 ? 'AI_PROVIDER_BUSY' : 'API_ERROR')
    this.isProviderBusy = this.code === 'AI_PROVIDER_BUSY' || status === 429 || status === 503
    this.data = data
  }
}

export async function sendMessage(content, sessionId, conversationId, signal) {
  const res = await fetch('/api/v1/chat/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: sessionId,
      conversation_id: conversationId,
      content,
    }),
    signal,
  })

  let data = null
  try {
    data = await res.json()
  } catch {
    data = null
  }

  if (!res.ok) {
    const errorCode = data?.error?.code
    const errorMsg = data?.error?.message || `Request failed with status ${res.status}`
    throw new ApiError(errorMsg, res.status, errorCode, data)
  }

  return data
}

export async function fetchHistory(conversationId, signal) {
  const res = await fetch(`/api/v1/chat/${conversationId}`, { signal })
  let data = null
  try {
    data = await res.json()
  } catch {
    data = null
  }

  if (!res.ok) {
    const errorCode = data?.error?.code
    const errorMsg = data?.error?.message || `Request failed with status ${res.status}`
    throw new ApiError(errorMsg, res.status, errorCode, data)
  }

  return data
}

export async function fetchConversationTitle(conversationId, signal) {
  const res = await fetch(`/api/v1/chat/${conversationId}/title`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    signal,
  })
  let data = null
  try {
    data = await res.json()
  } catch {
    data = null
  }

  if (!res.ok) {
    const errorCode = data?.error?.code
    const errorMsg = data?.error?.message || `Request failed with status ${res.status}`
    throw new ApiError(errorMsg, res.status, errorCode, data)
  }

  return data?.title
}

