"""Reranking retrieved text against the query: Qwen3-Reranker on SiliconFlow.

What counts as relevant enough depends on the model, so each model the project has
calibrated (`eidolon eval rerank`) has thresholds of its own.

Reranking holds up a turn, so each request is given a few seconds and made again once if
it fails in passing (`retry`)."""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Protocol

import httpx

from eidolon.billing import bill
from eidolon.config import DEFAULT_RERANK_MODEL, RerankSettings
from eidolon.retry import TURN_TIMEOUT, ServiceError, answered, retry_once, transient_status

RERANK_TIMEOUT = httpx.Timeout(30, connect=10)


@dataclass(frozen=True)
class RerankThresholds:
    """The reranker's scores below which a candidate is left out of the prompt."""

    references: float
    """For story passages and character facts, reranked together."""
    memories: float
    """For the user's memories."""


KNOWN_THRESHOLDS: dict[str, RerankThresholds] = {
    # On the calibration set (backend/eval/rerank-calibration.toml) relevant passages score
    # 0.99 at the median and nine in ten unrelated ones below 0.3, so a question about
    # something the character never lived through brings back nothing rather than filler;
    # the unrelated ones above it are mostly the same topic but another event, which no
    # threshold separates. A short memory scores low against a loosely worded remark (a
    # quarter of the relevant ones below 0.015) but unrelated ones lower still (nine in ten
    # below 0.0011), so memories get a threshold well below that of story and character facts.
    # Checked again once memories were found with the character's previous reply (2026-10-08):
    # the questions leaning on it score 0.99, the one whose previous reply is beside the point
    # leaves every memory below 0.002, and 0.01 still lets in 12 of 15 relevant, 1 of 158 not.
    # Checked again once references were looked up with her previous reply too (2026-10-14):
    # of the 14 relevant candidates of 11 short follow-ups, asked alone 10 never reached the
    # reranker; with her reply 10 do and all score 0.33 or more, while 0.4 would drop three
    # (both 1stLIVE days at 0.33 and 0.35, her father's change of heart at 0.36), so 0.3
    # stays. What her reply lets in besides is the rest of its topic (the other bento, other
    # illumination STARS events) above 0.9, and, when the user changes the subject, the old
    # one (the owl episodes when asked her birthday) at 0.99: no threshold separates either.
    # Checked again with hybrid RRF + FTS5 retrieval on the expanded 80-case set (2026-11-26;
    # 64 reference cases, 96/101 relevant items recalled vs 87/101 vector-only): 91/96 relevant
    # candidates clear 0.3 (median 0.9978, p10 0.5404) while 332/1993 irrelevant clear it
    # (median 0.0020, mostly same-topic or follow-up spillover as before), and 12/15 memories
    # clear 0.01 (1/158 irrelevant), so 0.3 / 0.01 stay.
    "Qwen/Qwen3-Reranker-0.6B": RerankThresholds(references=0.3, memories=0.01),
    # From the same set. 4B scores near misses (another year's Christmas, another bento)
    # between 0.4 and 0.7 where 0.6B puts them below 0.3, so it needs a higher bar for the
    # same precision. Its unrelated memories stay below 0.005 but for one, while it scores
    # loosely worded remarks a little higher than 0.6B, so its memory threshold is lower.
    # With her previous reply (2026-10-14) the short follow-ups' relevant candidates all score
    # 0.83 or more, so 0.7 stays; the rest of the topic and an old one get in as with 0.6B.
    # Checked again with hybrid RRF + FTS5 retrieval on the expanded 80-case set (2026-11-26):
    # 85/96 relevant candidates clear 0.7 (median 0.9966, p10 0.6169), 259/1995 irrelevant clear
    # it (median 0.0056, p90 0.8357), and 14/15 memories clear 0.005 (2/158 irrelevant), so
    # 0.7 / 0.005 stay.
    "Qwen/Qwen3-Reranker-4B": RerankThresholds(references=0.7, memories=0.005),
}
FALLBACK_MODEL = "Qwen/Qwen3-Reranker-4B"
"""Whose thresholds a model not calibrated gets."""
DEFAULT_THRESHOLDS = KNOWN_THRESHOLDS[DEFAULT_RERANK_MODEL]


def thresholds_for(settings: RerankSettings) -> RerankThresholds:
    """The thresholds of the reranker `settings` describe, as overridden there."""
    thresholds = KNOWN_THRESHOLDS.get(settings.model, KNOWN_THRESHOLDS[FALLBACK_MODEL])
    if settings.min_relevance is not None:
        thresholds = replace(thresholds, references=settings.min_relevance)
    if settings.memory_min_relevance is not None:
        thresholds = replace(thresholds, memories=settings.memory_min_relevance)
    return thresholds


class Reranker(Protocol):
    async def rerank(
        self, query: str, documents: Sequence[str], top_n: int
    ) -> list[tuple[int, float]]:
        """Indexes into `documents` of the (at most) `top_n` most relevant, best first, with
        their relevance scores (0 to 1)."""
        ...


class RerankError(ServiceError):
    pass


class SiliconFlowReranker:
    """SiliconFlow's `/rerank` endpoint."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        client: httpx.AsyncClient | None = None,
        timeout: float = TURN_TIMEOUT,
    ) -> None:
        self.model = model
        self._url = base_url.rstrip("/") + "/rerank"
        self._api_key = api_key
        self._client = client or httpx.AsyncClient(timeout=RERANK_TIMEOUT)
        self._timeout = timeout

    async def rerank(
        self, query: str, documents: Sequence[str], top_n: int
    ) -> list[tuple[int, float]]:
        return await retry_once(lambda: self._rerank(query, documents, top_n))

    async def _rerank(
        self, query: str, documents: Sequence[str], top_n: int
    ) -> list[tuple[int, float]]:
        async with answered("重排服务", self._timeout, RerankError):
            res = await self._client.post(
                self._url,
                json={
                    "model": self.model,
                    "query": query,
                    "documents": list(documents),
                    "top_n": top_n,
                    "return_documents": False,
                },
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
        if res.status_code >= 400:
            raise RerankError(
                f"重排服务返回 {res.status_code}: {res.text[:500]}",
                transient=transient_status(res.status_code),
            )
        try:
            body = res.json()
            results = sorted(body["results"], key=lambda r: -r["relevance_score"])
            ranked = [(int(r["index"]), float(r["relevance_score"])) for r in results]
        except (ValueError, KeyError, TypeError) as e:
            raise RerankError(f"重排服务的返回无法解析（{len(res.text)} 字）") from e
        if any(not 0 <= i < len(documents) for i, _ in ranked):
            raise RerankError(f"重排服务返回了不存在的文档编号：{[i for i, _ in ranked]}")
        tokens = ((body.get("meta") or {}).get("tokens") or {}).get("input_tokens")
        if isinstance(tokens, int):
            bill("tokens", tokens)
        return ranked[:top_n]

    async def aclose(self) -> None:
        await self._client.aclose()
