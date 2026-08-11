const SESSION_ID = 'stage1-demo-session'

let currentConversationId = crypto.randomUUID()

export async function sendMessage(content) {
  const res = await fetch('/api/v1/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: SESSION_ID,
      conversation_id: currentConversationId,
      content,
    }),
  })

  const data = await res.json()

  if (!res.ok) {
    throw new Error(`Request failed with status ${res.status}`)
  }

  if (data.conversation_id) {
    currentConversationId = data.conversation_id
  }

  return data
}
