"""
Сборка базы знаний: data/*.csv + knowledge_src/*.md  ->  knowledge/*.md

Запуск:  python scripts/build_kb.py

Источник правды — таблицы в data/. Руками правятся CSV (или Google Таблица,
экспортированная в CSV), затем запускается этот скрипт, и файлы из knowledge/
загружаются в целевую оболочку ассистента. Так таблица и файлы знаний не расходятся.

Для настройки под другую компанию меняется data/company.json: названия,
домен, часы работы подставляются в {{ПЛЕЙСХОЛДЕРЫ}} везде, где они встречаются.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _csvio import ROOT, read_csv  # noqa: E402

COMPANY = json.loads((ROOT / "data" / "company.json").read_text(encoding="utf-8"))
PLACEHOLDER = re.compile(r"\{\{([A-Z_]+)\}\}")


def fill(text: str) -> str:
    """Подставляет значения из company.json и падает, если плейсхолдер неизвестен."""
    def repl(m):
        key = m.group(1)
        if key not in COMPANY:
            raise KeyError(f"В company.json нет ключа {key}")
        return str(COMPANY[key])
    return PLACEHOLDER.sub(repl, text)


def numbered(cell: str) -> str:
    lines = [ln.strip() for ln in cell.split("\n") if ln.strip()]
    return "\n".join(f"{i}. {ln}" for i, ln in enumerate(lines, 1))


def write(name: str, text: str) -> None:
    out = ROOT / "knowledge" / name
    out.parent.mkdir(exist_ok=True)
    out.write_text(fill(text).rstrip() + "\n", encoding="utf-8")
    print(f"  {name}: {len(out.read_text(encoding='utf-8')):>6} знаков")


def src(name: str) -> str:
    return (ROOT / "knowledge_src" / name).read_text(encoding="utf-8")


def build_company() -> str:
    base = src("01_company.md").rstrip()
    rows = read_csv("staffing_map.csv")
    table = ["## Учебная штатная карта", "", "| Функциональная зона | Человек | Комментарий |", "|---|---:|---|"]
    for r in rows:
        table.append(f"| {r['department']} | {r['headcount']} | {r['note']} |")
    table += ["", f"**Всего в учебной модели: {sum(int(r['headcount']) for r in rows)} человек.**"]
    marker = "<!-- STAFFING_TABLE -->"
    if marker not in base:
        raise RuntimeError(f"В knowledge_src/01_company.md отсутствует маркер {marker}")
    return base.replace(marker, "\n".join(table))


def build_checklists() -> str:
    rows = read_csv("checklists.csv")
    titles = {
        "before_start": "Подготовка до выхода сотрудника",
        "day1": "День 1",
        "week1": "Неделя 1",
        "month1": "Месяц 1",
        "probation_end": "Испытательный срок: контрольные точки",
        "manager_check": "Режим руководителя: что проверить у новичка",
    }
    parts = ["# 02. Общий план адаптации", "",
             "Общий план для всех ролей. Ролевые надстройки лежат в файле «04. Ролевые треки». "
             "Блок «Режим руководителя» нужен руководителю и наставнику.", ""]
    for stage, title in titles.items():
        parts.append(f"## {title}")
        parts.append("")
        for r in rows:
            if r["stage"] != stage:
                continue
            parts.append(f"- **{r['item']}**")
            parts.append(f"  - Ответственный: {r['owner']}; срок: {r['due']}")
            parts.append(f"  - Готово, когда: {r['done_criterion']}")
        parts.append("")
    return "\n".join(parts)


def build_tools() -> str:
    parts = ["# 03. Инструменты и доступы", "",
             "Инструкции по настройке рабочих инструментов. У каждого инструмента указано, "
             "куда обращаться, если не получается.", ""]
    for r in read_csv("tools_access.csv"):
        parts += [f"## {r['tool_id']}. {r['tool']}", "",
                  f"- Кому нужно: {r['used_by']}",
                  "- Как настроить:", numbered(r["setup_steps"]), "",
                  f"- Типичная проблема: {r['typical_problem']}",
                  f"- Куда обращаться: {r['escalate_to']}", ""]
    return "\n".join(parts)


def build_roles() -> str:
    parts = ["# 04. Ролевые треки", "",
             "Ролевая надстройка добавляется к общему плану адаптации. Роль определяется по словам "
             "сотрудника: если названа должность из списка «Должности», применяется соответствующий трек.", ""]
    for r in read_csv("role_tracks.csv"):
        parts += [f"## {r['track_id']}. {r['track']}", "",
                  f"- Должности: {r['roles']}",
                  "- Что добавляется к первой неделе:", numbered(r["first_week_extra"]), "",
                  f"- Инструменты: {r['tools']}",
                  f"- Первое задание: {r['first_task']}",
                  f"- Наставник из числа: {r['mentor_from']}",
                  f"- Типичные ошибки новичков: {r['typical_mistakes']}",
                  f"- Куда обращаться: {r['escalate_to']}", ""]
    return "\n".join(parts)


def build_processes() -> str:
    parts = ["# 05. Документы и процессы", "",
             "Внутренние процессы компании: у каждого есть ответственный отдел, срок реакции "
             "и условие, когда вопрос нужно передать человеку.", ""]
    for r in read_csv("processes.csv"):
        parts += [f"## {r['process_id']}. {r['name']}", "",
                  f"- Для кого: {r['audience']}",
                  f"- Типичный вопрос: {r['typical_question']}",
                  "- Шаги:", numbered(r["steps"]), "",
                  f"- Ответственный: {r['owner']}",
                  f"- Целевой срок процесса: {r['process_target']}",
                  f"- Когда передавать человеку: {r['escalation_if']}", ""]
    return "\n".join(parts)


def build_escalation() -> str:
    parts = [src("06_escalation_rules.md").rstrip(), ""]
    for r in read_csv("departments.csv"):
        parts += [f"### {r['department']}", "",
                  f"- Должности: {r['roles']}",
                  f"- За что отвечает: {r['responsibility']}",
                  f"- Контакт: {r['contact']}",
                  f"- Ориентир ответа подразделения: {r['reply_target']}",
                  f"- Передавать, когда: {r['escalate_when']}", ""]
    return "\n".join(parts)


def main() -> int:
    print("Сборка базы знаний:")
    write("01_COMPANY_AND_STRUCTURE.md", build_company())
    write("02_COMMON_ONBOARDING.md", build_checklists())
    write("03_TOOLS_AND_ACCESS.md", build_tools())
    write("04_ROLE_TRACKS.md", build_roles())
    write("05_DOCUMENTS_AND_PROCESSES.md", build_processes())
    write("06_ESCALATION_AND_CONTACTS.md", build_escalation())
    write("07_SUCCESS_CASES_AND_DIALOGS.md", src("07_cases_and_dialogs.md"))

    prompt = ROOT / "system_prompt.md"
    prompt_out = ROOT / "knowledge" / "_system_prompt_filled.md"
    prompt_out.write_text(fill(prompt.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"  system_prompt (Instructions, не Knowledge): "
          f"{len(prompt_out.read_text(encoding='utf-8'))} знаков")
    print("Готово. В Knowledge/Files загружаются 01–07; файл с префиксом _ используется как Instructions и отдельно не загружается.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
