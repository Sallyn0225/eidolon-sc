# 调研：朋友圈动态的地点池从哪来、用哪家地图

票：`.scratch/moments/issues/01-place-pool-research.md`（feat/moments）
日期：2026-10-31

## 结论

1. **地点池预先整理成仓库里的数据文件，不在运行时查地图服务。** 建议用 `characters/places.toml`，由维护者维护，和 `jobs.toml` 一样启动时读入、校验。每个地点写名字、经纬度、类别、所在地区，可选写有关的偶像、季节和时段标签、出处。运行时不调用任何地图 API，所以没有频率限制、没有费用，也不会被封。理由：
   - Nominatim 公共服务一个应用合计最多每秒 1 次，禁止定期请求和系统性查询，OSMF 可以随时撤掉访问权限（见「4.1」）；拿它做“找一个地方”并不合适。
   - Google Places 每个 SKU 每月有免费额度，超出要付费，开项目必须绑定计费账户；它的条款还禁止把 Places 内容（地点 ID 除外）预取或长期缓存（见「4.2」）。用它建池子，等于每次都要重新查。
   - 地名本来就不让模型编，池子是固定的，运行时去查没有任何好处。
2. **点开地图：用经纬度拼 openstreetmap.org 的标记链接**（`https://www.openstreetmap.org/?mlat=<纬度>&mlon=<经度>#map=17/<纬度>/<经度>`）。不需要 key，也不需要账户，日本的 OSM 数据 `name` 就是日文。Google Maps URLs（`https://www.google.com/maps/search/?api=1&query=...`）同样完全不需要 key，官方文档原话是 “You don't need a Google API key to use Maps URLs”。两种链接都只靠数据文件里的名字和坐标拼出来，以后换一家只改一行。默认选 OSM 有两个原因：不依赖 Google 的服务和条款；用户里可能有人打不开 google.com（这一点本次没有核实，见「4.3」）。如果更看重手机上直接唤起 Google Maps App、店铺照片和营业时间，就换成 Maps URLs，同样不用申请 key。
3. **不需要申请 Google Maps 的 key。** 只有在页面里嵌地图（Maps Embed API 免费不限量，但要 key 和计费账户），或者运行时查 Places，才需要 key；这两件事按上面的方案都不做。
4. **池子做到 300–500 个就够。** 每位用户 30 天里最多 3×30=90 条动态。按“一位用户 30 天内地点不重复”算，再加上按场景筛选（比如只有 1/10 的地点适合某一条），池子 300 个时每条还剩约 20 个候选，500 个时约 40 个（算法见「3.3」）。几百个够用，不必上千。
5. **池子分三层来源：**
   - **原作圣地**，约 40–60 处（粉丝考据，集中在聖蹟桜ヶ丘、渋谷、お台場一带，大多能对上具体卡面和偶像）；
   - **东京名所**（公园、神社、美术馆、水族馆、展望台……），从 Wikidata（CC0）或各区的观光开放数据里批量取，再人工挑；
   - **日常小地方**（咖啡馆、商店街、书店、海边……），从 OSM 的 Geofabrik 关东抽取文件里离线按类别取，人工挑一批。

   OSM 数据是 ODbL：按自己的标准挑出来的一批地点按 OSMF 的指引大概率算“非实质性”摘录，但数据文件里仍注明「© OpenStreetMap contributors」。
6. **剧情库几乎抽不出东京实地名。** 原作刻意不写真实地名：东京的知名地名在全部 8,308 个剧本文件里只有「原宿」出现过 1 次，而且是“原宿系服装”的意思。剧情库能提供的是**场所类别**（カフェ、公園、神社、海、商店街、図書館……出现得很多），用来定池子的类别和权重，比用来抽地名有用。另有两类真实地名可用，但都不多：
   - 角色资料里的老家（佐世保、岡山、長野、青森……），适合回老家时用；
   - `world.json` 里约 30 个演出场馆，适合“往年今天的演出”那类动态。
7. **Eidolon Hibi 没有真实地理数据可借。** 它的地图是手绘的东京示意图，约 18 个抽象地点（office、cafe、park、asakusa……），行程里的 `where` 由模型自由写，再按关键词归类；出外景从写死的 12 个城市名里抽。能借鉴的只有两点：用“类别 → 地点”的分层结构，以及它的天气用 Open-Meteo（一对固定经纬度、不要 key），这一点可以留给天气票参考。

---

## 1. 原作圣地

### 1.1 有没有官方背书

283 プロ周边以聖蹟桜ヶ丘（东京都多摩市）为原型，这一点有官方口径：京王电铁和京王 SC Creation 2025-06-18 的新闻稿标题和正文都写着「聖蹟桜ヶ丘をモデルとする『アイドルマスター シャイニーカラーズ』」（[digitalpr.jp 转载的京王新闻稿](https://digitalpr.jp/r/112100)；2024 年第一弹见[京王新闻稿 PDF](https://www.keio.co.jp/news/update/news_release/news_release2024/pdf/nr20240917_idolmaster.pdf)，以及 [アイマス官网新闻](https://idolmaster-official.jp/news/01_15923)）。除此之外，具体哪张卡面、哪张背景对应哪里，都是粉丝考据，官方没有逐条确认。

### 1.2 可信度较高的考据来源

都是个人博客或 note，不是官方，但大多附有“游戏画面 vs 实拍”的对照照片，可以逐条复核：

| 来源 | 内容 | 时间 |
|---|---|---|
| すゞや「[シャニマスをマッピングする](https://note.com/suzuya_blowgun/n/n60331dc9f76a)」 | 公开的 Google My Maps「シャニマス 聖地巡礼・舞台検証マップ」的发布帖（本次没能拿到这张地图的直链，下面两篇文章说“更新以マイマップ上が最速”） | 2020-10 |
| すゞや「[シャニ散歩〈桜ヶ丘編〉](https://note.com/suzuya_blowgun/n/n87ab6e463404)」 | 聖蹟桜ヶ丘、多摩一带约 20 个点位，每条附对照照片；含 283 事务所原型 | 2020-12，2021-03 修订 |
| すゞや「[シャニ散歩〈都区内編〉](https://note.com/suzuya_blowgun/n/n67eb12eeb6d9)」 | 东京 23 区，文中说“現時点で30以上”个点位 | 2021-04 |
| 黒咲真雫「[聖地巡礼候補地メモ](https://baki1771104.com/archives/4673)」 | 从上面那张 Google My Maps 抄出的点位清单（地点 + 卡面） | 2022-04，2022-10 更新 |
| 黒咲真雫「[総まとめ編](https://baki1771104.com/archives/6851)」 | 作者实地去过的点位，含 SETSUNA BEAT 主视觉、成田机场等 | 2023-03 |
| laquari「[聖地巡礼 シャニマス 東京編](https://laquari.hatenablog.jp/entry/2020/08/12/105328)」 | 按地点整理，附路线建议 | 2020-08 |
| やこラボ「[シャニマス背景画像の話【まとめ編】](https://yakolab.hatenablog.jp/entry/Shiny_Location)」 | 背景图的考据，作者自己标了把握程度 | 2019-02 至 2019-08 |
| ラムダ「[聖蹟桜ヶ丘の聖地巡礼マップ](https://note.com/lambda39/n/na24656abc004)」 | 可打印的 PDF 地图，2026-09 仍在更新（点位在 PDF 里，正文没有列） | 2021-09 首发，2026-09 更新 |
| あおかみろんぐ「[聖地巡礼・検証](https://aokamilong.hatenablog.com/archive/category/%E8%81%96%E5%9C%B0%E5%B7%A1%E7%A4%BC%E3%83%BB%E6%A4%9C%E8%A8%BC)」 | 单张卡、单段剧情的深度考据（千雪老家、甜花、凛世等），作者自称是“ガバガバ盲言” | 2021–2023 |

没有采用的：动画版（2024）圣地目前只看到聚合站的整理（如 [旅する亜人ちゃん](https://ajin-movie.com/syanimasu-seitijyunrei/)：一ノ宮公園、ラゾーナ川崎、さる小），可信度较低，要用的话需另找一手考据；`aki-seiseki.com` 的「東京23区編」系列本次抓取失败，没有读到正文。

### 1.3 能整理出多少

- 桜ヶ丘・多摩：すゞや那篇约 20 个条目，按地点去重后约 14 处。
- 23 区：すゞや说有 30 个以上；黒咲那份清单列了约 20 处。
- 千叶及地方：海浜幕張、イオンモール幕張新都心、成田機場、神津島（19 年夏活动）、初島、八王子、下北沢、鎌倉高校前一带（SETSUNA BEAT ノクチル主视觉；黒咲文中只说是“スラダンの聖地”，具体地点是推断，**未核实**）。

**估计：考据出来的条目约 70–100 条，按地点去重后约 50–70 处。** 去掉已经消失的（旧 HMV 渋谷店、朝日生命大手町ビル已拆、东北沢 5 号道口已拆、一ノ宮公園的秋千已撤）、不适合偶像日常的（歌舞伎町）和过于细碎的（某个投币停车场），**能用的大约 40–60 处**。这是根据上面几篇文章的条目估算的，Google My Maps 的准确点数没拿到。

偶像覆盖不均：初期偶像（イルミネ、放クラ、アンティーカ、アルスト）的点位多；にちか只有タワレコ一处，美琴、CoMETIK 等后来加入的偶像在这些来源里基本没有。原因是考据活动集中在 2019–2022 年。

### 1.4 样例清单（20 个）

| # | 地点（所在地） | 对应 | 偶像 / 组合 | 出处 |
|---|---|---|---|---|
| 1 | 桜ヶ丘中央ストアー（多摩市関戸2-39-9）；另一个原型是府中的しみずビル | 283 プロ事务所外观（背景） | 全员 | [すゞや 桜ヶ丘編](https://note.com/suzuya_blowgun/n/n87ab6e463404)；地址见 [夜散歩のススメ](https://yorusannpo.blog.jp/archives/1013949022.html) |
| 2 | 聖蹟桜ヶ丘駅前交差点 | ［背景］街中；【さかさま世界】 | 芹沢あさひ（Straylight） | [すゞや 桜ヶ丘編](https://note.com/suzuya_blowgun/n/n87ab6e463404) |
| 3 | 聖蹟桜ヶ丘駅 西口改札 | 【駅線上の日常】 | 櫻木真乃（イルミネ） | 同上；[laquari](https://laquari.hatenablog.jp/entry/2020/08/12/105328) |
| 4 | 聖蹟桜ヶ丘駅 西口広場 | 【金色の元気いっぱいガール】 | 八宮めぐる（イルミネ） | 同上 |
| 5 | いろは坂（多摩市桜ヶ丘） | ［背景］坂道；【お散歩サンライト】 | 大崎甘奈（アルスト） | [すゞや 桜ヶ丘編](https://note.com/suzuya_blowgun/n/n87ab6e463404) |
| 6 | いろは坂桜公園 | ［背景］公園；【オフデーゲーム】【君・空・我・空】 | 西城樹里（放クラ）、幽谷霧子（アンティーカ） | 同上 |
| 7 | いろは坂通りの階段 | 【風吹く丘にはよ来んね】 | 月岡恋鐘（アンティーカ） | 同上 |
| 8 | 乞田川桜並木 | 【友情の花吹雪】 | 八宮めぐる | 同上；[baki 4673](https://baki1771104.com/archives/4673) |
| 9 | 都立桜ヶ丘公園 ゆうひの丘 | ［背景］高台；【意地っ張りサンセット】 | 西城樹里 | [すゞや 桜ヶ丘編](https://note.com/suzuya_blowgun/n/n87ab6e463404)；[baki 6851](https://baki1771104.com/archives/6851) |
| 10 | 府中四谷橋（多摩川） | ［背景］河川敷；【アイムカミングスーン】 | 八宮めぐる；河川敷对イルミネ、アルスト是重要场景 | [すゞや 桜ヶ丘編](https://note.com/suzuya_blowgun/n/n87ab6e463404) |
| 11 | 多摩川百草ふれあい広場 | 【つむぎ、まばゆく。星屑たち】（アジェンダ283） | 櫻木真乃 | 同上；[hahaeatora](https://hahaeatora.hateblo.jp/entry/2021/08/28/200000) |
| 12 | 永山五丁目バス停（多摩市） | ［背景］バス停；透的 W.I.N.G. 剧情 | 浅倉透（ノクチル） | [すゞや 桜ヶ丘編](https://note.com/suzuya_blowgun/n/n87ab6e463404)；[laquari](https://laquari.hatenablog.jp/entry/2020/08/12/105328) |
| 13 | 蔦屋書店 多摩永山店 | 【ぐうぜんBOOKS】 | 櫻木真乃 | [すゞや 桜ヶ丘編](https://note.com/suzuya_blowgun/n/n87ab6e463404) |
| 14 | パルテノン大通り（多摩センター） | 【冬街イルミネート】 | 櫻木真乃 | 同上；[やこラボ](https://yakolab.hatenablog.jp/entry/Shiny_Location) |
| 15 | 渋谷スクランブル交差点 | 【と～りゃんせ！】 | 月岡恋鐘 | [すゞや 都区内編](https://note.com/suzuya_blowgun/n/n67eb12eeb6d9) |
| 16 | 渋谷 スペイン坂 | 【お願い、ただの少女がいい】 | 三峰結華（アンティーカ） | 同上；[laquari](https://laquari.hatenablog.jp/entry/2020/08/12/105328) |
| 17 | タワーレコード 渋谷店 1F | 【♡まっクろはムウサぎ♡】 | 七草にちか（SHHis） | [baki 4673](https://baki1771104.com/archives/4673)；[baki 6851](https://baki1771104.com/archives/6851) |
| 18 | 明治神宮外苑 いちょう並木 | 【ギンコ・ビローバ】；［背景］いちょう並木 | 樋口円香（ノクチル） | [baki 4673](https://baki1771104.com/archives/4673) |
| 19 | 谷中銀座（日暮里） | 【坂道だらけのこの街で】 | 西城樹里 | [baki 6851](https://baki1771104.com/archives/6851)；[laquari](https://laquari.hatenablog.jp/entry/2020/08/12/105328) |
| 20 | お台場海浜公園 / デックス東京ビーチ | 【ちょこ色×きらきらロマン】；【曲り角のランウェイ】 | 園田智代子、西城樹里（放クラ） | [やこラボ](https://yakolab.hatenablog.jp/entry/Shiny_Location)；[baki 6851](https://baki1771104.com/archives/6851) |

还可以补上的：
- 浜離宮恩賜庭園（［背景］菜の花畑，千雪）
- アトレ秋葉原1前（【ザ・冬優子イズム】）
- 市ヶ谷フィッシュセンター（【スプリング・フィッシュ】摩美々）
- BOOK AND BED TOKYO 新宿（【それは途中の１ページ】咲耶）
- 東京都庁北展望室（甘奈【お散歩サンライト】フェス绘）
- 東京スカイツリー（【NOT≠EQUAL】結華）
- 表参道ヒルズ 同潤館（結華）
- 海浜幕張駅（【をとめ条約】凛世）
- 八王子駅八高線ホーム（【HAPPY-!NG】雛菜）

出处见 [すゞや 都区内編](https://note.com/suzuya_blowgun/n/n67eb12eeb6d9)、[baki 6851](https://baki1771104.com/archives/6851)、[laquari](https://laquari.hatenablog.jp/entry/2020/08/12/105328)。

整理时要注意：
- 这些都是卡面或背景的取景地，不是剧情里写明的地名。动态里“她在这里”只是借景，不要让模型说“这是我那张卡拍的地方”。
- 有些地点会变（店铺关门、楼拆掉），数据文件里给每个地点记一个核对日期。

## 2. 剧情库里的地名

### 2.1 数据在哪

- 术语：`GLOSSARY.md` 中「剧情库 (Story Corpus)」是“由作品剧情文本构成的、角色可以回忆的资料层”，「剧情 (Episode)」是其中“完整的一段コミュ”。
- 代码：`backend/src/eidolon/corpus.py`（`episodes`、`episode_cast` 表，向量索引）、`story_import.py`、`story_sync.py`、`mirror.py`。
- 原文：本机有，但不进仓库（`.gitignore` 第 21 行 `/corpus/`，ADR-0003）。`corpus/SCTranslationData/data/story/**.csv` 是汉化组数据，`text` 列为日文原文，5,672 个 CSV；`corpus/mirror/scripts/**.json` 是游戏脚本镜像，2,684 个 JSON。合计 8,308 个文件、约 720 万字。

### 2.2 抽样结果

用脚本把全部剧本的台词读进内存，逐词统计出现在多少个文件里（脚本在 `E:/tmp/moments-research-scripts/`，不在仓库里）。

**东京具体地名：** 試了 渋谷、原宿、表参道、新宿、池袋、秋葉原、お台場、浅草、銀座、六本木、吉祥寺、下北沢、中野、高円寺、横浜、みなとみらい、恵比寿、代官山、自由が丘、品川、東京タワー、スカイツリー、東京駅、竹下通り、有楽町、築地、豊洲、舞浜、代々木、井の頭、谷中、両国、立川、八王子、三鷹 等约 80 个。结果：

- 「原宿」1 个文件（结華说「原宿ファッションの申し子」，指服装风格）；
- 「上野」「鎌倉」各 1 处，都不是地名用法（「鎌倉の前くらい」说的是镰仓时代）；
- 其余全部是 0。

**东京以外：**
- 「長崎」36 个文件、「佐世保」「九十九島」「五島」若干，都是恋鐘的老家；
- 「東京」18 个，多是“东京出身”“上京”；
- 「北海道」4、「富士山」4、「京都」2、「大阪」2，「岡山」「富山」「筑波山」「鳥取県」各 1–2；
- 「大分」14 处是副词「だいぶ」，不算。

**虚构地名：** 糸名公園（3 个文件，透、とまりかぜ活动）、紅蘭偉魔空珠学園、「県庁通り」（にちか卡里的广告词）、「湾岸地区」（咲耶）。

**泛称场所**（出现在多少个文件里，粗略统计，含少量误匹配）：

| 场所 | 文件数 | 场所 | 文件数 |
|---|---|---|---|
| コンビニ | 167 | 図書館 | 27 |
| カフェ | 160 | ショッピングモール | 23 |
| 公園 | 140 | 本屋 | 23 |
| 神社 | 49 | 喫茶 | 21 |
| 花火 | 43 | 砂浜 | 20 |
| 屋上 | 42 | 美術館 | 19 |
| 温泉 | 40 | ゲームセンター | 15 |
| 雑貨屋 | 34 | 水族館 | 14 |
| 遊園地 | 31 | パン屋 | 12 |
| 商店街 | 30 | プラネタリウム | 8 |
| ファミレス | 30 | 動物園 | 7 |

「海」出现在 298 个文件里，但含「海外」等，偏高。

### 2.3 结论和抽取办法

- **能抽出的东京实地名约等于 0。** 原作只给场所类型，不给真实地名，背景图是实景描的但不写名字。这也说明给动态挂真实地名是在原作之外加设定，池子里的地名应该像背景一样“普通但真实”，而不是全挑旅游名胜。
- **能用的是类别分布。** 上表可以直接当池子的类别权重参考：咖啡馆、公园、便利店、神社、商店街、杂货店、图书馆、书店、海边、温泉、游乐园、水族馆、美术馆、天象仪。便利店、家庭餐厅这类不必挂具体店名，可以不进池子，或者只挂所在街区。
- **小批量真实地名的来源：**
  - `characters/facts/*.md` 里的老家：恋鐘佐世保、羽那岡山、はるき長野、霧子青森、千雪山口、冬優子茨城、智代子千葉、甘奈甜花富山、樹里雛菜神奈川……只适合偶尔回老家时用。
  - `characters/world.json` 的 `lives` 里有 31 个演出场馆名，如 東京ドーム、日本武道館、幕張メッセ、ぴあアリーナMM、京王アリーナTOKYO。适合「往年今天的演出」类动态，要注意这些是现实里的 live 场馆。
- 如果以后要系统抽取：对 `episodes` 的正文跑一个“地名词典匹配 + 人工审”就够，不值得上 NER。用上面的结果判断，投入产出很低，**不建议做**。

## 3. 地点池怎么做得够大

### 3.1 现成数据

**OSM，本次实测。** 2026-10-31 对公共 Overpass 做了一次计数查询，范围是东京都 `ISO3166-2=JP-13`：

| 类别（OSM 标签） | 数量 | 其中有 `name` |
|---|---|---|
| 咖啡馆 `amenity=cafe` | 5,206 | 4,899 |
| 公园 `leisure=park` | — | 5,891 |
| 神社 `amenity=place_of_worship` + `religion=shinto` | — | 1,638 |
| 寺院 `religion=buddhist` | — | 2,148 |
| 商场 `shop=mall` | — | 227 |
| 百货店 `shop=department_store` | — | 78 |

后续查询（景点、博物馆、海滩、庭园）在公共 Overpass 上一次超时、两次返回 502「server is currently at capacity」，没有拿到。OSM 约定 `name` 用当地语言（[Key:name](https://wiki.openstreetmap.org/wiki/Key:name)：“The primary name is generally in the local language”），所以日本的 `name` 就是日文名，日文覆盖没有问题。

- **取法：** 不要依赖公共 Overpass。它的政策是一次性使用每天少于 1 万次查询、1 GB 流量，定期使用的话这些数要除以 100，不得并发，商用应自建；页面还写着“Nowadays this server is overloaded”（[Overpass API wiki](https://wiki.openstreetmap.org/wiki/Overpass_API)），本次实测也确实如此。建议下载 Geofabrik 的关东抽取文件（[kanto-latest.osm.pbf，499 MB，ODbL 1.0，几乎每天更新](https://download.geofabrik.de/asia/japan/kanto.html)），本地用 osmium 或 pyosmium 按标签过滤，一次性生成候选 CSV，再人工挑。
- **许可：** OSM 是 ODbL。OSMF 的《Substantial》指引说，少于 100 个要素算非实质性摘录；超过 100 个时，只要是按自己的定性标准挑选、不是系统性全取（原文例子是“你去过的餐馆”这种个人地图），也可以算非实质性。但重复的小批量摘录会被合并计算（[Substantial - Guideline](https://osmfoundation.org/wiki/Licence/Community_Guidelines/Substantial_-_Guideline)）。人工挑几百个大概率在这个范围内，**但不是法律意见**。稳妥做法：数据文件头注明「Contains data © OpenStreetMap contributors, ODbL」，并在 `LICENSING.md` 记一笔。

**Wikidata，本次实测，CC0。** 结构化数据全部以 CC0 发布（[Wikidata:Licensing](https://www.wikidata.org/wiki/Wikidata:Licensing)），不用署名，适合名所类。按东京一带的经纬度框（139.2–139.95E，35.5–35.85N，会带上少量神奈川、埼玉、千叶）只数直接 `P31`（不含子类）、有坐标的条目：

| 类别 | 数量 |
|---|---|
| 神社 Q845945 | 1,083 |
| 公园 Q22698 | 235 |
| 博物馆 Q33506 | 64 |
| 体育场馆 Q1076486 | 31 |
| 公共水族馆 Q2281788 | 10 |

算上子类会多得多。名所、庭园、展望台、桥、商店街可以照此去取。

**东京都和各区市的开放数据：** 没有全都统一的一份。各区市各自发布「観光施設一覧」，多数按「自治体標準オープンデータセット」格式带经纬度，许可多为 CC BY。例子：
- 汇总页「[観光施設の分布と一覧](https://portal.data.metro.tokyo.lg.jp/visualization/distribution-and-list-of-tourist-facilities/)」，收了中央、墨田、江東、世田谷、豊島、荒川、練馬、葛飾等 15 个区市；
- [世田谷区 観光施設一覧](https://catalog.data.metro.tokyo.lg.jp/dataset/t131121d0000000006)。

适合补下町、多摩一带，但格式要逐个对齐，只建议当补充。

### 3.2 按偶像日常筛

建议的类别（参照 2.2 的剧情分布和 `jobs.toml` 的工作）：

- 咖啡馆、甜品
- 公园、河边
- 神社、寺
- 商店街
- 杂货、服装街区（原宿、下北沢、高円寺……）
- 书店、图书馆
- 商场、车站大楼
- 海边、湾岸（お台場、葛西、江ノ島）
- 水族馆、动物园、游乐园
- 美术馆、博物馆、天象仪
- 展望台、夜景
- 温泉、钱汤
- 季节名所（赏樱、红叶、花火大会会场、灯饰）
- 演出场馆
- 圣地（单独一层）

每位偶像在 `characters.toml`（或另一个表）里写类别偏好权重，比如：真乃→公园、鸟；智代子→甜品；凛世→神社、和风；あさひ→科学馆、怪地方。圣地按卡面挂上“有关的偶像”，挑的时候加权。

**注意不适合的地方：**
- 未成年偶像（果穂 12 岁）不该出现在夜生活街区，歌舞伎町一类不收；
- 私宅、学校具体名不收，避免把真实学校和角色绑在一起。

### 3.3 几百个够不够：简单算一下

设每位用户每天最多 N 条（默认 3），保留 30 天，那么一位用户的窗口里最多 30N = 90 条带地点的动态。若约 1/3 动态不挂地名（纯室内，比如事务所、练习室），实际约 60 条。

最严格的要求是“同一位用户的 30 天里地点不重复”。不同用户之间可以重复，所以池子大小和用户数无关。

一条动态要按场景筛选（类别对得上今天的工作和素材，天气、季节、时段也合适，偶像偏好加权），设筛完剩下比例为 f。窗口里已经用掉的地点按比例也只占掉 f 那部分，所以剩余候选约为 f × (P − 90)：

| 池子 P | f = 20% | f = 10% | f = 5% |
|---|---|---|---|
| 150 | 12 | 6 | 3 |
| 200 | 22 | 11 | 5 |
| 300 | 42 | 21 | 10 |
| 500 | 82 | 41 | 20 |

结论：
- 200 个勉强够；
- **300 个是舒服的下限**；
- 每位偶像的偏好筛得很窄（f≈5%）或者部署者把 N 调大时，做到 400–500 个；
- 上千个没有必要，维护成本还更高。

N 变了就按 30N 重算。另外建议同一位偶像跨月也少重复：每个地点记最近被她用过的时间，在挑选时降权，不需要硬性排除。

## 4. 地图服务

### 4.1 OSM / Nominatim

[Nominatim 使用政策](https://operations.osmfoundation.org/policies/nominatim/)要点：
- **频率：** “an absolute maximum of 1 request per second”，按网站或应用合计算，所有用户加起来不能超。
- **标识：** 必须带能识别应用的 User-Agent 或 Referer，库的默认 UA 不行。
- **缓存：** 结果必须在自己这边缓存。
- **批量：** 不鼓励大批量地理编码；小规模一次性任务要单线程，长时间或定期跑的不超过每分钟 4 次。
- **禁止：** 自动补全；系统性查询；转卖。
- **公开服务：** 终端用户直接触发的请求可以，用户量要适中；应用定期发请求“strongly discouraged”；OSMF 要求时必须能不发版就关掉这项功能。
- **署名与保障：** 要显示署名（ODbL）；政策可能不经通知就改，访问权限可能被撤回。

→ 后台定时生成动态时去查 Nominatim，正属于“定期请求”，不合适。建池子时用它补坐标也不必：OSM 抽取文件和 Wikidata 本来就带坐标。

[OSM 瓦片使用政策](https://operations.osmfoundation.org/policies/tiles/)：
- 网站可以用，但必须在地图上显示 OSM 署名、发送有效的 Referer；
- 禁止批量下载和预取；
- 没有 SLA，访问可能被无预警封禁。

只有在页面里嵌入地图时才涉及这条；只放外链则完全不涉及。

**点开跳 openstreetmap.org：** 链接格式是 `?mlat=&mlon=` 放红色标记，`#map=缩放/纬度/经度` 定视图；也能链到具体要素 `/node/<id>`、`/way/<id>`（[Browsing](https://wiki.openstreetmap.org/wiki/Browsing)）。页面提醒部分参数“may not be supported long term”，所以数据文件只存经纬度（和可选的 OSM id），链接在前端拼，改格式时只改一处。

不足：openstreetmap.org 是地图编辑和浏览站，没有店铺照片和评价；手机上打开是网页，不会唤起 App。对“看看这地方在哪”够用。

### 4.2 Google Maps Platform

- **价格**（[官方价格页](https://developers.google.com/maps/billing-and-pricing/pricing)，2026-10-28 更新）：

  | SKU | 每月免费 | 超出后每千次 |
  |---|---|---|
  | Places API (New) Text Search Pro | 5,000 次 | $32 |
  | Nearby Search Pro | 5,000 次 | $32 |
  | Place Details Essentials | 10,000 次 | $5 |
  | Place Details Pro | 5,000 次 | $17 |
  | Dynamic Maps | 10,000 次 | $7 |
  | Static Maps | 10,000 次 | $2 |
  | Maps Embed API | 不限量，免费 | — |

  “Text Search Essentials (IDs Only)”也不限量免费。
- **免费额度的变化：** 2025-03-01 起，每月 $200 抵扣额度取消，改为每个 SKU 各自的免费额度（Essentials 1 万、Pro 5 千、Enterprise 1 千），每月 1 日重置（[March 2025 changes](https://developers.google.com/maps/billing-and-pricing/march-2025)、[FAQ](https://developers.google.com/maps/billing-and-pricing/faq)）。
- **申请条件：** 要建一个开通计费的 Cloud 项目（“you must create a billing-enabled Cloud project”，[Get started](https://developers.google.com/maps/get-started)），也就是要绑信用卡。
- **Places 条款**（[Places API policies](https://developers.google.com/maps/documentation/places/web-service/policies)）：
  - “You must not pre-fetch, cache, or store Places API content beyond the allowed exceptions”，只有地点 ID 可以无限期保存；
  - Places 结果显示在地图上时必须用 Google 地图；
  - 不配地图显示时要带 Google 标志。

  → 用 Places 建一份长期存放的地点池（名字、坐标）不合规，只能存地点 ID，每次显示再查。
- **Maps Embed API**（[文档](https://developers.google.com/maps/documentation/embed/get-started)）：“All Maps Embed API requests are available at no charge with unlimited usage”，但 URL 里要带 `key`，所以仍要建项目。
- **Maps URLs**（[文档](https://developers.google.com/maps/documentation/urls/get-started)）：“You don't need a Google API key to use Maps URLs.”
  - 格式：`https://www.google.com/maps/search/?api=1&query=<名称或"纬度,经度">[&query_place_id=<ID>]`，必须带 `api=1`，参数要 URL 编码，整条 URL 不超过 2,048 字符。
  - `query` 只写名字时，可能会搜到同名的别处；写成“名字 + 区名”或直接写坐标更稳。只写坐标的话，地图上只有一个针，没有店名。

### 4.3 没核实的

- 用户能不能打开 openstreetmap.org、google.com：中国大陆普遍无法直接访问 Google，这是常识，但本次没有找到可引用的一手来源，openstreetmap.org 在大陆的可达性也没有实测。如果在意这一点，部署者可以先用自己的用户群做一次实测，再定默认链接。
- Google My Maps「シャニマス 聖地巡礼・舞台検証マップ」的直链和准确点数没拿到。

## 5. Eidolon Hibi 的做法

看的是 [Eidolon-Hibi](https://github.com/x499806631-commits/Eidolon-Hibi) 的 `1fb2454`（2026-10-23）。

- **行程地点：** `schedules.py` 的 `Slot.where` 是模型写行程时自由填写的一段文字（没有地点池）。
- **地图：** `city_map.py` 用关键词把 `where` 归到约 18 个抽象地点（`office`、`lesson`、`school`、`studio`、`venue`、`home`、`town`、`away`，以及约会去处 `aquarium`、`amusement`、`cinema`、`cafe`、`shopping`、`park`、`tower`、`sea`、`zoo`、`asakusa`）。比如「浅草」「雷门」「神社」都归到 `asakusa`，「台场」「江之岛」都归到 `sea`。前端 `components/map/` 画的是插画式东京示意图（`MapArt.tsx`），**没有经纬度，没有接任何地图服务**。
- **约会站点：** `outing_spots.py` 给每个抽象地点写了 3–4 个站点（名字、给模型的场景描述、生图 tag），如上野动物园的熊猫馆、不忍池，东京塔展望台，浅草寺。全是写死的中文描述。
- **出外景：** `TRIP_PLACES` 写死 12 个城市（大阪、京都、北海道、福冈、冲绳、横滨……），每 8 天抽一次。
- **天气：** `weather.py` 调用 Open-Meteo（`api.open-meteo.com/v1/forecast`），注释写着不要 key；坐标是部署者配的一对 `EIDOLON_WEATHER_LAT/LON`。

**可借鉴的：**
- “类别 → 具体地点”的两层结构，和按关键词把工作、行程映射到类别的做法，可以用在“今天的工作 → 适合的地点类别”上。
- 给每个地点配一句场景描述和生图 tag 的做法（`Stop.scene`、`Stop.tags`），可以给配图票参考。

**不可借鉴的：** 地点由模型自由写，这正是本票要避免的；也没有真实坐标。

## 6. 建议的数据文件形状（供后续拍板）

```toml
# characters/places.toml（示意）
[[places]]
id = "seiseki-iroha-sakura-park"
name = "いろは坂桜公園"           # 动态上显示的地名
area = "多摩市"                    # 消歧用，也拼进 Google 查询
lat = 35.6468                      # 示意数字，未核实
lon = 139.4497
category = "park"
idols = ["kiriko", "juri"]         # 可选：有关的偶像（圣地）
tags = ["sakura", "daytime"]       # 可选：季节、时段、室内外
source = "【君・空・我・空】幽谷霧子；すゞや 桜ヶ丘編"
checked = "2026-11"
```

建议的挑法：服务器按素材、类别、天气、季节、偶像偏好，从“这位用户 30 天内没用过的”里筛出 3–5 个候选；模型按 id 选一个，选错或没选就由服务器随机定一个。地名始终来自数据文件，模型只能挑，不能写。

## 附：本次做过的实测

- 剧情库统计脚本：`E:/tmp/moments-research-scripts/places.py`、`count.py`、`suffix.py`、`ctx.py`，只读 `corpus/`，没有改仓库。
- Overpass 计数查询 1 次成功（部分超时），2 次 502。
- Wikidata SPARQL 计数 1 次成功，1 次超时。
- Eidolon-Hibi 浅克隆在 `E:/tmp/moments-research-hibi/`，只读。
