# 01: 召回评测命令、扩充用例与纯向量基线

**What to build:** 新增 `eidolon eval retrieval` 子命令（复用 `backend/eval/rerank-calibration.toml`，不调重排 API），输出总体与分源（`story` / `facts` / `work`）的 `recall@k`、`MRR` 和漏召回明细，并支持 `--save` / `--compare` 基线对比；扩充一批专有名词、未汉化日文剧情、曲名/演出名、2 字偶像名和短追问召回用例（`reviewed = false`），在本地真实库上跑出纯向量基线留档。背景见 `../spec.md`。

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

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

- [ ] 新增单元测试 `backend/tests/test_retrieval_eval.py`：覆盖 `Recall@k`、MRR 计算、同一剧情多段落去重计最高排位、跳过 `memory` 和空 `relevant`、`--save` / `--compare` 差值与新找回/新漏掉清单。
- [ ] `eidolon eval retrieval --help` 与 `__main__.py` 帮助文档包含该子命令。
- [ ] `backend/eval/rerank-calibration.toml` 通过加载校验（所有 `work` 标题能在 `characters/world.json` 中找到、无重复 `id`、不含剧情原文）。
- [ ] `backend/` 下相关测试、`pyright`、`ruff check` 通过。
- [ ] **人工验收**（agent 先跑并把纯向量基线结果记入 Comments，待用户校对新增的 `reviewed = false` 用例）：在本地 `eidolon.db` 上跑 `eidolon eval retrieval --mode vector`，确认新旧用例里确实暴露出纯向量的漏召回样本。

## Comments
