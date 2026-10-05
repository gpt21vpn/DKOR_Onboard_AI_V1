from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.retrieval import KnowledgeIndex

ROOT=Path(__file__).resolve().parents[1]
def test_retrieval_hits_vpn():
    idx=KnowledgeIndex(str(ROOT/'knowledge'))
    hits=idx.search('не работает VPN к кому обратиться',5)
    joined=' '.join(x['text'] for x in hits)
    assert 'IT-поддержка' in joined
    assert 'VPN' in joined

def test_retrieval_hits_salary_boundary():
    idx=KnowledgeIndex(str(ROOT/'knowledge'))
    hits=idx.search('какая зарплата после испытательного срока бонус',5)
    joined=' '.join(x['text'] for x in hits)
    assert 'зарплат' in joined.lower() or 'сумм' in joined.lower()
