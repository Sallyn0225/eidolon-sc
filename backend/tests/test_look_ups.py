"""What she looks up (GLOSSARY.md「查看」) typing and in a call, and what she is told of now
instead (「此刻」): of her jobs only the one under way, of the weather only what she may bring
up, and that but once in a stretch of their being in touch, again for a warning new in it
(ADR-0033).

As she looks something up, the browser is told what (`looking-up`), typing and in a call alike.

Driven through text turns as the producer takes them, and calls as `test_call_turns` runs them,
the chat model scripted to look things up, Open-Meteo and QWeather stood in for over their
transports, her jobs saved through the API as the producer saves them, on a clock the tests
move."""

from dataclasses import replace

import httpx

from eidolon.config import Settings
from eidolon.her_weather import TOLD_TO_BRING_UP
from eidolon.llm import ChatMessage, ToolCall
from tests.conftest import ClientFactory
from tests.fakes import (
    HANG,
    HARBIN,
    FakeClock,
    FakeLLM,
    FakeQWeather,
    FakeWeather,
    alert,
    context_of,
)
from tests.test_call_turns import (
    INTERRUPTING,
    CallUnderTest,
    mano_call,  # noqa: F401  # the fixture
    spoken,
)
from tests.test_her_now import scheduling
from tests.test_producer_weather import NOON, account, city_of
from tests.test_schedule_she_knows import ABOUT_THEM, HER_JOBS, UNDER_WAY
from tests.test_text_turn import send_turn, start_conversation

REPLY = ["<ja>はいっ</ja><zh>好的</zh>"]
WEATHER = ToolCall("call_w", "look_up_weather", {})
SCHEDULE = ToolCall("call_s", "look_up_schedule", {})
# Copied, not imported: the wording was tried against the real chat model
# (research/on-demand-context), so an untried rewording should fail here.
LOOK_UP_BOTH = (
    "今天的天气和你这周、下周的日程，你要看一眼手机才知道：制作人问起或话题需要时用工具查，"
    "不要凭印象说。"
)
LOOK_UP_THE_SCHEDULE = (
    "你这周、下周的日程，你要看一眼手机才知道：制作人问起或话题需要时用工具查，不要凭印象说。"
)
LOOKED_UP_NOTE = (
    "（这一轮不能再调用任何工具了，请现在就回答制作人。可以像看了一眼手机那样自然地说，"
    "不要提到工具或记录。）"
)
TOKYO_NOW = "东京（你这边）这会儿"
THERE_NOW = "制作人那边（哈尔滨）这会儿"


def looked_up(prompt: list[ChatMessage]) -> list[str]:
    """What she read of what she looked up, as the model is told it in `prompt`."""
    return [m.content for m in prompt if m.role == "tool"]


def now_of(prompt: list[ChatMessage]) -> str:
    """What she is told of now in `prompt`, the first section of what changes turn to turn."""
    return context_of(prompt).split("\n\n")[0]


def names(llm: FakeLLM) -> list[list[str]]:
    return [[t.name for t in tools] for tools in llm.tools]


async def test_typing_she_is_told_only_the_job_under_way_and_looks_the_rest_up(
    make_client: ClientFactory, settings: Settings
):
    llm = FakeLLM([SCHEDULE], REPLY)
    client, clock = await scheduling(
        make_client, settings, ("声乐课", 1, 0, 0), ("开会", 1, 2, 1), ("外景", 3, 3, 0),
        llm=llm,
    )
    clock.advance(days=2, hours=13)  # Wednesday 14:00

    events = await send_turn(client, await start_conversation(client), "明天你有什么工作吗？")

    told = now_of(llm.prompts[0])
    assert f"现在（下午 12–18 点）你正在开会：说明。{UNDER_WAY}" in told
    assert HER_JOBS not in told and "声乐课" not in told and "外景" not in told
    assert told.endswith(f"{UNDER_WAY}\n{LOOK_UP_BOTH}")  # her cycle after it, if anywhere
    assert llm.forbidden == [False, True]
    assert looked_up(llm.prompts[1]) == ["\n".join([
        HER_JOBS,
        "周一（前天）上午：声乐课——说明（做完了）",
        "周四（明天）一整天：外景——说明",
        f"现在（下午 12–18 点）你正在开会：说明。{UNDER_WAY}",
        ABOUT_THEM,
    ]) + f"\n\n{LOOKED_UP_NOTE}"]
    assert events[-1]["type"] == "done"


async def test_with_no_jobs_she_looks_up_that_she_has_none(make_client: ClientFactory):
    llm = FakeLLM([SCHEDULE], REPLY)
    client = make_client(llm)

    await send_turn(client, await start_conversation(client), "最近忙不忙呀？")

    assert looked_up(llm.prompts[1]) == [f"这两周没有安排。\n\n{LOOKED_UP_NOTE}"]


async def test_she_may_look_up_the_same_every_turn_and_with_schedules_off_not_her_schedule(
    make_client: ClientFactory, settings: Settings
):
    on = FakeLLM(REPLY, REPLY)
    off = FakeLLM([SCHEDULE], REPLY)
    client = make_client(on)
    conversation = await start_conversation(client)
    await send_turn(client, conversation, "在吗")
    await send_turn(client, conversation, "在吗")
    without = make_client(off, settings=replace(settings, schedule=False))

    await send_turn(without, await start_conversation(without), "最近忙不忙呀？")

    assert names(on) == [["look_up_weather", "look_up_schedule"]] * 2
    assert on.tools[0] == on.tools[1]
    assert names(off) == [["look_up_weather"]] * 2
    told = now_of(off.prompts[0])
    assert told.endswith("今天的天气你要看一眼手机才知道：制作人问起或话题需要时用工具查，不要凭印象说。")
    assert "日程" not in told.splitlines()[-1]
    assert looked_up(off.prompts[1]) == [
        "没有 look_up_schedule 这个工具。\n\n（这一轮不能再调用任何工具了，请现在就回答制作人。"
        "上面想起来的内容如果答不上他的问题，就像一时记不清那样自然地说，不要提到查找、工具、记录或剧情库。）"
    ]


async def weathered(
    make_client: ClientFactory,
    llm: FakeLLM,
    weather: FakeWeather | None = None,
    qweather: FakeQWeather | None = None,
    settings: Settings | None = None,
) -> tuple[httpx.AsyncClient, str, FakeClock]:
    """A client of the producer's in Harbin, Open-Meteo and QWeather as `weather` and
    `qweather` have them, on a clock at `NOON`; a conversation and the clock."""
    clock = FakeClock(NOON)
    weather = weather or FakeWeather()
    qweather = qweather or FakeQWeather()
    weather.clock = qweather.clock = clock
    extra = {"settings": settings} if settings is not None else {}
    client = make_client(
        llm, clock=clock, weather_transport=weather.transport(),
        qweather_transport=qweather.transport(), **extra,
    )
    assert (await client.put("/api/profile", json={"city": city_of(HARBIN)})).status_code == 200
    return client, await start_conversation(client), clock


async def test_she_looks_up_both_sides_weather_without_being_told_whether_to_bring_it_up(
    make_client: ClientFactory, settings: Settings
):
    llm = FakeLLM(REPLY, [WEATHER], REPLY)
    client, conversation, clock = await weathered(
        make_client, llm, settings=replace(settings, qweather=account())
    )
    await send_turn(client, conversation, "我回来啦")
    clock.advance(minutes=10)

    await send_turn(client, conversation, "我这边今天冷不冷，你知道吗？")

    first, second = now_of(llm.prompts[0]), now_of(llm.prompts[1])
    assert TOKYO_NOW in first and THERE_NOW in first and first.endswith(LOOK_UP_THE_SCHEDULE)
    assert "这会儿" not in second and TOLD_TO_BRING_UP not in second
    assert "制作人在哈尔滨（黑龙江省，中国）" in second  # where the producer is, every turn
    assert second.endswith(LOOK_UP_BOTH)
    [result] = looked_up(llm.prompts[2])
    weather, note = result.split("\n\n")
    assert weather.splitlines() == [
        line for line in first.splitlines() if "这会儿" in line or "制作人在哈尔滨" in line
    ]
    assert note == LOOKED_UP_NOTE


async def test_without_the_weather_she_looks_up_that_she_sees_none(make_client: ClientFactory):
    llm = FakeLLM([WEATHER], REPLY)
    client, conversation, _ = await weathered(make_client, llm, FakeWeather(failing=True))

    await send_turn(client, conversation, "东京今天天气怎么样？")

    assert looked_up(llm.prompts[1]) == [
        f"现在看不到天气。不要编造天气，可以坦率地说没看到。\n\n{LOOKED_UP_NOTE}"
    ]


async def test_she_is_told_the_weather_once_in_a_while_and_again_after_long_apart(
    make_client: ClientFactory,
):
    llm = FakeLLM(*[REPLY] * 3)
    client, conversation, clock = await weathered(make_client, llm, FakeWeather(code=61))

    await send_turn(client, conversation, "我回来啦")
    clock.advance(minutes=10)
    await send_turn(client, conversation, "你在干嘛")  # raining in Tokyo: stands out still
    clock.advance(hours=3)
    await send_turn(client, conversation, "又来了")

    first, soon, apart = (context_of(p) for p in llm.prompts)
    assert TOKYO_NOW in first and TOLD_TO_BRING_UP in first
    assert TOKYO_NOW not in soon and TOLD_TO_BRING_UP not in soon
    assert TOKYO_NOW in apart and TOLD_TO_BRING_UP in apart


async def test_a_warning_new_there_is_told_once_more_but_not_the_weather_changing(
    make_client: ClientFactory, settings: Settings
):
    llm = FakeLLM(*[REPLY] * 4)
    qweather = FakeQWeather()
    client, conversation, clock = await weathered(
        make_client, llm, qweather=qweather, settings=replace(settings, qweather=account())
    )
    await send_turn(client, conversation, "我回来啦")
    qweather.alerts = [alert("哈尔滨市气象台发布暴雨蓝色预警信号")]
    clock.advance(minutes=70)  # the warnings are kept an hour
    await send_turn(client, conversation, "下雨了")
    clock.advance(minutes=70)
    await send_turn(client, conversation, "还在下")
    qweather.later_icon, qweather.temperature = "305", 5
    clock.advance(minutes=70)
    await send_turn(client, conversation, "冷了")

    first, warned, still, changed = (context_of(p) for p in llm.prompts)
    assert TOKYO_NOW in first and THERE_NOW in first and "预警" not in first
    assert "制作人那边正生效的气象预警：哈尔滨市气象台发布暴雨蓝色预警信号。" in warned
    assert THERE_NOW in warned and TOKYO_NOW not in warned and TOLD_TO_BRING_UP in warned
    assert "这会儿" not in still and "预警" not in still
    assert "这会儿" not in changed and "预警" not in changed


LEAKED = [
    '<look_up_weather">\n\n</look_up_weather>\n<', "/｜｜DSML｜｜ parameter>\n",
    "</｜｜DSML｜｜ invoke>\n</｜｜DSML｜｜ calls>",
]
"""DeepSeek's own tool-call markup, as the chat model once wrote it out instead of calling
(research/on-demand-context), split where the markup could not yet be told apart."""


def shown_text(events: list[dict]) -> str:
    return "".join(e["text"] for e in events if e["type"] == "delta")


async def test_markup_written_out_is_neither_shown_nor_kept_and_she_is_asked_again(
    make_client: ClientFactory,
):
    llm = FakeLLM(LEAKED, REPLY)
    client = make_client(llm)

    events = await send_turn(client, await start_conversation(client), "我这边今天冷不冷？")

    assert llm.forbidden == [False, False] and llm.prompts[0] == llm.prompts[1]
    assert shown_text(events) == "はいっ好的"
    assert events[-1]["type"] == "done"
    assert events[-1]["message"]["segments"] == [{"ja": "はいっ", "zh": "好的"}]


async def test_markup_written_out_again_fails_the_turn(make_client: ClientFactory):
    llm = FakeLLM(LEAKED, ["<｜tool▁calls▁begin｜>"])
    client = make_client(llm)

    events = await send_turn(client, await start_conversation(client), "我这边今天冷不冷？")

    assert [e["type"] for e in events] == ["user", "error"]
    assert len(llm.prompts) == 2


async def test_what_she_said_before_markup_stands_and_the_round_goes_no_further(
    make_client: ClientFactory,
):
    llm = FakeLLM(["<ja>えっと</ja><zh>嗯</zh><ja>ちょっと", *LEAKED, "</ja><zh>等等</zh>"])
    client = make_client(llm)

    events = await send_turn(client, await start_conversation(client), "我这边今天冷不冷？")

    assert len(llm.prompts) == 1
    assert "DSML" not in shown_text(events) and "look_up" not in shown_text(events)
    assert events[-1]["message"]["segments"] == [
        {"ja": "えっと", "zh": "嗯"}, {"ja": "ちょっと", "zh": ""},
    ]


def looking_up(events: list[dict]) -> list[list[str]]:
    """What the browser was told she was looking up, in turn."""
    return [list(e["what"]) for e in events if e["type"] == "looking-up"]


async def test_the_browser_is_told_what_she_looks_up_between_her_words(
    make_client: ClientFactory,
):
    llm = FakeLLM(["<ja>えっと</ja><zh>嗯</zh>", WEATHER, SCHEDULE], REPLY)
    client = make_client(llm)

    events = await send_turn(client, await start_conversation(client), "周六天气好的话有空吗？")

    types = [e["type"] for e in events]
    assert looking_up(events) == [["weather", "schedule"]]
    at = types.index("looking-up")
    assert "delta" in types[:at] and "delta" in types[at:]
    assert events[-1]["type"] == "done"
    assert events[-1]["message"]["segments"] == [
        {"ja": "えっと", "zh": "嗯"}, {"ja": "はいっ", "zh": "好的"},
    ]


async def test_what_she_may_not_look_up_is_not_told(
    make_client: ClientFactory, settings: Settings
):
    llm = FakeLLM([SCHEDULE, ToolCall("call_x", "look_up_horoscope", {})], REPLY)
    client = make_client(llm, settings=replace(settings, schedule=False))

    events = await send_turn(client, await start_conversation(client), "最近忙不忙呀？")

    assert looking_up(events) == []
    assert events[-1]["type"] == "done"


async def test_in_a_call_she_looks_up_as_typing_and_the_browser_is_told(
    mano_call: CallUnderTest,
):
    llm = FakeLLM([SCHEDULE], ["<ja>ほわっ</ja><zh>哇</zh>"])

    _, messages = await mano_call.run(llm, [spoken("明天有工作吗")])

    assert looking_up(messages) == [["schedule"]]
    assert [t.name for t in llm.tools[0]] == ["look_up_weather", "look_up_schedule"]
    assert LOOK_UP_BOTH in context_of(llm.prompts[0])


async def test_interrupted_as_she_looks_something_up_she_stops_there(mano_call: CallUnderTest):
    llm = FakeLLM(["<ja>ほわっ</ja><zh>哇</zh>", SCHEDULE], ["<ja>今日", HANG], delay=0.3)

    _, messages = await mano_call.run(llm, [spoken("明天有工作吗"), *INTERRUPTING])

    assert looking_up(messages) == [["schedule"]]
    assert [m["type"] for m in messages if m["type"] in ("done", "error")] == ["done"]
    assert await mano_call.record() == [
        ("user", "明天有工作吗", None, None), ("character", None, "ほわっ", "哇"),
    ]
