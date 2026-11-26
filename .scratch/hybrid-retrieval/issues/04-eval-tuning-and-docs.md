# 04: 真实库基线对比、参数定型与文档收尾

**What to build:** 在人工校对后的扩充评测集上，用本地真实 `eidolon.db` 对比 `vector` / `fts` / `hybrid` 三种模式的 `Recall@k` 和 `MRR`，按实测结果定型 RRF `k`、单路候选数和短追问 token 阈值；再跑 `eidolon eval rerank` 验证重排分数线与误放行不恶化；最后清扫过时的注释、docstring 和相关文档。背景见 `../spec.md`。

**Blocked by:** 03

**Status:** ready-for-agent

## 已定的设计（详见 spec）

- **落地门槛**：`hybrid` 必须在总体 `Recall@k` 和 `MRR` 上高于纯向量基线（尤其专有名词、未汉化日文剧情和作品资料题），且 `eidolon eval rerank` 的误放行率不恶化、现有分数线仍然有效（若需微调参数，把对比数据记清）。
- **文档边界**：
  - `GLOSSARY.md` 不改，不新增 ADR。
  - 清扫 `corpus.py`、`retrieval.py`、`references.py`、`rerank.py`、`__main__.py` 等处描述旧行为（「纯向量」「向量化失败就不查资料」）的 docstring 与注释。
  - 检查 `docs/configuration*.md` / `docs/deploy.md` / `README*.md` 是否有需要同步说明的地方（如 `eidolon eval retrieval` 或向量化失败降级说明；无相关描述处不必硬加）。

## 验收

- [ ] 扩充进 `backend/eval/rerank-calibration.toml` 的新用例已由用户校对并标 `reviewed = true`。
- [ ] 在本地 `eidolon.db` 上跑完 `eidolon eval retrieval --mode vector`（基线）、`--mode fts`、`--mode hybrid --compare <baseline>`，确认 `hybrid` 的 `Recall@k` 与 `MRR` 优于纯向量基线，完整数据记入本票 Comments。
- [ ] 跑完 `eidolon eval rerank`，确认重排分数线与误放行无恶化，校准记录写入 `rerank.py` 与本票 Comments。
- [ ] 检查并更新所有受影响模块的 docstring、注释与相关文档；确认不留临时基线 JSON 文件在未跟踪目录中（是否提交正式基线 JSON 由用户决定）。
- [ ] `backend/` 下 `pytest`、`pyright`、`ruff check` 全部通过；`sh scripts/affected-tests.sh <基点>` 通过。

## Comments
