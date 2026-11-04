"""The weather she knows of as she talks (GLOSSARY.md「此刻」), typing, in a call or reaching out:
Tokyo's always, from Open-Meteo, and where the producer has a city in their profile and the
deployer a QWeather account, where the producer is and the weather and the warnings there,
from QWeather. She may bring it up herself only after they have long been apart, or on a day
that stands out, or with a warning in force, and typing is told only what she may bring up
(once in a while, `test_look_ups`; the rest she looks up); nothing of it she cannot have in
time.

Driven through text turns as the producer takes them, Open-Meteo and QWeather stood in for
over their transports (`FakeWeather`, `FakeQWeather`), on a clock the tests move; the
fetching and keeping of the day's weather on a clock of its own."""

import asyncio
import sqlite3
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
)

from eidolon.config import QWeatherSettings, Settings
from eidolon.her_weather import TOLD_TO_BRING_UP
from eidolon.qweather import QWeather
from eidolon.store import read_last_contact
from eidolon.weather import TOKYO, Spot, Today, Weather, Weathers
from tests.conftest import ClientFactory
from tests.fakes import (
    DONGCHENG,
    HARBIN,
    SHINJUKU,
    FakeClock,
    FakeLLM,
    FakeQWeather,
    FakeWeather,
    alert,
    context_of,
)
from tests.test_delete_account import user_id
from tests.test_reach_outs import backend_of, connected_call, last_contact
from tests.test_text_turn import send_turn, start_conversation

REPLY = ["<ja>はいっ</ja><zh>好的</zh>"]
NOON = datetime(2026, 10, 31, 3, 20, tzinfo=UTC)
"""12:20 in Tokyo, 11:20 in Harbin."""


def account() -> QWeatherSettings:
    """A QWeather account, its private key made for the test."""
    pem = Ed25519PrivateKey.generate().private_bytes(
        Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
    ).decode()
    return QWeatherSettings("abc123.re.qweatherapi.com", "Q000000001", "PROJ0001", "KEY00001", pem)


@pytest.fixture
def settings(settings: Settings) -> Settings:
    return replace(settings, qweather=account())


def city_of(found: dict) -> dict:
    """A city as the producer saves it, as `/api/cities` answered it."""
    return {
        "name": found["name"], "adm2": found["adm2"], "adm1": found["adm1"],
        "country": found["country"], "latitude": float(found["lat"]),
        "longitude": float(found["lon"]),
    }


async def talk(
    make_client: ClientFactory,
    weather: FakeWeather,
    qweather: FakeQWeather | None = None,
    *,
    city: dict | None = None,
    turns: int = 1,
    clock: FakeClock | None = None,
    settings: Settings | None = None,
) -> tuple[list[str], FakeLLM, httpx.AsyncClient, str]:
    """Take `turns` text turns, the producer in `city` if any; what she is told of now in
    each, the model, the client and the conversation."""
    clock = clock or FakeClock(NOON)
    weather.clock = clock
    qweather = qweather or FakeQWeather()
    qweather.clock = clock
    llm = FakeLLM(*[REPLY] * 5)
    extra = {"settings": settings} if settings is not None else {}
    client = make_client(
        llm, clock=clock, weather_transport=weather.transport(),
        qweather_transport=qweather.transport(), **extra,
    )
    if city is not None:
        assert (await client.put("/api/profile", json={"city": city})).status_code == 200
    conversation = await start_conversation(client)
    for i in range(turns):
        await send_turn(client, conversation, f"第{i + 1}句")
    return [context_of(p) for p in llm.prompts], llm, client, conversation


async def anew(
    client: httpx.AsyncClient, llm: FakeLLM, settings: Settings, ago: timedelta
) -> str:
    """What she is told of now in a text turn of a new conversation, where she has been told
    none of the weather yet, they last in touch `ago` before `NOON`, in whichever."""
    with sqlite3.connect(settings.database_path) as db:
        db.execute("UPDATE messages SET created_at = ?", ((NOON - ago).isoformat(),))
    await send_turn(client, await start_conversation(client), "还在吗")
    return context_of(llm.prompts[-1])


async def test_she_is_told_tokyos_day_and_after_long_apart_may_bring_it_up(
    make_client: ClientFactory,
):
    weather = FakeWeather(code=0, temperature=18.4)

    [told], *_ = await talk(make_client, weather)

    assert "东京（你这边）这会儿：晴，18°C；今天 15～21°C。" in told
    assert TOLD_TO_BRING_UP in told
    assert told.index("# 此刻") < told.index("东京（你这边）")
    [asked] = weather.days_asked()
    assert (asked["latitude"], asked["longitude"], asked["models"]) == (
        "35.6895", "139.6917", "jma_msm"
    )
    assert (asked["past_days"], asked["forecast_days"], asked["timezone"]) == ("1", "2", "auto")


async def test_soon_after_they_last_talked_on_a_day_like_any_other_she_is_told_none_of_it(
    make_client: ClientFactory, settings: Settings
):
    clock = FakeClock(NOON)
    weather = FakeWeather(clock=clock)
    _, llm, client, _ = await talk(make_client, weather, clock=clock)

    second = await anew(client, llm, settings, timedelta(hours=2, minutes=59))

    assert "东京（你这边）这会儿" not in second and TOLD_TO_BRING_UP not in second
    assert len(weather.days_asked()) == 1  # kept

    assert TOLD_TO_BRING_UP in await anew(client, llm, settings, timedelta(hours=3))


@pytest.mark.parametrize(
    ("weather", "said"),
    [
        (FakeWeather(code=2, later_code=61), "多云，18°C；今天 15～21°C，今天晚些时候还会下雨。"),
        (FakeWeather(code=2, later_code=73), "今天晚些时候还会下雪。"),
        (FakeWeather(code=95), "雷雨，18°C；今天 15～21°C。"),
        (FakeWeather(code=1, yesterday_high=30.4), "比昨天冷了不少（最高气温低了 9°C）。"),
        (FakeWeather(code=1, yesterday_low=7.4), "比昨天热了不少（最低气温高了 8°C）。"),
    ],
    ids=["rain-later", "snow-later", "thunder-now", "colder", "warmer"],
)
async def test_on_a_day_that_stands_out_she_may_bring_it_up_however_lately_they_talked(
    make_client: ClientFactory, settings: Settings, weather: FakeWeather, said: str
):
    clock = FakeClock(NOON)
    _, llm, client, _ = await talk(make_client, weather, clock=clock)

    told = await anew(client, llm, settings, timedelta(minutes=5))

    assert said in told
    assert TOLD_TO_BRING_UP in told


@pytest.mark.parametrize(
    ("weather", "said"),
    [
        (FakeWeather(code=61, ahead=[61, 61], later_code=0), "雨，18°C；今天 15～21°C。"),
        (
            FakeWeather(code=61, ahead=[61, 0], later_code=61),
            "雨，18°C；今天 15～21°C，今天晚些时候还会下雨。",
        ),
        (
            FakeWeather(code=0, ahead=[61], later_code=0),
            "晴，18°C；今天 15～21°C，今天晚些时候还会下雨。",
        ),
    ],
    ids=["about-to-stop", "again-after-it-stops", "within-the-hour"],
)
async def test_rain_later_is_rain_to_come_not_the_rain_now_about_to_stop(
    make_client: ClientFactory, weather: FakeWeather, said: str
):
    [told], *_ = await talk(make_client, weather)

    assert f"东京（你这边）这会儿：{said}" in told


async def test_a_swing_under_eight_degrees_does_not_stand_out(
    make_client: ClientFactory, settings: Settings
):
    clock = FakeClock(NOON)
    weather = FakeWeather(code=1, yesterday_high=28.4)  # 7 degrees warmer yesterday
    _, llm, client, _ = await talk(make_client, weather, clock=clock)

    told = await anew(client, llm, settings, timedelta(minutes=5))

    assert "东京（你这边）这会儿" not in told and TOLD_TO_BRING_UP not in told


async def test_with_a_city_she_knows_where_the_producer_is_and_the_weather_and_warnings_there(
    make_client: ClientFactory, settings: Settings
):
    clock = FakeClock(NOON)
    weather = FakeWeather(code=0)
    qweather = FakeQWeather(icon="104", temperature=-5, high=-1, low=-8, alerts=[
        alert("哈尔滨市气象台发布寒潮蓝色预警信号"),
        alert("哈尔滨市气象台解除大风蓝色预警信号", code="cancel"),
        alert("哈尔滨市气象台发布道路结冰黄色预警信号"),
    ])
    [first], llm, client, _ = await talk(
        make_client, weather, qweather, city=city_of(HARBIN), clock=clock
    )

    told = await anew(client, llm, settings, timedelta(minutes=5))

    assert "制作人在哈尔滨（黑龙江省，中国），这是制作人自己在档案里填的" in told
    assert "制作人那边（哈尔滨）这会儿：阴，-5°C；今天 -8～-1°C。" in told
    assert (
        "制作人那边正生效的气象预警：哈尔滨市气象台发布寒潮蓝色预警信号；"
        "哈尔滨市气象台发布道路结冰黄色预警信号。"
    ) in told
    assert "解除" not in told
    # a warning in force there, though they talked just now; Tokyo's day is like any other
    assert TOLD_TO_BRING_UP in told and "东京（你这边）" not in told
    assert first.index("制作人在哈尔滨") < first.index("东京（你这边）") < first.index("制作人那边（")
    assert len(weather.days_asked()) == 1  # Tokyo's alone: there, QWeather's
    for path in ("/v7/weather/now", "/v7/weather/24h", "/v7/weather/3d"):
        assert qweather.asked(path) == [{"location": "126.54,45.80"}]  # kept an hour
    assert qweather.asked("/v7/historical/weather") == [{"location": "101050101", "date": "20261030"}]
    assert qweather.warnings_asked()[0] == "/weatheralert/v1/current/45.80/126.54"
    assert len(qweather.warnings_asked()) == 1  # kept an hour


@pytest.mark.parametrize(
    ("weather", "qweather", "said", "kept"),
    [
        (
            FakeWeather(code=1), FakeQWeather(later_icon="305"),
            "制作人那边（哈尔滨）这会儿：晴，18°C；今天 15～21°C，今天晚些时候还会下雨。",
            "东京（你这边）这会儿",
        ),
        (
            FakeWeather(code=61), FakeQWeather(),
            "东京（你这边）这会儿：雨，18°C；今天 15～21°C。", "制作人那边（哈尔滨）这会儿",
        ),
    ],
    ids=["rain-there", "rain-in-tokyo"],
)
async def test_a_day_that_stands_out_on_one_side_frees_her_to_bring_up_that_side_alone(
    make_client: ClientFactory, settings: Settings, weather: FakeWeather,
    qweather: FakeQWeather, said: str, kept: str,
):
    clock = FakeClock(NOON)
    _, llm, client, _ = await talk(
        make_client, weather, qweather, city=city_of(HARBIN), clock=clock
    )

    told = await anew(client, llm, settings, timedelta(minutes=5))

    assert said in told and kept not in told
    assert TOLD_TO_BRING_UP in told


async def test_each_warning_is_told_once_without_its_full_stop_doubled(
    make_client: ClientFactory,
):
    qweather = FakeQWeather(alerts=[
        alert("哈尔滨市气象台2026年10月31日10时发布大风蓝色预警信号。", id="2"),
        alert("哈尔滨市气象台发布寒潮蓝色预警信号", id="3"),
        alert("哈尔滨市气象台发布寒潮黄色预警信号", code="update", id="4", supersedes=["3"]),
        alert("哈尔滨市气象台2026年10月31日10时发布大风蓝色预警信号", id="5"),
    ])

    [told], *_ = await talk(make_client, FakeWeather(), qweather, city=city_of(HARBIN))

    assert (
        "制作人那边正生效的气象预警：哈尔滨市气象台2026年10月31日10时发布大风蓝色预警信号；"
        "哈尔滨市气象台发布寒潮黄色预警信号。\n"
    ) in told


async def test_in_tokyo_too_tokyos_weather_is_told_once_as_theirs_both(
    make_client: ClientFactory,
):
    weather = FakeWeather(code=0)
    qweather = FakeQWeather(cities=[SHINJUKU])

    [told], *_ = await talk(make_client, weather, qweather, city=city_of(SHINJUKU))

    assert "你和制作人都在东京一带，东京这会儿：晴" in told
    assert "制作人那边（" not in told and "东京（你这边）" not in told
    assert len(weather.days_asked()) == 1 and qweather.asked("/v7/weather/now") == []


async def test_without_the_deployers_qweather_the_city_is_neither_told_nor_used(
    make_client: ClientFactory, settings: Settings
):
    weather = FakeWeather(code=0)
    qweather = FakeQWeather()

    [told], *_ = await talk(
        make_client, weather, qweather, city=city_of(DONGCHENG),
        settings=replace(settings, qweather=None),
    )

    assert "东城" not in told and "制作人那边" not in told
    assert "东京（你这边）这会儿" in told
    assert len(weather.days_asked()) == 1 and qweather.requests == []


async def test_without_any_weather_she_is_told_none_but_where_the_producer_is(
    make_client: ClientFactory,
):
    [told], *_ = await talk(
        make_client, FakeWeather(failing=True), FakeQWeather(failing=True),
        city=city_of(DONGCHENG),
    )

    assert "制作人在东城（北京，中国）" in told
    assert "这会儿" not in told and TOLD_TO_BRING_UP not in told


async def test_at_the_top_of_the_hour_none_is_fetched_and_she_is_told_none(
    make_client: ClientFactory,
):
    weather = FakeWeather()

    [told], *_ = await talk(make_client, weather, clock=FakeClock(NOON.replace(minute=1)))

    assert "这会儿" not in told and TOLD_TO_BRING_UP not in told and weather.requests == []


async def test_reaching_out_and_in_a_call_she_knows_the_weather_but_not_at_the_bar_nor_posting(
    make_client: ClientFactory,
):
    clock = FakeClock(NOON)
    weather = FakeWeather(clock=clock)
    client = make_client(FakeLLM(), clock=clock, weather_transport=weather.transport())
    her_now = backend_of(client).her_now

    for occasion in ("typing", "in_call", "apart"):
        known = await her_now.weather(occasion, None, NOON, None)
        assert known is not None and known.tokyo is not None, occasion
    for occasion in ("visit", "moments"):
        assert await her_now.weather(occasion, None, NOON, None) is None, occasion


async def test_in_a_call_they_were_last_in_touch_before_it_connected(
    make_client: ClientFactory, settings: Settings
):
    _, _, client, conversation = await talk(make_client, FakeWeather(failing=True))
    database = settings.database_path
    last_contact(database, conversation, NOON - timedelta(hours=5))
    connected_call(database, conversation, NOON - timedelta(hours=4), 600)
    with sqlite3.connect(database) as db:  # a turn of the call under way
        db.execute(
            "INSERT INTO messages (conversation_id, role, text, created_at)"
            " VALUES (?, 'user', '喂', ?)",
            (conversation, (NOON - timedelta(minutes=1)).isoformat()),
        )
    user = user_id(database, "producer")
    backend = backend_of(client)

    async def before(at: datetime) -> datetime | None:
        return await backend.database.read(
            lambda db: read_last_contact(db, user, "mano", before=at)
        )

    assert await before(NOON - timedelta(minutes=2)) == NOON - timedelta(hours=4) + timedelta(
        seconds=600
    )
    assert await before(NOON - timedelta(hours=4)) == NOON - timedelta(hours=5)
    assert await before(NOON - timedelta(hours=6)) is None


class _Slow(httpx.AsyncBaseTransport):
    """Answers as `answer` does, once `go` is set."""

    def __init__(self, answer: httpx.MockTransport) -> None:
        self.answer = answer
        self.go = asyncio.Event()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        await self.go.wait()
        return await self.answer.handle_async_request(request)


async def test_a_day_is_waited_on_no_longer_than_asked_and_kept_once_fetched():
    clock = FakeClock(NOON)
    slow = _Slow(FakeWeather(clock=clock).transport())
    weathers = Weathers(clock, slow)
    try:
        assert await weathers.today(TOKYO, 0.01) is None
        slow.go.set()
        await asyncio.sleep(0.05)
        assert await weathers.today(TOKYO, 0) == Today(Weather("clear", 18), None, 21, 15, 21, 15)
    finally:
        await weathers.aclose()


async def test_a_spots_day_is_kept_three_hours_and_after_failing_none_is_asked_for_ten_minutes():
    clock = FakeClock(NOON)
    weather = FakeWeather(clock=clock)
    weathers = Weathers(clock, weather.transport())
    harbin = Spot(45.80, 126.54)
    try:
        assert await weathers.today(harbin, 1) is not None
        clock.advance(hours=2, minutes=50)
        assert await weathers.today(harbin, 1) is not None
        assert len(weather.requests) == 1

        clock.advance(minutes=20)
        weather.failing = True
        assert await weathers.today(harbin, 1) is None
        assert await weathers.today(TOKYO, 1) is None  # another cell: asked all the same
        clock.advance(minutes=9)
        assert await weathers.today(harbin, 1) is None
        assert len(weather.requests) == 3

        weather.failing = False
        clock.advance(minutes=1)
        assert await weathers.today(harbin, 1) is not None
        assert len(weather.requests) == 4
    finally:
        await weathers.aclose()


HARBIN_AT = Spot(45.80298, 126.53505)


def qweather_on(fake: FakeQWeather, clock: FakeClock) -> QWeather:
    fake.clock = clock
    settings = account()
    return QWeather(lambda: settings, clock, fake.transport())


async def test_the_producers_day_is_kept_an_hour_no_longer_than_the_day_there_and_after_failing_none_is_asked_for_ten_minutes():
    clock = FakeClock(NOON)  # 11:20 in Harbin
    fake = FakeQWeather()
    qweather = qweather_on(fake, clock)
    try:
        assert await qweather.today(HARBIN_AT, 1) == Today(Weather("clear", 18), None, 21, 15, 21, 15)
        clock.advance(minutes=59)
        assert await qweather.today(HARBIN_AT, 1) is not None
        assert len(fake.asked("/v7/weather/now")) == 1

        clock.advance(minutes=1)
        assert await qweather.today(HARBIN_AT, 1) is not None
        assert len(fake.asked("/v7/weather/now")) == 2
        assert len(fake.asked("/v7/historical/weather")) == 1  # yesterday's kept

        clock.advance(hours=11, minutes=20)  # 23:40 in Harbin
        assert await qweather.today(HARBIN_AT, 1) is not None
        clock.advance(minutes=30)  # the day after there, within the hour
        assert await qweather.today(HARBIN_AT, 1) is not None
        assert len(fake.asked("/v7/weather/now")) == 4
        assert [q["date"] for q in fake.asked("/v7/historical/weather")] == ["20261030", "20261031"]
        assert len(fake.lookups()) == 1  # the city's ID kept for good

        clock.advance(hours=1)
        fake.failing = True
        assert await qweather.today(HARBIN_AT, 1) is None
        clock.advance(minutes=9)
        assert await qweather.today(HARBIN_AT, 1) is None
        assert len(fake.asked("/v7/weather/now")) == 5

        fake.failing = False
        clock.advance(minutes=1)
        assert await qweather.today(HARBIN_AT, 1) is not None
    finally:
        await qweather.aclose()


@pytest.mark.parametrize(
    "fake", [FakeQWeather(no_records=True), FakeQWeather(cities=[])], ids=["no-records", "no-city"]
)
async def test_without_yesterdays_records_the_producers_day_goes_without_them(fake: FakeQWeather):
    qweather = qweather_on(fake, FakeClock(NOON))
    try:
        assert await qweather.today(HARBIN_AT, 1) == Today(Weather("clear", 18), None, 21, 15)
    finally:
        await qweather.aclose()


@pytest.mark.parametrize(
    ("fake", "now", "later"),
    [
        (FakeQWeather(icon="150", later_icon="456"), Weather("clear", 18), "snow"),
        (FakeQWeather(icon="302"), Weather("thunder", 18), None),
        (FakeQWeather(icon="511"), Weather("overcast", 18), None),
    ],
    ids=["snow-later", "thunder", "haze"],
)
async def test_the_producers_day_is_of_qweathers_icons(
    fake: FakeQWeather, now: Weather, later: str | None
):
    qweather = qweather_on(fake, FakeClock(NOON))
    try:
        today = await qweather.today(HARBIN_AT, 1)
        assert today is not None and (today.now, today.later) == (now, later)
    finally:
        await qweather.aclose()


async def test_the_producers_day_is_todays_where_the_spot_is_though_the_days_told_have_not_turned():
    fake = FakeQWeather(days_not_turned=True, yesterday_high=30)
    qweather = qweather_on(fake, FakeClock(NOON))
    try:
        today = await qweather.today(HARBIN_AT, 1)
        assert today is not None and (today.high, today.yesterday_high) == (21, 30)
    finally:
        await qweather.aclose()


async def test_the_producers_day_is_none_for_an_icon_of_none_of_the_kinds():
    qweather = qweather_on(FakeQWeather(icon="999"), FakeClock(NOON))
    try:
        assert await qweather.today(HARBIN_AT, 1) is None
    finally:
        await qweather.aclose()


async def test_the_producers_day_is_waited_on_no_longer_than_asked_and_kept_once_fetched():
    clock = FakeClock(NOON)
    fake = FakeQWeather(clock=clock)
    slow = _Slow(fake.transport())
    settings = account()
    qweather = QWeather(lambda: settings, clock, slow)
    try:
        assert await qweather.today(HARBIN_AT, 0.01) is None
        slow.go.set()
        await asyncio.sleep(0.05)
        assert await qweather.today(HARBIN_AT, 0) is not None
    finally:
        await qweather.aclose()
