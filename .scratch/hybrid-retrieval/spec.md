# 检索混合召回与召回评测：FTS5 全文召回、RRF 融合与 recall@k 基线

Status: ready-for-agent

术语以 `GLOSSARY.md` 为准，本轮不新增或改动术语，也不新增 ADR（分词与无正文 FTS5 索引可随时从已有原文在数秒内丢弃重建，选型权衡记在本规格的 Decisions 与模块 docstring 中）。遵守 ADR-0002（共享记忆）、ADR-0003（剧情不随仓库分发，评测集只含编号与标题，不含原文）、ADR-0012（数据库备份）、ADR-0028（写入走单写者线程，事件循环上不直接碰数据库）。

起因是参考已开源的 [LAPLACE Eidolon](https://github.com/laplace-live/eidolon)（`docs/retrieval.md`）并收尾 `.scratch/retrieval-and-hotwords/spec.md`「Out of Scope」中留下的两项：关键词检索（BM25 / FTS）与 `recall@k / MRR` 召回评测。

## Problem Statement

- **专有名词与未汉化剧情纯向量容易漏召回。** 剧情库目前有 8,039 篇剧情（5,342 篇中译 + 2,697 篇未汉化日文，共 14,525 段），角色资料与作品资料合计 1,995 条。用户问起冷门卡名、活动名、歌曲名、演出名、2 字偶像名或日语原文词时，纯向量检索容易把真正对应的段落或条目排在 `CANDIDATES_PER_SOURCE`（12）之外，后面的重排模型根本看不到。
- **没有端到端召回基线。** 现有的 `eidolon eval rerank` 必须调外部重排 API、重心在定重排分数线；调整召回策略时缺少零重排费用的 `recall@k` / `MRR` 对比基线。
- **向量化服务抖动时参考资料完全不可用。** 目前回合中 `EmbeddingError` 会直接放弃参考资料和回顾剧情（角色只能回答想不起来），明明剧情和资料原文都在本地 SQLite / 内存里。

## Solution

- **新增独立召回评测命令 `eidolon eval retrieval`（票 01）。** 复用并扩充 `backend/eval/rerank-calibration.toml`（增补冷门卡名/活动名、未汉化日文剧情、曲名/演出名、2 字人名和短追问召回题），不调重排 API，支持 `--mode vector|fts|hybrid` 与 `--save / --compare` 基线对比，输出总体及分源（`story` / `facts` / `work`）的 `recall@k`、`MRR` 和漏召回明细。
- **零外部依赖的 CJK 2-gram + ASCII 全文索引（票 02）。**
  - 剧情库在 `eidolon.db` 中持久化无正文 FTS5 表（`content=""`, `contentless_delete=1`, `detail="column"`, `tokenize="unicode61"`），约占 24 MB，随导入/同步/删除增量维护，旧库首次打开自动建表并补建一次；查询在 SQLite 内直接 `JOIN episode_cast` 按角色过滤。
  - 角色资料与作品资料不入库，在内存按需建 `:memory:` FTS5（与 `EmbeddedTexts` 首次搜索加载生命周期一致）；角色资料把 `Fact.title` 和 `Fact.text` 合并索引。
- **三源 RRF 混合召回、查询串分流与向量化降级（票 03）。**
  - 常规参考资料检索与回顾剧情（判断模型预回忆 + `recall_story` 工具）共用混合召回：各源并行取向量 Top-N 与 FTS5 BM25 Top-N，用 RRF 合并去重后取前 `CANDIDATES_PER_SOURCE` 条送重排。记忆维持纯向量 + 重排不变。
  - 常规检索时向量仍用 `memory_query`（上一句回复 + 用户这句话），FTS5 优先只用用户这句话，仅在有效词极少（短追问）时补上上一句；`recall_story` 工具两边都用模型写的 `query`。
  - 向量化失败（`EmbeddingError`）时，参考资料和回顾剧情退回用 FTS5 候选送重排（重排也失败则取 FTS5 前几条）；重排失败（`RerankError`）时，降级排序改按 RRF 融合分。
- **基线对比与参数定型（票 04）。** 在校对后的扩充评测集上实测 `vector` / `fts` / `hybrid`，验证 `hybrid` 在 `recall@k` 与 `MRR` 上优于纯向量基线，再跑 `eidolon eval rerank` 确认重排误放行不恶化后定稿参数。

## User Stories

1. 作为用户，我提到一张冷门卡名、活动名、歌曲名或演出名时，希望角色更稳定地想起对应的剧情或作品资料，不因向量漏召回而答非所问。
2. 作为用户，我用中文夹杂日语原名、片假名或 2 字角色名提问，或问到尚未汉化的日文剧情里的专有名词时，希望角色照样能查到相关剧情和角色资料。
3. 作为用户，我在短追问（「那时候累吗」）时，希望不会因为全文检索只看当前句而丢掉上下文；在换话题或正常发问时，希望全文检索不被角色上一句长回复稀释关键词。
4. 作为用户，当外部向量化服务临时超时或不可用时，希望角色依然能凭关键词想起明显的剧情、角色资料和作品资料，而不是整回合失去所有参考资料。
5. 作为开发者，我希望改召回逻辑时有一条不花重排费用、几秒跑完的 `eidolon eval retrieval --save / --compare` 命令，能直观看到 `recall@k`、`MRR` 和每道题的漏召回变化。

## Decisions

### 覆盖范围

- **只覆盖参考资料三项**（剧情库、角色资料、作品资料），**记忆不动**。记忆按用户动态增删且单用户条数少、多为口语描述，纯向量 + 重排已足够。
- **常规参考资料检索与回顾剧情共用混合召回**（含判断模型触发的预回忆和 `recall_story` 工具；回顾剧情查作品资料里的 `live` / `release` 同样走混合召回）。

### 分词与匹配（票 02）

- **选用零外部依赖的 CJK 2-gram + ASCII 小写整词**，走 SQLite FTS5 `unicode61`：
  - 连续中日文字符（平假名、片假名、汉字）按 2-gram 切分（长度 ≤ 2 保留原词），连续 ASCII 字母/数字保持小写整词（`W.I.N.G.` 可由字母段切出，连字符/点号作分隔）。
  - **为什么不用 SQLite 原生 `trigram`**：`trigram` 要求查询词至少 3 个字符，导致 `真乃`、`灯織`、`恋鐘`、`写真` 等大量 2 字中文/日语专有名词完全匹配不到。
  - **为什么不引入 `jieba` / 日语分词库**：剧情库含 2,697 篇未汉化日文和大量二次元人名/卡名/片假名，`jieba` 不处理日语且需额外依赖与词典维护；CJK 2-gram 零依赖、中日英统一，局部误命中由后续重排模型过滤。
- **停用词规则**：**入库端不去停用词**（去停用词会破坏 BM25 长度归一化与词频分布），**仅在查询端跳过高频虚词与口语停用词**（如「的」「了」「吗」「呢」「啊」「什么」「怎么」「一下」等常见中文/日文功能词），并去掉标点。
- **匹配语法**：查询切词去重后以 `OR` 组合送给 FTS5 `MATCH`（双引号安全转义每个 token，避免 FTS5 保留字 `AND`/`OR`/`NOT`/`NEAR` 或特殊字符引发语法错误），靠 BM25 的 IDF 自动给命中稀有专有名词的条目高分。查询没有任何有效 token 时直接返回空列表，不查 FTS5。

### 索引存放与生命周期（票 02）

- **剧情库持久化无正文 FTS5 表**：在 `eidolon.db` 中建 `episode_passages_fts`（`CREATE VIRTUAL TABLE IF NOT EXISTS episode_passages_fts USING fts5(tokens, content='', contentless_delete=1, tokenize='unicode61', detail='column')`），以 `episode_passages.rowid` 关联。
  - 实测（14,525 段剧情，SQLite 3.50.4）：内存重建需 7.6 秒，带正文持久化占 82.8 MB，无正文表仅占 **23.6 MB**（相对 188 MB 库约 +12%），单次查询约 **3 ms**。
  - 导入/替换/删除剧情时在同一事务内同步更新 `episode_passages_fts`（利用 `contentless_delete=1` 按 `rowid` 删除旧项再插入新项，并在更新文本时维护好 `rowid`）。
  - **旧库自动升级**：`StoryCorpus` 打开数据库时检测 `episode_passages` 有数据而 `episode_passages_fts` 为空（或未建）时自动回填一次并打 info 日志（耗时数秒，一次性完成，无需部署者手工跑迁移命令）。
  - **角色过滤下推**：SQL 查询中直接 `JOIN episode_passages` 与 `JOIN episode_cast` 按 `character_id` 过滤后再 `ORDER BY bm25(episode_passages_fts) LIMIT ?`，防止冷门角色被其他角色的高分段落挤出 Top-N。
  - 随 `eidolon backup`（`VACUUM INTO`）自然一并备份，无需改备份逻辑。
- **角色资料与作品资料走内存 FTS5**：两者合计 1,995 条、来自配置文件（修改后重启生效、无导入命令），按需在内存中建 `:memory:` SQLite FTS5 表（与 `EmbeddedTexts` 首次搜索加载一致，耗时 < 0.2 秒、不占磁盘和备份体积）。
  - 角色资料建索引时将 `Fact.title`（如有）与 `Fact.text` 合并送入分词器（`Fact.title` 如 `人物关系 / 風野灯織` 未必出现在正文里）。
  - 作品资料建索引时记录每条 `EntryKind`（或按 `among` 位置集合过滤），支持回顾剧情只查 `("live", "release")`。

### 融合、查询串与降级（票 03）

- **RRF 融合**：每个参考源取向量 Top-`N` 与 FTS5 Top-`N`（初值 `N = CANDIDATES_PER_SOURCE * 2` 即 24，票 04 实测可调），按 `score = sum(1 / (RRF_K + rank))`（1-based rank，初值 `RRF_K = 60`）合并去重，按融合分降序取前 `CANDIDATES_PER_SOURCE`（12）条送重排。同一篇剧情的不同段落分别保留（按 `(episode_id, seq)` 或段落文本去重），与现状一致。
- **FTS5 查询串分流**：
  - 常规回合：向量查询仍为 `memory_query(history, text)`；FTS5 优先只对 `text`（用户这句话）切词，当去停用词后的有效 token 数低于阈值（初值 `< 2`，票 04 实测校准）且存在上一句回复时，改用 `memory_query(history, text)` 切词。
  - `recall_story` 工具：向量与 FTS5 都直接用对话模型写的 `query`。
- **向量化失败（`EmbeddingError`）降级**：
  - 常规回合提前检索阶段，将「向量化 + 向量检索」与「FTS5 检索」解耦或分别容错：向量化失败时，参考资料各源仍可返回 FTS5 Top-`CANDIDATES_PER_SOURCE` 候选送重排（若重排也失败则取 FTS5 前 `FALLBACK_REFERENCES` 条）；记忆仍按原规则不带（没有向量无法检索记忆）。
  - 判断模型触发的预回忆与 `recall_story` 工具在向量化失败时同样退回用 FTS5 候选送重排（重排也失败则取 FTS5 最优 1 篇剧情 + 1 条作品资料）。
  - 剧情库中某批未向量化（换模型未 `reembed`）但有 FTS5 索引的段落，在混合召回与降级时也能被 FTS5 找到。
- **重排失败（`RerankError`）降级**：`Reference.similarity`（或等价排序分）承载 RRF 融合分（单路退回时为该路归一化/RRF 排位分），重排失败时按此分降序取 `FALLBACK_REFERENCES`（3）条；回顾剧情同理取最高分剧情与作品条目。
- **提前检索与判断模型并行**：FTS5 查询本身在毫秒级，但仍放进现有的提前检索并发流程中（且不阻塞事件循环，剧情库 SQLite 读走 `Database.read`，内存 FTS5 读可走 `asyncio.to_thread` 或极快读）。判断为「不用查」时照常丢弃结果、不调重排。

### 评测与验收门槛（票 01, 04）

- 复用 `backend/eval/rerank-calibration.toml`（不另开第二份标注文件）。
- 新增 `eidolon eval retrieval [--mode vector|fts|hybrid] [--k N] [--file F] [--db P] [--characters P] [--save F] [--compare F]`：
  - 评测对象：`kind` 为 `story` / `facts` / `work` 且 `relevant` 非空的用例（跳过 `memory` 和 `relevant = []` 的闲聊题，并在报告头注明跳过数量）。
  - 指标：总体及按 `story` / `facts` / `work` 分源统计 **Recall@k**（相关项命中比例，默认 `k = CANDIDATES_PER_SOURCE`，以及全命中率 / 至少命中 1 条）、**MRR**（首个相关项倒数排名的均值），并列出每个漏召回的用例 ID 与漏掉的 `relevant` 编号/标题。
  - `--save <path>` 输出结构化 JSON（模式、参数、总计、分源、逐条命中排名与漏召回）；`--compare <path>` 与已存基线逐项对比差值（ΔRecall@k、ΔMRR、新找回与新漏掉的用例清单）。
- **落地门槛（票 04）**：在人工校对后的扩充评测集上，与纯向量基线对比，`hybrid` 必须在总体 `Recall@k` 和 `MRR` 上提升，且跑 `eidolon eval rerank` 确认重排分数线与误放行不恶化。

## Testing Decisions

- 好的测试只看外部行为（返回的候选、系统提示词、评测报告与退出码），不把测试绑死在内部私有函数名上。
- **分词与 RRF 单元测试**（新测试文件，如 `test_text_search.py`）：覆盖中/日/英混杂切词（2 字偶像名、片假名、ASCII 词如 `W.I.N.G.` / `L'Antica`）、入库不去停用词与查询去停用词、FTS5 保留字与特殊符号安全转义、空查询返回空、RRF 合并去重与排序正确性。
- **剧情库 FTS5 测试**（`test_story_corpus.py`）：导入、替换、删除剧情后 FTS5 同步更新；按 `character_id` 过滤时不会返回该角色未出场的剧情，也不会被其他角色的高分剧情挤出 Top-N；旧库已有 `episode_passages` 但无 FTS5 表时，重新打开 `StoryCorpus` 自动补建且立即可搜。
- **资料源 FTS5 测试**（`test_world_retrieval.py`、`test_retrieval_services.py`）：角色资料命中 `Fact.title` 中的关键词；作品资料支持按 `kinds=("live", "release")` 过滤；更改资料列表重启后内存索引反映新内容。
- **文字回合与回顾剧情集成测试**（`test_retrieval.py`、`test_recall_story.py`）：
  - 假向量化返回无关向量时，靠关键词仍能通过混合召回把对应剧情/资料送进重排并进入提示词；
  - 短追问（用户句有效词极少）FTS5 补入上一句，正常长句不被上一句稀释；
  - `recall_story` 工具与判断模型预回忆均走混合召回；
  - 假向量化报错（`EmbeddingError`）时，参考资料与回顾剧情自动降级为 FTS5 候选送重排（重排也挂时回退 FTS5 前几条），记忆仍不带；
  - 假重排报错（`RerankError`）时，按 RRF 融合分取降级候选。
- **召回评测测试**（`test_retrieval_eval.py`）：验证 `vector` / `fts` / `hybrid` 三种模式、Recall@k 与 MRR 计算、`--save` 与 `--compare` 差值输出，以及跳过 `memory` 和空 `relevant` 用例。
- **不属于自动化测试的验收**（票 01、04）：
  - 人工校对扩充进 `rerank-calibration.toml` 的新召回用例；
  - 在本地真实 `eidolon.db` 上跑 `eidolon eval retrieval`（`vector` vs `fts` vs `hybrid`）和 `eidolon eval rerank`，把对比数据记进票 04 Comments 与 `rerank.py` 校准记录。

## Out of Scope

- **记忆（`Memory`）的全文检索**：继续走纯向量 + 重排。
- **时间线/频次类问题路由**（「上次/第一次/几次」查结构化目录）：留作后续独立议题。
- **剧情摘要层与按卡名/活动名预筛目录**：留作后续独立议题。
- **通话链路改动**（Soniox `<fin>`、Fish 串行 flush、Smart Turn）：另开独立规格，不混入本轮。
- **新增外部依赖或环境变量**：不引入 `jieba` 等第三方分词包，不新增部署者需要配置的环境变量。

## Further Notes

- 分波建议：
  - **第 1 波**：票 01（召回评测命令、扩充用例与纯向量基线）和票 02（分词器与三源 FTS5 索引），互相独立，可串行先后落地。
  - **第 2 波**：票 03（接入 `ReferenceSources` / `Retrieval` 的 RRF 混合召回、FTS5 查询串分流与向量化/重排降级，并打通 `eval retrieval --mode fts|hybrid`），依赖 01、02。
  - **第 3 波**：票 04（基于真实库对比基线、调参、跑 `eval rerank` 验收并清理过时文档/docstring），依赖 03。
- 实测记录（2026-11-26，本地 `backend/data/eidolon.db`，14,525 段剧情，SQLite 3.50.4）：读取全量段落 0.13s，内存建 CJK 2-gram FTS5 约 7.6s，单次查询 3.1ms；持久化普通 FTS5 82.8 MB，无正文 FTS5（`content=""`, `contentless_delete=1`, `detail="column"`）仅 23.6 MB。
