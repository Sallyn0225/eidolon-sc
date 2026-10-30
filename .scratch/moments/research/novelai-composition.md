# 调研：NovelAI 非自拍构图和多角色（给朋友圈配图用）

调研日期 2026-10-31，对应票 `.scratch/moments/issues/03-novelai-composition-research.md`。接着远端 `research/novelai-prompting` 分支的 `.scratch/photos/research/novelai-prompting.md`（下称「前一份调研」）往下写，那份已经查清的写法规则、语法字符、质量 tag、自拍实测这里不再重复。

**本次没有生成任何图片，也没有花钱。** 做过的请求只有三类：读官方文档和 API 规格（`image.novelai.net/docs/doc.json`）、调官方 tag 建议接口（不带 token，按 `nai-diffusion-5-curated` 查，约 120 次）、读 Danbooru wiki 和社区页面。下面凡是说「效果」的，除非标了【实测】，都来自文档或别人的经验，要等原型票（04）出图核实。

来源标记：
- **【官方文档】** docs.novelai.net；**【官方规格】** image.novelai.net 的 Swagger 规格 `doc.json`；**【官方博客】** NovelAI 的发布公告。
- **【Danbooru】** danbooru.donmai.us 的 tag wiki（本机直连和代理都连不上 Danbooru，wiki 原文是经 exa 抓取的；帖子数这次没拿到）。
- **【建议接口】** 官方 tag 建议接口的返回，判断「V5 Curated 认不认这个 tag」，`count` 封顶 10000。
- **【社区】** 第三方仓库、博客、论坛，只作佐证，写明是谁、什么条件。
- **【推断】** 本文自己的推理，没有直接出处，原型要验证。

---

## 结论

1. **构图做成枚举，由她选，服务器换成固定的前后缀**。建议七种：`scenery` 风景、`food` 食物、`object` 物品（这三种画面里没有人）、`selfie` 自拍、`posed` 别人帮她拍（看镜头）、`candid` 别人抓拍（不看镜头）、`group` 和其他偶像合照。前四种和 `posed` 都只是改现有的单人提示词，代价小；`group` 要用多角色提示框，单独评估。理由：决定构图的就那几个 tag（`no humans`、`food focus`、`object focus`、`selfie`、视线 tag、人数 tag），让 LLM 自己写很容易漏或写反（比如风景照里写了 `1girl`），枚举更稳，也和照片里「拍法」「景别」的做法一致。
2. **无人构图的关键是 `no humans` 放在最前面，同时去掉人物前缀和作品 tag**。官方入门教程原话是「since we want an image of a landscape with no characters on it, the `no humans` tag at the start is very important」。官方还提醒质量 tag「may bias the AI towards generating pictures of anime characters」，用户的画风插槽 `0.7::artist:rella::` 本身也偏爱画人。所以无人构图不写 `1girl, solo`、角色 tag、外貌和 `idolmaster shiny colors`（作品 tag 会把这部作品的角色拉进来【推断】），负面再补 `1girl, 1boy, people`。画风插槽照常加，有没有把人画回来要实测。
3. **`candid` 不是 tag**（建议接口和 Danbooru 都没有），`group selfie`、`unseen person` 也不是。「像朋友随手拍」只能靠组合：去掉 `looking at viewer`，换成具体的视线 tag（`looking to the side`、`looking down`、`looking afar`、`looking at another`），配一个正在做的动作（`eating`、`walking`、`reading`），可选 `from side`、`profile`、`depth of field`。动漫模型默认就爱看镜头（Danbooru 上 `looking at viewer` 有五百多万帖，数字引自前一份调研），所以抓拍时她没写视线，服务器就补 `looking away`，负面再加 `looking at viewer`。
4. **`looking at viewer` 什么时候去掉**：无人构图一律不加；`candid` 不加；`posed`、`selfie` 照旧加（她写了别的视线就不加，现有逻辑不变）；`group` 他拍时默认加（合照本来就是看镜头），合照自拍加。
5. **多角色提示框官方支持 V4 起所有模型，V5 Curated 也在内**。官方规格里的结构是 `v4_prompt.caption.char_captions: [{char_caption, centers: [{x, y}]}]`，`v4_negative_prompt` 结构相同。官方写的上限：V4 6 人，V5 22 人；V4/V4.5 的坐标只有 5×5 格，V5 坐标可以随便放。人数 tag（`2girls`）只写在 base，每个角色框以不带数字的 `girl` 开头。**OpenAI images 形态的中转只传 prompt、negative_prompt、size，传不了这个字段**：OpenAI 的图像接口本来就没有这个字段，我们的 `openai_request` 也不发。个别中转有自己的透传字段，但那是各家私有的，不能指望。
6. **合照值得进 v1，但只做两人、只在 NovelAI 形态下开，还要原型达标才进**。门槛建议：两人合照的样张里，至少 3/4 人数正确、两人都认得出是谁、发色没有串。理由：社区的零星实测（V4.5/V5，2–3 人，原创角色）大多没有串色，偶尔会左右手或谁搭谁的肩反过来；**但没人测过「两个版权角色名分别放进角色框」在 V5 Curated 上的效果**，这是我们最关心的，只能靠原型。三人合照先不进 v1，看原型结果再说。
7. **黑名单不用「放行」**：`people` 和 `appearance` 两类继续只管她写的栏。合照的人数 tag、每个人的角色 tag 和外貌都由服务器写进 base 或角色框，不经过清洗，和画风插槽的处理方式一样。合照里她只用 id 选「和谁」（从有 `photo_tag` 的偶像里选 1 位，以后可能放到 2 位），不写人名 tag。要补的是反方向：**制作人永远不在画面里，`pov`、`pov hands`、`pov across table`、`viewer holding phone` 要加进 `people` 类**。现在这几个都没挡，`viewer holding phone` 还在已知表里。单人和无人构图里也要剥掉 `holding hands`，否则容易画出镜头外伸进来的一只手【推断，依据是 Danbooru `pov hands` 的举例就有 holding hands】。
8. **本地 tag 表要补种子**：`no humans`、`scenery`、`food focus`、`depth of field`、`profile`、`table`、`plate`、`cake`、`tree`、`building`、`side-by-side`、`heads together`、`cheek-to-cheek` 等，在 V5 Curated 里都是已知 tag（建议接口 count 都是 10000），但现在的 `known` 里没有，因为生成脚本当初没拿它们当种子。清单见第 6.4 节。
9. **原型测试矩阵**：必测 14 张、选测 6 张，合计不超过 20 张，见第 7 节。最该花钱看的是：rella 画风下无人构图会不会把人画回来（3 张），抓拍会不会还是看镜头（3 张），两人合照串不串、人数准不准（6 张）。

---

## 1. 可信的指南和工具

| 来源 | 类型 | 对我们有用的 |
|---|---|---|
| NovelAI 官方文档 [Image Generation Basics](https://docs.novelai.net/en/image/basics)、[Tagging](https://docs.novelai.net/en/image/tags)、[Models](https://docs.novelai.net/en/image/models)、[Multi-Character Prompting](https://docs.novelai.net/en/image/multiplecharacters)、[入门教程](https://docs.novelai.net/en/image/tutorial-imgintro/)、[Quality Tags](https://docs.novelai.net/en/image/qualitytags) | 【官方文档】 | `no humans` 放最前、构图 tag 列表、`object focus` 一类、`background dataset`、多角色的写法和上限 |
| image.novelai.net 的 Swagger（`/docs/index.html`，规格文件 `/docs/doc.json`） | 【官方规格】 | `V4ExternalCaption`、`V4ExternalCharacterCaption`、`Coordinates` 的字段定义 |
| [V5 发布公告](https://novelai.net/updates?id=naid-v5)（2026-08-21） | 【官方博客】 | 22 人、坐标改为自由摆放、坐标有助于减少串色 |
| Danbooru wiki：`no_humans`、`scenery`、`landscape`、`still_life`、`food_focus`、`object_focus`、`solo_focus`、`group_picture`、`side-by-side`、`looking_away`、`looking_afar`、`from_behind`、`wide_shot`、`very_wide_shot`、`depth_of_field`、`photo_background`、`pov_hands`、`2girls`、`multiple_girls` | 【Danbooru】 | 每个 tag 的准确含义（NovelAI 的 tag 沿用 Danbooru，但有改名，见前一份调研 2.1） |
| [Miint-Sunny/nai5-prompting](https://github.com/Miint-Sunny/nai5-prompting)（137 星，GPL-3.0，2026-10-30 仍在更新） | 【社区】 | 最成熟的 V5 写法 skill。多人图：人数只在主串最前写一次，角色框只写 `girl` + 外貌 + 服装；版权角色写 `girl, <规范名>`，不凭印象补外貌；无人画面写 `no humans`，不开角色框；串色时在该角色的 UC 里排除对方的特征 |
| [LlmKira/novelai-python](https://github.com/LlmKira/novelai-python)（49 星，Apache-2.0，10-24 更新） | 【社区】 | 照官方网页客户端实现的 SDK：坐标取值、`use_coords` 怎么定、每个模型最多几人；仓库里有一份网页端抓包 `record/ai/generate_image/text2image_v4.json` |
| [caru-ini/novelai-sdk 文档](https://caru-ini.github.io/novelai-sdk/docs/examples/multi-character/) | 【社区】 | V4/V4.5 坐标吸附到 5×5 格的中心（0.1/0.3/0.5/0.7/0.9），V5 原样发送 |
| [イツキ AI Laboratory：人物别欄 A/B](https://note.com/itsuki_ailab/n/n0ea83d2da0ab)（2026-07-29）、[22 人验证整理](https://note.com/itsuki_ailab/n/n4e92554f1625)（2026-08-24） | 【社区】 | V4.5 Full 同种子对比；V5 发布后别人的人数实测汇总 |
| [ats-project NovelAI 指南：複数キャラ（V5）](https://app.ats-project.net/novelai-guide/multiple-characters/) | 【社区】 | 左右位置会照做，上下位置没照做 |
| [arca.live：NAI 5 实验帖](https://arca.live/b/characterai/180655219)（2026-08-22） | 【社区】 | V5 三人图：外貌和左中右位置都保住了，但「谁搭谁的肩」「左右手」会反 |
| [Yoom：NovelAI 提示词技巧](https://lp.yoom.fun/blog-posts/novelai-prompt-techniques-highlighting-specific-tags-with-examples)（2026-04） | 【社区】 | 风景基础串 `scenery, no humans, wide shot, cityscape, …` |

**没找到**专门讲「动漫风朋友圈 / 随手拍生活照」的指南。照片感的写法只能从上面这些拼出来。

---

## 2. 决定构图的 tag

「V5」列是建议接口在 `nai-diffusion-5-curated` 下有没有把它当已知 tag（count，封顶 10000）；「表」列是我们 `photo_tags.json` 的 `known` 里有没有。

### 2.1 无人构图

| tag | 含义（出处） | V5 | 表 | 用法建议 |
|---|---|---|---|---|
| `no humans` | 「No human or human-like characters are visible in the picture」，例子包括风景配动物、物品特写【Danbooru】；官方教程说做风景时「the `no humans` tag at the start is very important」【官方文档】 | 10000 | 无 | 三种无人构图的第一个 tag，服务器写死 |
| `scenery` | 「pays special attention to the scene or landscape … usually favoring it over any characters present」【Danbooru】 | 10000 | 无 | 只用在风景构图。**有人的构图里别加**：它的意思就是景比人重要，再叠上 rella 偏爱「人在风景里」，人会更小【推断】 |
| `landscape` / `cityscape` | 自然风景，一般有地平线 / 城市风景【Danbooru】 | 10000 / 10000 | 无 / 有 | 让她写在地点栏里，服务器不写死 |
| `still life` | 「A work of art focused mostly on commonplace inanimate objects. Fruit bowl paintings are a common example.」【Danbooru】 | 10000 | 无 | **不建议用**：定义就是「静物画」，可能把画风拉向油画或水彩【推断】。改用下面两个 |
| `food focus` | 「major focus on one or more items of food or drink. It is most often … no humans, is a still life, has a certain degree of realism, and has a relatively simple background」【Danbooru】 | 10000 | 无 | 食物构图写死。注意它偏写实、偏简单背景，所以要配地点 tag（`cafe`、`on table`）把场景拉回来 |
| `object focus` | 「an inanimate object – other than weapons, vehicles, clothes or foods – is the main focus」【Danbooru】；官方把 `object focus`、`animal focus`、`cloud focus` 列为「Object Focus」类，说能让构图更清楚【官方文档】 | 10000 | 有 | 物品构图写死 |
| `sky focus` / `cloud focus` | 天空、云为主体 | 4176 / 1480 | 无 | 可放进她的地点栏，数字小，不写死 |
| `background dataset` | 数据集 tag，要放在 base 最前面，「generate landscapes, animal portraits, still lifes and other images without people in them in a photographic style」，V4.5 起【官方文档】 | 建议接口不返回（特殊 tag） | 无 | **会把画面变成实拍照片风**，和画风插槽冲突。但朋友圈里风景用实拍照片也说得通，值得测 1 张再决定 |
| `visual novel bg` | 「let you explore images in the style found in visual novels」，V5 才有【官方文档】 | 10000 | 无 | 本身就是一种画风，会和画风插槽抢，不建议默认用 |
| `location` | 「works like a combination of the indoors and outdoors tags」【官方文档】；V4.5 的质量预设里有它，V5 的没有 | 10000 | — | 不用 |

### 2.2 有人的构图（他拍、抓拍、合照）

| tag | 含义（出处） | V5 | 表 | 用法建议 |
|---|---|---|---|---|
| `looking at viewer` | 「looking directly at the viewer, i.e. looking at the camera」【Danbooru】 | 10000 | 有 | 摆拍、自拍、合照用；抓拍不用 |
| `looking away` | Danbooru 说这个 tag 本身含义模糊，建议标具体方向：`looking to the side`、`looking down`、`looking up`、`looking afar`、`looking back`、`looking ahead`【Danbooru】 | 10000 | 有 | 抓拍时她没写视线就补这个（模型理解成「不看镜头」就够了） |
| `looking to the side` / `looking down` / `looking afar` | 看向一侧 / 往下看 / 看远处（「looking off into the distance」）【Danbooru】 | 10000 | 有 | 让她按动作写：吃东西 `looking down`，看风景 `looking afar` |
| `looking at another` / `eye contact` | 看着画面里的另一个人 / 两人对视【Danbooru】 | 10000 | 无 | 只用于合照的抓拍 |
| `from side` / `profile` | 侧面机位 / 侧脸 | 10000 | 有 / 无 | 抓拍可选，让她写。前一份调研 5.1 说过机位不开放，**这里建议只在抓拍时开放这两个** |
| `from behind` | 「observed from behind. They may be looking back at the camera or completely facing away」【Danbooru】；官方列为 Framing tag【官方文档】 | 10000 | 有 | 「背影照」。看不到脸就认不出是谁，朋友圈里偶尔一张可以，但不建议当默认 |
| `facing away` | 背对 | 10000 | 有 | 同上 |
| `depth of field` / `blurry background` / `blurry foreground` | 景深，模仿「a camera only being able to focus on one distance」【Danbooru】 | 10000 | 无 | 抓拍、食物、物品都建议服务器写死 `depth of field`，营造手机拍照的感觉【推断，要实测】。`blurry foreground` 有「隔着东西偷拍」的感觉，可选 |
| `wide shot` / `very wide shot` | 人完整入画但不超过画面约 25% / 小到缩略图里认不出【Danbooru】 | 10000 / 8092 | 无 | `wide shot` 可以当景别的第五档，只给他拍和抓拍用；`very wide shot` 认不出是谁，不用 |
| `candid`、`candid photo` | — | **不是 tag**（建议接口只给出 `candy` 之类） | — | 不用。V5 能读英文句子，可以试一句「A candid snapshot taken by a friend.」，但 `photo`、`snapshot` 这类词可能把画风拉向写实【推断】，不进默认 |
| `photo (medium)` / `photo background` / `realistic` / `photorealistic` | 实拍 / 真实照片当背景（「a real-world photo is used as the background for a drawing」）【Danbooru】 | 3648 / 3784 / 10000 / 5584 | — | 已在 `style` 类黑名单里，保持 |
| `pov` / `pov hands` / `pov across table` / `viewer holding phone` | 第一人称，往往画出观者的手（官方原话「often adding first-person hands to the image」【官方文档】）；`pov hands` 是「the viewer's hands being visible」，举例有 holding hands、拿手机【Danbooru】 | 都是已知 tag | 只有 `viewer holding phone` 在 | **加进 `people` 黑名单**：观者就是制作人，而制作人从不出现在画面里 |
| `solo focus` | 「multiple people, but focused on only a single person … faceless or mostly out of frame males, POV self-insert characters, or anonymous bystanders」【Danbooru】 | 10000 | 无 | 会引来不明的第二个人（常是男性），**加进 `people` 黑名单** |

### 2.3 合照

| tag | 含义（出处） | V5 | 用法 |
|---|---|---|---|
| `2girls` / `3girls` | 「two female characters … Only living characters who are visibly present count」【Danbooru】；官方：人数 tag 只写在 base【官方文档】 | 10000 | 服务器写在 base 最前面 |
| `side-by-side` | 「Two or more characters positioned sideways right next to each other」【Danbooru】；官方：两人加 `side-by-side` 时，第一个角色框通常在左边【官方文档】 | 10000 | 他拍合照写死 |
| `group picture` | 「A group of characters posing together for a picture. The group should consist of at least three characters」【Danbooru】 | 10000 | 只在三人时用 |
| `heads together` / `cheek-to-cheek` | 两人头靠头 / 脸贴脸 | 10000 / 10000 | 合照自拍可选，让她写 |
| `arm around shoulder` / `hand on another's shoulder` / `holding hands` / `arm hug` | 肢体接触 | 10000 | 可以让她写，但社区报告「谁搭谁」经常反过来，见第 4 节 |
| `shoulder-to-shoulder` | — | 1740 | 数字小，用 `side-by-side` |
| `group selfie` | — | **不是 tag** | 写 `selfie` + 人数 tag |

### 2.4 和画风插槽（`0.7::artist:rella::`）冲突的

- **画师 tag 会把人拉回无人画面**：原型 11 已经看到 rella 偏爱「人在风景里」。一篇讲做背景的社区文章也说，不写 `no humans` 时模型「starts putting sexy women into your picture」（[the-last-secret](https://the-last-secret.mozellosite.com/news/params/post/4186810/how-to-make-ai-backgrounds)，2022 年的老模型，只作佐证）【社区】。对策是 `no humans` 放最前、负面加 `1girl, 1boy, people`，**能不能压住要实测**。
- **质量 tag 也会拉人**：「this setting may bias the AI towards generating pictures of anime characters」【官方文档】。质量 tag 还是要加（没有它画质会掉），靠 `no humans` 压。
- **`background dataset`、`visual novel bg`、`photo (medium)`、`realistic` 本身就是画风**，和插槽一起用，结果是两种画风打架。`background dataset` 只适合「风景用实拍照片」这个产品选择，选了它，风景构图就要去掉画风插槽。
- **`still life`** 带「静物画」的意思，可能和画师画风叠出油画感【推断】。
- **`scenery`、`wide shot`** 会和 rella 的「人小」倾向叠加，有人的构图里不用 `scenery`；`wide shot` 只在她选了才加。
- 前一份调研已有结论：画风插槽原样插在作品 tag 后面，不经过清洗。合照的画风也只写在 base 里，不进角色框（官方：「The base prompt determines the scene, style」）。

---

## 3. 他拍、不是摆拍：怎么写像朋友随手拍的

依据是上面这些 tag 的定义加推断，**都没出过图**：

1. **视线是关键**。`looking at viewer` 在 Danbooru 上有五百多万帖，模型默认就会看镜头；我们现在的代码在 `other` 时还会主动补上它。抓拍要反过来：不补 `looking at viewer`，她没写视线就补 `looking away`，负面再加 `looking at viewer`。V4.5 起也可以在正面写负权重 `-1::looking at viewer::`（前一份调研 2.3），但我们的负面是固定一串，放负面更简单。
2. **给一个正在做的动作，不要给姿势**。`eating`、`drinking`、`walking`、`reading`、`laughing`、`holding cup` 这类，比 `peace sign`、`hand on own hip` 更像被抓拍的瞬间。系统提示词里写明：抓拍时动作栏写「正在做什么」，不写比耶、叉腰。
3. **机位**：抓拍时可以开放 `from side` / `profile`，别人拍她常在侧面。`from behind` 能拍，但认不出脸，不建议常用。
4. **景深**：服务器写死 `depth of field`，背景虚化的手机照片感【推断】。
5. **景别**：可以加第五档 `wide shot`（人占画面四分之一以下），只给他拍和抓拍。和 rella 叠在一起人会很小，原型要看能不能认出是她。
6. **不要写** `pov`、`taking picture`（变成她在拍照）、`holding phone`、`photo (medium)`（前一份调研第 6 条）。
7. **`looking at viewer` 什么时候去掉**：

| 构图 | 服务器补不补 `looking at viewer` |
|---|---|
| 风景、食物、物品 | 不补；她的栏里写了也剥掉 |
| 自拍 `selfie` | 补（现有逻辑） |
| 摆拍 `posed` | 动作栏没写视线时补（现有 `other` 的逻辑） |
| 抓拍 `candid` | 不补；动作栏没写视线时补 `looking away`；负面加 `looking at viewer` |
| 合照 `group` | 他拍、自拍都补，写在 base。她写了 `looking at another` 就不补 |

---

## 4. 多角色提示框

### 4.1 官方说明【官方文档】【官方博客】

- 「A unique feature only found on our V4 models or higher … With V5 being able to go up to twenty-two different characters, while V4 can go up to six.」Models 页对 V5 Full 和 **V5 Curated** 写的都是「support for up to 22 distinct characters」，V4.5 Full/Curated 是「first class support for prompting images with multiple characters」。**结论：V5 Curated 支持。**
- base 写场景、画风；每个角色框写一个人，「in a way that minimizes information leakage」。
- 人数 tag「should always go into the base prompt (e.g. `2girls, 2boys, outdoors`), then in each character prompt, just specify `girl`, `boy`, or `other`, without a number」。
- 顺序：「the AI will usually follow the order in which your character prompts are listed, following a top to bottom, left to right scheme」，两人加 `side-by-side` 时第一个通常在左边。
- 坐标：默认「AI's Choice」，改成 Custom 后「the model will closely follow the positions you set」；「The V4 and V4.5 models are limited to a 5x5 grid」；建议坐标别和角色框的顺序矛盾，最好再用自然语言补一句。
- 串色时：「you can use the character's Undesired Content field to prompt against it」。
- 互动前缀 `source#` / `target#` / `mutual#`：「this syntax is not always reliable」。
- `|` 写法：「If any character prompt box exists, the `|` syntax is disabled.」
- V5 公告：「No more tiny grids. You can now freely position your character prompts」，坐标「helps make your characters more consistent … while minimizing bleed between their features. Of course, even without using the positioning feature, V5 greatly enhances how naturally your characters interact」。
- token：V4.5 是「~512 T5 tokens over the base prompt and all character prompts combined」，V5 Curated 约 703。两三个角色框远远用不完。

### 4.2 请求格式【官方规格】【社区】

官方规格 `image.novelai.net/docs/doc.json` 里的定义（`v4_prompt` 和 `v4_negative_prompt` 都是 `V4ConditionInput`）：

```
V4ConditionInput           { caption: V4ExternalCaption, use_coords: bool, use_order: bool, legacy_uc: bool }
V4ExternalCaption          { base_caption: string, char_captions: [V4ExternalCharacterCaption] }
V4ExternalCharacterCaption { char_caption: string, centers: [Coordinates] }
Coordinates                { x: number, y: number }
```

规格没写坐标的取值范围，下面几条来自社区：
- 坐标是 0–1 的归一化值，x 从左到右，y 从上到下；V4/V4.5 吸附到 0.1/0.3/0.5/0.7/0.9，V5 原样发送（caru-ini/novelai-sdk 文档、novelai-python 的 `PositionMap`）。
- 「AI's Choice」时 `use_coords: false`。novelai-python 收录的一份网页端抓包（V4.5 Curated）里，这时每个角色的 `centers` 是 `[{"x":0,"y":0}]`，网页端在 `parameters` 顶层还另发了 `characterPrompts`（`prompt`/`uc`/`center`/`enabled`）和 `use_coords`。规格里没有这两个字段；NovelAI-Image-MCP 的文档说 API 实际接受它们（「The spec is not a field whitelist」）。**只发 `v4_prompt` 够不够，原型时看 PNG 元数据确认**。
- 负面的 `char_captions` 和正面一一对应、坐标相同，没有负面时 `char_caption` 写空串（novelai-python 就这样构造）。

给我们的草案（两人他拍、不用坐标；NovelAI 形态）：

```json
"v4_prompt": {
  "caption": {
    "base_caption": "2girls, idolmaster shiny colors, 0.7::artist:rella::, side-by-side, upper body, cafe, indoors, casual, smile, looking at viewer, rating:general, very aesthetic, masterpiece, no text",
    "char_captions": [
      {"char_caption": "girl, sakuragi mano, brown hair, medium hair, brown eyes", "centers": [{"x": 0, "y": 0}]},
      {"char_caption": "girl, kazano hiori, black hair, long hair, ponytail, blue eyes", "centers": [{"x": 0, "y": 0}]}
    ]
  },
  "use_coords": false,
  "use_order": true
},
"v4_negative_prompt": {
  "caption": {
    "base_caption": "<现有 NEGATIVE_PROMPT>",
    "char_captions": [
      {"char_caption": "", "centers": [{"x": 0, "y": 0}]},
      {"char_caption": "", "centers": [{"x": 0, "y": 0}]}
    ]
  },
  "legacy_uc": false
}
```

顶层 `input` 仍然等于 `base_caption`（和现在一样）。要用坐标时，两人是 `(0.3, 0.5)` 和 `(0.7, 0.5)`，三人是 `0.2 / 0.5 / 0.8`，同时把 `use_coords` 改成 `true`。

### 4.3 OpenAI images 形态的中转

- 我们的 `openai_request` 只发 `model / prompt / negative_prompt / size / n / response_format`，OpenAI 的 `/images/generations` 本来也没有角色框字段。**这个形态下传不了 `char_captions`，可以确认。**
- 有的中转支持私有透传（例如 [GALIAIS/NovelAI2api](https://github.com/GALIAIS/NovelAI2api) 在它自己的 `/api/image/generate` 上收 `parameters`、`raw_request`；[platberlitz/sillytavern-image-gen](https://github.com/platberlitz/sillytavern-image-gen) 的「extended」模式多发一些顶层字段），但字段名各家不同，不是标准【社区】。
- `|` 写法能不能当退路：官方只说「有角色框时禁用」，没说服务端解析不解析 `|`。novelai-python 发请求时把带 `|` 的原文整串放进 `base_caption`，看不出是谁在拆。中转会不会原样转发也不知道。**不建议依赖**，而且我们的清洗本来就会剥掉 `|`。
- **建议**：`api_format == "openai"` 时不提供合照（她的说明里不列这个选项），其他构图不受影响。原型里加 1 张「两人全写在一串 prompt 里、不用角色框」的对照（矩阵 G1），看退化到什么程度；结果尚可的话，以后再考虑在 openai 形态下也开合照。

### 4.4 社区实测（都不是我们的条件）【社区】

| 出处 | 模型、条件 | 结果 |
|---|---|---|
| [イツキ AI Lab，2026-07-29](https://note.com/itsuki_ailab/n/n0ea83d2da0ab) | V4.5 Full，2girls，原创外貌，同一个种子，全写在 base 和分开写进角色框（坐标 0.3/0.7）各 1 张 | 两张发色、瞳色、服装、左右都对，**这个种子上没看到串色**；分进角色框后背景和姿势也跟着变了。作者说 1 个种子不能说明成功率 |
| [イツキ AI Lab，2026-08-24](https://note.com/itsuki_ailab/n/n4e92554f1625) 整理的他人报告 | V5，多人 | 有人用 `|` 写法、1216×832 时「4 to 5 characters were the most likely result」，换成角色框后能稳定出 8 人（一个人的条件性结果）。另有人报告「characters only look at the viewer」，互动不好控制 |
| [arca.live，2026-08-22](https://arca.live/b/characterai/180655219) | V5，三人，全用英文句子 | 三人的外貌、服装颜色、左中右位置都保住了；**「3 号把手搭在 2 号肩上」生成成了反方向，指定的左右手互换，一个人同时做两个动作时会丢一个** |
| [ats-project 指南](https://app.ats-project.net/novelai-guide/multiple-characters/) | V5，漫画配置测试 | 左右位置照做了，上下位置没照做 |
| [PixAI 的 NovelAI 评测](https://blog.pixai.art/en/novelai-review-features-pricing-pros-cons-and-is-it-worth-using-in-2026/) | V5 之前的版本（作者自己说不能当 V5 基准），三人，全写在一句英文里 | 三人发色、瞳色、服装都没串；「sharing desserts」只是暗示出来 |
| [Miint-Sunny/nai5-prompting](https://github.com/Miint-Sunny/nai5-prompting) 的规则 | V5，作者自称基于两千多张实测 | 版权角色框写 `girl, <规范名>`；人数 tag 只在主串最前写一次，`solo` 只配单人；串色时在该角色的 UC 里排除对方的特征 |

**没找到的**：两个**版权角色名**分别放进角色框、在 **V5 Curated** 上的实测；同作品里同色系角色（比如大崎姐妹）会不会认混；名字和外貌 tag 都写时是互相加强还是打架。这几条只能靠原型。

### 4.5 我们的用法建议

- **base**：人数 tag，作品 tag，画风插槽，拍法（`selfie` 或空），`side-by-side`（他拍）或 `group picture`（三人），景别，她的地点、服装、动作，视线，质量 tag。
- **角色框**：`girl, <photo_tag>, <photo_appearance>`，发帖的她放第一个（在左边或最前）。不写动作、表情，这和 nai5-prompting 的约定一致，也让每个框只管「这个人是谁」。
- **服装**：先写在 base，大家穿同一类（`casual`、`school uniform`、`idol clothes`）。各穿各的要在每个角色框里写服装，她就得为每个人写一栏，LLM 的负担和出错面都会翻倍，v1 不做。
- **负面角色框**：默认空串。原型里看到串色，再试「每个人的 UC 写上别人有、自己没有的发色 tag」，这些从 `photo_appearance` 里自动取，不用人写。
- **坐标**：默认不用（`use_coords: false`），靠顺序和 `side-by-side`。原型里对比一组坐标，有明显好处再开。
- **景别**：合照只允许 `upper body`、`cowboy shot`，自拍合照只允许 `portrait`、`upper body`。832×1216 的竖图里，全身合照的脸太小，认不出是谁【推断】。合照适合横图，1216×832 和现在的像素数一样，Opus 免费额度的条件也一样（官方：「28 or fewer Steps … if the size stays under the normal threshold」），但 `kept_as_webp` 现在会拒掉不是 832×1216 的图，要改。

---

## 5. 人数上限和常见失败

- **官方上限**：V4 6 人；V5 22 人（「In testing, we've gotten up to 22 distinct characters … using Character Positioning」，是用坐标的条件下）。novelai-python 注释说网页端的 `maxCharacters` 是 V5 32、V4/V4.5 6，和文档的 22 不一致，以文档为准。
- **实际上限**：没有官方数字。社区零星报告是：不用角色框时 4–5 人就开始不稳，用角色框能到 8 人（单人报告）。**我们只要 2–3 人，离上限很远**，要担心的不是人数上限，而是认不认得出来。
- **常见失败形态**（社区报告加 Danbooru 定义推出来的）：
  1. **人数不对**：多一个人或少一个人。base 写了 `2girls`，角色框又写 `1girl`，就成了 `2girls, 1girl, 1girl`，nai5-prompting 专门把这条列为错误。我们的角色框用 `girl`，可以避开。
  2. **发色、服装串到另一个人身上**：官方承认会漏，给的对策是用该角色的 UC。
  3. **两个人长成一张脸**：同一画师画风下更明显【推断】。
  4. **互动方向反了**：谁搭谁的肩、左右手（arca.live）。互动类 tag 让她少写，或者只写对称的（`side-by-side`、`heads together`）。
  5. **都看镜头，或者都不看**：互动和视线难控制（イツキ整理的报告）。
  6. **一个人的两个动作丢一个**（arca.live）：沿用「一个人一个动作」。
  7. **手**：前一份调研的自拍 8 张里没出过手的问题；多人搭肩、牵手时手的数量最容易错，这是常识，没有找到具体统计。
  8. **位置**：左右会照做，上下不一定（ats-project）。

---

## 6. 建议：枚举、前后缀和 tag 表

### 6.1 构图枚举和她写的栏

| 构图 `kind` | 她写的栏 | 景别 | 画面里的人 |
|---|---|---|---|
| `scenery` 风景 | 地点和时间（2–4）、景物（1–3，比如 `cherry blossoms`、`ocean`、`city lights`） | 无 | 无 |
| `food` 食物 | 地点（1–2）、食物（1–3，比如 `parfait`、`coffee`、`bento`） | 无 | 无 |
| `object` 物品 | 地点（1–2）、物品（1–3） | 无 | 无 |
| `selfie` 自拍 | 现有三栏 | `portrait` / `upper body` | 她 |
| `posed` 别人帮她拍 | 现有三栏 | 现有四档 + `wide shot` | 她 |
| `candid` 别人抓拍 | 现有三栏（动作写正在做的事，可写 `from side`、`profile`） | 同上 | 她 |
| `group` 合照 | 现有三栏 + 和谁（偶像 id，1 位；以后可能 2 位）+ 拍法（自拍 / 他拍） | 他拍 `upper body` / `cowboy shot`；自拍 `portrait` / `upper body` | 她和 1–2 位偶像 |

前一份调研里的 `other` 拆成 `posed` 和 `candid`。照片功能不必跟着改。术语表里「配图」还包括「其他偶像」：`posed` / `candid` 的主角换成另一位偶像（她给别人拍），用的还是单人提示词，只是角色 tag 和外貌换成那个人的，不需要多角色框。要不要开放由「拍板：一条动态里有什么」决定，这里只说明技术上很便宜。

### 6.2 固定前后缀草案（可以直接放进代码）

记号：`{style}` 是画风插槽（空就省掉），`{tag}` / `{look}` 是 `photo_tag` / `photo_appearance`，`{framing}` 是景别，`{place}` `{subject}` `{outfit}` `{action}` 是她写的栏清洗后的结果，`Q` 是 `rating:general, very aesthetic, masterpiece, no text`，`NEG` 是现有的 `NEGATIVE_PROMPT`。

```python
# 无人：no humans 打头；不写 1girl、solo、角色 tag、外貌、作品 tag
SCENERY = "no humans, scenery, {style}, {place}, {subject}, " + Q
FOOD    = "no humans, food focus, {style}, {subject}, {place}, depth of field, " + Q
OBJECT  = "no humans, object focus, {style}, {subject}, {place}, depth of field, " + Q
NEG_NO_HUMANS = NEG + ", 1girl, 1boy, people"

# 单人（和现在一样的前缀）
SELFIE = "1girl, solo, {tag}, idolmaster shiny colors, {style}, {look}, selfie, looking at viewer, {framing}, {place}, {outfit}, {action}, " + Q
POSED  = "1girl, solo, {tag}, idolmaster shiny colors, {style}, {look}, {framing}, {place}, {outfit}, {action}[, looking at viewer], " + Q
CANDID = "1girl, solo, {tag}, idolmaster shiny colors, {style}, {look}, {framing}, {place}, {outfit}, {action}[, looking away], depth of field, " + Q
NEG_CANDID = NEG + ", looking at viewer"
#  [, looking at viewer] / [, looking away]：她的动作栏里没有视线（_GAZES）时才补

# 合照（NovelAI 形态，char_captions）
GROUP_BASE_OTHER  = "{n}girls, idolmaster shiny colors, {style}, side-by-side, {framing}, {place}, {outfit}, {action}[, looking at viewer], " + Q
#  三人时 side-by-side 换成 group picture
GROUP_BASE_SELFIE = "{n}girls, idolmaster shiny colors, {style}, selfie, {framing}, {place}, {outfit}, {action}[, looking at viewer], " + Q
GROUP_CHAR        = "girl, {tag_i}, {look_i}"      # 每人一个，发帖的她排第一
GROUP_CHAR_NEG    = ""                              # 原型里串色了再改成「别人有、自己没有的发色」
```

说明：
- 无人构图把画风放在 `no humans, scenery`（或 `food focus` / `object focus`）后面，让「无人」排在最前；有人的构图还是现在的位置（作品 tag 后面）。
- 无人构图照用 `NEG`，只在后面补三个人物词。全年龄那些细项对无人画面用不上，但留着可以少一条分支；Human Focus 预设对无人画面也没有坏处【推断】。
- 无人构图里，她栏里出现的 `1girl`、`solo`、`selfie`、`looking …`、`holding …` 一律剥掉（风景照里写这些只会把人画回来）。实现上可以给这三种构图单独一份剥除表，不必进 `photo_tags.json` 的分类。

### 6.3 黑名单在合照时怎么处理

- **不放行任何东西**。`people` 和 `appearance` 继续只管她写的栏：她写 `2girls`、`kazano hiori`、`black hair` 照样剥掉。人数 tag、每个人的 `photo_tag` 和 `photo_appearance` 由服务器写进 base 或角色框，不经过 `_field`，和画风插槽一样不清洗。
- 「和谁」是她从名单里选的 id，不是 tag。服务器查到对方的 `photo_tag`、`photo_appearance`，任一项为空就不能合照（降级成她一个人的照片，或者让她换人；由规格定）。
- `read_tag` 里的 `seen` 现在写死了 `1girl`、`solo`（`_FIXED`），合照时要换成实际的人数 tag，避免去重出错。
- **`people` 类要补的**（所有构图都挡）：`pov`、`pov hands`、`pov across table`、`viewer holding phone`、`solo focus`。**单人和无人构图另外挡** `holding hands`。合照里放行 `holding hands`，但它是互动 tag，容易画反。
- `characters.toml` 里有一位角色的角色 tag 自带外貌词怎么办：目前 28 位的 `photo_tag` 都是纯人名，没有这个问题。

### 6.4 本地 tag 表要补的种子

都已用建议接口确认在 `nai-diffusion-5-curated` 下是已知 tag（2026-10-31），现在不在 `known` 里（`depth of field`、`blurry background` 前一份调研说是已知的，但当时没当种子加进表）：

- 无人构图的地点和景物：`no humans`、`scenery`、`landscape`、`sky focus`、`cloud focus`、`horizon`、`tree`、`building`、`reflection`、`night sky`（`cityscape`、`sky`、`cloud`、`sunset`、`ocean`、`street`、`city lights`、`cherry blossoms` 已在表里）
- 食物和物品：`food focus`、`plate`、`table`、`on table`、`bowl`、`mug`、`coffee mug`、`cake`、`dessert`、`parfait`、`ramen`、`bento`、`vase`、`cat`、`animal focus`（`food`、`coffee`、`drink`、`flower`、`object focus` 已在）
- 抓拍：`profile`、`depth of field`、`blurry background`、`blurry foreground`、`wide shot`、`looking at another`、`eye contact`、`laughing`（`looking away`、`looking to the side`、`looking afar`、`looking down`、`from side`、`from behind`、`facing away` 已在）
- 合照（只在她的动作栏里用）：`side-by-side`、`heads together`、`cheek-to-cheek`、`arm around shoulder`、`hand on another's shoulder`、`arm hug`、`group picture`（`holding hands`、`hug`、`peace sign` 已在）
- **改写表**建议加：`candid` / `candid photo` / `candid shot` → 剥掉（不是 tag，也没有对应的 tag）；`group selfie` → `selfie`；`food on table` → `on table`；`no human` → `no humans`（只在无人构图里有意义，其他构图剥掉）；`landscape view` → `landscape`；`shoulder to shoulder` → `side-by-side`。

改法：在 `backend/scripts/photo_tags.py` 的种子里加上这些，重跑脚本。

### 6.5 合照值不值得进 v1

**值得，但有条件**：只做两人，只在 NovelAI 形态下开，原型达标才进。

- **好处**：朋友圈里偶像之间的互动，是比单人自拍更有「朋友圈」感的内容；地图里的评论区也是围绕偶像之间的关系设计的。代码改动不大：`generation_request` 填 `char_captions`，`photo_prompt` 加一个分支，一个「和谁」字段。
- **风险**：两个人认不出、长成一张脸、发色互串。原作玩家对角色外貌很敏感，一张串了的合照比没有合照更糟。
- **费用**：一张合照和一张单人照价钱一样，不增加费用。
- **达标线**（建议）：原型的两人合照（矩阵 E1–E4，共 6 张）里，至少 5/6 人数正确、两个人都认得出、发色没有串。达不到就延后，v1 先做「她给别的偶像拍」的单人版，代替合照。
- **三人合照**：v1 不做。矩阵 F 只出 2 张试探，效果好再议。

---

## 7. 原型测试矩阵（给票 04）

固定条件：V5 Curated，用户的中转（A 形态 `/ai/generate-image`，同种子可复现），832×1216（另注明的除外），23 步，scale 7，`k_euler_ancestral`，画风插槽 `0.7::artist:rella::`（用户的实际配置），负面用现有 `NEGATIVE_PROMPT`（无人构图和抓拍按 6.2 补）。前后缀照 6.2 的草案拼。每张都存 PNG 元数据，确认 `char_captions` 生效。

**必测 14 张**

| 组 | 内容 | 张数 | 看什么 |
|---|---|---|---|
| A1 | 风景 `scenery`：①黄昏的街道 `street, dusk, city lights`；②海边 `ocean, beach, blue sky` | 2 | rella 下有没有把人画回来；像不像随手拍的风景 |
| A2 | 同 A1①，前面加 `background dataset`，去掉画风插槽 | 1 | 实拍照片风能不能当朋友圈风景；和动漫风比哪个好 |
| B1 | 食物 `food`：咖啡店的芭菲 `parfait, cafe, on table` | 1 | 会不会变成白底写实食物图；有没有场景 |
| B2 | 物品 `object`：桌上的花 `flower, vase, window, sunlight` | 1 | 同上 |
| C1 | 抓拍 `candid`，真乃，咖啡店，`eating, looking down`，`upper body` | 1 | 像不像抓拍；看不看镜头 |
| C2 | 抓拍 `candid`，真乃，街道，`walking`，没写视线（服务器补 `looking away`），`cowboy shot` | 1 | 只靠默认补的视线够不够 |
| C3 | C2 的种子和场景改成 `posed`（补 `looking at viewer`） | 1 | 和 C2 对比，抓拍和摆拍有没有拉开差别 |
| E1 | 合照他拍：真乃 + 灯织（棕发 / 黑发马尾），AI's Choice，`upper body, side-by-side, cafe, casual, smile`，2 个种子 | 2 | 人数对不对；两人认不认得出；有没有串色 |
| E2 | E1 第一个种子，加坐标 `(0.3,0.5)` / `(0.7,0.5)` | 1 | 坐标有没有好处 |
| E3 | 合照自拍：真乃 + 灯织，`selfie, upper body, heads together`，1 个种子 | 1 | 两人自拍会不会多出手或手机 |
| E4 | 合照他拍：大崎甘奈 + 甜花（双胞胎，`photo_appearance` 都是棕色长发、黄眼睛，只差刘海），AI's Choice | 1 | 最难的情况：会不会长成一个人、名字会不会认混 |

**选测 6 张**（看完必测再决定跑不跑）

| 组 | 内容 | 张数 | 看什么 |
|---|---|---|---|
| C4 | 抓拍 + `wide shot`，真乃，海边 | 1 | 人小了还认不认得出（rella 本来就让人偏小） |
| F1 | 三人他拍：真乃 + 灯织 + めぐる（棕 / 黑 / 金），`3girls, group picture`，AI's Choice | 1 | 三人人数和认人 |
| F2 | F1 加坐标 0.2 / 0.5 / 0.8 | 1 | 三人要不要坐标 |
| G1 | E1 第一个种子，不用角色框，`2girls, sakuragi mano, kazano hiori, <两人外貌>` 全写在一串里 | 1 | OpenAI 形态能不能退而求其次；也看角色框到底值多少 |
| H1 | E1 第一个种子，改成 1216×832 横图 | 1 | 合照用横图是不是更好（票 04 要回答尺寸） |
| H2 | A1① 改成 1216×832 横图 | 1 | 风景用横图是不是更好 |

全跑是 20 张，用户嫌多可以只跑必测的 14 张。E1 如果有一张就串了，先加跑「负面角色框写对方发色」的 1 张再下结论，这张不在上面的计数里。

---

## 查不到或没核实的

- **版权角色名分别写进角色框，在 V5 Curated 上的效果**：没找到任何实测，只能靠原型。
- **只发 `v4_prompt.char_captions`、不发网页端那份 `characterPrompts`，服务端认不认**：官方规格只定义了前者，网页端两个都发。要看原型出图的 PNG 元数据。
- **`use_coords: false` 时 `centers` 该填什么**：网页端抓包里填的是 `(0, 0)`；官方没写，推测这时会被忽略。
- **`|` 写法是服务端解析还是网页端解析**：官方没写（前一份调研也没查到）。
- **`depth of field`、`looking away`、负面 `looking at viewer` 对抓拍的实际效果**：只有 tag 定义，没出图。
- **`still life` 会不会带出油画画风**：只是从 Danbooru 定义推出来的。
- **`background dataset` 和画师 tag 一起写会怎样**：官方只说它是「photographic style」，没说和画师 tag 怎么混。
- **Danbooru 帖子数**：本机连不上 Danbooru，这次只拿到 wiki 原文，没有帖子数；用的是建议接口的 count。
- **V5 实际能稳定出几个人**：官方的 22 人是带坐标的内部测试结果，社区只有零星报告。我们只要 2–3 人，不影响结论。

## 来源一览（2026-10-31 访问）

- 官方文档：<https://docs.novelai.net/en/image/multiplecharacters>、<https://docs.novelai.net/en/image/models>、<https://docs.novelai.net/en/image/basics>、<https://docs.novelai.net/en/image/tags>、<https://docs.novelai.net/en/image/qualitytags>、<https://docs.novelai.net/en/image/undesiredcontent>、<https://docs.novelai.net/en/image/tutorial-imgintro/>
- 官方规格：<https://image.novelai.net/docs/index.html>（规格文件 `https://image.novelai.net/docs/doc.json`）
- 官方公告：<https://novelai.net/updates?id=naid-v5>（V5，2026-08-21）
- 官方 tag 建议接口：`GET https://image.novelai.net/ai/generate-image/suggest-tags?model=nai-diffusion-5-curated&prompt=…`（查询脚本和结果在仓库外的 `E:/tmp/moments-research/tagcheck.py`、`tags1.json`、`tags2.json`）
- Danbooru wiki：`https://danbooru.donmai.us/wiki_pages/<tag>`，查了第 1 节表格里列的那些 tag
- 社区：<https://github.com/Miint-Sunny/nai5-prompting>、<https://github.com/LlmKira/novelai-python>（`src/novelai_python/sdk/ai/generate_image/schema.py`、`__init__.py`、`record/ai/generate_image/text2image_v4.json`）、<https://caru-ini.github.io/novelai-sdk/docs/examples/multi-character/>、<https://xinvxueyuan.github.io/NovelAI-Image-MCP/development/api-alignment.html>、<https://note.com/itsuki_ailab/n/n0ea83d2da0ab>、<https://note.com/itsuki_ailab/n/n4e92554f1625>、<https://app.ats-project.net/novelai-guide/multiple-characters/>、<https://arca.live/b/characterai/180655219>、<https://blog.pixai.art/en/novelai-review-features-pricing-pros-cons-and-is-it-worth-using-in-2026/>、<https://lp.yoom.fun/blog-posts/novelai-prompt-techniques-highlighting-specific-tags-with-examples>、<https://the-last-secret.mozellosite.com/news/params/post/4186810/how-to-make-ai-backgrounds>、<https://github.com/GALIAIS/NovelAI2api>、<https://github.com/platberlitz/sillytavern-image-gen>
- 仓库内（只读）：`backend/src/eidolon/photo_prompt.py`、`backend/src/eidolon/image_generation.py`、`backend/src/eidolon/photo_tags.json`、`backend/scripts/photo_tags.py`、`characters/characters.toml`、`.scratch/photos/issues/04、05、11`、`origin/research/novelai-prompting:.scratch/photos/research/novelai-prompting.md`
