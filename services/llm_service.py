import os
import json
import logging
import time
import threading
from queue import Queue
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = None
        self.listeners: List[Queue] = []
        self._lock = threading.Lock()
        self.event_history: List[Dict[str, Any]] = []

        if self.api_key and self.api_key not in ["your_gemini_api_key_here", ""]:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Google GenAI Client: {e}. Falling back to smart mock mode.")

    def subscribe(self) -> Queue:
        """Subscribes an SSE listener queue to real-time model loading events."""
        q = Queue()
        with self._lock:
            self.listeners.append(q)
        return q

    def unsubscribe(self, q: Queue):
        """Unsubscribes an SSE listener queue."""
        with self._lock:
            if q in self.listeners:
                self.listeners.remove(q)

    def emit_event(self, event_type: str, payload: Dict[str, Any]):
        """Emits a model loading/status event to all SSE subscribers and history log."""
        event = {
            "type": event_type,
            "data": payload,
            "timestamp": time.time()
        }
        with self._lock:
            self.event_history.append(event)
            if len(self.event_history) > 50:
                self.event_history.pop(0)

            dead_listeners = []
            for q in self.listeners:
                try:
                    q.put_nowait(event)
                except Exception:
                    dead_listeners.append(q)
            for q in dead_listeners:
                if q in self.listeners:
                    self.listeners.remove(q)

    def generate_json(self, prompt: str, schema_description: str) -> Optional[Dict[str, Any]]:
        """Invokes Gemini LLM requesting JSON output matching schema_description with resilient model fallback chain."""
        if not self.client:
            self.emit_event("model_fallback", {
                "model": None,
                "progress": 100,
                "message": "Gemini API key not configured or client inactive. Operating in offline smart synthesis mode."
            })
            return None

        full_prompt = (
            f"{prompt}\n\n"
            f"CRITICAL: Return ONLY valid, parseable raw JSON matching this structure without markdown formatting or code blocks:\n"
            f"{schema_description}"
        )

        candidate_models = [
            'gemini-3.6-flash',
            'gemini-3.7-flash',
            'gemini-3.8-flash',
            'gemini-3.5-flash',
            'gemini-3.1-flash',
            'gemini-2.5-flash'
        ]
        total_models = len(candidate_models)

        for idx, model_name in enumerate(candidate_models, start=1):
            progress_pct = round((idx / total_models) * 100, 1)
            self.emit_event("model_start", {
                "model": model_name,
                "index": idx,
                "total": total_models,
                "progress": progress_pct,
                "message": f"Loading Gemini model {model_name} ({idx}/{total_models})..."
            })

            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=full_prompt,
                )

                text = response.text.strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

                parsed_result = json.loads(text)

                self.emit_event("model_success", {
                    "model": model_name,
                    "index": idx,
                    "total": total_models,
                    "progress": 100.0,
                    "message": f"Successfully connected and generated response with {model_name}!"
                })
                return parsed_result
            except Exception as e:
                err_msg = str(e)
                err_msg_lower = err_msg.lower()

                if "429" in err_msg or "resource_exhausted" in err_msg_lower or "quota" in err_msg_lower or "rate limit" in err_msg_lower:
                    event_type = "rate_limit"
                    msg = f"Rate limit reached for {model_name} (429 Resource Exhausted). Retrying fallback model..."
                elif "503" in err_msg or "unavailable" in err_msg_lower or "overloaded" in err_msg_lower or "busy" in err_msg_lower or "500" in err_msg:
                    event_type = "model_busy"
                    msg = f"Model {model_name} is currently busy or unavailable (503). Retrying fallback model..."
                else:
                    event_type = "model_error"
                    msg = f"Gemini API model {model_name} unavailable: {err_msg[:90]}. Retrying fallback model..."

                logger.warning(msg)
                self.emit_event(event_type, {
                    "model": model_name,
                    "index": idx,
                    "total": total_models,
                    "progress": progress_pct,
                    "message": msg
                })
                continue

        logger.error("All Gemini LLM candidate models failed or unavailable. Triggering deterministic smart fallback mode.")
        self.emit_event("model_fallback", {
            "model": None,
            "progress": 100,
            "message": "All Gemini candidate models failed or rate-limited. Activated smart offline fallback."
        })
        return None

    def trigger_demo_events(self):
        """Emits a sequence of model loading, rate limit, model busy, and success events for testing."""
        def run_demo():
            candidate_models = [
                ('gemini-3.6-flash', 'rate_limit', 'Rate limit reached for gemini-3.6-flash (429 Resource Exhausted). Retrying fallback...'),
                ('gemini-3.7-flash', 'model_busy', 'Model gemini-3.7-flash is currently busy (503 Service Unavailable). Retrying fallback...'),
                ('gemini-3.8-flash', 'model_success', 'Successfully connected and generated content using gemini-3.8-flash!')
            ]
            total = 6
            for idx, (model_name, status, msg) in enumerate(candidate_models, start=1):
                progress = round((idx / total) * 100, 1)
                self.emit_event("model_start", {
                    "model": model_name,
                    "index": idx,
                    "total": total,
                    "progress": progress,
                    "message": f"Loading Gemini model {model_name} ({idx}/{total})..."
                })
                time.sleep(1.0)
                if status == "rate_limit":
                    self.emit_event("rate_limit", {
                        "model": model_name,
                        "index": idx,
                        "total": total,
                        "progress": progress,
                        "message": msg
                    })
                    time.sleep(0.8)
                elif status == "model_busy":
                    self.emit_event("model_busy", {
                        "model": model_name,
                        "index": idx,
                        "total": total,
                        "progress": progress,
                        "message": msg
                    })
                    time.sleep(0.8)
                elif status == "model_success":
                    self.emit_event("model_success", {
                        "model": model_name,
                        "index": idx,
                        "total": total,
                        "progress": 100.0,
                        "message": msg
                    })

        threading.Thread(target=run_demo, daemon=True).start()

