export async function sendMessage(content, sessionId, conversationId) {
  const res = await fetch('/api/v1/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: sessionId,
      conversation_id: conversationId,
      content,
    }),
  })

  const data = await res.json()

  if (!res.ok) {
    throw new Error(`Request failed with status ${res.status}`)
  }

  return data
}

export async function fetchHistory(conversationId) {
  const res = await fetch(`/api/v1/chat/${conversationId}`)
  const data = await res.json()

  if (!res.ok) {
    throw new Error(`Request failed with status ${res.status}`)
  }

  return data
}
