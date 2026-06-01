🗺️ Phased Execution Plan

🏗️ Phase 0: Foundation & Architecture Skeleton
Goal: Establish the environment, folder structure, and basic server.
Set up Python virtual environment and Git repository.
Create the Clean Architecture folder structure (api, core, infrastructure).
Implement the Flask App Factory (app/__init__.py).
Create a basic main.py entry point to run the server.
Set up .env loading for environment variables.
🛑 DO NOT BUILD: Any frontend UI, database connections, or AI logic.
✅ Definition of Done: Running python main.py starts the server successfully, and a dummy /api/health route returns {"status": "ok"}.


📝 Phase 1: Core Data Layer & Basic CRUD (The "Dumb" Notebook)
Goal: Build the foundational ability to save and retrieve text using SQLite.
Write schema.sql with tables for conversations, messages, and notes.
Implement SQLite connection pooling in infrastructure/database.py.
Write repository functions (create_note, get_notes) in infrastructure/repositories.py.
Create Flask routes (/api/notes) in api/ to expose CRUD operations.
Build a minimal Vanilla JS/HTML frontend with a textarea and a list of saved notes.
🛑 DO NOT BUILD: Rich text editing, folders, tags, or AI features.
✅ Definition of Done: A user can type text in the browser, save it, refresh the page, and see the persisted text.


🤖 Phase 2: AI Integration & Short-Term Memory (The Conversationalist)
Goal: Introduce the LLM with basic conversational context (Sliding Window).
Implement core/llm_client.py to handle OpenRouter API requests securely.
Create the /api/chat route.
Implement "Sliding Window Memory": Fetch the last 10 messages for a conversation_id from SQLite and format them into the LLM prompt.
Save both user and AI messages to the SQLite messages table.
Build a basic chat UI in HTML/JS.
🛑 DO NOT BUILD: Streaming text, long-term memory, or knowledge graphs.
✅ Definition of Done: The AI remembers context within the current 10-message window. If asked "What was my first message?", it answers correctly based on the SQLite history.


🕵️ Phase 3: Long-Term Keyword Memory (The Librarian)
Goal: Enable the AI to recall information from weeks/months ago using SQLite FTS5.
Add an FTS5 (Full-Text Search) virtual table to schema.sql linked to messages.
Write a basic keyword extraction utility in core/ (using regex or a lightweight NLP library).
Update the Chat flow: Extract keywords from the current prompt -> Search FTS5 table -> Inject top 3 relevant old messages into the System Prompt.
🛑 DO NOT BUILD: Vector databases (ChromaDB) or embeddings. Stick to FTS5 for now.
✅ Definition of Done: User states a fact on Day 1. On Day 10, user asks a question related to that fact, and the AI retrieves the exact old message via FTS5 to answer correctly.


🧠 Phase 4: Semantic Memory & Vector Search (The Cartographer)
Goal: Upgrade from keyword search to meaning-based (semantic) search.
Integrate sentence-transformers and chromadb.
Implement a post-save hook: When a note/message is saved to SQLite, chunk it, embed it, and save it to ChromaDB.
Implement Hybrid Search: Query both SQLite FTS5 and ChromaDB, merge results, and feed to the LLM.
🛑 DO NOT BUILD: The Knowledge Graph visualization. Focus purely on the backend retrieval pipeline.
✅ Definition of Done: User writes a note about "canine behavior". Later asks about "dog training". ChromaDB retrieves the note based on semantic meaning, despite zero keyword overlap.


🕸️ Phase 5: Knowledge Graph & Visualization (The Network)
Goal: Structure unstructured data into a visual graph.
Add concepts (nodes) and relationships (edges) tables to SQLite.
Write an OpenRouter prompt that reads a new note and outputs strict JSON extracting concepts and relationships.
Parse the JSON and save it to the SQLite graph tables.
Create /api/graph endpoint to serve the graph data as JSON.
Integrate D3.js on the frontend to render an interactive force-directed graph.
✅ Definition of Done: Writing a new note automatically generates nodes and edges that appear and link dynamically in the D3.js canvas.


⏳ Phase 6: Proactive Agents & Reflection (The OS)
Goal: The system acts autonomously to assist the user.
Introduce a background task queue (Celery or APScheduler).
Build the "Daily Reflection" agent: Summarizes the day's notes and generates a morning brief.
Build "Proactive Suggestions": Queries ChromaDB in the background while the user types to surface related past thoughts in a sidebar.
✅ Definition of Done: The app feels "alive", proactively surfacing insights and summaries without explicit user prompts.