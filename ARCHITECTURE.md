# Архитектура DKOR Onboard AI V1

## Production contour

```text
React / PWA
    |
    v
FastAPI
    |
    +--> Session memory (RAM)
    +--> Voice service
    +--> ChatService
            |
            v
      Hybrid lexical retrieval
      TF-IDF word + char
            |
            v
         top-K
            |
            v
 System Prompt + runtime grounding
            |
            v
      Provider Router
       |   |   |   |
       v   v   v   v
   GigaChat Groq Qwen OpenAI
            |
            +--> Local fallback
```

## Knowledge pipeline

```text
company.json + CSV/JSON + knowledge_src
                  |
                  v
          scripts/build_kb.py
                  |
                  +--> knowledge/01..07.md
                  +--> _system_prompt_filled.md
                  |
                  v
         scripts/validate_kb.py
                  |
                  v
              tests / QA
```

## Runtime retrieval

Поиск строится по вопросу пользователя. Для короткого follow-up может использоваться предыдущий содержательный вопрос.

Роль и этап адаптации не добавляются в retrieval query: они попадают только в LLM-контекст после поиска.

`07_SUCCESS_CASES_AND_DIALOGS.md` не индексируется для runtime retrieval.

## Answer flow

```text
question
   |
retrieval
   |
top-K Knowledge
   |
system prompt + runtime grounding
   |
short session history + role/stage context
   |
LLM provider
   |
post-processing guard
   |
answer + source metadata
```

Post-processing не создаёт новые факты. Он удаляет отдельные неподтверждённые контактные или технические действия.

## Voice

```text
microphone
   |
   +--> browser SpeechRecognition -> live-preview only
   |
   +--> MediaRecorder -> FastAPI -> Groq Whisper -> final transcript
```

Озвучка ответа: backend TTS, если он настроен, иначе browser/OS system TTS fallback. Скорость по умолчанию 1.25x.

## Security / demo protection

- `.env` вне Git;
- `.private/` вне Git и Docker;
- admin token;
- safe errors;
- request-size limits;
- rate limiting;
- demo budgets;
- path traversal protection;
- grounding guard;
- session isolation.

## Deployment

Multi-stage Docker image собирает React, затем запускает FastAPI, который раздаёт UI и API.

Это позволяет использовать один Render Web Service.

Knowledge V1 read-only и входит в image. Session memory и rate-limit counters находятся в RAM.
