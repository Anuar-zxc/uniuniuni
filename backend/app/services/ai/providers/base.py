from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class ProviderError(RuntimeError):
    """Raised when the upstream LLM call fails (network, auth, quota, malformed response)."""


@dataclass
class CompletionResult:
    text: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    raw: dict = field(default_factory=dict)


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    def complete(
        self,
        messages: list[dict],
        *,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        json_mode: bool = False,
        task: str = "chat",
        meta: dict | None = None,
    ) -> CompletionResult:
        """messages: [{"role": "system"|"user"|"assistant", "content": str}]"""


def estimate_tokens(text: str) -> int:
    # Rough heuristic used when the provider does not report usage.
    return max(1, len(text) // 4)
