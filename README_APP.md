# DKOR Onboard AI V1 — Runtime

Standalone web/PWA-приложение для онбординга сотрудников.

## Stack

```text
React + Vite
FastAPI
Python
TF-IDF word + char retrieval
GigaChat / Groq / OpenAI / Qwen / Local
Groq Whisper STT
Browser / OS system TTS
Docker
```

Frontend и backend в production работают как один сервис: FastAPI раздаёт собранный React и API.

## API

```text
GET    /api/health
POST   /api/chat
POST   /api/voice/transcribe
POST   /api/voice/synthesize
DELETE /api/session/{session_id}
```

## Retrieval

Используется локальный hybrid lexical retrieval: word TF-IDF + character TF-IDF.

Роль и этап пользователя не добавляются в retrieval query и передаются только как дополнительный LLM-контекст после поиска.

`07_SUCCESS_CASES_AND_DIALOGS.md` исключён из runtime retrieval.

## Providers

Поддерживаются `gigachat`, `groq`, `qwen`, `openai`, `local`, `auto`.

`auto` использует последовательный fallback согласно `AUTO_PROVIDER_ORDER`.

## Voice

Browser SpeechRecognition показывает только промежуточный live-preview.

Финальная расшифровка выполняется Groq Whisper.

Русская озвучка текущего V1 использует системный browser/OS TTS. Скорости: 1.0x / 1.25x / 1.5x.

Yandex SpeechKit остаётся опциональной backend-интеграцией и не требуется для текущего demo.

## Safety

Реализованы grounding, фильтрация неподтверждённых контактных и troubleshooting-инструкций, request-size limits, rate limiting, admin token, safe provider errors, path traversal protection и session isolation.

## Tests

Текущий baseline:

```text
33 passed
```

На Windows после успешного pytest может появляться `PermissionError ... pytest-current` во время cleanup временной папки. Он возникает уже после результата `33 passed`.

## Knowledge update

См. `docs/UPDATE_KNOWLEDGE.md`.
