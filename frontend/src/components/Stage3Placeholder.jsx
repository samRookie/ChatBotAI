import React from 'react'

export default function Stage3Placeholder() {
  return (
    <div className="flex h-full flex-col overflow-y-auto bg-[#141313] p-6 text-[#ededed]">
      <div className="mx-auto max-w-4xl space-y-6">
        {/* Header banner */}
        <div className="rounded border border-[#27272a] bg-[#16161a] p-5 shadow-md">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">
              <span className="material-symbols-outlined text-[24px]">architecture</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-semibold text-white">
                  System Architecture &amp; Planning Canvas
                </h2>
                <span className="rounded bg-blue-500/20 px-2 py-0.5 text-[10px] font-semibold text-blue-400 border border-blue-500/30">
                  STAGE 3 PREVIEW
                </span>
              </div>
              <p className="text-xs text-[#a1a1aa] mt-0.5">
                Technical pipeline layout, vector memory subsystem, and autonomous execution layer.
              </p>
            </div>
          </div>
        </div>

        {/* Architecture Pipeline Visualizer */}
        <div className="rounded border border-[#27272a] bg-[#121214] p-5 shadow-md">
          <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[#71717a] mb-4">
            RAG Vector Memory &amp; Resilience Pipeline
          </h3>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {/* Step 1 */}
            <div className="flex flex-col rounded border border-[#27272a] bg-[#16161a] p-4">
              <div className="flex items-center gap-2 text-xs font-semibold text-white mb-2">
                <span className="flex h-5 w-5 items-center justify-center rounded bg-[#201f1f] text-[10px]">
                  1
                </span>
                <span>User Input &amp; Retrieval</span>
              </div>
              <p className="text-[11px] text-[#a1a1aa] leading-relaxed">
                Incoming prompt generates 768d vector via <code>gemini-embedding-2</code>.
                Performs cosine KNN search on <code>sqlite-vec</code> virtual table.
              </p>
              <div className="mt-3 text-[10px] text-emerald-400 font-mono">
                ✓ Top-3 chunks injected
              </div>
            </div>

            {/* Step 2 */}
            <div className="flex flex-col rounded border border-[#27272a] bg-[#16161a] p-4">
              <div className="flex items-center gap-2 text-xs font-semibold text-white mb-2">
                <span className="flex h-5 w-5 items-center justify-center rounded bg-[#201f1f] text-[10px]">
                  2
                </span>
                <span>Resilient Generation</span>
              </div>
              <p className="text-[11px] text-[#a1a1aa] leading-relaxed">
                Primary call on <code>gemini-3.5-flash</code> with 5 bounded exponential jitter retries.
                Fails over to <code>gemini-3.6-flash</code> on persistent 503 capacity overload.
              </p>
              <div className="mt-3 text-[10px] text-emerald-400 font-mono">
                ✓ 6 provider calls ceiling
              </div>
            </div>

            {/* Step 3 */}
            <div className="flex flex-col rounded border border-[#27272a] bg-[#16161a] p-4">
              <div className="flex items-center gap-2 text-xs font-semibold text-white mb-2">
                <span className="flex h-5 w-5 items-center justify-center rounded bg-[#201f1f] text-[10px]">
                  3
                </span>
                <span>Async Memory Write</span>
              </div>
              <p className="text-[11px] text-[#a1a1aa] leading-relaxed">
                Chat response returns immediately. Background worker embeds turns and updates SQLite vector index with transactional rollback isolation.
              </p>
              <div className="mt-3 text-[10px] text-emerald-400 font-mono">
                ✓ Zero latency impact
              </div>
            </div>
          </div>
        </div>

        {/* Roadmap Milestones */}
        <div className="rounded border border-[#27272a] bg-[#16161a] p-5 shadow-md space-y-4">
          <h3 className="text-[11px] font-semibold uppercase tracking-wider text-[#71717a]">
            Upcoming Stage 3 Project Layer Capabilities
          </h3>

          <div className="space-y-2.5 font-mono text-xs">
            <div className="flex items-start gap-2.5 rounded border border-[#27272a] bg-[#121214] p-3">
              <span className="material-symbols-outlined text-[16px] text-blue-400 mt-0.5">
                folder_open
              </span>
              <div>
                <strong className="text-white">Multi-File Project Ingestion:</strong>
                <span className="text-[#a1a1aa] block mt-0.5">
                  Attach and index full code repositories, markdown documentation folders, and technical specs into project-scoped vector collections.
                </span>
              </div>
            </div>

            <div className="flex items-start gap-2.5 rounded border border-[#27272a] bg-[#121214] p-3">
              <span className="material-symbols-outlined text-[16px] text-blue-400 mt-0.5">
                account_tree
              </span>
              <div>
                <strong className="text-white">Autonomous Planning Mode:</strong>
                <span className="text-[#a1a1aa] block mt-0.5">
                  Interactive requirement gathering, step-by-step milestone execution, and automated diff artifact generation.
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
