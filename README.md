# OfferReady

AI Interview Coach: «Don't just prepare for interviews. Train for your offer.»

CV + вакансия → анализ кандидата → прогноз интервью → реалистичное AI-интервью с follow-up → оценка → Error Memory → персональные тренировки → ретест → Interview Readiness Score.

## Быстрый старт

```bash
cp .env.example .env          # впишите ALEM_API_KEY (или AI_PROVIDER=mock, чтобы работать без ключей)
docker compose up --build
```

- Web: http://localhost:3000
- API docs: http://localhost:8000/api/docs
- Пользователь с email из `ADMIN_EMAIL` при регистрации получает роль admin (`/admin`).

Локально без Docker:

```bash
cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt
DATABASE_URL=sqlite:///./dev.db AI_PROVIDER=mock uvicorn app.main:app --reload
cd frontend && npm install && npm run dev      # проксирует /api → http://localhost:8000
```

Тесты: `cd backend && pytest` (SQLite + mock-провайдер; сквозной сценарий от загрузки CV до ретеста и оплаты).

## Архитектура

```
frontend/  Next.js 15 (App Router, TS, Tailwind, shadcn-style UI), i18n ru/kk/en, dark/light
backend/   FastAPI + SQLAlchemy 2 + Pydantic 2, PostgreSQL, Redis (rate limit), S3/MinIO
  app/api/v1/        routes: auth, profile, resumes, jobs, interviews, progress, billing, ai, admin, orgs
  app/models/        User, Profile, Resume, Job, Application, Interview, InterviewSession, InterviewQuestion,
                     InterviewAnswer, InterviewEvaluation, Skill, UserSkill, Weakness, TrainingPlan, TrainingTask,
                     ReadinessSnapshot, Company, Role, Question, Prompt, AIRequest, Plan, Subscription, Payment,
                     Organization, Usage, AuditLog, Event
  app/services/      бизнес-логика (см. ниже)
  app/repositories/  доступ к данным с проверкой владельца
```

Ключевые сервисы:

| Модуль | Что делает |
|---|---|
| `ai/gateway.py` | Единая точка вызова LLM: провайдеры (alem / openai / anthropic / gemini / mock), версии промптов из БД, извлечение JSON, валидация строгими схемами, одна попытка «починки», детерминированный fallback, логирование токенов/стоимости/ошибок |
| `ai/prompts.py` | Промпты по умолчанию (v1); новые версии и активация — в админке |
| `resume_service.py` | Парсинг PDF/DOCX/TXT, анализ CV, смешивание оценок LLM с детерминированными сигналами, автозаполнение профиля |
| `job_service.py`, `prediction.py` | Требования вакансии, объяснимый Job Match (strong/weak/missing), Interview Blueprint |
| `interview_engine.py` | План интервью, вопросы как у живого интервьюера, follow-up (shallow/generic/contested/error/probe), адаптивная сложность, повторная проверка слабых мест |
| `evaluation.py` | Evaluation consistency layer: медиана нескольких оценок, кросс-проверка с подоценками, независимая эвристика, ограничение для «не знаю», выведение severity |
| `weakness_service.py` | Error Memory: попытки, первая/текущая оценка, статус, интервальные ретесты (1/3/7/14/30 дней) |
| `training_service.py` | План по дням из слабых мест; каждая задача заканчивается оцениваемой проверкой |
| `readiness.py` | Readiness: веса роли и уровня, recency-взвешивание, поправка на сложность, байесовское сжатие для неизученных категорий, штраф за критичные слабости, Job Match; топ-3 риска |
| `billing/` | Абстракция PaymentProvider: sandbox, Stripe; интерфейсы Kaspi / Freedom Pay / Halyk / Paddle; идемпотентные webhooks; цены в KZT/USD |

## LLM

По умолчанию — alem.ai (`https://llm.alem.ai/v1`, модель `qwen3-8`, OpenAI-совместимый API). Для Qwen3 автоматически добавляется `/no_think`, а `<think>`-блоки вырезаются. Смена провайдера — переменная `AI_PROVIDER`. Без ключей (`AI_PROVIDER=mock`) продукт работает полностью на детерминированных анализаторах.

## Безопасность и данные

httpOnly-cookie сессии (JWT), bcrypt, RBAC (user/admin, org manager), rate limiting (Redis), валидация загрузок по magic bytes и размеру, шифрование CV at rest (Fernet), audit log, экспорт и удаление всех данных пользователя (`/profile/export`, `DELETE /profile`). Ключи только в `.env`.

## Что дальше (после валидации MVP)

Серверный STT/TTS для voice mode (сейчас — Web Speech API браузера), браузерная IDE с запуском кода, company-specific симуляции, LinkedIn-оптимизация, CV tailoring, интеграции Kaspi / Freedom Pay по договорам мерчанта, Alembic-миграции для prod.
