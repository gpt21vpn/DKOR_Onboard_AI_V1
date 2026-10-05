"""Общие функции чтения/записи CSV. Разделитель «;», кодировка utf-8-sig: открывается в Excel и Google Sheets."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read_csv(name):
    with open(ROOT / "data" / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def write_csv(name, header, rows):
    with open(ROOT / "data" / name, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        w.writerow(header)
        for r in rows:
            w.writerow(r)
