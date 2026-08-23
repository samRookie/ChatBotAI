import React from 'react'

export default function Header({
  activeConversation,
  currentView,
  onViewChange,
  onOpenSidebar,
  isInspectorOpen,
  onToggleInspector,
}) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-[#27272a] bg-[#141313]/90 px-4 backdrop-blur-md">
      <div className="flex items-center gap-3">
        {/* Mobile sidebar toggle button */}
        <button
          type="button"
          onClick={onOpenSidebar}
          aria-label="Open conversations sidebar"
          className="rounded p-1.5 text-[#71717a] hover:bg-[#201f1f] hover:text-white focus:outline-none md:hidden"
        >
          <span className="material-symbols-outlined text-[20px]">menu</span>
        </button>

        {/* Active conversation title and metadata */}
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <h1 className="max-w-[160px] truncate text-xs font-semibold text-[#ededed] sm:max-w-xs md:max-w-md">
              {activeConversation?.title || 'ChatbotAI Workspace'}
            </h1>
            <span className="hidden rounded border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.2 text-[9px] font-medium text-emerald-400 sm:inline-block">
              RAG Active
            </span>
          </div>
          <span className="text-[10px] text-[#71717a]">v4.2.0-stable</span>
        </div>
      </div>

      {/* View Switcher Tabs (Chat vs Architecture / Planning Canvas) */}
      <div
        role="tablist"
        aria-label="Workspace views"
        className="flex items-center rounded border border-[#27272a] bg-[#0e0e0e] p-0.5 text-xs font-medium text-[#71717a]"
      >
        <button
          type="button"
          role="tab"
          aria-selected={currentView === 'chat'}
          onClick={() => onViewChange('chat')}
          className={`flex items-center gap-1.5 rounded px-3 py-1 transition-all ${
            currentView === 'chat'
              ? 'bg-[#201f1f] font-semibold text-white shadow-xs'
              : 'hover:text-[#ededed]'
          }`}
        >
          <span className="material-symbols-outlined text-[14px]">chat</span>
          <span>Chat</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={currentView === 'project'}
          onClick={() => onViewChange('project')}
          className={`flex items-center gap-1.5 rounded px-3 py-1 transition-all ${
            currentView === 'project'
              ? 'bg-[#201f1f] font-semibold text-white shadow-xs'
              : 'hover:text-[#ededed]'
          }`}
        >
          <span className="material-symbols-outlined text-[14px]">architecture</span>
          <span>Architecture</span>
          <span className="rounded bg-blue-500/20 px-1 text-[8px] font-semibold text-blue-400 border border-blue-500/30">
            Stage 3
          </span>
        </button>
      </div>

      {/* Right Controls & Inspector Toggle */}
      <div className="flex items-center gap-2">
        {/* Model status pill */}
        <div className="hidden items-center gap-1.5 rounded border border-[#27272a] bg-[#16161a] px-2.5 py-1 text-[11px] text-[#a1a1aa] lg:flex">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          <span>Gemini 3.6 Flash</span>
        </div>

        {/* Project Inspector Toggle */}
        <button
          type="button"
          onClick={onToggleInspector}
          aria-label="Toggle Project Inspector"
          title="Toggle Project Inspector"
          className={`flex items-center gap-1 rounded border px-2.5 py-1 text-xs font-medium transition-all ${
            isInspectorOpen
              ? 'border-blue-500/50 bg-blue-500/10 text-blue-400'
              : 'border-[#27272a] bg-[#16161a] text-[#71717a] hover:border-[#3f3f46] hover:text-[#ededed]'
          }`}
        >
          <span className="material-symbols-outlined text-[16px]">dock_to_left</span>
          <span className="hidden sm:inline">Inspector</span>
        </button>
      </div>
    </header>
  )
}
