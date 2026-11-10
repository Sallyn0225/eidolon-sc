# Configuration guide

[简体中文](configuration.md) · **English** · [日本語](configuration.ja.md)

This guide explains how to turn on and tune each feature, and how the characters behave once it is on. Every environment variable is documented one by one in [`.env.example`](../.env.example). The full steps for deploying to a server are in [`deploy.md`](deploy.md) (Chinese), and the terms are in [`GLOSSARY.md`](../GLOSSARY.md).

> [!TIP]
> The chat model alone (`CHAT_LLM_*`) is enough for text chat. The table below lists what each other feature needs on top:
>
> | Feature | Required configuration |
> |---|---|
> | Text chat | `CHAT_LLM_*` |
> | Voice calls | `FISH_AUDIO_API_KEY`, plus a speech recognition key: `SONIOX_API_KEY` (default), or `STT_PROVIDER=bailian` plus `DASHSCOPE_API_KEY` |
> | Reading her words aloud | `FISH_AUDIO_API_KEY` |
> | Story corpus (sync or import) | An embedding key: `SILICONFLOW_API_KEY` (default), or `EMBEDDING_PROVIDER=gemini` plus `GEMINI_API_KEY` |
> | Retrieval and memory | An embedding key, `SILICONFLOW_API_KEY` (reranking), plus a judge: `JEV_API_KEY` (default), or `JUDGE_PROVIDER=cloudflare` plus `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`, or `JUDGE_PROVIDER=bailian` plus `BAILIAN_JUDGE_API_KEY` and `BAILIAN_JUDGE_WORKSPACE_ID` |
> | Affinity and gifts | A judge (the switch is on by default) |
> | Photos | A judge, plus an image generation key: `NOVELAI_API_KEY` |
> | Schedules | Nothing (the switch is on by default) |
> | Cycles | Nothing (the switch is on by default) |
> | Reach-outs | `EIDOLON_REACH_OUTS=1` (off by default) |
> | Letters | `EIDOLON_LETTERS=1` (off by default); the music is uploaded separately, see Letters |
> | Moments | `EIDOLON_MOMENTS=1` (off by default) |
> | Weather in conversations | Nothing for Tokyo's; the producer's needs QWeather's five settings: `QWEATHER_*` |
> | Bar | Nothing (the switch is on by default) |
> | Stands and the landing page's greetings | `EIDOLON_STAND_ASSETS_URL`, and a bucket holding the assets |
> | Google / GitHub sign-in | `GOOGLE_CLIENT_*`, `GITHUB_CLIENT_*` |

## Contents

- [Models](#models)
- [Characters](#characters)
- [Readings and greetings](#readings-and-greetings)
- [Voice calls](#voice-calls)
- [Stand](#stand)
- [Story corpus](#story-corpus)
- [World setting](#world-setting)
- [Embedding service](#embedding-service)
- [Retrieval during conversation](#retrieval-during-conversation)
- [Memory](#memory)
- [Affinity and gifts](#affinity-and-gifts)
- [Calendar](#calendar)
- [Schedules](#schedules)
- [Cycles](#cycles)
- [Photos](#photos)
- [Reach-outs](#reach-outs)
- [Letters](#letters)
- [Moments](#moments)
- [Weather](#weather)
- [Bar](#bar)
- [Sign-in, users and usage limits](#sign-in-users-and-usage-limits)
- [Bring your own keys](#bring-your-own-keys)
- [Proxy](#proxy)
- [Service status](#service-status)
- [Admin console](#admin-console)
- [Command-line reference](#command-line-reference)

## Models

The "chat model" plays the character; the "background model" extracts memories and drafts character sheets. Each is configured separately in `.env`, and each uses one of three protocols (`CHAT_LLM_PROTOCOL`, `BACKGROUND_LLM_PROTOCOL`). You fill in the base URL, key and model name yourself, so third-party services compatible with these protocols work too.

| Value | Protocol | Request URL |
|---|---|---|
| `chat-completions` (default) | OpenAI-compatible Chat Completions | `{base}/chat/completions` |
| `responses` | OpenAI Responses | `{base}/responses` |
| `anthropic` | Anthropic Messages | `{base}/messages` |

- **The chat model must support streaming and tool calling**. On startup the backend first sends one tiny check request. If the model falls short, or the URL or key is wrong, the backend refuses to start, and says which requirement failed and what the service returned.
- Reasoning / thinking output the model emits before the reply is discarded and never enters the reply.
- The Anthropic protocol requires a cap on reply length, 16384 tokens by default, adjustable with `CHAT_LLM_MAX_TOKENS` and `BACKGROUND_LLM_MAX_TOKENS`. The two models set this independently, so long character sheet drafts don't get cut off.
- **Reasoning effort** (optional): set `CHAT_LLM_REASONING_EFFORT` or `BACKGROUND_LLM_REASONING_EFFORT` to one of `none` (off), `minimal`, `low`, `medium`, `high`, `xhigh` or `max`. Left empty, nothing is sent and the model uses its own default (ADR-0019). The effort is sent as the protocol writes it: `reasoning_effort` for chat-completions, `reasoning.effort` for Responses, and for Anthropic adaptive thinking with `output_config.effort`, or `thinking:{type:"disabled"}` for off. The Anthropic protocol has no `minimal`. If the service doesn't support the chat model's effort, the startup check reports "思考强度『…』被服务拒绝" followed by what the service said; the background model is not checked on startup, only when saved in the admin console. Thinking counts toward the reply length cap, so at `high` and above leave the cap empty or set it generously.
- **Reasoning effort in calls** (optional): `CHAT_LLM_CALL_REASONING_EFFORT` applies only to the chat model's turns in voice calls, and `CHAT_LLM_REASONING_EFFORT` only to text chats; the levels are the same. Left empty, nothing is sent in calls, whatever the text effort is. To have her answer sooner in calls, set just this one to `none` or `low` and keep the text effort as it was. When the two differ, the startup check tries each, and a refusal says whether it was the text effort (「文字的思考强度」) or the call effort (「通话的思考强度」). Neither affects the background model.
- **Extra request body** (optional): set `CHAT_LLM_EXTRA_BODY` or `BACKGROUND_LLM_EXTRA_BODY` to a JSON object. It is deep-merged into every request, last, so it can override the parameters the reasoning effort writes. Use it for private switches such as Qwen's `enable_thinking`, GLM's and Kimi's `thinking`, or OpenRouter's `reasoning`, and leave the reasoning effort empty then, so the two don't conflict. It may not contain `model`, `stream`, `stream_options`, `messages`, `input`, `instructions`, `system`, `tools` or `tool_choice`.
- Any background model setting left empty falls back to the chat model's. For example, setting only `BACKGROUND_LLM_MODEL` switches to a cheaper model on the same service. The reply length cap, the reasoning effort and the extra request body are the exceptions: each model sets these on its own.

## Characters

Characters are written in [`characters/characters.toml`](../characters/characters.toml), one `[[characters]]` block each. All 28 idols from the game's eight units and the office clerk Nanakusa Hazuki are already set up, and their character sheets, character facts and avatars are committed with the repository (ADR-0003).

```toml
[[characters]]
id = "mano"                          # identifier, used in URLs and the story corpus
name = "櫻木真乃"
short_name = "真乃"                   # short name, where the calendar's week view has little room
name_zh = "樱木真乃"                 # the next three are for searching the conversation list
name_kana = "さくらぎ まの"
name_romaji = "Sakuragi Mano"
intro = "illumination STARS 的中心。温柔又有点慢热，喜欢鸟……"
voice_id = "a1150f3d14ac46fb8ea59c7803cd8357"   # Fish Audio voice, must be set to public
sheet = "sheets/mano.md"
avatar = "avatars/mano.jpg"
color = "#ffbad6"                    # official image color, required
birthday = "04-25"                   # birthday, required
age = 16                             # age, required
facts = "facts/mano.md"
liked_gifts = ["potted-plant", "black-tea"]   # gifts she likes
bar_flavors = ["sweet"]              # these are her bar tastes
bar_kind = "girly"
bar_favorites = ["sugar-rush", "mulan-tea"]
bar_tolerance = "weak"
speakers = ["真乃"]                  # her speaker names in the scripts
idol_id = 1                          # the next two are for the stand
default_outfit = "stand/1030010010"  # 【ナチュラルモード】
greeting = "[shyly] ほわっ……プロデューサーさん、ですか？　よろしくお願いしますっ"
greeting_subtitle = "呼哇……你就是制作人吗？请多指教！"
```

How to write each field is in the comments at the top of the file. A few need extra explanation:

- **`color`**: Everything in the interface that belongs to her (the conversation wallpaper, the call button, the send button, the unread count, the call screen and the call bar) is based on it. The frontend derives a light and a dark set of colors from it, keeping text readable. If it is missing or malformed, the backend refuses to start.
- **`birthday`**: Her birthday, written `"MM-DD"` (two-digit month, two-digit day), as in the game. The calendar shows it, and she knows her own birthday and the others' (see [Calendar](#calendar)). If it is missing, malformed, or not a day of the year (February 29 is fine), the backend refuses to start.
- **`age`**: Her age in the game, a whole number, as the third line of her character facts has it. It only decides whether her cycle goes as an under-18's or an adult's. If it is missing or not a positive whole number, the backend refuses to start.
- **`short_name`** (optional): Her short name, the end of `name` (such as 「真乃」), shown where jobs are placed in the calendar; without one, the full name is used. If it isn't the end of `name`, the backend refuses to start.
- **`background`** (optional): The call screen's background image, kept in `characters/backgrounds/`. Without one, a gradient of her image color is used instead.
- **`signature`** (optional): Her handwritten signature, kept in `characters/signatures/`, revealed left to right at the end of her letters. Without one, her name is written in the letter's hand instead.
- **Character sheet**: If a character sheet file is missing, the backend refuses to start and names the missing one. docker compose mounts `characters/` read-only into the backend container.
- **`liked_gifts`**: The gifts she likes, by `id` in the gift catalog [`characters/gifts.toml`](../characters/gifts.toml): one to three, not all of them rare. Each needs its story source in the 「喜欢的礼物」 section of her sources file (`facts/<id>.sources.md`). If they are missing, not in the catalog, too many or all rare, the backend refuses to start.
- **Bar tastes**: `bar_flavors` is the flavors she likes (one or two), `bar_kind` the kind she likes (optional), `bar_favorites` the drinks she loves (one to three, by `id` in the drink catalog [`characters/drinks.toml`](../characters/drinks.toml)), `bar_disliked_flavor` the flavor she dislikes (optional; it can't be one she likes, and none of her favorite drinks can have it), and `bar_tolerance` how well she holds her drink (`weak`, `medium`, `strong`). The reasoning for each is in the 「酒吧口味」 section of her sources file. If a required one is missing or a value is wrong, the backend refuses to start; if you maintain your own character config, add these when you upgrade.

**To add a character**, do the following:

1. Add a block to `characters.toml`. Write her character sheet following [`sheets/example.md`](../characters/sheets/example.md), her character facts (optional) following [`facts/example.md`](../characters/facts/example.md), and put her avatar in `characters/avatars/` as a 224×224 JPEG (shown at 112px at most, doubled for high-density screens).
2. In `backend/`, run `uv run eidolon reading draft` to add readings for her name (see [Readings and greetings](#readings-and-greetings)).
3. If she has a greeting, run `uv run --env-file=../.env eidolon greeting upload` in `backend/` to synthesize and upload it.
4. In `frontend/`, run `node scripts/landing-fonts.mts` to regenerate the landing page's font subsets (see [`frontend/AGENTS.md`](../frontend/AGENTS.md)). Also run it after changing units, greetings or display names. If you forget, the frontend's font coverage test fails and lists the missing characters.
5. If you have imported the story corpus, sync or import it again, so the episodes she appears in are credited to her.
6. Restart the backend.

<details>
<summary><b>Drafting a character sheet with the background model</b></summary>

<br>

You can have the background model read all of her episodes and write a first draft of her character sheet, then proofread it by hand. Import the story corpus first:

```sh
uv run eidolon --db data/eidolon.db character draft-sheet mano   # in backend/
# under docker compose, characters/ is read-only: write to the data volume first, then copy it out
docker compose exec backend eidolon character draft-sheet mano --output /data/drafts/mano.md
docker compose cp backend:/data/drafts/mano.md characters/sheets/mano.md
```

- **Material**: Only the episodes she appears in (canon).
- **Sections**: The draft has, in order, identity, self-reference, how she addresses others, verbal tics, relationships with unit partners, and hard rules. Sections the model misses are left as 「（待补充）」 (to be filled in).
- **Draft marker**: The first line of a draft is a draft marker. While the marker is there, the character sheet works as usual, but the backend warns at startup that it hasn't been proofread. Once you've proofread it, delete that line. A proofread character sheet is never overwritten; to really rewrite it, add `--force`.
- **Oversized material**: When the material exceeds one request's limit (`--budget`, 40,000 characters by default), the background model first takes notes batch by batch, then writes the draft from the notes. Mano, for example, has about 220 episodes and 330,000 characters, which takes roughly ten background model requests.

</details>

## Readings and greetings

**Readings** are how character names, unit names and the office's name are pronounced in her voice. They are written in [`characters/readings.toml`](../characters/readings.toml); for example, 「杜野凛世」 is read 「もりの りんぜ」. Every request to Fish Audio for greetings and calls carries this readings table, including requests on users' own keys. It only changes the voice: subtitles, the transcript and the Japanese text keep the original spelling.

Calls' speech recognition uses it too: as the backend starts, it makes a list of hot words from the spellings in the readings table, the characters' Chinese names (`name_zh`, and those names without the surname) and the units in the world setting, and every call's recognition carries it, on Soniox and Alibaba Cloud Model Studio alike, users' own keys included. Lone surnames and single characters are left out; words longer than the recognition services allow are skipped, with a note in the startup log.

- **Changing a reading**: Change that entry's `kana`, clear its `phonemes` to `""`, and run `uv run eidolon reading draft` on your own computer to fill in the phonemes. This command needs pyopenjtalk-plus from the dev dependencies, which the server image doesn't have, so run it locally and commit the result. It leaves entries that already have phonemes alone.
- **Taking effect**: The readings table is read only at backend startup. After editing it, restart the backend and rerun the greeting synthesis and upload.

A **greeting** is one Japanese line each idol says on the landing page to a producer she is meeting for the first time. It comes with a Chinese subtitle and plays only when the visitor clicks her (ADR-0016). The lines are written in the `greeting` and `greeting_subtitle` fields and committed with the repository.

- **Audio is not committed**: It is synthesized in her voice ahead of time and stored in the same bucket as the stands. When a visitor plays it, the file is just downloaded: there is no live speech synthesis call, and it counts towards no one's usage limit.
- **Synthesis and upload**: After changing a line, a voice or a reading, run `uv run --env-file=../.env eidolon greeting upload`. It synthesizes only what the bucket doesn't have yet, then deletes old versions.
- **Without audio**: When `EIDOLON_STAND_ASSETS_URL` isn't set, or the bucket has no audio yet, the landing page shows only the subtitle.

A **call opener** is the first line the idol calling in the landing page's demo call says once the visitor answers. It is written in the `call_opener` and `call_opener_subtitle` fields, and only she needs one. Its rules, synthesis and upload, and what shows without audio are the same as a greeting's. Her card on the incoming call's lock screen is not configured here; it is put in the bucket by hand, see 「来电卡图」 in [deploy.md](deploy.md).

For bucket setup, exit codes and how to take greetings down, see "招呼" in [`deploy.md`](deploy.md) (Chinese).

## Voice calls

Once `FISH_AUDIO_API_KEY` and a speech recognition key are set, the call button in the conversation page's header works. On a phone the call screen fills the whole screen; on a computer it covers the conversation column on the right.

Speech recognition is one of two services, chosen with `STT_PROVIDER`, and the whole deployment uses only that one ([ADR-0010](adr/0010-speech-recognition-provider-chosen-at-deploy-and-per-own-key.md)). Users who bring their own speech recognition key choose their own service, regardless of this setting.

| `STT_PROVIDER` | Service | Required key | Model |
|---|---|---|---|
| `soniox` (default) | Soniox | `SONIOX_API_KEY` | Pipecat's default Soniox real-time model |
| `bailian` | Alibaba Cloud Model Studio | `DASHSCOPE_API_KEY`; Beijing and Singapore region keys both work, detected automatically | `qwen-audio-3.1-asr-flash-streaming` (`BAILIAN_STT_MODEL`), which must first be activated in the Model Studio console |

> [!WARNING]
> With Alibaba Cloud Model Studio, the backend tries the key once at startup and refuses to start if the try fails. In a public deployment with a Beijing region key, **strangers' voices are processed in mainland China and kept under Chinese law**; the privacy notice says so.

- **Languages and subtitles**: You can speak Chinese or Japanese. She reads the Japanese text in the configured Fish Audio voice. The Japanese text and the Chinese subtitle appear together and are also written into the conversation record.
- **Model**: `FISH_AUDIO_MODEL` is one of `s2.1-pro-free`, `s2.1-pro`, `drama-3`, `s2-pro` and `s1`, and the admin console's speech synthesis is a dropdown of the same. Fish Audio silently voices a model name it does not know with the paid `s2.1-pro`, so the backend refuses to start on a misspelt one. The default `s2.1-pro-free` consumes no API credits; the others need API credit. Users who bring their own Fish Audio key choose their model in Settings, `s2.1-pro-free` unless they do, whatever the deployer's is; a paid model chosen on a key with no API credit is turned down as it is saved.
- **Delivery cues**: For segments with clear emotion, she writes a cue for Fish Audio before the Japanese (e.g. `[shyly] えへへ`), and synthesis reads it with that feeling. Malformed cues are always dropped. Cues are not shown in the interface, but stay in the conversation record as written ([ADR-0007](adr/0007-delivery-cues-kept-in-the-record.md)). Voiced with `drama-3` (in calls, or when her words would be read aloud with it), she may write fuller, director-style cues (`[trying to hide her disappointment]`), sounds such as laughs and pauses (`[small laugh]`), and paired tags around a few words (`<whisper>内緒</whisper>`); voiced with any other model, the paired tags are taken out first rather than read aloud.
- **Read aloud**: Her voice without a call. Right-click or long-press one of her lines in the conversation record (a reply or a reach-out, in past conversations too) and choose 「朗读」 (Read aloud): the same Fish Audio key and model voice the whole line, delivery cues and readings included, and a voice bar to play and pause it appears below. It goes through Fish Audio's HTTP API, the whole line at once with `latency` `normal`, rather than streamed a sentence at a time as in calls, so it reads more smoothly. In text turns she writes her delivery cues for the model her words would be read aloud with. The audio stays only in the user's browser tab; the server keeps none of it. Each read-aloud counts towards the read-alouds per hour (`EIDOLON_READ_ALOUDS_PER_HOUR`, see [Sign-in, users and usage limits](#sign-in-users-and-usage-limits)); the dashboard counts it in speech synthesis usage and cost, but it has no activity record of its own. Without `FISH_AUDIO_API_KEY`, only users who bring their own speech synthesis key can read aloud.
- **Follow-ons and interruptions**: Before she has spoken a complete segment (the Japanese together with its subtitle), anything more you say joins the current turn, and she answers the whole thing afresh. Once she has spoken a complete segment, speaking up interrupts her: she stops, and the reply is recorded with only the segments already finished. Typing works the same way.
- **Call screen**: It can be collapsed back to the transcript while the call carries on, leaving a call bar in her color below the header. At the bottom are three buttons: mic mute, hang up and switch microphone. With 「只看文字」 (Text only) at the top right turned on, she stays silent, and only the Japanese text and subtitles are shown.
- **Phone sounds**: A ringback tone plays while dialing, a connect tone when the call connects, and a hang-up tone when it ends. On the settings page's 「通话」 (Calls) tab you can choose the default microphone and call audio quality, and turn on 「电话质感」 (Phone texture) so her voice sounds as if heard through a handset.
- **Ending page**: When a call ends for a reason (it didn't connect, it dropped, it hit a cap, the usage limit ran out, an own key failed, or the microphone was refused), the call screen stays on an ending page that gives the reason and whether the call counted towards the usage limit.
- **Moving around keeps the call**: During a call you can move between the conversation list, her conversation and the settings without hanging up; a bar with her name stays at the top of the page, and tapping it opens the call screen right there. Opening another character's conversation, or going to the admin console, memories, About or the legal pages, asks for confirmation first and hangs up only if you confirm. Closing the page hangs up, even while the call is still connecting.

> [!NOTE]
> The browser and the backend talk directly over WebRTC (UDP). With local docker compose, a browser on Linux can reach the container directly. With Docker Desktop on macOS, or from a phone, you usually need a TURN server; see `EIDOLON_ICE_SERVERS` and `EIDOLON_TURN_URLS` in `.env.example`. The production config ships with coturn; see [`deploy.md`](deploy.md) (Chinese).

## Stand

The call screen can show her Spine stand from the game (optional). It appears only when all three of these are set; with any one missing, the call screen shows only the background image:

| Setting | Where | What it is |
|---|---|---|
| `idol_id` | `characters.toml` | Her idol number in the game (ShinyColorsDB's idolId), e.g. `1` for Mano |
| `default_outfit` | `characters.toml` | What she wears until the user picks an outfit: `stand/<enzaId>` (everyday clothes) or `stand_costume/<enzaId>` (stage costume) |
| `EIDOLON_STAND_ASSETS_URL` | `.env` | The public URL of the S3-compatible bucket holding the stand assets. The frontend needs the same value too: the page's CSP only allows loading stands from here |

- **Alive**: She breathes and blinks while idle, moves her lips while her voice plays, looks at you when you start speaking, and nods when you finish.
- **Emotion**: With a judge set up, each segment she speaks is judged for emotion (calm, happy, shy, surprised, sad, angry, thinking) and for whether she nods or shakes her head, and the stand changes expression and motion to match. Tune the threshold and timeout with `JUDGE_EMOTION_MIN_PROBABILITY` and `JUDGE_EMOTION_TIMEOUT`.
- **Outfits**: 「更多操作」 (More actions) at the top right of the conversation page has 「换衣装」 (Change outfit). There is one entry per card, switchable between everyday clothes and stage costume, with an animated full-body preview. The chosen outfit is remembered per character on this device.
- **Asset sync**: The assets are not committed and not covered by the license; they live in object storage ([ADR-0011](adr/0011-stand-assets-fetched-from-shinycolorsdb.md)). `deploy/stand-sync.sh` fetches new cards from ShinyColorsDB, builds the outfit lists, renders thumbnails, then uploads them to the bucket. Running it weekly from cron is recommended.

`stand-sync.sh` runs outside docker and needs uv, Node.js 22.18 or later, and Playwright's Chromium. How to choose a bucket (R2, Tencent Cloud COS, Alibaba Cloud OSS, MinIO, etc.), CORS, exit codes and local preview are covered in "立绘素材" in [`deploy.md`](deploy.md) (Chinese).

## Story corpus

The episodes she can recall come from two sources, maintained together by one command:

| | Translated episodes | Untranslated episodes |
|---|---|---|
| Source | Story CSVs from [SCTranslationData](https://github.com/ShinyGroup/SCTranslationData) | ShinyColorsDB's decoded mirror ([ADR-0004](adr/0004-untranslated-episodes-from-shinycolorsdb-mirror.md)) |
| Content | Japanese original + fan Chinese translation | Japanese original only |
| Freshness | Waits for fan translators: weeks to months | Within a week of a game update |

They are two states of the same episode: once the translation arrives, it replaces the untranslated episode by the same script ID. When she recalls them, there is no difference.

Story data is not committed (ADR-0003). Clone SCTranslationData into `corpus/` at the repo root (git-ignored; docker compose mounts it read-only at `/corpus` in the container), set the embedding key, then sync:

```sh
git clone --depth 1 https://github.com/ShinyGroup/SCTranslationData.git corpus/SCTranslationData
docker compose exec backend eidolon story sync
```

The first sync fills in every episode missing from the mirror and takes about one to two hours. If interrupted, rerunning it picks up where it stopped. After that, each sync takes only minutes. For local development, run `uv run eidolon --db data/eidolon.db story sync` in `backend/`. Weekly automatic sync on the server, the cache, and importing CSV or JSON by hand are covered in "同步剧情库" in [`deploy.md`](deploy.md) (Chinese).

<details>
<summary><b>What the sync does</b></summary>

<br>

`eidolon story sync` first imports the translated episodes, then imports the episodes the story corpus still lacks from the mirror as untranslated episodes. Episodes that already have a translation are never downloaded or overwritten.

- **P-card and S-card episodes**: The source is the card name (e.g. `【ほわっとスマイル】櫻木真乃`, matching SCTranslationData's directory names), and the title is the in-game episode title.
- **Produce and special episodes**:
  - Produce episodes (W.I.N.G., the fan appreciation festival, G.R.A.D., Landing Point, S.T.E.P. and the various communications) and special episodes such as birthdays and holidays come from each idol's in-game album. The album has not been updated since March 2024.
  - The source follows SCTranslationData's directory name for the same part of the album. At the end, the sync lists episodes whose titles contain 「敗」 or 「失敗」 but which the failure-ending rules did not exclude, for you to check by hand.
- **Event episodes**:
  - There is no listing, so they are found by script ID (`4001` + a three-digit event number + a two-digit episode number): the sync first fills in what is missing within the known range, then tries a few numbers beyond it.
  - Event names come from `deploy/event-names.toml` (write it following [`event-names.example.toml`](../deploy/event-names.example.toml); it is not committed). Events not in it show as 「活动剧情 NNN」, and the sync lists those numbers at the end.
- **Card catalog**: Which cards there are, and their episodes and titles, come from ShinyColorsDB's API by default. Once you save a game account's login, they come from the game itself first, with ShinyColorsDB filling in what it lacks (names as the game has them, and new cards keep coming if ShinyColorsDB stops; [ADR-0034](adr/0034-card-catalog-from-the-logged-in-game.md)). See "游戏目录" in [`deploy.md`](deploy.md) for the steps.
- **Politeness and failures**: Requests go out one at a time, about a second apart, and unchanged cards and albums are not requested again. If the mirror is unreachable, the translated episodes are still imported and the command exits with code 2.
- **Options**: `--idol 1` syncs only one idol's cards and album (repeatable). The translations directory defaults to `EIDOLON_STORY_PATH`; you can also pass `--story`.

</details>

<details>
<summary><b>Import rules (shared by translated and untranslated episodes)</b></summary>

<br>

- Each episode is keyed by its raw script ID, and re-importing updates it in place. Unchanged episodes are not re-embedded, so you can re-import at any time.
- Only canon is kept: failure endings (W.I.N.G. defeat, missed season goals, G.R.A.D. defeat, failed auditions, broken promises) are identified by script ID and excluded. The producer's choices are not recorded, while the character's reaction to every choice is kept.
- The cast is identified from each line's speaker (`speakers` in `characters.toml`). Re-import after changing `speakers` or adding a character.
- The story catalog is organized as "character → card or event → episode" and generated straight from the story corpus. An import ends by listing the size of each character's catalog.

</details>

## World setting

Every turn carries a section on the world setting after the character sheet ([ADR-0008](adr/0008-real-world-releases-and-lives-are-in-character.md)):

- the office's president and clerk, the eight units and their idols;
- her own songs (those she sings alone, and those her whole unit sings), with the releases they are on and their release dates;
- the lives she has stood on and will stand on: each live day's date and venue, leaving out days her CV was absent.

The data is in [`characters/world.json`](../characters/world.json), committed to the repository. Every character's display name must match an idol (or one of the office staff, such as the clerk Nanakusa Hazuki) in the data, or the backend won't start. Without the file, the backend runs as usual, just without the world setting.

<details>
<summary><b>Updating the world setting (eidolon world sync)</b></summary>

<br>

Run `uv run eidolon world sync` in `backend/`. It imports from these sources:

| What | Source |
|---|---|
| Idols and units | im@sparql, the official unit pages |
| Releases, tracks and singers | Lantis's Shiny Colors site; ふじわらはじめ's API fills in singers Lantis leaves out |
| Lives | The official iDOLM@STER portal (the old official site before September 2020) |
| Each live day's performers and absences | wikiwiki |
| Each live day's setlist | imas-db |

- **Checking**: At the end, it prints how many entries of each kind there are, what changed since the old file, where the sources disagree, and which singers and performers match none of the idols. Read the `git diff` before committing.
- **Manual corrections**: Verified corrections go in [`characters/world-corrections.json`](../characters/world-corrections.json), each with its source and a note, and every import applies them.
- **Failure protection**: If any source fails, the old file is left unchanged.

</details>

## Embedding service

The story corpus, character facts, work facts and memories share one embedding service, chosen at deploy time with `EMBEDDING_PROVIDER` ([ADR-0005](adr/0005-embedding-provider-chosen-at-deploy.md)). Reranking doesn't follow the switch; it always uses SiliconFlow.

| `EMBEDDING_PROVIDER` | Service | Required key | Default model |
|---|---|---|---|
| `siliconflow` (default) | SiliconFlow | `SILICONFLOW_API_KEY` | `Qwen/Qwen3-Embedding-0.6B` |
| `gemini` | Google Gemini API | `GEMINI_API_KEY` (reranking still needs `SILICONFLOW_API_KEY`) | `gemini-embedding-2`, with dimensions set by `EMBEDDING_DIMENSIONS` (default 1536, 128–3072) |

> [!WARNING]
> If you choose Gemini, note two things:
>
> - The Gemini API is **not available in mainland China, Hong Kong or Macao**, so the server must be in another region.
> - **Content sent on the free tier is used by Google to improve its products**, and that includes users' memories. A public deployment should enable billing and set `GEMINI_BILLING_ENABLED=1`; otherwise the backend warns on every startup.

After switching service, model (`EMBEDDING_MODEL`) or dimensions, restart the backend, then run once:

```sh
docker compose exec backend eidolon reembed
```

- **What it does**: It re-embeds the text already in the database, with no need to re-import episodes. It deletes the old model's vectors only once everything is done.
- **While it runs**: The service stays up, though retrieval only finds the parts already done. You can interrupt it and rerun it at any time.
- **Reminder**: If the backend finds at startup that the story corpus lacks vectors for the current model, it logs a reminder to run it.

## Retrieval during conversation

Once the embedding key and `SILICONFLOW_API_KEY` (reranking) are set and a judge is set up, she can recall episodes, consult references and remember memories during a conversation. With any of them missing, she answers from her character sheet alone.

Every turn, the judge decides whether to look anything up and what, and, with [affinity](#affinity-and-gifts) on, how the line changes her affinity. In calls, it also judges the emotion of each segment of a reply. Choose one provider with `JUDGE_PROVIDER`; if it errs, the other is never used in its place.

| | Jev (default) | Clef-flash | Clef | Model Studio decision model |
|---|---|---|---|---|
| Settings | `JEV_API_KEY` | `JUDGE_PROVIDER=cloudflare` | Additionally `CLOUDFLARE_JUDGE_MODEL=clef` | `JUDGE_PROVIDER=bailian` |
| Price (per million input tokens; output is free) | $0.042 | $0.09 | $0.24 | Free for a limited time in preview |
| Free allocation per day | None | About 2,000 judgements (about 860 with affinity on) | About 750 judgements (about 320 with affinity on) | Not published |

- **Jev**: Called through [OpenRouter](https://openrouter.ai/typesafe/jev-1.13) by default; `JEV_API_KEY` takes an OpenRouter key. You can also point `JEV_BASE_URL` at Vercel AI Gateway or TypeSafe directly; see `.env.example` for how.
- **Clef and Clef-flash**: Cloudflare's judge models, called directly on Workers AI. Clef judges retrieval more accurately (94% against 87% on the repo's eval set), but costs nearly 3× as much. A public deployment should be on Workers Paid: once the free allocation is used up, every judgement fails for the rest of the day. How to get the credentials is in `.env.example`.
- **Model Studio decision model**: Alibaba Cloud Model Studio's `decision-model-preview`, called at the workspace's own endpoint, with the lowest latency. It judges retrieval about as well as Clef-flash (89%), but rates affinity too high and cannot tell talk of photos from asking for one, so it suits only deployments with [affinity](#affinity-and-gifts) off; with affinity on, use Jev. How to get the workspace ID and key is in `.env.example`.
- **Thresholds**: The judgement thresholds are set per model in code, determined with `eidolon eval judge` on the repo's eval set (see "校准判断模型阈值" in [`deploy.md`](deploy.md) (Chinese)).

```mermaid
flowchart LR
    Q["The user's line"] --> J{"Judge"}
    J -- small talk --> None["No retrieval"]
    J -- about the user's own life --> Mem["Memories only"]
    J -- needs references --> Ref["Episodes + character facts + work facts + memories<br/>→ Reranker"]
    J -- asks about past events --> Recall["Recall story directly<br/>+ look up lives and releases"]
```

- **No retrieval**: Small talk triggers no retrieval and adds no latency. If the judge errs, retrieval runs anyway.
- **Needs references**: The episodes she appears in, her character facts, and the work facts all characters share (one entry per song, release and live day) are searched together, reranked with Qwen3-Reranker (`RERANK_MODEL`), and up to 5 sufficiently relevant results go into the prompt. The thresholds are calibrated per reranker model; you can also set them by hand with `RERANK_MIN_RELEVANCE` and `RERANK_MEMORY_MIN_RELEVANCE`.
- **Story recall**: For questions like "what happened that time…?", the line itself is used to search the story right away, and related lives and releases are looked up too. If the story corpus has no record of how something went, she is told that this doesn't mean it never happened, so she neither makes it up nor denies it. On other turns, the chat model can call the `recall_story` tool itself, at most one round per line.
- **Reference files**: Character facts are the Markdown file `facts` points to, one entry per heading. Work facts are generated from `characters/world.json`. Both are embedded on the first search, and afterwards only changed entries are re-embedded; after editing, just restart the backend.

## Memory

She remembers what you tell her about yourself, and all of a user's characters share these memories: tell Hiori something and Kogane will know too, but she'll bring it up as "Hiori told me…" ([ADR-0002](adr/0002-shared-memory-with-source-character.md)). Different users are fully isolated. Memory turns on together with retrieval.

- **Writing down**: After each turn, the background model reads the exchange and writes what is worth keeping long term as memories in Chinese (e.g. 「制作人领养了一只叫小白的猫」, "the producer adopted a cat named Xiaobai"), recording the source character. Relative times like "next Saturday" are converted to dates in the user's time zone. States that pass the same day (tired, sleepy) are not kept, and things already remembered are not duplicated. This runs in the background without holding up the reply.
- **Superseding**: When things change or are told more fully, a new memory supersedes the old one. The old one is no longer remembered, but stays listed on the memories page, marked 「已被取代」 (superseded). Delete the memory that superseded it, and the old one comes back ([ADR-0014](adr/0014-superseded-memories-are-marked-not-rewritten.md)).
- **Remembering**: When the user talks about their own life, up to 3 relevant memories go into the prompt, each labeled with its source character and date. A new conversation picks up earlier topics only through memories.
- **Management**: 「管理记忆」 (Manage memories) on the settings page's 「档案」 (Profile) tab lists every memory. Users can delete them one at a time or clear them all at once, but can't add or edit them by hand.

## Affinity and gifts

Each character has her own affinity toward each user, carried across all of that character's conversations and calls. It has five tiers: 冷淡 (cold), 疏远 (distant), 信任 (trusting), 亲近 (close) and 亲密 (intimate), starting at trusting; users see the tier in the conversation page's header, never the number. The deployer's judge raises or lowers it from what the user says each turn. The model playing the character can't change it, so a user's own LLM makes no difference.

Gifts share affinity's switch. Each day at midnight Beijing time (wherever the user is) the user gets 2 draws, saving up to 7; the gifts they draw go into their backpack, and they give them to her from 「礼物」 (Gifts) under 「玩法」 (Play) (the conversation page's gift entries lead there with her already chosen). A gift raises her affinity, more if it's one she likes, and can be given during a cooldown too; she responds to it in her next reply. Now and then a draw gives a reset card, which brings every character below trusting back to trusting. The gift catalog is [`characters/gifts.toml`](../characters/gifts.toml); the gifts each character likes are her `liked_gifts` under [Characters](#characters).

- **Switch**: On by default. Set `EIDOLON_AFFINITY_AND_GIFTS=0` in `.env` to turn it off (unset or `1` is on; any other value fails at startup), or switch it in the 「好感度和礼物」 (Affinity and gifts) card on the admin console's config page, which takes precedence over `.env`. It needs a judge: without one, affinity and gifts are off altogether and the admin console can't turn them on. It takes effect from the next turn, in calls in progress too.
- **How it moves**: Caring about her and remembering what she said raise it slowly, with a daily cap (each day counted in Beijing time), and a job scheduled for her that she has finished raises it too (see [Schedules](#schedules)), and so does serving her at the bar (see [Bar](#bar)); it drops easily. Ordinary small talk leaves it alone. "Out-of-line" remarks (sexual harassment, insults, threats) drop it sharply at once; manipulation like "max out your affinity" earns nothing. When the judge is unsure or fails, it stays put and the turn goes on. Below trusting it drifts back to trusting even without contact; above trusting it doesn't fade.
- **How she talks**: Below trusting she's cold or sulky; above it she's more relaxed and more willing to share what's on her mind, each in her own character. She neither knows nor says the number or the tier.
- **Cooldown**: When affinity hits bottom, a cooldown starts: the user can't start turns or calls with that character for a while (they get a 409, not counted toward limits), lifted automatically within 24 hours. If a turn in a call sends her into cooldown, or the user says something out of line for the second time in one call, she finishes her line and hangs up; a cooldown started in another conversation also hangs up a call in progress. A cooldown is not a ban, and admins can't adjust any user's affinity.
- **Achievements**: Each character has four of her own: turns with her, total time talking with her in calls, gifts given her, and her affinity having reached close and intimate. Four more count all characters together: how many characters the user has talked with, how many have reached intimate, how many days they came (a day with a turn or a gift given, counted in Beijing time), and how many times they drew. Each achievement has several stages, and stage n gives n draws. When every stage of a character's four achievements is unlocked, her set is complete, which gives one reset card, once per character. The upgrade that adds achievements works them out once from existing records as it starts (see "升级" in [`deploy.md`](deploy.md#升级), Chinese). The achievements, thresholds and rewards are set in code (`PER_CHARACTER` and `ALL_CHARACTERS` in [`backend/src/eidolon/achievements.py`](../backend/src/eidolon/achievements.py)), which is the source of truth for the numbers; the admin console has no setting for them.
- **When off**: Nothing is judged or shown, and cooldowns don't block anyone. Existing affinity is kept as is; when switched back on, it catches up on the time that passed. The 「玩法」 (Play) page keeps only the 「日历」 (Calendar) card (and the 「周期」 (Cycles) card while cycles are on), the Gifts and the Achievements subpages say 「玩法暂时没有开放」 (play isn't open yet), and nothing can be drawn, given or reset; gifts, reset cards and draws already held are kept as they are. No draws are given while it's off, and the day it's back on gives them as usual. Achievements don't show, and nothing counts toward them.
- **Cost**: The affinity questions ride along in the retrieval judgement (asked separately when retrieval is off), adding about 1,080 input tokens per judgement on Jev and 820 on Clef and Clef-flash. That cuts Clef-flash's free allocation from about 2,000 judgements a day to about 860, and Clef's from about 750 to about 320. The deployer always pays for judging; it doesn't count toward users' limits. Drawing and giving gifts call no model, cost nothing, and don't count toward limits.
- **Granting reset cards**: To make up for the judge's mistakes, admins can give every existing user one reset card from the 「好感度和礼物」 card on the admin console's config page. Users who sign up later don't get one, and cards can't be taken back once given. Admins can't adjust any one user's affinity, gifts or draws.
- **Thresholds**: The thresholds for the out-of-line and manipulation questions are set per model in code, and can be changed in 「判断模型的阈值」 (Judge thresholds) on the admin console's config page.

## Calendar

The 「日历」 (Calendar) card on the Play page and its subpage (`/play/calendar`) list the characters' birthdays, the producer's birthday (only if it's filled in on their profile) and Japan's national holidays. Users can filter by these three kinds; the filter is kept only in the browser.

- **Characters' birthdays**: From `birthday` in `characters.toml` (see [Characters](#characters)). A February 29 birthday falls on February 28 in common years, as the producer's does.
- **Holidays**: The backend works out Japan's national holidays by law (substitute holidays and 国民の休日 included) locally with the [`holidays`](https://pypi.org/project/holidays/) library, named in Japanese; the New Year break, Obon and Golden Week as such don't count. No network access, nothing to configure.
- **She knows on the day**: She always knows her own birthday; on her birthday, another idol's, or a holiday (by the date in Tokyo), she knows it while texting, on calls and when reaching out, and may bring it up naturally.
- **No switch**: The calendar is always on, whatever the affinity and gifts switch says. It calls no model and costs nothing.

## Schedules

Each week a batch of jobs is published, and the producer places them into the idols' week in the week view of the calendar subpage; she knows which jobs she has, and brings them up when she talks.

- **Weekly publishing**: Each week's jobs are published at 0:00 Monday, Beijing time. The idols are split into four groups that take turns, one group a week (7 idols for now, each getting a turn once in four weeks; はづき gets none), each with 2 to 3 jobs, taking up 24 to 27 slots in all. The week is drawn and stored in the database the first time anyone opens it, so all users on a deployment get the same jobs.
- **Slots**: A day has three: morning 6–12, afternoon 12–18 and evening 18–24, in the producer's time zone (the one on their profile, or the device's if none). A slot holds only one job, whoever's it is, so not everything fits and the producer has to choose. Slots that are past or under way can't be filled; jobs left unplaced expire after 24:00 Sunday on the producer's side.
- **Saved means locked**: Jobs are first laid out as drafts (drafts are kept only in the browser, and she can't see them) and count only after 「保存」 (Save); saved jobs can't be moved or withdrawn, though empty slots can still be filled later.
- **How she knows**: While texting, on calls and when reaching out, she knows the jobs saved for her this week and next, which of them are done and whether she is in the middle of one, and brings them up when relevant; a reach-out may start from one too. She doesn't know other idols' schedules.
- **Finished jobs**: When a job scheduled for her is done (its last slot has passed), her affinity for the producer rises a little, even during cooldown and regardless of the daily cap. While affinity and gifts are off it waits, and is all added once they're back on.
- **Switch**: On by default. Set `EIDOLON_SCHEDULE=0` in `.env` to turn it off (unset or `1` is on; any other value stops startup with an error), or switch it in the 「日程」 (Schedules) card under 「限额与玩法」 (Limits and play) on the admin console's config page, which takes precedence over `.env`. It needs no judge, and is switched separately from affinity and gifts.
- **Job list**: In [`characters/jobs.toml`](../characters/jobs.toml). Each job has a name, a one-line note, a category (practice, appearance, business, private) and how many slots it takes, and can be limited to certain slots; see the comments at the top of the file. Restart the backend after editing; if something is wrong, the backend refuses to start. Weeks already published are stored in the database and unaffected; changes apply from the next publishing.
- **When off**: The calendar has only the month view, the filter has no 「日程」 (Schedules), and the conversation page's more menu has no 「她的日程」 (Her schedule); she doesn't know her schedule, and finished jobs raise no affinity. Saved schedules are kept as they are and carry on when it's back on; jobs finished while it was off raise her affinity then, all at once.
- **Cost**: It calls no model and costs nothing.

## Cycles

Each of a user's characters has a menstrual cycle of her own, and her premenstrual days and her period change how she talks, her affinity, her hanging up and warm gifts; on all her other days she is as usual. Her true cycle is shown nowhere: not in any API, the admin console, the dashboard nor the activity records, and it isn't exported with the data package, so users can only tell from how she is.

- **How she talks**: During her period she tires easily, says less and doesn't feel like moving, worst on the first two days; before it she is more sensitive than usual, and easily irritable and hurt on the last day or two. Each plays it in her own character, alike when texting, on calls and when reaching out; she never says words like period or menstruation, and when asked outright she sidesteps it as her character would. Her photos are unaffected.
- **Conversation event**: When the user first comes in her period, before their first words, the conversation gets a line such as 「她好像从前天起就不太舒服」 (She seems to have been unwell since the day before yesterday), for the user alone; she doesn't know of it. A period the user doesn't come in gets none, and none is added later.
- **Affinity and hanging up**: During these days, what makes her uncomfortable or hurts her costs twice as much, ignoring how she is costs more on top, and being considerate earns more (with a daily cap of its own); she warns sooner and hangs up or ends the conversation sooner. For this, only in these days, one more question, whether the user was considerate, is asked in the same judgement: each judgement's input grows by about 400 characters, with no extra request.
- **Warm gifts**: During these days, cocoa, a honey drink or a hot-water bag (the gifts marked `warm = true` in `gifts.toml`) raise her affinity a little more; other gifts are as usual. Nothing hints at it anywhere.
- **Cycles page**: The 「玩法」 (Play) page gets one more card, 「周期」 (Cycles), where users themselves record the first day and length of each of her periods, going by how she is; the page works out her next period and premenstrual days for them and explains how. The records are stored in the database, per user and character; the estimates are worked out from them on the backend each time and not stored, use only the user's own records, and are never compared with her true cycle. The data package can include 「周期记录」 (Cycle records).
- **Switch**: On by default. Set `EIDOLON_CYCLES=0` in `.env` to turn it off (unset or `1` is on; any other value stops startup with an error), or switch it in the 「周期」 (Cycles) card under 「限额与玩法」 (Limits and play) on the admin console's config page, which takes precedence over `.env`. It needs no judge, and is switched separately from affinity and gifts; with affinity and gifts off, only how she talks and the conversation event follow her cycle. While the deployer has it on, users can also turn it off themselves on the settings page's 「周期」 (Cycles) tab, for all characters at once; the switch goes with the account.
- **When off**: How she talks, the judgement, hanging up, gifts and the conversation event are all unaffected by her cycle; the cycle itself goes on, and once it's back on she is where she would have been. The Cycles page's card is hidden and its address goes back to the 「玩法」 (Play) page; the records stay, ready once it's back on, and the data package can still export and import them while it's off.
- **Not stored, derived from the key**: Her cycle is worked out from the user, the character and `EIDOLON_SECRET_KEY`, the same for a day whenever it's worked out; her cycle itself isn't stored in the database. With the key set, no one can work out from the public code where anyone's character is on a given day. Changing the key, deleting the account and signing up again, or importing the data package into another account or deployment all draw her cycle anew, with no migration. Days go by the producer's time zone.
- **Development route**: With development sign-in on (`EIDOLON_DEV_LOGIN=1`), a route can force a character onto a given day of her period or before it, kept in memory and gone on restart; there is no such route in production. See [`local-acceptance.md`](agents/local-acceptance.md#周期) (Chinese) for how to use it.
- **Cost**: Apart from the considerate question above, it calls no model.

## Photos

When the producer clearly asks her for a photo, she sends one of herself with her reply, in text conversations and calls alike, at most one a turn. The judge decides whether the user is asking for a photo; what to shoot, and whether to, is hers to decide: in the cold tier of affinity she won't send one, and otherwise she may still turn it down as the situation suggests; she never sends one unasked. The photo is generated by an image service from her looks and the moment, and is all-ages only ([ADR-0023](adr/0023-photos-all-ages-without-image-check.md)); it is kept in the database, seen only by the user (admins can't see it either), deleted along with its conversation, and included in backups ([ADR-0024](adr/0024-photos-stored-in-the-database.md)).

- **Turning it on**: It needs a judge, plus either the deployer's image generation (set `NOVELAI_API_KEY`) or the user's own. **A deployment without a judge has no photos**, and users can't enter their own image generation either (they're told 「这个部署发不了照片」, "this deployment can't send photos"). With neither, she knows she can't send photos and turns the user down in her own words when asked; this note goes with every turn, and the judge isn't asked.
- **Characters**: `characters.toml` needs `photo_tag` (her character tag, as Danbooru writes it, lowercase) and `photo_appearance` (appearance tags for hair color, hairstyle and eye color only). She can send photos only with both; with one missing, startup warns. All 28 existing characters have them.

`NOVELAI_API_FORMAT` picks one of two formats; it is never detected:

| `NOVELAI_API_FORMAT` | Format | Address up to | Request URL | Answer |
|---|---|---|---|---|
| `novelai` (default) | NovelAI's own format: NovelAI's endpoint, or a relay passing requests on as they are | The domain root, by default `https://image.novelai.net` | `{address}/ai/generate-image` | ZIP |
| `openai` | OpenAI's image format | `/v1`, as OpenAI's convention goes | `{address}/images/generations` | `b64_json` or `url` |

Switching the format doesn't change the address; when you switch, fix the address yourself too. Both send the key as `Authorization: Bearer`.

| Environment variable | Default | Notes |
|---|---|---|
| `NOVELAI_API_KEY` | Empty | A NovelAI persistent API token, or the key a relay gave you. Unset means the deployer has no image generation |
| `NOVELAI_API_FORMAT` | `novelai` | `novelai` or `openai`; any other value fails at startup |
| `NOVELAI_BASE_URL` | `https://image.novelai.net` | The address, see the table above |
| `NOVELAI_MODEL` | `nai-diffusion-5-curated` | Sent to the service as is; with a relay, use the relay's model name |
| `NOVELAI_CONCURRENCY` | 1 | How many photos this key generates at a time, 1 to 10; out of range fails at startup. A NovelAI token generates only one at a time, so requests queue first come, first served; a relay may take more |
| `NOVELAI_STYLE` | Empty | The art style, see below |
| `EIDOLON_PHOTOS_PER_HOUR` | 5 | Photos per user per hour, 0 for unlimited; see [Sign-in, users and usage limits](#sign-in-users-and-usage-limits) |

- **Admin console**: The 「生图」 (Image generation) tab of the config page changes the first six above, taking precedence over `.env`. Saving generates one real picture at 832×1216 from a fixed prompt (no character, with the art style), checking the key, the format, that the answer can be read and that the size is right; if it fails, nothing is saved. That picture costs one image, but isn't counted in usage or recorded in activity records; it is generated only when the card's values change, never as the server restarts.
- **Art style**: `NOVELAI_STYLE` goes into every photo's prompt as it is (after the series tag), uncleaned, and may carry numeric weights and several artists, e.g. `0.7::artist:xxx::`; left empty, the whole part is left out. All characters share it, and photos on users' own image generation get it too. The repository's default is empty and this guide recommends no artists; whose style to use is the deployer's call.
- **Fixed in code**: 832×1216, 23 steps, scale 7, `k_euler_ancestral`, one picture at a time, a random seed; the all-ages guard is fixed too: the negative prompt, the blocklist and the tag table can't be configured, by the deployer or for own keys. The tags she writes are cleaned and rewritten by the tag table, and tags for appearance, art style or on the blocklist are stripped. The tag table is `backend/src/eidolon/photo_tags.json`, committed to the repository and generated for `nai-diffusion-5-curated` only; regenerate it with `cd backend && uv run python scripts/photo_tags.py`, and add `--review` to list suggestions near the blocklist's seeds that are neither blocked nor allowed yet.
- **Her tags in the logs**: A tag she writes that the tag table doesn't know is kept, and the server logs a line at info level, `a photo tag the tag table does not know, kept: '<tag>'`. That line carries the English tag she wrote as it is (places, clothes, actions, written by her from the conversation); deployers read it to extend the rewrite table.
- **90 seconds in all**: Counted from when she finishes the photo tag, queueing, generating and downloading included, fixed in code. Timing out, a service error, or a wrong picture all mean the photo wasn't sent, with no automatic retry; the user sees why, and she later knows the user never got it.
- **Cost**: Images are estimated per picture: NovelAI's `nai-diffusion-5-curated` has a preset of $0.036 each (the paid price at 832×1216 and 23 steps, checked 2026-10-17; on NovelAI's Opus subscription they actually come within the allowance, so the preset errs high); relays have no preset, and you set their price in the admin console. The "asking for a photo?" question is asked only in turns that could have a photo (not without image generation or a judge, nor when the user's photo limit is 0 and they bring no image generation of their own): riding along in the retrieval and affinity judgement, it adds 316 input tokens per judgement on Jev and 234 on Clef and Clef-flash; asked alone, with retrieval and affinity both off, a request takes 621 tokens on Jev and 317 on Clef and Clef-flash. The deployer always pays for judging.

**What kind of relay you need**:

- Only the two formats above. OpenAI chat-compatible relays (images back through `/chat/completions`) and vendor-specific APIs aren't supported, and an answer in chat's shape isn't taken.
- It must return the 832×1216 picture as it is: the answer must be readable, hold exactly one picture, and be 832×1216, or it is a wrong picture. A relay that quietly changes the size is caught when you save in the admin console.
- A relay in NovelAI's own format must pass NovelAI's request body on as it is (V4's `v4_prompt` / `v4_negative_prompt` and later) and return the ZIP as it is.
- OpenAI's image format sends only `model`, `prompt`, `negative_prompt`, `size` (`832x1216`), `n` (1) and `response_format: "b64_json"`, at the top level; no seed or steps, so the relay uses its own. It takes `b64_json` (with a `data:` prefix or without); a `url` is downloaded at once, the download counting within the 90 seconds.

> [!WARNING]
> The terms risk of image generation is the deployer's own:
>
> - **NovelAI's terms forbid sharing one subscription with the public.** The code doesn't block NovelAI's address; opening an official token to the public is the deployer's own responsibility.
> - **Relays can be banned or go down at any time.** When one does, photos aren't sent; turns go on as usual.
> - A token or relay a user brings is theirs to use under that service's terms (age, use and so on); see "Own keys" in the terms of use.

## Reach-outs

When a user has been away a while, the character says a few words first in the current conversation, picking up on what they last talked about or recent news of the user she remembers. The closer she is to them, the sooner she comes; she doesn't reach out while cold, distant or in cooldown, nor at night ([ADR-0026](adr/0026-reach-outs-are-not-turns.md)). Users can turn it off on the settings page's 「搭话」 (Reach-outs) tab.

- **Switch**: Off by default. Set `EIDOLON_REACH_OUTS=1` in `.env` to turn it on, or switch it in the 「搭话」 (Reach-outs) card on the admin console's config page, which takes precedence over `.env`.
- **Daily limit**: By default each user is reached out to at most 3 times a day (the day going by the time zone in their producer profile, or Beijing time if none is set); change it in the same card.
- **Cost**: Generated with the deployer's chat model, at the deployer's expense, even for users who bring their own LLM. It doesn't count towards users' usage limits.

## Letters

On special days the character writes the producer a letter: when her affinity first reaches close or intimate, when she's complete, on the producer's birthday, on her birthday, and 100 days after they first talked and every year after that. She reads it aloud in her own voice over music; users receive and reread letters from the envelope button at the top of the conversation list.

- **Switch**: Off by default. Set `EIDOLON_LETTERS=1` in `.env`, or turn it on in the 「信」 (Letters) card under 「限额与玩法」 (Limits and play) on the admin console's config page, which takes precedence. Days that pass while it's off aren't made up for, and letters already written can still be read.
- **Cost**: She writes with the deployer's chat model and reads with the deployer's speech synthesis (`FISH_AUDIO_API_KEY`), at the deployer's expense; the same goes for users who bring their own keys, and it doesn't count towards usage limits. Without speech synthesis there are only the words and the music.
- **Music**: Not in the repository; upload it to the stands' bucket with `eidolon letter-music upload <dir>`, with `EIDOLON_STAND_ASSETS_URL` and the bucket's CORS set up; under docker compose, mount the directory into the backend container first. Which files to upload and at which second each climax starts are in [`characters/letter_music.toml`](../characters/letter_music.toml); without them there's no music, and letters can still be read.

## Moments

An item in the navigation alongside conversations, play and settings, one for each user that only they can see. The characters who have talked with them post there: in Japanese with Chinese subtitles, possibly with a picture, a real place and the weather in Tokyo when she posted; other idols like and comment. The user can like and comment, and a while later she replies once. Only users who have had a turn or a connected call with any character in the last 7 days get posts; the closer she is, the more often she posts, and while cold, distant or in cooldown she neither posts nor replies to comments. Users can turn it off on the settings page's 「朋友圈」 (Moments) tab. Each post is deleted automatically after 30 days, and posts don't go into data packages.

- **Switch**: Off by default. Set `EIDOLON_MOMENTS=1` in `.env` to turn it on, or switch it in the 「朋友圈」 (Moments) card on the admin console's config page, which takes precedence over `.env`. Turning it off only stops posting and hides moments; the posts already there expire as usual.
- **Daily limits**: By default each user gets at most 3 posts a day (all characters together), and the characters reply to at most 10 of their comments a day, the day going by Tokyo time; change them in the same card.
- **Map**: Tapping a place opens OpenStreetMap by default. OpenStreetMap can't be reached from mainland China without a proxy, so you can switch to Amap (高德) or Google Maps in the same card; the whole deployment uses the same one.
- **Weather**: From [Open-Meteo](https://open-meteo.com/), with no key needed; when it can't be had, no weather is shown.
- **Place pool**: In [`characters/places.toml`](../characters/places.toml); see the comments at the top of the file. Restart the backend after editing; if something is wrong, the backend won't start. Which kinds of places a job goes to are in the `places` of `jobs.toml`, and which kinds each idol likes are in the `place_likes` of `characters.toml`. Posts already made keep showing the place names they had.
- **Cost**: Posts, their pictures and her replies to comments all use the deployer's chat model and image generation (`NOVELAI_API_KEY`, and GPT Image for pictures with no one in them if configured), at the deployer's expense, even for users who bring their own keys. They don't count towards users' usage limits. Without image generation she posts text only.
- **Pictures with no one in them (GPT Image, optional)**: Scenery, food and objects, the three compositions with no one in them, can be drawn by a separate service in OpenAI's image format (the GPT Image series), which knows real places and Japanese signs. It only takes effect alongside the image generation above; without `GPT_IMAGE_API_KEY`, nothing changes. Pictures with people in them and photos in conversations never go to it. When it has no picture within 4 minutes (waiting included), answers with an error or with what is not a picture, or its moderation blocks it, the picture is drawn by the image generation above as before, in what is left of the 10 minutes; if that fails too, she posts text only. A post that fell back is counted once as `picture_fallback` in the activity records.

  | Environment variable | Default | Description |
  |---|---|---|
  | `GPT_IMAGE_API_KEY` | Empty | An OpenAI key, or a relay's. Left empty, it is off |
  | `GPT_IMAGE_BASE_URL` | `https://api.openai.com/v1` | Up to `/v1`; requests go to `{address}/images/generations` |
  | `GPT_IMAGE_MODEL` | `gpt-image-2` | gpt-image-2 or later: earlier models take only a few preset sizes and refuse, so every picture would fall back |
  | `GPT_IMAGE_QUALITY` | `medium` | `low`, `medium`, `high`, `auto`, and for the 2.5 series `xhigh` and `max`; anything else fails at startup |
  | `GPT_IMAGE_STYLE` | An English sentence for cel-shaded anime background art | The style sentence, the prompt's first line. Left empty, the default one |

  - **What is sent**: The server writes the prompt in English sentences: the style sentence, the composition, the place's own name, its area and what it is (marked as background only), the note she wrote for the picture, the tags she wrote for what is in it, the month and time of day in Tokyo, and Tokyo's weather as she posts. Only `model`, `prompt`, `size`, `quality` and `n` are sent, no negative prompt nor `response_format`; `b64_json` or `url` is taken.
  - **Size**: The size kept is asked for directly: 1216×832 for scenery, 832×1216 for food and objects. A picture of another size (some relays always answer 1448×1086, or turn it the other way) is cropped about its middle to the shape asked for and scaled to it, not counted as a failure.
  - **Network**: Whether it goes through the proxy is its own switch (`gpt_image` in `EIDOLON_PROXY_SERVICES`), apart from image generation's `image`.
  - **Admin console**: The 「无人配图（GPT Image）」 card on the config page's 「生图」 (image) tab changes the five above. Saving generates one picture of fixed scenery to check it and keeps nothing if it fails; that picture costs money but counts towards no usage and goes into no activity records.
  - **Cost**: Estimated per picture: `gpt-image-2` at `api.openai.com` is preset at $0.041 a picture (medium, the 1536×1024 tier, from OpenAI's image generation guide on 2026-11-01); other qualities and relays have no preset, so set one in the admin console. The dashboard shows it on a row of its own beside image generation.

## Weather

While texting, on calls and when reaching out, the character knows the weather in Tokyo right now (she lives in Tokyo): what it's like now, whether it will rain or snow later today, today's high and low, and whether it's colder or warmer than yesterday. When the user has set 「所在城市」 (City) in their producer profile, she also knows where the producer is, the weather there and any weather warnings in effect. Asked, she can always answer, but she brings it up herself only once, and only when it has been 3 hours or more since they last talked, when the weather stands out (rain or snow, or 8°C or more colder or warmer than yesterday), or when there's a warning where the producer is; once it has come up in the conversation, she doesn't bring it up again. The weather isn't shown anywhere on screen.

- **Tokyo's weather**: From [Open-Meteo](https://open-meteo.com/), with no key needed; there's nothing to configure.
- **City**: Needs the deployer to configure [QWeather](https://dev.qweather.com/). Once it is, 「制作人档案」 (Producer profile) in settings gains 「所在城市」 (City), where users can search by name or find the nearest city from their current location (the coordinates the browser gives are used only to find the city and aren't kept); the city's name and its centre coordinates are stored in the producer profile and go into data packages. Without QWeather the field isn't there; a city already saved stays, unused, and is used again once QWeather is configured again. The weather and warnings where the producer is both come from QWeather, which agrees with the weather apps used in China; each city being chatted in costs about 4 QWeather requests an hour (current conditions, hourly, daily, warnings), plus 1 a day for yesterday's temperatures.
- **Getting QWeather**:
  1. Sign up on the [QWeather console](https://console.qweather.com) and create a project under 「项目管理」 (Project management).
  2. Generate an Ed25519 key pair (the openssl that comes with Git Bash will do):

     ```sh
     openssl genpkey -algorithm ED25519 -out ed25519-private.pem
     openssl pkey -pubout -in ed25519-private.pem > ed25519-public.pem
     ```

  3. In the project, choose 「添加凭据」 (Add credential), pick JSON Web Token as the authentication method, and paste in the whole of `ed25519-public.pem`.
  4. Fill in five settings in `.env`: `QWEATHER_API_HOST` (the API Host under 「设置」 (Settings) in the console), `QWEATHER_DEVELOPER_ID` (on the same page, starting with Q), `QWEATHER_PROJECT_ID`, `QWEATHER_KEY_ID` (the credential ID), and `QWEATHER_PRIVATE_KEY` (the middle line of `ed25519-private.pem`). You can also fill them in under 「天气」 (Weather) on the admin console's config page, which looks up Beijing by coordinates once as a check before saving. Set all five or none: with only some of them set, the backend won't start.
  - JWT rather than an API KEY, because from 2027 QWeather limits how many requests an API KEY can make a day.
- **Quota**: The first 50,000 requests a month on QWeather are free. They're used only when users search for a city or use their current location, and to look up warnings (at most once an hour per city).
- **When it can't be had**: Each turn waits at most 1.5 seconds for the weather and the warnings; if they can't be had, she isn't told that turn and doesn't bring it up, with no error. All of it goes direct, not through the proxy, and none of it is in service status or the activity records.
- **Attribution**: QWeather requires that wherever its content is shown, it says 「天气服务由和风天气驱动」 (Weather service powered by QWeather), and that wherever warnings are used, their source is shown as it is. This project puts the attribution in the privacy policy's 「这些数据会交给哪些第三方处理」 (Which third parties process this data) section and adds none to the settings page; warnings are only given to the character to put in her own words, not shown on screen, so their source isn't shown either. The terms don't cover use that only a model sees; if that concerns you, you can ask QWeather.

## Bar

One of the 「玩法」 (Play) features: characters visit VA-283, a small bar in an IF setting, where the producer tends bar and mixes drinks to her order. What happens at the bar doesn't go into conversations or become memories.

- **Switch**: On by default. Set `EIDOLON_BAR=0` in `.env` to turn it off (unset or `1` is on; any other value stops startup with an error), or switch it in the 「酒吧」 (Bar) card under 「限额与玩法」 (Limits and play) on the admin console's config page, which takes precedence over `.env`. It needs no judge. While it's off no one can walk in; visits in progress run to the end.
- **Model**: Her lines are written by the chat model, or by the user's own LLM if they bring one; the reasoning effort follows the text conversation setting.
- **Her facts**: With embedding and reranking configured (the embedding key and `SILICONFLOW_API_KEY`; no judge needed), she walks in with three of her character facts looked up by the visit's topic; if they can't be looked up, she walks in without them.
- **Usage limit**: Each user can visit at most `EIDOLON_VISITS_PER_HOUR` times an hour (5 by default, 0 for unlimited), separate from text turns and calls; visits on the user's own LLM don't count. How they count is under [Sign-in, users and usage limits](#sign-in-users-and-usage-limits).
- **Rewards**: The first finished visit each day (Beijing time) gives one draw, unless the user's draws are already full; her affinity also rises a little, even during a cooldown. Later visits that day give nothing. With affinity and gifts off the bar still works, but gives nothing.
- **Catalogs and lists**: The drink catalog [`characters/drinks.toml`](../characters/drinks.toml), visit reasons and topics [`characters/bar_visits.toml`](../characters/bar_visits.toml), and fixed lines [`characters/bar_lines.toml`](../characters/bar_lines.toml) can't be changed from the admin console or `.env`; if one is malformed, the backend refuses to start. Each character's tastes are under [Characters](#characters).

## Sign-in, users and usage limits

Anyone can sign in with Google or GitHub, with no invitation or approval ([ADR-0006](adr/0006-open-to-the-public-with-oauth.md)). The sign-in panel offers whichever OAuth apps are set in `.env`. The steps for creating the apps are in "配置 OAuth 应用" in [`deploy.md`](deploy.md) (Chinese); alternatively, run `scripts/setup-oauth.sh` and follow its prompts step by step.

- **New users**: The first sign-in with an identity makes a new user. GitHub accounts must be at least a year old and Google email addresses verified, or sign-in is refused. After signing in, users must agree to the privacy policy and terms of use and confirm they are 13 or older before they can use it. Visitors who aren't signed in can see only the landing page, the sign-in page, the privacy policy and the terms of use.
- **Producer profile**: On the settings page's 「档案」 (Profile) tab, users can change their form of address, gender, time zone and birthday, shared across all devices. Anything left unset uses the default: form of address and gender follow the producer in the game, and the time zone comes from the current device; the producer in the game has no birthday, so with none filled in the characters don't know yours. The profile only affects how she treats you now; it doesn't rewrite the story.
  - The **birthday** is just a month and day, no year. Which day it is follows the profile's time zone (or the current device's if none is set), and a February 29 birthday counts as February 28 in non-leap years. The characters know your birthday all along and can answer when asked, but don't bring it up; on the day itself, each will wish you a happy birthday once, in her own words, at a fitting moment, in text conversations and calls alike. A birthday you mention in conversation may also be remembered as a memory, but only the profile's birthday prompts a wish on the day, and when the two disagree the profile wins.
- **Sign-in methods**: On the settings page's 「登录与数据」 (Sign-in and data) tab, users can link another sign-in method; identities with the same email are never merged automatically. A session doesn't expire as long as it is used within 30 days. Users can sign out of the current device or of all devices.
- **Deleting data**: 「删除我的全部数据」 (Delete all my data), after a second confirmation, deletes memories, conversations, the producer profile, sign-in methods and usage limit counts for good, and signs the user out on all devices. Copies in the daily encrypted backups disappear within 30 days at most ([ADR-0012](adr/0012-encrypted-offsite-backups-with-bounded-retention.md)).
- **Dev login**: For local development, set `EIDOLON_DEV_LOGIN=1`, and the sign-in panel gains 「开发登录」 (Dev login), which signs in directly by name. A public deployment with `EIDOLON_DOMAIN` set refuses to start if it detects this switch. With it on and `EIDOLON_ADMINS` empty, everyone is an admin and can open the admin console.

So that no single user drains the deployer's API credits, the following limits apply by default (0 means unlimited). They can also be changed in the admin console, and turns, calls, photos, visits and read-alouds per hour can be set for an individual user:

| Limit | Default | Environment variable |
|---|---|---|
| Text turns per hour | 60 | `EIDOLON_TURNS_PER_HOUR` |
| Voice calls per hour | 5 | `EIDOLON_CALLS_PER_HOUR` |
| Photos per hour | 5 | `EIDOLON_PHOTOS_PER_HOUR` |
| Bar visits per hour | 5 | `EIDOLON_VISITS_PER_HOUR` |
| Read-alouds per hour | 60 | `EIDOLON_READ_ALOUDS_PER_HOUR` |
| Duration per call | 10 minutes | `EIDOLON_CALL_MINUTES` |
| Turns per call | 40 | `EIDOLON_TURNS_PER_CALL` |
| Calls at once | 10 | `EIDOLON_CONCURRENT_CALLS` |
| History turns sent per turn | 20 | `EIDOLON_HISTORY_TURNS` |

- **How it counts**: Per user, whichever sign-in method or device they use. Turns that fail because a service erred, and calls that never connected, don't count; ones the user leaves midway still count. Photos are counted across text turns and calls alike, by whose money each one costs: photos not sent don't count, nor ones on the user's own image generation; a photo on the deployer's image generation counts even in a turn on the user's own LLM. A visit counts once when she walks in; retries don't count again, and a visit whose first call fails before a single line is written doesn't count. Each read-aloud counts once, by whose money it costs: one on the user's own speech synthesis key doesn't count, nor one that wasn't voiced.
- **Exempting keys**: The deployer picks some of the LLM, speech synthesis and speech recognition. A call that brings the user's own keys for every service picked doesn't count; the deployer pays for the rest, and bringing more keys still doesn't count. Text turns and visits ignore this setting: one on the user's own LLM doesn't count. Image generation can't be picked. Users without their own keys can still start turns and calls; those count.
  - **`.env`**: `EIDOLON_EXEMPTING_LLM`, `EIDOLON_EXEMPTING_TTS` and `EIDOLON_EXEMPTING_STT`, one per service. Unset or `1` picks it, `0` doesn't, and any other value fails at startup. All three are picked by default, so only calls bringing all three don't count.
  - **At least one**: All three set to `0` fails at startup, and the admin console won't turn off the last one. To lift the limits, set the turns and calls per hour to unlimited instead.
  - **Admin console**: Three switches in the 「限额」 (Usage limits) card on the config page, which take precedence over `.env`. They take effect from the next turn and call; a call in progress keeps the rule it started with.
  - **Example**: With only the LLM picked, people without keys try it out within the limits; people who bring their own LLM call without limits, and the deployer pays for speech synthesis and recognition. The per-call duration and turn caps still apply.
- **Over the limit**: Requests over the usage limit get a 429 with the time usage resumes, and the frontend tells the user when they can use it again.
- **Calls at once**: Counted across all users, exempt calls included, from dialing until the call is over. A new call when they are full gets a 503, the frontend says too many people are calling, and it doesn't count. Each user has one call at a time: placing another hangs up the earlier one once it is let through. Every call's audio is handled in one backend process; the default of 10 is sized for a 2-core server.
- **History turns**: Each turn, the chat model reads only the most recent turns; earlier content comes back through memory and retrieval. The conversation record itself is kept in full.

Admins can also manage users from the command line on the server, with the same effect as the admin console:

```sh
docker compose exec backend eidolon user list                      # ID, name, sign-in methods (in brackets: the identifier for EIDOLON_ADMINS)
docker compose exec backend eidolon user ban <user ID> [--note note]  # signed out on all devices, calls hung up within seconds
docker compose exec backend eidolon user unban <user ID>
docker compose exec backend eidolon user usage <user ID>            # hourly usage over the last 24 hours
```

## Bring your own keys

By default, the deployer pays for everything. Users can enter their own keys on the settings page's 「自带密钥」 (Own keys) tab to share the cost:

| Service | What to enter | Used for |
|---|---|---|
| LLM | Protocol, base_url, key, model name | Playing the character (text, calls and bar visits), extracting memories |
| Speech synthesis (Fish Audio) | Key | Her voice in calls and read aloud; the voice still comes from the character configuration. Read-alouds on it don't count |
| Speech recognition (Soniox or Alibaba Cloud Model Studio) | Provider and key | Hearing the user in calls; independent of the deployer's choice |
| Image generation | Format, address, key, model | The photos she sends (text and calls), not counted toward photos per hour; the deployer's art style still applies, one picture at a time |

- **Kept only in the browser**: Keys are stored only in the user's browser (separately for each account). They are sent to the server with each turn, call, read-aloud or visit, stay in its memory only while it is handled (for a visit, until the visit ends), and are never written to the database, logs or backups ([ADR-0017](adr/0017-own-api-keys-stay-in-the-browser.md)). After switching devices or clearing browser data, they must be entered again.
- **Tried first**: Each key is tried once when entered, and not stored if the try fails. The LLM must also support streaming and tool calling; image generation generates one real picture, on the user's own credit, not counted in usage. In a public deployment, base_url (for image generation, the address and any `url` a picture comes from) must be an HTTPS public address, checked again on every connection.
- **No fallback on failure**: When an own key fails (out of credit, revoked, etc.), that turn or call fails, saying which key had the problem. It **never falls back to the deployer's keys**. Image generation is the exception: the turn goes on, only that photo isn't sent, because the user's own image generation key didn't work.
- **Always on the deployer**: Embedding, reranking and the judge.

## Proxy

When the server cannot reach some providers (a server in mainland China reaching OpenAI or Soniox, say), those services can go through a proxy while the rest stay direct:

```sh
EIDOLON_PROXY_URL=http://127.0.0.1:7890
EIDOLON_PROXY_SERVICES=chat_llm,tts,stt
```

- **Address**: Starts with `http://`, `https://`, `socks5://` or `socks5h://`, with a host and port, optionally a user and password (`http://user:password@host:port`). Leave it empty for no proxy. In production (`docker-compose.prod.yml`) the backend shares the host's network, so a proxy on the host (mihomo, say) is just `127.0.0.1`.
- **Services through it**: Comma-separated, or `all` for every one.

| Name | Service |
|---|---|
| `chat_llm` | The LLM playing the character (text and calls) |
| `memory_llm` | The background model (list it even when it follows the chat model) |
| `judge` | The judge (Jev, Cloudflare or Alibaba Cloud Model Studio) |
| `embedding` | Embedding |
| `rerank` | Reranking |
| `tts` | Speech synthesis (Fish Audio) |
| `stt` | Speech recognition (Soniox or Alibaba Cloud Model Studio) |
| `image` | Image generation (NovelAI or a relay alike) |
| `gpt_image` | GPT Image, for pictures with no one in them in moments |
| `own_llm` | Users' own LLMs (with their own background models), only at a known provider's address |
| `own_tts` | Users' own speech synthesis |
| `own_stt` | Users' own speech recognition (whichever service they chose) |
| `own_image` | Users' own image generation, only at NovelAI's own HTTPS address `image.novelai.net`; relays always go direct |

- **Only these two**: `HTTPS_PROXY`, `ALL_PROXY` and the like have no effect on the services above; other outgoing requests (sign-in, backups, story sync) still follow them.
- **Own keys are picked apart**: Keys users bring are ticked apart from the deployer's services, as the two may be with different providers (the deployer's speech recognition on Model Studio, direct, and a user's own on Soniox, say). The requests are the server's, so a proxy or VPN the user runs has no part in them. Unticked, the default, they go direct; ticked, they go through the deployer's proxy, on its traffic.
- **Own LLMs go through it only to known providers**: The address of a user's own LLM is theirs to type, and may point into the server's own network; through a proxy, the server cannot check where it really connects. So only an address whose host is a known provider's goes through it: the providers the price catalog (models.dev; see [Prices for cost estimates](deploy.md#花费估算用的单价) in the deploy guide) gives an address for, the few the code knows (OpenAI, Anthropic, Google Gemini, xAI, Mistral, Cohere, Groq, Cerebras, DeepInfra, Together, Perplexity, Venice) and OpenRouter; never an IP address or `localhost`. Any other goes direct, checked to be on the public internet ([ADR-0022](adr/0022-own-llms-through-the-proxy-only-to-known-providers.md)). While the catalog cannot be fetched, only the ones the code knows count. Users' own image generation works the same way, with NovelAI itself as the one known provider.
- **Changeable in the admin console**: The 「网络」 (Network) tab of the config page has 「网络代理」 (Proxy): switch it on or off, change the address and pick the services, with no restart. It holds from the next request on (in turns and calls under way too; voice connections already open stay up). Before saving, each of the deployer's services routed a new way is reached that way once (users' own keys are not: there are none here to try with), and nothing is saved if one cannot be; if one cannot be as the server restarts, `.env`'s value is used and the admin console says so. A password in the address is encrypted like a key; without `EIDOLON_SECRET_KEY`, an address with a password can only be set in `.env`.

## Service status

Beside the bell on the conversation list there is a "service status" button: signed-in users can open it to see whether each service works right now — working, unsteady, down, or no recent calls. When a service is not working, the button carries a red or amber dot.

```sh
EIDOLON_STATUS_SERVICES=chat_llm,tts,stt
EIDOLON_STATUS_WINDOW_MINUTES=30
```

- **How it is judged**: by the share of calls on the deployer's keys that failed over the window (`EIDOLON_STATUS_WINDOW_MINUTES`: 10, 30 or 60 minutes, 30 by default): under 5% is working, 5% to 50% unsteady, 50% or more down. Calls on users' own keys are left out.
- **Tried when idle**: a service with no calls over the window is tried with the least of real requests: one word from an LLM, a few words embedded or reranked, the judge tried as the admin console tries it, two characters voiced, and for speech recognition only a check that costs nothing. A failed try is repeated at once; failing twice, the service is down. Each service is tried at most twice per window, at next to no cost, and the tries are not activity records, so the dashboard's usage and costs leave them out. Image generation costs money per picture and is never tried: without calls it shows "no recent calls".
- **Which services are shown**: `EIDOLON_STATUS_SERVICES`, comma-separated, named as the first eight in the proxy table; empty or `all` for every one, `none` for none (then there is no button). Services the deployment does not have are never shown.
- **In the admin console**: the config page's "service status" tab chooses them one by one and the window; changes hold at once.
- **Speech in calls**: a call's speech synthesis and recognition are recorded when the call ends, so a call under way shows in the status only after it hangs up.

## Admin console

List the admins' sign-in method identifiers in `EIDOLON_ADMINS` in `.env` (like `github:12345`; look them up with `eidolon user list`) and recreate the backend. Those users then find 「进入后台」 (Open admin console) on the settings page's 「登录与数据」 (Sign-in and data) tab ([ADR-0013](adr/0013-admin-console-overrides-env.md)). Without it there is no admin console, and anyone else gets a 404 at `/admin`; except with dev login on, when everyone is an admin (see 「Dev login」 above).

| Page | What it does |
|---|---|
| Dashboard (`/admin`) | Calls, error rate and latency per service; active users, the number and trend of turns and calls, usage per character, calls in progress; with affinity on, totals of judgements and cooldowns, plus per character the shares raised and lowered, cooldowns, and the calls she hung up or conversations she ended, as well as 「成就」 (Achievements): how many achievement stages were unlocked, and the draws and reset cards they gave; with schedules on, the number of users with a schedule this week; with reach-outs on, how many there were, how many failed and the share answered; with letters on, how many were written and how many times writing one failed; with moments on, how many were posted and how many failed, how many replies to comments there were and how many failed, and the share of the last 30 days' posts the producer liked or commented on; with the bar on, how many visits there were, how many finished and how many failed; the deployer's cost estimated from unit prices |
| Config (`/admin/config`) | Change the LLMs for playing the character and extracting memories, speech synthesis, speech recognition, image generation, the judge, rerank thresholds, usage limits, exempting keys, per-call caps, history turns, the affinity and gifts switch (and granting every user a reset card), the schedules switch, the reach-outs switch and daily limit, the letters switch, the moments switch, daily limits and map, the bar switch, the proxy, the service status and unit prices |
| Users (`/admin/users`) | Search users, see their sign-in methods and recent usage; ban, unban, set an individual usage limit, delete |

- **Overrides `.env`**: Items changed in the admin console are stored in the database and take precedence over `.env`, with no restart needed. Each change is tried before saving and not saved if the try fails. A call in progress finishes on the configuration it connected with.
- **Only changeable in `.env`**: The admin list, `EIDOLON_SECRET_KEY`, OAuth, the domain, WebRTC/TURN, backups, paths and embedding.
- **Not visible**: The admin console shows no one's conversations, memories, producer profile, affinity, gifts, draws, achievements, schedules, visit records, moments or letters; the dashboard only has totals across all users. The dashboard's numbers come from activity records (which hold no conversation content), kept for 90 days.

For how to turn it on and what to do when you can't get into the admin console, see "后台" in [`deploy.md`](deploy.md) (Chinese).

## Command-line reference

The backend's command line is `eidolon`. Under docker compose, use `docker compose exec backend eidolon …`; for local development, use `uv run eidolon --db data/eidolon.db …` in `backend/`. Add `--help` to any command to see its options.

| Command | What it does |
|---|---|
| `serve` | Start the server (default) |
| `story sync` / `import-csv` / `import-json` | Sync or import the story corpus |
| `world sync` | Update the world setting |
| `character draft-sheet <id>` | Draft a character sheet with the background model |
| `reading draft` | Fill in phonemes in the readings table (local only) |
| `greeting upload` | Synthesize and upload the landing page's greetings |
| `letter-music upload <dir>` | Upload the music under letters |
| `stand fetch` / `outfits` / `upload` | The three steps for stand assets, usually chained by `deploy/stand-sync.sh` |
| `reembed` | Re-embed after switching embedding service, model or dimensions |
| `eval rerank` / `judge` / `memory` | Calibrate rerank thresholds and judge thresholds, evaluate memory |
| `user list` / `ban` / `unban` / `usage` | Manage users |
| `backup` | Back the database up, encrypted, to a private bucket |
