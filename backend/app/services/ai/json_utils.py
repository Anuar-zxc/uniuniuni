import json
import re

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def strip_reasoning(text: str) -> str:
    """Remove <think> blocks emitted by reasoning models (e.g. Qwen3) and unterminated leading ones."""
    text = _THINK_RE.sub("", text)
    if "<think>" in text.lower() and "</think>" not in text.lower():
        text = text[text.lower().index("<think>") + 7 :]
    return text.strip()


def extract_json(text: str) -> dict:
    """Best-effort extraction of the first JSON object from a model response."""
    text = strip_reasoning(text)
    fence = _FENCE_RE.search(text)
    if fence:
        text = fence.group(1).strip()
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    try:
                        value = json.loads(candidate)
                        if isinstance(value, dict):
                            return value
                    except json.JSONDecodeError:
                        # tolerate trailing commas
                        try:
                            value = json.loads(re.sub(r",\s*([}\]])", r"\1", candidate))
                            if isinstance(value, dict):
                                return value
                        except json.JSONDecodeError:
                            pass
                    break
        start = text.find("{", start + 1)
    raise ValueError("No JSON object found in model output")
