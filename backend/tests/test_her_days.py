"""How she feels where her cycle has her (GLOSSARY.md「周期」): in her period and the days
before it, what she is told of now (「此刻」) ends, after her jobs, with how she feels by the
day and how she keeps it to herself; on her other days, or while the deployment or the user
has cycles off, nothing. Typing, in a call and reaching out alike; never in what her photos are
prompted with.

Driven through the backend's external API. Where she is is found with her true cycle
(`her_cycle`) for the user and the character, with the tests' secret key, and the clock
moved there; where the clock cannot be (a call's, `test_call_turns.NOW`, and reaching out's,
as `test_schedule_she_knows` has it), a secret key is found that has her there that day."""

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
import pytest

from eidolon.config import Settings
from eidolon.her_cycle import HerDay, Period, Premenstrual, cycle_seed, her_day
from eidolon.her_now import LOOK_UP_BOTH
from tests.conftest import ClientFactory
from tests.fakes import (
    FAKE_JUDGE,
    FakeClock,
    FakeIdentityProvider,
    FakeImageService,
    FakeLLM,
    FakeRandom,
    context_of,
)
from tests.test_admin_commands import user_id
from tests.test_admin_users import ADMIN, admin_beside
from tests.test_calendar import REPLY, told_now
from tests.test_cycles_switch import switch
from tests.test_call_turns import MANO_REPLY, NOW, CallUnderTest, spoken
from tests.test_photos import IMAGE, WORDS, asking, photo_events, settled
from tests.test_reach_outs import backend_of, last_contact
from tests.test_schedule_saving import WEEK, placed, publish, save
from tests.test_schedule_she_knows import EARLY_MONDAY, UNDER_WAY
from tests.test_text_turn import send_turn, start_conversation

PERIOD_EARLY = (
    "你今天身体很不舒服：浑身没力气，说话比平时少、慢，偶尔会走神。"
    "身上可能发冷、腰酸、身子发沉、只想窝着不动，喝点热的会好些。"
)
PERIOD_LATE = "你这几天身体还有点虚：比平时容易累，不太想出门，不过已经比前两天好多了。"
PREMENSTRUAL_FAR = "你这几天心情有点起伏：比平时敏感，小事也容易在意。"
PREMENSTRUAL_NEAR = (
    "你这两天特别容易烦躁、委屈，小事也会在意很久，自己也说不清为什么心情不好；"
    "身上也可能有点发胀、睡不踏实。"
)
UNSAID = (
    "这是你自己身体的事，你不会说出经期、月经、生理期这些词，也不提出血、卫生用品这类细节；"
    "只让状态自然地流露在语气和小事里。制作人问起时，照你的性格含糊带过（比如说有点累、没睡好）。"
)
ASKED_IN_PERIOD = (
    "制作人直接问到是不是那几天时，照你的性格决定认不认：可以含糊地认下，也可以岔开，"
    "或者嫌他问得太直接；认的话也用你自己的说法，不说出那个词，也不细讲。"
)
ASKED_BEFORE = (
    "那几天还没到，只是快了；制作人直接问到时，照你的性格决定怎么应：可以含糊地说快了，"
    "也可以岔开，或者嫌他问得太直接；不说出那个词，也不细讲。"
)
STILL_HERSELF = (
    "不舒服不是冲制作人发火的理由，也不拿它要挟或讨好处；工作照常，人设里的规则照旧。"
    "身上的不适一次最多顺口带出一样，换着说，不要每次都提同一样，也不逐条描述身体。"
)
IN_PERIOD = f"{UNSAID}{ASKED_IN_PERIOD}{STILL_HERSELF}"
BEFORE_IT = f"{UNSAID}{ASKED_BEFORE}{STILL_HERSELF}"
NOTHING_OF_IT = ("身体", "心情有点起伏", "烦躁", "经期", "那几天")

SHANGHAI = ZoneInfo("Asia/Shanghai")
START = datetime(2026, 10, 1, 4, tzinfo=UTC)
"""Noon in Shanghai, where the producer is, without a time zone of their own."""

MANO_UNDER_18 = True
"""Mano is 16 in the tests' character configuration."""


@pytest.fixture
def settings(settings: Settings) -> Settings:
    """With cycles on, as the deployment has them unless it turns them off."""
    return replace(settings, cycles=True)


def where(settings: Settings, day: date) -> HerDay:
    """Where her true cycle has the producer's Mano on `day`."""
    seed = cycle_seed(settings.secret_key, user_id(settings, "producer"), "mano")
    return her_day(seed, MANO_UNDER_18, day)


def a_noon_when(settings: Settings, wanted: Callable[[HerDay], bool]) -> datetime:
    """The first noon in Shanghai from `START` on when Mano is where `wanted`."""
    for n in range(120):
        noon = START + timedelta(days=n)
        if wanted(where(settings, noon.astimezone(SHANGHAI).date())):
            return noon
    raise AssertionError("she is never there")


def a_key_when(settings: Settings, at: datetime, wanted: Callable[[HerDay], bool]) -> str:
    """A secret key with which Mano is where `wanted` on the producer's day at `at`."""
    for n in range(1000):
        key = f"test-secret-key-{n}"
        if wanted(where(replace(settings, secret_key=key), at.astimezone(SHANGHAI).date())):
            return key
    raise AssertionError("no key has her there")


def in_period(early: bool) -> Callable[[HerDay], bool]:
    return lambda d: isinstance(d, Period) and (d.day <= 2) == early


def premenstrual(near: bool) -> Callable[[HerDay], bool]:
    return lambda d: isinstance(d, Premenstrual) and (d.days_left <= 2) == near


def on_a_day(
    make_client: ClientFactory,
    settings: Settings,
    wanted: Callable[[HerDay], bool],
    llm: FakeLLM,
    deployment: Settings | None = None,
    **services,
) -> httpx.AsyncClient:
    """A client of the producer's on a noon Mano is where `wanted`, signed in then, so that
    their session has not run out by it; the deployment as `settings` has it unless
    `deployment` is given."""
    make_client(FakeLLM())  # the producer, signed up
    clock = FakeClock(a_noon_when(settings, wanted))
    return make_client(llm, clock=clock, settings=deployment or settings, **services)


async def told_on(
    make_client: ClientFactory,
    settings: Settings,
    wanted: Callable[[HerDay], bool],
    deployment: Settings | None = None,
) -> str:
    """What she is told of now in a typed turn on a day she is where `wanted`, the deployment
    as `settings` has it unless `deployment` is given."""
    llm = FakeLLM(REPLY)
    client = on_a_day(make_client, settings, wanted, llm, deployment)
    return await told_now(client, llm)


@pytest.mark.parametrize(
    ("wanted", "feeling", "keeping"),
    [
        (in_period(early=True), PERIOD_EARLY, IN_PERIOD),
        (in_period(early=False), PERIOD_LATE, IN_PERIOD),
        (premenstrual(near=False), PREMENSTRUAL_FAR, BEFORE_IT),
        (premenstrual(near=True), PREMENSTRUAL_NEAR, BEFORE_IT),
    ],
    ids=[
        "period-first-two-days", "period-from-the-third", "premenstrual-3-or-more",
        "premenstrual-last-two",
    ],
)
async def test_in_her_period_and_before_it_what_she_is_told_of_now_ends_with_how_she_feels(
    make_client: ClientFactory,
    settings: Settings,
    wanted: Callable[[HerDay], bool],
    feeling: str,
    keeping: str,
):
    told = await told_on(make_client, settings, wanted)

    now, *_ = told.split("\n\n")
    assert now.startswith("# 此刻\n")
    assert now.endswith(f"\n{feeling}\n{keeping}")


async def test_with_jobs_saved_she_is_told_it_after_them(
    make_client: ClientFactory, settings: Settings
):
    """On Wednesday 14:00 in Shanghai, a job of hers saved for then: typing, she is told the
    job under way, and to look up the rest."""
    make_client(FakeLLM())  # the producer, signed up
    wednesday = EARLY_MONDAY + timedelta(days=2, hours=13)
    keyed = replace(settings, secret_key=a_key_when(settings, wednesday, in_period(early=False)))
    llm = FakeLLM(REPLY)
    clock = FakeClock(EARLY_MONDAY)
    client = make_client(llm, clock=clock, settings=keyed)
    publish(settings.database_path, WEEK, ("声乐课", 1, None))
    await save(client, WEEK, placed("声乐课", 2, 1))
    clock.now = wednesday

    told = await told_now(client, llm)

    now, *_ = told.split("\n\n")
    assert now.endswith(
        f"\n现在（下午 12–18 点）你正在声乐课：说明。{UNDER_WAY}\n{LOOK_UP_BOTH}"
        f"\n{PERIOD_LATE}\n{IN_PERIOD}"
    )


async def test_on_her_other_days_she_is_told_nothing_of_it(
    make_client: ClientFactory, settings: Settings
):
    told = await told_on(make_client, settings, lambda d: d is None)

    assert not any(words in told for words in NOTHING_OF_IT)


async def test_with_the_deployment_turning_cycles_off_she_is_told_nothing_of_it(
    make_client: ClientFactory, settings: Settings
):
    told = await told_on(
        make_client, settings, in_period(early=True), replace(settings, cycles=False)
    )

    assert not any(words in told for words in NOTHING_OF_IT)


async def test_the_admin_console_turning_cycles_off_overrides_env(
    make_client: ClientFactory, settings: Settings, github: FakeIdentityProvider
):
    llm = FakeLLM(REPLY)
    client = on_a_day(
        make_client, settings, in_period(early=True), llm,
        replace(settings, admins=frozenset({ADMIN})),
    )

    async with admin_beside(client, github) as admin:
        turned_off = await admin.put("/api/admin/config/cycles", json={"enabled": False})
    told = await told_now(client, llm)

    assert turned_off.status_code == 200
    assert not any(words in told for words in NOTHING_OF_IT)


async def test_with_the_user_turning_cycles_off_she_is_told_nothing_of_it_till_it_is_on_again(
    make_client: ClientFactory, settings: Settings
):
    llm = FakeLLM(REPLY, REPLY)
    client = on_a_day(make_client, settings, in_period(early=True), llm)

    await switch(client, False)
    told_off = await told_now(client, llm)
    await switch(client, True)
    told_on_again = await told_now(client, llm)

    assert not any(words in told_off for words in NOTHING_OF_IT)
    now, *_ = told_on_again.split("\n\n")
    assert now.endswith(f"\n{PERIOD_EARLY}\n{IN_PERIOD}")


async def test_in_a_call_she_is_told_it_too(make_client: ClientFactory, settings: Settings):
    client = make_client(FakeLLM())
    conversation = await start_conversation(client)
    keyed = replace(settings, secret_key=a_key_when(settings, NOW, in_period(early=True)))
    call = await CallUnderTest.of(keyed, client, conversation)
    call_llm = FakeLLM(MANO_REPLY)

    await call.run(call_llm, [spoken("早上好")])

    now, *_ = context_of(call_llm.prompts[-1]).split("\n\n")
    assert now.endswith(f"\n{PERIOD_EARLY}\n{IN_PERIOD}")


async def test_reaching_out_she_is_told_it_too(make_client: ClientFactory, settings: Settings):
    """She reaches out at 20:00 in Shanghai on September 23, as `test_schedule_she_knows`
    has her."""
    make_client(FakeLLM())  # the producer, signed up
    at = datetime(2026, 9, 23, 12, tzinfo=UTC)
    keyed = replace(
        settings, secret_key=a_key_when(settings, at, premenstrual(near=True)), reach_outs=True
    )
    llm = FakeLLM(REPLY, REPLY)
    clock = FakeClock(at - timedelta(hours=3))
    client = make_client(llm, clock=clock, random=FakeRandom(0), settings=keyed)
    conversation = await start_conversation(client)
    await send_turn(client, conversation, "我去练习了")
    last_contact(settings.database_path, conversation, datetime(2026, 9, 22, 13, tzinfo=UTC))
    clock.now = at

    await backend_of(client).reach_outs.run_due()

    assert len(llm.prompts) == 2
    now, *_ = context_of(llm.prompts[-1]).split("\n\n")
    assert "你们这会儿没在说话" in now
    assert now.endswith(f"\n{PREMENSTRUAL_NEAR}\n{BEFORE_IT}")


async def test_what_her_photos_are_prompted_with_tells_nothing_of_it(
    make_client: ClientFactory, settings: Settings
):
    image = FakeImageService()
    llm = FakeLLM([f"<photo>\nshot: selfie\nframing: upper body\n</photo>{WORDS}"])
    client = on_a_day(
        make_client, settings, in_period(early=True), llm,
        replace(settings, image=IMAGE, judge=FAKE_JUDGE, affinity_and_gifts=False),
        clients=asking(), image_transport=image.transport(),
    )
    conversation = await start_conversation(client)

    [photo] = photo_events(await send_turn(client, conversation, "发张自拍给我看看"))
    await settled(client, photo["id"])

    assert PERIOD_EARLY in context_of(llm.prompts[0])
    [request] = image.requests
    assert request["body"]["input"].isascii()
