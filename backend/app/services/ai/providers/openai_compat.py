"""OpenAI-compatible chat completions (OpenAI, alem.ai, vLLM, Ollama, LM Studio, ...)."""

import httpx

from app.services.ai.providers.base import CompletionResult, LLMProvider, ProviderError, estimate_tokens


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: str | None,
        timeout: float = 90.0,
        supports_json_mode: bool = True,
        disable_thinking: bool = False,
    ) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.supports_json_mode = supports_json_mode
        self.disable_thinking = disable_thinking

    def complete(self, messages, *, model, temperature=0.2, max_tokens=1500, json_mode=False, task="chat", meta=None):
        if not self.api_key:
            raise ProviderError(f"{self.name}: API key is not configured")
        msgs = [dict(m) for m in messages]
        if self.disable_thinking and model.lower().startswith("qwen3"):
            # Qwen3 soft switch: skip the <think> phase for faster, cleaner structured output.
            for m in reversed(msgs):
                if m["role"] == "user":
                    m["content"] = m["content"] + "\n/no_think"
                    break
        body: dict = {"model": model, "messages": msgs, "temperature": temperature, "max_tokens": max_tokens}
        if json_mode and self.supports_json_mode:
            body["response_format"] = {"type": "json_object"}
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                json=body,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout,
            )
        except httpx.HTTPError as e:
            raise ProviderError(f"{self.name}: network error: {e}") from e
        if resp.status_code >= 400:
            raise ProviderError(f"{self.name}: HTTP {resp.status_code}: {resp.text[:300]}")
        try:
            data = resp.json()
            text = data["choices"][0]["message"]["content"] or ""
        except (ValueError, KeyError, IndexError) as e:
            raise ProviderError(f"{self.name}: unexpected response shape") from e
        usage = data.get("usage") or {}
        prompt_text = " ".join(m["content"] for m in msgs)
        return CompletionResult(
            text=text,
            model=data.get("model", model),
            provider=self.name,
            input_tokens=int(usage.get("prompt_tokens") or estimate_tokens(prompt_text)),
            output_tokens=int(usage.get("completion_tokens") or estimate_tokens(text)),
        )
