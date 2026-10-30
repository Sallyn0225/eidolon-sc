# 调研：动态旁边的天气从哪取

对应票：`.scratch/moments/issues/02-weather-research.md`。调研日期 2026-10-31。下文的「实测」都是当天东京时间 02:40 前后用 curl 跑的，原始返回放在 `E:/tmp/moments-research/raw/`。

## 结论

**建议用 Open-Meteo 的 Forecast API（`api.open-meteo.com/v1/forecast`，不用 key），按地点坐标取逐小时的 `weather_code`（WMO 码）和 `temperature_2m`。生成动态时取「动态露出那一刻」所在小时的值，把天气写进提示词，也和动态一起存下来，之后不再改。动态旁边显示一个天气图标和整数气温（如「☀ 18°」）。取不到就不显示天气，提示词里也不给天气素材，不换别家补，也不编。**

理由：

1. **条款对得上这类部署。** 免费版限非商业使用，但条款把「没有订阅、没有广告的个人或非营利网站」算作非商业，还写明自愿打赏（tip jar）不算商业。我们的「赞赏」就是一张收款码，付不付都不影响能用什么，在允许的范围里。要求是 CC BY 4.0 署名：显示数据的地方旁边放一个指向 open-meteo.com 的链接。
2. **数据正合用，量也远够。** 在东京，它的默认模型就是气象庁的 MSM（5 km，每 3 小时更新），实测 `best_match` 和 `jma_msm` 的返回逐项相同。它按经纬度取值，一次请求能带多个坐标，能取过去的小时（`past_days` 最多 92 天，或者用 `start_hour`/`end_hour`），也能取未来 4 天。全站一天几百条动态，就算逐条取也只有几百次请求，免费额度是每天 1 万次。
3. **从我们的服务器直连就能用。** 在京东云 VPS 上不走代理，curl 返回 200，用时 1.7 s。社区分支 Eidolon Hibi 的天气用的也是它，写法和这里建议的差不多。

为什么「生成时定下，之后不改」：天气本来就是动态的素材之一（地图里定的「此刻里的素材」）。如果她写了「下雨了」，旁边的小字却在露出时改成晴，就对不上了。动态最多比生成时晚几小时露出，MSM 能预报 4 天，取露出那一刻的预报值就够用。

几个配套的决定：

- **不进网络代理选项。** 直连已经通了。天气取不到只是少一行小字，不像对话模型那样非通不可。代理的选项一加，`ProxiedService`、GLOSSARY、后台设置、体检都要跟着改。真有部署者连不上，以后再加一项 `weather` 也很容易。客户端照 `proxy.py` 的规矩写 `trust_env=False`，不去读环境里的 `HTTPS_PROXY`。
- **不进「服务状态」。** 它不是部署者付费的服务，坏了也不影响任何功能。
- **缓存是为了稳，不是为了省额度。** 按「坐标格（取两位小数，约 1 km）× 小时」缓存一份，最多存 3 小时（MSM 每 3 小时更新一次）。请求失败后 10 分钟内不再试，免得服务挂了的时候每次生成都卡在超时上。不要整点去取：Open-Meteo 的维护者说过，他们只在每个整点的高峰丢请求。

**什么情况下要改结论：**

- 部署开始放广告或收订阅费：免费版就不能用了，要改用付费版，或者换 MET Norway（见后文）。fork 出去的部署也是这样，部署文档里要写明。
- 用户在意天气实况准不准：实测时 Open-Meteo 把「几乎没有日照的阴天」判成了「大致晴」（见「精度」一节）。如果要「东京此刻真实的天」，可以只在东京用气象庁 AMeDAS 的观测值（有气温、降水和日照时数，但没有天气分类），自己推出晴、阴、雨。代价是要用一个非正式的接口，地点也只能落到观测站。眼下建议不做。

## 1. 候选数据源

| | Open-Meteo | 气象庁 bosai JSON | wttr.in | MET Norway Locationforecast | OpenWeatherMap |
|---|---|---|---|---|---|
| 要不要 key | 不要 | 不要 | 不要 | 不要，但必须带能认出你的 User-Agent | 要 |
| 条款 | 免费版限非商业，CC BY 4.0 | 公共データ利用規約 1.0，要写出处，可以商用 | 没写数据许可 | CC BY 4.0 | 价目页没写清 |
| 频率限制 | 每分钟 600、每小时 5,000、每天 10,000 | 没公布 | 没公布，上游额度用完就整站停到 UTC 0 点 | 每个应用合计超过 20 次/秒要另谈 | 免费版每分钟 60、每月 100 万 |
| 天气分类 | WMO 码 | 只有预报有气象庁天气码（按地方、按天）；AMeDAS 实况没有 | WWO 码 | `symbol_code` | 有 |
| 按什么取 | 经纬度（可以一次多个） | 地方代码或观测站号 | 城市名或经纬度 | 经纬度 | 经纬度或城市 |
| 历史值 | 有（最多 92 天；更早的有 Historical Forecast API） | AMeDAS 逐站数据大约留 10 天 | 没有 | 没有，从当前小时开始 | 免费版没有 |
| 日本的数据 | 气象庁 MSM 5 km | 官方观测 | WWO，实测离谱 | 全球模式 | 没测 |

### Open-Meteo

- 条款：免费 API 限每天 1 万次以下、每小时 5,000、每分钟 600，按 IP 和应用计数。非商业的例子有「没有订阅也没有广告的私人或非营利网站、应用」，商业的例子是「有订阅或展示广告的网站、应用」，并写明「Voluntary donations, including contributions through a tip jar, are permitted」。服务按现状提供，不保证不中断。见 [Terms](https://open-meteo.com/en/terms)。
- 计数：一般一次 HTTP 请求算一次。超过 10 个变量或超过 2 周的数据会按比例多算。多个坐标怎么算，页面没写。见 [Pricing](https://open-meteo.com/en/pricing)。我们只要 2 个变量、几个小时，所以一次请求就是一次。
- 署名：CC BY 4.0，「You must include a link next to any location Open-Meteo data are displayed」，示例是 `<a href="https://open-meteo.com/">Weather data by Open-Meteo.com</a>`。JMA 是它列出的数据源之一，许可链接指向气象庁的版权页。见 [Licence](https://open-meteo.com/en/licence)。
- 日本的数据：东京的区域模式是 JMA MSM，全球的底子是 ICON、GFS、IFS（[Docs](https://open-meteo.com/en/docs)）。MSM 是 0.05°（约 5 km）、逐小时、预报 4 天、每 3 小时更新；在 JMA 模式里，`weather_code` 是从云量、气温、降水、降雪算出来的，**不出雷暴和雾的码**（[JMA API](https://open-meteo.com/en/docs/jma-api)）。
- 稳定性：2026-10-17 的 [issue #2220](https://github.com/open-meteo/open-meteo/issues/2220) 里，免费 API 在中欧过载、返回 503。维护者说，他们用 Geo IP 把请求分到各区域的服务器，只在每个整点的高峰丢请求，因为很多人把定时任务设在 XX:00。三天后加了服务器，issue 已关闭。往年的故障报告大多出在 archive-api（[#1864](https://github.com/open-meteo/open-meteo/issues/1864)、[#1410](https://github.com/open-meteo/open-meteo/issues/1410)），forecast 少一些（[#1870](https://github.com/open-meteo/open-meteo/issues/1870)，502）。

### 气象庁 bosai JSON

- 性质：2021 年气象庁网站改版成单页应用后，页面数据改由 JSON 提供，被开发者「发现」。气象庁职员 @e_toyoda 的说法是：气象庁不承诺规格的连续性，也不发运行状况的通知，所以只能说「不是 API」；但可以按政府标准利用规约使用（[窓の杜 2021-03-02](https://forest.watch.impress.co.jp/docs/serial/yajiuma/1309318.html)）。
- 条款：页面内容按「公共データ利用規約（第1.0版）」使用，必须写出处（如「出典：気象庁ホームページ（URL）」）；加工过要另外注明；不能让人以为是国家做的。部分内容受气象业务法第 17 条（预报业务许可）和第 23 条（警报的限制）约束（[気象庁ホームページについて](https://www.jma.go.jp/jma/kishou/info/coment.html)）。我们只显示一个时刻的天气，不算对外发布预报；但这一点没有仔细查。
- 实测：
  - `forecast/data/forecast/130000.json`（东京都）只有「東京地方」这种地方级别、按天的预报：天气码（如 `200`）、描述（「くもり　所により　夕方　雨」）、6 小时的降水概率、早晚的气温。粒度太粗，不是「此刻」。
  - AMeDAS 全国一览 `amedas/data/map/<时刻>.json`（1,286 站，约 250 KB）和单站 `amedas/data/point/44132/<日期>_<时>.json` 都有每 10 分钟的气温、降水、日照、风。**1,286 个站里没有一个带天气分类字段**，晴、阴只能自己从日照、降水推，夜里连晴和阴都分不出来。
  - 单站数据能往回取：9 天前的返回 200，15 天前的返回 404。
  - 从本机走代理（`127.0.0.1:10808`）取，TLS 连接被断开；直连和从 VPS 直连都正常。
- 结论：要 Open-Meteo 不提供的东西（真实观测）时才值得用。代价是用一个非正式接口、天气分类要自己推、地点只能落到观测站。不作为首选。

### wttr.in

- 实测：`wttr.in/Tokyo?format=j1` 把「Tokyo」解析成了**式根島**（34.327, 139.218，离东京约 150 km 的海上小岛），返回阴、23°C。改用坐标 `35.6895,139.6917` 取，返回「Light rain +62°F」，同一时刻 AMeDAS 东京的 1 小时降水是 0.0。单位跟着请求方的 IP 走，代理出口在美国，返回的就是华氏度。
- 上游是 WorldWeatherOnline。额度用完时，`format=j1` 照样返回 HTTP 200，内容是「Unknown location; please try ...」（[issue #890](https://github.com/chubin/wttr.in/issues/890)）。维护者把这种情况的 issue 标题改成「wttr.in is down until 0:00 UTC」（[#1059](https://github.com/chubin/wttr.in/issues/1059)，2025-01；类似的还有 [#522](https://github.com/chubin/wttr.in/issues/522)）。
- README 建议脚本和监控类的调用改用 `wttr.is`，没写数据许可和频率限制（[README](https://github.com/chubin/wttr.in)）。
- 结论：不能用。

### MET Norway Locationforecast（备选）

- 条款：请求必须带能认出你的 User-Agent（最好附联系方式）；每个应用合计超过 20 次/秒要另谈；在 `Expires` 之前别重复请求，要用 `If-Modified-Since`；数据按 CC BY 4.0 署名（[Terms of Service](https://api.met.no/doc/TermsOfService)）。条款页没说能不能商用。
- 实测：`locationforecast/2.0/compact?lat=35.69&lon=139.75` 返回 200，88 个时间点，从当前小时开始（没有过去的），每小时给 `symbol_code`（如 `partlycloudy_night`）和气温，`Expires` 设在半小时后。
- 结论：Open-Meteo 用不了时（比如部署开始放广告）可以换它，图标映射要重写。眼下不接。

### OpenWeatherMap（没深入）

免费版每分钟 60 次、每月 100 万次，必须注册拿 key（[Pricing](https://openweathermap.org/price)）。价目页没写免费版能不能商用、怎么署名。要 key 就多一项部署者配置，没有理由放着 Open-Meteo 不用，所以没有往下查。

## 2. 能拿到什么（Open-Meteo）

- **分类码**：WMO 码 0（晴）、1（大致晴）、2（局部多云）、3（阴）、45/48（雾）、51–57（毛毛雨）、61–67（雨）、71–77（雪）、80–82（阵雨）、85–86（阵雪）、95–99（雷暴）。表见 [Docs](https://open-meteo.com/en/docs)。在日本走 JMA 模式时不会出现雾和雷暴（见上）。
- **气温**：`temperature_2m`，°C。
- **白天还是夜里**：`is_day`，夜里的晴可以换月亮图标。
- **按经纬度取**，一次能带多个坐标（逗号分隔，返回一个列表）。`cell_selection` 默认是 `land`：挑一个海拔相近的陆地格点。
- **时刻**：`current` 是每 15 分钟的模式值；`hourly` 可以用 `past_hours`/`forecast_hours`，或者 `start_hour`/`end_hour` 精确圈定一段时间。`timezone=Asia/Tokyo` 返回的是东京本地时间，也可以用 `timeformat=unixtime` 避开时区换算。
- **历史**：Forecast API 的 `past_days` 最多 92 天。更早的走 Historical Forecast API，实测取 2025-10-30 的逐小时值，返回 200。

实测返回（节选）：

```json
{"latitude":35.7,"longitude":139.6875,"timezone":"Asia/Tokyo","elevation":40.0,
 "current":{"time":"2026-10-31T02:45","interval":900,"temperature_2m":12.7,"weather_code":0,"is_day":0}}
```

```json
"hourly":{"time":["2026-10-30T12:00", "...", "2026-10-30T18:00"],
          "temperature_2m":[18.6,20.3,20.9,18.5,17.6,16.8,16.3],
          "weather_code":[1,1,1,1,1,2,1]}
```

## 3. 精度：和气象庁观测对一下（实测，样本很少）

| 时刻、地点 | Open-Meteo | AMeDAS 观测 |
|---|---|---|
| 10-31 02:40 东京（北之丸，35.6917, 139.75） | 13.4°C，码 0 | 14.3°C，降水 0 |
| 10-31 02:40 横滨（35.4383, 139.6517） | 18.2°C，码 0 | 18.2°C |
| 10-30 14:00 东京 | 20.9°C，码 1（大致晴），云量 28% | 18.4°C，当小时日照 0.4 h |
| 10-30 12–18 时 东京 | 码全是 1–2，云量 28–72% | 日照 0–0.4 h/h，气象庁当天预报「くもり　所により　夕方　雨」 |

- 气温误差在 2–3°C 以内。东京和横滨夜里差了 5°C，模型也报出来了。
- 天气分类可能偏差一档：那天下午实际几乎没有日照，模型给的却是「大致晴」。`best_match`、`jma_seamless`、`jma_msm` 三个模型这一段的返回完全相同。
- 只对了两个时刻，说明不了平均有多准，只能说明会有「阴天显示成晴」这种情况。对一行小字来说可以接受。

## 4. 取值开销

- 量：全站一天几百条动态。最笨的办法是每条取一次，一天也就几百次，约占免费额度（每天 1 万次）的 3%。地点多在东京周边，要是按格点和小时缓存，次数还会少不少。**额度不是问题。**
- 建议的取法：
  1. 生成一条动态时，用它地点的坐标（来自地点池，地图要用坐标，所以地点池本来就要有）和它的露出时刻，向缓存要「这个格点这个小时」的码和气温。
  2. 缓存没有，就发一次 `hourly=temperature_2m,weather_code,is_day&past_hours=1&forecast_hours=12&timezone=Asia/Tokyo` 的请求，把返回的十几个小时都放进缓存。缓存 3 小时内有效，放内存就行，进程重启后丢了也没关系。
  3. 取到的码和气温写进提示词的素材，也和动态存在一起（存两个可以为空的列：WMO 码、整数气温）；之后不再改。
- 不建议每小时去拉一批所有地区：拉回来的数据大多用不上，还容易撞上整点高峰。
- 超时设短一些（Hibi 是 5 秒、连接 3 秒）。生成动态本来就在后台，等一会儿没关系，但也不值得多等。

## 5. Eidolon Hibi 是怎么做的

看的是默认分支 `My-features` 的 `1fb2454`：[`backend/src/eidolon/weather.py`](https://github.com/x499806631-commits/Eidolon-Hibi/blob/1fb2454acd98063a4113c1b55f083a57fb8e40c7/backend/src/eidolon/weather.py)，GLOSSARY 的「天气」条目。

- 数据源是 **Open-Meteo**，`/v1/forecast`，`current=temperature_2m,weather_code`，`timezone=auto`，不用 key。
- 只有一个地点：部署者在 `.env` 里填的 `EIDOLON_WEATHER_LAT`/`EIDOLON_WEATHER_LON`，算作「制作人那边」，不是按用户、按地点取。不填就没有天气。
- 用法：每个回合告诉她一句「制作人那边现在下着小雨，12°C。」；通话的环境音选「自动」时供判断模型参考；「家」的窗外跟着变。
- 缓存和失败：同一句话 30 分钟内重复用；请求失败后 10 分钟内不再试，这期间沿用上一句，没有就不提；超时 5 秒（连接 3 秒）。不认识的码返回 None，不提天气。
- WMO 码先翻成中文短句（`SKIES`），再归成六类：clear/cloudy/fog/rain/snow/storm（`sky_of`）。这两张表可以直接拿来参考。
- 用的是普通的 `httpx.AsyncClient`，没走代理，`trust_env` 用默认值。没在它的「关于」页找到给 Open-Meteo 的署名（GitHub 的代码搜索不索引 fork，所以没能把整个仓库查一遍）。
- 用户能在设置的「玩法」里把天气关掉。

和我们的差别：它只取一个固定地点的「现在」，我们要按动态的地点、在指定的时刻取，所以要用 `hourly` 加时刻，不能只用 `current`。

## 6. 仓库里能沿用什么

- **HTTP 客户端**：后端统一用 `httpx`（`pyproject.toml` 是 `httpx[socks]`）。有两种写法可以照抄：
  - `backend/src/eidolon/proxy.py` 的 `open_client(proxy, timeout)`：`trust_env=False`，共用 `TLS_CONTEXT`；传 `None` 就是直连。模块说明写明「不按环境里的 `HTTPS_PROXY` 这类变量走」。
  - `backend/src/eidolon/price_catalog.py` 的 `Catalog`：构造时接收一个可注入的 `transport`（测试里换成 `httpx.MockTransport`，见 `backend/tests/fakes.py`），自己持有一个长期的 `AsyncClient`，带 `User-Agent: eidolon-sc`，再挂进 `assembly.py` 的 `closers`。天气客户端照这个写，再加上 `trust_env=False`。
- **网络代理**：`config.py` 的 `ProxiedService` 列了 12 项，分部署者的八项和用户自带的四项；GLOSSARY「网络代理」说的也是这些服务。价格目录（models.dev、OpenRouter）就不在代理选项里，直连，这是「辅助性的外部数据不进代理选项」的先例。
- **要不要进代理选项**：建议不进（理由见「结论」）。实测：从 VPS 直连 Open-Meteo 返回 200（1.7 s），bosai 200（0.8 s），wttr.in 200（0.5 s）。本机走代理取 bosai 失败，说明走代理反而可能出问题。以后要加，就是在 `ProxiedService` 里加一项 `weather`，再同步改 GLOSSARY、后台设置和 `doctor.py` 的体检。

## 7. 显示粒度和退路

- **显示**：一个图标加整数气温，如「☀ 18°」。图标的 `aria-label`/`title` 写中文，如「晴 18°C」。不加「天气数据来自……」之类的说明文字。
- **图标分档**（WMO 码 → 图标），粒度比 Hibi 的六类稍细：
  - 0–1 晴（夜里 `is_day=0` 换月亮）
  - 2 多云
  - 3 阴
  - 45/48 雾
  - 51–67、80–82 雨
  - 71–77、85–86 雪
  - 95–99 雷雨

  「大致晴」和「晴」合成一档，因为模型本来就分不太清。
- **署名**：朋友圈页面底部放一个很小的「天气：Open-Meteo」链接，指向 open-meteo.com。这算 CC BY 4.0 要求的「数据旁边的链接」。另外在「关于」或使用条款里列一下，写进地图里「隐私政策和使用条款」那一项。顺带一提：Open-Meteo 只会收到地点坐标，不涉及任何用户数据，对隐私政策几乎没有影响。
- **退路**：
  - 取不到（超时、HTTP 错误、不认识的码）：这条动态不带天气，存空值，前端不显示那一格；提示词里也不给天气素材，免得文字里出现一个没有依据的天气。不换备用服务，不按季节编，事后也不补（补上去可能和已经写好的文字对不上）。
  - 连续失败：失败后 10 分钟内不再请求，这期间生成的动态都不带天气。
  - Open-Meteo 长期用不了，或者部署变成商业的：换 MET Norway Locationforecast。存的仍然是我们自己的图标分档，只是映射表改从 `symbol_code` 来。

## 来源

- Open-Meteo：[Terms](https://open-meteo.com/en/terms)、[Pricing](https://open-meteo.com/en/pricing)、[Licence](https://open-meteo.com/en/licence)、[Docs（Forecast API）](https://open-meteo.com/en/docs)、[JMA API](https://open-meteo.com/en/docs/jma-api)、[issue #2220](https://github.com/open-meteo/open-meteo/issues/2220)、[#1864](https://github.com/open-meteo/open-meteo/issues/1864)、[#1870](https://github.com/open-meteo/open-meteo/issues/1870)、[#1410](https://github.com/open-meteo/open-meteo/issues/1410)
- 气象庁：[気象庁ホームページについて（利用規約）](https://www.jma.go.jp/jma/kishou/info/coment.html)；关于 bosai JSON 性质的职员发言，转引自[窓の杜 2021-03-02](https://forest.watch.impress.co.jp/docs/serial/yajiuma/1309318.html)（原推文没有找到）
- wttr.in：[README](https://github.com/chubin/wttr.in)、[issue #890](https://github.com/chubin/wttr.in/issues/890)、[#1059](https://github.com/chubin/wttr.in/issues/1059)、[#522](https://github.com/chubin/wttr.in/issues/522)
- MET Norway：[Terms of Service](https://api.met.no/doc/TermsOfService)
- OpenWeatherMap：[Pricing](https://openweathermap.org/price)
- Eidolon Hibi：[weather.py @ 1fb2454](https://github.com/x499806631-commits/Eidolon-Hibi/blob/1fb2454acd98063a4113c1b55f083a57fb8e40c7/backend/src/eidolon/weather.py)
- 本仓库：`backend/src/eidolon/config.py`（`ProxiedService`、`ProxySettings`）、`backend/src/eidolon/proxy.py`、`backend/src/eidolon/price_catalog.py`、`GLOSSARY.md`「网络代理」「赞赏」、`.scratch/moments/map.md`
- 实测原始返回：`E:/tmp/moments-research/raw/`
