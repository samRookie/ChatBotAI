# 🤖 ChatBotAI — Intelligent Assistant with Long-Term Semantic Memory

> A full-stack, context-aware AI chatbot featuring real-time conversational intelligence, persistent vector memory powered by `sqlite-vec`, and robust upstream provider resilience.

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React_18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Styling-Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![SQLite](https://img.shields.io/badge/Vector_DB-sqlite--vec-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://github.com/asg017/sqlite-vec)
[![Google Gemini](https://img.shields.io/badge/LLM-Google_Gemini-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)

---

## 🌟 What is ChatBotAI?

Most AI chatbots forget who you are the moment you switch conversations or exceed standard context windows. **ChatBotAI** solves this by pairing conversational chat with **persistent, long-term semantic memory**.

When you chat with ChatBotAI:
1. **It listens & learns**: Past exchanges, preferences, and facts are automatically chunked and vectorized in the background.
2. **It remembers**: When you ask new questions, relevant facts from past conversations are semantically retrieved (via K-Nearest Neighbors vector search) and seamlessly referenced.
3. **It stays reliable**: Automated retries and failover algorithms keep the application running smoothly even during upstream AI provider rate limits or capacity spikes.

---

## ✨ Key Features

- **💬 Natural Multi-Turn Conversations**: Fast, context-rich chatting with structured message histories and clean markdown rendering.
- **🧠 Semantic Long-Term Memory (RAG)**: Automatically vectorizes dialogue into 768-dimensional embeddings using Google's text-embedding models.
- **⚡ Local Vector Database**: Powered by `sqlite-vec` directly in SQLite—no external vector database or heavy infrastructure required.
- **🏷️ Automated Topic Generation**: Intelligently creates concise 2–5 word conversation titles in the background.
- **🛡️ High-Resilience AI Routing**: Built-in exponential backoff jitter and automatic fallback failover if primary AI models experience temporary capacity limits.
- **🔒 Prompt-Injection Defenses**: Semantic memories are framed strictly as passive reference data, preventing untrusted past text from overriding safety guidelines.
- **🎨 Sleek, Responsive Interface**: Modern UI with a collapsible sidebar, conversation history search, code syntax highlighting, copy-to-clipboard, and error boundaries.

---

## 🏗️ Architecture Overview

```
                          ┌────────────────────────┐
                          │   React Web Frontend   │
                          │ (Vite + Tailwind CSS)  │
                          └───────────┬────────────┘
                                      │ REST API
                                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                             FastAPI Backend                              │
│                                                                          │
│  ┌───────────────────────┐  ┌────────────────────┐  ┌─────────────────┐  │
│  │      Chat Router      │  │   Memory Reader    │  │  Memory Writer  │  │
│  │   (/api/v1/chat/)     │  │ (KNN Vector Search)│  │ (Async Embedder)│  │
│  └───────────┬───────────┘  └─────────┬──────────┘  └────────┬────────┘  │
│              │                        ▲                      ▲           │
│              ▼                        │                      │           │
│  ┌───────────────────────┐            │                      │           │
│  │      LLM Router       │────────────┘                      │           │
│  │ (Gemini Flash + Retry)│                                   │           │
│  └───────────┬───────────┘                                   │           │
│              │                                               │           │
└──────────────┼───────────────────────────────────────────────┼───────────┘
               │                                               │
               │ Background Task                               │
               └───────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                           SQLite Local Engine                            │
│                                                                          │
│  [Relational Tables]                    [Vector Tables (sqlite-vec)]     │
│  • sessions                             • memory_vectors (768-dim float) │
│  • conversations                        • vec0 KNN similarity index      │
│  • messages                                                              │
│  • memory_chunks <─────────────────────> (1:1 Rowid Alignment)           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | React 18, Vite | High-performance reactive web application |
| **Styling** | Tailwind CSS, Lucide Icons | Responsive modern design system & icons |
| **Backend** | Python 3.10+, FastAPI, Uvicorn | Asynchronous REST API service |
| **AI Models** | Google Gemini 2.5 Flash / 2.0 Flash | Conversational reasoning & topic generation |
| **Embeddings** | Google Gemini Embedding Models | 768-dimensional float32 vector generation |
| **Database** | SQLite + `sqlite-vec` | Relational chat storage & native vector similarity |
| **Resilience** | Tenacity | Bounded exponential backoff with randomized jitter |
| **Validation** | Pydantic v2 | Strict schema validation and settings management |

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.10 or higher**
- **Node.js 18 or higher**
- **Google Gemini API Key** ([Obtain free API key from Google AI Studio](https://aistudio.google.com/))

---


## 🛡️ Security Best Practices

- **Zero Credential Exposure**: `.env` and local `.db` files are strictly excluded from version control via `.gitignore`.
- **Sandboxed Memory Context**: Memories are treated as untrusted historical data and cannot override developer directives or user intent.
- **Sanitized Logging**: Prompts and sensitive user credentials are automatically scrubbed from retry and error logs.

---

## 📄 License

This project is licensed under the **MIT License** — feel free to use and adapt it for your own personal or commercial projects.
