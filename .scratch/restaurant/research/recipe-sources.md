# 开源菜谱数据源与结构化工序抽取可行性调研

> 调研日期：2026-11-20（一手仓库快照基准见各节标注）
> 关联议题：Ticket 02（为 05 通用烹饪模型、06 菜谱清单与抽取管线提供事实依据）
> 立场声明：本文仅汇报一手查证事实、实测抽样数据与方案权衡，不做 Eidolon-SC 最终设计拍板。

---

## 一、`Anduin2017/HowToCook` 一手拆解

### 1.1 仓库元数据与许可协议

- **仓库地址**：<https://github.com/Anduin2017/HowToCook>
- **查证快照**：`master` 分支 commit `58c1b9af7900a9489c340bca39ef94a9a62314b1`（2026-11-17 推送），Stars `104,155`、Forks `11,238`（来源：<https://api.github.com/repos/Anduin2017/HowToCook>）。
- **许可协议**：**The Unlicense**（SPDX: `Unlicense`），公有领域奉献声明（来源：<https://raw.githubusercontent.com/Anduin2017/HowToCook/master/LICENSE>）。允许任何人以任何方式、用于商业或非商业目的自由复制、修改、发布、分发，无署名强制要求与传染性（ShareAlike）限制。
- **版权清洗注意点**：仓库内少量社区贡献菜谱在「附加内容」中引用了外部商业菜谱站（例如 `糖醋里脊.md` 附带了下厨房与百度百科参考链接）。虽然贡献者以 The Unlicense 提交了改写后的 Markdown，但在实际项目中若仅抽取**原料、工序结构与风味参数**并重新编写游戏内描述，法律风险最低；直接照搬原文长段文字需逐条复核是否夹带第三方出处。

### 1.2 顶层目录结构与 `dishes/` 分类统计

通过 GitHub Git Trees API 递归遍历 `master`（共 984 个条目，`truncated: false`），顶层结构包含：`dishes/`、`tips/`（含 `tips/learn/` 基础技法 12 篇与 `tips/advanced/` 进阶技巧 4 篇）、`.github/`（含 CI 校验脚本 `manual_lint.js` 与目录生成脚本 `readme-generate.js`）、`LICENSE`、`README.md`、`package.json` 等。

`dishes/` 下共 **10 个正式品类目录 + 1 个模板目录**，合计 **374 道正式菜谱 Markdown 文件**（含模板为 375 个）：

| 目录名 | README 中文分类名 | `.md` 数量 | 代表菜谱示例 |
| :--- | :--- | :---: | :--- |
| `meat_dish` | 荤菜 | 111 | 宫保鸡丁、简易/南派/湖南/徽派红烧肉、麻婆豆腐、可乐鸡翅、糖醋里脊、回锅肉、烤鸡翅、粉蒸肉 |
| `vegetable_dish` | 素菜 | 65 | 西红柿炒鸡蛋、酸辣土豆丝、凉拌黄瓜、地三鲜、手撕包菜、干锅花菜 |
| `staple` | 主食 | 59 | 蛋炒饭、日式咖喱饭、蛋包饭、日式肥牛丼饭、照烧鸡腿饭、电饭煲三文鱼炊饭、蒸卤面 |
| `aquatic` | 水产 | 28 | 清蒸鲈鱼、油焖大虾、清蒸生蚝、咖喱炒蟹、水煮鱼 |
| `breakfast` | 早餐 | 25 | 温泉蛋、蒸水蛋、微波炉荷包蛋、煎饺、韩国麻药鸡蛋 |
| `soup` | 汤与粥 | 24 | 紫菜蛋花汤、番茄牛肉蛋花汤、玉米排骨汤、黄瓜皮蛋汤 |
| `drink` | 饮料 | 23 | 酸梅汤、杨枝甘露、奶茶、柠檬水、泰国手标红茶 |
| `dessert` | 甜品 | 19 | 烤蛋挞、炸鲜奶、烤箱版巴斯克芝士蛋糕、提拉米苏 |
| `condiment` | 酱料和其它材料 | 10 | 糖醋汁、油泼辣子、简易版炒糖色、葱油、蒜香酱油 |
| `semi-finished` | 半成品加工 | 10 | 空气炸锅鸡翅中、炸薯条、半成品意面 |
| `template` | （模板，非正式菜谱） | 1 | `dishes/template/示例菜/示例菜.md` |
| **合计（不含模板）** | — | **374** | — |

> 注：中文分类映射见 `.github/readme-generate.js`（<https://raw.githubusercontent.com/Anduin2017/HowToCook/master/.github/readme-generate.js>）。
> 另查：仓库中已存在少量日料/洋食菜谱（如 `日式咖喱饭`、`日式肥牛丼饭`、`蛋包饭`、`照烧鸡腿饭`、`空气炸锅照烧鸡饭`、`电饭煲三文鱼炊饭`、`温泉蛋`、`牛排`、`奶酪培根通心粉`、`意式肉酱面`），但**不包含**长崎地方菜（如强棒面、皿乌冬、长崎天妇罗、柠檬牛排、虾多士等）。

### 1.3 难度星级体系（`starsystem/` 现状变更）与标准 Markdown 模板

1. **`starsystem/` 目录已于 2026 年 5 月移除**：
   - 一手查证显示，`master` 根目录下**已不存在 `starsystem/` 目录**。
   - 根据提交记录 `b7c4dabf470356c0a9b39916cee5195c687ed8e5`（2026-05-11，作者 Anduin Xue，提交信息 `delete: remove 1 to 5 star difficulty category files and associated dish links`，<https://github.com/Anduin2017/HowToCook/commit/b7c4dabf470356c0a9b39916cee5195c687ed8e5>），原独立星级索引文件已被删除。
   - **星级元数据本身完整保留在每道菜谱正文中**，并由 CI 脚本 `.github/manual_lint.js` 强校验。

2. **标准 Markdown 模板与 CI 强约束**（来源：`dishes/template/示例菜/示例菜.md` <https://raw.githubusercontent.com/Anduin2017/HowToCook/master/dishes/template/%E7%A4%BA%E4%BE%8B%E8%8F%9C/%E7%A4%BA%E4%BE%8B%E8%8F%9C.md> 与 `.github/manual_lint.js` <https://raw.githubusercontent.com/Anduin2017/HowToCook/master/.github/manual_lint.js>）：
   - **主标题**：必须严格为 `# <文件名>的做法`，且文件名不含空格。
   - **元信息区（H1 与首个 H2 之间）**：
     - 菜品简介：CI 校验字数 30–300 字。
     - 难度评级：强制匹配正则 `/^预估烹饪难度：\s*★{1,5}\s*$/`（1–5 颗实心星）。模板中对 1–5 星的定义如下：
       - **1 星**：无困难步骤，简单混合烹饪，约 5 分钟；
       - **2 星**：步骤非常简单，不太需要经验，约 10 分钟；
       - **3 星**：步骤不算太复杂，需掌握一定火候/时间/组合技巧，约 15 分钟；
       - **4 星**：包含较多复杂步骤，需精妙掌握火候与组合，40 分钟以内；
       - **5 星**：步骤复杂且易失误，可能需 40 分钟以上。
     - 热量估算：强制匹配正则 `/^预估卡路里：\s*\d+\s*大卡$/`。
   - **强制四段式二级标题**（数量与顺序由 `manual_lint.js` 硬编码校验）：
     1. `## 必备原料和工具`：列出必需原料（模板注释特别要求**省略**燃气灶、饮用水、锅、食用油、碗盘、筷子、炒勺、菜刀等基础厨房用品，仅列特殊器具如烤箱、电饭煲）。
     2. `## 计算`：给出一份用量或按份数缩放的公式（规范建议用 g / ml，避免「适量」「少许」）。
     3. `## 操作`：CI 校验必须使用有序列表（允许下方嵌套 `###` 阶段子标题），按时间顺序列出操作步骤。
     4. `## 附加内容`：注意事项、变体做法、参考资料。

### 1.4 20 道跨品类经典家常菜一手抽样统计

以下 20 道菜均直接读取自 `Anduin2017/HowToCook`（`master` `58c1b9af`）原始 Markdown 文件，覆盖素菜（4）、荤菜（8）、水产（2）、主食含日料/洋食（4）、汤与粥（2）：

| # | 菜名与源码路径 | 品类 | 星级 | 实际主/辅原料 | 实际备料动作 | 厨具与核心技法 | 实际调味料 |
| :-: | :--- | :---: | :-: | :--- | :--- | :--- | :--- |
| 1 | [西红柿炒鸡蛋](https://github.com/Anduin2017/HowToCook/blob/master/dishes/vegetable_dish/%E8%A5%BF%E7%BA%A2%E6%9F%BF%E7%82%92%E9%B8%A1%E8%9B%8B.md) | 素菜 | ★★ | 西红柿、鸡蛋、葱花(可选) | 洗、烫皮去皮(可选)、去蒂切块、打散蛋液 | 炒锅：先滑炒蛋盛出 → 炒西红柿 → 合炒 | 食用油、盐、糖(可选)、醋(可选)、番茄酱(可选) |
| 2 | [酸辣土豆丝](https://github.com/Anduin2017/HowToCook/blob/master/dishes/vegetable_dish/%E9%85%B8%E8%BE%A3%E5%9C%9F%E8%B1%86%E4%B8%9D.md) | 素菜 | ★★ | 土豆、青椒、红椒、干辣椒、大蒜、葱 | 去皮、切丝、清水洗淀粉、焯水10秒沥干、拍蒜切末、配菜切丝段 | 煮锅焯水 + 炒锅爆香快炒 | 食用油、生抽、陈醋、盐 |
| 3 | [凉拌黄瓜](https://github.com/Anduin2017/HowToCook/blob/master/dishes/vegetable_dish/%E5%87%89%E6%8B%8C%E9%BB%84%E7%93%9C.md) | 素菜 | ★ | 黄瓜、蒜 | 刀拍扁剁碎块、拍蒜切末、加糖静置腌制15分钟 | 拌碗：无火冷拌 | 醋、酱油、盐、香油、蚝油、白糖(仅步骤出现) |
| 4 | [地三鲜](https://github.com/Anduin2017/HowToCook/blob/master/dishes/vegetable_dish/%E5%9C%B0%E4%B8%89%E9%B2%9C/%E5%9C%B0%E4%B8%89%E9%B2%9C.md) | 素菜 | ★★★ | 茄子、土豆、尖椒、葱、姜、蒜 | 洗净、土豆去皮切块、茄子切块、手撕尖椒控干、切葱姜蒜、调碗汁 | 油锅宽油分批炸(土豆→茄子→尖椒) → 炒锅炒红油勾芡裹汁 | 食用油、豆瓣酱、生抽、糖、淀粉 |
| 5 | [宫保鸡丁](https://github.com/Anduin2017/HowToCook/blob/master/dishes/meat_dish/%E5%AE%AB%E4%BF%9D%E9%B8%A1%E4%B8%81/%E5%AE%AB%E4%BF%9D%E9%B8%A1%E4%B8%81.md) | 荤菜 | ★★★★ | 鸡腿/鸡胸肉、大葱、干辣椒/二荆条、花生、姜、莴笋(可选) | 去骨拍松切丁、泡水控干、泡葱姜水、上浆腌制1小时、切段、焙/炒花生、调水淀粉 | 炒锅焙干辣椒花椒 → 煎炒鸡丁 → 盖盖小焖2分钟 → 大火翻炒勾芡(+可选微波炉焙花生) | 植物油、盐、生抽、老抽、料酒、淀粉、香醋、白糖、花椒、鸡精、芝麻油、豆瓣酱/油泼辣子(进阶) |
| 6 | [简易红烧肉](https://github.com/Anduin2017/HowToCook/blob/master/dishes/meat_dish/%E7%BA%A2%E7%83%A7%E8%82%89/%E7%AE%80%E6%98%93%E7%BA%A2%E7%83%A7%E8%82%89.md) | 荤菜 | ★★★ | 猪五花肉、姜、大葱、鹌鹑蛋/鸡蛋(可选)、豆皮(可选) | 切大块、姜切片、煮蛋扎孔、烧开水、冷水焯水15分钟 | 煮锅焯水 → 炒锅干煸出油 → 炒糖色 → 加开水炖煮80分钟 → 大火收汁 | 冰糖、生抽、老抽、料酒、八角、香叶、盐 |
| 7 | [麻婆豆腐](https://github.com/Anduin2017/HowToCook/blob/master/dishes/meat_dish/%E9%BA%BB%E5%A9%86%E8%B1%86%E8%85%90/%E9%BA%BB%E5%A9%86%E8%B1%86%E8%85%90.md) | 荤菜 | ★★★ | 内脂豆腐、咸鸭蛋(仅蛋白，非传统魔改)、五花肉/肉糜、蒜、姜、小米椒 | 切蒜姜辣椒、剁肉糜并腌拌、咸鸭蛋去黄捣蛋白、盒内划豆腐块 | 炒锅爆香 → 炒肉糜 → 加开水炖煮10分钟收汁(无焯水与勾芡) | 食用油、蒜蓉辣酱、花椒、盐、酱油 |
| 8 | [可乐鸡翅](https://github.com/Anduin2017/HowToCook/blob/master/dishes/meat_dish/%E5%8F%AF%E4%B9%90%E9%B8%A1%E7%BF%85.md) | 荤菜 | ★★★ | 鸡翅中、可乐、姜、小葱 | 冷水焯水2分钟撇沫、两面改刀划口、生抽腌10分钟、葱挽结 | 煮锅焯水 → 炒锅两面煎金黄 → 倒可乐煮沸撇沫 → 中火焖煮收汁挂丝 | 食用油、料酒/啤酒、生抽、老抽、白糖、盐 |
| 9 | [糖醋里脊](https://github.com/Anduin2017/HowToCook/blob/master/dishes/meat_dish/%E7%B3%96%E9%86%8B%E9%87%8C%E8%84%8A.md) | 荤菜 | ★★★★ | 猪里脊肉、鸡蛋 | 切片拍松切条、加蛋与调料腌20分钟、调糖醋汁、裹干淀粉 | 油锅160℃初炸 → 200℃复炸40秒 → 另起炒锅煮汁冒泡裹酱翻炒 | 食用油、淀粉、料酒、生抽、蚝油、盐、白胡椒粉、番茄酱、醋、白糖 |
| 10 | [回锅肉](https://github.com/Anduin2017/HowToCook/blob/master/dishes/meat_dish/%E5%9B%9E%E9%94%85%E8%82%89/%E5%9B%9E%E9%94%85%E8%82%89.md) | 荤菜 | ★★★★ | 五花肉(二刀肉)、小葱、姜、青红椒、蒜苗 | 热锅炙皮刷洗、冷水加葱姜料酒白煮15分钟、过冷水擦干切2mm薄片、切配菜、预混酱料 | 煮锅白煮 → 炒锅滑油煸炒至起灯盏窝 → 加酱与配菜快炒 | 食用油、料酒、豆瓣酱、生抽、味精 |
| 11 | [烤鸡翅](https://github.com/Anduin2017/HowToCook/blob/master/dishes/meat_dish/%E7%83%A4%E9%B8%A1%E7%BF%85.md) | 荤菜 | ★★★ | 鸡翅中 | 调料抓匀腌制30–40分钟 | 烤箱：预热200℃，烤15–20分钟 → 翻面再烤15–20分钟 | 盐、黑胡椒粉、酱油、料酒(可选蜂蜜/五香粉) |
| 12 | [粉蒸肉](https://github.com/Anduin2017/HowToCook/blob/master/dishes/meat_dish/%E7%B2%89%E8%92%B8%E8%82%89.md) | 荤菜 | ★★★★ | 五花肉、蒸肉米粉、土豆(或南瓜)、姜、蒜 | 洗净切片、切姜蒜末、腌制30分钟、裹蒸肉米粉、土豆去皮切片垫碗底压实 | 蒸锅：水开后中火蒸60分钟 | 生抽、老抽、料酒、郫县豆瓣酱(可选)、白砂糖 |
| 13 | [清蒸鲈鱼](https://github.com/Anduin2017/HowToCook/blob/master/dishes/aquatic/%E6%B8%85%E8%92%B8%E9%B2%88%E9%B1%BC/%E6%B8%85%E8%92%B8%E9%B2%88%E9%B1%BC.md) | 水产 | ★★★ | 鲈鱼、香葱、姜 | 切葱姜丝段(葱丝泡水)、洗净擦干鱼身、改刀划口、盐抹腌10分钟、塞葱姜架筷摆盘 | 蒸锅大火清蒸10分钟 → 换盘去旧姜葱浇豉油 → 炒锅烧热油泼淋 | 食用油、蒸鱼豉油、料酒、盐 |
| 14 | [油焖大虾](https://github.com/Anduin2017/HowToCook/blob/master/dishes/aquatic/%E6%B2%B9%E7%84%96%E5%A4%A7%E8%99%BE/%E6%B2%B9%E7%84%96%E5%A4%A7%E8%99%BE.md) | 水产 | ★★★★ | 黑虎虾/明虾、葱、姜 | 剪虾枪须爪、挑沙包、开背挑虾线、洗净、切姜米 | 炒锅炸葱花椒料油 → 煎虾变色按虾头出油 → 加水盖盖小火焖 → 过滤收浓浇汁 | 植物油、花椒(必备栏漏列)、黄酒/料酒、盐、冰糖 |
| 15 | [蛋炒饭](https://github.com/Anduin2017/HowToCook/blob/master/dishes/staple/%E8%9B%8B%E7%82%92%E9%A5%AD.md) | 主食 | ★★★ | 冷米饭、鸡蛋、火腿、黄瓜(可选)、胡萝卜(可选)、香葱 | 铲松冷饭、配菜切片/丁、蛋白蛋黄分离分别打散 | 炒锅分步炒蛋白与蛋黄 → 炒配菜 → 大火合炒米饭捣散至跳粒 | 食用油、盐、胡椒粉、生抽 |
| 16 | [电饭煲三文鱼炊饭](https://github.com/Anduin2017/HowToCook/blob/master/dishes/staple/%E7%94%B5%E9%A5%AD%E7%85%B2%E4%B8%89%E6%96%87%E9%B1%BC%E7%82%8A%E9%A5%AD/%E7%94%B5%E9%A5%AD%E7%85%B2%E4%B8%89%E6%96%87%E9%B1%BC%E7%82%8A%E9%A5%AD.md) | 主食(日) | ★★ | 大米、三文鱼、有盐黄油(牛油)、玉米/金菇/冬菇(可选) | 三文鱼去鳞去骨、菌菇切碎、淘米三次 | 电饭煲：煲饭模式焖煮30–45分钟 | 有盐黄油 |
| 17 | [紫菜蛋花汤](https://github.com/Anduin2017/HowToCook/blob/master/dishes/soup/%E7%B4%AB%E8%8F%9C%E8%9B%8B%E8%8A%B1%E6%B1%A4.md) | 汤与粥 | ★★ | 干紫菜、鸡蛋、葱花、虾仁/虾皮(可选) | 干紫菜清水泡发15分钟沥干、鸡蛋打散 | 煮锅/汤锅：水开煮紫菜3分钟 → 淋蛋液成蛋花 → 撒葱花 | 食用油、盐、香油 |
| 18 | [番茄牛肉蛋花汤](https://github.com/Anduin2017/HowToCook/blob/master/dishes/soup/%E7%95%AA%E8%8C%84%E7%89%9B%E8%82%89%E8%9B%8B%E8%8A%B1%E6%B1%A4.md) | 汤与粥 | ★★★ | 牛肉、番茄、鸡蛋、葱、姜、蒜 | 牛肉切薄片、番茄切块、切葱姜蒜、牛肉腌制15–20分钟、打散蛋液 | 煮锅/汤锅：水开煮牛肉变色 → 煮番茄软烂 → 淋蛋液成蛋花 | 盐、胡椒粉 |
| 19 | [日式咖喱饭](https://github.com/Anduin2017/HowToCook/blob/master/dishes/staple/%E6%97%A5%E5%BC%8F%E5%92%96%E5%96%B1%E9%A5%AD/%E6%97%A5%E5%BC%8F%E5%92%96%E5%96%B1%E9%A5%AD.md) | 主食(日) | ★★★★ | 咖喱块、土豆、胡萝卜、洋葱、肉(猪/鸡/牛)、蒜、米饭 | 去皮切块/滚刀块、切洋葱月牙、肉切块、拍蒜切碎、切碎咖喱块 | 炒锅/炖锅依次翻炒肉菜 → 加水煮15分钟 → 关火融化咖喱 → 开火搅拌10分钟熬稠(+电饭煲蒸饭) | 食用油、日式咖喱块 |
| 20 | [蛋包饭](https://github.com/Anduin2017/HowToCook/blob/master/dishes/staple/%E8%9B%8B%E5%8C%85%E9%A5%AD.md) | 主食(洋) | ★★★ | 鸡蛋、米饭、洋葱、胡萝卜、玉米粒、青豆(可选)、火腿/鸡胸、牛奶(可选) | 蔬菜与肉切小丁、鸡蛋加牛奶打散 | 炒锅炒茄汁炒饭盛出 → 小火摊煎半熟蛋皮 → 放入炒饭折叠包裹 | 食用油、番茄酱 |

#### 抽样分布汇总（N = 20）

- **星级分布**：1 星 1 道（5%）、2 星 4 道（20%）、3 星 9 道（45%）、4 星 6 道（30%）、5 星 0 道（抽样聚焦常规家常菜）。
- **核心原料复用度**：共出现约 28 种独立主/辅原料（不含纯调味及葱姜蒜），头部高频复用原料明显——鸡蛋（6 道）、五花肉/猪肉（5 道）、土豆（3 道）、番茄（2 道）、鸡翅（2 道）、洋葱/胡萝卜（各 2–3 道）、米饭/大米（3 道）、青红椒/尖椒（3 道）。
- **备料动作频次**：切配改刀（19/20，95%，含切块/切丝/切片/切丁/拍碎/划口）、清洗/泡发/控水（11/20，55%）、精细预处理如去皮/去骨/开背挑虾线/分蛋（10/20，50%）、腌制/上浆（9/20，45%）、打散/搅拌（6/20，30%）、焯水/白煮前置（4/20，20%）、调碗汁/水淀粉（4/20，20%）、裹粉/挂糊（2/20，10%）。
- **厨具与技法频次**（一道菜可跨多工位）：炒锅/平底锅（14/20，含炒/煎/煸/焖烧/泼油）、煮锅/汤锅（8/20，含焯水/白煮/煮汤/炖煮）、油炸（2/20）、蒸锅（2/20）、烤箱（1/20）、电饭煲（主厨具 1 + 配套煮饭 1）、冷拌无火（1/20）。
- **调味料频次**：盐（16/20）、葱姜蒜芳香底料（15/20）、食用油（15/20）、生抽/酱油/豉油（13/20）、糖/冰糖（9/20）、料酒/黄酒（8/20）、辣麻系[豆瓣酱/干辣椒/花椒/小米椒]（6/20）、醋（4/20）、老抽（4/20）、胡椒粉（4/20）、淀粉（3/20）、香油/芝麻油（3/20）、番茄酱（2/20）、蚝油（2/20）、专有单菜风味料（八角香叶/可乐/咖喱块/黄油/蒸肉米粉各 1 道）。

#### 一手检出的 HowToCook 数据质量隐患（对自动化抽取的直接影响）

1. **非经典/魔改做法混入**：例如 `麻婆豆腐.md` 用「留夫鸭咸鸭蛋蛋白」替代传统郫县豆瓣酱，且省略豆腐焯水与勾芡；直接抽入游戏会与玩家常识冲突。
2. **章节内部不一致**：`凉拌黄瓜.md` 的 `必备原料和工具` 漏列盐、香油、蚝油与白糖（白糖仅在操作第 4 步出现）；`油焖大虾.md` 原料栏漏列花椒，且原料写「料酒」、步骤写「黄酒」。
3. **同菜多文件与单文件多版本并存**：红烧肉在仓内拆分为 4 个独立文件（`简易红烧肉`、`南派红烧肉`、`湖南家常红烧肉`、`徽派红烧肉`）；`宫保鸡丁`、`回锅肉`、`西红柿炒鸡蛋` 在单文件内并列「简易版本」与「进阶版本」，若脚本机械按行解析会把两个互斥版本拼成一条线性步骤。
4. **计量异常与地域方言混杂**：`简易红烧肉.md` 一份（2–3 人）写 `猪五花肉：约 3~4 斤`；`电饭煲三文鱼炊饭.md` 使用粤语词表（牛油、粟米、金菇、調較至煲飯模式）。
5. **隐含厨具省略**：模板明确禁止在原料栏写锅、灶、油、刀，导致仅解析 `必备原料和工具` 无法还原所需厨具，必须结合 `操作` 文本与人工标注。

---

## 二、衍生项目与同类开源菜谱数据源核查

### 2.1 `HowToCook` 结构化衍生项目

| 项目 | 仓库/地址 | 许可协议 | 数据规模与结构 | 一手实测规整度与适用性 |
| :--- | :--- | :--- | :--- | :--- |
| **HowToCook-mcp** (`worryzyy`) | <https://github.com/worryzyy/HowToCook-mcp> | `package.json` 声明 `ISC`（仓根无 `LICENSE` 文件） | 内置 `all_recipes.json`（~1.21 MB），TypeScript 定义 `Recipe` 含 `ingredients[]`、`steps[]`、`difficulty`、`category` | **自动解析瑕疵明显**：实测 `all_recipes.json` 将 `必备原料` 与 `计算` 同时解析进 `ingredients[]`，导致同种食材重复出现两次且 `quantity`/`unit` 大量落空为 `null`（`notes: "量未指定"`）；`steps[]` 仍为纯文本句，未结构化拆出备料动作与厨具。 |
| **厨房计划 (Proj. Kitchen)** (`chenranj`) | <https://github.com/chenranj/proj.kitchen> / <https://proj.kitchen> | **MIT License**（仓根 `LICENSE` 明确授权） | 341 道中文菜谱 JSON + 静态 API（`recipes.json`、`all-recipes.json`、`units.json`），字段含 `id`、`name`、`category`、`difficulty`、`tools[]`、`ingredients[{name,amount}]`、`steps[]`、`tips` | **分层质量差异显著**：前 5 道 ASCII slug 菜谱（如 `fanqiechaodan`、`mapodoufu` 豆瓣酱版、`gongbaojiding`）为人工重写，结构干净且修正了 HowToCook 麻婆豆腐的咸鸭蛋问题；其余约 336 道中文文件名菜谱由 HowToCook 自动导入，实测 `回锅肉.json` 仍出现切分错位（`"name": "五花肉的用量为"`）及把普通版与简易版混拼进同一 `steps[]` 的缺陷。 |
| **HowToCook_json** (`DingJunyao`) | <https://github.com/DingJunyao/HowToCook_json> | **无 `LICENSE` 文件**（404） | Python + LLM 解析 HowToCook 为 JSON 并尝试匹配 USDA 营养数据 | 作者在 README 中明确自述「AI 解析效果并不理想，之后还需要手工修正」「USDA 匹配成功率极低」；加之无明确 LICENSE，仅作参考。 |
| **Vibe Cook** (`zkeq`) | <https://github.com/zkeq/vibe-cook> | **BSL 1.1**（非开源协议，2030-08-19 前禁止生产/商用） | 基于 HowToCook 的交互式步骤应用 | 虽然列于 HowToCook README 衍生推荐中，但协议为 Business Source License 1.1，**不可直接复用其代码或二次加工数据于生产项目**。 |

### 2.2 其他合规开源菜谱数据源（中餐 / 日料 / 洋食 / 长崎乡土料理）

| 数据源 | 地址 | 许可协议 | 语言与规模 | 优缺点与长崎/日料覆盖情况 |
| :--- | :--- | :--- | :--- | :--- |
| **日本农林水产省「うちの郷土料理」**（Our Regional Cuisines） | 总览：<https://www.maff.go.jp/j/keikaku/syokubunka/k_ryouri/search_menu/><br>长崎县：<https://www.maff.go.jp/j/keikaku/syokubunka/k_ryouri/search_menu/area/nagasaki.html><br>许可条款：<https://www.maff.go.jp/j/use/link.html> | **日本公共数据利用规约 PDL 1.0**（官方明示**兼容 CC BY 4.0**，允许商用、翻译与改编，需注明出处与加工声明；见数字厅原文 <https://www.digital.go.jp/resources/open_data/public_data_license_v1.0>） | 日语，全国 47 都道府县 **1,365 道**；其中**长崎县 30 道**，均含历史背景、标准 2–4 人份材料表与分步做法 | **长崎料理最高权威一手源**。长崎 30 道中直接收录：**ちゃんぽん（强棒面）**、**皿うどん（皿乌冬）**、**長崎天ぷら**、**レモンステーキ（佐世保柠檬牛排）**、**ハトシ（虾多士）**、**ヒカド**、**具雑煮**、**大村寿司**、**長崎ミルクセーキ**、**かんざらし**等。注意：站内部分配图归属第三方，文字数据可按 PDL 1.0 / CC BY 4.0 安全改编，图片须逐张核对标注。 |
| **Wikibooks Cookbook**（含 `gossminn/wikibooks-cookbook` 结构化快照） | <https://en.wikibooks.org/wiki/Cookbook:Table_of_Contents><br>结构化集：<https://huggingface.co/datasets/gossminn/wikibooks-cookbook> | **CC BY-SA 4.0**（允许商用与改编，但**文本衍生品需相同方式共享 ShareAlike**） | 多语种共约 4,620 道（英语 1,405、日语 209、中文 29 等） | 覆盖欧美洋食及部分经典日料（如天妇罗、蛋包饭、咖喱、长崎蛋糕 Castella 等），结构化字段包含食材、器具与步骤。**权衡**：CC BY-SA 4.0 的传染性条款要求直接派生的菜谱文本也以相同协议发布；若仅参考公开烹饪事实（食材配比与传统做法在著作权法中通常不受独创性表达保护）并独立重写游戏数据，则需做好隔离。 |
| **UniTools World Recipes** (`farcrak/unitools-recipes`) | <https://github.com/farcrak/unitools-recipes> | **CC BY-SA 4.0** | 俄语 + 英语，501 道（127 国），带结构化 `prepMinutes` / `cookMinutes`、食材线性/非线性缩放规则（`linear`/`sublinear`/`fixed`）与营养数据 | 数据工程质量极高，适合作为多国洋食/配时参数与食材缩放建模的参考；但同样受 CC BY-SA 4.0 ShareAlike 约束，且无中文。 |
| **Ishotihadus/recipe** | <https://github.com/Ishotihadus/recipe> | **MIT License**（明确声明仅限文本，成品不限） | 日语，仅 9 道（和食 3 道：照烧鸡腿、姜烧鸡、滑子菇味噌汤；洋食 6 道：汉堡排、蛋包饭 3 种、奶油培根意面、焗通心粉） | 许可极宽松、步骤清晰且显式列出「道具」，但总量过小，仅可作为少数日式家常/洋食参考。 |
| **TheMealDB** | <https://www.themealdb.com/>（条款：<https://www.themealdb.com/terms_of_use.php>） | **专有 API 条款**（开发测试用 key `1` 免费；公开上线/商用需 Patreon 付费订阅，且禁止转售或直接抓站） | 英语，结构化 JSON API（含少量中餐与日料） | **非开源许可**，且偏向在线 API 调用，不符合「离线开源自持菜谱库」的零依赖诉求。 |

### 2.3 明确排除的高法律风险 / 爬虫数据集（不可采用）

| 项目/数据集 | 来源地址 | 风险定性 | 一手查证依据 |
| :--- | :--- | :--- | :--- |
| **CookLikeHOC**（像老乡鸡那样做饭） | <https://github.com/Gar-b-age/CookLikeHOC> | **高风险 / 无授权** | 仓库无任何 `LICENSE` 文件（默认保留所有权利）；作者在 Issue #26（<https://github.com/Gar-b-age/CookLikeHOC/issues/26>）明确说明内容人工整理自企业发布的《老乡鸡菜品溯源报告》PDF，原报告并未以任何开放协议授权商用或二次分发。 |
| **XiaChuFang_Recipe_Corpus**（下厨房语料库） | <https://huggingface.co/datasets/xzm1999/XiaChuFang_Recipe_Corpus> | **非法定授权爬虫集** | 收录 152 万+ 条抓取自下厨房（`xiachufang.com`）的 UGC 菜谱，未获得 41 万原作者及平台的商业授权。 |
| **MIRecipe / `bimissing/recipeData`** | <https://github.com/bimissing/recipeData> | **非法定授权爬虫集** | README 明示 `"Our recipe data is crawlered from https://www.haodou.com/recipe"`（好豆网爬虫数据，26,725 道），无商业许可。 |
| **`Sorosliu1029/recipe-crawler`** 等同类爬虫库 | <https://github.com/Sorosliu1029/recipe-crawler> | **非法定授权爬虫集** | 面向商业菜谱站的爬虫工具/抓取数据，存在明确的著作权与反爬条款违约风险。 |

---

## 三、结构化游戏映射可行性分析

将真实 Markdown 菜谱压缩为游戏内有限状态机模型 `ingredients × prep_actions × cookware × seasonings` 时，基于上述 20 道实测菜谱与 2 道 MAFF 长崎菜谱（强棒面、皿乌冬），可识别以下核心瓶颈与词表边界。

### 3.1 信息损失与玩法撞车点（以中式炒菜同质化为核心）

1. **炒菜高度同质化（Stir-fry Homogeneity）**
   - 20 道样本中有 **14 道（70%）** 经过炒锅。若游戏将烹饪抽象为单一「切完 → 全丢进炒锅 → 点盐/酱油 → 等进度条满」，则西红柿炒蛋、酸辣土豆丝、宫保鸡丁、麻婆豆腐、回锅肉、蛋炒饭在玩家手上的操作回路几乎完全一致，只剩下「换贴图选不同原料」的记忆题。
2. **最易丢失的四类现实工序信息**
   - **分步与「盛出再合炒」时序**：西红柿炒蛋（先炒蛋盛出 → 炒番茄 → 合炒）、蛋包饭（炒饭盛出 → 煎蛋皮包裹）、地三鲜（分批炸熟 → 统一勾芡）、糖醋里脊（初炸 → 复炸 → 另锅裹酱）。如果数据 schema 仅支持扁平的 `ingredients[] + cookware`，这些菜谱最具辨识度的多段节奏会被完全抹平。
   - **跨工位预处理链路**：回锅肉（煮锅白煮 → 切片 → 炒锅煸炒）、红烧肉/可乐鸡翅（焯水 → 炒锅煎/炒糖色 → 炖/焖收汁）、清蒸鲈鱼（腌 → 蒸锅 → 炒锅泼热油）、长崎强棒面（煮面 + 炒肉菜 + 冲汤合煮）。单厨具字段无法表达「前置焯/煮 + 主加工 + 收尾」的工位切换。
   - **刀工与形态分化**：切块、切丝、切片、切丁、拍碎、改刀在 20 道菜中出现于 19 道，若压缩为单一 `切`，备料阶段将失去差异化。
   - **隐含基础料与火候阶段**：HowToCook 故意省略水、油、通用锅具，但真实风味区分往往来自「小火爆香/炒糖色」「大火快炒」「小火慢炖」「水淀粉勾芡」「泼热油」等阶段特征。

### 3.2 游戏保持菜谱区分度的常见建模机制与权衡

| 区分度维度 | 建模方式 | 带来的游玩区分 | 代价与复杂度权衡 |
| :--- | :--- | :--- | :--- |
| **1. 工位拓扑链路** | 允许菜谱声明 1–3 个有序阶段（前置备料/预处理 → 主热加工 → 可选收尾/组装），而非绑定单个厨具 | 凉拌菜（0 热加工）、蒸菜（腌+蒸+泼油）、炸菜（腌+裹粉+炸+裹汁）、炒菜（切+快炒）、盖饭/面（主食+浇头组装）自然拉开操作节奏 | 状态机需支持中间产物（如「炒好的蛋」「炸好的里脊」「米饭」）暂存与合并 |
| **2. 备料动作分层** | 在基础「切配」外，保留有明确视觉/手感差异的备料动作（如：切配、打散、腌制、焯水、裹粉） | 鸡蛋打散 vs 切块、里脊裹粉 vs 鸡丁上浆、五花肉焯水 vs 鲜炒，让同类肉菜前置路径不同 | 每多 1 种备料动作，需对应增加食材中间态图标/规则校验 |
| **3. 调味抽象粒度** | 方案 A：**基础单料直选**（隐去油/水/葱姜蒜底味，暴露 10–14 种核心调味）；<br>方案 B：**风味签名/碗汁抽象**（将复合调味打包为 7–10 种风味，如红烧酱香、麻辣豆瓣、糖醋、酸辣蒜蓉、清蒸豉油、日式咖喱、照烧、番茄茄汁） | 方案 A 拟真度与自由试错（黑暗料理）空间更大；方案 B 避免反复机械点「盐+生抽+老抽+料酒」四件套，突出菜系辨识度 | 方案 A 容易产生点瓶疲劳；方案 B 削弱自由组合感，但更适合快节奏或休闲单局 |
| **4. 烹饪微节奏/火候** | 在热加工工位区分火候或收尾节点（快炒翻锅、慢炖控火、复炸二次起锅、勾芡/收汁窗口） | 即使同为炒锅菜，快炒土豆丝、滑炒鸡蛋、慢焖可乐鸡翅、收汁红烧肉的操作体验仍不同 | 增加交互教学与 UI 反馈成本，需与整体游戏节奏（休闲 vs 动作）匹配 |

### 3.3 面向 30–50 道精选菜谱的词表规模估算

基于 20 道实测样本的复用率（28 种核心原料即可覆盖 20 道跨品类菜，其中鸡蛋/猪肉/鸡肉/土豆/番茄/洋葱/胡萝卜/米饭跨菜复用率最高），向 30–50 道菜（以中式家常菜为主，混入约 5–8 道日料/洋食及长崎特色菜如强棒面、皿乌冬、咖喱饭、蛋包饭、照烧鸡、柠檬牛排等）外推，词表存在「紧凑型」与「丰富型」两个实用区间：

| 词表维度 | 紧凑规模（偏向 30 道 / 低 UI 负担） | 丰富规模（偏向 50 道 / 高区分度） | 组成举例（基于实测高频项） |
| :--- | :---: | :---: | :--- |
| **核心主/辅食材**（不含纯调味） | **28–35 种** | **38–48 种** | **肉禽 (5–7)**：五花肉、里脊/瘦肉、鸡肉(胸/腿)、鸡翅、牛肉、火腿/培根；<br>**水产 (3–5)**：鲈鱼/鱼、大虾、三文鱼、鱿鱼/蛤蜊（支撑长崎强棒面/皿乌冬）；<br>**蛋豆主食 (6–8)**：鸡蛋、豆腐、米饭/大米、面条/强棒面、土豆、红薯/粉条、鱼板(かまぼこ)；<br>**蔬菜菌菇 (12–18)**：番茄、黄瓜、青红椒、茄子、洋葱、胡萝卜、包菜/白菜、豆芽、青菜/西兰花、蒜苗、香菇、紫菜/木耳、花生、玉米/青豆 |
| **备料动作** | **4–5 种** | **6–7 种** | 核心 5 项：**切配**、**打散**、**腌制**、**焯水**、**裹粉**；<br>可选扩展：**清洗/泡发**、**调碗汁**（或将洗/泡发并入自动前置） |
| **厨具 / 工位** | **4–5 种** | **6–7 种** | 核心 4 项：**炒锅/平底锅**、**煮/炖锅**、**蒸锅**、**冷拌/装盘台**；<br>扩展项：**油炸锅**、**烤箱**、**电饭煲**（若压缩工位，炸可并入炒锅高油态、电饭煲可并入蒸/煮锅） |
| **调味料 / 风味** | **8–10 种**（风味包抽象） | **12–15 种**（核心单料直选） | 若隐去油、水、基础盐/葱姜蒜底味：生抽/酱油、老抽、醋、糖/冰糖、料酒、豆瓣酱、干辣椒/花椒、番茄酱、蚝油、淀粉(勾芡)、胡椒粉、蒸鱼豉油、咖喱块、照烧汁/可乐/黄油等 |

- **规模边界观察**：
  - **食材超过 50 种**时，单屏备料台检索成本急剧上升，且长尾单菜专用食材（如只做一道菜的鸭蛋、蒸肉米粉、可乐）占比过高，降低复用趣味。
  - **食材低于 25 种**时，50 道菜内极易出现大量「换调味不换料」的换皮菜谱。
  - **自动化抽取与人工策展分工**：鉴于实测 `HowToCook` 原仓及全部衍生 JSON 项目（`HowToCook-mcp`、`proj.kitchen`、`HowToCook_json`）在食材去重、版本拆离、隐含厨具和经典做法一致性上均存在机器解析缺陷，工程上可行的路径通常是**「离线脚本初筛提取候选草稿（原料+步骤+星级） → 人工策展校对并映射到游戏有限词表与阶段模板」**，而非运行时或构建时全自动直出。

---

## 四、主要一手出处索引

1. `Anduin2017/HowToCook` 仓库、LICENSE 与目录树：
   - <https://github.com/Anduin2017/HowToCook>
   - <https://raw.githubusercontent.com/Anduin2017/HowToCook/master/LICENSE>
   - <https://raw.githubusercontent.com/Anduin2017/HowToCook/master/dishes/template/%E7%A4%BA%E4%BE%8B%E8%8F%9C/%E7%A4%BA%E4%BE%8B%E8%8F%9C.md>
   - <https://raw.githubusercontent.com/Anduin2017/HowToCook/master/.github/manual_lint.js>
   - <https://raw.githubusercontent.com/Anduin2017/HowToCook/master/.github/readme-generate.js>
   - `starsystem/` 移除提交：<https://github.com/Anduin2017/HowToCook/commit/b7c4dabf470356c0a9b39916cee5195c687ed8e5>
2. HowToCook 衍生项目：
   - `worryzyy/HowToCook-mcp`：<https://github.com/worryzyy/HowToCook-mcp>（`package.json`、`src/types/index.ts`、`all_recipes.json`）
   - `chenranj/proj.kitchen`：<https://github.com/chenranj/proj.kitchen>、<https://proj.kitchen>（`LICENSE`、`scripts/build-api.ts`、`recipes/*.json`）
   - `DingJunyao/HowToCook_json`：<https://github.com/DingJunyao/HowToCook_json>
   - `zkeq/vibe-cook`（BSL 1.1）：<https://github.com/zkeq/vibe-cook>
3. 合规开源替代与长崎料理一手源：
   - 日本农林水产省「うちの郷土料理」长崎县（30 道）：<https://www.maff.go.jp/j/keikaku/syokubunka/k_ryouri/search_menu/area/nagasaki.html>
   - 农林水产省著作权与 PDL 1.0 说明：<https://www.maff.go.jp/j/use/link.html>
   - 日本数字厅公共数据利用规约（PDL 1.0，兼容 CC BY 4.0）：<https://www.digital.go.jp/resources/open_data/public_data_license_v1.0>
   - 实测长崎代表菜页：ちゃんぽん <https://www.maff.go.jp/j/keikaku/syokubunka/k_ryouri/search_menu/menu/46_8_nagasaki.html>、皿うどん <https://www.maff.go.jp/j/keikaku/syokubunka/k_ryouri/search_menu/menu/46_7_nagasaki.html>
   - Wikibooks Cookbook 与结构化集（CC BY-SA 4.0）：<https://huggingface.co/datasets/gossminn/wikibooks-cookbook>
   - UniTools World Recipes（CC BY-SA 4.0）：<https://github.com/farcrak/unitools-recipes>
   - `Ishotihadus/recipe`（MIT）：<https://github.com/Ishotihadus/recipe>
   - TheMealDB 服务条款：<https://www.themealdb.com/terms_of_use.php>
4. 排除的高风险/爬虫源：
   - `Gar-b-age/CookLikeHOC` 无协议说明：<https://github.com/Gar-b-age/CookLikeHOC/issues/26>
   - `xzm1999/XiaChuFang_Recipe_Corpus`：<https://huggingface.co/datasets/xzm1999/XiaChuFang_Recipe_Corpus>
   - `bimissing/recipeData`（好豆爬虫）：<https://github.com/bimissing/recipeData>
