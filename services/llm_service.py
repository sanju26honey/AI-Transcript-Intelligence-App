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
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = None
        self.listeners: List[Queue] = []
        self._lock = threading.Lock()
        self.event_history: List[Dict[str, Any]] = []

        if self.api_key and self.api_key not in ["your_groq_api_key_here", ""]:
            try:
                from groq import Groq
                self.client = Groq(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Groq Client: {e}. Falling back to smart mock mode.")

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

    def generate_json(self, prompt: str, schema_description: str, task_label: str = "Synthesis Task") -> Optional[Dict[str, Any]]:
        """Invokes Groq LLM requesting JSON output matching schema_description with resilient model fallback chain."""
        if not self.client:
            self.emit_event("model_fallback", {
                "model": None,
                "task_label": task_label,
                "progress": 100,
                "message": f"[{task_label}] Groq client inactive. Operating in instant RAG synthesis mode."
            })
            return None

        full_prompt = (
            f"{prompt}\n\n"
            f"CRITICAL: Return ONLY valid, parseable raw JSON matching this structure without markdown formatting or code blocks:\n"
            f"{schema_description}"
        )

        candidate_models = [
            'openai/gpt-oss-20b',
            'openai/gpt-oss-120b',
            'groq/compound-mini'
        ]
        total_models = len(candidate_models)

        for idx, model_name in enumerate(candidate_models, start=1):
            next_model = candidate_models[idx] if idx < total_models else None
            progress_pct = round((idx / total_models) * 100, 1)

            self.emit_event("model_start", {
                "model": model_name,
                "next_model": next_model,
                "task_label": task_label,
                "index": idx,
                "total": total_models,
                "progress": progress_pct,
                "message": f"Loading {model_name}..."
            })

            try:
                completion = self.client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {
                            "role": "user",
                            "content": full_prompt
                        }
                    ]
                )

                text = completion.choices[0].message.content.strip() if completion and completion.choices else ""
                if not text:
                    continue

                import re
                cleaned = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
                cleaned = re.sub(r'\s*```$', '', cleaned, flags=re.MULTILINE).strip()

                parsed_result = None
                try:
                    parsed_result = json.loads(cleaned)
                except Exception:
                    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
                    if match:
                        try:
                            parsed_result = json.loads(match.group(0))
                        except Exception:
                            pass

                if parsed_result is None and len(cleaned) > 10:
                    parsed_result = {"overall_summary": cleaned}

                # If parsed_result wrapped a nested JSON object inside "overall_summary", unpack it
                if parsed_result and isinstance(parsed_result, dict) and "overall_summary" in parsed_result and isinstance(parsed_result["overall_summary"], str):
                    val = parsed_result["overall_summary"].strip()
                    if val.startswith("{") and val.endswith("}"):
                        try:
                            unpacked = json.loads(val)
                            if isinstance(unpacked, dict):
                                parsed_result = unpacked
                        except Exception:
                            pass

                if parsed_result and isinstance(parsed_result, dict):
                    self.emit_event("model_success", {
                        "model": model_name,
                        "task_label": task_label,
                        "index": idx,
                        "total": total_models,
                        "progress": 100.0,
                        "message": f"Connected to {model_name} successfully!"
                    })
                    return parsed_result
            except Exception as e:
                err_msg = str(e)
                err_msg_lower = err_msg.lower()

                if "429" in err_msg or "rate limit" in err_msg_lower:
                    event_type = "rate_limit"
                    reason = "429 Rate Limit"
                    msg = f"Failed due to 429 Rate Limit ({model_name})" + (f", loading {next_model} instead..." if next_model else "...")
                elif "503" in err_msg or "unavailable" in err_msg_lower or "500" in err_msg:
                    event_type = "model_busy"
                    reason = "503 Model Busy"
                    msg = f"Failed due to 503 Model Busy ({model_name})" + (f", loading {next_model} instead..." if next_model else "...")
                else:
                    event_type = "model_error"
                    reason = "Unavailable"
                    msg = f"Failed ({model_name})" + (f", loading {next_model} instead..." if next_model else "...")

                logger.warning(f"[{task_label}] {msg}")
                self.emit_event(event_type, {
                    "model": model_name,
                    "next_model": next_model,
                    "reason": reason,
                    "task_label": task_label,
                    "index": idx,
                    "total": total_models,
                    "progress": progress_pct,
                    "message": msg
                })
                continue

        logger.error(f"[{task_label}] All candidate Groq models unavailable. Triggering offline summary.")
        self.emit_event("model_fallback", {
            "model": None,
            "task_label": task_label,
            "progress": 100,
            "message": f"[{task_label}] All Groq candidate models unavailable. Showing offline summary."
        })
        return None



    def trigger_demo_events(self):
        """Emits a sequence of multi-task model loading, rate limit, and model busy events for testing."""
        def run_demo():
            tasks = [
                ('Guide Q1', [
                    ('gemini-2.5-flash', 'rate_limit', '[Guide Q1] Rate limit reached for gemini-3.6-flash (429 Resource Exhausted). Retrying fallback...'),
                    ('gemini-3.7-flash', 'model_success', '[Guide Q1] Connected to gemini-3.7-flash successfully!')
                ]),
                ('Themes', [
                    ('gemini-3.6-flash', 'model_busy', '[Themes] Model gemini-3.6-flash is currently busy (503 Service Unavailable). Retrying...'),
                    ('gemini-3.7-flash', 'rate_limit', '[Themes] Rate limit reached for gemini-3.7-flash (429). Retrying...'),
                    ('gemini-3.8-flash', 'model_success', '[Themes] Connected to gemini-3.8-flash successfully!')
                ])
            ]
            total = 6
            for task_label, events in tasks:
                for idx, (model_name, status, msg) in enumerate(events, start=1):
                    progress = round((idx / total) * 100, 1)
                    self.emit_event("model_start", {
                        "model": model_name,
                        "task_label": task_label,
                        "index": idx,
                        "total": total,
                        "progress": progress,
                        "message": f"[{task_label}] Loading Gemini model {model_name} ({idx}/{total})..."
                    })
                    time.sleep(0.9)
                    if status == "rate_limit":
                        self.emit_event("rate_limit", {
                            "model": model_name,
                            "task_label": task_label,
                            "index": idx,
                            "total": total,
                            "progress": progress,
                            "message": msg
                        })
                        time.sleep(0.7)
                    elif status == "model_busy":
                        self.emit_event("model_busy", {
                            "model": model_name,
                            "task_label": task_label,
                            "index": idx,
                            "total": total,
                            "progress": progress,
                            "message": msg
                        })
                        time.sleep(0.7)
                    elif status == "model_success":
                        self.emit_event("model_success", {
                            "model": model_name,
                            "task_label": task_label,
                            "index": idx,
                            "total": total,
                            "progress": 100.0,
                            "message": msg
                        })
                        time.sleep(0.5)

        threading.Thread(target=run_demo, daemon=True).start()


