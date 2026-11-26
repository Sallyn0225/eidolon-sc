"""What a reference source is: one of the places a turn looks references up in (the
story, the character facts, the work facts), searched by vector similarity, FTS5 full-text
matching, or both fused with RRF, and reranked together.

Each source carries its kind, the heading its references go under in the prompt, the
line telling the character how to use them, and its search; and, being embedded, it can
be embedded again (`embedding.Reembeddable`). So adding one is writing it and registering
it where the sources are opened (`retrieval.open_reference_sources`).
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable, Hashable, Sequence
from dataclasses import dataclass, replace
from typing import Literal, Protocol, TypeVar

from eidolon.characters import Character
from eidolon.embedding import EmbeddingError, Reembeddable
from eidolon.text_search import RRF_K, rrf_fuse

log = logging.getLogger(__name__)

ReferenceKind = Literal["episode", "fact", "work"]

HYBRID_CANDIDATE_MULTIPLIER = 2
"""When fusing vector and FTS5 candidates in one source, each path fetches `limit *
HYBRID_CANDIDATE_MULTIPLIER` candidates before RRF fusion and truncation to `limit`."""
FTS_RRF_WEIGHT = 0.9
"""Weight applied to FTS5 rankings relative to dense vector rankings (1.0) during RRF
fusion, keeping high-precision vector top hits ahead of FTS5 noise while still lifting
dual-matched and strong FTS5-only candidates into the reranker pool."""


@dataclass(frozen=True)
class Reference:
    kind: ReferenceKind
    text: str
    origin: str
    """The episode's identifier, the fact's title (its text, if it has none), or the work
    fact's title."""
    similarity: float
    """Vector cosine similarity in vector-only searches, or RRF score in hybrid and FTS5
    searches, used to order fallback references if reranking fails."""


class ReferenceSource(Reembeddable, Protocol):
    @property
    def kind(self) -> ReferenceKind: ...

    @property
    def heading(self) -> str:
        """The heading each of its references goes under in the prompt."""
        ...

    @property
    def guide(self) -> str:
        """The line telling the character what its references are and how to use them."""
        ...

    async def search(
        self,
        query_vector: Sequence[float] | None,
        character: Character,
        limit: int,
        query: str | None = None,
    ) -> list[Reference]:
        """Its references for `character` matching `query_vector`, `query`, or both
        (fused with RRF), as many as `limit`, best first."""
        ...

    async def search_by_text(
        self, query: str, character: Character, limit: int
    ) -> list[Reference]:
        """Its references for `character` matching `query` via FTS5 BM25, best first."""
        ...


T = TypeVar("T")


def fuse_hybrid(
    vector_items: Sequence[T],
    fts_items: Sequence[T],
    limit: int,
    *,
    key: Callable[[T], Hashable],
) -> list[tuple[T, float]]:
    """Fuse vector and FTS5 rankings with weighted RRF (`RRF_K`, weighting FTS5 by
    `FTS_RRF_WEIGHT` when both paths are present) and truncate to `limit`."""
    if limit <= 0 or (not vector_items and not fts_items):
        return []
    weights = (1.0, FTS_RRF_WEIGHT) if vector_items and fts_items else None
    fused = rrf_fuse([vector_items, fts_items], key=key, k=RRF_K, weights=weights)
    return fused[:limit]


def fuse_references(
    vector_refs: Sequence[Reference],
    fts_refs: Sequence[Reference],
    limit: int,
) -> list[Reference]:
    """Fuse vector and FTS5 candidates from one source with RRF (`RRF_K`, weighting
    FTS5 by `FTS_RRF_WEIGHT` when both paths are present), keeping distinct
    passages/entries (deduplicated by `(origin, text)`) and storing the RRF score in
    `Reference.similarity`."""
    fused = fuse_hybrid(vector_refs, fts_refs, limit, key=lambda r: (r.origin, r.text))
    return [replace(ref, similarity=score) for ref, score in fused]


async def search_hybrid_references(
    vector_search: Callable[[int], Awaitable[list[Reference]]],
    text_search: Callable[[int], Awaitable[list[Reference]]],
    query_vector: Sequence[float] | None,
    query: str | None,
    limit: int,
    label: str,
) -> list[Reference]:
    """Search one reference source by vector (`query_vector`), FTS5 (`query`), or both
    in parallel fused with RRF. Empty `query` uses vector only; `query_vector=None` uses
    FTS5 only; when `query` is non-empty, `EmbeddingError` in vector search degrades that
    source to FTS5."""
    if limit <= 0:
        return []
    if not query:
        return await vector_search(limit) if query_vector is not None else []
    if query_vector is None:
        return fuse_references([], await text_search(limit), limit)
    fetch_limit = limit * HYBRID_CANDIDATE_MULTIPLIER
    fts_task = asyncio.ensure_future(text_search(fetch_limit))
    try:
        try:
            vec_refs = await vector_search(fetch_limit)
        except EmbeddingError:
            log.warning(
                "vector search failed for %s; falling back to FTS5", label, exc_info=True
            )
            fts_refs = await fts_task
            return fuse_references([], fts_refs[:limit], limit)
        fts_refs = await fts_task
        return fuse_references(vec_refs, fts_refs, limit)
    finally:
        if not fts_task.done():
            fts_task.cancel()

