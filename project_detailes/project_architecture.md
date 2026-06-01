# 🧠 Cognitive Operating System: Engineering Roadmap & Architecture Guide

## 📋 Context for AI Coding Agent
You are an expert Senior Software Engineer assisting in building a "Cognitive Operating System" (an AI-native Second Brain). 
**Your primary directives are:**
1. **Strictly adhere to the phased approach.** Do not suggest or write code for Phase 4 features if we are currently in Phase 1.
2. **Maintain Clean Architecture.** Keep business logic strictly separated from frameworks and databases.
3. **Prevent feature creep.** Follow the "DO NOT BUILD" constraints for each phase rigorously.
4. **Write production-ready code.** Use type hinting, docstrings, and modular design.

---

## 🎯 Project Vision
This is **NOT** a standard note-taking app or a simple chatbot wrapper. It is a persistent AI learning companion, memory system, and cognitive assistant. 
* **Core Problem Solved:** Information overload and fragmented knowledge.
* **Goal:** Transform unstructured information into structured understanding over long periods of time.
* **Target Evolution:** Start as a web-based Flask/JS app, eventually evolving into a desktop/mobile platform with autonomous agents.

---

## 🛠️ Tech Stack & Evolution Strategy

| Component | Phase 1-3 (MVP) | Phase 4+ (Scale) |
| :--- | :--- | :--- |
| **Backend** | Python, Flask | Python, FastAPI |
| **Database** | SQLite (with FTS5) | PostgreSQL |
| **Vector DB** | N/A (Use SQLite FTS5) | ChromaDB |
| **AI Provider** | OpenRouter API (OpenAI compatible) | OpenRouter / Local Models |
| **Frontend** | Vanilla HTML/CSS/JS | React / Next.js |
| **Graph Viz** | N/A | D3.js (Force-directed graph) |

---

## 🏛️ System Architecture (Clean Architecture)

The codebase must follow a strict Layered Architecture. The `core` domain logic must never import from `api` or `infrastructure`.

```text
cognitive_os/
├── app/
│   ├── __init__.py             # Flask App Factory
│   ├── api/                    # 🟢 Presentation Layer (HTTP routes, request parsing)
│   ├── core/                   # 🔵 Domain Logic (LLM wrappers, memory logic, data models)
│   └── infrastructure/         # 🟠 Data Access (SQLite connections, SQL queries, file I/O)
├── tests/                      # Unit and integration tests
├── main.py                     # Entry point
├── schema.sql                  # Database schema definition
└── .env                        # Secrets (OPENROUTER_API_KEY)