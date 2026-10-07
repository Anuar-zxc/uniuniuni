"""Deterministic analysers. Used three ways:
1. as the offline `mock` provider (no API keys needed),
2. as a fallback when the LLM fails or returns invalid output,
3. as an independent signal in the evaluation consistency layer ("don't trust a single LLM output").
"""

import re

from app.schemas.ai import (
    AnswerEvaluationAI,
    BulletQuestions,
    JobAnalysisAI,
    ResumeAnalysisAI,
    ResumeScores,
)
from app.services.skills_catalog import extract_skills, infer_family

WORD_RE = re.compile(r"[\w#+.-]+", re.UNICODE)
IDK_RE = re.compile(
    r"(не знаю|не помню|понятия не имею|затрудняюсь|don'?t know|do not know|no idea|not sure|"
    r"білмеймін|білмеймiн|есімде жоқ|pass)",
    re.IGNORECASE,
)
EXAMPLE_RE = re.compile(
    r"(for example|for instance|e\.g\.|например|к примеру|мысалы|in my (last |previous )?(project|job|team)|"
    r"в (моём|моем|нашем) проекте|на (прошлой|предыдущей) работе|we used|мы использовали|біз қолдандық|\d+\s?(%|ms|мс|rps|x))",
    re.IGNORECASE,
)
STOP = {
    "the", "and", "for", "with", "that", "this", "what", "when", "how", "why", "from", "into", "your",
    "что", "как", "это", "для", "при", "или", "его", "она", "они", "чем", "если",
}


def words(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def _stems(text: str) -> set[str]:
    return {w[:5] for w in words(text) if len(w) > 3 and w not in STOP}


# --------------------------------------------------------------------------- resume

BULLET_RE = re.compile(r"^\s*(?:[-•*▪●–]|\d+[.)])\s+(.+)$")
METRIC_RE = re.compile(r"\d+(?:[.,]\d+)?\s?(%|x|k|m|ms|мс|rps|users|пользоват|клиент|раз|млн|тыс)", re.IGNORECASE)
YEARS_RE = re.compile(r"(\d{1,2})\+?\s*(?:years|year|лет|года|год|жыл)", re.IGNORECASE)
RANGE_RE = re.compile(r"(20\d{2}|19\d{2})\s*[-–—]\s*(20\d{2}|19\d{2}|present|now|настоящее|по н\.в\.|н\.в\.|қазір)", re.I)
SECTIONS = {
    "experience": r"(experience|опыт работы|опыт|тәжірибе)",
    "education": r"(education|образование|білім)",
    "skills": r"(skills|навыки|технологии|stack|дағдылар)",
    "projects": r"(projects|проекты|жобалар)",
    "contacts": r"(@|\+7|linkedin|github\.com|telegram)",
}


def resume_bullets(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        m = BULLET_RE.match(line)
        if m and len(m.group(1).split()) >= 4:
            out.append(m.group(1).strip())
    if not out:  # fall back to sentence-ish lines containing an action + tech/metric
        out = [ln.strip() for ln in text.splitlines() if 6 <= len(ln.split()) <= 40 and (METRIC_RE.search(ln) or extract_skills(ln))]
    return out[:40]


def estimate_years(text: str) -> float:
    explicit = [int(m.group(1)) for m in YEARS_RE.finditer(text) if int(m.group(1)) < 40]
    total = 0
    for m in RANGE_RE.finditer(text):
        start = int(m.group(1))
        end_raw = m.group(2)
        end = int(end_raw) if end_raw.isdigit() else 2026
        if 0 <= end - start <= 30:
            total += end - start
    candidates = explicit + ([total] if total else [])
    return float(max(candidates)) if candidates else 0.0


def seniority_from_years(years: float) -> str:
    if years < 1:
        return "intern" if years == 0 else "junior"
    if years < 3:
        return "junior"
    if years < 6:
        return "middle"
    return "senior"


def bullet_questions(bullet: str, lang: str = "en") -> list[str]:
    q = {
        "en": [
            "What exactly was the problem, and how did you discover it?",
            "What was your personal contribution versus the team's?",
            "Which alternatives did you consider, and what were the trade-offs?",
            "How did you measure the result?",
            "What would change if the load were 10x higher?",
        ],
        "ru": [
            "В чём именно была проблема и как вы её обнаружили?",
            "Каков был ваш личный вклад, а что сделала команда?",
            "Какие альтернативы вы рассматривали и какие были trade-off'ы?",
            "Как вы измеряли результат?",
            "Что изменилось бы при нагрузке в 10 раз выше?",
        ],
        "kk": [
            "Мәселе нақты неде болды және оны қалай анықтадыңыз?",
            "Сіздің жеке үлесіңіз қандай, ал команда не істеді?",
            "Қандай баламаларды қарастырдыңыз және trade-off-тары қандай болды?",
            "Нәтижені қалай өлшедіңіз?",
            "Жүктеме 10 есе артса, не өзгерер еді?",
        ],
    }[lang if lang in ("en", "ru", "kk") else "en"]
    skills = extract_skills(bullet)
    extra = []
    if skills:
        extra.append({
            "en": f"Why {skills[0]} specifically, and what are its limitations here?",
            "ru": f"Почему именно {skills[0]} и какие у него ограничения в этом контексте?",
            "kk": f"Неге дәл {skills[0]} және мұнда оның қандай шектеулері бар?",
        }[lang if lang in ("en", "ru", "kk") else "en"])
    if METRIC_RE.search(bullet):
        return [q[0], q[3], *extra, q[2], q[4]]
    return [q[0], q[1], *extra, q[2]]


def resume_heuristics(text: str, lang: str = "en") -> ResumeAnalysisAI:
    low = text.lower()
    skills = extract_skills(text)
    bullets = resume_bullets(text)
    metric_bullets = [b for b in bullets if METRIC_RE.search(b)]
    years = estimate_years(text)
    sections_found = {k for k, pat in SECTIONS.items() if re.search(pat, low)}
    n_words = len(words(text))

    ats = 30 + 10 * len(sections_found) + min(20, len(skills) * 2)
    if n_words < 150:
        ats -= 15
    if n_words > 1200:
        ats -= 10
    technical = min(100, 25 + len(skills) * 5 + (10 if any(s in skills for s in ("System Design", "Kubernetes", "Kafka")) else 0))
    impact = min(100, 20 + (len(metric_bullets) / max(1, len(bullets))) * 60 + min(20, len(metric_bullets) * 5))
    avg_bullet = sum(len(b.split()) for b in bullets) / max(1, len(bullets))
    clarity = 70 - abs(avg_bullet - 18) * 1.5 + (10 if bullets else -20)
    experience = min(100, 15 + years * 12)

    missing = []
    if "contacts" not in sections_found:
        missing.append({"ru": "Нет контактов (email, телефон, LinkedIn/GitHub)", "kk": "Байланыс деректері жоқ", "en": "No contact details"}.get(lang, "No contact details"))
    if not metric_bullets:
        missing.append({"ru": "Нет измеримых результатов (%, время, пользователи)", "kk": "Өлшенетін нәтижелер жоқ", "en": "No measurable results (%, time, users)"}.get(lang, "No measurable results"))
    if "education" not in sections_found:
        missing.append({"ru": "Не указано образование", "kk": "Білімі көрсетілмеген", "en": "Education is missing"}.get(lang, "Education is missing"))

    suspicious = [b for b in metric_bullets if re.search(r"\b(9\d|[1-9]\d{2,})\s?%", b)][:3]
    picked = (metric_bullets + [b for b in bullets if b not in metric_bullets])[:5]

    return ResumeAnalysisAI(
        headline=None,
        seniority=seniority_from_years(years),
        years_experience=years,
        role_family=infer_family(skills),
        technologies=skills,
        achievements=metric_bullets[:6],
        weak_areas=[],
        missing_information=missing,
        suspicious_claims=suspicious,
        measurable_impact=metric_bullets[:6],
        scores=ResumeScores(ats=ats, technical=technical, impact=impact, clarity=clarity, experience=experience),
        likely_questions=[BulletQuestions(bullet=b, questions=bullet_questions(b, lang)) for b in picked],
    )


# --------------------------------------------------------------------------- job

NICE_RE = re.compile(r"(nice to have|will be a plus|would be a plus|bonus|плюсом|будет плюсом|желательно|артықшылық)", re.I)
LEVEL_RE = [
    ("lead", r"\b(lead|тимлид|team lead|principal|staff)\b"),
    ("senior", r"\b(senior|сеньор|синьор|старший)\b"),
    ("middle", r"\b(middle|mid-level|мидл|миддл)\b"),
    ("junior", r"\b(junior|джун|младший|intern|стажер|стажёр)\b"),
]


def job_heuristics(text: str) -> JobAnalysisAI:
    m = NICE_RE.search(text)
    must_text, nice_text = (text[: m.start()], text[m.start():]) if m else (text, "")
    must = extract_skills(must_text)
    nice = [s for s in extract_skills(nice_text) if s not in must]
    level = next((lvl for lvl, pat in LEVEL_RE if re.search(pat, text, re.I)), None)
    title_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")[:120]
    family = infer_family(must + nice)
    stages = ["Recruiter screen", "Technical interview"]
    if level in ("middle", "senior", "lead") or "System Design" in must:
        stages.append("System design")
    stages.append("Behavioral / team fit")
    diff = {"junior": 2, "middle": 3, "senior": 4, "lead": 5}.get(level or "", 3)
    return JobAnalysisAI(
        title=title_line or None,
        level=level,
        role_family=family,
        must_have=must,
        nice_to_have=nice,
        interview_topics=must[:8],
        likely_stages=stages,
        expected_difficulty=diff,
    )


# --------------------------------------------------------------------------- answer evaluation


def severity_for(score: float) -> str:
    if score >= 75:
        return "low"
    if score >= 55:
        return "medium"
    if score >= 35:
        return "high"
    return "critical"


def evaluate_heuristic(
    *, question: str, answer: str, ideal_points: list[str], category: str, followups_so_far: int = 0
) -> AnswerEvaluationAI:
    text = answer.strip()
    ws = words(text)
    n = len(ws)
    low = text.lower()
    if n < 4 or (IDK_RE.search(low) and n < 25):
        return AnswerEvaluationAI(
            score=8, correctness=5, depth=5, communication=30, technical_accuracy=5,
            missing_points=list(ideal_points), follow_up_needed=False, follow_up_reason="none",
            severity="critical" if category not in ("hr", "behavioral") else "high",
            mistakes=["No substantive answer given"], correct_concept="; ".join(ideal_points),
            feedback="No substantive answer.",
        )
    ans_stems = _stems(text)
    covered, missing = [], []
    for p in ideal_points:
        ps = _stems(p)
        (covered if ps and len(ps & ans_stems) / len(ps) >= 0.34 else missing).append(p)
    coverage = len(covered) / len(ideal_points) if ideal_points else min(1.0, n / 80)
    has_example = bool(EXAMPLE_RE.search(low))
    sentences = max(1, len(re.findall(r"[.!?]+", text)))

    depth = 15 + 55 * min(1.0, n / 110) + 30 * coverage
    correctness = 25 + 70 * coverage if ideal_points else 40 + 35 * min(1.0, n / 70)
    communication = 45 + (20 if sentences >= 2 else 0) + (15 if has_example else 0) - (20 if n > 300 else 0) + (10 if 25 <= n <= 220 else 0)
    technical = correctness - 5 + (10 if has_example else 0)
    if category in ("behavioral", "hr"):
        star = sum(bool(re.search(p, low)) for p in (r"(situation|ситуац|жағдай)", r"(task|задач|тапсырма)", r"(i did|я сделал|я предложил|мен|action|действ)", r"(result|результат|нәтиже|\d+%)"))
        correctness = 30 + 15 * star + (10 if has_example else 0)
        technical = correctness
    score = 0.35 * correctness + 0.25 * depth + 0.15 * communication + 0.25 * technical
    score = max(0, min(100, score))

    if score >= 80 or followups_so_far >= 2:
        need, reason = False, "none"
    elif n < 35:
        need, reason = True, "shallow"
    elif not has_example and category in ("project_deep_dive", "behavioral", "situational"):
        need, reason = True, "generic"
    elif coverage < 0.34 and ideal_points:
        need, reason = True, "error"
    elif score < 70:
        need, reason = True, "shallow"
    else:
        need, reason = followups_so_far == 0, "probe"

    return AnswerEvaluationAI(
        score=round(score, 1), correctness=correctness, depth=depth, communication=communication,
        technical_accuracy=technical, missing_points=missing, follow_up_needed=need, follow_up_reason=reason,
        severity=severity_for(score), skills_detected=extract_skills(text),
        mistakes=[] if coverage >= 0.5 else ["Key concepts were not covered"],
        correct_concept="; ".join(ideal_points),
        feedback="",
    )


# --------------------------------------------------------------------------- interviewer phrases

PHRASES: dict[str, dict[str, str]] = {
    "intro": {
        "en": "Hi! I'll be your interviewer today. We'll go through several questions, and I may ask follow-ups. Let's start.",
        "ru": "Здравствуйте! Сегодня я буду вашим интервьюером. Пройдём несколько вопросов, по ходу я могу задавать уточняющие. Начнём.",
        "kk": "Сәлеметсіз бе! Бүгін мен сіздің интервьюеріңізбін. Бірнеше сұрақтан өтеміз, қосымша сұрақтар да қоюым мүмкін. Бастайық.",
    },
    "ack": {"en": "Okay.", "ru": "Хорошо.", "kk": "Жақсы."},
    "next": {"en": "Let's move on.", "ru": "Двигаемся дальше.", "kk": "Әрі қарай жүрейік."},
    "shallow": {
        "en": "Can you go deeper? What actually happens under the hood?",
        "ru": "Можете копнуть глубже? Что на самом деле происходит под капотом?",
        "kk": "Тереңірек түсіндіріп бере аласыз ба? Ішкі жағынан шын мәнінде не болады?",
    },
    "generic": {
        "en": "Give me a concrete example from your own experience.",
        "ru": "Приведите конкретный пример из вашего опыта.",
        "kk": "Өз тәжірибеңізден нақты мысал келтіріңізші.",
    },
    "contested": {"en": "Why do you believe that?", "ru": "Почему вы так считаете?", "kk": "Неге олай деп ойлайсыз?"},
    "error": {
        "en": "Let's double-check that. Walk me through it step by step — what exactly happens?",
        "ru": "Давайте перепроверим. Пройдитесь по шагам — что именно происходит?",
        "kk": "Қайта тексеріп көрейік. Қадам-қадаммен түсіндіріңізші — нақты не болады?",
    },
    "probe": {
        "en": "What trade-offs would you consider, and what changes at 10x scale?",
        "ru": "Какие trade-off'ы вы бы учли и что изменится при нагрузке в 10 раз больше?",
        "kk": "Қандай trade-off-тарды ескерер едіңіз және жүктеме 10 есе өссе не өзгереді?",
    },
    "closing": {
        "en": "Thank you, that's all from my side. Your report is being prepared.",
        "ru": "Спасибо, с моей стороны всё. Готовлю ваш отчёт.",
        "kk": "Рақмет, менің тарапымнан бәрі осы. Есебіңізді дайындап жатырмын.",
    },
}


def phrase(key: str, lang: str) -> str:
    table = PHRASES[key]
    return table.get(lang) or table["en"]
