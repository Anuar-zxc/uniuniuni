"""Deterministic offline provider. Lets the whole product run end-to-end without API keys (dev, CI, demos)."""

import json

from app.services import heuristics as h
from app.services.ai.providers.base import CompletionResult, LLMProvider, estimate_tokens


class MockProvider(LLMProvider):
    name = "mock"

    def complete(self, messages, *, model, temperature=0.2, max_tokens=1500, json_mode=False, task="chat", meta=None):
        meta = meta or {}
        lang = meta.get("lang", "en")
        if task == "analyze_resume":
            out = h.resume_heuristics(meta.get("resume_text", ""), lang).model_dump()
        elif task == "analyze_job":
            out = h.job_heuristics(meta.get("job_text", "")).model_dump()
        elif task == "evaluate_answer":
            out = h.evaluate_heuristic(
                question=meta.get("question", ""),
                answer=meta.get("answer", ""),
                ideal_points=meta.get("ideal_points", []),
                category=meta.get("category", "technical"),
                followups_so_far=meta.get("followups_so_far", 0),
            ).model_dump()
        elif task == "interviewer_turn":
            out = {"message": _interviewer_message(meta, lang)}
        elif task == "interview_report":
            out = _report(meta)
        elif task == "training_questions":
            out = {"questions": meta.get("fallback_questions", [])}
        else:
            out = None
        text = json.dumps(out, ensure_ascii=False) if out is not None else _chat_reply(meta, lang)
        prompt = " ".join(m["content"] for m in messages)
        return CompletionResult(
            text=text, model="mock-1", provider=self.name,
            input_tokens=estimate_tokens(prompt), output_tokens=estimate_tokens(text),
        )


def _interviewer_message(meta: dict, lang: str) -> str:
    action = meta.get("action")
    if action == "follow_up":
        return f"{h.phrase(meta.get('reason') or 'probe', lang)}"
    if action == "close":
        return h.phrase("closing", lang)
    prefix = h.phrase("intro", lang) if meta.get("first") else h.phrase("ack", lang)
    return f"{prefix} {meta.get('question_seed', '')}".strip()


def _report(meta: dict) -> dict:
    cats = []
    for cat, score in (meta.get("category_scores") or {}).items():
        items = [e for e in meta.get("evaluations", []) if e["category"] == cat]
        strengths = [f"{e['topic']}: {round(e['score'])}" for e in items if e["score"] >= 70][:3]
        weak = [f"{e['topic']}: {', '.join(e.get('missing_points', [])[:2]) or 'needs more depth'}" for e in items if e["score"] < 70][:3]
        recs = [f"Review {e['topic']} and practise explaining it with a concrete example." for e in items if e["score"] < 70][:3]
        cats.append({"category": cat, "strengths": strengths, "weaknesses": weak, "recommendations": recs})
    overall = meta.get("overall", 0)
    return {
        "summary": f"Overall score {round(overall)}/100. See the category breakdown for strengths and gaps.",
        "categories": cats,
        "top_recommendations": [r for c in cats for r in c["recommendations"]][:4],
    }


def _chat_reply(meta: dict, lang: str) -> str:
    return {
        "ru": "Я офлайн-режим коуча (mock). Подключите LLM-провайдера, чтобы получать развёрнутые ответы.",
        "kk": "Мен коучтың офлайн режиміндемін (mock). Толық жауап алу үшін LLM провайдерін қосыңыз.",
    }.get(lang, "I'm the offline (mock) coach. Configure an LLM provider for full answers.")
