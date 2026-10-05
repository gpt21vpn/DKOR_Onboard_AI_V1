# Обновление базы знаний DKOR Onboard

V1 использует version-controlled Knowledge.

## Если появился новый документ или изменились правила

1. Перенесите нужные факты в соответствующий источник в `knowledge_src/`, CSV/JSON или `company.json`.
2. Не добавляйте реальные персональные данные, пароли, API-ключи, банковские данные и приватные клиентские материалы.
3. Пересоберите Knowledge:

```powershell
.\.venv\Scripts\python.exe .\scripts\build_kb.py
```

4. Выполните валидацию:

```powershell
.\.venv\Scripts\python.exe .\scripts\validate_kb.py
```

5. Запустите regression tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests
```

Текущий standalone baseline: `33 passed`.

6. Выполните короткий ручной smoke-test.
7. Сделайте Git commit/push.
8. После deployment новая версия Knowledge попадёт в приложение.

## Почему в V1 нет публичной кнопки Upload

Knowledge статична, проверяется перед публикацией и хранится вместе с кодом.

Простое сохранение загруженного файла на локальный диск облачного контейнера не даёт надёжного постоянного хранения после restart/redeploy.

Кроме того, автоматическое включение произвольного файла в RAG без проверки создаёт риск противоречащих фактов, секретов, персональных данных и prompt injection.

Для V1.1 правильная схема: admin authorization -> persistent object storage -> parser -> security validation -> human approval -> reindex -> version rollback.
