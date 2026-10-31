# 03: 她的声音念信

**What to build:** 拆开信以后，她用自己的声音念，字跟着她念到哪里写到哪里；重看时一样有声音。部署者没有语音合成、或者合成失败时，信照样来，只是没有声音，字按估的时间写。读信时能静音。

见 spec「写一封信」的语音一条、「时间轴（浏览器里）」「接口」。

**Blocked by:** 01

**Status:** done

- [x] 信写好后，用部署者的语音合成和它的模型，把抬头和每段分别合成成 mp3（照朗读的请求写法：语气提示按模型的规矩、读音词典、`latency: normal`），存进「信的语音」；自带语音合成密钥的用户也用部署者的。
- [x] 语音合成失败或部署者没有语音合成时，信照样存下来，读一封里语音为空；不算写信失败，运行记录里记下没合成；合成的服务调用挂在这封信的运行记录下，用量和花费进看板。
- [x] 读一封返回每块语音的地址；取语音的接口只给信的主人（别人 404），`Cache-Control: private` 加长期缓存（照照片）。
- [x] 前端拆开时取下全部语音，用 Web Audio 解码，按每块时长排时间轴：信纸展开后 1.2 秒开口，抬头后停 0.6 秒、段间停 0.9 秒，最后一块念完 0.8 秒后签名，签名 1.6 秒（和旧版一致）。取不到或解码失败时退回按字数估。网络卡住时不让字和声音对不上（旧版有处理，照着做）。
- [x] 右上角静音键。
- [x] 时间轴按实际时长排的情形补进 01 的纯函数单测。
- [x] 后端测试用 `FakeFishAudio` 经 `fish_transport` 传进 `make_client`（照 `test_read_aloud.py`）：抬头和每段各一次请求、用部署者的 key 和模型、拒绝时信照样存。
- [x] 本地构建版上自己验声音能放、字跟着走；好不好听留给用户在本机浏览器里听。

## Comments

### 票 01 交接

- 读一封的 `voice` 现在恒为 `null`（`letters.Letter.shown`），前端类型 `Letter.voice: null` 要改成每块地址的数组。`letter_voices` 表已建好、已登记进用户数据，`block` 0 是抬头。
- 时间轴已经留了每块实际时长：`partsOf(letter, durations)`，块数对不上时按字数估。`LetterLayer` 现在纯按时钟走，旧版按音频进度走的那套（`STALL_MS`、`START_MS`、静音键、`fadeOut`）这一票删掉了，要加回来看 `last-letter` 分支的 `LetterLayer.tsx`；静音键的图标和 `copy.letter.mute` 也一起删了。

### 实现说明（票 03）

- 后端：`ReadAloud.said_on_deployers`（`read_aloud.py`）照朗读的请求写法，用部署者的密钥和模型念一块；`Letters._write` 写好信后在同一条运行记录下逐块念（抬头、每段各一次），和信一起存进 `letter_voices`。部署者没有语音合成、她没配音色、或者任何一块失败时，整封都不要语音（失败那块之后的不再请求），运行记录 `degraded` 记 `{"voice": 1}`（`letters.NOT_VOICED`，和朋友圈共用这一列），结果照样是成功。
- 接口：读一封的 `voice` 是每块的地址数组，没有时为 `null`；`GET /api/letters/{id}/voice/{block}` 只给信的主人，缓存头照照片。`assembly` 里 `OwnKeys`、`ReadAloud` 挪到 `Letters` 前面建，`Letters` 多一个 `read_aloud` 参数。
- 测试设施：`fakes.build_faked` 默认带一个 `FakeFishAudio`，信写完要念，不能让测试去连真的 Fish Audio。`close_with_mano` 多收 `**services` 转给 `make_client`。
- 前端：`components/letter/letterVoice.ts` 的 `LetterVoice` 管取语音、在拆开那一下建 `AudioContext`、解码、排到音频时钟上、静音、淡出。信封一出来就开始取 mp3（照旧版 `preload`，比规格「拆开时取」早一步）；拆开后最多等 `VOICE_WAIT_MS`（10 秒，和旧版 `START_MS` 一样），等的时候字停着，等不到就按字数估。字跟着音频时钟走，纯函数 `tick`（lib/letter）在音频时钟停住超过 `STALL_MS`（4 秒，系统挂起、来电）时改按时钟写，拆信层随即停掉声音、藏起静音键。语音全部在内存里解码好才开口，放的过程中网络再卡也不会错开。
- 本地验收（真的对话模型和 Fish Audio，走本机代理）：5 块在点开 0.9 秒后排上音频时钟，信纸展开 1.2 秒开口，每块念时字往前走、块间停顿时字也停；静音键 `aria-pressed` 生效；收起后音频上下文关掉；拦下语音 404 时按每字 0.15 秒写、没有静音键。审查后把等待超时挪进 `LetterVoice.unlock`，这一处只跑了类型检查和单测，没有再走一遍浏览器。
- 留给真机验收：iPhone 打着静音拨片时 Web Audio 不出声（旧版 `<audio>` 不受拨片管），会看到字在写却听不到；好不好听、和字对得上对不上，留给用户在本机浏览器里听。
