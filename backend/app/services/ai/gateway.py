"""AI Gateway: single entry point for every LLM call.

Responsibilities: provider selection, versioned prompts, JSON extraction + schema validation with one
repair attempt, deterministic fallbacks, and AIRequest logging (tokens, cost, latency, failures).
"""

import logging
import time
from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models import AIRequest
from app.services.ai.json_utils import extract_json, strip_reasoning
from app.services.ai.prompts import get_prompt
from app.services.ai.providers.anthropic import AnthropicProvider
from app.services.ai.providers.base import CompletionResult, LLMProvider, ProviderError
from app.services.ai.providers.gemini import GeminiProvider
from app.services.ai.providers.mock import MockProvider
from app.services.ai.providers.openai_compat import OpenAICompatibleProvider

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

LANGUAGE_NAMES = {"ru": "Russian", "en": "English", "kk": "Kazakh"}


class AIError(RuntimeError):
    pass


def build_provider(name: str, s: Settings) -> LLMProvider:
    if name == "alem":
        return OpenAICompatibleProvider(
            "alem", s.alem_base_url, s.alem_api_key, s.ai_timeout_seconds,
            supports_json_mode=False, disable_thinking=s.ai_disable_thinking,
        )
    if name == "openai":
        return OpenAICompatibleProvider("openai", s.openai_base_url, s.openai_api_key, s.ai_timeout_seconds)
    if name == "anthropic":
        return AnthropicProvider(s.anthropic_api_key, s.ai_timeout_seconds)
    if name == "gemini":
        return GeminiProvider(s.gemini_api_key, s.ai_timeout_seconds)
    return MockProvider()


class AIGateway:
    def __init__(self, db: Session | None, user_id: int | None = None, provider: LLMProvider | None = None):
        self.db = db
        self.user_id = user_id
        self.settings = get_settings()
        self.provider = provider or build_provider(self.settings.ai_provider, self.settings)
        self.model = self.settings.ai_model if self.provider.name != "mock" else "mock-1"

    # ------------------------------------------------------------------ public API

    def run_json(
        self,
        task: str,
        variables: dict,
        schema: type[T],
        *,
        meta: dict | None = None,
        fallback: Callable[[], T] | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1800,
        model: str | None = None,
    ) -> tuple[T, str]:
        """Returns (validated_output, status) where status is ok | repaired | fallback."""
        variables = self._with_language(variables)
        prompt = get_prompt(self.db, task, variables)
        messages = [{"role": "system", "content": prompt.system}, {"role": "user", "content": prompt.user}]
        meta = {**(meta or {}), "lang": variables.get("language", "en")}
        model = model or self.model
        last_error = ""
        for attempt in range(2):
            try:
                res = self._call(messages, model=model, temperature=temperature, max_tokens=max_tokens, task=task, meta=meta)
            except ProviderError as e:
                last_error = str(e)
                self._log(task, prompt.key, prompt.version, None, "error", last_error, model)
                break
            try:
                parsed = schema.model_validate(extract_json(res.text))
                self._log(task, prompt.key, prompt.version, res, "ok" if attempt == 0 else "repaired", None, model)
                return parsed, "ok" if attempt == 0 else "repaired"
            except (ValueError, ValidationError) as e:
                last_error = f"invalid output: {str(e)[:400]}"
                self._log(task, prompt.key, prompt.version, res, "invalid", last_error, model)
                messages = messages + [
                    {"role": "assistant", "content": strip_reasoning(res.text)[:4000]},
                    {"role": "user", "content": "Your previous reply was not valid JSON for the requested shape. "
                     f"Error: {str(e)[:300]}. Reply again with ONLY the corrected JSON object."},
                ]
        if fallback is not None:
            log.warning("AI task %s fell back to deterministic output: %s", task, last_error)
            return fallback(), "fallback"
        raise AIError(f"AI task '{task}' failed: {last_error}")

    def run_text(self, task: str, variables: dict, *, meta: dict | None = None, temperature: float = 0.5,
                 max_tokens: int = 800) -> str:
        variables = self._with_language(variables)
        prompt = get_prompt(self.db, task, variables)
        messages = [{"role": "system", "content": prompt.system}, {"role": "user", "content": prompt.user}]
        try:
            res = self._call(messages, model=self.model, temperature=temperature, max_tokens=max_tokens, task=task,
                             meta={**(meta or {}), "lang": variables.get("language", "en")})
        except ProviderError as e:
            self._log(task, prompt.key, prompt.version, None, "error", str(e), self.model)
            raise AIError(str(e)) from e
        self._log(task, prompt.key, prompt.version, res, "ok", None, self.model)
        return strip_reasoning(res.text)

    # ------------------------------------------------------------------ internals

    @staticmethod
    def _with_language(variables: dict) -> dict:
        lang = variables.get("language") or "en"
        return {**variables, "language": lang, "language_name": LANGUAGE_NAMES.get(lang, "English")}

    def _call(self, messages, *, model, temperature, max_tokens, task, meta) -> CompletionResult:
        start = time.perf_counter()
        res = self.provider.complete(
            messages, model=model, temperature=temperature, max_tokens=max_tokens, json_mode=True, task=task, meta=meta
        )
        res.raw["latency_ms"] = int((time.perf_counter() - start) * 1000)
        return res

    def _log(self, task, key, version, res: CompletionResult | None, status, error, model) -> None:
        if self.db is None:
            return
        s = self.settings
        cost = 0.0
        if res is not None and self.provider.name != "mock":
            cost = res.input_tokens / 1e6 * s.ai_price_input_per_m + res.output_tokens / 1e6 * s.ai_price_output_per_m
        self.db.add(
            AIRequest(
                user_id=self.user_id, task=task, provider=self.provider.name, model=res.model if res else model,
                prompt_key=key, prompt_version=version,
                input_tokens=res.input_tokens if res else 0, output_tokens=res.output_tokens if res else 0,
                cost_usd=round(cost, 6), latency_ms=res.raw.get("latency_ms", 0) if res else 0,
                status=status, error=error, response_excerpt=(res.text[:2000] if res else None),
            )
        )
        self.db.flush()
