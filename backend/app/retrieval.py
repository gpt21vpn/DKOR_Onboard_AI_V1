from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

@dataclass
class Chunk:
    source: str
    section: str
    chunk_id: str
    text: str

class KnowledgeIndex:
    def __init__(self, knowledge_dir: str):
        self.knowledge_dir = Path(knowledge_dir)
        self.chunks: list[Chunk] = []
        self.word_vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1,2), token_pattern=r'(?u)\b[\w-]{2,}\b', sublinear_tf=True)
        self.char_vectorizer = TfidfVectorizer(lowercase=True, analyzer='char_wb', ngram_range=(3,5), min_df=1, sublinear_tf=True)
        self.word_matrix = None
        self.char_matrix = None
        self.rebuild()

    def rebuild(self):
        self.chunks = []
        for path in sorted(self.knowledge_dir.glob('[0-9][0-9]_*.md')):
            # ???? 07 ???????? ??????? ???????? ? ????? ?????? ??? reference,
            # ?? ?? ?????? ????????????? ? ???????????? ????????? ? retrieval.
            if path.name == '07_SUCCESS_CASES_AND_DIALOGS.md':
                continue
            self.chunks.extend(self._parse_file(path))
        corpus = [f'{c.section}\n{c.text}' for c in self.chunks]
        if corpus:
            self.word_matrix = self.word_vectorizer.fit_transform(corpus)
            self.char_matrix = self.char_vectorizer.fit_transform(corpus)
        return len(self.chunks)

    def _parse_file(self, path: Path) -> list[Chunk]:
        text = path.read_text(encoding='utf-8')
        lines = text.splitlines()
        out=[]; section=path.stem; buf=[]; idx=0
        def flush():
            nonlocal buf, idx
            body='\n'.join(buf).strip()
            if body and len(body) >= 40:
                idx += 1
                out.append(Chunk(path.name, section, f'{path.stem}:{idx:03d}', body))
            buf=[]
        for line in lines:
            if line.startswith('## '):
                flush(); section=line[3:].strip(); buf=[line]
            elif line.startswith('### '):
                # keep level-3 headings with the following content but split long sections
                if len('\n'.join(buf)) > 1400: flush()
                section=line[4:].strip(); buf.append(line)
            else:
                buf.append(line)
                if len('\n'.join(buf)) > 2200: flush()
        flush()
        return out

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        if not self.chunks or self.word_matrix is None:
            return []
        q_word=self.word_vectorizer.transform([query])
        q_char=self.char_vectorizer.transform([query])
        ws=cosine_similarity(q_word, self.word_matrix)[0]
        cs=cosine_similarity(q_char, self.char_matrix)[0]
        scores=0.68*ws + 0.32*cs
        ids=np.argsort(scores)[::-1][:max(top_k,1)]
        result=[]
        for i in ids:
            c=self.chunks[int(i)]
            result.append({'source':c.source,'section':c.section,'chunk_id':c.chunk_id,'text':c.text,'score':float(scores[int(i)])})
        return result
