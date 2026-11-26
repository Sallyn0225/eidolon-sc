"""The work facts (every song, release and live day, shared by every character), as a
reference source.

They come from the world setting's data file (`World.entries`), not an import: they are
the work's scope of the embedded text set, embedded the first time they are searched and
kept until an entry is edited or removed, so a new data file takes effect after a restart
without any command and costs only the changed entries.

As a reference source they are searched whatever they are about; recalling how something
went searches them itself (`search_entries`), for the lives and releases only.
"""

import asyncio
import logging
from collections.abc import Callable, Collection, Sequence

from eidolon.characters import Character
from eidolon.corpus import REEMBED_BATCH
from eidolon.data_access import Database
from eidolon.embedded_texts import WORK_SCOPE, EmbeddedTexts
from eidolon.embedding import Document, Embedder, EmbeddingError
from eidolon.references import (
    HYBRID_CANDIDATE_MULTIPLIER,
    Reference,
    ReferenceKind,
    search_hybrid_references,
)
from eidolon.text_search import RRF_K, MemoryFtsIndex, fts_query, rrf_fuse, titled_text
from eidolon.world import EntryKind, World, WorldEntry

log = logging.getLogger(__name__)

WORK_RULE = "作品资料里只有名称、日期、会场、出演者这类事实，没有台上或当时具体发生了什么，不要编造。"
"""What the work facts do not tell, for every prompt that carries them."""


class WorkFacts:
    kind: ReferenceKind = "work"
    heading = "作品资料"
    guide = (
        "「作品资料」是关于歌曲、唱片和演出的事实，可以照着回答；"
        "日期在今天之后的，是还没发售或还没举办的。" + WORK_RULE
    )
    label = "作品资料"
    unit = "条"

    def __init__(self, db: Database, embedder: Embedder, world: World | None) -> None:
        """Without `world` (no data file), there are no work facts: any vectors stored
        for the embedder's model are forgotten the first time they are searched."""
        self._texts = EmbeddedTexts(db, embedder)
        self._entries = list({e.text: e for e in (world.entries() if world else [])}.values())
        self._documents = [Document(e.text, e.title) for e in self._entries]
        self._fts: MemoryFtsIndex | None = None
        self._fts_lock = asyncio.Lock()

    async def search(
        self,
        query_vector: Sequence[float] | None,
        character: Character,
        limit: int,
        query: str | None = None,
    ) -> list[Reference]:
        return await search_hybrid_references(
            lambda n: self._search_by_vector(
                query_vector if query_vector is not None else (), n
            ),
            lambda n: self.search_by_text(query or "", character, n),
            query_vector,
            query,
            limit,
            self.label,
        )

    async def _search_by_vector(
        self, query_vector: Sequence[float], limit: int
    ) -> list[Reference]:
        return [
            Reference(self.kind, e.text, e.title, similarity)
            for e, similarity in await self._nearest(query_vector, limit)
        ]

    async def search_by_text(
        self, query: str, character: Character, limit: int
    ) -> list[Reference]:
        """The work facts most relevant to `query` by FTS5 BM25."""
        return [
            Reference(self.kind, e.text, e.title, score)
            for e, score in await self._nearest_by_text(query, limit)
        ]

    async def search_entries(
        self,
        query_vector: Sequence[float] | None,
        limit: int,
        kinds: Collection[EntryKind] | None = None,
        query: str | None = None,
    ) -> list[WorldEntry]:
        """The entries (of `kinds`, or any) matching `query_vector`, `query`, or both
        (fused with RRF), best first."""
        if limit <= 0:
            return []
        if not query:
            if query_vector is None:
                return []
            return [e for e, _ in await self._nearest(query_vector, limit, kinds)]
        if query_vector is None:
            return [e for e, _ in await self._nearest_by_text(query, limit, kinds)]
        fetch_limit = limit * HYBRID_CANDIDATE_MULTIPLIER
        fts_task = asyncio.ensure_future(self._nearest_by_text(query, fetch_limit, kinds))
        try:
            try:
                vec_entries = [e for e, _ in await self._nearest(query_vector, fetch_limit, kinds)]
            except EmbeddingError:
                log.warning(
                    "vector search failed for %s entries; falling back to FTS5",
                    self.label,
                    exc_info=True,
                )
                fts_entries = [e for e, _ in await fts_task]
                return fts_entries[:limit]
            fts_entries = [e for e, _ in await fts_task]
            fused = rrf_fuse([vec_entries, fts_entries], key=lambda e: e.text, k=RRF_K)
            return [e for e, _ in fused[:limit]]
        finally:
            if not fts_task.done():
                fts_task.cancel()

    async def search_entries_by_text(
        self,
        query: str,
        limit: int,
        kinds: Collection[EntryKind] | None = None,
    ) -> list[WorldEntry]:
        """The entries (of `kinds`, or any) most relevant to `query` by FTS5 BM25."""
        return [e for e, _ in await self._nearest_by_text(query, limit, kinds)]

    async def _nearest(
        self,
        query_vector: Sequence[float],
        limit: int,
        kinds: Collection[EntryKind] | None = None,
    ) -> list[tuple[WorldEntry, float]]:
        """As `search_entries`, with their similarity."""
        among = [i for i, e in enumerate(self._entries) if kinds is None or e.kind in kinds]
        best = await self._texts.search(WORK_SCOPE, self._documents, query_vector, limit, among)
        return [(self._entries[i], similarity) for i, similarity in best]

    async def _nearest_by_text(
        self,
        query: str,
        limit: int,
        kinds: Collection[EntryKind] | None = None,
    ) -> list[tuple[WorldEntry, float]]:
        if (
            not self._entries
            or limit <= 0
            or (kinds is not None and not kinds)
            or fts_query(query) is None
        ):
            return []
        index = await self._fts_index()
        best = await asyncio.to_thread(index.search, query, limit, kinds)
        return [(self._entries[i], score) for i, score in best]

    async def _fts_index(self) -> MemoryFtsIndex:
        async with self._fts_lock:
            if self._fts is None:
                texts = [titled_text(e.title, e.text) for e in self._entries]
                kinds = [e.kind for e in self._entries]
                self._fts = await asyncio.to_thread(MemoryFtsIndex, texts, kinds)
            return self._fts

    async def embed_missing(
        self, batch: int = REEMBED_BATCH, progress: Callable[[int], None] | None = None
    ) -> int:
        """Embed the entries that have no vector from this source's embedder yet, `batch`
        at a time; returns how many that was, telling `progress` once done."""
        embedded = await self._texts.embed_missing(WORK_SCOPE, self._documents, batch)
        if progress is not None:
            progress(embedded)
        return embedded

    async def forget_other_models(self) -> int:
        """Drop every vector not from this source's embedder; returns how many there were."""
        return await self._texts.forget_other_models(WORK_SCOPE)
