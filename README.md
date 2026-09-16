# Hasamex AI Case Study - Expert-Call Transcript Intelligence App

A local Flask web application designed for the **Hasamex European Robotic Surgery Market** case study. The app ingests expert-call transcripts from France, Germany, and the UK, automatically answers the project's 6 interview guide questions per expert with grounded quotes, surfaces cross-market themes & disagreements, and enables free-form RAG chat across all calls with click-to-scroll transcript highlighting.

---

## 🚀 Quickstart (How to Run Locally)

### Prerequisites
- Python 3.11+
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
   Add your `GEMINI_API_KEY` in `.env` for live LLM completions. *(Note: If no API key is provided, the app automatically runs in deterministic smart-fallback mode).*

4. **Run Application Server:**
   ```bash
   python app.py
   ```

5. **Open Browser:**
   Navigate to `http://localhost:5000`

---

## 🏛️ System Architecture

```
                                  ┌───────────────────────────────┐
                                  │      Flask Web Dashboard      │
                                  │ (Jinja2 + Vanilla JS + CSS)   │
                                  └──────────────┬────────────────┘
                                                 │ REST API Calls
                                                 ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   Flask REST API Layer                                 │
│          GET /api/transcripts │ GET /api/guide-answers │ GET /api/themes │ POST /api/chat│
└───────┬───────────────────────────────┬───────────────────────────────┬────────────────┘
        │                               │                               │
        ▼                               ▼                               ▼
┌──────────────┐             ┌─────────────────────┐          ┌───────────────────┐
│ GuideService │             │  TranscriptRAGService│          │   ThemeService    │
│ (Per-Expert) │             │ (ChromaDB Vector DB)│          │(Cross-Call Synt.) │
└───────┬──────┘             └──────────┬──────────┘          └─────────┬─────────┘
        │                               │                               │
        └───────────────────────────────┼───────────────────────────────┘
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │   Quote Verification Engine │
                         │ (Fuzzy Match & Timestamp ID)│
                         └─────────────────────────────┘
```

---

## 🎯 Technical Case Requirements Matrix

| Requirement | Implementation Detail | Location |
| :--- | :--- | :--- |
| **1. Read 3 Transcripts** | Custom parser (`transcript_parser.py`) extracts metadata (Expert Name, Role, Market), timestamp headers (`MM:SS`), and dialogue turns. | `services/transcript_parser.py` |
| **2. Answer Guide Questions per Expert** | Answers all 6 market research questions, split by expert (Dr. Jean Martin - France, Anna Keller - Germany, Dr. Emily Carter - UK). | `services/guide_service.py` |
| **3 & 4. Exact Quotes & Timestamps** | Output schema enforces `QuoteEvidence` (`transcript_id`, `quote`, `timestamp`, `segment_index`). Clicking any card smooth scrolls the transcript & flashes a yellow pulse. | `static/js/app.js` |
| **5. Cross-Call Themes & Disagreements** | Synthesizes consensus (e.g., training bottlenecks, procurement ROI weight) vs. key disagreements (e.g., expected 3-5y procedure volume growth: Germany 7-12% vs France/UK 15-20%+). | `services/theme_service.py` |
| **6. RAG Free-Form Chat** | ChromaDB vector store embeds dialogue segments with rich metadata (`market`, `expert_name`, `timestamp`). RAG endpoint handles arbitrary search questions. | `services/rag_service.py` & `services/chat_service.py` |

---

## 🎙️ Technical Interview Talking Points

### 1. Model Choice & RAG Strategy
* **LLM Engine:** Gemini 2.5 / 1.5 Flash via `google-genai` for fast inference and structured JSON schema compliance.
* **Vector Store:** ChromaDB in-memory vector database with `all-MiniLM-L6-v2` embeddings.
* **Why RAG?** Even though 3 transcripts fit in context (~6KB total text), RAG was implemented for free-form search and to demonstrate a modular vector architecture that scales.

### 2. Citation & Timestamp Grounding
* Grounding is enforced at the schema level using Pydantic `QuoteEvidence` structures (`quote`, `timestamp`, `segment_index`, `speaker`).
* On the UI side, clicking any citation pill executes:
  ```javascript
  el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  el.classList.add('highlight-pulse'); // Yellow keyframe flash animation
  ```

### 3. How We Reduce Hallucinations
* **Structured Output Constraint:** Forcing the LLM to return strict Pydantic JSON schemas.
* **Quote Verification Engine (`quote_verifier.py`):** Runs a post-processing pass comparing returned quote strings against actual `TranscriptSegment`s using SequenceMatcher fuzzy alignment. If the LLM miscalculates `segment_index`, the verifier auto-repairs the index and timestamp before returning to the UI.

### 4. How to Scale from 3 Transcripts to 30+ or 300+
In the technical round, explain how our current architecture scales seamlessly:
1. **Vector Retrieval vs. Context Explosion:**
   * Passing 30 transcripts (~600KB) into a single prompt increases latency and token costs. RAG allows retrieving only the top $k$ relevant segments (e.g., top 10 segments across 300 files) per query.
2. **Metadata Partitioning:**
   * ChromaDB vector metadata filters (e.g. `where={"market": "Germany"}` or `where={"specialty": "Urology"}`) narrow vector search bounds instantly.
3. **Chunking Optimization:**
   * Chunking by multi-turn conversation windows (3–5 segments) preserves dialogue context while preserving fine-grained `start_seconds` timestamps for UI highlighting.
4. **Database Persistence & Async Indexing:**
   * Move from in-memory Chroma to persistent Chroma/pgvector SQLite storage, indexing new transcripts asynchronously via background tasks.
