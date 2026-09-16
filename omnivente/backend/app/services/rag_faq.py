"""RAG FAQ leger : recherche lexicale TF-IDF maison sur les reponses existantes.

Aucune dependance externe ni appel reseau : l'index est construit en memoire a
partir des entrees `faq_entries` de la base PostgreSQL du tenant courant.
"""
from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, List, Optional

STOPWORDS = {
    "le", "la", "les", "un", "une", "des", "du", "de", "d", "l", "et", "ou",
    "a", "au", "aux", "en", "pour", "par", "sur", "avec", "sans", "je", "tu",
    "il", "elle", "nous", "vous", "ils", "elles", "est", "es", "sont", "ce",
    "cette", "ces", "que", "qui", "quoi", "dans", "votre", "vos", "mon", "ma",
    "mes", "son", "sa", "ses", "bonjour", "bonsoir", "svp", "s", "il", "y",
}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower()


def tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-z0-9]+", normalize(text))
    return [t for t in tokens if len(t) > 1 and t not in STOPWORDS]


@dataclass
class FaqDocument:
    id: int
    question: str
    answer: str
    tags: str = ""

    @property
    def searchable(self) -> str:
        return f"{self.question} {self.tags}"


@dataclass
class FaqMatch:
    document: FaqDocument
    score: float


class FaqIndex:
    """Index TF-IDF + similarite cosinus."""

    def __init__(self, documents: Iterable[FaqDocument]):
        self.documents: List[FaqDocument] = list(documents)
        self._doc_tokens = [tokenize(doc.searchable) for doc in self.documents]
        self._idf: dict[str, float] = {}
        self._vectors: List[dict[str, float]] = []
        self._build()

    def _build(self) -> None:
        n_docs = len(self.documents)
        if n_docs == 0:
            return
        doc_freq: dict[str, int] = {}
        for tokens in self._doc_tokens:
            for token in set(tokens):
                doc_freq[token] = doc_freq.get(token, 0) + 1
        self._idf = {
            token: math.log((1 + n_docs) / (1 + freq)) + 1.0
            for token, freq in doc_freq.items()
        }
        for tokens in self._doc_tokens:
            self._vectors.append(self._vectorize(tokens))

    def _vectorize(self, tokens: List[str]) -> dict[str, float]:
        if not tokens:
            return {}
        counts: dict[str, float] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0.0) + 1.0
        vector = {
            token: (count / len(tokens)) * self._idf.get(token, 1.0)
            for token, count in counts.items()
        }
        norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
        return {token: value / norm for token, value in vector.items()}

    def search(self, query: str, top_k: int = 3) -> List[FaqMatch]:
        if not self.documents:
            return []
        query_vector = self._vectorize(tokenize(query))
        if not query_vector:
            return []
        scored: List[FaqMatch] = []
        for doc, vector in zip(self.documents, self._vectors):
            score = sum(weight * vector.get(token, 0.0) for token, weight in query_vector.items())
            if score > 0:
                scored.append(FaqMatch(document=doc, score=round(score, 4)))
        scored.sort(key=lambda match: match.score, reverse=True)
        return scored[:top_k]

    def best_answer(self, query: str, threshold: float = 0.18) -> Optional[FaqMatch]:
        matches = self.search(query, top_k=1)
        if matches and matches[0].score >= threshold:
            return matches[0]
        return None
