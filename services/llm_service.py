import os
import json
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = None

        if self.api_key and self.api_key not in ["your_gemini_api_key_here", ""]:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Google GenAI Client: {e}. Falling back to smart mock mode.")

    def generate_json(self, prompt: str, schema_description: str) -> Optional[Dict[str, Any]]:
        """Invokes Gemini LLM requesting JSON output matching schema_description with resilient model fallback chain."""
        if not self.client:
            return None

        full_prompt = (
            f"{prompt}\n\n"
            f"CRITICAL: Return ONLY valid, parseable raw JSON matching this structure without markdown formatting or code blocks:\n"
            f"{schema_description}"
        )

        # Candidate model fallback sequence across Gemini Flash models
        candidate_models = [
            'gemini-3.6-flash',
            'gemini-3.7-flash',
            'gemini-3.8-flash',
            'gemini-3.5-flash',
            'gemini-3.1-flash',
            'gemini-2.5-flash'
        ]

        for model_name in candidate_models:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=full_prompt,
                )

                text = response.text.strip()
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
                logger.warning(f"Gemini API model {model_name} unavailable: {e}. Attempting fallback model...")
                continue

        logger.error("All Gemini LLM candidate models failed or unavailable. Triggering deterministic smart fallback mode.")
        return None
