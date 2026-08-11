import { useEffect, useRef, useState } from 'react'
import MessageBubble from '../components/MessageBubble'
import ChatInput from '../components/ChatInput'
import { sendMessage, fetchHistory } from '../services/api'

const CONVERSATION_KEY = 'chatbot_conversation_id'
const SESSION_KEY = 'chatbot_session_id'

function getOrCreateStoredId(key) {
  let id = localStorage.getItem(key)
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem(key, id)
  }
  return id
}

export default function ChatInterface() {
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const bottomRef = useRef(null)
  const [conversationId] = useState(() => getOrCreateStoredId(CONVERSATION_KEY))
  const [sessionId] = useState(() => getOrCreateStoredId(SESSION_KEY))

  useEffect(() => {
    let active = true

    fetchHistory(conversationId)
      .then((data) => {
        if (active && Array.isArray(data) && data.length > 0) {
          setMessages(data)
        }
      })
      .catch(() => {})

    return () => {
      active = false
    }
  }, [conversationId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const handleSend = async (content) => {
    setMessages((prev) => [...prev, { role: 'user', content }])
    setIsLoading(true)

    try {
      const data = await sendMessage(content, sessionId, conversationId)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data.message.content },
      ])
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, something went wrong. Please try again.',
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex h-full flex-col bg-white">
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {messages.length === 0 && (
          <div className="flex h-full items-center justify-center text-sm text-gray-400">
            Ask me anything to get started.
          </div>
        )}
        <div className="flex flex-col gap-3">
          {messages.map((msg, i) => (
            <MessageBubble key={i} role={msg.role} content={msg.content} />
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="flex items-center gap-1 rounded-lg rounded-bl-sm bg-gray-100 px-4 py-2">
                <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400" />
                <span
                  className="h-2 w-2 animate-bounce rounded-full bg-gray-400"
                  style={{ animationDelay: '0.15s' }}
                />
                <span
                  className="h-2 w-2 animate-bounce rounded-full bg-gray-400"
                  style={{ animationDelay: '0.3s' }}
                />
              </div>
            </div>
          )}
        </div>
        <div ref={bottomRef} />
      </div>
      <ChatInput onSend={handleSend} disabled={isLoading} />
    </div>
  )
}
