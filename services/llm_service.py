import os
import json
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = None

        if self.api_key and self.api_key not in ["your_groq_api_key_here", "your_gemini_api_key_here"]:
            try:
                from groq import Groq
                self.client = Groq(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Groq Client: {e}. Falling back to smart mock mode.")

    def generate_json(self, prompt: str, schema_description: str) -> Optional[Dict[str, Any]]:
        """Invokes Groq LLM requesting JSON output matching schema_description."""
        if not self.client:
            return None

        full_prompt = (
            f"{prompt}\n\n"
            f"CRITICAL: Return ONLY valid, parseable raw JSON matching this structure without markdown formatting or code blocks:\n"
            f"{schema_description}"
        )

        candidate_models = [
            "openai/gpt-oss-20b",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant"
        ]

        for model_name in candidate_models:
            try:
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are a helpful JSON-only data extraction assistant. Return only raw, valid JSON."},
                        {"role": "user", "content": full_prompt}
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"}
                )

                text = response.choices[0].message.content.strip()
                # Clean possible markdown code fences
                if text.startswith("```json"):
                    text = text[7:]
                if text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

                return json.loads(text)
            except Exception as e:
                logger.warning(f"Groq API model {model_name} unavailable: {e}. Attempting next candidate model...")
                continue

        logger.error("All Groq LLM candidate models failed or unavailable. Triggering deterministic smart fallback mode.")
        return None
