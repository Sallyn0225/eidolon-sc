# 做饭限时营业类游戏机制、节奏与交互模式调研报告

> 对应调研票：[01-cooking-games-mechanics-research.md](../issues/01-cooking-games-mechanics-research.md)
> 目标：为后续烹饪模型设计（05）与营业循环/经营成长设计（07）提供来自代表作的事实依据、机制拆解与设计权衡。本报告仅陈述事实、机制与权衡，不替 Eidolon-SC 做出设计拍板。

---

## 一、代表作深度拆解

### 1. 《沙威玛传奇》（Shawarma Legend）

- **开发/发行**：Eyad Alshafei / Patates Games（2024 年 7 月发行于 Steam / iOS / Android）[Steam 商店页](https://store.steampowered.com/app/3036080/Shawarma_Legend/)。
- **核心单局循环与零容错压力设计**：
  - 单局为实时限时营业日（约 2–3 分钟级短局快节奏循环），核心动线是「切肉/备土豆/炸薯条 → 放饼皮 → 填 4 种核心配料（烤肉、黄瓜、酱料、薯条）→ 卷饼并套包装袋 → 递给顾客 → **手动收桌上的金币**」。
  - **零食材成本与无完美率硬失败**：所有食材零成本，不存在原料损耗破产；也没有强制完美率（可以战略性放弃低价值或麻烦的顾客），唯一的隐性成本是玩家操作时间与体力；错做或少料的卷饼无法直接复用，只能套袋后喂给左侧员工消耗或丢弃 [Steam 社区系统与科技树指南](https://steamcommunity.com/sharedfiles/filedetails/?id=3341305528&l=schinese)。
  - **收钱机制**：金币留在柜台上不会因时间自然消失，但**营业结束时留在桌上的钱系统不会自动结算**，迫使玩家在收尾前手动清扫柜台 [Steam 社区系统与科技树指南](https://steamcommunity.com/sharedfiles/filedetails/?id=3341305528&l=schinese)。
- **备料补货压力与客单分化**：
  - 初期备料全靠高频重复手操：鼠标/手指反复滑动切旋转烤肉、手动切土豆进炸锅（基础油炸 15 秒）、点左侧员工（大鼻子工人）补齐 4 格配料槽、每种配料需点击 3 次才能铺满饼皮 [Shawarma Legend Upgrades Guide](https://grindnstrat.com/shawarma-legend-upgrades/)。
  - **客单定制机制**：前期所有顾客默认要全配料（可无脑流水线生产）；解锁「涨价与顾客自选口味（Custom Ingredients）」升级后，顾客开始提出「不要某配料 / 加石榴糖浆 / 多杯饮料 + 多份小吃」等差异化需求，心智核对成本骤升 [BaiduWiki: Shawarma Legend](https://baike.baidu.com/en/item/Shawarma%20Legend/1480415)。
- **特殊干扰顾客**：
  - **乞丐（Beggar）**：中后期（约第 10 天起）出现，拿走餐品后不会主动付钱，需要玩家在离开前点击/提醒才会付款，否则直接白嫖逃单 [Cheatbook 机制整理](https://www.cheatbook.de/files/shawarmalegend.htm)。
  - **小偷（Thief）**：在柜台偷窃尚未收取的金币，需要连续点击击打迫使其吐出偷走的金额；可通过升级「防盗警报（1000）→ 自动收钱（3100）」反制 [Cheatbook 机制整理](https://www.cheatbook.de/files/shawarmalegend.htm)。
  - **耐心安抚道具**：巴斯布萨甜点（Basbousa）等可直接喂给快失去耐心的顾客回满/延缓耐心流失 [BaiduWiki: Shawarma Legend](https://baike.baidu.com/en/item/Shawarma%20Legend/1480415)。
- **局外升级的半自动化演进与「负提升陷阱」**：
  - 科技树本质是**把前期极其繁琐的机械点击逐级压缩为半自动/全自动**：
    - 铺配料次数：3 次点击 → 2 次（$250）→ 1 次（$2100）；
    - 自动出饼机（$650）、切土豆加速（$150/$250）→ 自动切土豆（$1600）、双刃切肉（$350）→ 自动切肉（$2400）；
    - 炸锅：15s → 10s（$1000）→ 5s 且自动装填（$4500）；
    - 包装：取消拖拽改为一键包装（$800）→ 卷好自动打包（$2400）；
    - 员工培训（$1500–$2400）：一键补齐全部配料、饮料与小吃；
    - 客槽扩容：初始 3 位同时在场顾客 → 4 位（$1850）→ 5 位（$4000）[Shawarma Legend Upgrades Guide](https://grindnstrat.com/shawarma-legend-upgrades/)、[Steam 升级表指南](https://steamcommunity.com/sharedfiles/filedetails/?id=3336854589)。
  - **核心权衡与踩坑**：如果在核心自动化尚未成型前，过早解锁新副食品（可乐、薯条盒、烤盘、石榴糖浆、橙汁）或顾客挑剔口味，会大幅增加单客点击与跨屏拖拽次数（例如最右侧 5 号位顾客要 2 杯橙汁 + 2 份小吃 + 2 份薯条时，需从最左侧跨屏拖拽 6 次以上），反而导致**日收入不升反降** [Shawarma Legend Upgrades Guide](https://grindnstrat.com/shawarma-legend-upgrades/)。

---

### 2. 《Cook, Serve, Delicious!》1 / 2 / 3（Vertigo Gaming）

- **开发背景**：由 David Galindo（Vertigo Gaming Inc.）主导开发，以极高信息密度、键鼠/手柄高速操作与上百道菜谱规模著称。
- **有限工位支撑海量菜谱的架构**：
  - **Prep Stations（现做工位，CSD1 为 4→8 格，CSD2 扩至 6→14 格）**：被动接收顾客订单票与杂务（Chores，如倒垃圾、洗碗、灭鼠、冲马桶）。玩家不能主动选中空 Prep Station，只能等订单到达后逐一按键完成原料组装、烹制与出餐 [David Galindo CSD2 Preview: Holding Stations](https://chubigans.tumblr.com/post/139981408924/cook-serve-delicious-2-preview-holding)。
  - **Holding Stations（HS，保温备料台，CSD2 引入、CSD3 成为核心）**：与 Prep Station 相反，永不出现客单，由玩家主动选择空闲格**提前批量制作** 4 类内容：半成品原料（如汉堡肉饼）、批量大锅菜（如一份千层面可供 6 位客人、油炸小吃可供一打客人）、配菜（Side Dishes，延长客人耐心）与甜点。备好后客人点单可 1–2 秒内瞬间出餐（甚至在 CSD3 中通过 Ctrl 键让机器人一键 **Auto-Serve** 全部就绪订单）[David Galindo CSD2 Preview: Holding Stations](https://chubigans.tumblr.com/post/139981408924/cook-serve-delicious-2-preview-holding)、[PC Gamer CSD3 评测](https://www.pcgamer.com/cook-serve-delicious-3-review/)。
  - **HS 的反制代价**：备料台菜品有持续衰减的**新鲜度计时（Freshness）**，过期必须丢弃并产生额外垃圾杂务（加剧垃圾桶爆仓风险）；占用备料格还会挤压配菜与甜点槽位；CSD2/3 的部分 HS 菜品仍带「后置组装（post-prep）」工序，玩家实测反馈这类菜品在高压关卡中极易引发疲劳 [David Galindo CSD2 Preview](https://chubigans.tumblr.com/post/139981408924/cook-serve-delicious-2-preview-holding)、[CSD3 Steam 讨论区反馈](https://steamcommunity.com/app/1000030/discussions/3/1745643665631401854/)。
  - **通用工序模板**：上百道菜谱并未各自编写独立小游戏，而是由「选材键序列（如千层面循环按 `PSCR`）+ 多阶段翻面/切配/加热 + 熟度计时 + 后置加料」等极少数通用操作原语组合而成 [David Galindo: The Speed of a Keyboard, in Controller Form](https://www.gamedeveloper.com/design/the-speed-of-a-keyboard-in-controller-form)。
- **CSD2 的关键设计演进：分离「烹饪时长」与「出锅防糊窗口」**：
  - 在 CSD1 中，菜品的烹饪时长（Cook Time）与煮熟后的防糊窗口（Ready Time）绑定为同一数值，导致龙虾等慢煮菜顺理成章拥有极长的安全宽限期；同时旧版只有 8 方位时钟与 4 色温度计，红区剩余时间难以精确判断，且烧糊的菜仍可滞留工位并勉强作为 Average 订单出餐 [David Galindo CSD2 Preview: Order Tickets](https://chubigans.tumblr.com/post/139122771199/cook-serve-delicious-2-preview-order-tickets)。
  - **CSD2 改动**：
    1. **解耦两个计时器**：允许高端复杂菜（如惠灵顿牛排、舒芙蕾）拥有很长的烹饪时间，但成熟后只有极短的完美出锅窗口，制造精准卡点的紧张感；
    2. **更友好的读秒反馈**：升级为 360° 连续表盘 + 4 象限逐段点亮；进入最后红色防糊区时**计时器自动减速 50%**、伴随黑烟与剧烈抖动，在“更难的机制”与“更清晰的可读性”间取得平衡；
    3. **更严厉的烧糊惩罚**：一旦烧糊直接起火强制弹出工位、记为 Bad Order，且可能触发灭火杂务，不能再凑合出餐 [David Galindo CSD2 Preview: Order Tickets](https://chubigans.tumblr.com/post/139122771199/cook-serve-delicious-2-preview-order-tickets)。
- **开张前自选当日菜单的策略深度**：
  - **CSD1/2 的 Boosters & Detractors 与 Buzz 系统**：玩家只能从菜谱库中挑出有限道菜（如 CSD1 为 6 道）放入当日 Active Menu。每道菜带有正负词条（24+ 种）：如 `Menu Rot`（连续多日挂在菜单上会降低人气，需撤下至少 2 天恢复，强迫轮换）、`The Muncher`（零食类在高峰期不会被点单，用来给高峰减压）、`Rainy Day Food`（雨天 +5% Buzz）、`The Fats`（同场 ≥3 道油腻菜触发 -10% Buzz 惩罚）、`Trashy`（增加垃圾杂务）[Vertigo Gaming 官方博客: Boosters and Detractors](https://www.vertigogaming.net/blog/?p=1646)。
  - **Buzz（热度）的双刃剑数值**：热度越高客流越大，但客人耐心越短——0% Buzz 时基础耐心为 37 秒，每提升 5% Buzz 减少 1.5 秒，直至 115% Buzz 时耐心压低至仅 1 秒！单局约 7 分钟，含 12:00 PM 与 6:00 PM 两轮各 1 分钟（现实时间）的 **Rush Hour**，高峰期配菜提供的耐心加成减半 [CSD Wiki: How to Play](https://cookservedelicious.fandom.com/wiki/How_to_play_guide_for_Cook,_Serve,_Delicious)。
  - **CSD3 的餐车分段与菜单点数（Points Tariff）**：单局约 10 分钟，改为「行车备料段 → 站点集中出餐」循环；菜单分为 **HS 批量菜** 与 **SO 预约特餐**（行车途中预先做好，数量受 Prep Station 上限约束）。关卡要求当日菜单达到指定难度点数总和（每道菜 0–5 分），且官方采纳玩家建议后把**开启的额外 Prep Station 设为 -1 点菜单难度门槛的调节器**——开启更多现做工位会提高操作并发上限，但换来更宽松的选菜空间，形成显式风险收益交换 [CSD3 Steam 官方更新公告](https://store.steampowered.com/news/posts/?appids=1000030&enddate=1588272816&feed=steam_community_announcements)、[PC Gamer CSD3 评测](https://www.pcgamer.com/cook-serve-delicious-3-review/)。

---

### 3. 《老爹餐厅》系列（Papa's ...eria，Flipline Studios）

- **分站式微操架构（Station-based Multitasking）**：
  - 典型结构为 3–4 个独立切屏工位：**Order Station（大堂接单）→ Grill/Fry/Bake/Mix Station（火候/混合控制）→ Build/Top Station（空间堆叠与淋酱）→ 可选第四工位（如 Drink/Sides Station）** [Papa's Pancakeria 官方 FAQ](https://i.flipline.com/games/papaspancakeria/faq.html)。
  - 与 CSD 的纯按键抽象不同，老爹系列强调**连续模拟量微操**：煎台每块食物带双进度条（左 Flip Meter 显示两面生熟、右 Time Meter 显示总进度，需在半程翻面）；淋酱/撒料强调沿食物表面均匀涂抹、块状配料讲究等距摆放；饮料机/搅拌机带移动指针条，停在中心区域触发额外小费 [Papa's Pancakeria 官方 FAQ](https://i.flipline.com/games/papaspancakeria/faq.html)。
- **多维度独立评分与顾客成长**：
  - 每份订单按工位拆分为多项百分比评分（**Waiting/Order Score** 等候分、**Grill/Cook Score** 火候分、**Build/Top Score** 组装对称与配料准确分，及可选第 4 工位分），综合均分决定小费与顾客星级：
    - 总分 ≥80% 为该顾客累积 1 颗星，满 5 星晋升铜/银/金顾客奖章（Customer Award），后续点单与评分动画变快且小费更高；
    - 总分 <60% 会将该顾客当前未满星条清零（不剥夺已获勋章）[Papa's Pancakeria 官方 FAQ](https://i.flipline.com/games/papaspancakeria/faq.html)。
  - **压轴挑战设计**：每天营业尾声都会出现一位标准更苛刻的 **Closer（压轴客）**（7 天轮换，每周仅来一次）；其中每周一次的美食评论家 **Jojo** 每次随机点单，若令其满意可赢得持续 3 天的蓝丝带（Blue Ribbon），全店小费提升 [Papa's Pancakeria 官方 FAQ](https://i.flipline.com/games/papaspancakeria/faq.html)。
- **多客并发下的注意力切换工具**：
  - 由于工位切屏存在「视野盲区」（在组装台看不到大堂新客与煎台糊锅），游戏通过三层机制支撑并发：
    1. **物理小票挂轨（Ticket Line）**：玩家可自由拖拽小票在顶部滑轨分区排布（如左新单、中煎制、右待组装），拖到侧边大挂钩可放大查看，避免死记硬背；
    2. **听觉与视觉跨屏提示升级**：Door Chime（进门风铃）、Grill/Waffle Timers（翻面/出锅闹铃）与大堂等候人数角标；
    3. **大堂家具减缓等候扣分**：海报与互动家具（报摊、点唱机）直接提升 Waiting Score 容忍度；熟手还可在开店动画瞥见前 2 位客人后「提前下锅预煎」[Papa's Pancakeria 官方 FAQ](https://i.flipline.com/games/papaspancakeria/faq.html)。
- **触屏移动端适配经验（`To Go!` vs `HD` vs PC/Flash）**：
  - Flipline Studios 联合创始人 Tony Solary 在官方开发日志中详述了将 Flash 键鼠交互重构为小屏手机 `To Go!` 的原则（同时单独推出面向平板大屏的 `HD` 版，拒绝“一套 UI 强行缩放”）[Flipline 官方 Apps 说明](https://www.flipline.com/apps.html)：
    1. **解决手指遮挡（Occlusion）**：在 Build/Top Station 放弃 PC 端“用光标抓配料在食物上方精准落点”的做法，改为**让配料从顶部固定下落，玩家用手指在底部左右拖动食物/圣代去接配料**，确保手指永远不遮挡落点视线 [Flipline Blog: Sneak Peek Top Station To Go](https://www.flipline.com/blog/archives/3592)。
    2. **拇指热区重构**：把原本附着在机器上的小号 Pour 按钮拆离出来，放大移至屏幕左下角拇指舒适区，并将计时条直接放在按钮正上方保持视觉联动 [Flipline Blog: Sneak Peek Build Station To Go](https://www.flipline.com/blog/archives/3559)。
    3. **复杂操作拆步降维**：在《Freezeria To Go!》中把原本同屏堆叠的顶部配料拆为「先选奶油（独立步骤）→ 再用左侧 Switch 按钮在 **Pourables（需左右拖动接取的糖浆/撒粉）** 与 **Placeables（对齐后点按落下的樱桃/饼干）** 之间切换」，既容纳更多配料又避免小屏误触 [Flipline Blog: Sneak Peek Top Station To Go](https://www.flipline.com/blog/archives/3592)。
    4. **利用多点触控反超鼠标**：煎台支持多指同时点按翻多块肉饼，组装台支持一手按住底部滑槽微调、另一手点按落料 [Flipline Blog: Papa's Burgeria To Go](https://www.flipline.com/blog/archives/2789) / [Flipline Wiki: Burgeria To Go](https://fliplinestudios.fandom.com/wiki/Papa%27s_Burgeria_To_Go!)。

---

### 4. 《东方夜雀食堂》（Touhou Mystia's Izakaya）

- **昼夜分离循环**：
  - **白天（10:00–18:00）**：行动消耗制（不按现实秒流逝），用于采买/采集食材、推进羁绊、在家用烤箱预制外带/备菜。
  - **夜晚营业（18:00–24:00）**：实时制，时钟每数秒跳进 5 分钟；打开料理菜单或图鉴时**时间暂停**；到达 24:00 后排队客离去，但已落座客人会继续吃完并可能追加点单。左侧「气氛/热度槽（Heat Bar）」随好评上升并提高客流量 [Steam 社区基础机制指南](https://steamcommunity.com/sharedfiles/filedetails/?id=2730526153)。
- **厨具 + 主材 + 配料的组合出菜与标签代数**：
  - **5 类通用厨具**：煮锅（Boiling Pot）、烤架（Grill）、油锅（Frying Pan）、蒸锅（Steamer）、料理台（Cutting Board）。每晚可携带的厨具格数受等级限制，允许带多个同类厨具提升并发产能；不同厨具系列（基础 / Super / Xtreme / 夜雀 / 核能 / 可疑 / 赏月）附带加速、提高客人复购率、完美音游无视稀客点单或 40% 几率出黑暗物质等差异化词条 [Mystia Wiki: Kitchenwares](https://touhou-mystias-izakaya.fandom.com/wiki/Kitchenwares)。
  - **菜谱组合规则**：选择「对应厨具 + 基础菜谱主材」后，可自由追加任意配料至**最多 5 种食材**（达到 5 种自动获得 `大份（Large Portion）` 标签）。玩家额外投入的配料不增加菜品售价，只用于叠加标签以换取更高满意度与小费，从而在「食材库存消耗」与「小费/评价收益」间形成权衡 [Steam 社区基础机制指南](https://steamcommunity.com/sharedfiles/filedetails/?id=2730526153)、[Mystia Wiki: Tags](https://touhou-mystias-izakaya.fandom.com/wiki/Tags)。
  - **标签优先级覆盖与冲突禁区**：
    - 菜品自带粉红原生标签，追加食材提供橙色附加标签，价格自动派生 `实惠`（<20￥）或 `昂贵`（>60￥）标签，每日报纸还会隐藏附加 `流行/冷门` 趋势标签。
    - **互斥覆盖规则**（前者划掉后者）：`肉 > 素`、`大份 > 小份`、`饱腹 > 下酒`、`重油 > 清淡`、`灼热 > 清爽`。
    - **黑色禁忌标签**：一旦追加的配料带有该菜品的黑色禁用标签，整道菜直接坍缩为 **黑暗物质（Dark Matter）**，上菜触发 -2 评价惩罚（特定角色或符卡例外）[Mystia Wiki: Tags](https://touhou-mystias-izakaya.fandom.com/wiki/Tags)。
- **普客 vs 稀客与符卡反应机制**：
  - **普通顾客**：只从当日挂牌菜单点单；按结果分为黑（错单）、绿（满足所点菜与酒）、橙（满足所点 + 至少 1 个**额外添加**的偏好标签）[Mystia Wiki: Customers](https://touhou-mystias-izakaya.fandom.com/wiki/Customers)。
  - **稀客/特殊角色（Rare & Special Guests）**：不报菜名，而是给出指向偏好标签的模糊要求（首次点出时记入图鉴，羁绊 Lv.5 揭露全部喜恶），按积分制严格定级：`命中喜好标签 +1`（菜与酒均计入）、`命中厌恶标签 -1`、`黑暗物质 -2`：
    - **黑评（≤0 分）**：掉满意度、断连击、触发**惩罚符卡**（如妖梦令客人耐心 2 倍速下降、青娥令稀客有几率额外放惩罚卡）；
    - **紫评（1 分）**：断连击（若两个要求标签均未满足，评分锁死最高紫评）；
    - **绿评（2 分）**：无增减；
    - **橙评（3 分）**：涨满意度（若仅满足 1 个要求标签，评分锁死最高橙评）；
    - **粉评（≥4 分且满足双要求标签）**：大幅涨满意度并触发**奖励符卡**（如幽幽子整晚让客人瞬间吃完）[Mystia Wiki: Customers](https://touhou-mystias-izakaya.fandom.com/wiki/Customers)、[Mystia Wiki: Status Effects](https://touhou-mystias-izakaya.fandom.com/wiki/Status_Effects)。
  - **角色专属彩蛋与预算限制**：存在高于通用规则的专属反应（如给恋恋上“帽子造型慕斯”强制黑评、给蕾米莉亚上“帽子造型蛋糕”强制粉评、给梅蒂欣上黑暗物质保底橙评）；稀客还有预算上限，轻度超支绿框提醒、重度超支直接黑框放惩罚符卡 [Mystia Wiki: Customers](https://touhou-mystias-izakaya.fandom.com/wiki/Customers)。
  - **烹饪音游（Sparrow Tune）与爆发期**：出菜时随机触发简短节拍判定——全漏变黑暗物质，全中概率获得 60 秒增益（冻结耐心 / 无限距离投掷上菜 / 客人瞬间吃完），集齐三者自动引爆 60 秒 **Hyper 模式**（三效果合一且免音游），把高压操作节奏拉出“积攒 → 爽快释放”的波峰 [Mystia Wiki: Status Effects](https://touhou-mystias-izakaya.fandom.com/wiki/Status_Effects)。

---

### 5. 《可口的披萨，美味的披萨》（Good Pizza, Great Pizza）与《胡闹厨房》（Overcooked）

#### 5.1 《可口的披萨，美味的披萨》（TapBlaze）
- **点单表达与“对话解谜”机制**：
  - 顾客极少用冷冰冰的图标列表点单，而是使用自然语言、谐音梗、文化典故与谜语（例如只说“想要一片素食草原”或复杂的半拼/去料/双烤指令），并依赖一组隐式常规（未说明则默认白面团、红酱/青酱、切 6 块、每料铺 18 份均匀分布）[GPGP Wiki: List of Orders](https://good-pizza-great-pizza.fandom.com/wiki/List_of_orders)。
  - **“What?”追问权衡**：玩家听不懂时可点“什么？（What?）”让顾客换更直白的说法（最多追问约 3 次），但**每次追问都会扣除顾客耐心/满意度（Happiness Meter）**，压缩后续制作时间并减少小费——用“信息清晰度”与“利润/时间”做精巧交换 [Steam 玩家评测拆解](https://steamcommunity.com/id/mzcookies/recommended/770810/)、[GPGP Wiki: List of Orders](https://good-pizza-great-pizza.fandom.com/wiki/List_of_orders)。
- **低焦虑单客串行节奏 + 中期外卖异步并发**：
  - 常规堂食严格采用**单客串行（每次只接 1 位店内客人）**，营业时间为 12:00 PM – 9:00 PM（升级夏令时后延至 10:00 PM），每天通常接待 5–10 位客人，烤箱基础烤制 10 秒（升级快速烤箱缩至 5 秒），整体属于低挫败、强叙事的治愈节奏 [NamuWiki: GPGP Shop](https://en.namu.wiki/w/%EC%A2%8B%EC%9D%80%20%ED%94%BC%EC%9E%90%2C%20%EC%9C%84%EB%8C%80%ED%95%9C%20%ED%94%BC%EC%9E%90/%EC%83%81%EC%A0%90)。
  - 第 3 章引入 **ZaZoom 外卖 App** 后，才在单客框架上叠加温和的异步并发：每日最多 3 单定时取餐（默认 3:30 / 5:15 / 7:15 PM），玩家必须在做堂食披萨的间隙顺手做好外卖放进**保温箱（最多存 5 个）**；骑手到达时无法再进后厨现做，迫使玩家提前规划烤箱空档 [GPGP Wiki: ZaZoom App](https://good-pizza-great-pizza.fandom.com/wiki/ZaZoom_app)。
- **自动化减负与商业/本地化洞察**：
  - 随着章节推进配料增至数十种，纯手动给每张饼点 18 下极易疲劳，因此店铺提供了按单个配料逐一购买的 **Auto Buddy（自动放料助手）**、自动切饼机、放料辅助线（Topping Guide）以及移动/Steam 差异化定价的升级项 [GPGP Wiki: Upgrades](https://good-pizza-great-pizza.fandom.com/wiki/Upgrades)。
  - TapBlaze CEO Anthony Lai 与社区负责人 Yuni Cho 在 GDC 与 GamesBeat 访谈中提到，该作在无买量前提下靠持续迭代与深度本地化/文化适配（当地梗、节日与故事角色）实现超 3 亿下载与百万 DAU [GDC Vault 演讲简介](https://www.gdcvault.com/play/1025561/-Good-Pizza-Great-Pizza)、[GamesBeat 2024 访谈实录](https://venturebeat.com/games/how-tapblazes-good-pizza-great-pizza-reached-300m-downloads/)。

#### 5.2 《胡闹厨房》（Overcooked，Ghost Town Games）
- **为何把烹饪压缩为极少原子动作（切、煮/煎、装盘、洗碗）**：
  - 联合创始人 Phil Duncan 与 Oli De-Vine 在 *Game Developer* 深度复盘与 *MCV/DEVELOP* 事后复盘中明确记录了早期原型的教训：
    - **早期高自由度配方构建导致挫败**：最初原型偏重“菜谱构建（recipe construction）”、允许极高操作自由度——玩家能往锅里乱加多余洋葱、食材只切一半、文本式菜谱界面且**不显示锅内已有内容**。结果在展会试玩中，开发者不得不站在玩家身后不断提醒“不能这么做”，玩家频繁陷入“这锅里到底放了几个洋葱？”的琐碎失误和沮丧中，且玩家对复杂菜谱本身的兴趣远低于对**厨房空间协作与环境谜题**的兴趣 [MCV/DEVELOP Post-Mortem](https://mcvuk.com/development-news/the-develop-post-mortem-overcooked/)、[Phil Duncan: Game Developer Deep Dive](https://www.gamedeveloper.com/design/game-design-deep-dive-building-truly-cooperative-play-in-i-overcooked-i-)。
    - **大刀阔斧做减法与防呆限制**：
      1. **输入极简**：全游戏压到**1 摇杆 + 2 按键**（拿起/放下、交互切菜/洗碗；2 代仅追加冲刺与投掷），拒绝给不同厨师做数值差异，保证非核心玩家和家庭成员零门槛上手 [Phil Duncan Deep Dive](https://www.gamedeveloper.com/design/game-design-deep-dive-building-truly-cooperative-play-in-i-overcooked-i-)、[Nintendo UK 访谈](https://www.nintendo.com/en-gb/News/2017/April/Interview-Cooking-up-chaos-in-Overcooked-Special-Edition-on-Nintendo-Switch-1214957.html)。
      2. **取消文本查阅与摆盘微操**：用**纯图标化订单卡片**替代文字说明，严禁未切食材下锅或装盘，锅具上限锁定并直接浮现内容图标；所有菜谱无须查阅多页菜谱书，也没有独立摆盘/火候微调小游戏，统一归约为「取料 → 切 → 煮/煎/烤 → 装盘 → 上菜 → 洗碗」几个原子交互 [Phil Duncan Deep Dive](https://www.gamedeveloper.com/design/game-design-deep-dive-building-truly-cooperative-play-in-i-overcooked-i-)。
      3. **UI 认知预算守恒**：Oli De-Vine 指出，UI 传达菜谱的上限非常紧，因此**每当关卡引入一道新菜谱，团队就必须刻意调低环境机关的复杂度**，避免玩家双线信息过载 [MCV/DEVELOP Post-Mortem](https://mcvuk.com/development-news/the-develop-post-mortem-overcooked/)。
      4. **“命数生存制”改为“限时积分制”**：早期漏单会扣命直至 Game Over，玩家感觉一直在“苟活并不断失败”；改为固定限时冲分、漏单仅扣少量分数后，玩家获得了沟通喘息空间 [Phil Duncan Deep Dive](https://www.gamedeveloper.com/design/game-design-deep-dive-building-truly-cooperative-play-in-i-overcooked-i-)。
  - **极简动作如何制造持续紧张感（三根支柱）**：(1) 原子任务总数始终大于人数；(2) 引入**等待延迟与滞后回流**（汤锅煮熟后继续放着会起火；脏盘子按非明示节拍回流，逼迫团队打断流水线去洗碗）；(3) **动态环境干扰**（滑动甲板、地震裂谷、传送带、浮冰）阻止玩家形成一成不变的分工死循环 [Phil Duncan Deep Dive](https://www.gamedeveloper.com/design/game-design-deep-dive-building-truly-cooperative-play-in-i-overcooked-i-)、[Superjump 设计分析](https://www.superjumpmagazine.com/overcooked-how-design-creates-teamwork/)。

---

## 二、跨作横向综合对比与权衡

### 1. 通用烹饪原语的抽象粒度

不同作品在「工序仿真度」与「菜谱可扩展性 / 多线并发上限」之间呈现清晰的反比权衡：

| 抽象范式 | 代表作 | 备料/切配 | 厨具/火候状态机 | 调味/组装规则 | 优势与代价权衡 |
|---|---|---|---|---|---|
| **极简空间原子** | Overcooked | 单键按住读条（切） | 煮/煎/烤（完成→起火两态） | 食材放盘即自动合成 | 上手门槛最低、适合强空间/多人调度；但单道菜烹调手感趋同、菜谱深度受图标 UI 上限制约 |
| **键位序列 + 批处理** | CSD 1/2/3 | 按键切配或进 HS 预制 | CSD2 起**解耦烹饪时长与防糊窗口**；HS 有新鲜度衰减 | 按字母/快捷键依次加料 | 极少数模板即可撑起 200+ 菜谱、吞吐量最高；但强依赖肌肉记忆，信息密度不适合小屏触控 |
| **厨具 × 食材标签代数** | 东方夜雀食堂 | 白天采买/备菜，夜间零手切 | 5 类厨具固定耗时 + 随机短音游 | 底座菜谱 + 自由加料（≤5料），通过**标签覆盖/禁区**运算 | 组合自由度高、角色喜好表达极强；但夜晚单菜烹饪交互偏“菜单勾选+等条”，缺乏真实烹调手感 |
| **高交互手操流水线** | 沙威玛传奇 | 滑动切肉、切土豆、点击补货 | 炸锅定长读条（15s→5s） | 放饼→点填4料→卷→打包 | 前期“手忙脚乱”的物理爽感强，升级自动化落差极大；但 SKU 一多极易变成重复鼠标拖拽劳动 |
| **连续模拟量分站微操** | Papa's 系列 / GPGP | 拉面/倒糊/选杯 | 双面火候条+精准翻面（Papa's）/ 单或双烤烤箱（GPGP） | 空间均匀度、对称度、落点位置评分 | 单菜制作沉浸感与掌控感最强；代价是单客耗时极长，难以支撑高并发客流（GPGP 干脆改为单客串行） |

### 2. 单局时长、并发客槽、耐心与评分/连击机制

| 作品 | 典型单局时长 | 同时在场/并发客槽 | 耐心与压力调节机制 | 容错、连击与评价维度 |
|---|---|---|---|---|
| **沙威玛传奇** | 约 2–3 分钟（实时短局） | 初始 3 槽，升级扩至 4–5 槽 | 独立耐心条；可用巴斯布萨安抚；乞丐/小偷制造突发中断 | **无完美率硬失败**、无原料成本；漏客仅少赚；未收桌钱不自动入账 |
| **CSD 1 / 2** | 约 7 分钟（含 2 次 1 分钟高峰期） | 4→8（CSD1） / 6→14（CSD2）现做槽 + HS 备料槽 | **Buzz 越高耐心越短**（37s → 最低 1s）；配菜加耐心但高峰减半；杂务占工位 | 极苛刻完美日（Perfect Day）追求；CSD2 烧糊即 Bad Order 并可能起火；杂务失误给 Sick 扣大额 Buzz |
| **CSD 3** | 约 10 分钟（多站点行车+停靠） | 现做槽（可开关调难度）+ HS 保温槽 | 行车期无客压、停靠期爆发；敌车攻击可损毁温控令新鲜度骤降 | 金/银/铜牌评价；Auto-Serve 带来高频连续清场爽感 |
| **老爹餐厅系列** | 约 4–6 分钟（固定每日客数+压轴客） | 排队大堂多客 + 顶部小票轨同时挂多单 | 进店即开始消耗 Waiting Score；大堂家具/海报减缓扣分 | 按工位打百分比分（等候/火候/组装）；≥80% 涨星升勋章，<60% 清空当前星条；周常美食家发蓝丝带 |
| **东方夜雀食堂** | 夜间营业约 3–5 分钟（菜单暂停） | 多桌位并发（随店铺升级扩张） | 客人有耐心条；完美音游可触发 60s 冻结耐心/瞬吃/投掷上菜，集齐进 Hyper | 连击（Combo）随紫/黑评中断；稀客 5 档颜色评价并触发正负**符卡**；有预算上限判定 |
| **可口的披萨** | 约 3–5 分钟（12:00–9:00/10:00 PM） | **堂食 1 客串行** + 第 3 章起最多 3 单异步外卖 | Happiness Meter 随等待与点“What?”下降；Happy Folks 升级与送花提升耐心 | 错单直接退款（净亏原料与时间）；无高强度连击清零焦虑 |
| **Overcooked** | 固定 2–4 分钟关卡 | 顶部滚动订单队列（通常 3–5 张并发） | 订单条倒计时，超时扣小费/微扣分并重刷；脏盘回流不可预测 | 早期扣命制已废弃，改为定时冲星（1–3 星）；按顺序出餐维持连击小费加成 |

### 3. 局外成长杠杆与经济/节奏踩坑

各作常用的局外成长杠杆可归纳为四类，每一类都伴随着已被验证的设计踩坑：

1. **操作减负 / 半自动化升级**（沙威玛自动机、GPGP Auto Buddy、Papa's 闹铃、CSD3 加热灯/Auto-Serve）
   - **正向作用**：将玩家注意力从“低级重复点击”释放到“高阶决策与多线调度”，形成清晰的成长体感。
   - **踩坑**：若前期未自动化就解锁大量高点击 SKU（沙威玛过早买饮料/薯条盒、GPGP 未买 Buddy 就堆满十几种配料），单客操作量线性暴涨但收益涨幅跟不上，产生**“花钱买罪受”的负提升体验** [Shawarma Upgrades Guide](https://grindnstrat.com/shawarma-legend-upgrades/)、[GPGP Upgrades](https://good-pizza-great-pizza.fandom.com/wiki/Upgrades)。
2. **产能/并发扩容**（客槽扩容、Prep Station 增多、厨具槽位增加、快速烤箱）
   - **正向作用**：直接提高单局理论收入天花板。
   - **踩坑**：扩大客流/工位上限若不同步降低单客认知成本或给予额外激励，高难度下玩家会主动规避扩容——CSD3 早期测试中玩家甚至选择买了 Prep Station 后手动关掉，最终开发者不得不将其改造为「每开一个额外工位，当日菜单难度点数要求 -1」才解决动机错配 [CSD3 Steam 官方公告](https://store.steampowered.com/news/posts/?appids=1000030&enddate=1588272816&feed=steam_community_announcements)。
3. **菜单扩展与强制轮换**（CSD Boosters/Detractors、东方夜雀食堂库存轮换）
   - **正向作用**：防止玩家永远只卖最高性价比的 1–2 道“逃课菜”。CSD1/2 用 `Menu Rot`、天气词条与油腻惩罚倒逼换菜；夜雀食堂则用**有限原料库存 + 每日潮流标签 + 地点客群偏好**自然驱动轮换。
   - **踩坑**：若菜谱池里混入工序极度冗长但收益/订单权重未补偿的菜（如 CSD3 早期带复杂后置工序的 HS 菜），玩家会将其彻底打入冷宫 [CSD3 Steam 讨论区反馈](https://steamcommunity.com/app/1000030/discussions/3/1745643665631401854/)。
4. **原料经济模型：零成本 vs 进货成本**
   - **零成本模型**（沙威玛传奇、CSD）：玩家敢于试错和战略弃单，失败惩罚体现为时间/连击/评分损失，心流不被破产焦虑打断。
   - **有成本/库存模型**（东方夜雀食堂、GPGP）：每放一片料都要算成本或消耗白天采集的库存，赋予“精准控料”与“白天筹备”策略意义；但如果叠加高错单退款（GPGP）或黑暗物质报废，前期经济滚雪球失衡的风险显著高于零成本模型。

### 4. 电脑键鼠 vs 手机横屏触控的交互模式与踩坑

从开发者一线复盘（David Galindo、Flipline Studios）及跨端游戏实测可见，键鼠与手机横屏触控存在根本性人因差异：

1. **输入链路步数与盲打能力差异（David Galindo 实证拆解）**：
   - David Galindo 在 *Game Developer* 撰文将同一道加料动作按设备拆解为操作步数：**键盘 3–4 步**（熟悉键位后可直接跳过“扫视配料表”实现盲打，最快且精准）→ **触屏 4 步**（按钮更大、双手直达响应快于光标移动，但因为必须点击可视按钮，无法完全跳过视觉扫描）→ **鼠标 4 步**（单指针跨屏移动大幅拉低吞吐速度）→ **手柄摇杆轮盘 6 步+**（需持续视觉微调防过冲，最终被迫改为“把手柄当快捷键映射”）[David Galindo: The Speed of a Keyboard, in Controller Form](https://www.gamedeveloper.com/design/the-speed-of-a-keyboard-in-controller-form)。
   - 也正因 CSD2/3 屏幕同时承载多达 14 格 Prep Station + 顶部 Holding Stations + 复杂快捷键，David Galindo 在 2023 年访谈中明确表示 **CSD2 与 CSD3 过于复杂，无法直接搬上手机小屏**，仅初代做过放宽手势容错与放大 UI 的移动移植 [TouchArcade 2023 访谈](https://toucharcade.com/2023/05/15/cook-serve-forever-steam-deck-early-access-interview-mobile-ports-vertigo-gaming/)。
2. **手机横屏触控的四大高频踩坑与成熟解法**：
   - **踩坑 A — 手指遮挡落点**：PC 鼠标光标极细不会挡住食物，但手机上直接拖拽配料到中心食物会被指肚遮死。**解法**：参考 Flipline `To Go!` 思路——保持配料/出料口固定在上方，让玩家在下方空白区**左右拖动容器去接料**，或使用半透明偏移预览 [Flipline Blog: Top Station To Go](https://www.flipline.com/blog/archives/3592)。
   - **踩坑 B — 小按钮密排误触与屏幕边缘死角**：手机横屏高度紧张，直接照搬 PC 横向多列图标极易误点。**解法**：将高频触发键（如倾倒/确认/切换）拆出放大并置于**左下/右下双拇指热区**，将读条紧贴按钮上方；配料种类多时拆为分步或标签页切换（如 Pourables / Placeables），避免同屏塞入超过手指宽度容忍度的热区 [Flipline Blog: Build Station To Go](https://www.flipline.com/blog/archives/3559)、[Flipline Blog: Top Station To Go](https://www.flipline.com/blog/archives/3592)。
   - **踩坑 C — 单指针跨屏拖拽疲劳（PC 反过来吃亏）**：沙威玛传奇等以移动端单/双指短距离点拖设计的布局搬到 PC 后，鼠标单光标需要频繁在最左侧饮品机与最右侧 5 号顾客之间长距离来回拖拽，极易引发手腕疲劳 [Shawarma Upgrades Guide](https://grindnstrat.com/shawarma-legend-upgrades/)。反之，支持**点选-再点目标（Tap-to-Select / Click-to-Serve）或快捷键补位**可同时缓解 PC 长距拖拽与手机拖拽断触问题。
   - **踩坑 D — 多指并行 vs 单光标不对称**：移动端天然支持双手多指并行（如 Papa's 煎台多指同翻、沙威玛左右手同时切肉收钱），而 PC 仅靠鼠标是单点串行——跨端平衡时若只按键盘快捷键速度或只按双指触控速度定耐心数值，另一端极易出现“数值过松”或“物理上按不过来”的断层。

---

## 三、主要参考来源

1. **Shawarma Legend**：
   - Steam 官方商店页：https://store.steampowered.com/app/3036080/Shawarma_Legend/
   - Steam 社区指南《游戏系统介绍和科技树具体介绍》：https://steamcommunity.com/sharedfiles/filedetails/?id=3341305528&l=schinese
   - Steam 社区指南《Shawarma Legend 店铺升级选项一览》 / Upgrades System：https://steamcommunity.com/sharedfiles/filedetails/?id=3336854589
   - Shawarma Legend Upgrades Guide & Costs：https://grindnstrat.com/shawarma-legend-upgrades/
   - Cheatbook 机制整理（Beggar/Thief/Upgrades）：https://www.cheatbook.de/files/shawarmalegend.htm
   - BaiduWiki 机制与道具表：https://baike.baidu.com/en/item/Shawarma%20Legend/1480415
2. **Cook, Serve, Delicious! 1/2/3**：
   - David Galindo 官方开发日志（Order Tickets & 烹饪/防糊时间分离）：https://chubigans.tumblr.com/post/139122771199/cook-serve-delicious-2-preview-order-tickets
   - David Galindo 官方开发日志（Holding Stations）：https://chubigans.tumblr.com/post/139981408924/cook-serve-delicious-2-preview-holding
   - Vertigo Gaming 官方博客（Boosters & Detractors）：https://www.vertigogaming.net/blog/?p=1646
   - David Galindo 专栏（键盘/鼠标/触控/手柄交互对比）：https://www.gamedeveloper.com/design/the-speed-of-a-keyboard-in-controller-form
   - David Galindo 专栏（UI 与难度演进）：https://www.gamedeveloper.com/design/deep-dive-cook-serve-forever-and-difficulty-levels
   - TouchArcade 对 David Galindo 访谈（移动端小屏复杂度权衡）：https://toucharcade.com/2023/05/15/cook-serve-forever-steam-deck-early-access-interview-mobile-ports-vertigo-gaming/
   - CSD2 / CSD3 Steam 官方更新日志（Prep Station 菜单点数抵扣与平衡调整）：https://store.steampowered.com/news/posts/?appids=386620&enddate=1540320908&feed=steam_community_announcements 、https://store.steampowered.com/news/posts/?appids=1000030&enddate=1588272816&feed=steam_community_announcements
   - CSD Wiki（Buzz 耐心公式 / Chores / Rush Hour）：https://cookservedelicious.fandom.com/wiki/How_to_play_guide_for_Cook,_Serve,_Delicious
   - PC Gamer CSD3 评测（餐车分段与 Auto-Serve）：https://www.pcgamer.com/cook-serve-delicious-3-review/
3. **Papa's ...eria（Flipline Studios）**：
   - Flipline Studios 官方 FAQ（Papa's Pancakeria 工位、评分、Closer/Food Critic、小票管理）：https://i.flipline.com/games/papaspancakeria/faq.html
   - Flipline Studios 官方开发日志（Build Station To Go 拇指区改造）：https://www.flipline.com/blog/archives/3559
   - Flipline Studios 官方开发日志（Top Station To Go 防手指遮挡与 Pourables/Placeables 分离）：https://www.flipline.com/blog/archives/3592
   - Flipline Studios 官方 Apps 说明（To Go vs HD 分版本适配）：https://www.flipline.com/apps.html
   - Flipline Studios Wiki（Papa's Burgeria To Go 多点触控）：https://fliplinestudios.fandom.com/wiki/Papa%27s_Burgeria_To_Go!
4. **东方夜雀食堂（Touhou Mystia's Izakaya）**：
   - Touhou Mystia's Izakaya Wiki — Kitchenwares：https://touhou-mystias-izakaya.fandom.com/wiki/Kitchenwares
   - Touhou Mystia's Izakaya Wiki — Tags（标签覆盖优先级与黑暗物质规则）：https://touhou-mystias-izakaya.fandom.com/wiki/Tags
   - Touhou Mystia's Izakaya Wiki — Customers（普客/稀客评分公式、预算与专属反应）：https://touhou-mystias-izakaya.fandom.com/wiki/Customers
   - Touhou Mystia's Izakaya Wiki — Status Effects（雀歌音游 Buff、Hyper 与符卡）：https://touhou-mystias-izakaya.fandom.com/wiki/Status_Effects
   - Steam 社区基础机制指南（昼夜循环与营业时钟）：https://steamcommunity.com/sharedfiles/filedetails/?id=2730526153
5. **Good Pizza, Great Pizza**：
   - GDC Vault 演讲记录（Anthony Lai, TapBlaze）：https://www.gdcvault.com/play/1025561/-Good-Pizza-Great-Pizza
   - GamesBeat 2024 对 Anthony Lai & Yuni Cho 访谈：https://venturebeat.com/games/how-tapblazes-good-pizza-great-pizza-reached-300m-downloads/
   - GPGP Wiki — List of Orders（谜语点单与“What?”惩罚）：https://good-pizza-great-pizza.fandom.com/wiki/List_of_orders
   - GPGP Wiki — ZaZoom App（定时外卖并发与保温箱）：https://good-pizza-great-pizza.fandom.com/wiki/ZaZoom_app
   - GPGP Wiki — Upgrades（Auto Buddy 与升级项）：https://good-pizza-great-pizza.fandom.com/wiki/Upgrades
   - NamuWiki — GPGP Shop（营业时间与烤炉耗时）：https://en.namu.wiki/w/%EC%A2%8B%EC%9D%80%20%ED%94%BC%EC%9E%90%2C%20%EC%9C%84%EB%8C%80%ED%95%9C%20%ED%94%BC%EC%9E%90/%EC%83%81%EC%A0%90
6. **Overcooked（Ghost Town Games）**：
   - Phil Duncan（设计总监）Game Developer 深度复盘：https://www.gamedeveloper.com/design/game-design-deep-dive-building-truly-cooperative-play-in-i-overcooked-i-
   - MCV/DEVELOP 事后复盘（Phil Duncan & Oli De-Vine 访谈）：https://mcvuk.com/development-news/the-develop-post-mortem-overcooked/
   - GodisaGeek 访谈（单人双厨切人与加长计时器设计）：https://godisageek.com/2016/08/overcooked-interview-phil-duncan/
   - Superjump 机制分析（脏盘子非预期回流）：https://www.superjumpmagazine.com/overcooked-how-design-creates-teamwork/
