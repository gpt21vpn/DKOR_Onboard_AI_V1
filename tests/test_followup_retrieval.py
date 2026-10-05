from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.chat import _build_retrieval_query
from app.retrieval import KnowledgeIndex

ROOT = Path(__file__).resolve().parents[1]


VPN = "\u041d\u0435 \u0440\u0430\u0431\u043e\u0442\u0430\u0435\u0442 VPN"
IT_ANSWER = "\u041e\u0431\u0440\u0430\u0442\u0438\u0442\u0435\u0441\u044c \u0432 IT"
VACATION = "\u041a\u0430\u043a \u043e\u0444\u043e\u0440\u043c\u0438\u0442\u044c \u043e\u0442\u043f\u0443\u0441\u043a?"
FOLLOWUP = "\u0410 \u043a\u0442\u043e \u0437\u0430 \u044d\u0442\u043e \u043e\u0442\u0432\u0435\u0447\u0430\u0435\u0442?"


def test_explicit_question_stays_independent():
    history = [
        {"role": "user", "content": VPN},
        {"role": "assistant", "content": IT_ANSWER},
    ]

    assert _build_retrieval_query(VACATION, history) == VACATION


def test_short_followup_uses_previous_user_question():
    history = [
        {"role": "user", "content": VPN},
        {"role": "assistant", "content": IT_ANSWER},
    ]

    query = _build_retrieval_query(FOLLOWUP, history)

    assert query == VPN


def test_vpn_followup_keeps_vpn_context():
    history = [
        {"role": "user", "content": VPN},
        {"role": "assistant", "content": IT_ANSWER},
    ]

    query = _build_retrieval_query(FOLLOWUP, history)

    idx = KnowledgeIndex(str(ROOT / "knowledge"))
    hits = idx.search(query, 5)

    assert any(
        h["section"].startswith("T06.")
        for h in hits
    )
