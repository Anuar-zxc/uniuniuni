import httpx

from app.services.ai.providers.base import CompletionResult, LLMProvider, ProviderError


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str | None, timeout: float = 90.0) -> None:
        self.api_key = api_key
        self.timeout = timeout

    def complete(self, messages, *, model, temperature=0.2, max_tokens=1500, json_mode=False, task="chat", meta=None):
        if not self.api_key:
            raise ProviderError("gemini: API key is not configured")
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        contents = [
            {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
            for m in messages
            if m["role"] != "system"
        ]
        gen_cfg: dict = {"temperature": temperature, "maxOutputTokens": max_tokens}
        if json_mode:
            gen_cfg["responseMimeType"] = "application/json"
        body: dict = {"contents": contents, "generationConfig": gen_cfg}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        try:
            resp = httpx.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                params={"key": self.api_key},
                json=body,
                timeout=self.timeout,
            )
        except httpx.HTTPError as e:
            raise ProviderError(f"gemini: network error: {e}") from e
        if resp.status_code >= 400:
            raise ProviderError(f"gemini: HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        try:
            text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
        except (KeyError, IndexError) as e:
            raise ProviderError("gemini: unexpected response shape") from e
        usage = data.get("usageMetadata") or {}
        return CompletionResult(
            text=text,
            model=model,
            provider=self.name,
            input_tokens=int(usage.get("promptTokenCount", 0)),
            output_tokens=int(usage.get("candidatesTokenCount", 0)),
        )
