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

        if self.api_key and self.api_key != "your_gemini_api_key_here":
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Google GenAI Client: {e}. Falling back to smart mock mode.")

    def generate_json(self, prompt: str, schema_description: str) -> Optional[Dict[str, Any]]:
        """Invokes Gemini LLM requesting JSON output matching schema_description."""
        if not self.client:
            return None

        try:
            full_prompt = (
                f"{prompt}\n\n"
                f"CRITICAL: Return ONLY valid, parseable raw JSON matching this structure without markdown formatting or code blocks:\n"
                f"{schema_description}"
            )

            response = self.client.models.generate_content(
                model='gemini-3.6-flash',
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
            logger.error(f"Error calling Gemini API: {e}")
            return None
