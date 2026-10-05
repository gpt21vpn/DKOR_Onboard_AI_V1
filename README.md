# DKOR Onboard AI V1

Учебный standalone AI-ассистент для онбординга новых сотрудников.

Проект выполнен в рамках Практики №2, ТЗ №5 курса Prompt Engineering 2026.

**Компания:** `DKORWORLD2 Studio — учебный контур`.

Все сотрудники, контакты и внутренние реквизиты в демонстрационной базе вымышлены.

## Возможности

- React/Vite интерфейс и FastAPI backend;
- локальный hybrid lexical RAG без внешней vector DB;
- 7 Knowledge-файлов, 68 runtime-чанков;
- GigaChat, Groq, OpenAI, Qwen и Local fallback;
- Auto routing между настроенными провайдерами;
- голосовой ввод: live-preview в поле ввода + финальная расшифровка Groq Whisper;
- системная русская озвучка браузера/ОС;
- скорость TTS: 1.0x / 1.25x / 1.5x, по умолчанию 1.25x;
- источники ответа в UI;
- короткая память текущей сессии в RAM;
- rate limiting, ограничения размера запросов и safe errors;
- Docker deployment одним сервисом.

## Архитектура

```text
Browser / React
      |
      v
FastAPI
      |
      +--> Session memory (RAM)
      +--> Hybrid retrieval: word TF-IDF + char TF-IDF
      +--> top-K Knowledge chunks
      +--> System Prompt + runtime grounding
      +--> Provider Router
             +--> GigaChat
             +--> Groq
             +--> Qwen
             +--> OpenAI
             +--> Local fallback
```

## Knowledge

Финальная база состоит из:

1. `01_COMPANY_AND_STRUCTURE.md`
2. `02_COMMON_ONBOARDING.md`
3. `03_TOOLS_AND_ACCESS.md`
4. `04_ROLE_TRACKS.md`
5. `05_DOCUMENTS_AND_PROCESSES.md`
6. `06_ESCALATION_AND_CONTACTS.md`
7. `07_SUCCESS_CASES_AND_DIALOGS.md`

Контрольная конфигурация:

- 57 719 знаков;
- 14 функциональных зон;
- 18 процессов;
- 14 инструментов;
- 13 ролевых треков;
- 40 пунктов чек-листов;
- 38 сотрудников в учебной модели.

`07_SUCCESS_CASES_AND_DIALOGS.md` хранится для примеров и QA, но исключён из runtime retrieval.

Роль и этап адаптации не добавляются в retrieval query: они передаются модели только после поиска как контекст пользователя.

## Grounding

Ассистент не должен придумывать контакты, сроки, суммы, статусы, документы, каналы обращения и технические процедуры, которых нет в найденном Knowledge.

Дополнительный post-processing guard удаляет отдельные неподтверждённые контактные и troubleshooting-инструкции.

## Голос

Во время диктовки browser SpeechRecognition используется только как live-preview.

После остановки записи аудио отправляется в backend, а финальную расшифровку делает Groq Whisper.

Для русской озвучки V1 использует системный TTS браузера/операционной системы. Отдельный TTS API key для этого не требуется.

## QA

Standalone regression baseline:

```text
33 passed
```

Knowledge validator:

```text
7 файлов
57 719 знаков
14 отделов
18 процессов
14 инструментов
13 ролевых треков
40 пунктов чек-листов
38 сотрудников
ошибок: 0
```

Отдельный frozen baseline Knowledge + system prompt в ChatGPT Project ранее получил:

```text
24/24 контрольных вопросов
141/144 = 98%
hallucinations: 0
stress: 5/5
blind: 6/6
```

Важно: 98% относится к тому зафиксированному QA-контуру, а не автоматически к standalone FastAPI-приложению после последующих runtime-доработок.

## Обновление базы

См. `docs/UPDATE_KNOWLEDGE.md`.

V1 не принимает новые документы через публичный upload UI. База обновляется как version-controlled часть проекта:

```text
source -> build_kb.py -> validate_kb.py -> pytest -> Git -> Render redeploy
```

Для будущей writable-версии нужен внешний persistent storage, проверка документа, подтверждение и reindex.

## Docker

Создайте локальный `.env` на основе `.env.example`, добавьте только необходимые ключи и запустите:

```powershell
docker build -t dkor-onboard .
docker run --rm -p 8015:8000 --env-file .env dkor-onboard
```

UI: `http://localhost:8015`

Health: `http://localhost:8015/api/health`

## Render

Проект подготовлен к deployment одним Docker Web Service. Dockerfile поддерживает переменную `PORT`.

Секреты задаются только через Environment Variables платформы. `.env` в Git не публикуется.

Knowledge статична и входит в Docker image, поэтому V1 не требует постоянного диска для базы.

## Безопасность

В публичный репозиторий не должны попадать:

- `.env`;
- `.private/denylist.local.json`;
- реальные API-ключи и токены;
- реальные персональные данные;
- реальные клиентские документы;
- runtime-логи и временные backup-файлы.

## Ограничения

Это учебный portfolio/demo-проект, а не production HRIS.

Telegram, UI-загрузка Knowledge, внешнее постоянное хранилище и vector DB оставлены как возможные расширения.
