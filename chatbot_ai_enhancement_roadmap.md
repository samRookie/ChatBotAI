# ChatbotAI — Master 100-Point Enhancement & Architectural Roadmap

A comprehensive, point-by-point architectural and feature roadmap listing **100 actionable enhancements** to transform **ChatbotAI** into a state-of-the-art, personal AI workspace and Retrieval-Augmented Generation (RAG) platform.

---

## 🏛️ Category A: Vector Search & RAG Retrieval Engine

### 1. Hybrid Search Engine (FTS5 BM25 + Vector KNN)
- **Why:** Vector search excels at semantic concepts, but misses exact serial numbers, function names, or code symbols. BM25 keyword search misses intent. Combining both eliminates blind spots.
- **How it works:** Execute a `sqlite-vec` KNN query and a SQLite `FTS5` BM25 keyword query in parallel. Merge and re-rank results using Reciprocal Rank Fusion (RRF).
- **When to include:** **Stage 2, Step 3** (Retrieval Engine).

### 2. Cosine Distance Threshold Filtering
- **Why:** Prevents irrelevant memory chunks from polluting context when query similarity is low.
- **How it works:** Filter `vec_distance_cosine` query results to only retain chunks where distance < 0.35 (similarity > 0.65).
- **When to include:** **Stage 2, Step 3** (Retrieval Engine).

### 3. Maximal Marginal Relevance (MMR) Re-ranking
- **Why:** Standard Top-K vector retrieval often returns 5 redundant chunks saying the exact same thing.
- **How it works:** Re-rank candidate chunks by balancing query relevance against novelty relative to already selected chunks.
- **When to include:** **Stage 2, Step 3** (Retrieval Engine).

### 4. Time-Decay Recency Weighting
- **Why:** Recent memories are generally more relevant than 6-month-old past chat turns.
- **How it works:** Multiply similarity score by `exp(-lambda * (now - chunk_timestamp))`.
- **When to include:** **Stage 2, Step 3** (Retrieval Engine).

### 5. Dynamic Context Budget Allocator
- **Why:** Prevents exceeding Gemini's token limit or drowning system prompt instructions.
- **How it works:** Calculate remaining context budget (e.g. 8000 tokens) and fill iteratively with top-ranked chunks until limit is reached.
- **When to include:** **Stage 2, Step 4** (RAG Context Orchestration).

### 6. Multi-Query Expansion
- **Why:** User questions can be brief or ambiguously phrased.
- **How it works:** Generate 3 prompt variations of the user query via a fast LLM pass, embed all 3, and retrieve aggregate unique chunks.
- **When to include:** **Stage 2, Step 4** (RAG Context Orchestration).

### 7. Hypothetical Document Embeddings (HyDE)
- **Why:** Matching question vectors directly to answer vectors can fail when query phrasing differs from stored text phrasing.
- **How it works:** Generate a hypothetical answer first, embed that answer vector, and search vector storage with it.
- **When to include:** **Stage 2, Step 4** (RAG Context Orchestration).

### 8. Conversation-Scoped Vector Filtering
- **Why:** Allows users to scope AI memory search to the current active chat session.
- **How it works:** Pass `WHERE conversation_id = ?` into SQLite vector queries before distance sorting.
- **When to include:** **Stage 2, Step 3** (Retrieval Engine).

### 9. Metadata-Filtered Vector Queries
- **Why:** Allows filtering memories by tag, file type, or date range.
- **How it works:** Join `memory_chunks` and `memory_vectors` on `rowid` with SQL `WHERE` clauses applied to metadata columns.
- **When to include:** **Stage 2, Step 3** (Retrieval Engine).

### 10. Parent-Child Chunk Retrieval
- **Why:** Small chunks (200 chars) are better for vector matching, but larger chunks (1000 chars) provide better LLM context.
- **How it works:** Match small child chunks during vector search, but fetch and inject their parent chunk into prompt context.
- **When to include:** **Stage 2, Step 4** (RAG Context Orchestration).

### 11. Auto-Cutoff Similarity Score Gap Detection
- **Why:** Fixed Top-K (e.g. K=5) can retrieve 3 great results and 2 garbage results.
- **How it works:** Sort chunks by similarity; if the drop between chunk N and N+1 exceeds 0.2, stop retrieving further chunks.
- **When to include:** **Stage 2, Step 3** (Retrieval Engine).

### 12. Token Counting Boundary Guard
- **Why:** Prevents HTTP 400 Bad Request errors from LLM providers caused by context overflow.
- **How it works:** Count exact tokens of system prompt, history, and retrieved chunks using `google-genai` SDK token counter before API call.
- **When to include:** **Stage 2, Step 4** (RAG Context Orchestration).

### 13. Cross-Encoder Re-ranker Integration
- **Why:** Vector bi-encoders are fast but less precise than full cross-attention re-ranking.
- **How it works:** Pass top 20 candidate chunks through a local mini cross-encoder to re-score top 5.
- **When to include:** **Stage 2, Step 4** (RAG Context Orchestration).

### 14. Citation Requirement Enforcement in System Prompt
- **Why:** Prevents AI hallucinations by requiring memory rowid references.
- **How it works:** Inject strict prompt instructions: "Base response ONLY on provided memories [Memory #ID]. If unknown, state so."
- **When to include:** **Stage 2, Step 4** (RAG Context Orchestration).

### 15. Query Intent Classifier Router
- **Why:** Casual greetings ("hi", "thanks") don't need expensive DB vector searches.
- **How it works:** Fast intent classifier routes conversational turns straight to LLM, skipping vector DB lookups when unnecessary.
- **When to include:** **Stage 2, Step 4** (RAG Context Orchestration).

---

## 📄 Category B: Chunking, Ingestion & Document Processing

### 16. Markdown Structure-Aware Chunker
- **Why:** Naive character splitting cuts headers and list items in half.
- **How it works:** Parse Markdown headers (`#`, `##`, `###`) and code blocks, grouping complete logical sections into chunks.
- **When to include:** **Stage 2, Step 2** (Embedding Pipeline Enhancement).

### 17. Code-Aware AST Syntax Chunker
- **Why:** Splitting code files mid-function creates ungrammatical, useless snippets.
- **How it works:** Use Python `ast` module or `tree-sitter` to chunk code cleanly by function and class definitions.
- **When to include:** **Stage 3, Step 1** (Document Ingestion).

### 18. PDF Document Ingestion Pipeline
- **Why:** Users want to upload and query local PDF documents.
- **How it works:** Extract text via `pypdf`/`pdfplumber`, chunk by page/section, embed, and store in `memory_chunks`.
- **When to include:** **Stage 3, Step 1** (Document Ingestion).

### 19. Overlapping Sliding Window Chunking
- **Why:** Important facts bridging chunk boundaries can be lost if chunks don't overlap.
- **How it works:** Set chunk size to 512 tokens with a 64-token overlap window.
- **When to include:** **Stage 2, Step 2** (Embedding Pipeline Enhancement).

### 20. CSV / Tabular Data Ingestion
- **Why:** Tabular CSV data looks like gibberish when split by character length.
- **How it works:** Convert each CSV row into key-value text pairs (e.g. `Column Header: Value`) before embedding.
- **When to include:** **Stage 3, Step 1** (Document Ingestion).

### 21. Codebase Zip Archive Uploader
- **Why:** Allows indexing entire software projects in one click.
- **How it works:** Extract `.zip` in temp folder, walk source trees ignoring `.git`/`node_modules`, chunk files, and insert into vector storage.
- **When to include:** **Stage 3, Step 2** (Codebase Intelligence).

### 22. Duplicate Chunk Deduplication (SHA-256 Hashing)
- **Why:** Re-uploading identical files wastes DB space and embedding credits.
- **How it works:** Calculate SHA-256 hash of `chunk_text`; skip insertion if hash already exists in `memory_chunks`.
- **When to include:** **Stage 2, Step 2** (Embedding Pipeline Enhancement).

### 23. Image & Diagram OCR Ingestion
- **Why:** Screenshots and architecture diagrams contain valuable text data.
- **How it works:** Run local OCR (`pytesseract` / `easyocr`) or Gemini Vision API to convert image text into embedding chunks.
- **When to include:** **Stage 3, Step 3** (Multimodal Support).

### 24. Source Lineage Metadata Storage
- **Why:** Users need to know exactly which file and line number a memory came from.
- **How it works:** Store `file_path`, `start_line`, and `end_line` as JSON metadata in `memory_chunks`.
- **When to include:** **Stage 2, Step 2** (Embedding Pipeline Enhancement).

### 25. Automatic Language Detection for Code Snippets
- **Why:** Enhances code syntax highlighting and indexing tags.
- **How it works:** Detect code language from file extension or text heuristic and tag chunk with `lang: python/js/cpp`.
- **When to include:** **Stage 2, Step 2** (Embedding Pipeline Enhancement).

### 26. File MIME Type Validation
- **Why:** Prevents uploading binary executables or corrupted files into the text pipeline.
- **How it works:** Inspect file magic bytes using `python-magic` before ingestion.
- **When to include:** **Stage 3, Step 1** (Document Ingestion).

### 27. Background Batch Ingestion Manager
- **Why:** Uploading 100 files should not freeze the web application.
- **How it works:** Enqueue batch file ingestion in background worker with progress status tracking.
- **When to include:** **Stage 3, Step 2** (Codebase Intelligence).

### 28. Chunk Length Normalizer
- **Why:** Extremely short chunks (2 words) create noisy vector matches.
- **How it works:** Merge adjacent chunks shorter than 50 characters into neighboring chunks.
- **When to include:** **Stage 2, Step 2** (Embedding Pipeline Enhancement).

---

## 🧠 Category C: Memory Distillation, Summarization & Governance

### 29. Automatic Fact Extraction Engine
- **Why:** Raw chat turns contain conversational fluff; explicit facts are more concentrated.
- **How it works:** Run a prompt pass over chat turns: "Extract core facts about user, tech stack, and decisions as short bullet points."
- **When to include:** **Stage 2, Step 5** (Memory Management).

### 30. Memory Decay & Archival Worker
- **Why:** Stale, temporary memories should not clog vector search forever.
- **How it works:** Periodic job marks chunks older than 90 days as archived unless pinned by user.
- **When to include:** **Stage 2, Step 5** (Memory Management).

### 31. User Memory Pinning
- **Why:** Users want specific critical instructions (e.g. "Always use TypeScript") to NEVER expire.
- **How it works:** Add `is_pinned BOOLEAN` column to `memory_chunks`; pinned chunks bypass decay rules.
- **When to include:** **Stage 2, Step 5** (Memory Management).

### 32. Memory Contradiction Reconciliation
- **Why:** User preferences change over time (e.g., from "I use Python 3.9" to "I use Python 3.12").
- **How it works:** When storing new facts, check similarity against existing facts; update or soft-delete obsolete facts.
- **When to include:** **Stage 2, Step 5** (Memory Management).

### 33. Entity-Relation Knowledge Graph Table
- **Why:** Vector search misses multi-hop relational queries ("What DB does Project X use?").
- **How it works:** Extract `(Subject, Relation, Object)` triples into SQLite `entities` table alongside vector DB.
- **When to include:** **Stage 3, Step 4** (Advanced Knowledge Graph).

### 34. Interactive Memory Bank UI Table
- **Why:** Users need full visibility and control over what the AI remembers.
- **How it works:** React table component displaying stored `memory_chunks` with search, filter, edit, and delete buttons.
- **When to include:** **Stage 2, Step 5** (Memory Management).

### 35. 1-Click Memory Wipe by Session
- **Why:** Essential for privacy and clean-state testing.
- **How it works:** API endpoint `DELETE /api/v1/memories?conversation_id=X` executing atomic delete across `memory_chunks` and `memory_vectors`.
- **When to include:** **Stage 2, Step 5** (Memory Management).

### 36. Automatic Session Summarization on Close
- **Why:** Summarizes long chat sessions into 2-paragraph summaries.
- **How it works:** When a session ends or exceeds 20 messages, trigger background summary task and store in `session_summaries`.
- **When to include:** **Stage 2, Step 5** (Memory Management).

### 37. Memory Usage Analytics Dashboard
- **Why:** Helps users monitor stored memories count and DB storage size.
- **How it works:** Endpoint returning count of chunks, vector size in MB, and category breakdown.
- **When to include:** **Stage 2, Step 5** (Memory Management).

### 38. Sensitive PII Scrubbing Before Memory Insertion
- **Why:** Prevents storing credit cards, passwords, or SSNs in vector storage.
- **How it works:** Pass `chunk_text` through regex scrubber for API keys/tokens/emails before embedding.
- **When to include:** **Stage 2, Step 2** (Embedding Pipeline Enhancement).

### 39. Memory Category Tagging
- **Why:** Improves retrieval filtering by domain.
- **How it works:** Categorize memory chunks on insertion into `user_pref`, `code_rule`, or `domain_fact`.
- **When to include:** **Stage 2, Step 2** (Embedding Pipeline Enhancement).

### 40. Exportable Memory Backup (JSON/CSV)
- **Why:** Users should own their AI memory data.
- **How it works:** `GET /api/v1/memories/export` generating a downloadable JSON file of all memories.
- **When to include:** **Stage 2, Step 5** (Memory Management).

---

## 🎨 Category D: Frontend UI, UX & Rendering

### 41. Prism.js Code Syntax Highlighting
- **Why:** Raw text code blocks are hard to read.
- **How it works:** Integrate Prism.js / Highlight.js in React message components with theme styling.
- **When to include:** **Stage 1 Polish / Stage 2 UI**.

### 42. 1-Click Copy Code Button
- **Why:** Saves user time copying code snippets manually.
- **How it works:** Add a top-right copy button on code blocks using `navigator.clipboard.writeText`.
- **When to include:** **Stage 1 Polish**.

### 43. Mermaid.js Dynamic Diagram Rendering
- **Why:** AI can output flowcharts, sequence diagrams, and architecture maps visually.
- **How it works:** Detect ` ```mermaid ` code blocks and render interactive SVG diagrams using `mermaid.js`.
- **When to include:** **Stage 2 UI**.

### 44. KaTeX LaTeX Math Formula Renderer
- **Why:** Math equations and formulas look broken in plaintext.
- **How it works:** Use `remark-math` and `rehype-katex` to render `\(...\)` and `\[...\]` math blocks cleanly.
- **When to include:** **Stage 2 UI**.

### 45. Interactive Rendered HTML/SVG Preview Sandbox
- **Why:** Allows previewing generated HTML/CSS/SVG code directly inside the chat interface.
- **How it works:** Sandboxed `<iframe>` tab alongside code blocks to render live HTML previews safely.
- **When to include:** **Stage 3 UI**.

### 46. Settings Modal for Model & API Key Configuration
- **Why:** Users shouldn't need to edit `.env` files to change settings or API keys.
- **How it works:** React settings modal storing configuration in `localStorage` or sending to backend `POST /api/v1/config`.
- **When to include:** **Stage 2 UI**.

### 47. Dynamic Temperature & Top-P Sliders
- **Why:** Gives users control over creativity vs determinism per chat.
- **How it works:** Add sliders in chat controls and pass `temperature` in request payload to FastAPI.
- **When to include:** **Stage 2 UI**.

### 48. Custom System Prompt / Persona Switcher
- **Why:** Switching between "Coding Assistant", "Writing Editor", and "Database Expert" modes.
- **How it works:** Dropdown selector sending selected system prompt prefix with each payload.
- **When to include:** **Stage 2 UI**.

### 49. Sidebar Conversation Search Input
- **Why:** Finding specific past conversations quickly.
- **How it works:** Real-time filter input in React sidebar filtering conversation titles by keyword.
- **When to include:** **Stage 1 Polish**.

### 50. Chat Session Export (Markdown, PDF, JSON)
- **Why:** Allows sharing or saving chat transcripts locally.
- **How it works:** Download button formatting conversation history into downloadable `.md` or `.pdf` files.
- **When to include:** **Stage 1 Polish**.

### 51. Auto-Scrolling with Smart Scroll Lock
- **Why:** Streaming messages should auto-scroll down, but stop scrolling if user manually scrolls up.
- **How it works:** React `useEffect` tracking scroll position; disable auto-scroll when user scrolls upward.
- **When to include:** **Stage 1 Polish**.

### 52. Responsive Sidebar Collapser for Mobile/Tablet
- **Why:** Ensures clean UI layout across screen sizes.
- **How it works:** Toggle button sliding sidebar in/out on screens smaller than 768px.
- **When to include:** **Stage 1 Polish**.

### 53. Dark / Light / System Color Theme Switcher
- **Why:** Improves visual comfort and accessibility.
- **How it works:** CSS variables / Tailwind dark mode class toggled via React context.
- **When to include:** **Stage 1 Polish**.

### 54. Message Regeneration Button
- **Why:** Retrying an AI response if output wasn't satisfactory.
- **How it works:** Re-send conversation history up to selected message index to FastAPI.
- **When to include:** **Stage 1 Polish**.

### 55. Editable User Messages
- **Why:** Allows fixing typos in a prompt without creating a new session.
- **How it works:** Inline edit button on user message bubbles that truncates history after edit and re-triggers completion.
- **When to include:** **Stage 1 Polish**.

---

## 🔍 Category E: Developer Tools, Inspection & Debugging

### 56. RAG Context Inspector Panel
- **Why:** Full transparency into what retrieved chunks influenced the AI response.
- **How it works:** Drawer component showing retrieved `memory_chunks`, similarity scores, and sources for each assistant message.
- **When to include:** **Stage 2, Step 4** (RAG Orchestration).

### 57. Vector DB Diagnostic Endpoint (`GET /api/v1/db-stats`)
- **Why:** Checking total vector count, DB size, and table row counts.
- **How it works:** Endpoint returning count of `sessions`, `conversations`, `messages`, `memory_chunks`, and `memory_vectors`.
- **When to include:** **Stage 2, Step 1/2**.

### 58. Interactive SQL Query Sandbox (Read-Only Admin)
- **Why:** Rapid debugging of DB state during development.
- **How it works:** Protected backend endpoint allowing read-only `SELECT` queries on local `chatbot.db`.
- **When to include:** **Stage 2 DevTools**.

### 59. Embedding Vector Visualization (2D Projection)
- **Why:** Visualizing how memories cluster in vector space.
- **How it works:** Use UMAP / t-SNE to reduce 768-dim vectors to 2D coordinates and plot on React scatter plot.
- **When to include:** **Stage 3 DevTools**.

### 60. LLM Response Token Counter Badge
- **Why:** Gives users visibility into token consumption per response.
- **How it works:** Display input/output token counts in footer of AI message bubble.
- **When to include:** **Stage 1 Polish**.

### 61. Latency & Execution Time Profiler
- **Why:** Monitoring API latency, vector search time, and total TTFT (Time To First Token).
- **How it works:** Return `X-Response-Time-ms` header and print breakdown in server logs.
- **When to include:** **Stage 2 Infrastructure**.

### 62. Automated Unit & Integration Test Suite
- **Why:** Ensures code quality and prevents regressions.
- **How it works:** `pytest` suite covering DB connection, embedding generation, vector search, and API routes.
- **When to include:** **Stage 2 Ongoing**.

### 63. OpenAPI / Swagger Interactive Documentation Customization
- **Why:** Clean API reference for extensions and integrations.
- **How it works:** Configure FastAPI `title`, `description`, `version`, and custom schema examples.
- **When to include:** **Stage 1 Polish**.

### 64. Structured JSON Logging Handler
- **Why:** Formatted logs for debugging production server runs.
- **How it works:** Configure Python `logging` with JSON formatter printing `timestamp`, `level`, `module`, and `message`.
- **When to include:** **Stage 2 Infrastructure**.

### 65. Mock Gemini Client for Offline Testing
- **Why:** Running full automated test suite without consuming API credits or needing internet.
- **How it works:** Mock class returning deterministic text completions and fake 768-dim float vectors.
- **When to include:** **Stage 2 Testing**.

### 66. Database Schema Version Migration Runner
- **Why:** Safe DB upgrades across future project stages.
- **How it works:** Versioned SQL migration scripts executing idempotent schema migrations on startup.
- **When to include:** **Stage 2 Infrastructure**.

### 67. Frontend State Persistence Health Check
- **Why:** Prevents UI crashes if `localStorage` gets corrupted or outdated.
- **How it works:** Schema validation check on app load that repairs or resets invalid `localStorage` state.
- **When to include:** **Stage 1 Polish**.

---

## ⚡ Category F: Backend Performance, Async & Infrastructure

### 68. Async Background Task Memory Pipeline
- **Why:** Prevents blocking chat completion while waiting for embedding generation and DB inserts.
- **How it works:** Offload `write_memory` call to `FastAPI BackgroundTasks` or `asyncio.create_task`.
- **When to include:** **Stage 2, Step 2/3**.

### 69. SQLite Write-Ahead Logging (WAL Mode)
- **Why:** Allows concurrent database reads while writes are occurring without database locking errors.
- **How it works:** Execute `PRAGMA journal_mode = WAL;` on database initialization.
- **When to include:** **Stage 2 Step 1/2**.

### 70. SQLite Busy Timeout Tuning
- **Why:** Prevents `sqlite3.OperationalError: database is locked` during concurrent operations.
- **How it works:** Execute `PRAGMA busy_timeout = 5000;` on connection creation.
- **When to include:** **Stage 2 Step 1**.

### 71. Connection Pooling via aiosqlite / Manager
- **Why:** Efficient thread-safe connection handling.
- **How it works:** Implement connection pool manager reusing pre-initialized sqlite-vec loaded connections.
- **When to include:** **Stage 2 Infrastructure**.

### 72. HTTP/2 & Gzip Compression Middleware
- **Why:** Reduces network payload size for large chat histories and responses.
- **How it works:** Add `GZipMiddleware` to FastAPI application instance.
- **When to include:** **Stage 1 Polish**.

### 73. In-Memory Embedding Cache (LRU Cache)
- **Why:** Avoids re-embedding identical text strings multiple times.
- **How it works:** Wrap `generate_embedding` with `functools.lru_cache(maxsize=1000)` or Redis/disk cache.
- **When to include:** **Stage 2, Step 2**.

### 74. Streaming Server-Sent Events (SSE) Response Handler
- **Why:** Provides word-by-word real-time typing effect.
- **How it works:** Use `EventSourceResponse` in FastAPI to stream tokens from Gemini stream generator to React.
- **When to include:** **Stage 1 Refinement**.

### 75. Graceful Shutdown & Connection Cleanup
- **Why:** Prevents database corruption when terminating server process.
- **How it works:** FastAPI lifespan handler closing database connection pools and flushing logs on SIGTERM.
- **When to include:** **Stage 2 Infrastructure**.

### 76. Environment Variable Validation (Pydantic Settings)
- **Why:** Fails fast on startup if configuration or API keys are invalid.
- **How it works:** Pydantic `BaseSettings` validating `.env` parameters on app launch.
- **When to include:** **Stage 1 Polish**.

### 77. Rate Limit Throttling Middleware (SlowAPI)
- **Why:** Protects server from accidental client loops or API key exhaustion.
- **How it works:** Limit requests to 30 requests per minute per IP address.
- **When to include:** **Stage 2 Infrastructure**.

### 78. Single-Click One-File Executable Packaging (PyInstaller)
- **Why:** Easy deployment for non-technical users without requiring Python/Node installation.
- **How it works:** Bundle FastAPI backend and compiled React static dist into standalone `.exe`.
- **When to include:** **Stage 3 Packaging**.

### 79. Health Check Endpoint (`GET /health`) Enhancement
- **Why:** Automated container/system monitoring.
- **How it works:** Endpoint verifying DB connectivity, disk space, and Gemini API readiness returning 200 OK.
- **When to include:** **Stage 1 Polish**.

---

## 🔒 Category G: Security, Privacy, Auth & Data Control

### 80. Local Secret & Credential Redaction Scrubber
- **Why:** Prevents leaking API keys, DB passwords, or tokens in logs or AI completions.
- **How it works:** Regex filter checking input text for key patterns (`AIza...`, `bearer ...`, `sk-...`) and replacing with `[REDACTED]`.
- **When to include:** **Stage 2 Infrastructure**.

### 81. CORS Origin Strict Whitelisting
- **Why:** Prevents unauthorized websites from calling local FastAPI backend.
- **How it works:** Configure `CORSMiddleware` with exact origins (`http://localhost:5173`) instead of wildcard `*`.
- **When to include:** **Stage 1 Polish**.

### 82. SQL Injection Prevention Enforcement
- **Why:** Eliminates vulnerability to database injection attacks.
- **How it works:** Enforce parameterized queries (`?` placeholders) across 100% of database calls.
- **When to include:** **Stage 1/2 Audited**.

### 83. API Key Local Storage Encryption
- **Why:** Prevents unauthorized local processes from reading stored API keys.
- **How it works:** Encrypt API keys stored in browser/file using AES-GCM before saving to disk.
- **When to include:** **Stage 2 Security**.

### 84. Optional Master Passcode Lock for UI
- **Why:** Privacy on shared computer screens.
- **How it works:** PIN/Passcode modal locking application UI after 15 minutes of inactivity.
- **When to include:** **Stage 3 Security**.

### 85. SQLCipher Database Encryption at Rest
- **Why:** Protects local `chatbot.db` file from physical theft or malware reading.
- **How it works:** Replace standard `sqlite3` driver with `pysqlcipher3` using passphrase decryption.
- **When to include:** **Stage 3 Security**.

### 86. Content Security Policy (CSP) Headers
- **Why:** Prevents Cross-Site Scripting (XSS) in frontend Markdown rendering.
- **How it works:** Set strict CSP headers in FastAPI/Vite allowing script execution only from local origin.
- **When to include:** **Stage 1 Polish**.

### 87. Input Sanitization (DOMPurify)
- **Why:** Prevents malicious script execution when rendering HTML/Markdown output.
- **How it works:** Sanitize all AI-generated HTML output with `DOMPurify` before injecting into DOM.
- **When to include:** **Stage 1 Polish**.

### 88. 1-Click Total Data Erasure (Factory Reset)
- **Why:** Compliance with data privacy and instant clean wipe.
- **How it works:** UI button executing total file deletion of `chatbot.db` and clearing `localStorage`.
- **When to include:** **Stage 2 Governance**.

### 89. Audit Trail Logging for Memory Modifications
- **Why:** Tracking when memories were created, edited, or deleted.
- **How it works:** Write audit event records to `audit_logs` table on memory mutations.
- **When to include:** **Stage 2 Governance**.

### 90. Non-Root Docker Container Packaging
- **Why:** Secure containerized execution for server deployment.
- **How it works:** `Dockerfile` running application under non-privileged user `appuser`.
- **When to include:** **Stage 3 Packaging**.

---

## 🤖 Category H: Advanced LLM Routing, Offline Models & Agentic Extensions

### 91. Ollama / Llama.cpp Local LLM Provider Integration
- **Why:** 100% offline capability with zero external API dependencies.
- **How it works:** Add local provider interface in `llm_router.py` pointing to `http://localhost:11434/api/generate`.
- **When to include:** **Stage 3 Provider Expansion**.

### 92. Automatic LLM Provider Fallback Router
- **Why:** Ensures high availability if primary API key or provider is rate-limited.
- **How it works:** If Gemini API returns 503/429 repeatedly, fallback to alternative API provider or local model.
- **When to include:** **Stage 3 Reliability**.

### 93. Web Search Tool Integration (Tavily / DuckDuckGo)
- **Why:** Answers questions requiring up-to-the-minute real-time web info.
- **How it works:** Detect web search intent, execute DuckDuckGo search query, and feed top web snippets into prompt.
- **When to include:** **Stage 3 Agents**.

### 94. Python Code Interpreter Sandbox (Local Execution)
- **Why:** Enables AI to execute math calculations, data analysis, and script output directly.
- **How it works:** Execute generated Python code inside isolated subprocess or Docker container and capture stdout.
- **When to include:** **Stage 3 Agents**.

### 95. Multi-Agent Orchestration (Planner + Execution Agent)
- **Why:** Solves complex multi-step tasks (e.g. "Research X, write code, run test").
- **How it works:** Planner agent breaks prompt into sub-tasks; Worker agents execute sub-tasks sequentially.
- **When to include:** **Stage 3 Agents**.

### 96. Structured Output Parser (Pydantic / JSON Mode)
- **Why:** Guarantees LLM outputs valid JSON schemas for downstream application consumption.
- **How it works:** Pass Pydantic schema into Gemini `response_schema` parameter.
- **When to include:** **Stage 2 Integration**.

### 97. Contextual Compression & Summarizer
- **Why:** Compresses long retrieved documents to save tokens before prompt construction.
- **How it works:** Extract only relevant sentences from retrieved chunks before sending to LLM.
- **When to include:** **Stage 2, Step 4** (RAG Orchestration).

### 98. Custom Prompt Template Manager
- **Why:** Saves and reuses frequently used complex prompts (e.g. "Code Reviewer", "Refactoring Helper").
- **How it works:** UI library storing prompt templates in SQLite database.
- **When to include:** **Stage 2 UI**.

### 99. Streaming Token Throughput Speedometer
- **Why:** Visual indication of tokens per second (tokens/sec) streaming performance.
- **How it works:** Calculate tokens received per second and display live speed counter in UI.
- **When to include:** **Stage 1 Polish**.

### 100. Standalone Tauri / Electron Desktop App Wrapper
- **Why:** Converts web application into a native desktop app with system tray icon.
- **How it works:** Wrap React frontend and FastAPI backend inside Tauri (Rust) desktop framework.
- **When to include:** **Stage 3 Desktop**.

---
*Updated Master 100-Point Roadmap for **ChatbotAI**.*
