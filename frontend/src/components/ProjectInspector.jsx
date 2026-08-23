import React, { useState } from 'react'

export default function ProjectInspector({ isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState('config') // 'config' | 'memory' | 'milestones'

  if (!isOpen) return null

  return (
    <aside
      className="fixed inset-y-0 right-0 z-40 flex w-72 sm:w-80 flex-col border-l border-[#27272a] bg-[#0e0e0e] text-[#ededed] shadow-2xl transition-all md:static md:shadow-none"
      aria-label="Project Inspector"
    >
      {/* Inspector Header */}
      <div className="flex h-14 shrink-0 items-center justify-between border-b border-[#27272a] px-4">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px] text-blue-400">
            tune
          </span>
          <span className="font-semibold tracking-wider text-[11px] uppercase text-white">
            Project Inspector
          </span>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close inspector"
          className="rounded p-1 text-[#71717a] hover:bg-[#201f1f] hover:text-white transition-colors"
        >
          <span className="material-symbols-outlined text-[18px]">close</span>
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#27272a] bg-[#141313] p-1 text-xs">
        <button
          type="button"
          onClick={() => setActiveTab('config')}
          className={`flex-1 rounded py-1.5 text-[11px] font-semibold transition-colors ${
            activeTab === 'config'
              ? 'bg-[#201f1f] text-white shadow-xs'
              : 'text-[#71717a] hover:text-[#ededed]'
          }`}
        >
          Engine
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('memory')}
          className={`flex-1 rounded py-1.5 text-[11px] font-semibold transition-colors ${
            activeTab === 'memory'
              ? 'bg-[#201f1f] text-white shadow-xs'
              : 'text-[#71717a] hover:text-[#ededed]'
          }`}
        >
          Memory
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('milestones')}
          className={`flex-1 rounded py-1.5 text-[11px] font-semibold transition-colors ${
            activeTab === 'milestones'
              ? 'bg-[#201f1f] text-white shadow-xs'
              : 'text-[#71717a] hover:text-[#ededed]'
          }`}
        >
          Roadmap
        </button>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5 text-xs font-mono">
        {activeTab === 'config' && (
          <>
            <section className="space-y-2">
              <h3 className="text-[10px] font-semibold uppercase tracking-wider text-[#71717a]">
                Model Pipeline
              </h3>
              <div className="space-y-2 rounded border border-[#27272a] bg-[#16161a] p-3">
                <div className="flex justify-between items-center">
                  <span className="text-[#a1a1aa]">Primary Model</span>
                  <span className="font-semibold text-white">gemini-3.5-flash</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[#a1a1aa]">Fallback Model</span>
                  <span className="font-semibold text-blue-400">gemini-3.6-flash</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[#a1a1aa]">Embedding Model</span>
                  <span className="font-semibold text-[#ededed]">gemini-embedding-2</span>
                </div>
              </div>
            </section>

            <section className="space-y-2">
              <h3 className="text-[10px] font-semibold uppercase tracking-wider text-[#71717a]">
                Resilience &amp; Limits
              </h3>
              <div className="space-y-2 rounded border border-[#27272a] bg-[#16161a] p-3 text-[11px]">
                <div className="flex justify-between items-center">
                  <span className="text-[#a1a1aa]">Primary Retries</span>
                  <span className="text-white">5 Attempts Max</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[#a1a1aa]">Failover Attempt</span>
                  <span className="text-white">1 Attempt Max</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[#a1a1aa]">Jittered Backoff</span>
                  <span className="text-emerald-400">2.0s - 10.0s</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[#a1a1aa]">HTTP Error Code</span>
                  <span className="text-amber-400">AI_PROVIDER_BUSY</span>
                </div>
              </div>
            </section>
          </>
        )}

        {activeTab === 'memory' && (
          <>
            <section className="space-y-2">
              <h3 className="text-[10px] font-semibold uppercase tracking-wider text-[#71717a]">
                Vector DB Engine
              </h3>
              <div className="space-y-2 rounded border border-[#27272a] bg-[#16161a] p-3">
                <div className="flex justify-between items-center">
                  <span className="text-[#a1a1aa]">Extension</span>
                  <span className="font-semibold text-emerald-400">sqlite-vec</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[#a1a1aa]">Vector Dimensions</span>
                  <span className="text-white">768-dim float</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[#a1a1aa]">Distance Metric</span>
                  <span className="text-white">Cosine Distance</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[#a1a1aa]">Top-K Retrieval</span>
                  <span className="text-white">K = 3 chunks</span>
                </div>
              </div>
            </section>

            <section className="space-y-2">
              <h3 className="text-[10px] font-semibold uppercase tracking-wider text-[#71717a]">
                Memory Ingestion
              </h3>
              <div className="rounded border border-[#27272a] bg-[#16161a] p-3 text-[11px] text-[#a1a1aa] leading-relaxed">
                Background memory writer asynchronously embeds user queries and assistant responses after completion. Zero latency overhead on the live chat stream.
              </div>
            </section>
          </>
        )}

        {activeTab === 'milestones' && (
          <div className="space-y-3">
            <h3 className="text-[10px] font-semibold uppercase tracking-wider text-[#71717a]">
              Development Milestones
            </h3>

            {/* P0 */}
            <div className="rounded border border-emerald-500/30 bg-[#16161a] p-3 shadow-xs">
              <div className="flex items-center justify-between mb-1.5">
                <span className="rounded bg-emerald-500/20 px-1.5 py-0.2 text-[9px] font-bold text-emerald-400 border border-emerald-500/30">
                  STAGE 1 &amp; 2: DONE
                </span>
                <span className="material-symbols-outlined text-[16px] text-emerald-400">
                  check_circle
                </span>
              </div>
              <h4 className="font-semibold text-white">sqlite-vec &amp; RAG Pipeline</h4>
              <p className="mt-1 text-[11px] text-[#a1a1aa] leading-tight">
                768-dim embeddings, semantic search, background writer, and context injection.
              </p>
            </div>

            {/* P1 */}
            <div className="rounded border border-emerald-500/30 bg-[#16161a] p-3 shadow-xs">
              <div className="flex items-center justify-between mb-1.5">
                <span className="rounded bg-emerald-500/20 px-1.5 py-0.2 text-[9px] font-bold text-emerald-400 border border-emerald-500/30">
                  STAGE 2.5: DONE
                </span>
                <span className="material-symbols-outlined text-[16px] text-emerald-400">
                  check_circle
                </span>
              </div>
              <h4 className="font-semibold text-white">Provider Resilience &amp; UX</h4>
              <p className="mt-1 text-[11px] text-[#a1a1aa] leading-tight">
                Bounded retries, 503 model failover, calm amber notifications, and duplicate rollback.
              </p>
            </div>

            {/* P2 */}
            <div className="rounded border border-blue-500/30 bg-[#16161a] p-3 shadow-xs">
              <div className="flex items-center justify-between mb-1.5">
                <span className="rounded bg-blue-500/20 px-1.5 py-0.2 text-[9px] font-bold text-blue-400 border border-blue-500/30">
                  STAGE 3: NEXT
                </span>
                <span className="material-symbols-outlined text-[16px] text-blue-400">
                  pending
                </span>
              </div>
              <h4 className="font-semibold text-white">Project Layer &amp; Planning</h4>
              <p className="mt-1 text-[11px] text-[#a1a1aa] leading-tight">
                Multi-document file attachments, workspace canvas, and autonomous task execution.
              </p>
            </div>
          </div>
        )}
      </div>
    </aside>
  )
}
