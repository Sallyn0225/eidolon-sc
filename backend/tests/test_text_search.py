"""Unit tests for CJK 2-gram + ASCII tokenizer, FTS5 query escaping, RRF fusion, and
in-memory FTS5 index."""

import pytest

from eidolon.text_search import MemoryFtsIndex, fts_query, index_tokens, query_tokens, rrf_fuse


def test_tokenizer_splits_cjk_2grams_and_ascii_words():
    assert index_tokens("真乃 灯織 恋鐘") == ["真乃", "灯織", "恋鐘"]
    assert index_tokens("めぐる ピーちゃん") == ["めぐ", "ぐる", "ピー", "ーち", "ちゃ", "ゃん"]
    assert index_tokens("W.I.N.G.編 L'Antica 283事務所 ３人") == [
        "w", "i", "n", "g", "編", "l", "antica", "283", "事務", "務所", "3", "人",
    ]


def test_index_keeps_stopwords_while_query_drops_them_and_deduplicates():
    text = "真乃 的 了 吗 什么 怎么 一下 です 真乃"
    assert index_tokens(text) == ["真乃", "的", "了", "吗", "什么", "怎么", "一下", "です", "真乃"]
    assert query_tokens(text) == ["真乃"]
    assert query_tokens("的 了 吗 呢 啊 什么 怎么 一下") == []


def test_fts_query_escapes_reserved_words_and_special_characters():
    assert fts_query('AND OR NOT NEAR "L\'Antica" (foo*bar)') == (
        '"and" OR "or" OR "not" OR "near" OR "l" OR "antica" OR "foo" OR "bar"'
    )
    assert fts_query("") is None
    assert fts_query("？！……") is None
    assert fts_query("什么 怎么 的 了") is None


def test_rrf_fuse_merges_deduplicates_and_orders_by_reciprocal_rank_score():
    fused = rrf_fuse(
        [
            [("a", 0.9), ("b", 0.8), ("a", 0.1)],  # duplicate "a" inside same list counts only once at rank 1
            [("b", 5.0), ("c", 4.0)],
        ],
        key=lambda item: item[0],
        k=60,
    )

    assert [item[0] for item, _ in fused] == ["b", "a", "c"]
    assert [score for _, score in fused] == pytest.approx(
        [1 / 62 + 1 / 61, 1 / 61, 1 / 62]
    )
    assert rrf_fuse([[], []], key=lambda item: item) == []


def test_memory_fts_index_ranks_bm25_and_filters_by_kind():
    index = MemoryFtsIndex(
        [
            "歌曲「ヒカリのdestination」演唱：illumination STARS",
            "演出「6thLIVE TOUR」2024年3月2日 ヒカリのdestination",
            "唱片《BRILLI@NT WING 02》ヒカリのdestination",
        ],
        kinds=["song", "live", "release"],
    )

    hits = index.search("ヒカリのdestination ライブ 2024年3月2日", limit=3)
    assert hits[0][0] == 1
    assert {doc_id for doc_id, _ in hits} == {0, 1, 2}
    assert all(score >= 0.0 for _, score in hits)

    filtered = index.search("ヒカリのdestination", limit=5, kinds=("live", "release"))
    assert {doc_id for doc_id, _ in filtered} == {1, 2}

    assert index.search("ヒカリのdestination", limit=5, kinds=()) == []
    assert index.search("的 了", limit=5) == []
    assert index.search('AND "OR" NOT (ヒカリ)', limit=5)
    assert MemoryFtsIndex([]).search("ヒカリ", limit=5) == []


