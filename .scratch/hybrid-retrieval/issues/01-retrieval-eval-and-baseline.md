# 01: 召回评测命令、扩充用例与纯向量基线

**What to build:** 新增 `eidolon eval retrieval` 子命令（复用 `backend/eval/rerank-calibration.toml`，不调重排 API），输出总体与分源（`story` / `facts` / `work`）的 `recall@k`、`MRR` 和漏召回明细，并支持 `--save` / `--compare` 基线对比；扩充一批专有名词、未汉化日文剧情、曲名/演出名、2 字偶像名和短追问召回用例（`reviewed = false`），在本地真实库上跑出纯向量基线留档。背景见 `../spec.md`。

**Blocked by:** None (can start immediately)

**Status:** done

## 已定的设计（详见 spec）

- 子命令签名：`eidolon eval retrieval [--mode vector|fts|hybrid] [--k N] [--file F] [--db P] [--characters P] [--save F] [--compare F]`。
  - 本票先完整跑通 `--mode vector`（混合召回与 FTS5 尚未接入时，`fts` / `hybrid` 可清晰报错提示或留好接缝由票 03 接通）。
- 复用 `backend/eval/rerank-calibration.toml` 的解析与校验逻辑（`rerank_eval.load_calibration`）：
  - 只评测 `kind` 为 `story` / `facts` / `work` 且 `relevant` 非空的用例；跳过 `memory` 和 `relevant = []` 的闲聊题并在输出中说明跳过条数。
  - `k` 默认取 `CANDIDATES_PER_SOURCE`（12）；剧情按 `episode_id` 去重后算排名与命中（同一篇剧情多个段落命中只计最高排位），资料和作品资料按 `origin`（标题路径 / 作品条目标题）匹配。
- 指标口径：
  - `Recall@k`：各用例命中的 `relevant` 数 / `relevant` 总数（同时报告微平均或宏平均、以及「全部命中」用例数，口吻清晰即可）。
  - `MRR`：每个用例首个命中 `relevant` 的 `1 / rank`（未命中为 `0`）取平均。
  - 列出每条漏召回的用例 ID 及其漏掉的 `relevant` 编号/标题。
  - `--save <path>` 写 JSON（含 mode、k、summary、by_kind、per_case）；`--compare <path>` 读 JSON 并打印 ΔRecall@k、ΔMRR、新找回与新漏掉的用例。
- 扩充评测用例（追加到 `backend/eval/rerank-calibration.toml`，严格遵守 ADR-0003 只写编号与标题、不写剧情原文，标 `reviewed = false`）：
  - 结合本地 `eidolon.db`、`characters/facts/`、`characters/world.json` 起草约 15–25 条新题，重点覆盖：冷门卡名/活动名、未汉化日文剧情（`imported_from = 'json'`）、歌曲/唱片/演出名、2 字角色名及日语原名/片假名、带 `previous` 的短追问。

## 验收

- [x] 新增单元测试 `backend/tests/test_retrieval_eval.py`：覆盖 `Recall@k`、MRR 计算、同一剧情多段落去重计最高排位、跳过 `memory` 和空 `relevant`、`--save` / `--compare` 差值与新找回/新漏掉清单。
- [x] `eidolon eval retrieval --help` 与 `__main__.py` 帮助文档包含该子命令。
- [x] `backend/eval/rerank-calibration.toml` 通过加载校验（所有 `work` 标题能在 `characters/world.json` 中找到、无重复 `id`、不含剧情原文）。
- [x] `backend/` 下相关测试、`pyright`、`ruff check` 通过。
- [x] **人工验收**（agent 先跑并把纯向量基线结果记入 Comments，待用户校对新增的 `reviewed = false` 用例）：在本地 `eidolon.db` 上跑 `eidolon eval retrieval --mode vector`，确认新旧用例里确实暴露出纯向量的漏召回样本。

## Comments

### 实现说明（票 01）

- 新增 `backend/src/eidolon/retrieval_eval.py`：实现 `validate_retrieval_options`、`evaluate_retrieval`、`summarize_retrieval`、`save_baseline`、`load_baseline`、`compare_retrieval`、`report_retrieval`；跳过 `memory` 与 `relevant = []` 用例，各源按 `origin` 去重并保留最高排位（剧情按 `episode_id`），统计微/宏平均 `Recall@k`、全命中率、至少命中 1 条数、MRR 与漏召回明细，支持 `--save` / `--compare`。
- 扩展 `backend/src/eidolon/retrieval.py`：`ReferenceSources.candidates` 新增可选参数 `limit: int = CANDIDATES_PER_SOURCE`，保持默认行为不变。
- 更新 `backend/src/eidolon/__main__.py`：新增 `eidolon eval retrieval [--mode vector|fts|hybrid] [--k N] [--file F] [--db P] [--characters P] [--save F] [--compare F]` 与帮助文档，不要求 `SILICONFLOW_API_KEY`。
- 扩充 `backend/eval/rerank-calibration.toml`：遵守 ADR-0003（只含编号与标题，不含剧情原文），追加 20 条 `reviewed = false` 召回用例（总计 80 条），覆盖冷门卡名/活动名、未汉化日文剧情（`imported_from = 'json'`）、歌曲/唱片/演出名、2 字偶像名/日语原名/片假名、带 `previous` 的短追问；全部剧情编号、出场角色、角色资料与作品资料标题均已核对真实存在。
- 新增 `backend/tests/test_retrieval_eval.py` 单元测试，并与 `test_rerank_eval.py`、`pyright`、`ruff check`、`affected-tests.sh` 全部通过。

### 本地纯向量基线（2026-11-26）

命令：`eidolon eval retrieval --mode vector --db data/eidolon.db --characters ../characters/characters.toml`（`k = 12`）

- 评测范围：评测 60 条（跳过 20 条：`memory` 16 条，`relevant` 为空 4 条）
- 总体：`Recall@12 86.1%`（87/101，宏平均 86.9%），全命中 47/60，至少命中 1 条 56/60，`MRR 0.8235`
- 分源：
  - `story`（33 条）：`Recall@12 85.1%`（57/67，宏平均 86.9%），全命中 24/33，至少命中 1 条 32/33，`MRR 0.8949`
  - `facts`（14 条）：`Recall@12 88.9%`（16/18，宏平均 89.3%），全命中 12/14，至少命中 1 条 13/14，`MRR 0.7589`
  - `work`（13 条）：`Recall@12 87.5%`（14/16，宏平均 84.6%），全命中 11/13，至少命中 1 条 11/13，`MRR 0.7115`
- 漏召回（13 条，新旧用例均暴露漏召回）：
  - `mano-story-flower-bird-park-arc`（漏 `produce_events/100100401`）
  - `mano-story-bench-nap`（漏 `produce_events/200100411`）
  - `kogane-story-leaving-home`（漏 `produce_events/100400504`）
  - `kogane-story-homecoming-live`（漏 `produce_events/600400109`）
  - `kogane-work-release-wing03`（漏 `唱片《THE IDOLM@STER SHINY COLORS BRILLI@NT WING 03 バベルシティ・グレイス》（LACM-14783）`）
  - `mano-followup-hatsumoude-wish`（漏 `produce_events/200100602`）
  - `kogane-followup-mamimi-pronoun`（漏 `produce_events/300501501`）
  - `kogane-followup-genwaku-cd`（漏 `唱片《THE IDOLM@STER SHINY COLORS BRILLI@NT WING 03 バベルシティ・グレイス》（LACM-14783）`）
  - `mano-followup-topic-change-birthday`（漏 `档案 / 基本信息`）
  - `fuyuko-story-starring-f`（新增，漏 `produce_events/201800703`、`produce_events/201800704`）
  - `rinze-story-kaidan`（新增，漏 `game_event_communications/400102108`）
  - `fuyuko-json-miramira`（新增，漏 `produce_events/301802302`）
  - `luca-json-by-spiral`（新增，漏 `game_event_communications/400106407`）

### 审查记录（票 01，基点 `545b0134`）

- Standards 轴：合并了 `test_retrieval_eval.py` 中同 setup 拆分的 `test_report_retrieval_shows_metrics_skipped_and_missed`（CODING_STANDARDS 冗余测试）；抽出了 `validate_retrieval_options` 与 `_metric_delta` 消除重复逻辑；将 `_format_delta` 中的缩写变量展开。保留判断题：`compare_retrieval` 返回结构化 dict（与 `summarize_retrieval` 的 JSON 序列化口径一致，不另建包装类）。
- Spec 轴：无缺漏、无范围外行为；观察到新增用例 `hiori-json-father-gift` 的 `acceptable` 项为已汉化 `csv` 剧情（不影响 `relevant` 计分），留作人工校对提示。
