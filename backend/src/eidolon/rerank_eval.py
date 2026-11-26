"""Calibrating the reranker's thresholds (`eidolon eval rerank`) against a small labelled
set of questions committed with the code (`eval/rerank-calibration.toml`).

Each question is run as a turn would: story, character-fact and work-fact questions
through the same hybrid reference sources, candidates and reranking as retrieval
(`ReferenceSources.rank`: the story, the character's facts and the work facts reranked
together, with FTS5 using `retrieval.fts_query_for_reply`), memory questions through the
nearest of the set's sample memories, which are embedded for the run and never stored.
Any question is asked after the character's reply before it when it gives one, as a turn
looks references and memories up (`memory.memory_query`, while FTS5 drops the reply on
non-short queries). Each candidate the reranker scores is labelled relevant, acceptable
(either way is fine, so left out of the counts) or irrelevant; an episode scores as its
best passage. The report sets the scores of the relevant against those of the irrelevant,
for the references (under their threshold) and the memories (under theirs), and counts
what a threshold would let in. A relevant candidate retrieval never offered is listed
apart: that is a recall problem no threshold fixes.

The set holds questions, episode identifiers, fact and work-fact titles and labels, never
story text, so it can be committed (ADR-0003).
"""

import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, get_args

import numpy as np

from eidolon.characters import Character
from eidolon.embedding import Document, nearest, to_blob
from eidolon.memory import CANDIDATES, joined_query
from eidolon.rerank import Reranker, RerankThresholds
from eidolon.retrieval import ReferenceSources, fts_query_for_reply
from eidolon.world import World

CaseKind = Literal["story", "facts", "work", "memory"]
Verdict = Literal["relevant", "acceptable", "irrelevant"]


class CalibrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class SampleMemory:
    """A memory of a made-up user's, for the memory questions."""

    key: str
    source: str
    text: str


@dataclass(frozen=True)
class Case:
    """One question, and which candidates answering it needs."""

    id: str
    character: str
    kind: CaseKind
    query: str
    relevant: tuple[str, ...]
    """Episode identifiers and fact titles, for a work-fact question the titles of the
    work facts, or for a memory question, memory keys."""
    acceptable: tuple[str, ...] = ()
    previous: str | None = None
    """What the character replied just before, if anything: a turn looks references and
    memories up with it (`memory.memory_query`)."""


@dataclass(frozen=True)
class Calibration:
    memories: tuple[SampleMemory, ...]
    cases: tuple[Case, ...]


@dataclass(frozen=True)
class Scored:
    label: str
    """The episode's identifier, the fact's or work fact's title, or the memory's key."""
    score: float
    verdict: Verdict


@dataclass(frozen=True)
class CaseResult:
    case: Case
    scored: list[Scored]
    """Every candidate the reranker scored, best first."""
    not_retrieved: list[str]
    """What is labelled relevant but was never a candidate."""


def load_calibration(path: Path, world: World | None = None) -> Calibration:
    """The set at `path`. The work facts any question names must be among `world`'s
    entries (the work facts), so the set is checked against the data file it is run with."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise CalibrationError(f"找不到校准数据集 {path}") from None
    except tomllib.TOMLDecodeError as e:
        raise CalibrationError(f"校准数据集 {path} 格式有误：{e}") from None
    memories = tuple(
        SampleMemory(_text(m, "key", "memories"), _text(m, "source", "memories"),
                     _text(m, "text", "memories"))
        for m in data.get("memories", [])
    )
    keys = {m.key for m in memories}
    titles = {e.title for e in world.entries()} if world else set()
    cases: list[Case] = []
    for entry in data.get("cases", []):
        case_id = _text(entry, "id", "cases")
        kind = entry.get("kind")
        if kind not in get_args(CaseKind):
            raise CalibrationError(
                f"问题 {case_id} 的 kind 只能是 story、facts、work、memory，而不是 {kind}"
            )
        case = Case(
            case_id,
            _text(entry, "character", case_id),
            kind,
            _text(entry, "query", case_id),
            _labels(entry, "relevant", case_id, required=True),
            _labels(entry, "acceptable", case_id),
            _previous(entry, case_id),
        )
        if kind == "memory" and (unknown := set(case.relevant + case.acceptable) - keys):
            raise CalibrationError(f"问题 {case_id} 引用了不存在的示例记忆 {'、'.join(sorted(unknown))}")
        # The work facts are reranked with the story and the character facts, so any
        # reference question may name them; a work-fact question names nothing else.
        named = {
            label
            for label in case.relevant + case.acceptable
            if kind == "work" or (kind != "memory" and label.startswith(_WORK_TITLES))
        }
        if named:
            if world is None:
                raise CalibrationError(
                    f"问题 {case_id} 引用了作品资料，但没有作品资料（world.json）"
                )
            if unknown := named - titles:
                raise CalibrationError(
                    f"问题 {case_id} 引用了 world.json 里没有的作品资料 {'、'.join(sorted(unknown))}"
                )
        if any(c.id == case_id for c in cases):
            raise CalibrationError(f"问题 {case_id} 重复")
        cases.append(case)
    return Calibration(memories, tuple(cases))


_WORK_TITLES = ("歌曲「", "唱片《", "演出「")
"""How the work facts' titles begin (`World.entries`): a song, a release, a live day."""


def _text(entry: dict, field: str, where: str) -> str:
    value = entry.get(field)
    if not isinstance(value, str) or not value:
        raise CalibrationError(f"校准数据集的 {where} 缺少 {field}")
    return value


def _previous(entry: dict, case_id: str) -> str | None:
    value = entry.get("previous")
    if value is not None and (not isinstance(value, str) or not value):
        raise CalibrationError(f"问题 {case_id} 的 previous 应为字符串")
    return value


def _labels(entry: dict, field: str, case_id: str, required: bool = False) -> tuple[str, ...]:
    value = entry.get(field, None if required else [])
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise CalibrationError(f"问题 {case_id} 的 {field} 应为字符串列表")
    return tuple(value)


async def evaluate(
    calibration: Calibration,
    characters: Mapping[str, Character],
    reranker: Reranker,
    sources: ReferenceSources,
) -> list[CaseResult]:
    """Score each question's candidates, as a turn would find them in `sources` and
    rerank them; the memory questions' embedded with the sources' embedder."""
    embedder = sources.embedder
    if unknown := {c.character for c in calibration.cases} - characters.keys():
        raise CalibrationError(f"角色配置里没有 {'、'.join(sorted(unknown))}")
    memory_vectors = (
        [
            to_blob(v)
            for v in await embedder.embed_documents(
                [Document(m.text) for m in calibration.memories]
            )
        ]
        if any(c.kind == "memory" for c in calibration.cases)
        else []
    )
    results = []
    for case in calibration.cases:
        query_text = joined_query(case.previous, case.query)
        if case.kind == "memory":
            query = await embedder.embed_query(query_text)
            near = [
                calibration.memories[i] for i, _ in nearest(memory_vectors, query, CANDIDATES)
            ]
            best = (
                await reranker.rerank(query_text, [m.text for m in near], len(near))
                if near
                else []
            )
            scores = {near[i].key: score for i, score in best}
        else:
            ranked = await sources.rank(
                reranker,
                characters[case.character],
                query_text,
                fts_text=fts_query_for_reply(case.previous, case.query),
            )
            scores: dict[str, float] = {}
            for reference, score in ranked:  # an episode scores as its best passage
                scores[reference.origin] = max(score, scores.get(reference.origin, 0.0))
        scored = [
            Scored(label, score, _verdict(case, label))
            for label, score in sorted(scores.items(), key=lambda s: -s[1])
        ]
        not_retrieved = [label for label in case.relevant if label not in scores]
        results.append(CaseResult(case, scored, not_retrieved))
    return results


def _verdict(case: Case, label: str) -> Verdict:
    if label in case.relevant:
        return "relevant"
    return "acceptable" if label in case.acceptable else "irrelevant"


def report(results: Sequence[CaseResult], model: str, thresholds: RerankThresholds) -> str:
    """The scores of relevant and irrelevant candidates, for references (the story, the
    character facts and the work facts, reranked together as a turn does) and for
    memories, what each threshold lets in, and each question's candidates."""
    lines = [f"重排模型：{model}"]
    groups = [
        ("参考资料", [r for r in results if r.case.kind != "memory"], thresholds.references),
        ("记忆", [r for r in results if r.case.kind == "memory"], thresholds.memories),
    ]
    for title, group, threshold in groups:
        if not group:
            continue
        relevant = [s.score for r in group for s in r.scored if s.verdict == "relevant"]
        irrelevant = [s.score for r in group for s in r.scored if s.verdict == "irrelevant"]
        lines += [
            "",
            f"## {title}（{len(group)} 条问题）",
            f"相关　{_distribution(relevant)}",
            f"不相关 {_distribution(irrelevant)}",
            f"阈值 {threshold:g}：相关命中 {_at_least(relevant, threshold)}/{len(relevant)}，"
            f"不相关误放 {_at_least(irrelevant, threshold)}/{len(irrelevant)}",
        ]
        if missed := [(r.case.id, label) for r in group for label in r.not_retrieved]:
            lines.append("没进入检索结果的相关候选（召回问题，与阈值无关）：")
            lines += [f"  {case_id}：{label}" for case_id, label in missed]
    lines += ["", "## 逐条（+ 相关，~ 可放可不放，- 不相关）"]
    marks = {"relevant": "+", "acceptable": "~", "irrelevant": "-"}
    for result in results:
        lines.append(f"{result.case.id}（{result.case.kind}）{result.case.query}")
        if result.case.previous:
            lines.append(f"  上一句：{result.case.previous}")
        lines += [f"  {marks[s.verdict]} {s.score:.4f} {s.label}" for s in result.scored]
    return "\n".join(lines)


def _distribution(scores: Sequence[float]) -> str:
    if not scores:
        return "n=0"
    quantiles = np.quantile(scores, [0, 0.1, 0.25, 0.5, 0.75, 0.9, 1])
    names = ("最低", "p10", "p25", "中位", "p75", "p90", "最高")
    return f"n={len(scores)} " + " ".join(f"{n} {q:.4f}" for n, q in zip(names, quantiles))


def _at_least(scores: Sequence[float], threshold: float) -> int:
    return sum(score >= threshold for score in scores)
