import React, { useRef, useState, useEffect } from 'react'

export default function ChatInput({
  onSend,
  disabled,
  placeholder = '> Initialize prompt sequence...',
  prefillValue = '',
}) {
  const [value, setValue] = useState('')
  const textareaRef = useRef(null)

  const resizeTextarea = () => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    const newHeight = Math.min(el.scrollHeight, 240)
    el.style.height = `${newHeight}px`
  }

  // Handle external prefill from conversation starters
  useEffect(() => {
    if (prefillValue && typeof prefillValue === 'string') {
      setValue(prefillValue)
      // Auto-resize and focus after setting prefilled prompt
      setTimeout(() => {
        resizeTextarea()
        if (textareaRef.current) {
          textareaRef.current.focus()
        }
      }, 0)
    }
  }, [prefillValue])

  const handleChange = (e) => {
    setValue(e.target.value)
    resizeTextarea()
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleSubmit = () => {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const canSend = value.trim().length > 0 && !disabled

  return (
    <div className="flex-none border-t border-[#27272a] bg-[#0e0e0e] p-3 sm:p-4">
      <div className="mx-auto max-w-4xl">
        <div className="flex flex-col rounded border border-[#27272a] bg-[#16161a] focus-within:border-[#3f3f46] focus-within:ring-1 focus-within:ring-blue-500/30 transition-all shadow-md">
          {/* Text Area */}
          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            rows={1}
            placeholder={placeholder}
            className="min-h-[60px] max-h-60 w-full resize-none bg-transparent p-3.5 font-mono text-xs text-[#ededed] placeholder-[#71717a] focus:outline-none disabled:opacity-50"
          />

          {/* Action / Tooling Bar */}
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[#27272a] bg-[#121214] px-3 py-2 text-[11px] text-[#71717a]">
            {/* Left Badges */}
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1 rounded bg-[#201f1f] border border-[#27272a] px-2 py-0.5 text-[10px] text-[#a1a1aa]">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span>VSS_AGENT_READY</span>
              </span>
              <span className="hidden sm:inline-block text-[10px] text-[#71717a]">
                {value.length} chars
              </span>
            </div>

            {/* Right Controls & Send Button */}
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleSubmit}
                disabled={!canSend}
                className="flex items-center gap-1.5 rounded-lg bg-white px-3.5 py-1.5 text-xs font-semibold text-[#0e0e0e] shadow-xs transition-all hover:bg-[#e2e2e2] disabled:cursor-not-allowed disabled:bg-[#2a2a2a] disabled:text-[#71717a]"
              >
                <span>SEND</span>
                <span className="material-symbols-outlined text-[14px]">send</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
