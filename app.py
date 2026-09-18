import os
import json
from typing import Dict, List
from flask import Flask, render_template, jsonify, request, Response, stream_with_context

from models import TranscriptMetadata, TranscriptSegment
from services.transcript_parser import parse_transcript_file
from services.guide_parser import parse_interview_guide
from services.rag_service import TranscriptRAGService
from services.llm_service import LLMService
from services.guide_service import GuideService
from services.theme_service import ThemeService
from services.chat_service import ChatService

app = Flask(__name__)

# Base directory for case study data files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Global state loaded on startup
TRANSCRIPT_METADATA: Dict[str, TranscriptMetadata] = {}
TRANSCRIPT_SEGMENTS: Dict[str, List[TranscriptSegment]] = {}
ALL_SEGMENTS_FLAT: List[TranscriptSegment] = []
GUIDE_QUESTIONS: List[Dict[str, str]] = []

# Service instances
rag_service = TranscriptRAGService()
llm_service = LLMService()
guide_service = GuideService(rag_service, llm_service)
theme_service = ThemeService(llm_service)
chat_service = ChatService(rag_service, llm_service)

def load_case_pack():
    """Loads all transcript files and interview guide into memory and vector index."""
    global TRANSCRIPT_METADATA, TRANSCRIPT_SEGMENTS, ALL_SEGMENTS_FLAT, GUIDE_QUESTIONS

    TRANSCRIPT_METADATA.clear()
    TRANSCRIPT_SEGMENTS.clear()
    ALL_SEGMENTS_FLAT.clear()

    # Discover all transcript files in root directory
    file_list = [f for f in os.listdir(BASE_DIR) if f.startswith("Transcript_") and f.endswith(".txt")]
    file_list.sort()

    for fname in file_list:
        fpath = os.path.join(BASE_DIR, fname)
        if os.path.exists(fpath):
            meta, segs = parse_transcript_file(fpath)
            TRANSCRIPT_METADATA[meta.transcript_id] = meta
            TRANSCRIPT_SEGMENTS[meta.transcript_id] = segs
            ALL_SEGMENTS_FLAT.extend(segs)

    # Index into ChromaDB vector database
    rag_service.index_transcripts(ALL_SEGMENTS_FLAT)

    # Load Interview Guide
    guide_path = os.path.join(BASE_DIR, "Interview_Guide.txt")
    GUIDE_QUESTIONS = parse_interview_guide(guide_path)

# Initialize data on app startup
load_case_pack()

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route("/")
def index():
    """Renders the main single-page application dashboard."""
    return render_template("index.html")

@app.route("/api/transcripts", methods=["GET"])
def get_transcripts():
    """Returns all parsed transcript metadata and line-by-line segments."""
    data = {}
    for tid, meta in TRANSCRIPT_METADATA.items():
        data[tid] = {
            "metadata": meta.model_dump(),
            "segments": [s.model_dump() for s in TRANSCRIPT_SEGMENTS.get(tid, [])]
        }
    return jsonify(data)

@app.route("/api/guide-answers", methods=["GET"])
def get_guide_answers():
    """Returns answers to all 6 interview guide questions split per expert."""
    answers = guide_service.get_guide_answers(GUIDE_QUESTIONS, TRANSCRIPT_SEGMENTS)
    return jsonify([a.model_dump() for a in answers])

@app.route("/api/synthesize-guide-summary", methods=["POST"])
def synthesize_guide_summary():
    """Triggers Groq LLM model synthesis for a guide question summary and per-doctor AI summaries."""
    req_data = request.get_json() or {}
    q_id = req_data.get("question_id", "q1")

    q_text = "Robotic surgery adoption and market dynamics"
    for q in GUIDE_QUESTIONS:
        if q["id"] == q_id:
            q_text = q["text"]
            break

    full_res = guide_service._generate_with_llm(q_id, q_text, TRANSCRIPT_SEGMENTS)
    if full_res:
        return jsonify({
            "question_id": q_id,
            "summary": full_res.overall_summary,
            "answers_by_expert": [a.model_dump() for a in full_res.answers_by_expert]
        })

    summary = guide_service.synthesize_summary(q_id, q_text)
    return jsonify({"question_id": q_id, "summary": summary})


@app.route("/api/themes", methods=["GET"])
def get_themes():
    """Returns cross-call consensus and disagreement themes."""
    themes = theme_service.get_themes_and_disagreements(TRANSCRIPT_SEGMENTS)
    return jsonify([t.model_dump() for t in themes])

@app.route("/api/chat", methods=["POST"])
def chat():
    """RAG free-form chat endpoint across all expert transcripts."""
    req_data = request.get_json() or {}
    question = req_data.get("question", "").strip()

    if not question:
        return jsonify({"error": "Question is required"}), 400

    chat_msg = chat_service.answer_user_question(question, TRANSCRIPT_SEGMENTS)
    return jsonify(chat_msg.model_dump())

@app.route("/api/upload", methods=["POST"])
def upload_transcript():
    """Dynamically uploads, parses, and indexes a new transcript file."""
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.endswith(".txt"):
        return jsonify({"error": "Only .txt transcript files are supported"}), 400

    filename = file.filename
    save_path = os.path.join(BASE_DIR, filename)

    try:
        file.save(save_path)
        meta, segs = parse_transcript_file(save_path)

        TRANSCRIPT_METADATA[meta.transcript_id] = meta
        TRANSCRIPT_SEGMENTS[meta.transcript_id] = segs
        ALL_SEGMENTS_FLAT.extend(segs)

        # Index new segments into ChromaDB vector database
        rag_service.index_transcripts(segs)

        return jsonify({
            "success": True,
            "message": f"Successfully parsed and indexed {filename}",
            "transcript_id": meta.transcript_id,
            "expert_name": meta.expert_name,
            "market": meta.market,
            "segment_count": len(segs)
        })
    except Exception as e:
        return jsonify({"error": f"Failed to parse uploaded transcript: {str(e)}"}), 500

from queue import Empty

@app.route("/api/llm-events", methods=["GET"])
def llm_events_stream():
    """SSE endpoint streaming real-time Gemini model loading and status toast events."""
    def event_stream():
        q = llm_service.subscribe()
        try:
            yield f"data: {json.dumps({'type': 'connected', 'data': {'message': 'SSE stream connected'}})}\n\n"
            while True:
                try:
                    event = q.get(timeout=10)
                    yield f"data: {json.dumps(event)}\n\n"
                except Empty:
                    yield ": ping\n\n"
        except (GeneratorExit, Exception):
            pass
        finally:
            llm_service.unsubscribe(q)

    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")

@app.route("/api/model-status", methods=["GET"])
def get_model_status():
    """Returns active candidate models and recent model event history."""
    return jsonify({
        "client_active": llm_service.client is not None,
        "candidate_models": [
            'openai/gpt-oss-20b',
            'openai/gpt-oss-120b',
            'groq/compound-mini'
        ],
        "history": llm_service.event_history[-10:]
    })

@app.route("/api/demo-model-events", methods=["POST"])
def demo_model_events():
    """Triggers a sequence of model loading, rate limit, and model busy events for progress bar testing."""
    llm_service.trigger_demo_events()
    return jsonify({"success": True, "message": "Demo model loading event sequence started."})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

