from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_prompt_has_boundaries():
    t=(ROOT/'knowledge/_system_prompt_filled.md').read_text(encoding='utf-8')
    assert 'Не называешь зарплаты' in t
    assert 'не относящиеся к адаптации' in t
    assert '{{COMPANY}}' not in t
