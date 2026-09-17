# Hasamex AI Case Study - Expert-Call Transcript Intelligence App

A local Flask web application designed for the **Hasamex European Robotic Surgery Market** case study. The app ingests expert-call transcripts from France, Germany, and the UK (with support for dynamic upload of additional markets), automatically answers the project's 6 interview guide questions per expert with grounded quotes, surfaces cross-market themes & disagreements, and enables free-form RAG chat across all calls with click-to-scroll transcript highlighting.

---

## Key Features

- **Multi-Market Expert Intelligence:** Analyzes primary research transcripts across European markets (France, Germany, UK).
- **Automated Guide Question Answering:** Answers all 6 core research questions per expert with cross-market executive summaries.
- **Timestamp & Quote Grounding:** Enforces Pydantic output schemas with automatic SequenceMatcher quote verification. Clicking any quote pill smooth-scrolls to the exact line in the transcript tab with a yellow keyframe flash animation.
- **Cross-Call Themes & Disagreements:** Identifies key consensus drivers (e.g. training bottlenecks, ROI priorities) and market disagreements (e.g. 3-5y growth rates: Germany 7-12% vs France/UK 15-20%+).
- **Topic-Enriched RAG Search:** In-memory ChromaDB vector store pairing interviewer prompts and section topics directly into segment embeddings to ensure 100% equal market retrieval.
- **Dynamic Transcript Upload:** Drop new `.txt` transcript files via UI or `POST /api/upload` to parse and index new markets on the fly (test samples included in `samples/`).
- **Resilient Multi-Model LLM Chain:** Powered by Groq API (`openai/gpt-oss-20b`, `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`) with automatic fallback to deterministic smart-mock/RAG mode when offline or unconfigured.
- **Real-Time SSE Event Stream:** Live Server-Sent Events (`/api/llm-events`) driving status toasts and model fallback progress indicators in the frontend UI.

---

## Quickstart (How to Run Locally)

### Prerequisites
- **Python 3.11+**
- Virtual environment (recommended)

### Installation Steps

1. **Clone & Navigate:**
   ```bash
   cd "D:\Hasamex Case Study"
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables (Optional for LLM API):**
   ```bash
   cp .env.example .env
   ```
   Add your `GROQ_API_KEY` in `.env` for live LLM completions:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   FLASK_ENV=development
   PORT=5000
   ```
   *(Note: If no API key is provided, the app automatically runs in deterministic smart-fallback mode with full RAG functionality).*

4. **Run Application Server:**
   ```bash
   python app.py
   ```

5. **Open Browser:**
   Navigate to `http://localhost:5000` (or `http://127.0.0.1:5000`)

---

## System Architecture

```
                                  ┌───────────────────────────────┐
                                  │      Flask Web Dashboard      │
                                  │ (Jinja2 + Vanilla JS + CSS)   │
                                  └──────────────┬────────────────┘
                                                 │ REST API & SSE Events
                                                 ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                              Flask REST API Layer                                                │
│ GET /api/transcripts │ GET /api/guide-answers │ GET /api/themes │ POST /api/chat │ POST /api/upload │ GET /api/llm-events │
└───────┬───────────────────────┬───────────────────────┬───────────────────┬──────────────────┬───────────────────┘
        │                       │                       │                   │                  │
        ▼                       ▼                       ▼                   ▼                  ▼
┌──────────────┐     ┌─────────────────────┐  ┌───────────────────┐ ┌────────────────────┐ ┌───────────────────┐
│ GuideService │     │ TranscriptRAGService│  │   ThemeService    │ │ Dynamic Upload     │ │   LLMService      │
│ (Per-Expert) │     │ (ChromaDB Vector DB)│  │(Cross-Call Synt.) │ │ File Parser        │ │ (Groq + SSE Stream)│
└───────┬──────┘     └──────────┬──────────┘  └─────────┬─────────┘ └─────────┬──────────┘ └─────────┬─────────┘
        │                       │                       │                     │                    │
        └───────────────────────┼───────────────────────┴─────────────────────┴────────────────────┘
                                │
                                ▼
                 ┌─────────────────────────────┐
                 │   Quote Verification Engine │
                 │ (Fuzzy Match & Timestamp ID)│
                 └─────────────────────────────┘
```

---

## REST API Specification

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Main Single-Page Application (SPA) dashboard interface. |
| `/api/transcripts` | `GET` | Returns metadata and line-by-line segments for all loaded transcripts. |
| `/api/guide-answers` | `GET` | Returns structured answers to all 6 interview guide questions split per expert. |
| `/api/synthesize-guide-summary` | `POST` | Triggers Groq LLM synthesis for a guide question executive takeaway summary. |
| `/api/themes` | `GET` | Returns cross-call consensus and disagreement themes with quote evidence. |
| `/api/chat` | `POST` | Free-form RAG chat endpoint querying all uploaded transcripts. |
| `/api/upload` | `POST` | Dynamically uploads, parses, and vector-indexes a new `.txt` transcript file. |
| `/api/llm-events` | `GET` | Server-Sent Events (SSE) stream delivering real-time model loading and status events. |
| `/api/model-status` | `GET` | Returns active candidate model fallback list and recent model event history. |
| `/api/demo-model-events` | `POST` | Triggers a test sequence of multi-task model loading and rate limit events for UI progress testing. |

---

## Technical Case Requirements Matrix

| Requirement | Implementation Detail | Location |
| :--- | :--- | :--- |
| **1. Upload & Read Transcripts** | Custom transcript parser (`transcript_parser.py`) extracts metadata headers & dialogue turns. Drag-and-drop UI + `POST /api/upload` endpoint for dynamic transcript ingestion. | `app.py` & `services/transcript_parser.py` |
| **2. Answer Guide Questions per Expert** | Resolves all 6 market research questions per expert with cross-market executive takeaways. | `services/guide_service.py` & `services/guide_parser.py` |
| **3 & 4. Exact Quotes & Timestamps** | Output schema enforces `QuoteEvidence` (`transcript_id`, `quote`, `timestamp`, `segment_index`, `speaker`). Clicking citation pills smooth-scrolls to exact line & triggers yellow pulse flash. | `models.py` & `static/js/app.js` |
| **5. Cross-Call Themes & Disagreements** | Synthesizes consensus (e.g. training bottlenecks, ROI priorities) vs. key disagreements (e.g. 3-5y growth: Germany 7-12% vs France/UK 15-20%+). | `services/theme_service.py` |
| **6. Topic-Enriched RAG Search** | ChromaDB vector store embeds dialogue segments enriched with interviewer prompts & section topics. Per-market querying (`query_segments_per_market`) guarantees 100% equal market representation. | `services/rag_service.py` & `services/chat_service.py` |

---

### 1. Model Choice & RAG Strategy
* **LLM Engine:** Groq API (`openai/gpt-oss-20b` primary model, with resilient fallback across `llama-3.3-70b-versatile` and `llama-3.1-8b-instant`) for low-latency inference and structured JSON schema compliance.
* **Vector Store:** ChromaDB in-memory vector database using `all-MiniLM-L6-v2` embeddings.
* **Topic-Enriched Q+A Indexing:** Solves dialogue ellipsis by pairing interviewer prompts and section topics directly into candidate chunk embeddings, ensuring queries for *"decision-making timeline"* match exact answer turns (*"Nine to eighteen months..."*).
* **Per-Market Grouped Retrieval:** Prevents single-market adoption chunks from crowding out other markets, guaranteeing balanced side-by-side citations across all uploaded transcripts.

### 2. Citation & Timestamp Grounding
* Grounding is enforced at the schema level using Pydantic `QuoteEvidence` structures (`quote`, `timestamp`, `segment_index`, `speaker`).
* On the UI side, clicking any citation pill executes:
  ```javascript
  el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  el.classList.add('highlight-pulse'); // Yellow keyframe flash animation
  ```

### 3. How We Reduce Hallucinations
* **Structured Output Constraint:** Forcing the LLM to return strict Pydantic JSON schemas.
* **Quote Verification Engine (`quote_verifier.py`):** Runs a post-processing pass comparing returned quote strings against actual `TranscriptSegment`s using `SequenceMatcher` fuzzy alignment. If the LLM miscalculates `segment_index`, the verifier auto-repairs the index and timestamp before returning to the UI.

### 4. How to Scale from 3 Transcripts to 30+ or 300+
1. **Vector Retrieval vs. Context Explosion:**
   * Passing 30+ transcripts into a single prompt increases latency and token costs exponentially. RAG retrieves only top $k$ relevant segments per query.
2. **Metadata Partitioning & Per-Market Grouping:**
   * ChromaDB vector metadata filters (`where={"market": "Germany"}`) narrow search bounds instantly and ensure fair representation across 300+ files.
3. **Dynamic Upload Pipeline (`POST /api/upload`):**
   * Async file upload endpoint parses `.txt` files on the fly, updates vector indexes in real-time, and refreshes dashboard tabs dynamically. Additional test transcripts (Italy, Spain, Netherlands, Sweden) are available in `samples/` for instant testing.
4. **Database Persistence & Async Indexing:**
   * Move from in-memory ChromaDB to persistent Chroma/pgvector storage, indexing new transcripts asynchronously via background worker threads.
