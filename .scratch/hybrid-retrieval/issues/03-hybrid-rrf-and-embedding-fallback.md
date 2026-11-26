# 03: 三源 RRF 混合召回、查询串分流与向量化降级

**What to build:** 把票 02 的三源 FTS5 检索通过 RRF 融合接入 `ReferenceSources`、`Retrieval`（常规参考资料与判断模型预回忆）以及 `recall_story` 工具；实现 FTS5 的查询串分流（优先当前句、短追问补上一句）与向量化/重排失败时的优雅降级；同时打通票 01 的 `eidolon eval retrieval --mode fts|hybrid`。背景见 `../spec.md`。

**Blocked by:** 01, 02

**Status:** done

## 已定的设计（详见 spec）

- **单源混合检索与 RRF 融合**：
  - 扩展 `ReferenceSource`（`references.py`）与各源实现（`StoryReferences`、`CharacterFacts`、`WorkFacts`），支持同时接收向量查询与全文查询串（向量为 `None` 时仅走 FTS5，全文串为空时仅走向量）。
  - 各源分别取向量 Top-`N` 与 FTS5 Top-`N`（初值 `N = CANDIDATES_PER_SOURCE * 2` 即 24），按 RRF（`k = 60`）合并去重后取前 `CANDIDATES_PER_SOURCE`（12）条返回；`Reference.similarity`（或等价分数）承载最终用于降级排序的 RRF 分数。
  - 回顾剧情（判断模型触发的预回忆与 `recall_story` 工具）查剧情库和作品资料的 `live` / `release` 条目同样走混合召回 + RRF 融合。
  - 记忆（`MemoryTurn`）不变，仍走纯向量 + 重排。
- **FTS5 查询串分流**：
  - 常规回合：向量化仍用 `memory_query(history, text)`；FTS5 优先只对用户当前 `text` 切词，仅当 `text` 去掉停用词后的有效 token 数 `< 2` 且存在上一句回复时，才改用 `memory_query(history, text)`。
  - `recall_story` 工具：向量与 FTS5 均直接用模型写出的 `query`。
- **降级行为**：
  - **向量化失败（`EmbeddingError`）**：常规回合的参考资料检索与回顾剧情不放弃，自动用 FTS5 候选送重排（若重排也失败则取 FTS5 前 `FALLBACK_REFERENCES` 条 / 回顾剧情取最优 1 篇剧情与 1 条作品资料）；记忆仍按原规则不带。
  - **重排失败（`RerankError`）**：参考资料按融合分取前 `FALLBACK_REFERENCES`（3）条；回顾剧情按融合分取最优剧情与作品条目。
  - **提前检索并发**：向量化任务与 FTS5 检索在判断模型作答前并行启动；判断为「不用查」时丢弃结果、不调重排。
- **评测接通**：`eidolon eval retrieval` 支持 `--mode vector`、`--mode fts`、`--mode hybrid`，与真实回合走完全一致的召回和分流逻辑。

## 验收

- [x] `backend/tests/test_retrieval.py`：
  - 假向量化返回无关向量时，靠关键词仍能把对应剧情/角色资料/作品资料召回并送重排、进入提示词；
  - 短追问（如「那时候累吗」）FTS5 补上上一句词，正常带专有名词的句子不被上一句稀释；
  - 向量化失败（`EmbeddingError`）时，参考资料仍通过 FTS5 召回并送重排进入提示词（重排同时失败时降级取 FTS5 前几条），记忆不带；
  - 重排失败（`RerankError`）时，按 RRF 融合分选降级候选；
  - 判断为「不用查」时不调重排、提示词不带资料。
- [x] `backend/tests/test_recall_story.py` / `test_world_retrieval.py`：
  - 判断模型预回忆与 `recall_story` 工具均走混合召回（假向量无关时靠关键词仍能想起剧情与演出/唱片）；
  - 向量化失败时，预回忆与 `recall_story` 工具降级走 FTS5，不再直接返回「暂时想不起来」。
- [x] `backend/tests/test_retrieval_eval.py`：`--mode vector|fts|hybrid` 全部跑通并能互相对比。
- [x] `backend/` 下相关测试、`pyright`、`ruff check` 通过；`sh scripts/affected-tests.sh <基点>` 通过。

## Comments

### 票 01 交接

- `backend/src/eidolon/retrieval_eval.py` 的 `validate_retrieval_options` 与 `evaluate_retrieval` 已为 `--mode fts|hybrid` 留好接缝，目前仅放行 `vector`（`fts` / `hybrid` 抛出 `RetrievalEvalError`）。本票接入三源混合召回与 FTS5 查询串分流后，直接放开这两种模式并复用与真实回合一致的检索逻辑；同时注意 `--mode fts` 时不要求 `EmbeddingSettings`（无需向量化客户端）。

### 票 02 交接

- `StoryCorpus.search_by_text`、`CharacterFacts.search_by_text` 与 `WorkFacts.search_by_text` / `search_entries_by_text` 均已就绪，返回的 `score` / `similarity` 已取 `0.0 - bm25(...)`（正值，越大越相关）；多路合并请调用 `text_search.rrf_fuse` 并传入各自去重键。
- 重要细节（来自票 02 Spec 审查）：在当前 CJK 2-gram + `STOPWORDS` 下，规格示例短追问「那时候累吗」会产生 3 个查询 token（`["那时", "候累", "累吗"]`），而 `spec.md` 初值阈值是 `< 2`。票 03 实现短追问分流时请结合 `query_tokens(text)` 实测（并在测试和票 04 调参中关注 2-gram 跨边界切词对短追问有效 token 计数的影响，如按需将阈值设为常量供票 04 校准，或评估在短追问判断上是否需考虑字数/有效词数）。

### 实现说明（票 03）

- `backend/src/eidolon/references.py`：扩展 `ReferenceSource` 协议支持 `search(..., query=None)` 与 `search_by_text(...)`，新增 `HYBRID_CANDIDATE_MULTIPLIER = 2`、`fuse_references` 与 `search_hybrid_references`（按 `(origin, text)` 去重保留同篇剧情不同片段，RRF 融合分写入 `Reference.similarity`；有非空 `query` 时单源向量化失败单独降级走 FTS5）。
- `backend/src/eidolon/retrieval.py`：`StoryReferences` 实现 `search_by_text` 与混合 `search`；`ReferenceSources` 新增 `fts_candidates_by_source`、`fuse_with_fts` 并扩展 `candidates` / `rank`；导出短追问阈值 `FTS_MIN_STANDALONE_TOKENS = 4` 与分流函数 `fts_query_for_reply` / `fts_turn_query`；`Retrieval._find` 与 `recall_story` 在判断模型作答前并行启动向量化与 FTS5 检索（`nothing` 时一并取消）；`EmbeddingError` 时参考资料与回顾剧情均用 FTS5 候选继续送重排（双故障则按 RRF/FTS 排名降级，不再直接返回「暂时想不起来」，记忆仍不带）。
- `backend/src/eidolon/facts.py` & `work_facts.py`：`CharacterFacts.search` 与 `WorkFacts.search` 接入 `search_hybrid_references`；`WorkFacts.search_entries` 支持 `RECALL_KINDS` 下的混合 RRF、`query_vector=None` 纯 FTS5 与 `EmbeddingError` 降级。
- `backend/src/eidolon/retrieval_eval.py`、`embedding.py`、`__main__.py`：放通 `eidolon eval retrieval --mode vector|fts|hybrid`，共用 `fts_query_for_reply` 分流；`--mode fts` 使用 `NoEmbedder`（补齐 `aclose()`），不要求配置 `EmbeddingSettings`。
- 判断说明：CJK 2-gram 步长为 1，短追问「那时候累吗？」产生 3 个 token（`['那时', '候累', '累吗']`），典型短追问在 1–3 个 token、正常专有名词句 ≥ 4，因此将阈值初值设为 `FTS_MIN_STANDALONE_TOKENS = 4` 并导出供票 04 实测校准；跨源降级统一用 RRF 分数避免 BM25 与余弦尺度失衡。

### 审查记录（票 03，基点 `dd3bf037`）

- Standards 轴：无文档规范违规。已按建议提取 `_is_short_followup` 消除 `fts_query_for_reply` 与 `fts_turn_query` 的条件重复，并内联 `Retrieval._find` 中的单行中转 `_hybrid_candidates`。保留判断题：`references.py` / `work_facts.py` / `retrieval.py` 三处混合+降级函数以及三个 `ReferenceSource.search` 适配层各自承载不同的输入输出类型（`Reference`、`WorkEntry`、预启动的 `fts_task`），不过度泛型抽象；`_look_up`/`_recall_turn` 参数组保持现有可读签名。
- Spec 轴：无缺漏、无范围外行为、无逻辑错误。记录两项交接给票 04：`rerank_eval.py` 调 `sources.rank` 尚未传 `fts_text`，以及 4 字中文词（3 个 2-gram）在 `FTS_MIN_STANDALONE_TOKENS = 4` 下会拼入上一句，均由票 04 在真实库实测时一并校准。
