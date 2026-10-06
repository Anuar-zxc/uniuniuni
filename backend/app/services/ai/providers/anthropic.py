import httpx

from app.services.ai.providers.base import CompletionResult, LLMProvider, ProviderError


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str | None, timeout: float = 90.0) -> None:
        self.api_key = api_key
        self.timeout = timeout

    def complete(self, messages, *, model, temperature=0.2, max_tokens=1500, json_mode=False, task="chat", meta=None):
        if not self.api_key:
            raise ProviderError("anthropic: API key is not configured")
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        convo = [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] != "system"]
        try:
            resp = httpx.post(
                "https://api.anthropic.com/v1/messages",
                json={
                    "model": model,
                    "system": system,
                    "messages": convo,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
                timeout=self.timeout,
            )
        except httpx.HTTPError as e:
            raise ProviderError(f"anthropic: network error: {e}") from e
        if resp.status_code >= 400:
            raise ProviderError(f"anthropic: HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        usage = data.get("usage") or {}
        return CompletionResult(
            text=text,
            model=data.get("model", model),
            provider=self.name,
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
        )
