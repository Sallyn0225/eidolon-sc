# 厨房画风、前端渲染架构与合法免费美术/音频素材调研报告

> 对应调研票：[03-art-and-audio-assets-research.md](../issues/03-art-and-audio-assets-research.md)
> 目标：为后续原型设计（[09](../issues/09-kitchen-screen-prototype.md)）与音频方案拍板（[11](../issues/11-audio-and-feedback.md)）提供来自本仓库一手实现与外部一手协议/文档的事实依据与权衡对比。本报告仅陈述事实、技术边界与许可条款，不替 Eidolon-SC 做出设计决定。

---

## 一、本仓库一手实现审视：Spine、横屏、资源托管与通话共存

### 1.1 Spine 3.6 渲染架构与多立绘并发边界

- **底层技术栈并非 PixiJS，而是官方 `spine-ts` 3.6 WebGL runtime**：
  - 依据 `docs/adr/0009-spine-runtime-without-editor-license.md`、`docs/adr/0031-bar-built-in-this-repo-not-godot.md` 与 `frontend/src/components/conversations/stand/spineRuntime.ts`：项目直接将未改动的 `frontend/public/vendor/spine-3.6/spine-webgl.js`（约 176 KB min / 46 KB gzip）通过 `<script>` 注入 `window.spine`，并在 `LICENSING.md` 中通过 AGPL-3.0 第 7 节附加许可将其与主程序隔离。
  - 排除项原因已由 `.scratch/spine-stand/research/spine-web-runtime.md` 验证：`spine-canvas` 不支持 mesh attachment 与 clipping（原作立绘全量依赖 mesh）；`pixi-spine` 体积大 4–5 倍且 PixiJS v7 已停止维护；`spine-godot` 只读 4.x 数据。
- **现有 `<Stand>` 组件的资源开销模型**：
  - `frontend/src/components/conversations/stand/Stand.tsx` 与 `StandEngine.ts` 显示：**每个挂载的 `<Stand>` 实例都会独占 1 个 `<canvas>`、1 个 `ManagedWebGLRenderingContext`、1 个 `SceneRenderer`、1 个 `AssetManager` 以及 1 个独立的 `requestAnimationFrame` 循环**（通过 `frontend/src/lib/standFrames.ts` 的 `FrameGate` 限帧在 60 FPS、`MAX_PIXEL_RATIO = 2`，支持调用方传入更低的 `maxPixelRatio` 与 `isStill` 静帧档）。
  - **上下文释放细节**：`StandEngine.dispose()` 刻意**不调用 `WEBGL_lose_context`**（因为 React 开发模式 StrictMode 会双跑 effect，同一 `<canvas>` 上重建引擎时丢失上下文会导致黑屏）。因此落地页 `frontend/src/app/(landing)/StandSlot.tsx` 在移动端（`(hover: none)`）卸载时额外用 `setTimeout(..., 0)` 检查 `!canvas.isConnected` 后再显式 `loseContext()` 释放上下文。
- **浏览器 WebGL 上下文硬上限与移动端并发实操边界**：
  - **WebKit（iOS / macOS Safari）一手源码**：`WebKit/Source/WebCore/html/canvas/WebGLRenderingContextBase.cpp` 定义主线程 `maxActiveContexts = 16`、Worker `maxActiveWorkerContexts = 4`（[WebKit 源码](https://github.com/WebKit/WebKit/blob/main/Source/WebCore/html/canvas/WebGLRenderingContextBase.cpp)）。
  - **Chromium（Chrome / Android WebView）**：默认上限在桌面端为 16、Android 移动端为 8（可通过 `switches::kMaxActiveWebGLContexts` 配置，且受显存压力触发 LRU 驱逐旧上下文并派发 `webglcontextlost`，见 [Chromium commit bfea76f](https://chromium.googlesource.com/chromium/src/+/bfea76f48f8af2bd76157cfc0a025b3c81241777%5E%21/) 与 [Chromium Issue 40939743](https://issues.chromium.org/issues/40939743)）。
  - **与活跃通话共存时的隐性占用**：按 `docs/adr/0018-call-belongs-to-the-shell.md` 与 `frontend/src/components/app/NavShell.tsx`、`CallLayer.tsx`（`StandStage`），用户通话中进入玩法页时，外壳中的 `LiveCallLayer` 保持挂载（仅通过 `isPaused={isCollapsed}` 暂停 rAF），**其 `<Stand>` 仍占用 1 个活跃 WebGL 上下文**。
  - **对餐馆同时展示多位角色的实际含义**：
    - **1 个活跃 `<Stand>`**（如酒吧 `BarGuest` 单客、或餐馆仅由 1 个主舞台位渲染恋鐘/当前焦点顾客）：加上通话层最多 2 个上下文，在手机端安全稳定。
    - **3–5 个并发 `<Stand>`**（若直接在 3–5 个客槽位各挂一个 `<Stand>`）：叠加通话层即达 4–6 个活跃 WebGL 上下文，同时加载多套 2048px 级 Spine 贴图并每帧执行多套 60+ mesh 蒙皮变形，在 Android 8 上限设备与中低端机上极易触发显存抖动、发热掉帧或驱逐通话层上下文。
    - **可用技术边界方案**：
      1. 复用现有 `<Stand>` 时，同时保持 0–1 个动态立绘（例如恋鐘站在主厨/柜台位，或单焦点特写），其余多客槽位使用站内已有圆形头像（`frontend/src/components/app/MarkedAvatar.tsx`，源自 `characters/avatars/`）或轻量 2D 气泡卡；
      2. 若未来坚持同屏多具动态 Spine 角色，需将 `StandEngine` 改造为**单 WebGL 上下文 / 单 `<canvas>` 多骨架批渲染**，工程量高于直接复用 `<Stand>`。

### 1.2 VA-283 酒吧实现对照：横屏外壳、音频管线与通话共存

| 维度 | VA-283 现有实现（仓库一手源码） | 对餐馆的直接启示 / 约束 |
|---|---|---|
| **路由与独立视觉世界** | `frontend/src/app/(app)/(nav)/play/bar/page.tsx` 独立路由 + `bar.css`，不打进 `[subpage]` 包；沿用 `docs/adr/0016-landing-page-is-its-own-visual-world.md` 另立视觉，不套主站 shadcn 表单；`frontend/src/lib/navShell.ts` 的 `showsNav()` 在酒吧页隐藏侧边栏与底部 dock。 | 餐馆应同样独立路由（如 `/play/restaurant`），并在 `showsNav()` 中登记，避免重资产污染主应用包体。 |
| **手机横屏与安全区缩放** | `frontend/src/lib/barScreen.ts` + `BarScreen.tsx` + `PortraitGuard.tsx` + `useBarFullscreen.ts`：640×360 逻辑画布，细指针（电脑）取整倍缩放、粗指针（手机）小数倍自适应；通过不可见探针读取 `env(safe-area-inset-*)`，通过 `ResizeObserver` 动态扣减顶部通话条高度；手机竖屏时由 `@media (orientation: portrait) and (pointer: coarse)` 盖上提醒层但不卸载底层画面；Android 提供 `requestFullscreen()` + `screen.orientation.lock("landscape")` 按钮，iOS Safari 不支持两者故隐藏该按钮。 | 这套横屏保护 + 安全区/通话条动态扣减 + 禁止滚动/双指缩放（`touch-action: none`）可直接复用。但若餐馆不采用 640×360 像素硬缩放，而是响应式高分视口布局，文字与触控热区无需走像素二值化 canvas。 |
| **Spine 立绘与背景融合** | `frontend/src/components/play/bar/BarGuest.tsx` 将 `<Stand maxPixelRatio={1} />` 置于逻辑像素框中，再随外层 `.bar-stage` 的 `transform: scale(...)` + `image-rendering: pixelated` 最近邻放大，配合 CSS `steps(4)` 剪影淡入（`.bar-guest-in`）强行「像素化」对齐。 | 该手法适合 640×360 复古致敬酒吧；但在多食材、多按钮的高密度现代厨房 UI 里强行压到 1× 再最近邻放大，会让立绘细线产生明显闪烁锯齿。 |
| **静态资源 vs 公开存储桶** | 依 `docs/adr/0003-corpus-and-voices-stay-private.md`（历次修订）与 `LICENSING.md`：<br>1. **仓库 `frontend/public/`**：许可清晰且体量小的图/短音效（如 `public/sounds/` 通话音效，`next.config.ts` 配 1 天缓存；`public/gifts/` 20 张 512×512 WebP AI 生成礼物图，旁附 `CREDITS.md`）。<br>2. **公开 S3 存储桶（`EIDOLON_STAND_ASSETS_URL`）**：体积大（如几十 MB OST）或涉及第三方版权需「清空前缀即一键下线」的素材（`bar/music/*.ogg`、`bar/sfx/*.ogg`、`bar/manifest.json`，见 `backend/src/eidolon/bar_upload.py`：音频设 `immutable` 缓存，`manifest.json` 设 `no-cache`）。 | 餐馆若全部采用许可清晰的自产/CC0/MIT 素材，小体量图标与关键短 SFX 可直接放 `frontend/public/`（部署零额外上传步骤）；若 BGM 曲目多、体量大，则可沿用存储桶 + `manifest.json` 模式按需加载并支持静音降级。 |
| **CSP 严格域名限制** | `frontend/src/lib/contentSecurityPolicy.ts`：`img-src 'self' data: blob:<stands>`、`media-src 'self' blob:<stands>`、`connect-src 'self'<stands>`、`font-src 'self'`。 | **严禁引用任何第三方外部 CDN**（如 jsDelivr 加载 Twemoji、外链音效 URL 均会被 CSP 拦截）。所有图片、字体、音频必须自托管于 `'self'` 或 `EIDOLON_STAND_ASSETS_URL`。 |
| **音频播放与 Safari 坑点** | `useBarSound.ts` 用 Web Audio `AudioContext` + `decodeAudioData` 缓存 + `AudioBufferSourceNode` 无缝循环（解决 `<audio loop>` 接缝停顿）；`useBarJukebox.ts` 用 `<audio>` 流式播放 BGM。酒吧保留原版 `.ogg`，故 `barAudio.ts` 检测 `canPlayType('audio/ogg; codecs="vorbis"')`，**Safari 18.4 之前无声**；且按 [Apple iOS 官方文档](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/Using_HTML5_Audio_Video/Device-SpecificConsiderations/Device-SpecificConsiderations.html)，iOS 上 `<audio>.volume` 恒为只读 `1`，故 `BarSettingsBox` 在 iPhone 禁用音乐音量滑块。 | 餐馆没有「保留原版未转码 `.ogg`」的包袱：使用 **MP3 或 AAC（`.m4a`）**（或双格式回退）即可全版本兼容 iOS/macOS Safari 与所有桌面/安卓浏览器；若短循环或音量可控要求高，Web Audio `GainNode` 在 iOS 上支持软件音量调节（但长 BGM 解码占内存，需权衡）。 |
| **通话共存与音频冲突** | `NavShell.tsx` 保留顶部 `CallBar` 且不挂断通话；**但实查 `BarSubpage.tsx` 未读取 `useDirectory().call` 状态**，即酒吧目前不会在通话进行中自动静音或闪避（ducking）BGM/SFX，仅依赖用户在设置里手动调小音量。 | 餐馆的炒菜滋啦、倒计时警报与轻快 BGM 比酒吧更喧闹；票 11 需明确在 `call !== null` 时是自动静音、自动降音，还是保持独立由用户手动开关。 |

---

## 二、视觉风格与前端渲染架构权衡

### 2.1 「2D 卡通 / 柔和平涂矢量风」vs「像素风（VA-283 路线）」

| 对比维度 | 2D 卡通 / 柔和平涂矢量风（DOM/SVG + 高分透明 WebP/精灵） | 像素风（低逻辑分辨率 + `image-rendering: pixelated`） |
|---|---|---|
| **与 Spine 3.6 立绘 / 头像同框融合度** | **高**。站内 Spine 立绘为高清晰度二次元厚涂/赛璐璐风格，`MarkedAvatar` 与 `frontend/public/gifts/`（20 张柔和平涂 WebP 礼物插画）均采用柔和圆润、清晰边缘的现代手游风格。2D 平涂厨房与立绘/头像自然衔接，无需破坏立绘清晰度。 | **中等（需刻意妥协）**。如 `BarGuest.tsx` 所示，必须将 `<Stand>` 压到 `maxPixelRatio={1}` 再最近邻放大才能勉强融入像素环境；若混用高清圆形头像会显得画风割裂，若强行降采样则细节易闪烁。 |
| **30–50 道中式家常菜 + 多状态产出与维护成本** | **可控**。在 128–512px 画布下，番茄炒蛋、麻婆豆腐、宫保鸡丁、青椒肉丝、红烧肉等菜品可以通过色块层次、配菜形状与容器差异清晰分辨；可沿用 `frontend/public/gifts/CREDITS.md` 已验证的 AI 生图提示词骨架（透明底 WebP）批量保持风格一致，单菜增补成本低。 | **高**。在 16×16 或 32×32 像素网格内区分几十道颜色相近的中式炒菜（红烧/酱炒/炖菜）极易撞脸糊成色块；AI 直接生成像素图往往网格不齐（mixels），需大量逐像素手工修整（`.scratch/bar-room/spec.md` 中仅修一个 187×63 的「VA-283」像素 logo 就因生成图太糙改回手画）。 |
| **手机横屏小视口信息清晰度（667×375 / 844×390）** | **优**。原生高 DPR（2×/3×）矢量字体与 SVG 图标在任意缩放比下锐利可读，菜谱名、计时数字、客单气泡在小屏下无锯齿模糊；按钮尺寸与间距可直接用 CSS 响应适配触控热区（≥ 44×44 CSS px）。 | **受限**。手机横屏（如 844×390 扣掉安全区与通话条）几乎无法整数倍缩放固定逻辑画布，非整数倍最近邻缩放会导致像素宽度不均；为保文字可读，VA-283 不得不引入约 960 KB 像素字体并在 canvas 上手动二值化绘制每一段文字（`PixelText.tsx`）。 |
| **性能与包体** | 50 张 256×256 质量 82 的透明 WebP 菜品图约 400–800 KB，配合 CSS/SVG 动画几乎零 GPU 负担；浏览器原生硬件合成，无额外像素字 canvas 渲染开销。 | 单张 PNG 像素图极小（VA-283 全套 `public/bar/img/` 仅约 260 KB），但额外像素中文字体（`fusion-pixel-12px-zh_hans.woff2` 约 960 KB）抵消了部分体量优势。 |
| **差异化定位** | 与 VA-283 的暗黑赛博像素夜店形成鲜明对比，贴合「明亮温暖的日常家常餐馆」氛围，并与站内 `gifts` 插画视觉语言一致。 | 若沿用像素风，会与已有 `/play/bar` 高度趋同，但适合偏复古街机/开罗风审美取向。 |

### 2.2 组合式渲染（Compositional Rendering）避免贴图组合爆炸

如果为每道菜的每个状态单独准备静态图，假设 40 道菜 × 5 状态（生/备料/烹饪中/成品/烧糊）× 2–3 种容器/工位 = **400–600 张贴图**，无论外采还是生成都难以维护。采用**三层组合式渲染**可将静态资产规模从 $O(N \times S \times U)$ 压降至 $O(N + I + U)$：

1. **底层 — 通用容器与厨具（约 6–10 张静态 SVG/WebP）**：
   - 厨具工位：案板、炒锅（铁锅）、汤锅/砂锅、蒸笼/电饭煲、出餐托盘（各自仅需空闲态 + 工作态，或通过 CSS/SVG 附加火焰与光效）。
   - 盛具底盘：浅白瓷盘（炒菜）、深汤碗（汤羹/面）、砂锅/焖碗、凉菜小碟（3–4 种通用容器即可覆盖全部中式家常菜）。
2. **中层 — 基础食材与成品菜肴内容物（约 20–30 张核心食材 + 30–50 张成品菜）**：
   - **生料态 / 处理后态**：对基础食材（蛋、番茄、五花肉、豆腐、青椒、土豆等）提供生料图标；「切配处理后」可通过两类低成本方式表现——(a) 少量通用切配形态图（如切块/切丝/肉片通用模板叠加食材主色）或只对高频主材画 1 张切好态；(b) 在原食材图上叠加刀切斜纹/碗盛装角标。
   - **烹饪中态**：在厨具内展示下锅食材堆叠缩略图或半成品混合态，随进度过渡到成品菜图。
   - **成品态**：30–50 道成品菜内容物（透明底 WebP，居中去边）直接叠在对应盛具底盘之上。
3. **顶层 — 程序化状态滤镜与 SVG/CSS 特效（0 张额外菜品贴图）**：
   - **正在烹饪**：SVG 路径动画上升白色蒸汽 + 锅底暖橙火焰/电磁炉高亮 + 环形或条形进度指示。
   - **熟透/最佳出餐窗口**：暖金色柔光呼吸脉冲（CSS `box-shadow` / SVG glow）+ 「完成」小闪星。
   - **即将烧糊 / 已烧糊**：对中层菜品图施加 CSS 滤镜（如 `filter: brightness(0.25) sepia(0.55) contrast(1.25)`）叠加深色焦斑 SVG 遮罩 + 灰色升腾浓烟 SVG 动画 + 焦糊警告徽标；玩家一眼识别已糊且无需画 40 张焦黑版菜品图。
4. **结合项目已有 AI 生图能力的实操基准**：
   - `frontend/public/gifts/CREDITS.md` 已验证在本项目中用图像生成模型（`gpt-image-2.5` / `gpt-image-2`）+ 固定提示词骨架生成透明底「柔和平涂」图标的工作流：裁掉透明边使主体占画幅约 75–80%，统一缩至 512×512（餐馆菜品/食材可进一步缩至 256×256）转 WebP 质量 82，并用自动化测试校验尺寸与文件体积。
   - 优势：版权归属清晰、无第三方授权冲突、**彻底解决开源图标库普遍缺少中式家常菜的问题**；缺点：生成时需人工抽检辨识度与一致性，避免不同批次光影角度漂移。

---

## 三、合法免费/开源美术素材盘点（一手协议核实）

> **许可兼容性前提**：Eidolon-SC 主仓库采用 **`AGPL-3.0-or-later`**（`LICENSING.md`）。因此纳入仓库 `frontend/public/` 的素材须优先选用 **CC0 1.0**、**MIT** 或 **Apache-2.0**（保留版权声明即可，无分发限制冲突）；**CC BY 4.0** 可合规使用但须履行署名义务；**CC BY-SA 4.0** 若做衍生修改会触发 ShareAlike 传染，须在 `LICENSING.md` 划界隔离；任何**禁止独立再分发（Standalone）或禁止随源码分发**的专有免费网站素材不可直接提交进公开仓库。

| 来源 | 一手许可协议与出处 | 署名要求 | 风格与规格 | 食材/厨具/中餐覆盖度 | 局限与注意点 |
|---|---|---|---|---|---|
| **Microsoft Fluent Emoji** | **MIT License**<br>[LICENSE](https://github.com/microsoft/fluentui-emoji/blob/main/LICENSE) / [仓库](https://github.com/microsoft/fluentui-emoji) | 保留 MIT 版权与许可文本（放 `CREDITS.md`/`LICENSING.md`） | 提供 `3D`、`Color`、`Flat`、`High Contrast` 4 套风格（SVG + PNG），现代柔和圆润，视觉上最接近本站 `gifts` 插画 | 覆盖 Unicode Food & Drink 组约 **132 个**食物与餐具图标（含鸡蛋、肉、蔬菜、平底锅、炖锅、米饭、拉面、饺子、咖喱等，参考 [Unicode 18.0 Emoji Counts](https://www.unicode.org/emoji/charts-18.0/emoji-counts.html)） | **无具体中式家常菜**（无番茄炒蛋、麻婆豆腐、回锅肉、红烧肉等），缺中式铁锅、案板、切配过程态；仅适合作为基础食材/通用餐具或原型占位。 |
| **Google Noto Emoji** | **SVG/PNG 图像：Apache-2.0**<br>字体文件：SIL OFL 1.1<br>旗帜：公有领域<br>[README 许可节](https://github.com/googlefonts/noto-emoji/blob/main/README.md) / [LICENSE](https://github.com/googlefonts/noto-emoji/blob/main/LICENSE) | 保留 Apache-2.0 声明与 NOTICE | 柔和扁平矢量（SVG/PNG），轮廓友好、低噪点，小尺寸辨识度好 | 同 Unicode 全量 Food & Drink（~132 个） | 同上，仅覆盖 Unicode 标准食物，缺中餐成菜与厨具多状态；注意不要误把 `fonts/` 下的 OFL 文件与图像 Apache-2.0 混标。 |
| **Twemoji（`jdecked/twemoji` 社区维护版）** | **图形：CC BY 4.0**<br>代码：MIT<br>[LICENSE-GRAPHICS](https://github.com/jdecked/twemoji/blob/main/LICENSE-GRAPHICS) / [仓库](https://github.com/jdecked/twemoji) | **必须署名**（作者、来源链接、CC BY 4.0 链接、改动说明） | 极简扁平矢量（SVG，Unicode 17.0 同步；原 `twitter/twemoji` 已停更） | 同 Unicode Food & Drink | **不可直连 jsDelivr CDN**（会被本站 CSP 拦截），须自托管挑选出的 SVG；同样无中餐细分菜品。 |
| **OpenMoji** | **CC BY-SA 4.0**<br>[LICENSE.txt](https://github.com/hfg-gmuend/openmoji/blob/master/LICENSE.txt) / [仓库](https://github.com/hfg-gmuend/openmoji) | **必须署名 + 修改衍生须同样 CC BY-SA 4.0** | 统一粗黑描边手绘扁平风（SVG/PNG），含少量超出 Unicode 的拓展符号 | 覆盖 Unicode Food & Drink + 少量扩展食物/器具 | **ShareAlike 约束**：若对图标做二次修改合成，衍生图须按 CC BY-SA 4.0 共享；视觉风格偏粗线黑框，与 `gifts` 柔和平涂差异较大。 |
| **Kenney — Food Kit** | **CC0 1.0 Public Domain**<br>[素材页](https://kenney.nl/assets/food-kit) / [官方许可 FAQ](https://kenney.nl/support) | 无需署名 | **注意：是 3D 模型包**（200 个低多边形模型，非现成 2D 精灵） | 西式食物为主（汉堡、披萨、蔬菜、餐具、蛋糕、热狗等） | 用于 2D 厨房需离线批量渲染出透明 PNG/WebP，且几乎无中餐菜肴；仅适合借用部分西式食材/通用碗盘。 |
| **Kenney — Pixel Platformer Food Expansion & UI Pack** | **CC0 1.0 Public Domain**<br>[Food Expansion](https://kenney.nl/assets/pixel-platformer-food-expansion) / [UI Pack](https://kenney.nl/assets/ui-pack) | 无需署名 | 2D 像素平台跳跃风（110 个文件）；UI Pack 为 2D 卡通按钮/面板矢量与精灵 | Food Expansion 偏糖果/甜品/快餐像素块；UI Pack 提供大量干净的通用按钮、进度条、弹窗底板 | Food Expansion 与中餐写实度低；`UI Pack` 的 2D 按钮/进度条/面板规范极适合厨房独立 UI 框架参考或直接复用。 |
| **OpenGameArt CC0 食物/厨房像素包** | **CC0 1.0 Public Domain**（已逐页核实 CC0 徽标）<br>[CC0 Food Icons](https://opengameart.org/content/cc0-food-icons)<br>[Cute Food Sprites](https://opengameart.org/content/cute-food-sprites)<br>[32px Food Items](https://opengameart.org/content/32px-food-items)<br>[1950's Indoor Kitchen Tileset](https://opengameart.org/content/1950s-scifi-setting-indoor-tileset-with-kitchen-appliances) | 无需署名（部分作者附鼓励致谢） | 16×16 / 24×24 / 32×32 像素精灵为主（其中 `CC0 Food Icons` 汇总了多位作者的像素与 OCAL 矢量图标） | 偏 RPG 补给、寿司、甜品、快餐、咖啡；室内厨具包画风偏复古科幻或中世纪酒馆 | **多包拼凑画风极不统一**，且几乎找不到成套中式家常菜与现代中餐厨具；仅适合像素风原型验证或个别食材拾遗。 |
| **自产组合：AI 生图（沿用 `gifts` 管线）+ 自绘 SVG** | 项目自有产出（无第三方版权冲突）<br>参考本仓库 `frontend/public/gifts/CREDITS.md` | 无第三方署名义务 | 柔和平涂 WebP（256×256/512×512）+ 自绘矢量 SVG 厨具/柜台/状态特效 | **100% 精准覆盖** 30–50 道中式家常菜、中式食材（葱姜蒜/豆瓣酱/豆腐等）与铁锅/蒸笼/砂锅 | 需要前期定好统一提示词骨架与质检脚本（尺寸/体积/裁边），投入一定策展与抽检工时。 |

---

## 四、合法免费/开源音频素材盘点与许可雷区（一手核实）

### 4.1 推荐与可用来源（许可清晰，兼容公开仓库与存储桶）

| 来源 | 一手许可协议与出处 | 署名与分发规则 | 覆盖场景（厨房 SFX / 轻快 BGM） | 优势与局限 |
|---|---|---|---|---|
| **Kenney Audio 系列** | **CC0 1.0 Public Domain**<br>[音频目录](https://kenney.nl/assets/category:Audio) / [许可 FAQ](https://kenney.nl/support)<br>（本站 `public/sounds/connect.ogg` 已采用 `Interface Sounds`） | 无需署名，可直接进公开仓库或存储桶 | 包含 `Interface Sounds`、`UI Audio`、`Impact Sounds`、`RPG Audio`、`Digital Audio`、`Music Jingles`。**强项**：点击、点单提示、出餐叮咚、连击升调、营业结束短旋律（Jingles）、锅具轻撞（Impact） | 质量整齐、无底噪、现成短音效开箱即用；**短板**：不含炒菜滋啦、切菜、沸水等厨房写实 SFX，也无长循环 BGM。 |
| **Freesound（严格筛选 CC0 1.0）** | 平台提供 **CC0 1.0** / CC BY 4.0 / CC BY-NC 4.0 / Sampling+（历史）<br>[官方 FAQ 许可节](https://freesound.org/help/faq/#what-do-i-need-to-do-to-legally-use-the-files-on-freesound)<br>（本站 `public/sounds/hang-up.mp3` 已采用 CC0 条目） | 仅选用 **CC0 1.0** 时无需署名且可自由进仓库；若选 CC BY 4.0 需在 `CREDITS.md` 逐条写作者与链接；**严禁选用 CC BY-NC**（非商用限制与 AGPL 冲突） | **厨房写实 SFX 最全**：热油滋啦（pan sizzle/fry）、菜刀切菜（chopping board）、开火点火（gas stove）、汤锅沸腾（boiling）、瓷盘轻放、厨师铃（service bell） | 录音质量参差，需离线统一裁剪、淡入淡出制作无缝循环点、统一响度（LUFS）并转码为 MP3/M4A。 |
| **OpenGameArt CC0 音效与 BGM** | **CC0 1.0 Public Domain**（已逐页核实 CC0 徽标）<br>- 音效：[boiling water loops](https://opengameart.org/content/boiling-water-loops)（TinyWorlds）、[General Household Sound Effects](https://opengameart.org/content/general-household-sound-effects)（bretbernhoft）<br>- BGM：[Coffee House Bump](https://opengameart.org/content/coffee-house-bump)（OatCog，轻快咖啡馆爵士循环）、[Chips and a Soda](https://opengameart.org/content/chips-and-a-soda-chiptune)（Pro Sensory，轻快循环） | 无需署名，可直接进公开仓库或上传存储桶 | 提供现成可循环（loopable）的轻快 BGM 与少量厨房环境循环音 | 轻快日常向 CC0 曲目总量有限，需人工试听挑出不吵耳、久听不腻的 2–4 首循环曲；原文件多为大体积 WAV，须离线转码压缩。 |
| **Incompetech（Kevin MacLeod）** | 免费版为 **CC BY 4.0**<br>[官方许可页](https://www.incompetech.com/music/royalty-free/licenses/) | **必须按官方格式署名**（在 `CREDITS.md` 与致谢页注明曲名、作者、站点与 CC BY 4.0 链接） | 轻快爵士、波萨诺瓦、温馨厨房/咖啡馆风格 BGM 储备极大，成品编曲水准稳定 | 曲库丰富但**非 CC0**，必须严格保留署名；若想完全免署名则不选此源。 |
| **Web Audio API 程序化合成 SFX（兜底 / 轻量主方案）** | 浏览器原生 W3C 标准，**零外部许可负担**<br>[MDN AudioContext](https://developer.mozilla.org/en-US/docs/Web/API/AudioContext) / [createBuffer](https://developer.mozilla.org/en-US/docs/Web/API/BaseAudioContext/createBuffer) / [BiquadFilterNode](https://developer.mozilla.org/en-US/docs/Web/API/BiquadFilterNode) | 无 | 可纯代码实时合成：<br>- 煎炒滋啦 / 沸腾持续循环（白/粉红噪声缓冲 + 带通/高通 `BiquadFilterNode` + 随机爆裂包络）<br>- 切菜短促噪点脉冲<br>- 点单提示、出餐叮咚、连击升调、计时滴答、烧糊告警（`OscillatorNode` + 指数增益包络） | **0 KB 资源包体、无 Safari Ogg 兼容问题、天然支持 iOS `GainNode` 独立调音**、可随游戏状态实时变调（如快烧糊时提高滤频焦躁感、连击升高半音）；局限在于缺乏真实厨具与食材的有机录音质感，且不适合合成复杂乐器 BGM。 |

> **失效来源核查注记**：常见推荐名单中的公有领域音乐站 **FreePD.com** 主站现已停止托管关闭（访问首页直接显示 `FreePD.com - Site Closed`，[freepd.com](https://www.freepd.com/)）。尽管社区 GitHub/Codeberg 留有历史备份镜像，但主站停运导致原始授权页不可在线验证，溯源确定性弱于 OpenGameArt 与 Freesound。

### 4.2 必须规避的免费素材许可雷区（一手条文核实）

| 来源 | 一手官方条款核实 | 对 Eidolon-SC 的具体风险 |
|---|---|---|
| **Mixkit — Stock Music Free License** | [Mixkit Music Free License 原文](https://mixkit.co/license/modal/musicFree/)：<br>*"You're **not allowed to use them in** CDs or DVDs, **video games** or tv or radio broadcast."* | **明文禁止用于电子游戏**。餐馆玩法的 BGM **绝对不可**使用 Mixkit 免费音乐。 |
| **Mixkit — Sound Effects Free License** | [Mixkit SFX Free License 原文](https://mixkit.co/license/modal/sfxFree/)：<br>允许用于 video games，但同时规定：*"You **can't redistribute the Item on its own**, as stock, in a tool or template, or **with source files**."* | **禁止随源码文件再分发**。因为 Eidolon-SC 为 AGPL-3.0 公开开源仓库，将 Mixkit 音效放进 `frontend/public/` 与源码一同分发直接违反条款。 |
| **Pixabay Content License** | [Pixabay License Summary](https://pixabay.com/service/license-summary/)：<br>*"You **cannot sell or distribute Content** (either in digital or physical form) **on a Standalone basis**. Standalone means where no creative effort has been applied to the Content and it remains in substantially the same form as it exists on our website."*<br>且页尾明示部分内容可能存在第三方知识产权/版权主张，使用者自担核验责任。 | **禁止独立形态再分发**：开源 Git 仓库中直接提交未经改造的音频/图片原文件可被直接单独下载，存在违反 Standalone 禁令及第三方 Content ID 申诉风险，**不适合作为开源项目直接素材源**。 |

---

## 五、关键技术事实与权衡汇总（供票 09 / 票 11 拍板参考）

1. **角色呈现与 WebGL 并发预算**：现有 `<Stand>` 每实例独占 1 个 WebGL 上下文；活跃通话层在后台已常驻占用 1 个上下文，而 Android Chrome 默认上限仅约 8 个。因此「1 个动态 `<Stand>` + 多客位头像/轻量 2D 卡片」与「多位动态 `<Stand>` 同屏」在工程复杂度和移动端稳定性上差距显著（后者需重写单上下文多骨架渲染器）。
2. **风格与菜谱规模的匹配**：若目标包含 30–50 道以《HowToCook》中式家常菜为主的菜谱，开源图标/像素包几乎全量缺失具体中餐菜品；「柔和平涂 2D 矢量/WebP + 三层组合式渲染（容器底图 + 食材/成品图 + CSS/SVG 蒸汽与焦糊特效）」在视觉融合度（对齐 Spine 立绘与 `gifts` 插画）、手机横屏清晰度与资产规模控制上比低分像素风包袱小。
3. **资产存放位置与 CSP**：因本站 CSP 封锁外部域，一切自选图片/音频只能放 `frontend/public/`（体量小、许可干净时部署零步骤）或 `EIDOLON_STAND_ASSETS_URL` 公开存储桶（大体积 BGM 避免膨胀镜像、支持按需拉取与静音降级）。
4. **音频格式与 iOS 行为**：避开酒吧沿用原版 `.ogg` 导致 Safari 18.4 前静音的局限，餐馆自选/转码 CC0 音频使用 MP3/AAC（`.m4a`）即可全端播放；若需在 iPhone 上也能独立调节 BGM 音量（`<audio>.volume` 在 iOS 只读为 1），须考虑 Web Audio `GainNode` 路线（或像酒吧一样在 iPhone 禁用音乐音量条）；同时须在票 11 明确活跃通话时餐馆音频的静音/降音策略。
5. **素材合规红线**：优先 **CC0 1.0**（Kenney、Freesound CC0、OpenGameArt CC0）、**MIT**（Fluent Emoji）或 **Apache-2.0**（Noto Emoji 图像）及项目自产 AI 图/Web Audio 合成；**直接排除 Mixkit（音乐禁游戏、音效禁随源码分发）与 Pixabay（禁 Standalone 分发且有第三方权利免责）**。
