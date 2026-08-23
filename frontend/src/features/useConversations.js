import { useEffect, useRef, useState, useCallback } from 'react'
import { sendMessage, fetchHistory, fetchConversationTitle } from '../services/api'

export const SESSION_KEY = 'chatbot_session_id'
export const CONVERSATION_LIST_KEY = 'chatbot_conversations'
export const ACTIVE_CONV_KEY = 'chatbot_active_conversation_id'
export const LEGACY_CONV_KEY = 'chatbot_conversation_id'

// Safe Storage access utilities protecting against SecurityError, quota, or restricted environments
export function safeGetItem(key) {
  try {
    return typeof window !== 'undefined' && window.localStorage ? localStorage.getItem(key) : null
  } catch {
    return null
  }
}

export function safeSetItem(key, value) {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      localStorage.setItem(key, value)
    }
  } catch {
    // Graceful degradation when storage is unavailable or quota exceeded
  }
}

export function safeRemoveItem(key) {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      localStorage.removeItem(key)
    }
  } catch {
    // Graceful degradation
  }
}

function getOrCreateSessionId() {
  let id = safeGetItem(SESSION_KEY)
  if (!id || typeof id !== 'string' || id.trim().length === 0) {
    id = crypto.randomUUID()
    safeSetItem(SESSION_KEY, id)
  }
  return id
}

function isValidConversation(item) {
  return (
    item !== null &&
    typeof item === 'object' &&
    typeof item.id === 'string' &&
    item.id.trim().length > 0 &&
    typeof item.title === 'string'
  )
}

function createDefaultConversation() {
  const firstId = crypto.randomUUID()
  return {
    id: firstId,
    title: 'New Chat',
    lastActivity: new Date().toISOString(),
    createdAt: new Date().toISOString(),
  }
}

export function initConversations() {
  const legacyConvId = safeGetItem(LEGACY_CONV_KEY)
  const storedList = safeGetItem(CONVERSATION_LIST_KEY)
  let list = []

  if (storedList !== null) {
    try {
      const parsed = JSON.parse(storedList)
      if (Array.isArray(parsed)) {
        list = parsed.filter(isValidConversation)
        // If parsed contained items but NONE were valid, remove the corrupt key
        if (list.length === 0 && parsed.length > 0) {
          safeRemoveItem(CONVERSATION_LIST_KEY)
        }
      } else {
        // Corrupt schema (e.g. object, string, number): remove only this specific key
        safeRemoveItem(CONVERSATION_LIST_KEY)
        list = []
      }
    } catch {
      // Malformed JSON: remove only this specific key
      safeRemoveItem(CONVERSATION_LIST_KEY)
      list = []
    }
  }

  // Backwards-compatible migration of legacy single-conversation storage
  if (list.length === 0 && legacyConvId && typeof legacyConvId === 'string' && legacyConvId.trim().length > 0) {
    const migrated = {
      id: legacyConvId.trim(),
      title: 'Previous Chat',
      lastActivity: new Date().toISOString(),
      createdAt: new Date().toISOString(),
    }
    list = [migrated]
    safeSetItem(CONVERSATION_LIST_KEY, JSON.stringify(list))
    safeSetItem(ACTIVE_CONV_KEY, migrated.id)
    safeRemoveItem(LEGACY_CONV_KEY)
  } else if (list.length === 0) {
    const defaultConv = createDefaultConversation()
    list = [defaultConv]
    safeSetItem(CONVERSATION_LIST_KEY, JSON.stringify(list))
    safeSetItem(ACTIVE_CONV_KEY, defaultConv.id)
  }

  let activeId = safeGetItem(ACTIVE_CONV_KEY)
  if (!activeId || typeof activeId !== 'string' || !list.some((c) => c && c.id === activeId)) {
    activeId = list[0]?.id || crypto.randomUUID()
    safeSetItem(ACTIVE_CONV_KEY, activeId)
  }

  return { list, activeId }
}

export function useConversations() {
  const [sessionId] = useState(getOrCreateSessionId)
  const [initialData] = useState(initConversations)
  const [conversationList, setConversationList] = useState(initialData.list)
  const [activeConversationId, setActiveConversationId] = useState(
    initialData.activeId
  )
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [isHistoryLoading, setIsHistoryLoading] = useState(false)
  const [error, setError] = useState(null)

  const activeFetchIdRef = useRef(null)
  const abortControllerRef = useRef(null)

  // Persist conversation list changes
  useEffect(() => {
    if (Array.isArray(conversationList)) {
      safeSetItem(
        CONVERSATION_LIST_KEY,
        JSON.stringify(conversationList)
      )
    }
  }, [conversationList])

  // Persist active conversation ID changes
  useEffect(() => {
    if (activeConversationId) {
      safeSetItem(ACTIVE_CONV_KEY, activeConversationId)
    }
  }, [activeConversationId])

  // Fetch messages when activeConversationId changes
  useEffect(() => {
    if (!activeConversationId) return

    // Abort previous in-flight fetch
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }

    const controller = new AbortController()
    abortControllerRef.current = controller
    activeFetchIdRef.current = activeConversationId

    setIsHistoryLoading(true)
    setError(null)
    setMessages([])

    fetchHistory(activeConversationId, controller.signal)
      .then((data) => {
        // Race condition protection: ignore response if user switched away
        if (activeFetchIdRef.current === activeConversationId) {
          if (Array.isArray(data)) {
            const sanitized = data
              .filter((m) => m && typeof m === 'object')
              .map((m) => ({
                id: m.id || crypto.randomUUID(),
                role: m.role || 'assistant',
                content: typeof m.content === 'string' ? m.content : '',
                created_at: m.created_at || new Date().toISOString(),
                isStreaming: false,
              }))
            setMessages(sanitized)

            // Retroactive topic recognition: If conversation has generic title and has messages, fetch AI topic title
            const currentConv = (Array.isArray(conversationList) ? conversationList : []).find(
              (c) => c && c.id === activeConversationId
            )
            const genericTitles = new Set(['new chat', 'previous chat', 'hi', 'hello', 'hey', 'new conversation'])
            const isGeneric = currentConv && genericTitles.has((currentConv.title || '').trim().toLowerCase())

            if (isGeneric && sanitized.length > 0) {
              fetchConversationTitle(activeConversationId, controller.signal)
                .then((newTitle) => {
                  if (newTitle && newTitle !== 'New Conversation' && activeFetchIdRef.current === activeConversationId) {
                    setConversationList((prev) =>
                      (Array.isArray(prev) ? prev : []).map((c) =>
                        c && c.id === activeConversationId ? { ...c, title: newTitle } : c
                      )
                    )
                  }
                })
                .catch(() => {
                  // Silent fallback
                })
            }
          } else {
            setMessages([])
          }
          setIsHistoryLoading(false)
        }
      })
      .catch((err) => {
        if (err.name === 'AbortError') return
        if (activeFetchIdRef.current === activeConversationId) {
          setError('Failed to load conversation history. Please try again.')
          setIsHistoryLoading(false)
        }
      })

    return () => {
      controller.abort()
    }
  }, [activeConversationId])

  const handleNewChat = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }

    const newId = crypto.randomUUID()
    const newConv = {
      id: newId,
      title: 'New Chat',
      lastActivity: new Date().toISOString(),
      createdAt: new Date().toISOString(),
    }

    setConversationList((prev) => [newConv, ...(Array.isArray(prev) ? prev : [])])
    setActiveConversationId(newId)
    setMessages([])
    setError(null)
  }, [])

  const handleSelectConversation = useCallback(
    (id) => {
      if (id === activeConversationId) return
      setActiveConversationId(id)
    },
    [activeConversationId]
  )

  const handleSendMessage = useCallback(
    async (content) => {
      const targetConvId = activeConversationId
      if (!targetConvId || !content || typeof content !== 'string' || !content.trim()) return

      const userText = content.trim()
      const userMsgId = crypto.randomUUID()
      setMessages((prev) => [
        ...(Array.isArray(prev) ? prev : []),
        {
          id: userMsgId,
          role: 'user',
          content: userText,
          created_at: new Date().toISOString(),
          isStreaming: false,
        },
      ])
      setIsLoading(true)
      setError(null)

      // Update conversation timestamp and initial preview in the sidebar
      setConversationList((prev) => {
        return (Array.isArray(prev) ? prev : []).map((conv) => {
          if (conv && conv.id === targetConvId) {
            return {
              ...conv,
              lastActivity: new Date().toISOString(),
            }
          }
          return conv
        })
      })

      try {
        const data = await sendMessage(userText, sessionId, targetConvId)
        if (activeFetchIdRef.current === targetConvId) {
          setMessages((prev) => [
            ...(Array.isArray(prev) ? prev : []),
            {
              role: 'assistant',
              content: typeof data?.message?.content === 'string' ? data.message.content : '',
              id: data?.message?.id || crypto.randomUUID(),
              created_at: data?.message?.created_at || new Date().toISOString(),
              isStreaming: true,
            },
          ])
          setError(null)

          // Background AI topic title recognition: check if conversation has generic title
          const targetConv = (Array.isArray(conversationList) ? conversationList : []).find(
            (c) => c && c.id === targetConvId
          )
          const genericTitles = new Set(['new chat', 'previous chat', 'hi', 'hello', 'hey', 'new conversation'])
          const isGeneric = !targetConv || genericTitles.has((targetConv.title || '').trim().toLowerCase())

          if (isGeneric) {
            fetchConversationTitle(targetConvId)
              .then((newTitle) => {
                if (newTitle && newTitle !== 'New Conversation') {
                  setConversationList((prev) =>
                    (Array.isArray(prev) ? prev : []).map((conv) =>
                      conv && conv.id === targetConvId ? { ...conv, title: newTitle } : conv
                    )
                  )
                }
              })
              .catch(() => {
                // Silent fallback
              })
          }
        }
      } catch (err) {
        if (activeFetchIdRef.current === targetConvId) {
          const isBusy =
            Boolean(err?.isProviderBusy) ||
            err?.code === 'AI_PROVIDER_BUSY' ||
            err?.status === 429 ||
            err?.status === 503
          const message = isBusy
            ? 'The AI servers are currently busy. Please wait a few moments and try again.'
            : (err?.message || 'Failed to send message.')

          setError({
            message,
            isProviderBusy: isBusy,
          })
          // Remove the unpersisted user message so the retry does not duplicate
          setMessages((prev) => (Array.isArray(prev) ? prev.slice(0, -1) : []))
        }
      } finally {
        if (activeFetchIdRef.current === targetConvId) {
          setIsLoading(false)
        }
      }
    },
    [activeConversationId, sessionId, conversationList]
  )

  return {
    sessionId,
    conversationList,
    activeConversationId,
    messages,
    isLoading,
    isHistoryLoading,
    error,
    handleNewChat,
    handleSelectConversation,
    handleSendMessage,
  }
}
