import React from 'react'

function formatTimestamp(isoString) {
  if (!isoString) return ''
  try {
    const date = new Date(isoString)
    const now = new Date()
    const isToday =
      date.getDate() === now.getDate() &&
      date.getMonth() === now.getMonth() &&
      date.getFullYear() === now.getFullYear()

    if (isToday) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
  } catch {
    return ''
  }
}

export default function Sidebar({
  conversationList,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  isOpen,
  onClose,
}) {
  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-xs transition-opacity md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar container */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-[#27272a] bg-[#0e0e0e] text-[#ededed] transition-transform duration-200 ease-in-out md:static md:translate-x-0 ${
          isOpen ? 'translate-x-0 shadow-2xl md:shadow-none' : '-translate-x-full'
        }`}
        aria-label="Conversation Sidebar"
      >
        {/* Header */}
        <div className="flex h-14 items-center justify-between border-b border-[#27272a] px-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded bg-white text-[#0e0e0e] shadow-xs">
              <span className="material-symbols-outlined text-[18px]">terminal</span>
            </div>
            <span className="font-semibold tracking-tighter text-white">CHATBOTAI</span>
          </div>

          {/* Mobile close button */}
          <button
            type="button"
            onClick={onClose}
            aria-label="Close sidebar"
            className="rounded p-1.5 text-[#71717a] hover:bg-[#201f1f] hover:text-white transition-colors md:hidden"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        {/* New Chat Button */}
        <div className="p-3">
          <button
            type="button"
            onClick={() => {
              onNewChat()
              if (onClose) onClose()
            }}
            aria-label="Start new chat"
            className="flex w-full items-center justify-center gap-2 rounded border border-[#27272a] bg-[#1c1b1b] py-2 px-3 text-xs font-medium text-white transition-all hover:bg-[#2a2a2a] hover:border-[#3f3f46] focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <span className="material-symbols-outlined text-[16px]">add</span>
            <span>New Chat</span>
          </button>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto px-2 py-1">
          <div className="mb-2 px-2 text-[10px] font-semibold tracking-wider text-[#71717a] uppercase">
            Recent Threads
          </div>

          {(() => {
            const safeList = Array.isArray(conversationList) ? conversationList.filter(Boolean) : []
            if (safeList.length === 0) {
              return (
                <div className="flex h-32 flex-col items-center justify-center px-4 text-center text-xs text-[#71717a]">
                  <span className="material-symbols-outlined mb-2 text-[24px] text-[#3f3f46]">
                    chat_bubble_outline
                  </span>
                  No active threads. Start a new chat!
                </div>
              )
            }

            return (
              <nav className="space-y-1" aria-label="Conversations">
                {safeList.map((conv, idx) => {
                  const convId = conv?.id || `conv-${idx}`
                  const isActive = convId === activeConversationId
                  return (
                    <button
                      key={convId}
                      type="button"
                      onClick={() => {
                        onSelectConversation(convId)
                        if (onClose) onClose()
                      }}
                      aria-current={isActive ? 'true' : undefined}
                      className={`group flex w-full flex-col rounded px-3 py-2 text-left text-xs transition-colors focus:outline-none ${
                        isActive
                          ? 'border-l-2 border-white bg-[#201f1f] font-semibold text-white'
                          : 'border-l-2 border-transparent text-[#a1a1aa] hover:bg-[#16161a] hover:text-[#ededed]'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-1">
                        <span className="truncate">{conv?.title || 'Conversation'}</span>
                      </div>
                      <span className="mt-0.5 text-[10px] text-[#71717a]">
                        {formatTimestamp(conv?.lastActivity || conv?.createdAt)}
                      </span>
                    </button>
                  )
                })}
              </nav>
            )
          })()}
        </div>

        {/* Footer / User Profile & System Status */}
        <div className="border-t border-[#27272a] bg-[#141313] p-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded bg-[#201f1f] border border-[#27272a] text-white">
              <span className="material-symbols-outlined text-[16px]">person</span>
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-xs font-semibold text-[#ededed]">DevUser_01</div>
              <div className="flex items-center gap-1.5 text-[10px] text-[#71717a]">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                <span>sqlite-vec 768d</span>
              </div>
            </div>
            <button
              type="button"
              className="text-[#71717a] hover:text-white transition-colors"
              title="System Configuration"
            >
              <span className="material-symbols-outlined text-[18px]">settings</span>
            </button>
          </div>
        </div>
      </aside>
    </>
  )
}
