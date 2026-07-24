import os
import logging
from openai import OpenAI
from backend.config import Config

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self):
        api_key = Config.OPENAI_API_KEY
        base_url = Config.OPENAI_BASE_URL or None
        self.model = Config.OPENAI_MODEL

        # Auto-detect OpenRouter
        if api_key and api_key.startswith("sk-or-") and not base_url:
            base_url = "https://openrouter.ai/api/v1"
            if self.model == "gpt-4o-mini":
                self.model = "openai/gpt-4o-mini"
        elif base_url and "openrouter.ai" in base_url and self.model == "gpt-4o-mini":
            self.model = "openai/gpt-4o-mini"

        extra_headers = {}
        if base_url and "openrouter.ai" in base_url:
            extra_headers = {
                "HTTP-Referer": "http://localhost:3000",
                "X-Title": "Pipeline.sh",
            }

        self.client = None
        if api_key:
            try:
                self.client = OpenAI(
                    api_key=api_key,
                    base_url=base_url,
                    default_headers=extra_headers
                )
            except Exception as exc:
                logger.error("Failed to initialize OpenAI client: %s", exc)

    def analyze_logs(self, logs: str):
        if not logs:
            return {"summary": "No logs provided", "issues": []}

        if not self.client:
            return {"summary": "AI analysis unavailable", "error": "AI client not initialized. Check credentials."}

        prompt = (
            "Analyze the following CI/CD logs. Identify error patterns, warnings, root causes, and suggest fixes. "
            "Return a JSON object with issue categories, recommendations, and severity.\n\n" + logs
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3,
            )
            text = response.choices[0].message.content
            return {"summary": "AI analysis completed", "debug_advice": text}
        except Exception as exc:
            return {"summary": "AI analysis unavailable", "error": str(exc)}

    def explain_error(self, error_text: str):
        if not self.client:
            return "Could not analyze error: AI client not initialized. Check credentials."

        prompt = f"Explain this pipeline error and propose a fix: {error_text}"
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.2,
            )
            return response.choices[0].message.content
        except Exception as exc:
            return f"Could not analyze error: {exc}"

