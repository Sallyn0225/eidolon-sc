# 04: 真实库基线对比、参数定型与文档收尾

**What to build:** 在人工校对后的扩充评测集上，用本地真实 `eidolon.db` 对比 `vector` / `fts` / `hybrid` 三种模式的 `Recall@k` 和 `MRR`，按实测结果定型 RRF `k`、单路候选数和短追问 token 阈值；再跑 `eidolon eval rerank` 验证重排分数线与误放行不恶化；最后清扫过时的注释、docstring 和相关文档。背景见 `../spec.md`。

**Blocked by:** 03

**Status:** done

## 已定的设计（详见 spec）

- **落地门槛**：`hybrid` 必须在总体 `Recall@k` 和 `MRR` 上高于纯向量基线（尤其专有名词、未汉化日文剧情和作品资料题），且 `eidolon eval rerank` 的误放行率不恶化、现有分数线仍然有效（若需微调参数，把对比数据记清）。
- **文档边界**：
  - `GLOSSARY.md` 不改，不新增 ADR。
  - 清扫 `corpus.py`、`retrieval.py`、`references.py`、`rerank.py`、`__main__.py` 等处描述旧行为（「纯向量」「向量化失败就不查资料」）的 docstring 与注释。
  - 检查 `docs/configuration*.md` / `docs/deploy.md` / `README*.md` 是否有需要同步说明的地方（如 `eidolon eval retrieval` 或向量化失败降级说明；无相关描述处不必硬加）。

## 验收

- [x] 扩充进 `backend/eval/rerank-calibration.toml` 的新用例已由用户校对并标 `reviewed = true`。
- [x] 在本地 `eidolon.db` 上跑完 `eidolon eval retrieval --mode vector`（基线）、`--mode fts`、`--mode hybrid --compare <baseline>`，确认 `hybrid` 的 `Recall@k` 与 `MRR` 优于纯向量基线，完整数据记入本票 Comments。
- [x] 跑完 `eidolon eval rerank`，确认重排分数线与误放行无恶化，校准记录写入 `rerank.py` 与本票 Comments。
- [x] 检查并更新所有受影响模块的 docstring、注释与相关文档；确认不留临时基线 JSON 文件在未跟踪目录中（是否提交正式基线 JSON 由用户决定）。
- [x] `backend/` 下 `pytest`、`pyright`、`ruff check` 全部通过；`sh scripts/affected-tests.sh <基点>` 通过。

## Comments

### 票 01 交接

- `backend/eval/rerank-calibration.toml` 新增 20 条 `reviewed = false` 召回用例（总计 80 条），人工校对时可一并留意 `hiori-json-father-gift` 的 `acceptable` 项（`produce_events/200200711` 为 `csv` 汉化剧情，`relevant` 项 `produce_events/200200703` 为未汉化 `json` 剧情）。
- 票 01 本地纯向量基线（`k = 12`，60 条有效题）：总体 `Recall@12 86.1%`（87/101）、`MRR 0.8235`，共 13 条漏召回（详见票 01 Comments）。

### 票 03 交接

- 可调参数常量：
  - `backend/src/eidolon/text_search.py`: `RRF_K = 60`
  - `backend/src/eidolon/references.py`: `HYBRID_CANDIDATE_MULTIPLIER = 2`（单路 Top-24）
  - `backend/src/eidolon/retrieval.py`: `FTS_MIN_STANDALONE_TOKENS = 4`（当前按 CJK 2-gram 设的初值，使「那时候累吗？」的 3 个 token 补入上文；注意 4 字中文专有名词如「草莓大福」也是 3 个 2-gram，实测时请对比 `2 / 3 / 4` 对短追问和换话题题的影响）。
- `backend/src/eidolon/rerank_eval.py` 调用 `sources.rank(...)` 时目前未传 `fts_text`（默认用 `query_text` 同时做向量与 FTS5）。票 04 跑 `eidolon eval rerank` 前请检查并传入 `fts_text=fts_query_for_reply(case.previous, case.query)`，使重排校准与真实回合的混合召回口径完全一致。

### 实现说明（票 04）

- **统一评测口径**：`backend/src/eidolon/rerank_eval.py` 调 `sources.rank(...)` 时改为传入 `fts_text=fts_query_for_reply(case.previous, case.query)`，并在 `backend/tests/test_rerank_eval.py` 补充追问与换话题分流断言。
- **修复无正文 FTS5 `bm25()` 恒为 0 的 SQLite 缺陷**：在本地真实库（SQLite 3.50.4）实测发现无正文表（`content=''`）加 `detail='column'` 会导致 `bm25()` 恒返回 `-0.0`、完全失去相关性排序。`backend/src/eidolon/corpus.py` 改为使用默认 `detail='full'`，并在 `_open` 中通过 `sqlite_master` 自动检测旧的 `detail='column'` 建表语句，一次性重建并回填 `episode_passages_fts`（同步在 `test_story_corpus.py` 补全正分值、词频排序与旧表自动迁移测试）。注：内存 FTS5（`MemoryFtsIndex`）非无正文表，`bm25()` 返回正常分值，保持 `detail='column'` 不变。
- **定型参数与加权 RRF**：
  - `RRF_K = 15`（`text_search.py`）：对单源 Top-24 短列表比 `k = 60` 更能区分头部排位；
  - `HYBRID_CANDIDATE_MULTIPLIER = 2`（`references.py`，单路 Top-24）保持不变；
  - `FTS_RRF_WEIGHT = 0.9`（`references.py`，通过 `rrf_fuse(..., weights=...)` 与共享函数 `fuse_hybrid` 统一应用于 `fuse_references` 和 `WorkFacts.search_entries`）：因为作品资料的纯 FTS5 召回较弱（37.5% vs 向量 87.5%），将 FTS5 权重微调为 `0.9` 在并列时优先保住高置信度向量 Top-1，同时仍能把双命中和强 FTS5 独占条目拉进重排池；
  - `FTS_MIN_STANDALONE_TOKENS = 7`（`retrieval.py`）：经实测放宽至 7，使 4–6 token 的短追问带入上一句回复，而 7+ token 的独立/换话题句（如 `灯織ちゃんは元気？`、`对了，你生日是几号来着？`）不被上一句稀释。
- **重排校准与文档清扫**：
  - 将 2026-11-26 混合召回下的 0.6B / 4B 校准结果补记进 `backend/src/eidolon/rerank.py`（现有阈值 `0.3 / 0.01` 与 `0.7 / 0.005` 保持有效不变）。
  - 更新 `corpus.py`、`facts.py`、`work_facts.py`、`retrieval.py`、`rerank_eval.py` 的旧注释与 docstring，并同步更新 `README*.md`、`docs/configuration*.md`、`docs/deploy.md` 中关于混合召回、`eidolon eval retrieval`、向量化失败降级与 `eidolon reembed` 期间 FTS5 仍可用的说明（未改 `GLOSSARY.md`，未新增 ADR）。

### 本地真实库召回对比数据（2026-11-26）

数据集：`backend/eval/rerank-calibration.toml`（80 条均 `reviewed = true`；有效评测 60 条，跳过 `memory` 16 条与 `relevant` 为空 4 条），`k = 12`，本地 `backend/data/eidolon.db`：

| 模式 | 总体 Recall@12 | 总体 MRR | story Recall@12 / MRR | facts Recall@12 / MRR | work Recall@12 / MRR |
|---|---:|---:|---:|---:|---:|
| `vector`（基线） | 86.1%（87/101，宏 86.9%） | 0.8235 | 85.1%（57/67）/ 0.8949 | 88.9%（16/18）/ 0.7589 | 87.5%（14/16）/ 0.7115 |
| `fts` | 80.2%（81/101，宏 78.6%） | 0.6449 | 89.6%（60/67）/ 0.7682 | 83.3%（15/18）/ 0.6571 | 37.5%（6/16）/ 0.3187 |
| `hybrid`（定型） | **95.0%**（96/101，宏 93.3%） | **0.8410** | **97.0%**（65/67）/ **0.9129** | **94.4%**（17/18）/ **0.7857** | **87.5%**（14/16）/ **0.7179** |
| `hybrid` vs `vector` | **+8.9%**（全命中 47→55/60） | **+0.0175** | **+11.9%** / **+0.0179** | **+5.6%** / **+0.0268** | **+0.0%** / **+0.0064** |

- 新找回（10 条用例、11 个相关项，全部 4 条新增纯向量漏召回题均找回）：
  - `mano-story-flower-bird-park-arc`（`produce_events/100100401`）
  - `mano-story-bench-nap`（`produce_events/200100411`）
  - `kogane-story-homecoming-live`（`produce_events/600400109`）
  - `mano-followup-hatsumoude-wish`（`produce_events/200100602`）
  - `kogane-followup-mamimi-pronoun`（`produce_events/300501501`）
  - `mano-followup-topic-change-birthday`（`档案 / 基本信息`）
  - `fuyuko-story-starring-f`（`produce_events/201800703`、`produce_events/201800704`）
  - `rinze-story-kaidan`（`game_event_communications/400102108`）
  - `fuyuko-json-miramira`（`produce_events/301802302`）
  - `luca-json-by-spiral`（`game_event_communications/400106407`）
- 新漏掉（2 条）：`mano-facts-hiori`（`produce_events/300201401`，主条目 `人物关系 / 風野灯織@3` 仍在）、`hiori-json-father-gift`（`produce_events/200200703`，`档案 / 家人与家务@1` 仍在）。
- 剩余未命中（共 5 条）：上述 2 条及原基线已漏的 `kogane-story-leaving-home`、`kogane-work-release-wing03`、`kogane-followup-genwaku-cd`。

### 重排校准数据（`eidolon eval rerank`，2026-11-26）

在定型后的混合召回 + 80 条完整校准集（64 条参考资料题 + 16 条记忆题）上实测：

- `Qwen/Qwen3-Reranker-0.6B`（阈值 `0.3` / `0.01`）：
  - 参考资料：91/96 相关候选过线（中位数 `0.9978`，p10 `0.5404`），不相关过线 332/1993（中位数 `0.0020`，主要为同主题剧情或追问延伸，与此前一致）；
  - 记忆：12/15 相关过线，1/158 不相关过线。结论：维持 `0.3 / 0.01`。
- `Qwen/Qwen3-Reranker-4B`（阈值 `0.7` / `0.005`）：
  - 参考资料：85/96 相关候选过线（中位数 `0.9966`，p10 `0.6169`），不相关过线 259/1995（中位数 `0.0056`，p90 `0.8357`）；
  - 记忆：14/15 相关过线，2/158 不相关过线。结论：维持 `0.7 / 0.005`。

### 审查记录（票 04，基点 `a443d557`）

- Standards 轴：无文档规范违规。已采纳建议在 `references.py` 提取共享函数 `fuse_hybrid`，统一 `fuse_references` 与 `WorkFacts.search_entries` 的加权 RRF 融合策略，消除重复。
- Spec 轴：已补改 `docs/configuration.md` / `.en.md` / `.ja.md` 与 `docs/deploy.md` 中 `eidolon reembed` 运行期间仍写「只查得到已完成部分」的旧描述。保留两项基于实测的判断并记录于此：
  1. 剧情库无正文 FTS5 从 `spec.md` 原定的 `detail='column'` 改为默认 `detail='full'`（附旧表自动重建），原因是 SQLite 3.50.4 在 `content=''` + `detail='column'` 下 `bm25()` 恒为 `0.0`，无法排序；
  2. 引入 `FTS_RRF_WEIGHT = 0.9` 并定型 `RRF_K = 15`、`FTS_MIN_STANDALONE_TOKENS = 7` 是由实测数据驱动（使三源 `Recall@12` 与 `MRR` 全部高于或持平纯向量基线，总体 `+8.9%` / `+0.0175`）；4–6 token 短独立句会附带上一句的权衡已知，留待后续如扩展词级分词时再复评。
