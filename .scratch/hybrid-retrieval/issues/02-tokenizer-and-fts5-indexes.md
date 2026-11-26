# 02: CJK 2-gram 分词器与三源 FTS5 索引

**What to build:** 实现零外部依赖的 CJK 2-gram + ASCII 整词分词器、FTS5 安全查询构造与 RRF 融合工具；给 `StoryCorpus` 加上持久化在 `eidolon.db` 里的无正文 FTS5 索引（支持旧库自动补建与角色过滤下推），给 `CharacterFacts` 和 `WorkFacts` 加上按需构建的内存 FTS5 索引。本票不改回合主流程的检索行为（由票 03 接入）。背景见 `../spec.md`。

**Blocked by:** None (can start immediately)

**Status:** done

## 已定的设计（详见 spec）

- **分词与融合模块**（如 `backend/src/eidolon/text_search.py`）：
  - 连续中日文字符（平假名、片假名、汉字）按 2-gram 切分（长度 ≤ 2 保留原词）；连续 ASCII 字母/数字保留小写整词；标点与空白作分隔。
  - **入库端不去停用词**；**查询端去掉高频中/日文虚词与功能词**，再对 token 去重。
  - FTS5 查询构造：每个 token 用双引号安全转义后以 `OR` 连接；无有效 token 时返回 `None`（调用方直接返回空列表，不执行 `MATCH`）。
  - 通用 RRF 融合函数：`score = sum(1 / (k + rank))`（1-based rank，默认 `k = 60`），合并多路有序结果并按融合分降序返回。
- **剧情库持久化 FTS5（`corpus.py`）**：
  - 在 `_SCHEMA` 中新增 `episode_passages_fts`：`USING fts5(tokens, content='', contentless_delete=1, tokenize='unicode61', detail='column')`，以 `episode_passages.rowid` 关联。
  - 导入/替换/删除剧情时，在同一事务内同步删旧插新（`DELETE FROM episode_passages_fts WHERE rowid = ...` 后插入新段落的 `rowid` 与分词结果；注意删 `episodes` 级联删除 `episode_passages` 之前先清理对应 `rowid` 的 FTS 记录）。
  - 旧库升级：`_open` 发现 `episode_passages` 有数据且 `episode_passages_fts` 为空时，自动分批补建并记录 info 日志（含段落数和耗时）。
  - 新增 `StoryCorpus.search_by_text(query: str, character_id: str, limit: int) -> list[Passage]`：在 SQLite 中 `JOIN episode_passages` 与 `JOIN episode_cast` 按 `character_id` 过滤后 `ORDER BY bm25(episode_passages_fts) LIMIT ?`（通过 `self._db.read` 执行，不阻塞事件循环）。
- **角色资料与作品资料内存 FTS5（`facts.py`、`work_facts.py`）**：
  - 封装一个轻量的内存 FTS5 索引器（在 `:memory:` SQLite 连接上用 `unicode61` 建表，按文档列表一次构建、只读查询）。
  - `CharacterFacts`：按角色懒构建内存 FTS5，每条把 `Fact.title`（如有）与 `Fact.text` 合并索引；提供 `search_by_text(query: str, character: Character, limit: int)`。
  - `WorkFacts`：懒构建一次内存 FTS5，提供 `search_by_text(query: str, character: Character, limit: int)` 以及支持 `kinds` 过滤的 `search_entries_by_text(query: str, limit: int, kinds: Collection[EntryKind] | None = None)`。

## 验收

- [x] `backend/tests/test_text_search.py`：覆盖中日英混杂切词（2 字偶像名、片假名、`W.I.N.G.`、`L'Antica`）、入库不去停用词与查询去停用词、FTS5 保留字（`AND`/`OR`/`NOT`/`NEAR`）和引号/特殊符号安全转义、空查询不报错、RRF 合并排序。
- [x] `backend/tests/test_story_corpus.py`：新增测试覆盖剧情导入/替换/删除后 FTS5 同步更新；`search_by_text` 只返回该角色出场的剧情且冷门角色不会被其他角色的高分段落挤出 Top-N；模拟旧库（已有 `episode_passages`、无 FTS5 表）重新打开 `StoryCorpus` 自动补建并立即可搜。
- [x] `backend/tests/test_world_retrieval.py` / `test_retrieval_services.py`：角色资料能通过 `Fact.title` 中的关键词搜到；作品资料能按 `kinds=("live", "release")` 过滤。
- [x] `backend/` 下相关测试、`pyright`、`ruff check` 通过；`sh scripts/affected-tests.sh <基点>` 通过。

## Comments

### 实现说明（票 02）

- 新增 `backend/src/eidolon/text_search.py`：实现 CJK 2-gram + ASCII 小写整词分词（`index_tokens`、`index_text`、`titled_text`）、查询端停用词过滤与去重（`query_tokens`、`STOPWORDS`）、双引号安全转义 FTS5 `OR` 查询构造（`format_fts_query`、`fts_query`）、通用 RRF 融合（`RRF_K = 60`、`rrf_fuse`）以及线程安全的内存 FTS5 索引器 `MemoryFtsIndex`。
- 更新 `backend/src/eidolon/database.py`：将 `episode_passages_fts` 及其 4 张 FTS5 影子表加入 `NOT_USER_DATA`；新增 `database.memory()` 保持仅 `database.py` 调用 `sqlite3.connect` 的仓库约束。
- 更新 `backend/src/eidolon/corpus.py`：在 `_SCHEMA` 新增持久化无正文 FTS5 虚表 `episode_passages_fts`（`content=''`, `contentless_delete=1`, `tokenize='unicode61'`, `detail='column'`）；导入/替换/删除在同一写事务内维护 FTS5（删除 `episodes` 级联前先按 `rowid` 删除 FTS 记录）；`_open` 自动检测旧库空 FTS 表并在 `BEGIN IMMEDIATE` 事务中分批回填且打 info 日志；新增 `StoryCorpus.search_by_text(query, character_id, limit)` 走 `self._db.read` 并下推 `JOIN episode_cast`。
- 更新 `backend/src/eidolon/facts.py` 与 `backend/src/eidolon/work_facts.py`：按需懒构建 `MemoryFtsIndex`（角色资料合并 `Fact.title` 与 `Fact.text`；作品资料记录 `EntryKind`），分别提供 `search_by_text` 与 `search_entries_by_text(..., kinds=...)`；回合主流程保持未改。
- 新增 `backend/tests/test_text_search.py`，并扩充 `test_story_corpus.py` 与 `test_retrieval_services.py`。

### 审查记录（票 02，基点 `545b0134`）

- Standards 轴：无文档规范违规。保留判断题：`rrf_fuse` 供票 03 接线使用；`MemoryFtsIndex.close()` 作为持有 `:memory:` SQLite 连接的显式关闭口保留；`facts.py` / `work_facts.py` 提前用 `fts_query(query) is None` 避免空查询触发索引构建，轻微重复分词可接受。
- Spec 轴：无缺漏、无范围外行为。已按审查意见在 `corpus.py:_open` 的 `executescript(_SCHEMA)` 之后显式补上 `BEGIN IMMEDIATE`，防止多进程并发首次打开旧库时重复回填 FTS5。保留判断题：`CharacterFacts._fts` 按 `character.id` 缓存，符合规格「修改后重启生效」。另记跨票提示给票 03（见票 03 Comments）。
