"""Searching the story corpus: its vectors are kept in memory, read once, and read anew
once another process (a story sync or import, `eidolon reembed`) has changed the corpus;
searches go on with the vectors held meanwhile."""

import asyncio
import logging
import sqlite3
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Any, cast

import pytest

from eidolon.corpus import Episode, Line, StoryCorpus
from eidolon.data_access import Database
from eidolon.embedding import nearest
from tests.fakes import FakeEmbedder
from tests.stories import corpus_in

PARK = Episode(
    "produce_events/100100101", "produce", "W.I.N.G.編", "第1話", frozenset({"mano"}),
    (Line("真乃", "公園で鳩と一緒に歌っていました"),),
)
WON = Episode(
    "produce_events/100100106", "produce", "W.I.N.G.編", "第6話", frozenset({"mano"}),
    (Line("真乃", "優勝、したんですねっ"),),
)
NAGASAKI = Episode(
    "produce_events/201100401", "produce", "恋鐘のカード", "第1話", frozenset({"kogane", "mano"}),
    (Line("恋鐘", "長崎のちゃんぽん、ばりうまかよ！写真ば撮ろう、公園で"),),
)
HIORI = Episode(
    "game_event_communications/400100401", "event", "イベント", "第1話", frozenset({"hiori"}),
    (Line("灯織", "公園で写真の撮影、頑張ります"),),
)


@pytest.fixture
def database(tmp_path: Path) -> Path:
    return tmp_path / "eidolon.db"


@pytest.fixture
def loads(caplog: pytest.LogCaptureFixture) -> Callable[[], int]:
    """How many times the vectors have been loaded so far."""
    caplog.set_level(logging.INFO, logger="eidolon.corpus")
    return lambda: sum("story vectors loaded" in r.getMessage() for r in caplog.records)


@pytest.fixture
async def db(database: Path) -> AsyncIterator[Database]:
    """The server's data access layer."""
    db = Database(database)
    yield db
    await db.close()


@pytest.fixture
async def corpus(db: Database) -> AsyncIterator[StoryCorpus]:
    """The corpus as the server searches it."""
    corpus = StoryCorpus(db, FakeEmbedder())
    yield corpus
    await corpus.aclose()


async def saved(database: Path, *episodes: Episode, embedder: FakeEmbedder | None = None) -> None:
    """`episodes` saved by another process, as a story sync saves them."""
    async with corpus_in(database, embedder or FakeEmbedder()) as other:
        await other.save(list(episodes))


async def found(corpus: StoryCorpus, query: str, character_id: str, limit: int = 5) -> list[str]:
    return [p.episode_id for p in await corpus.search(query, character_id, limit)]


async def until(done: Callable[[], bool]) -> None:
    async with asyncio.timeout(5):
        while not done():
            await asyncio.sleep(0.01)


async def test_a_character_finds_only_the_passages_of_the_episodes_she_is_cast_in(
    database: Path, corpus: StoryCorpus
):
    await saved(database, PARK, WON, NAGASAKI, HIORI)

    assert await found(corpus, "公園の鳩", "mano", 1) == [PARK.id]
    assert set(await found(corpus, "公園で写真", "mano")) == {PARK.id, WON.id, NAGASAKI.id}
    assert await found(corpus, "公園で写真", "kogane") == [NAGASAKI.id]
    assert await found(corpus, "公園", "hazuki") == []
    [passage] = await corpus.search("優勝", "mano", 1)
    assert passage.text == "W.I.N.G.編「第6話」\n真乃：優勝、したんですねっ"


async def test_the_scores_are_the_cosine_similarity_of_the_stored_vectors(
    database: Path, corpus: StoryCorpus
):
    await saved(database, PARK, WON, NAGASAKI, HIORI)
    query = await FakeEmbedder().embed_query("公園で鳩の写真")
    with sqlite3.connect(database) as stored:
        rows = stored.execute(
            "SELECT p.episode_id, p.embedding FROM episode_passages p"
            " JOIN episode_cast c ON c.episode_id = p.episode_id WHERE c.character_id = 'mano'"
        ).fetchall()
    stored.close()
    expected = [(rows[i][0], score) for i, score in nearest([r[1] for r in rows], query, 3)]

    best = await corpus.search_by_vector(query, "mano", 3)

    assert [p.episode_id for p in best] == [episode_id for episode_id, _ in expected]
    assert [p.score for p in best] == pytest.approx([score for _, score in expected], abs=1e-6)


async def test_the_vectors_are_loaded_once_for_every_search(
    database: Path, corpus: StoryCorpus, loads: Callable[[], int]
):
    await saved(database, PARK, NAGASAKI)

    await asyncio.gather(*(found(corpus, "鳩", "mano") for _ in range(3)))
    await found(corpus, "長崎", "kogane")

    assert loads() == 1


async def test_loading_them_as_the_server_starts_spares_the_first_search(
    database: Path, corpus: StoryCorpus, loads: Callable[[], int]
):
    await saved(database, PARK)

    await corpus.load()
    assert loads() == 1
    assert await found(corpus, "鳩", "mano") == [PARK.id]
    assert loads() == 1


async def test_episodes_another_process_saves_are_found_once_a_search_has_noticed(
    database: Path, corpus: StoryCorpus, loads: Callable[[], int]
):
    await saved(database, PARK)
    assert await found(corpus, "優勝", "mano") == [PARK.id]

    await saved(database, WON)
    # The search that notices goes on with the vectors held; those after it find the episode.
    assert await found(corpus, "優勝", "mano", 1) == [PARK.id]
    await until(lambda: loads() == 2)

    assert await found(corpus, "優勝", "mano", 1) == [WON.id]


async def test_an_episode_another_process_removes_is_never_found_again(
    database: Path, corpus: StoryCorpus, loads: Callable[[], int]
):
    await saved(database, PARK, WON)
    assert await found(corpus, "鳩", "mano", 1) == [PARK.id]

    async with corpus_in(database, FakeEmbedder()) as other:
        assert await other.remove(PARK.id)

    # Not even by the search that notices, which still holds its vectors.
    assert await found(corpus, "鳩", "mano") == [WON.id]
    await until(lambda: loads() == 2)
    assert await found(corpus, "鳩", "mano") == [WON.id]


async def test_removing_an_episode_not_in_the_corpus_changes_nothing(
    database: Path, corpus: StoryCorpus, loads: Callable[[], int]
):
    await saved(database, PARK)
    await found(corpus, "鳩", "mano")

    async with corpus_in(database, FakeEmbedder()) as other:
        assert not await other.remove("produce_events/999999999")
    await found(corpus, "鳩", "mano")
    await asyncio.sleep(0.05)

    assert loads() == 1


async def test_passages_another_process_embeds_again_are_found_once_noticed(
    database: Path, corpus: StoryCorpus, loads: Callable[[], int]
):
    # Embedded with another model, as before the embedding model changed.
    await saved(database, PARK, embedder=FakeEmbedder("old-model"))
    assert await found(corpus, "鳩", "mano") == []

    async with corpus_in(database, FakeEmbedder()) as other:
        assert await other.embed_missing() == 1
    await found(corpus, "鳩", "mano")
    await until(lambda: loads() == 2)

    assert await found(corpus, "鳩", "mano") == [PARK.id]


async def test_searches_go_on_while_the_vectors_are_loaded_anew(
    database: Path, db: Database, corpus: StoryCorpus, monkeypatch: pytest.MonkeyPatch,
    loads: Callable[[], int],
):
    await saved(database, PARK)
    await found(corpus, "優勝", "mano")
    held_up = asyncio.Event()
    read = cast(Callable[..., Awaitable[Any]], db.read)

    async def slow_read(body: Callable[..., Any], *args: Any) -> Any:
        if body.__name__ == "_vectors":
            await held_up.wait()
        return await read(body, *args)

    monkeypatch.setattr(db, "read", slow_read)
    await saved(database, WON)

    async with asyncio.timeout(5):
        assert await found(corpus, "優勝", "mano", 1) == [PARK.id]
        assert await found(corpus, "優勝", "mano", 1) == [PARK.id]
    assert loads() == 1

    held_up.set()
    await until(lambda: loads() == 2)
    assert await found(corpus, "優勝", "mano", 1) == [WON.id]


async def test_a_load_that_fails_is_logged_and_tried_again_by_the_next_search(
    database: Path, db: Database, corpus: StoryCorpus, monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    await saved(database, PARK)
    read = cast(Callable[..., Awaitable[Any]], db.read)
    failures = [sqlite3.OperationalError("disk I/O error")]

    async def failing_read(body: Callable[..., Any], *args: Any) -> Any:
        if body.__name__ == "_vectors" and failures:
            raise failures.pop()
        return await read(body, *args)

    monkeypatch.setattr(db, "read", failing_read)

    with pytest.raises(sqlite3.OperationalError):
        await found(corpus, "鳩", "mano")
    assert await found(corpus, "鳩", "mano") == [PARK.id]
    assert [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR] == [
        "loading the story vectors failed"
    ]


async def test_closing_stops_a_load_under_way(
    database: Path, db: Database, monkeypatch: pytest.MonkeyPatch
):
    await saved(database, PARK)
    corpus = StoryCorpus(db, FakeEmbedder())
    started = asyncio.Event()
    read = cast(Callable[..., Awaitable[Any]], db.read)

    async def endless_read(body: Callable[..., Any], *args: Any) -> Any:
        if body.__name__ == "_vectors":
            started.set()
            await asyncio.Event().wait()
        return await read(body, *args)

    monkeypatch.setattr(db, "read", endless_read)
    loading = asyncio.create_task(corpus.load())
    await started.wait()

    async with asyncio.timeout(5):
        await corpus.aclose()
        with pytest.raises(asyncio.CancelledError):
            await loading


async def test_fts_search_filters_by_cast_and_stays_in_sync_on_replace_and_remove(
    database: Path, corpus: StoryCorpus
):
    mano_park_a = Episode(
        "produce_events/100100102", "produce", "W.I.N.G.編", "第2話", frozenset({"mano"}),
        (Line("真乃", "公園で公園の写真と公園の鳩を撮りました"),),
    )
    mano_park_b = Episode(
        "produce_events/100100103", "produce", "W.I.N.G.編", "第3話", frozenset({"mano"}),
        (Line("真乃", "公園で写真と公園の記念撮影です"),),
    )
    old_model_ep = Episode(
        "produce_events/100100104", "produce", "W.I.N.G.編", "第4話", frozenset({"mano"}),
        (Line("真乃", "猫カフェに行きました"),),
    )
    await saved(database, PARK, mano_park_a, mano_park_b, NAGASAKI, HIORI)
    await saved(database, old_model_ep, embedder=FakeEmbedder("old-model"))

    # Cast filter is pushed down before LIMIT: Mano's higher-scoring hits never crowd Hiori out.
    assert [p.episode_id for p in await corpus.search_by_text("公園 写真", "hiori", limit=1)] == [
        HIORI.id
    ]
    # BM25 scores are strictly positive and rank repeated term matches ahead of fewer matches.
    mano_park_hits = await corpus.search_by_text("公園 写真", "mano", limit=5)
    assert [p.episode_id for p in mano_park_hits[:2]] == [mano_park_a.id, mano_park_b.id]
    assert all(p.score > 0.0 for p in mano_park_hits)
    assert [p.episode_id for p in await corpus.search_by_text("猫カフェ", "mano", limit=5)] == [
        old_model_ep.id
    ]
    assert await corpus.search_by_text("的 了 吗", "mano", limit=5) == []

    assert [p.episode_id for p in await corpus.search_by_text("歌って", "mano", limit=5)] == [
        PARK.id
    ]
    replaced_park = Episode(
        PARK.id, PARK.category, PARK.source, PARK.title, PARK.cast,
        (Line("真乃", "海辺で貝殻を拾いました"),),
    )
    await saved(database, replaced_park)
    assert await corpus.search_by_text("歌って", "mano", limit=5) == []
    assert [p.episode_id for p in await corpus.search_by_text("貝殻", "mano", limit=5)] == [PARK.id]

    async with corpus_in(database, FakeEmbedder()) as other:
        assert await other.remove(PARK.id)
    assert await corpus.search_by_text("貝殻", "mano", limit=5) == []


async def test_opening_a_legacy_corpus_without_fts_backfills_and_searches_immediately(
    database: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    await saved(database, PARK, NAGASAKI)
    with sqlite3.connect(database) as raw:
        raw.execute("DROP TABLE episode_passages_fts")
    raw.close()
    monkeypatch.setattr("eidolon.corpus._FTS_BACKFILL_BATCH", 1)

    with caplog.at_level(logging.INFO, logger="eidolon.corpus"):
        async with corpus_in(database, FakeEmbedder()) as reopened:
            hits = await reopened.search_by_text("歌って", "mano", limit=5)
            assert [p.episode_id for p in hits] == [PARK.id]
            assert hits[0].score > 0.0

    backfill_logs = [
        r.getMessage() for r in caplog.records
        if r.levelno == logging.INFO and "FTS5" in r.getMessage()
    ]
    assert len(backfill_logs) == 1
    assert "2" in backfill_logs[0]

    caplog.clear()
    with caplog.at_level(logging.INFO, logger="eidolon.corpus"):
        async with corpus_in(database, FakeEmbedder()) as reopened_again:
            assert [
                p.episode_id for p in await reopened_again.search_by_text("ちゃんぽん", "kogane", limit=5)
            ] == [NAGASAKI.id]
    assert not any("FTS5" in r.getMessage() for r in caplog.records)

    # A legacy detail='column' FTS5 table (whose bm25() returns 0.0) is rebuilt automatically.
    with sqlite3.connect(database) as raw:
        raw.execute("DROP TABLE episode_passages_fts")
        raw.execute(
            "CREATE VIRTUAL TABLE episode_passages_fts USING fts5("
            "tokens, content='', contentless_delete=1, tokenize='unicode61', detail='column')"
        )
    raw.close()
    async with corpus_in(database, FakeEmbedder()) as upgraded:
        upgraded_hits = await upgraded.search_by_text("歌って", "mano", limit=5)
        assert [p.episode_id for p in upgraded_hits] == [PARK.id]
        assert upgraded_hits[0].score > 0.0


