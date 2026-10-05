import json
"""
Проверка базы знаний перед загрузкой в Custom GPT.

Запуск:  python scripts/build_kb.py && python scripts/validate_kb.py

Что проверяется:
  1. структура таблиц: нужные колонки, нет пустых обязательных ячеек, ID не повторяются;
  2. связность: ответственные и адреса эскалации существуют в справочнике отделов;
  3. утечки реальных данных: настоящие телефоны, e-mail не на .example, ссылки,
     суммы в рублях, номера документов, а также чёрный список слов из DENYLIST;
  4. лимиты: число файлов в Knowledge и длина системного промпта;
  5. что не осталось нераскрытых {{плейсхолдеров}}.

Код возврата 0 — всё чисто, 1 — есть ошибки.
"""

import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _csvio import ROOT, read_csv  # noqa: E402

# ТЗ №5 требует вымышленных данных. Всё, что относится к реальным людям, компаниям
# и серверам, сюда не должно попасть. Список пополняйте своими «опасными» словами.
_DENYLIST_LOCAL_PATH = (
    Path(__file__).resolve().parents[1]
    / ".private"
    / "denylist.local.json"
)

def _load_local_denylist():
    if not _DENYLIST_LOCAL_PATH.exists():
        return list()

    try:
        raw = json.loads(
            _DENYLIST_LOCAL_PATH.read_text(encoding="utf-8")
        )
    except Exception as exc:
        raise RuntimeError(
            "Local denylist file is invalid"
        ) from exc

    if not isinstance(raw, list) or not all(
        isinstance(x, str) for x in raw
    ):
        raise RuntimeError(
            "Local denylist must be a JSON array of strings"
        )

    return list(raw)

DENYLIST = _load_local_denylist()
ALLOWED_EXTRA_OWNERS = {"Наставник", "Руководитель отдела", "Руководитель проектов",
                        "Новичок", "Руководитель отдела и HR"}
EXPECTED_KNOWLEDGE_FILES = 7
PROMPT_CHAR_BUDGET = 7500  # внутренний бюджет проекта, а не заявленный лимит платформы

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def check_columns(name: str, rows: list[dict], required: list[str], id_col: str) -> None:
    if not rows:
        err(f"{name}: таблица пустая")
        return
    missing = [c for c in required if c not in rows[0]]
    if missing:
        err(f"{name}: нет колонок {missing}")
        return
    seen = set()
    for i, r in enumerate(rows, 2):
        for c in required:
            if not (r.get(c) or "").strip():
                err(f"{name}, строка {i}: пустая ячейка «{c}»")
        key = r[id_col]
        if key in seen:
            err(f"{name}: повторяется {id_col} = {key}")
        seen.add(key)


def main() -> int:
    deps = read_csv("departments.csv")
    procs = read_csv("processes.csv")
    tools = read_csv("tools_access.csv")
    roles = read_csv("role_tracks.csv")
    checks = read_csv("checklists.csv")
    staffing = read_csv("staffing_map.csv")
    questions = read_csv("../eval/questions.csv")

    check_columns("departments.csv", deps, ["dept_id", "department", "roles", "responsibility", "contact", "reply_target", "escalate_when"], "dept_id")
    check_columns("processes.csv", procs, ["process_id", "name", "audience", "typical_question", "steps", "owner", "process_target", "escalation_if"], "process_id")
    check_columns("tools_access.csv", tools, ["tool_id", "tool", "used_by", "setup_steps", "typical_problem", "escalate_to"], "tool_id")
    check_columns("role_tracks.csv", roles, ["track_id", "track", "roles", "first_week_extra", "tools", "first_task", "mentor_from", "typical_mistakes", "escalate_to"], "track_id")
    check_columns("checklists.csv", checks, ["checklist_id", "stage", "audience", "item", "owner", "due", "done_criterion"], "checklist_id")
    check_columns("staffing_map.csv", staffing, ["dept_id", "department", "headcount", "note"], "dept_id")
    check_columns("questions.csv", questions, ["id", "category", "question", "expected", "must_not"], "id")

    dept_names = {d["department"] for d in deps}
    allowed_owners = dept_names | ALLOWED_EXTRA_OWNERS

    staffing_depts = {r["department"] for r in staffing}
    if staffing_depts != dept_names:
        missing = sorted(dept_names - staffing_depts)
        extra_staff = sorted(staffing_depts - dept_names)
        if missing:
            err(f"staffing_map.csv: нет функциональных зон из departments.csv: {missing}")
        if extra_staff:
            err(f"staffing_map.csv: неизвестные функциональные зоны: {extra_staff}")
    try:
        staff_total = sum(int(r["headcount"]) for r in staffing)
        if not (35 <= staff_total <= 45):
            err(f"staffing_map.csv: сумма штата {staff_total}, ожидается учебный диапазон 35–45")
    except ValueError:
        err("staffing_map.csv: headcount должен быть целым числом")
        staff_total = -1

    for r in procs:
        if r["owner"] not in allowed_owners:
            err(f"processes.csv {r['process_id']}: ответственный «{r['owner']}» отсутствует в справочнике отделов")
    for r in tools:
        if r["escalate_to"] not in allowed_owners:
            err(f"tools_access.csv {r['tool_id']}: «{r['escalate_to']}» отсутствует в справочнике отделов")
    for r in checks:
        if r["owner"] not in allowed_owners:
            err(f"checklists.csv {r['checklist_id']}: ответственный «{r['owner']}» отсутствует в справочнике")
    for r in deps:
        if not r["contact"].endswith("@{{DOMAIN}}"):
            err(f"departments.csv {r['dept_id']}: контакт должен быть вида имя@{{{{DOMAIN}}}}")

    # --- независимость регрессионных вопросов от образцовых диалогов ---
    dialog_src = (ROOT / "knowledge_src" / "07_cases_and_dialogs.md").read_text(encoding="utf-8")
    dialog_questions = []
    for line in dialog_src.splitlines():
        m = re.match(r"\*\*(?:Сотрудник|Новичок|Руководитель):\*\*\s*(.+)", line.strip())
        if m:
            dialog_questions.append(m.group(1).strip())

    def norm(s: str) -> str:
        s = s.lower().replace("ё", "е")
        s = re.sub(r"[^a-zа-я0-9 ]+", " ", s)
        return " ".join(s.split())

    for qr in questions:
        nq = norm(qr["question"])
        for dq in dialog_questions:
            nd = norm(dq)
            seq = SequenceMatcher(None, nq, nd).ratio()
            qset, dset = set(nq.split()), set(nd.split())
            jac = len(qset & dset) / max(1, len(qset | dset))
            containment = (len(nd.split()) >= 4 and nd in nq) or (len(nq.split()) >= 4 and nq in nd)
            if nq == nd or containment or seq >= 0.78 or jac >= 0.70:
                err(f"questions.csv {qr['id']}: тест слишком похож на образцовый диалог "
                    f"(containment={containment}, seq={seq:.2f}, jaccard={jac:.2f})")
            elif seq >= 0.62 or jac >= 0.55:
                warnings.append(f"questions.csv {qr['id']}: заметное сходство с диалогом (seq={seq:.2f}, jaccard={jac:.2f})")

    # --- проверка собранных файлов ---
    kdir = ROOT / "knowledge"
    files = sorted(p for p in kdir.glob("*.md") if not p.name.startswith("_"))
    if not files:
        err("knowledge/ пуста: сначала запустите scripts/build_kb.py")
    if len(files) != EXPECTED_KNOWLEDGE_FILES:
        err(f"В knowledge/ должно быть ровно {EXPECTED_KNOWLEDGE_FILES} файлов, сейчас {len(files)}")

    phone = re.compile(r"(?<!\d)(?:\+7|8)[\s(\-]*\d{3}[\s)\-]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}(?!\d)")
    email = re.compile(r"[\w.\-+]+@([\w\-]+\.)+[A-Za-z]{2,}")
    url = re.compile(r"https?://\S+")
    money = re.compile(r"\d[\d\s]{2,}\s?(?:₽|руб|р\.)")
    for p in files + [ROOT / "system_prompt.md"]:
        text = p.read_text(encoding="utf-8")
        for m in re.finditer(r"\{\{[A-Z_]+\}\}", text) if p.parent == kdir else []:
            err(f"{p.name}: нераскрытый плейсхолдер {m.group(0)}")
        for pat, what in ((phone, "телефон"), (url, "ссылка"), (money, "сумма в рублях")):
            for m in pat.finditer(text):
                err(f"{p.name}: найден {what}: «{m.group(0)[:40]}»")
        for m in email.finditer(text):
            if not m.group(0).lower().endswith(".example"):
                err(f"{p.name}: e-mail не на домене .example: {m.group(0)}")
        low = text.lower()
        for bad in DENYLIST:
            if bad.lower() in low:
                err(f"{p.name}: слово из чёрного списка «{bad}»")

    prompt = (kdir / "_system_prompt_filled.md")
    if prompt.exists():
        n = len(prompt.read_text(encoding="utf-8"))
        if n > PROMPT_CHAR_BUDGET:
            warnings.append(f"Системный промпт {n} знаков превышает внутренний бюджет {PROMPT_CHAR_BUDGET}")
        print(f"Системный промпт: {n} знаков (внутренний бюджет {PROMPT_CHAR_BUDGET})")

    total = sum(len(p.read_text(encoding="utf-8")) for p in files)
    print(f"Файлов знаний: {len(files)}, всего {total} знаков")
    print(f"Отделов: {len(deps)}, процессов: {len(procs)}, инструментов: {len(tools)}, "
          f"ролевых треков: {len(roles)}, пунктов чек-листов: {len(checks)}, штат: {staff_total}")

    if warnings:
        print("\nПРЕДУПРЕЖДЕНИЯ:")
        for w in warnings:
            print("  -", w)

    if errors:
        print(f"\nОШИБОК: {len(errors)}")
        for e in errors:
            print("  -", e)
        return 1
    print("\nПроверка пройдена: ошибок нет.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
