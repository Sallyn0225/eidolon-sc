"""CJK 2-gram + ASCII whole-word tokenization, FTS5 safe query building, and RRF fusion.

Zero external dependencies: runs on SQLite FTS5 with the built-in ``unicode61``
tokenizer. Continuous Chinese/Japanese runs (hiragana, katakana, kanji) are split into
overlapping 2-grams (runs of length <= 2 are kept as-is), instead of SQLite's native
``trigram`` tokenizer which misses two-character idol names and terms such as ``真乃`` or
``灯織``, and instead of ``jieba`` which does not handle the corpus's ~2,700 untranslated
Japanese scripts. Continuous ASCII letters and digits are kept as lowercased whole
words so identifiers like ``W.I.N.G.`` and ``L'Antica`` stay searchable.

Stopwords are never stripped at index time (stripping them skews BM25 length
normalization and term frequency); only query tokens drop high-frequency Chinese and
Japanese functional words before deduplicating and joining as double-quoted ``OR``
clauses.
"""

import re
import sqlite3
import threading
import unicodedata
from collections.abc import Callable, Collection, Hashable, Sequence
from typing import TypeVar, cast

from eidolon import database

RRF_K = 15
"""Smoothing constant for Reciprocal Rank Fusion over top-N per-source lists."""

T = TypeVar("T")

_CJK_CHARS = (
    r"\u3005-\u3007"  # 々, 〆, 〇
    r"\u3041-\u3096\u309d-\u309f"  # hiragana
    r"\u30a1-\u30fa\u30fc-\u30ff"  # katakana (excludes ゠ and ・)
    r"\u31f0-\u31ff"  # katakana phonetic extensions
    r"\u3400-\u4dbf"  # CJK Extension A
    r"\u4e00-\u9fff"  # CJK Unified Ideographs
    r"\uf900-\ufaff"  # CJK Compatibility Ideographs
)
_SEGMENT = re.compile(rf"[{_CJK_CHARS}]+|[A-Za-z0-9]+")

STOPWORDS: frozenset[str] = frozenset(
    {
        # Chinese 1-char particles, pronouns, copula, auxiliaries, interjections
        "的", "了", "吗", "呢", "啊", "吧", "嘛", "呀", "哦", "嗯", "哇", "哈",
        "呗", "啦", "呐", "呵", "诶", "唉", "之", "乎", "者", "也", "矣", "哉",
        "与", "和", "跟", "及", "或", "而", "但", "却", "虽", "因", "为", "以",
        "于", "在", "从", "向", "往", "对", "把", "被", "让", "给", "着", "过",
        "地", "得", "是", "有", "没", "不", "很", "太", "更", "最", "都", "就",
        "还", "又", "再", "才", "只", "这", "那", "哪", "我", "你", "他", "她",
        "它", "们", "您",
        # Chinese 2-char functional / colloquial words
        "什么", "怎么", "怎样", "如何", "多少", "几个", "哪里", "哪儿", "哪个",
        "哪些", "这个", "那个", "这些", "那些", "这样", "那样", "这么", "那么",
        "这里", "那里", "这儿", "那儿", "时候", "一下", "一些", "一点", "有点",
        "可以", "能够", "应该", "必须", "需要", "不是", "没有", "就是", "还是",
        "或者", "以及", "关于", "对于", "因为", "所以", "虽然", "但是", "可是",
        "不过", "然后", "而且", "并且", "如果", "只要", "只有", "只是", "已经",
        "刚才", "一直", "觉得", "好像", "其实", "确实", "真的", "当然", "肯定",
        "可能", "大概", "或许", "我们", "你们", "他们", "她们", "自己", "大家",
        "别人",
        # Japanese 1-char particles & auxiliaries
        "の", "は", "が", "を", "に", "へ", "で", "と", "も", "や", "か", "な",
        "ね", "よ", "わ", "さ", "ぞ", "ぜ", "し", "て", "だ",
        # Japanese 2-char functional words
        "です", "ます", "した", "して", "ない", "ある", "いる", "なる", "する",
        "こと", "もの", "それ", "これ", "あれ", "どれ", "なに", "なん", "どう",
        "なぜ", "いつ", "どこ", "だれ", "から", "まで", "より", "ほど", "だけ",
        "しか", "ので", "のに", "けど", "でも", "って", "った", "んだ", "かな",
        "よね", "だよ", "だね",
    }
)


def index_tokens(text: str) -> list[str]:
    """Tokenize `text` for indexing: CJK 2-grams (keeping <=2-char runs) and lowercased
    ASCII words, with stopwords preserved."""
    normalized = unicodedata.normalize("NFKC", text)
    tokens: list[str] = []
    for match in _SEGMENT.finditer(normalized):
        segment = match.group()
        if segment[0].isascii():
            tokens.append(segment.lower())
        elif len(segment) <= 2:
            tokens.append(segment)
        else:
            for i in range(len(segment) - 1):
                tokens.append(segment[i : i + 2])
    return tokens


def index_text(text: str) -> str:
    """Space-joined index tokens ready to store in an FTS5 ``unicode61`` column."""
    return " ".join(index_tokens(text))


def titled_text(title: str | None, text: str) -> str:
    """Combine `title` and `text` for indexing when `text` does not already begin with `title`."""
    if title and not text.startswith(title):
        return f"{title}\n{text}"
    return text


def query_tokens(text: str) -> list[str]:
    """Tokenize `text` for querying: strip stopwords and deduplicate in first-seen order."""
    seen: set[str] = set()
    tokens: list[str] = []
    for token in index_tokens(text):
        if token in STOPWORDS or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def format_fts_query(tokens: Sequence[str]) -> str | None:
    """Escape `tokens` into a double-quoted FTS5 ``OR`` query, or None if empty."""
    if not tokens:
        return None
    return " OR ".join('"' + token.replace('"', '""') + '"' for token in tokens)


def fts_query(text: str) -> str | None:
    """Tokenize `text` as a query and return a safe FTS5 ``OR`` expression, or None."""
    return format_fts_query(query_tokens(text))


def rrf_fuse(
    rankings: Sequence[Sequence[T]],
    key: Callable[[T], Hashable] | None = None,
    *,
    k: int = RRF_K,
    weights: Sequence[float] | None = None,
) -> list[tuple[T, float]]:
    """Fuse multiple ordered result lists using Reciprocal Rank Fusion
    (``score = sum(w / (k + rank))`` with 1-based ranks), deduplicating by `key`."""
    rank_weights = weights if weights is not None else [1.0] * len(rankings)
    if len(rank_weights) != len(rankings):
        raise ValueError("weights length must match rankings length")
    scores: dict[Hashable, float] = {}
    items: dict[Hashable, T] = {}
    for ranking, weight in zip(rankings, rank_weights, strict=True):
        seen: set[Hashable] = set()
        for rank, item in enumerate(ranking, start=1):
            item_key = key(item) if key is not None else cast(Hashable, item)
            if item_key in seen:
                continue
            seen.add(item_key)
            items.setdefault(item_key, item)
            scores[item_key] = scores.get(item_key, 0.0) + weight / (k + rank)
    ordered = sorted(scores, key=lambda item_key: scores[item_key], reverse=True)
    return [(items[item_key], scores[item_key]) for item_key in ordered]


class MemoryFtsIndex:
    """Lightweight in-memory SQLite FTS5 index built once from a document list."""

    def __init__(self, texts: Sequence[str], kinds: Sequence[str] | None = None) -> None:
        self._lock = threading.Lock()
        self._db: sqlite3.Connection | None = None
        if not texts:
            if kinds is not None and len(kinds) != 0:
                raise ValueError("kinds length must match texts length")
            return
        if kinds is None:
            rows = [(i, index_text(text), "") for i, text in enumerate(texts)]
        else:
            rows = [
                (i, index_text(text), kind)
                for i, (text, kind) in enumerate(zip(texts, kinds, strict=True))
            ]
        db = database.memory()
        try:
            db.execute(
                "CREATE VIRTUAL TABLE docs USING fts5("
                "tokens, kind UNINDEXED, tokenize='unicode61', detail='column')"
            )
            db.executemany("INSERT INTO docs(rowid, tokens, kind) VALUES (?, ?, ?)", rows)
        except BaseException:
            db.close()
            raise
        self._db = db

    def search(
        self, query: str, limit: int, kinds: Collection[str] | None = None
    ) -> list[tuple[int, float]]:
        """Return ``(doc_index, score)`` best-first, optionally filtered to `kinds`."""
        if self._db is None or limit <= 0:
            return []
        kind_list = list(kinds) if kinds is not None else None
        if kind_list is not None and not kind_list:
            return []
        match = fts_query(query)
        if match is None:
            return []
        with self._lock:
            if self._db is None:
                return []
            if kind_list is None:
                rows = self._db.execute(
                    "SELECT rowid, 0.0 - bm25(docs) FROM docs"
                    " WHERE docs MATCH ? ORDER BY bm25(docs) LIMIT ?",
                    (match, limit),
                ).fetchall()
            else:
                placeholders = ", ".join("?" for _ in kind_list)
                rows = self._db.execute(
                    f"SELECT rowid, 0.0 - bm25(docs) FROM docs"
                    f" WHERE docs MATCH ? AND kind IN ({placeholders})"
                    f" ORDER BY bm25(docs) LIMIT ?",
                    (match, *kind_list, limit),
                ).fetchall()
        return [(int(rowid), float(score)) for rowid, score in rows]

    def close(self) -> None:
        with self._lock:
            if self._db is not None:
                self._db.close()
                self._db = None


