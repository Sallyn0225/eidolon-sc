"""按需加载天气和日程的对照实验：现在的做法（A，天气和日程每回合都在「此刻」里）
对比按需的做法（B，不放进去，给两个查询工具；能主动提的那回合才推一次天气）。

量三件事：
1. 闲聊时（没人问天气和日程）她提起天气、日程的比例；
2. 被问到时，B 调不调工具、有没有编；A、B 答得对不对；
3. 天气可以主动提的那天（好久没联系、天气变化大），A、B 第一回合提不提、之后会不会反复提。
另外记下每回合的首字时间和总时间、B 多出来的工具轮。

在 backend/ 下运行（用 eidolon 包里真的人设、世界设定、「此刻」和格式说明）：

    uv run python ../.scratch/on-demand-context/experiment.py run --trials 3
    uv run python ../.scratch/on-demand-context/experiment.py report

对话模型和 key 读仓库根目录 .env 的 CHAT_LLM_*；判断提没提、对不对用同一个模型。
每回合一行追加到 experiment-data/turns.jsonl；report 写 report.md。
"""

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from eidolon.affinity import affinity_prompt
from eidolon.characters import load_characters
from eidolon.cycles import always_neither
from eidolon.engine import LAST_ROUND_NOTE, MAX_TOOL_ROUNDS
from eidolon.her_now import HerNow, KnownNow
from eidolon.her_weather import KnownWeather, weather_lines
from eidolon.llm import ChatMessage, Reasoning, Tool, ToolCall
from eidolon.llm.openai_compat import OpenAICompatLLM
from eidolon.producer import Birthday, City, ProducerProfile, producer_prompt
from eidolon.reply_format import FORMAT_INSTRUCTIONS, ReplyParser, Segment, format_reply
from eidolon.retrieval import RECALL_STORY_TOOL
from eidolon.schedule import HerJob, HerSchedule, Job, schedule_lines
from eidolon.today import always_known
from eidolon.weather import Today, Weather
from eidolon.world import load_world, world_path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
DATA = HERE / "experiment-data"
TURNS = DATA / "turns.jsonl"
CHARACTER = "mano"
TZ = "Asia/Shanghai"
START = datetime(2026, 11, 4, 20, 30, tzinfo=ZoneInfo(TZ))  # 周三晚上
THIS_WEEK = date(2026, 11, 2)
NEXT_WEEK = date(2026, 11, 9)
SHANGHAI = City("上海", "上海", "上海", "中国", 31.23, 121.47)
PROFILE = ProducerProfile(birthday=Birthday(3, 8), city=SHANGHAI)

# ---- B 的工具和提示 ----

WEATHER_TOOL = Tool(
    name="look_up_weather",
    description="看天气：看一眼手机上的天气，返回东京（你这边）和制作人那边今天的天气。"
    "制作人问起天气、冷不冷、要不要带伞，或者话题真的需要知道今天的天气时使用；闲聊时不需要。",
    parameters={"type": "object", "properties": {}},
)
SCHEDULE_TOOL = Tool(
    name="look_up_schedule",
    description="看日程：看制作人给你排的这周和下周的安排（哪天、哪个时段、做什么、做完没有）。"
    "制作人问起你的安排、忙不忙、哪天有空，或者话题真的需要知道你的安排时使用；闲聊时不需要。",
    parameters={"type": "object", "properties": {}},
)
ON_DEMAND = (
    "今天的天气和你这周、下周的日程，你要看一眼手机才知道：制作人问起或话题需要时用工具查，"
    "不要凭印象说。"
)
ON_DEMAND_SCHEDULE = (
    "你这周、下周的日程，你要看一眼手机才知道：制作人问起或话题需要时用工具查，不要凭印象说。"
)
TOOL_LAST_ROUND_NOTE = (
    "（这一轮不能再调用任何工具了，请现在就回答制作人。可以像看了一眼手机那样自然地说，"
    "不要提到工具或记录。）"
)
NOT_FOUND = "剧情库里没有记录这段经过。不要编造经过，可以坦率地说细节记不太清了。"

# ---- 事实 ----


def job(id_: str, name: str, note: str, category: str, length: int = 1) -> Job:
    return Job(id_, CHARACTER, name, note, category, length, None)  # type: ignore[arg-type]


JOBS = [
    HerJob(job("dance-lesson", "舞蹈课", "在练习室跟着老师抠新编舞蹈的细节。", "practice"),
           THIS_WEEK, 0, 1),
    HerJob(job("magazine-shoot", "杂志拍摄", "给杂志拍一组内页照片，要换三四套衣服。", "appearance"),
           THIS_WEEK, 2, 1),
    HerJob(job("variety-show", "综艺节目录制", "在摄影棚录一期综艺，有游戏环节。", "appearance", 2),
           THIS_WEEK, 4, 0),
    HerJob(job("movie", "看电影", "去电影院看一部最近上映的电影。", "private"), THIS_WEEK, 5, 2),
    HerJob(job("vocal-lesson", "声乐课", "跟老师练发声，重点是新歌高音的部分。", "practice"),
           NEXT_WEEK, 1, 0),
]
FACTS_SCHEDULE = (
    "她的日程：周一下午舞蹈课（做完了）；今天周三下午杂志拍摄（做完了）；"
    "周四（明天）没有安排；周五上午到下午综艺节目录制；周六晚上私人安排：看电影；"
    "下周二上午声乐课。"
)


def mild_weather() -> KnownWeather:
    """平常的一天，刚聊过：只让她心里有数。"""
    return KnownWeather(
        tokyo=Today(Weather("cloudy", 14), None, 17, 11, 16, 10),
        city=SHANGHAI, there=Today(Weather("clear", 18), None, 21, 13, 20, 12),
        warnings=(), same_place=False, tokyo_free=False, there_free=False,
    )


def standout_weather() -> KnownWeather:
    """好久没联系，东京晚些时候下雨、比昨天冷不少：两边都能主动提。"""
    return KnownWeather(
        tokyo=Today(Weather("overcast", 11), "rain", 12, 8, 20, 13),
        city=SHANGHAI, there=Today(Weather("clear", 18), None, 21, 13, 20, 12),
        warnings=(), same_place=False, tokyo_free=True, there_free=True,
    )


FACTS_WEATHER = {
    "mild": "东京：多云，14°C，今天 11～17°C。上海（制作人那边）：晴，18°C，今天 13～21°C。",
    "standout": "东京：阴，11°C，今天 8～12°C，晚些时候还会下雨，比昨天冷了不少（最高低了 8°C）。"
    "上海（制作人那边）：晴，18°C，今天 13～21°C。",
}

# ---- 场景 ----

GREETING_REPLY = [Segment(
    ja="こんばんは、プロデューサーさん。ほわっ……今日もお疲れさまです",
    zh="晚上好，制作人。呼哇……今天也辛苦了",
)]

CASUAL = {
    "闲聊一": ["晚上好呀，真乃", "今天晚饭吃了什么？", "我最近在追一部推理剧，挺上头的",
              "你有没有什么想推荐我听的歌？", "唉，今天开了一整天会，好累", "那我先去洗澡啦，晚安"],
    "闲聊二": ["在吗？", "我今天在路上看到好多鸽子，就想到你了", "你最近有没有什么开心的事？",
              "我想学做甜点，你觉得从什么开始比较好？", "周末我大概会在家宅着", "好啦不打扰你了，早点休息"],
}
ASKED = [
    ("weather", "东京今天天气怎么样？"),
    ("weather", "我这边今天冷不冷，你知道吗？"),
    ("schedule", "明天你有什么工作吗？"),
    ("schedule", "这周六晚上有空吗？想约你吃饭"),
    ("schedule", "最近忙不忙呀？"),
]
PROACTIVE = ["我回来啦，这两天出差刚回来", "你最近怎么样？", "我给你带了点上海的小点心",
             "好啦，我去整理行李了"]


def env(name: str) -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip()
    sys.exit(f".env 里没有 {name}")


class Material:
    def __init__(self) -> None:
        characters_path = ROOT / "characters" / "characters.toml"
        self.characters = load_characters(characters_path)
        self.character = self.characters[CHARACTER]
        self.world = load_world(world_path(characters_path))
        self.her_now = HerNow(self.characters, self.world)
        world_prompt = self.world.prompt(self.character.name, START.date()) if self.world else None
        self.shared = "\n\n".join([*always_known(self.character, world_prompt), FORMAT_INSTRUCTIONS])

    def schedule(self, now: datetime) -> HerSchedule:
        return HerSchedule(now.replace(tzinfo=None), THIS_WEEK, JOBS)

    def now_section(self, variant: str, now: datetime, last_contact: datetime | None,
                    weather: KnownWeather | None, push_weather: bool) -> str:
        """引擎里 `_now_section` 那一节。A 照现在的样子；B 不带日程，天气只在 `push_weather`
        时带（能主动提、这段对话还没推过），另加一句「要看手机才知道」。"""
        schedule = self.schedule(now) if variant == "A" else None
        done_today = schedule.done_today() if schedule else None
        known = KnownNow(self.character, schedule, always_neither, done_today, None, ())
        told_weather = weather if variant == "A" or push_weather else None
        lines = self.her_now.lines(
            known, "typing", now, TZ, PROFILE, last_contact,
            affinity_prompt("close", None), known_weather=told_weather,
        )
        if variant == "B":
            lines.append(ON_DEMAND_SCHEDULE if told_weather else ON_DEMAND)
        return "\n".join(lines)

    def tool_result(self, call: ToolCall, now: datetime, weather: KnownWeather) -> str:
        if call.name == WEATHER_TOOL.name:
            # 数据那几行，不带「能不能主动提」那句
            return "\n".join(weather_lines(weather)[:-1])
        if call.name == SCHEDULE_TOOL.name:
            return "\n".join(schedule_lines(self.schedule(now))) or "这两周没有安排。"
        if call.name == RECALL_STORY_TOOL.name:
            return NOT_FOUND
        return f"没有 {call.name} 这个工具。"


@dataclass
class Turn:
    user: str
    segments: list[Segment]


@dataclass
class Result:
    segments: list[Segment]
    calls: list[str] = field(default_factory=list)
    first_text: float | None = None
    total: float = 0.0
    rounds: int = 1
    error: str | None = None


async def reply(llm: OpenAICompatLLM, m: Material, variant: str, history: list[Turn],
                text: str, now: datetime, last_contact: datetime | None,
                weather: KnownWeather, push_weather: bool) -> Result:
    prompt = [
        ChatMessage("system", m.shared, cache_breakpoint=True),
        ChatMessage("system", producer_prompt(PROFILE)),
    ]
    for t in history:
        prompt += [ChatMessage("user", t.user), ChatMessage("assistant", format_reply(t.segments))]
    prompt.append(ChatMessage("system", m.now_section(variant, now, last_contact, weather,
                                                      push_weather)))
    prompt.append(ChatMessage("user", text))
    tools = [RECALL_STORY_TOOL] + ([WEATHER_TOOL, SCHEDULE_TOOL] if variant == "B" else [])
    parser = ReplyParser()
    result = Result([])
    began = time.perf_counter()
    for step in range(MAX_TOOL_ROUNDS + 1):
        forbidden = step == MAX_TOOL_ROUNDS
        said = ""
        calls: list[ToolCall] = []
        reasoning: list[Reasoning] = []
        async for item in llm.stream(prompt, tools, forbid_calls=forbidden):
            if isinstance(item, ToolCall):
                calls.append(item)
            elif isinstance(item, Reasoning):
                reasoning.append(item)
            else:
                if item.strip() and result.first_text is None:
                    result.first_text = time.perf_counter() - began
                said += item
                parser.feed(item)
        parser.finish()
        if not calls or forbidden:
            break
        result.calls += [c.name for c in calls]
        result.rounds += 1
        prompt = [*prompt, ChatMessage("assistant", said, tuple(calls), reasoning=tuple(reasoning))]
        for call in calls:
            note = LAST_ROUND_NOTE if call.name == RECALL_STORY_TOOL.name else TOOL_LAST_ROUND_NOTE
            prompt.append(ChatMessage("tool", f"{m.tool_result(call, now, weather)}\n\n{note}",
                                      tool_call_id=call.id))
    result.total = time.perf_counter() - began
    result.segments = parser.complete
    return result


JUDGE = """你在给一段角色扮演对话做标注。角色是偶像櫻木真乃，对方是她的制作人。

事实（她可能知道，也可能不知道）：
- 天气：{weather}
- {schedule}

制作人这句：{user}
她的回复（中文字幕）：{reply}

只看她这一条回复，回答下面几项，输出一个 JSON 对象：
- "weather"：她有没有说到今天的天气（天气状况、气温、冷暖、下雨、带伞、加衣服之类）。只是泛泛说季节、或比喻，不算。
- "schedule"：她有没有说到她自己具体的工作或安排（某天的课、拍摄、录制、私人安排等，不论真假）。只说「最近挺忙」「刚忙完」这种笼统的话不算；说到「今天拍了杂志」这种具体的算。
- "wrong"：她说到的天气或安排有没有和上面的事实对不上（说错、编了不存在的安排或天气）。没说到就是 false。
- "note"：一句话说明（中文，20 字以内）。
"""


async def judge(client: httpx.AsyncClient, url: str, key: str, model: str, weather: str,
                user: str, said: str) -> dict[str, Any]:
    body = {
        "model": model, "response_format": {"type": "json_object"}, "temperature": 0,
        "messages": [{"role": "user", "content": JUDGE.format(
            weather=weather, schedule=FACTS_SCHEDULE, user=user, reply=said)}],
    }
    for attempt in range(3):
        try:
            res = await client.post(url, json=body, headers={"authorization": f"Bearer {key}"})
            res.raise_for_status()
            return json.loads(res.json()["choices"][0]["message"]["content"])
        except Exception as e:  # noqa: BLE001
            if attempt == 2:
                return {"error": str(e)}
            await asyncio.sleep(2)
    return {}


class Runner:
    def __init__(self, trials: int, concurrency: int) -> None:
        self.m = Material()
        base, key, model = env("CHAT_LLM_BASE_URL"), env("CHAT_LLM_API_KEY"), env("CHAT_LLM_MODEL")
        self.http = httpx.AsyncClient(timeout=180)
        self.llm = OpenAICompatLLM(base, key, model, client=self.http)
        self.judge_args = (base.rstrip("/") + "/chat/completions", key, model)
        self.model = model
        self.trials = trials
        self.gate = asyncio.Semaphore(concurrency)
        self.lock = asyncio.Lock()
        DATA.mkdir(exist_ok=True)

    async def log(self, record: dict[str, Any]) -> None:
        async with self.lock:
            with TURNS.open("a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    async def conversation(self, kind: str, name: str, variant: str, trial: int,
                           lines: list[str], weather_kind: str,
                           history: list[Turn] | None = None, asked: str | None = None) -> None:
        async with self.gate:
            weather = mild_weather() if weather_kind == "mild" else standout_weather()
            history = list(history or [])
            pushed = False
            for i, text in enumerate(lines):
                now = START + timedelta(minutes=2 * (len(history) + i))
                if kind == "proactive" and i == 0:
                    last_contact = now - timedelta(days=2)
                else:
                    last_contact = now - timedelta(minutes=2)
                # B：能主动提，并且这段对话还没推过，才推（由代码记）
                free = weather.tokyo_free or weather.there_free
                push = variant == "B" and free and not pushed
                pushed = pushed or push
                try:
                    r = await reply(self.llm, self.m, variant, history, text, now, last_contact,
                                    weather, push)
                except Exception as e:  # noqa: BLE001
                    r = Result([], error=repr(e))
                zh = " / ".join(s.zh for s in r.segments)
                ja = " / ".join(s.ja for s in r.segments)
                j = await judge(self.http, *self.judge_args, FACTS_WEATHER[weather_kind], text, zh) \
                    if r.segments else {}
                await self.log({
                    "kind": kind, "scenario": name, "variant": variant, "trial": trial, "turn": i,
                    "asked": asked, "user": text, "zh": zh, "ja": ja, "calls": r.calls,
                    "pushed_weather": push, "first_text": r.first_text, "total": r.total,
                    "rounds": r.rounds, "error": r.error, "judge": j, "model": self.model,
                })
                print(f"{kind} {name} {variant}#{trial} t{i} {r.calls or ''} {zh[:40]}", flush=True)
                if r.segments:
                    history.append(Turn(text, r.segments))

    async def run(self, kinds: list[str]) -> None:
        jobs = []
        for trial in range(self.trials):
            for variant in ("A", "B"):
                if "casual" in kinds:
                    for name, lines in CASUAL.items():
                        jobs.append(self.conversation("casual", name, variant, trial, lines, "mild"))
                if "asked" in kinds:
                    for about, q in ASKED:
                        jobs.append(self.conversation(
                            "asked", q, variant, trial, [q], "mild",
                            history=[Turn("晚上好呀，真乃", GREETING_REPLY)], asked=about))
                if "proactive" in kinds:
                    jobs.append(self.conversation("proactive", "出差回来", variant, trial,
                                                  PROACTIVE, "standout"))
        await asyncio.gather(*jobs)
        await self.http.aclose()


# ---- 报告 ----


def pct(n: int, d: int) -> str:
    return f"{n}/{d}（{round(100 * n / d)}%）" if d else "—"


def median(xs: list[float]) -> str:
    xs = sorted(x for x in xs if x is not None)
    return f"{xs[len(xs) // 2]:.1f}s" if xs else "—"


def report() -> None:
    rows = [json.loads(line) for line in TURNS.read_text(encoding="utf-8").splitlines() if line]
    ok = [r for r in rows if not r["error"] and "error" not in r["judge"] and r["judge"]]
    out = ["# 按需加载天气和日程：对照实验结果", "",
           f"模型 `{rows[0]['model']}`，共 {len(rows)} 回合，出错 {len(rows) - len(ok)} 回合。"
           "A＝现在的做法，B＝按需（工具＋能主动提时推一次）。", ""]

    def j(r: dict[str, Any], k: str) -> bool:
        return bool(r["judge"].get(k))

    out += ["## 1. 闲聊时提起天气、日程的比例", "",
            "| | 回合 | 提天气 | 提日程 | 说错 | B 调了工具 | 首字中位 |", "|---|---|---|---|---|---|---|"]
    for v in ("A", "B"):
        rs = [r for r in ok if r["kind"] == "casual" and r["variant"] == v]
        out.append(f"| {v} | {len(rs)} | {pct(sum(j(r, 'weather') for r in rs), len(rs))} | "
                   f"{pct(sum(j(r, 'schedule') for r in rs), len(rs))} | "
                   f"{pct(sum(j(r, 'wrong') for r in rs), len(rs))} | "
                   f"{pct(sum(bool(r['calls']) for r in rs), len(rs)) if v == 'B' else '—'} | "
                   f"{median([r['first_text'] for r in rs])} |")
    out += ["", "按回合（提天气 / 提日程，A → B）：", "",
            "| 场景 | 第几句 | 制作人说 | A | B |", "|---|---|---|---|---|"]
    for name, lines in CASUAL.items():
        for i, text in enumerate(lines):
            cell = []
            for v in ("A", "B"):
                rs = [r for r in ok if r["scenario"] == name and r["variant"] == v and r["turn"] == i]
                cell.append(f"天气 {sum(j(r, 'weather') for r in rs)}/{len(rs)}，"
                            f"日程 {sum(j(r, 'schedule') for r in rs)}/{len(rs)}")
            out.append(f"| {name} | {i + 1} | {text} | {cell[0]} | {cell[1]} |")

    out += ["", "## 2. 被问到时", "",
            "| 问题 | A 答对 | B 调了对的工具 | B 答对 | A 首字 / 总 | B 首字 / 总 |",
            "|---|---|---|---|---|---|"]
    for about, q in ASKED:
        want = WEATHER_TOOL.name if about == "weather" else SCHEDULE_TOOL.name
        a = [r for r in ok if r["kind"] == "asked" and r["scenario"] == q and r["variant"] == "A"]
        b = [r for r in ok if r["kind"] == "asked" and r["scenario"] == q and r["variant"] == "B"]
        out.append(
            f"| {q} | {pct(sum(not j(r, 'wrong') for r in a), len(a))} | "
            f"{pct(sum(want in r['calls'] for r in b), len(b))} | "
            f"{pct(sum(not j(r, 'wrong') for r in b), len(b))} | "
            f"{median([r['first_text'] for r in a])} / {median([r['total'] for r in a])} | "
            f"{median([r['first_text'] for r in b])} / {median([r['total'] for r in b])} |")

    out += ["", "## 3. 能主动提天气的那天（出差两天回来，东京要下雨、降温）", "",
            "| | 第 1 句提天气 | 第 2–4 句提天气 | 一段对话里提了 2 次及以上 |", "|---|---|---|---|"]
    for v in ("A", "B"):
        rs = [r for r in ok if r["kind"] == "proactive" and r["variant"] == v]
        first = [r for r in rs if r["turn"] == 0]
        later = [r for r in rs if r["turn"] > 0]
        trials = sorted({r["trial"] for r in rs})
        many = sum(sum(j(r, "weather") for r in rs if r["trial"] == t) >= 2 for t in trials)
        out.append(f"| {v} | {pct(sum(j(r, 'weather') for r in first), len(first))} | "
                   f"{pct(sum(j(r, 'weather') for r in later), len(later))} | "
                   f"{pct(many, len(trials))} |")

    out += ["", "## 逐条记录", ""]
    for r in rows:
        tag = []
        if r["judge"].get("weather"):
            tag.append("天气")
        if r["judge"].get("schedule"):
            tag.append("日程")
        if r["judge"].get("wrong"):
            tag.append("**说错**")
        calls = f" 调用 {','.join(r['calls'])}" if r["calls"] else ""
        out.append(f"- `{r['kind']}` {r['scenario']} {r['variant']}#{r['trial']} 第{r['turn'] + 1}句"
                   f"{calls}｜{'、'.join(tag) or '—'}｜{r['judge'].get('note', r['error'] or '')}  ")
        out.append(f"  制作人：{r['user']}  ")
        out.append(f"  她：{r['zh']}")
    (HERE / "report.md").write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print(f"写好了 {HERE / 'report.md'}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["run", "report", "preview"])
    p.add_argument("--trials", type=int, default=3)
    p.add_argument("--concurrency", type=int, default=6)
    p.add_argument("--kinds", default="casual,asked,proactive")
    args = p.parse_args()
    if args.command == "report":
        report()
    elif args.command == "preview":
        m = Material()
        for v in ("A", "B"):
            print(f"===== {v}：闲聊时的「此刻」 =====")
            print(m.now_section(v, START, START - timedelta(minutes=2), mild_weather(), False))
            print(f"===== {v}：能主动提的第一句 =====")
            print(m.now_section(v, START, START - timedelta(days=2), standout_weather(), True))
        print("===== 天气工具返回 =====")
        print(m.tool_result(ToolCall("x", WEATHER_TOOL.name, {}), START, mild_weather()))
    else:
        asyncio.run(Runner(args.trials, args.concurrency).run(args.kinds.split(",")))


if __name__ == "__main__":
    main()
