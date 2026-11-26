"""`eidolon eval retrieval`: recall@k and MRR of candidate retrieval against
`backend/eval/rerank-calibration.toml` without calling the reranker."""

import asyncio
import json
from pathlib import Path

import pytest

from eidolon.characters import load_characters
from eidolon.corpus import Episode, Line
from eidolon.data_access import Database
from eidolon.rerank_eval import load_calibration
from eidolon.retrieval import open_reference_sources
from eidolon.retrieval_eval import (
    RetrievalEvalError,
    compare_retrieval,
    evaluate_retrieval,
    load_baseline,
    report_retrieval,
    save_baseline,
    summarize_retrieval,
)
from eidolon.world import load_world, world_path
from tests.conftest import Admin, CharacterConfig
from tests.fakes import FakeEmbedder
from tests.test_world_setting import write_world

PARK = Episode(
    "produce_events/100100101", "培育剧情", "W.I.N.G.編", "公園の歌声", frozenset({"mano"}),
    (Line("真乃", "公園"),),
)
FINAL = Episode(
    "produce_events/100100109", "培育剧情", "W.I.N.G.編", "決勝", frozenset({"mano"}),
    tuple(Line("真乃", "公園 優勝 " + "あ" * 600) for _ in range(2))
    + (Line("真乃", "公園 優勝"),),
)
OTHER = Episode(
    "produce_events/100100201", "培育剧情", "W.I.N.G.編", "別の日", frozenset({"mano"}),
    (Line("真乃", "写真"),),
)
FACTS = "# 鸟\n## ピーちゃん\n公園で拾った鳥。\n\n# 档案\n写真。\n"

HIKARI = "歌曲「ヒカリのdestination」"

CALIBRATION = f"""
[[memories]]
key = "cat"
source = "mano"
text = "制作人养了一只猫"

[[cases]]
id = "story-dedup"
character = "mano"
kind = "story"
query = "公園 優勝"
relevant = ["produce_events/100100101", "produce_events/100100999"]

[[cases]]
id = "facts-followup"
character = "mano"
kind = "facts"
previous = "公園"
query = "それは？"
relevant = ["鸟 / ピーちゃん"]

[[cases]]
id = "work-hikari"
character = "mano"
kind = "work"
query = "destination"
relevant = ["{HIKARI}"]

[[cases]]
id = "smalltalk"
character = "mano"
kind = "story"
query = "天気"
relevant = []

[[cases]]
id = "cat-memory"
character = "mano"
kind = "memory"
query = "猫"
relevant = ["cat"]
"""


@pytest.fixture
def retrieval_world(tmp_path: Path):
    config = CharacterConfig(tmp_path / "characters")
    config.add("mano", "櫻木真乃", "sheet", speakers=["真乃"], facts=FACTS)
    write_world(config)
    world = load_world(world_path(config.path))
    assert world is not None
    characters = load_characters(config.path)
    calibration_path = tmp_path / "calibration.toml"
    calibration_path.write_text(CALIBRATION, encoding="utf-8")
    db = Database(tmp_path / "eidolon.db")
    yield characters, world, calibration_path, open_reference_sources(
        db, FakeEmbedder(), characters.values(), world
    )
    asyncio.run(db.close())


async def test_evaluate_retrieval_computes_recall_mrr_dedup_and_skips(retrieval_world):
    characters, world, calibration_path, sources = retrieval_world
    await sources.corpus.save([PARK, FINAL, OTHER])
    calibration = load_calibration(calibration_path, world)

    results = await evaluate_retrieval(calibration, characters, sources, mode="vector", k=4)
    summary = summarize_retrieval(results)

    # Skips memory (1) and empty relevant (1).
    assert results.skipped_memory == 1
    assert results.skipped_empty == 1
    assert [c.case.id for c in results.cases] == ["story-dedup", "facts-followup", "work-hikari"]

    # FINAL has 2 passages both matching "公園 優勝" ahead of PARK ("公園"), so after
    # episode_id deduplication FINAL is rank 1 and PARK is rank 2 (not 3).
    story_case, facts_case, work_case = results.cases
    assert story_case.ranks == {"produce_events/100100101": 2}
    assert story_case.missed == ("produce_events/100100999",)
    assert story_case.recall == pytest.approx(0.5)
    assert story_case.reciprocal_rank == pytest.approx(0.5)

    # facts-followup joins previous ("公園") + query ("それは？") -> matches "鸟 / ピーちゃん" or "档案".
    assert "鸟 / ピーちゃん" in facts_case.ranks
    assert facts_case.missed == ()
    assert facts_case.recall == pytest.approx(1.0)

    assert work_case.ranks == {HIKARI: 4}
    assert work_case.missed == ()
    assert work_case.reciprocal_rank == pytest.approx(0.25)

    # Overall: 3 of 4 relevant items hit -> micro recall 0.75; macro (0.5 + 1 + 1)/3.
    assert summary["summary"]["cases"] == 3
    assert summary["summary"]["relevant_total"] == 4
    assert summary["summary"]["relevant_hits"] == 3
    assert summary["summary"]["recall"] == pytest.approx(0.75)
    assert summary["summary"]["macro_recall"] == pytest.approx((0.5 + 1.0 + 1.0) / 3)
    assert summary["summary"]["all_hit"] == 2
    assert summary["summary"]["any_hit"] == 3
    assert summary["by_kind"]["story"]["recall"] == pytest.approx(0.5)
    assert summary["by_kind"]["story"]["mrr"] == pytest.approx(0.5)
    assert summary["by_kind"]["work"]["recall"] == pytest.approx(1.0)
    assert summary["by_kind"]["work"]["mrr"] == pytest.approx(0.25)

    text = report_retrieval(results)
    assert "模式：vector" in text
    assert "k = 4" in text
    assert "跳过 2 条（memory 1 条，relevant 为空 1 条）" in text
    assert "全部（3 条）：Recall@4 75.0%（3/4，宏平均 83.3%）" in text
    assert "全命中 2/3，至少命中 1 条 3/3" in text
    assert "story（1 条）：" in text
    assert "facts（1 条）：" in text
    assert "work（1 条）：" in text
    assert "story-dedup" in text
    assert "produce_events/100100999" in text


async def test_save_and_compare_baseline_reports_deltas_recovered_and_regressed(
    retrieval_world, tmp_path: Path
):
    characters, world, calibration_path, sources = retrieval_world
    await sources.corpus.save([PARK, FINAL, OTHER])
    results = await evaluate_retrieval(
        load_calibration(calibration_path, world), characters, sources, mode="vector", k=4
    )
    baseline_path = tmp_path / "baseline.json"
    summary = summarize_retrieval(results)
    # Simulate an earlier baseline where story-dedup had all items hit, while work-hikari missed HIKARI.
    summary["summary"]["recall"] = 0.75
    summary["summary"]["mrr"] = 0.50
    summary["by_kind"]["story"]["recall"] = 1.0
    summary["by_kind"]["story"]["mrr"] = 1.0
    summary["by_kind"]["work"]["recall"] = 0.0
    summary["by_kind"]["work"]["mrr"] = 0.0
    for item in summary["per_case"]:
        if item["id"] == "story-dedup":
            item["missed"] = []
        if item["id"] == "work-hikari":
            item["missed"] = [HIKARI]
    save_baseline(baseline_path, summary)
    loaded = load_baseline(baseline_path)

    diff = compare_retrieval(results, loaded)
    text = report_retrieval(results, baseline=loaded)

    assert diff["delta_recall"] == pytest.approx(0.0)
    assert diff["delta_mrr"] == pytest.approx((0.5 + 1.0 + 0.25) / 3 - 0.50)
    assert diff["recovered"] == [("work-hikari", [HIKARI])]
    assert diff["regressed"] == [("story-dedup", ["produce_events/100100999"])]
    assert "## 基线对比" in text
    assert "ΔRecall@4" in text
    assert "ΔMRR" in text
    assert "新找回（1 条）：" in text
    assert "work-hikari" in text
    assert "新漏掉（1 条）：" in text
    assert "story-dedup" in text
    assert "produce_events/100100999" in text


def test_load_baseline_rejects_missing_or_broken_file(tmp_path: Path):
    with pytest.raises(RetrievalEvalError, match="找不到"):
        load_baseline(tmp_path / "missing.json")

    broken = tmp_path / "broken.json"
    broken.write_text("{bad json", encoding="utf-8")
    with pytest.raises(RetrievalEvalError, match="格式有误"):
        load_baseline(broken)

    incomplete = tmp_path / "incomplete.json"
    incomplete.write_text(json.dumps({"mode": "vector"}), encoding="utf-8")
    with pytest.raises(RetrievalEvalError, match="缺少"):
        load_baseline(incomplete)


class _ClosableEmbedder(FakeEmbedder):
    async def aclose(self) -> None:
        pass


def test_cli_eval_retrieval_runs_vector_saves_and_compares_without_rerank_key(
    retrieval_world, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    _, _, calibration_path, sources = retrieval_world
    asyncio.run(sources.corpus.save([PARK, FINAL, OTHER]))
    monkeypatch.setenv("EMBEDDING_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "gm-key")
    monkeypatch.delenv("SILICONFLOW_API_KEY", raising=False)
    monkeypatch.setattr("eidolon.embedding.open_embedder", lambda *_: _ClosableEmbedder())

    admin = Admin(tmp_path / "eidolon.db", capsys)
    config = tmp_path / "characters" / "characters.toml"
    baseline_path = tmp_path / "baseline.json"

    out = admin.run(
        "eval", "retrieval", "--mode", "vector", "--k", "4",
        "--file", str(calibration_path), "--characters", str(config),
        "--save", str(baseline_path),
    )

    assert "模式：vector　k = 4" in out
    assert "Recall@4 75.0%" in out
    assert baseline_path.exists()
    saved = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert saved["mode"] == "vector"
    assert saved["k"] == 4

    compared = admin.run(
        "eval", "retrieval", "--k", "4",
        "--file", str(calibration_path), "--characters", str(config),
        "--compare", str(baseline_path),
    )
    assert "## 基线对比" in compared
    assert "新找回：无" in compared
    assert "新漏掉：无" in compared


def test_cli_eval_retrieval_rejects_unimplemented_mode_and_bad_k(
    retrieval_world, tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    _, _, calibration_path, _ = retrieval_world
    admin = Admin(tmp_path / "eidolon.db", capsys)
    config = tmp_path / "characters" / "characters.toml"

    err_mode = admin.fails(
        "eval", "retrieval", "--mode", "fts",
        "--file", str(calibration_path), "--characters", str(config),
    )
    assert "尚未接入" in err_mode

    err_k = admin.fails(
        "eval", "retrieval", "--k", "0",
        "--file", str(calibration_path), "--characters", str(config),
    )
    assert "1" in err_k



