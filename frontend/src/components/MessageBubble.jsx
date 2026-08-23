import React, { useEffect, useState, useRef } from 'react'

function formatMessageTime(dateString) {
  if (!dateString) return ''
  try {
    const d = new Date(dateString)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

// 3D Glowing Gradient Shiny Orb Emblem for Assistant
function GlowingOrb() {
  return (
    <div className="relative flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-gradient-to-tr from-cyan-400 via-blue-600 to-indigo-500 shadow-[0_0_12px_rgba(59,130,246,0.65)] ring-1 ring-white/20">
      {/* Glossy specular highlight layer */}
      <div className="absolute top-0.5 left-1 h-1.5 w-1.5 rounded-full bg-white/70 blur-[0.3px]" />
      <div className="h-2 w-2 rounded-full bg-white/30 backdrop-blur-xs" />
    </div>
  )
}

function CodeBlock({ language, code }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="my-3 overflow-hidden rounded-xl border border-[#27272a] bg-[#1a1a1e] text-xs shadow-sm">
      <div className="flex items-center justify-between border-b border-[#27272a] bg-[#111113] px-3.5 py-1.5 font-mono text-[11px] text-[#8e9192]">
        <span className="font-semibold uppercase tracking-wider text-[#a1a1aa]">
          {language || 'code'}
        </span>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 text-[#8e9192] hover:text-white transition-colors"
        >
          <span className="material-symbols-outlined text-[13px]">
            {copied ? 'check' : 'content_copy'}
          </span>
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>
      <pre className="overflow-x-auto p-3.5 font-mono leading-relaxed text-[#ededed]">
        <code>{code}</code>
      </pre>
    </div>
  )
}

// Parses inline markdown: **bold**, *italic*, `code`
function renderInlineMarkdown(text) {
  if (!text) return null

  const tokens = []
  const regex = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|_[^_]+_)/g
  let lastIndex = 0
  let match

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      tokens.push({ type: 'text', content: text.slice(lastIndex, match.index) })
    }
    const raw = match[0]
    if (raw.startsWith('`') && raw.endsWith('`')) {
      tokens.push({ type: 'code', content: raw.slice(1, -1) })
    } else if (raw.startsWith('**') && raw.endsWith('**')) {
      tokens.push({ type: 'bold', content: raw.slice(2, -2) })
    } else if (
      (raw.startsWith('*') && raw.endsWith('*')) ||
      (raw.startsWith('_') && raw.endsWith('_'))
    ) {
      tokens.push({ type: 'italic', content: raw.slice(1, -1) })
    }
    lastIndex = match.index + raw.length
  }

  if (lastIndex < text.length) {
    tokens.push({ type: 'text', content: text.slice(lastIndex) })
  }

  return tokens.map((token, i) => {
    switch (token.type) {
      case 'bold':
        return (
          <strong key={i} className="font-semibold text-white">
            {token.content}
          </strong>
        )
      case 'italic':
        return (
          <em key={i} className="italic text-[#d4d4d8]">
            {token.content}
          </em>
        )
      case 'code':
        return (
          <code
            key={i}
            className="rounded border border-[#27272a] bg-[#1c1b1b] px-1.5 py-0.5 text-[11px] font-mono text-cyan-300"
          >
            {token.content}
          </code>
        )
      default:
        return <span key={i}>{token.content}</span>
    }
  })
}

function FormattedContent({ text, isTypingActive }) {
  if (!text) {
    return isTypingActive ? (
      <span className="inline-block animate-pulse font-mono text-cyan-400">▌</span>
    ) : null
  }

  // Split by markdown code fences
  const parts = text.split(/(```[\s\S]*?```)/g)

  return (
    <div className="space-y-2.5 font-mono text-xs leading-relaxed text-[#ededed]">
      {parts.map((part, index) => {
        if (part.startsWith('```') && part.endsWith('```')) {
          const lines = part.slice(3, -3).trim().split('\n')
          const firstLine = lines[0].trim()
          const hasLang = /^[a-zA-Z0-9_-]+$/.test(firstLine)
          const language = hasLang ? firstLine : ''
          const code = hasLang ? lines.slice(1).join('\n') : lines.join('\n')
          return <CodeBlock key={index} language={language} code={code} />
        }

        const lines = part.split('\n')
        const isLastPart = index === parts.length - 1

        return (
          <div key={index} className="space-y-1.5">
            {lines.map((line, lineIdx) => {
              const trimmed = line.trim()

              // Bullet point list item: "* item" or "- item"
              if (/^[-*]\s+/.test(trimmed)) {
                const content = trimmed.replace(/^[-*]\s+/, '')
                return (
                  <div key={lineIdx} className="flex items-start gap-2.5 my-1 pl-1">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-cyan-400 shadow-[0_0_6px_rgba(34,211,238,0.6)]" />
                    <div className="flex-1 leading-relaxed text-[#ededed]">
                      {renderInlineMarkdown(content)}
                    </div>
                  </div>
                )
              }

              // Numbered list item: "1. item"
              const numMatch = trimmed.match(/^(\d+)\.\s+(.*)/)
              if (numMatch) {
                return (
                  <div key={lineIdx} className="flex items-start gap-2 my-1 pl-1">
                    <span className="font-mono text-[11px] font-bold text-cyan-400 shrink-0">
                      {numMatch[1]}.
                    </span>
                    <div className="flex-1 leading-relaxed text-[#ededed]">
                      {renderInlineMarkdown(numMatch[2])}
                    </div>
                  </div>
                )
              }

              // Headings
              if (trimmed.startsWith('### ')) {
                return (
                  <h3 key={lineIdx} className="text-xs font-bold text-white pt-1.5 pb-0.5 tracking-wide">
                    {renderInlineMarkdown(trimmed.slice(4))}
                  </h3>
                )
              }
              if (trimmed.startsWith('## ')) {
                return (
                  <h2 key={lineIdx} className="text-sm font-bold text-white pt-2 pb-0.5 tracking-wide">
                    {renderInlineMarkdown(trimmed.slice(3))}
                  </h2>
                )
              }
              if (trimmed.startsWith('# ')) {
                return (
                  <h1 key={lineIdx} className="text-sm font-extrabold text-white pt-2 pb-1 tracking-wider border-b border-[#27272a]/60">
                    {renderInlineMarkdown(trimmed.slice(2))}
                  </h1>
                )
              }

              // Empty line spacer
              if (!trimmed) {
                return <div key={lineIdx} className="h-1" />
              }

              // Regular paragraph
              return (
                <p key={lineIdx} className="leading-relaxed whitespace-pre-wrap">
                  {renderInlineMarkdown(line)}
                </p>
              )
            })}
            {isTypingActive && isLastPart && (
              <span className="inline-block animate-pulse font-mono text-cyan-400 ml-1 text-xs">▌</span>
            )}
          </div>
        )
      })}
    </div>
  )
}

function MessageBubble({
  id,
  role,
  content,
  createdAt,
  canAnimate = false,
  onStreamTick,
  onStreamComplete,
}) {
  const isUser = role === 'user'
  const [copiedAll, setCopiedAll] = useState(false)

  // Durable per-message completion latch: if mounted as ineligible, latch immediately as completed
  const completedRef = useRef(!canAnimate)

  const [displayedLength, setDisplayedLength] = useState(() =>
    canAnimate && !completedRef.current ? 0 : content?.length || 0
  )
  const [isTyping, setIsTyping] = useState(() => Boolean(canAnimate && !completedRef.current))

  const onStreamTickRef = useRef(onStreamTick)
  onStreamTickRef.current = onStreamTick
  const onStreamCompleteRef = useRef(onStreamComplete)
  onStreamCompleteRef.current = onStreamComplete

  useEffect(() => {
    // Lifecycle Gate: Ineligible or already-completed messages never start a timer
    if (!canAnimate || completedRef.current || !content) {
      setDisplayedLength(content?.length || 0)
      setIsTyping(false)
      return
    }

    setIsTyping(true)
    let currentIdx = displayedLength
    const totalLength = content.length

    // Responsive typing cadence: chunks of 2-5 chars every 14ms
    const interval = setInterval(() => {
      currentIdx = Math.min(currentIdx + Math.floor(Math.random() * 3) + 2, totalLength)
      setDisplayedLength(currentIdx)
      if (onStreamTickRef.current) {
        onStreamTickRef.current()
      }

      if (currentIdx >= totalLength) {
        clearInterval(interval)
        setIsTyping(false)
        completedRef.current = true
        if (onStreamCompleteRef.current) {
          onStreamCompleteRef.current(id)
        }
      }
    }, 14)

    return () => {
      clearInterval(interval)
    }
  }, [canAnimate, content, id])

  const displayedContent = isTyping ? content.slice(0, displayedLength) : content

  const handleCopyMessage = () => {
    navigator.clipboard.writeText(content)
    setCopiedAll(true)
    setTimeout(() => setCopiedAll(false), 2000)
  }

  return (
    <div
      className={`group flex flex-col gap-1.5 py-1 transition-all ${
        isUser
          ? 'self-end ml-auto items-end max-w-[85%] sm:max-w-[72%] md:max-w-[70%]'
          : 'self-start mr-auto items-start max-w-[85%] sm:max-w-[72%] md:max-w-[70%]'
      }`}
    >
      {/* Message Header */}
      <div
        className={`flex items-center gap-2 text-xs ${
          isUser ? 'flex-row-reverse' : 'flex-row'
        }`}
      >
        {isUser ? (
          <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#2a2a2a] border border-[#3f3f46] text-[10px] font-bold text-white shadow-xs">
            U
          </div>
        ) : (
          <GlowingOrb />
        )}

        <span className="font-semibold uppercase tracking-wider text-[11px] text-[#ededed]">
          {isUser ? 'User' : 'Assistant'}
        </span>

        {createdAt && (
          <span className="text-[10px] text-[#71717a]">
            {formatMessageTime(createdAt)}
          </span>
        )}

        <button
          type="button"
          onClick={handleCopyMessage}
          title="Copy message"
          className="opacity-0 group-hover:opacity-100 transition-opacity text-[#71717a] hover:text-white"
        >
          <span className="material-symbols-outlined text-[13px]">
            {copiedAll ? 'check' : 'content_copy'}
          </span>
        </button>
      </div>

      {/* Message Body with curved corners and natural fit */}
      <div
        className={`w-fit max-w-full rounded-2xl px-4 py-3 transition-colors shadow-xs ${
          isUser
            ? 'rounded-tr-xs border border-[#27272a] bg-[#1c1b1b] text-[#ededed]'
            : 'rounded-tl-xs border border-[#27272a]/70 bg-[#141416] text-[#ededed]'
        }`}
      >
        <FormattedContent text={displayedContent} isTypingActive={isTyping} />
      </div>
    </div>
  )
}

export default React.memo(MessageBubble)
