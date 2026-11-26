"""Evaluating candidate retrieval (`eidolon eval retrieval`) against
`eval/rerank-calibration.toml` without calling the reranker.

Each non-memory case with non-empty `relevant` is searched against the reference
sources (up to `k` candidates per source). Story candidates are deduplicated by
`episode_id` keeping each episode's highest rank before counting hits and MRR;
character facts and work facts are matched by `origin`.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from eidolon.characters import Character
from eidolon.memory import joined_query
from eidolon.references import Reference, ReferenceKind
from eidolon.rerank_eval import Calibration, CalibrationError, Case
from eidolon.retrieval import CANDIDATES_PER_SOURCE, ReferenceSources

RetrievalMode = Literal["vector", "fts", "hybrid"]
EvaluatedKind = Literal["story", "facts", "work"]

_EVALUATED_KINDS: tuple[EvaluatedKind, ...] = ("story", "facts", "work")


class RetrievalEvalError(RuntimeError):
    pass


@dataclass(frozen=True)
class RetrievalCaseResult:
    """One evaluated case's hit ranks and missed relevant labels."""

    case: Case
    ranks: dict[str, int]
    missed: tuple[str, ...]
    recall: float
    reciprocal_rank: float


@dataclass(frozen=True)
class RetrievalEvalResults:
    """All evaluated cases alongside skipped counts."""

    mode: RetrievalMode
    k: int
    skipped_memory: int
    skipped_empty: int
    cases: tuple[RetrievalCaseResult, ...]

    @property
    def skipped(self) -> int:
        return self.skipped_memory + self.skipped_empty


def validate_retrieval_options(mode: str, k: int) -> None:
    """Validate CLI / API options before opening the database or embedding client."""
    if k < 1:
        raise RetrievalEvalError("--k 至少是 1")
    if mode != "vector":
        raise RetrievalEvalError(
            f"检索模式 {mode} 尚未接入（需先完成 FTS5 全文索引与混合召回）"
        )


async def evaluate_retrieval(
    calibration: Calibration,
    characters: Mapping[str, Character],
    sources: ReferenceSources,
    *,
    mode: RetrievalMode = "vector",
    k: int = CANDIDATES_PER_SOURCE,
) -> RetrievalEvalResults:
    """Run candidate retrieval for each reference case with non-empty `relevant`."""
    validate_retrieval_options(mode, k)
    if unknown := {c.character for c in calibration.cases} - characters.keys():
        raise CalibrationError(f"角色配置里没有 {'、'.join(sorted(unknown))}")

    skipped_memory = 0
    skipped_empty = 0
    results: list[RetrievalCaseResult] = []
    for case in calibration.cases:
        if case.kind == "memory":
            skipped_memory += 1
            continue
        if not case.relevant:
            skipped_empty += 1
            continue
        query_text = joined_query(case.previous, case.query)
        query_vector = await sources.embedder.embed_query(query_text)
        candidates = await sources.candidates(
            query_vector, characters[case.character], limit=k
        )
        ranks_by_origin = _rank_origins(candidates)
        ranks = {
            label: ranks_by_origin[label]
            for label in case.relevant
            if label in ranks_by_origin
        }
        missed = tuple(label for label in case.relevant if label not in ranks)
        recall = len(ranks) / len(case.relevant)
        reciprocal_rank = (1.0 / min(ranks.values())) if ranks else 0.0
        results.append(
            RetrievalCaseResult(case, ranks, missed, recall, reciprocal_rank)
        )
    return RetrievalEvalResults(
        mode=mode,
        k=k,
        skipped_memory=skipped_memory,
        skipped_empty=skipped_empty,
        cases=tuple(results),
    )


def _rank_origins(candidates: Sequence[Reference]) -> dict[str, int]:
    """Deduplicate candidates per source keeping the earliest (highest) position,
    then assign 1-based ranks within each source."""
    seen: dict[ReferenceKind, list[str]] = {"episode": [], "fact": [], "work": []}
    for candidate in candidates:
        origins = seen[candidate.kind]
        if candidate.origin not in origins:
            origins.append(candidate.origin)
    ranks: dict[str, int] = {}
    for origins in seen.values():
        for rank, origin in enumerate(origins, start=1):
            # If two different sources ever share an origin string, keep the better rank.
            if origin not in ranks or rank < ranks[origin]:
                ranks[origin] = rank
    return ranks


def summarize_retrieval(results: RetrievalEvalResults, file: str | None = None) -> dict:
    """Summarize overall, by-kind, and per-case recall@k and MRR as a JSON-ready dict."""
    return {
        "mode": results.mode,
        "k": results.k,
        "file": file,
        "skipped": {
            "memory": results.skipped_memory,
            "empty_relevant": results.skipped_empty,
            "total": results.skipped,
        },
        "summary": _aggregate(results.cases),
        "by_kind": {
            kind: _aggregate([r for r in results.cases if r.case.kind == kind])
            for kind in _EVALUATED_KINDS
        },
        "per_case": [
            {
                "id": r.case.id,
                "character": r.case.character,
                "kind": r.case.kind,
                "relevant": list(r.case.relevant),
                "ranks": dict(r.ranks),
                "missed": list(r.missed),
                "recall": r.recall,
                "reciprocal_rank": r.reciprocal_rank,
            }
            for r in results.cases
        ],
    }


def _aggregate(cases: Sequence[RetrievalCaseResult]) -> dict:
    n = len(cases)
    relevant_total = sum(len(r.case.relevant) for r in cases)
    relevant_hits = sum(len(r.ranks) for r in cases)
    all_hit = sum(1 for r in cases if not r.missed)
    any_hit = sum(1 for r in cases if r.ranks)
    return {
        "cases": n,
        "relevant_total": relevant_total,
        "relevant_hits": relevant_hits,
        "recall": (relevant_hits / relevant_total) if relevant_total else 0.0,
        "macro_recall": (sum(r.recall for r in cases) / n) if n else 0.0,
        "all_hit": all_hit,
        "all_hit_rate": (all_hit / n) if n else 0.0,
        "any_hit": any_hit,
        "any_hit_rate": (any_hit / n) if n else 0.0,
        "mrr": (sum(r.reciprocal_rank for r in cases) / n) if n else 0.0,
    }


def save_baseline(path: Path, summary: dict[str, Any]) -> None:
    """Write a retrieval evaluation summary JSON to `path`."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except OSError as e:
        raise RetrievalEvalError(f"写不了基线文件 {path}：{e}") from None


def load_baseline(path: Path) -> dict[str, Any]:
    """Load and validate a saved retrieval evaluation JSON file."""
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise RetrievalEvalError(f"找不到基线文件 {path}") from None
    except OSError as e:
        raise RetrievalEvalError(f"读不了基线文件 {path}：{e}") from None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RetrievalEvalError(f"基线文件 {path} 格式有误：{e}") from None
    required = ("mode", "k", "summary", "by_kind", "per_case")
    if not isinstance(data, dict):
        raise RetrievalEvalError(f"基线文件 {path} 格式有误：根节点应为对象")
    if missing := [k for k in required if k not in data]:
        raise RetrievalEvalError(f"基线文件 {path} 缺少必要字段：{'、'.join(missing)}")
    return data


def _metric_delta(
    current_bucket: Mapping[str, Any], baseline_bucket: Mapping[str, Any]
) -> dict[str, float]:
    baseline_recall = float(baseline_bucket["recall"])
    current_recall = float(current_bucket["recall"])
    baseline_mrr = float(baseline_bucket["mrr"])
    current_mrr = float(current_bucket["mrr"])
    return {
        "baseline_recall": baseline_recall,
        "current_recall": current_recall,
        "delta_recall": current_recall - baseline_recall,
        "baseline_mrr": baseline_mrr,
        "current_mrr": current_mrr,
        "delta_mrr": current_mrr - baseline_mrr,
    }


def compare_retrieval(
    results: RetrievalEvalResults, baseline: Mapping[str, Any]
) -> dict[str, Any]:
    """Compare `results` against an earlier `baseline` JSON summary."""
    current = summarize_retrieval(results)
    base_summary = baseline["summary"]
    cur_summary = current["summary"]

    by_kind: dict[str, dict[str, float]] = {}
    for kind in _EVALUATED_KINDS:
        cur_k = current["by_kind"][kind]
        base_k = baseline["by_kind"].get(kind, {"recall": 0.0, "mrr": 0.0})
        by_kind[kind] = _metric_delta(cur_k, base_k)

    base_by_id = {c["id"]: c for c in baseline["per_case"]}
    recovered: list[tuple[str, list[str]]] = []
    regressed: list[tuple[str, list[str]]] = []
    for r in results.cases:
        if r.case.id not in base_by_id:
            continue
        base_missed = list(base_by_id[r.case.id].get("missed", ()))
        cur_missed = set(r.missed)
        base_missed_set = set(base_missed)
        if gained := [label for label in base_missed if label not in cur_missed]:
            recovered.append((r.case.id, gained))
        if lost := [label for label in r.missed if label not in base_missed_set]:
            regressed.append((r.case.id, lost))

    return {
        "baseline_mode": baseline["mode"],
        "baseline_k": baseline["k"],
        **_metric_delta(cur_summary, base_summary),
        "by_kind": by_kind,
        "recovered": recovered,
        "regressed": regressed,
    }


def report_retrieval(
    results: RetrievalEvalResults, baseline: Mapping[str, Any] | None = None
) -> str:
    """Human-readable summary of recall@k, MRR, skipped cases, and missed labels."""
    data = summarize_retrieval(results)
    k = results.k
    lines = [
        f"模式：{results.mode}　k = {k}　评测 {len(results.cases)} 条"
        f"（跳过 {results.skipped} 条（memory {results.skipped_memory} 条，"
        f"relevant 为空 {results.skipped_empty} 条））",
        "",
        "## 召回汇总",
        _format_bucket("全部", data["summary"], k),
    ]
    for kind in _EVALUATED_KINDS:
        bucket = data["by_kind"][kind]
        if bucket["cases"]:
            lines.append(_format_bucket(kind, bucket, k))

    missed_cases = [r for r in results.cases if r.missed]
    lines.append("")
    if missed_cases:
        lines.append(f"## 漏召回明细（{len(missed_cases)} 条）")
        for r in missed_cases:
            hit_info = (
                "、".join(f"{label}@{rank}" for label, rank in r.ranks.items())
                or "无"
            )
            lines.append(
                f"- {r.case.id}（{r.case.kind} / {r.case.character}）"
                f"漏：{'、'.join(r.missed)}｜已中：{hit_info}"
            )
    else:
        lines.append("## 漏召回明细（无）")

    if baseline is not None:
        diff = compare_retrieval(results, baseline)
        lines += ["", *_format_comparison(diff, data, k)]
    return "\n".join(lines)


def _format_comparison(diff: dict[str, Any], current: dict[str, Any], k: int) -> list[str]:
    base_k = diff["baseline_k"]
    k_note = f"（注意：基线 k = {base_k}，本次 k = {k}）" if base_k != k else ""
    lines = [
        f"## 基线对比（基线模式：{diff['baseline_mode']}，k = {base_k}{k_note}）",
        _format_delta("全部", diff, k),
    ]
    for kind in _EVALUATED_KINDS:
        if current["by_kind"][kind]["cases"]:
            lines.append(_format_delta(kind, diff["by_kind"][kind], k))
    recovered: list[tuple[str, list[str]]] = diff["recovered"]
    regressed: list[tuple[str, list[str]]] = diff["regressed"]
    if recovered:
        lines.append(f"新找回（{len(recovered)} 条）：")
        lines.extend(f"  + {case_id}：{'、'.join(labels)}" for case_id, labels in recovered)
    else:
        lines.append("新找回：无")
    if regressed:
        lines.append(f"新漏掉（{len(regressed)} 条）：")
        lines.extend(f"  - {case_id}：{'、'.join(labels)}" for case_id, labels in regressed)
    else:
        lines.append("新漏掉：无")
    return lines


def _format_delta(name: str, entry: Mapping[str, float], k: int) -> str:
    baseline_recall = entry["baseline_recall"]
    current_recall = entry["current_recall"]
    delta_recall = entry["delta_recall"]
    baseline_mrr = entry["baseline_mrr"]
    current_mrr = entry["current_mrr"]
    delta_mrr = entry["delta_mrr"]
    return (
        f"- {name}：ΔRecall@{k} {delta_recall:+.1%}（{baseline_recall:.1%} → {current_recall:.1%}），"
        f"ΔMRR {delta_mrr:+.4f}（{baseline_mrr:.4f} → {current_mrr:.4f}）"
    )


def _format_bucket(name: str, bucket: dict, k: int) -> str:
    return (
        f"- {name}（{bucket['cases']} 条）："
        f"Recall@{k} {bucket['recall']:.1%}"
        f"（{bucket['relevant_hits']}/{bucket['relevant_total']}，"
        f"宏平均 {bucket['macro_recall']:.1%}），"
        f"全命中 {bucket['all_hit']}/{bucket['cases']}，"
        f"至少命中 1 条 {bucket['any_hit']}/{bucket['cases']}，"
        f"MRR {bucket['mrr']:.4f}"
    )
