# Hasamex AI Case Study - Expert-Call Transcript Intelligence App

A local Flask web application designed for the **Hasamex European Robotic Surgery Market** case study. The app ingests expert-call transcripts from France, Germany, and the UK, automatically answers the project's 6 interview guide questions per expert with grounded quotes, surfaces cross-market themes & disagreements, and enables free-form RAG chat across all calls with click-to-scroll transcript highlighting.

---

## Quickstart (How to Run Locally)

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
   Add your `GROQ_API_KEY` (or `GEMINI_API_KEY`) in `.env` for live LLM completions. *(Note: If no API key is provided, the app automatically runs in deterministic smart-fallback mode).*

4. **Run Application Server:**
   ```bash
   python app.py
   ```

5. **Open Browser:**
   Navigate to `http://localhost:5000`

---

## System Architecture

```
                                  ┌───────────────────────────────┐
                                  │      Flask Web Dashboard      │
                                  │ (Jinja2 + Vanilla JS + CSS)   │
                                  └──────────────┬────────────────┘
                                                 │ REST API Calls
                                                 ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                          Flask REST API Layer                                          │
│ GET /api/transcripts │ GET /api/guide-answers │ GET /api/themes │ POST /api/chat │ POST /api/upload    │
└───────┬───────────────────────────────┬───────────────────────────────┬───────────────────┬────────────┘
        │                               │                               │                   │
        ▼                               ▼                               ▼                   ▼
┌──────────────┐             ┌─────────────────────┐          ┌───────────────────┐ ┌────────────────────┐
│ GuideService │             │  TranscriptRAGService│          │   ThemeService    │ │ Dynamic Upload     │
│ (Per-Expert) │             │ (ChromaDB Vector DB)│          │(Cross-Call Synt.) │ │ File Parser        │
└───────┬──────┘             └──────────┬──────────┘          └─────────┬─────────┘ └─────────┬──────────┘
        │                               │                               │                     │
        └───────────────────────────────┼───────────────────────────────┴─────────────────────┘
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │   Quote Verification Engine │
                         │ (Fuzzy Match & Timestamp ID)│
                         └─────────────────────────────┘
```

---

## Technical Case Requirements Matrix

| Requirement | Implementation Detail | Location |
| :--- | :--- | :--- |
| **1. Upload & Read Transcripts** | Custom parser (`transcript_parser.py`) extracts metadata & dialogue turns. Includes interactive drag & drop UI + `POST /api/upload` endpoint for dynamic transcript ingestion. | `app.py` & `services/transcript_parser.py` |
| **2. Answer Guide Questions per Expert** | Answers all 6 market research questions per expert with a unified cross-market executive takeaway summary at the top of each question card. | `services/guide_service.py` |
| **3 & 4. Exact Quotes & Timestamps** | Output schema enforces `QuoteEvidence` (`transcript_id`, `quote`, `timestamp`, `segment_index`). Clicking any card smooth-scrolls to the exact line & flashes a pulse highlight. | `static/js/app.js` |
| **5. Cross-Call Themes & Disagreements** | Synthesizes consensus (e.g., training bottlenecks, procurement ROI weight) vs. key disagreements (e.g., expected 3-5y growth: Germany 7-12% vs France/UK 15-20%+). | `services/theme_service.py` |
| **6. Topic-Enriched RAG Search** | ChromaDB vector store embeds dialogue segments enriched with interviewer question prompts & section topics. Per-market querying (`query_segments_per_market`) guarantees 100% equal market representation. | `services/rag_service.py` & `services/chat_service.py` |

---

## Technical Interview Talking Points

### 1. Model Choice & RAG Strategy
* **LLM Engine:** Google Gemini API (`gemini-2.5-flash`, with resilient multi-model fallback chain across `gemini-1.5-flash`, `gemini-2.0-flash`, `gemini-3.6-flash`) for low-latency inference and structured JSON schema compliance.
* **Vector Store:** ChromaDB in-memory vector database with `all-MiniLM-L6-v2` embeddings.
* **Topic-Enriched Q+A Indexing:** Solves dialogue ellipsis by pairing interviewer prompts and section topics directly into candidate chunk embeddings, ensuring queries for `"decision-making timeline"` match exact answer turns (*"Nine to eighteen months..."*).
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
* **Quote Verification Engine (`quote_verifier.py`):** Runs a post-processing pass comparing returned quote strings against actual `TranscriptSegment`s using SequenceMatcher fuzzy alignment. If the LLM miscalculates `segment_index`, the verifier auto-repairs the index and timestamp before returning to the UI.

### 4. How to Scale from 3 Transcripts to 30+ or 300+
In the technical round, explain how our current architecture scales seamlessly:
1. **Vector Retrieval vs. Context Explosion:**
   * Passing 30 transcripts (~600KB) into a single prompt increases latency and token costs. RAG allows retrieving only the top $k$ relevant segments per query.
2. **Metadata Partitioning & Per-Market Grouping:**
   * ChromaDB vector metadata filters (`where={"market": "Germany"}`) narrow search bounds instantly and ensure fair representation across 300+ files.
3. **Dynamic Upload Pipeline (`POST /api/upload`):**
   * Async file upload endpoint parses `.txt` files on the fly, updates vector indexes in real-time, and refreshes dashboard tabs dynamically.
4. **Database Persistence & Async Indexing:**
   * Move from in-memory Chroma to persistent Chroma/pgvector storage, indexing new transcripts asynchronously via background worker threads.
