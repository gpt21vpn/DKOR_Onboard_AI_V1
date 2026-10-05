from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.retrieval import KnowledgeIndex

ROOT = Path(__file__).resolve().parents[1]


def test_dialog_examples_are_not_in_retrieval_index():
    idx = KnowledgeIndex(str(ROOT / "knowledge"))
    assert all(
        c.source != "07_SUCCESS_CASES_AND_DIALOGS.md"
        for c in idx.chunks
    )


def test_vpn_query_finds_vpn_section():
    idx = KnowledgeIndex(str(ROOT / "knowledge"))
    hits = idx.search("?? ???????? VPN", 5)

    assert any(
        h["section"].startswith("T06.")
        for h in hits
    )

    assert all(
        h["source"] != "07_SUCCESS_CASES_AND_DIALOGS.md"
        for h in hits
    )
