import React, { useEffect, useRef, useCallback, useState, useMemo } from 'react'
import MessageBubble from '../components/MessageBubble'
import ChatInput from '../components/ChatInput'

export const CONVERSATION_STARTERS = [
  {
    title: 'Code Review',
    description: 'Paste a snippet for performance and security optimization.',
    prompt: 'Can you review this code snippet for any performance bottlenecks or security issues?\n\n```\n\n```',
    icon: 'code',
    iconColor: 'text-blue-400',
  },
  {
    title: 'Architecture Ideation',
    description: 'Brainstorm the stack and data flow for a new feature.',
    prompt: "I want to build a new feature. Let's discuss the database schema and system architecture.",
    icon: 'account_tree',
    iconColor: 'text-purple-400',
  },
  {
    title: 'Trace a Bug',
    description: 'Paste an error log and stack trace to find the root cause.',
    prompt: "I'm getting this error. Here is the stack trace, help me find the root cause:\n\n",
    icon: 'bug_report',
    iconColor: 'text-rose-400',
  },
  {
    title: 'Prompt Refinement',
    description: 'Draft a strict system instruction for another AI agent.',
    prompt: 'Help me write a strict, zero-shot system prompt for an AI agent that will...',
    icon: 'psychology',
    iconColor: 'text-cyan-400',
  },
  {
    title: 'Refactor to Modern Standards',
    description: 'Update legacy code to use modern, clean syntax.',
    prompt: 'Refactor this code to use modern best practices and clean up the syntax:\n\n',
    icon: 'auto_fix_high',
    iconColor: 'text-amber-400',
  },
  {
    title: 'API Design',
    description: 'Design a clean, consistent REST or RPC endpoint contract.',
    prompt: 'Help me design a clean, well-documented API for the following use case:\n\n',
    icon: 'api',
    iconColor: 'text-emerald-400',
  },
  {
    title: 'Database Design',
    description: 'Sketch a schema for a new feature before you build it.',
    prompt: "I need to design a database schema for a new feature. Here's what it needs to store:\n\n",
    icon: 'database',
    iconColor: 'text-indigo-400',
  },
  {
    title: 'Performance Investigation',
    description: 'Dig into why something is slower than it should be.',
    prompt: 'This part of my app is slower than expected. Help me figure out where the bottleneck is:\n\n',
    icon: 'speed',
    iconColor: 'text-yellow-400',
  },
  {
    title: 'Testing Strategy',
    description: 'Plan meaningful test coverage for a piece of code.',
    prompt: 'Help me think through a solid testing strategy for this code, including edge cases:\n\n',
    icon: 'fact_check',
    iconColor: 'text-teal-400',
  },
  {
    title: 'Debug a Dependency Issue',
    description: 'Work through a confusing package/version conflict.',
    prompt: "I'm running into a dependency issue and I'm not sure what's causing it. Here are the details:\n\n",
    icon: 'extension',
    iconColor: 'text-orange-400',
  },
]

// Non-mutating, deterministic sampling of 2 distinct starters keyed to conversation ID
export function selectRandomStarters(pool, conversationId) {
  if (!Array.isArray(pool) || pool.length < 2) return pool || []

  const copy = [...pool]
  let seed = 0
  if (conversationId && typeof conversationId === 'string') {
    for (let i = 0; i < conversationId.length; i++) {
      seed = ((seed << 5) - seed + conversationId.charCodeAt(i)) | 0
    }
  } else {
    seed = 12345
  }

  const prng = () => {
    seed = (seed * 9301 + 49297) % 233280
    return Math.abs(seed) / 233280
  }

  const idx1 = Math.floor(prng() * copy.length)
  let idx2 = Math.floor(prng() * (copy.length - 1))
  if (idx2 >= idx1) idx2++

  return [copy[idx1], copy[idx2]]
}

export default function ChatInterface({
  messages,
  isLoading,
  isHistoryLoading,
  error,
  onSendMessage,
  activeConversationId,
}) {
  const bottomRef = useRef(null)
  const [prefillPrompt, setPrefillPrompt] = useState('')

  // Stable pair of conversation starters per conversation session
  const starters = useMemo(
    () => selectRandomStarters(CONVERSATION_STARTERS, activeConversationId),
    [activeConversationId]
  )

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading, isHistoryLoading])

  const handleStreamTick = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  const errorText = typeof error === 'string' ? error : error?.message
  const isProviderBusy = typeof error === 'object' && Boolean(error?.isProviderBusy)

  const handleStarterClick = (prompt) => {
    setPrefillPrompt(prompt)
  }

  const safeMessages = Array.isArray(messages) ? messages.filter(Boolean) : []
  const lastIndex = safeMessages.length - 1

  return (
    <div className="flex h-full flex-col bg-[#141313] text-[#ededed]">
      {/* Scoped Provider-Busy / Error Banner */}
      {errorText && (
        <div
          className={`flex items-center justify-between border-b px-4 py-2.5 text-xs transition-colors ${
            isProviderBusy
              ? 'border-amber-500/30 bg-amber-500/10 text-amber-300'
              : 'border-red-500/30 bg-red-500/10 text-red-300'
          }`}
        >
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[16px]">
              {isProviderBusy ? 'warning' : 'error'}
            </span>
            <span className="font-medium">{errorText}</span>
          </div>
        </div>
      )}

      {/* Messages Thread Area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {isHistoryLoading ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-xs text-[#71717a]">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
            <span className="font-mono">Loading conversation history...</span>
          </div>
        ) : safeMessages.length === 0 ? (
          <div className="relative flex h-full flex-col items-center justify-center p-6 text-center">
            {/* Subtle Tech Grid */}
            <div className="absolute inset-0 bg-tech-grid pointer-events-none opacity-40" />

            <div className="relative z-10 flex max-w-lg flex-col items-center space-y-6">
              {/* Terminal Box Emblem */}
              <div className="flex h-14 w-14 items-center justify-center rounded border border-[#27272a] bg-[#1c1b1b] shadow-md">
                <span className="material-symbols-outlined text-[28px] text-white">terminal</span>
              </div>

              {/* Headline */}
              <div className="space-y-1.5">
                <h2 className="text-xl font-semibold tracking-tight text-white">
                  Ready
                </h2>
                <p className="text-xs text-[#a1a1aa] leading-relaxed max-w-sm">
                  Select a starter prompt below to prefill your query or type your own instructions into the composer.
                </p>
              </div>

              {/* Randomized General-Purpose Developer Conversation Starters */}
              <div className="grid w-full grid-cols-1 gap-3 sm:grid-cols-2 text-left pt-2">
                {starters.map((starter, sIdx) => (
                  <button
                    key={sIdx}
                    type="button"
                    onClick={() => handleStarterClick(starter.prompt)}
                    className="flex flex-col rounded border border-[#27272a] bg-[#16161a] p-3 transition-all hover:border-[#3f3f46] hover:bg-[#201f1f] group cursor-pointer text-left focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                  >
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-white mb-1">
                      <span className={`material-symbols-outlined text-[16px] ${starter.iconColor || 'text-blue-400'}`}>
                        {starter.icon || 'chat'}
                      </span>
                      <span>{starter.title}</span>
                    </div>
                    <span className="text-[11px] text-[#71717a] group-hover:text-[#a1a1aa] leading-normal">
                      {starter.description}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="mx-auto flex max-w-4xl flex-col gap-4">
            {safeMessages.map((msg, i) => {
              const isLatest = i === lastIndex
              const canAnimate = msg && msg.role === 'assistant' && isLatest && Boolean(msg.isStreaming)

              return (
                <MessageBubble
                  key={msg?.id || `${activeConversationId}-${i}`}
                  id={msg?.id}
                  role={msg?.role || 'assistant'}
                  content={typeof msg?.content === 'string' ? msg.content : (msg?.content ? String(msg.content) : '')}
                  createdAt={msg?.created_at}
                  canAnimate={canAnimate}
                  onStreamTick={handleStreamTick}
                />
              )
            })}

            {/* Independent Assistant Processing Status Component */}
            {isLoading && (
              <div className="flex items-center gap-3 self-start py-2 px-1 text-xs font-mono text-[#a1a1aa] transition-all">
                <div className="relative flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-gradient-to-tr from-cyan-400 via-blue-600 to-indigo-500 shadow-[0_0_12px_rgba(59,130,246,0.65)] ring-1 ring-white/20">
                  <span className="h-2 w-2 rounded-full bg-white/80 animate-ping" />
                </div>
                <span className="text-[11px] font-medium tracking-wider text-[#d4d4d8]">
                  VSS_AGENT_PROCESSING...
                </span>
                <div className="flex items-center gap-1.5 ml-1">
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-blue-400" />
                  <span
                    className="h-1.5 w-1.5 animate-bounce rounded-full bg-blue-400"
                    style={{ animationDelay: '0.15s' }}
                  />
                  <span
                    className="h-1.5 w-1.5 animate-bounce rounded-full bg-blue-400"
                    style={{ animationDelay: '0.3s' }}
                  />
                </div>
              </div>
            )}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Docked Composer */}
      <ChatInput
        key={activeConversationId}
        onSend={(text) => {
          setPrefillPrompt('')
          onSendMessage(text)
        }}
        prefillValue={prefillPrompt}
        disabled={isLoading || isHistoryLoading}
      />
    </div>
  )
}

