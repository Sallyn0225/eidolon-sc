"""What she knows of now (GLOSSARY.md「此刻」), as `HerNow` gives it for each occasion: typing,
in a call, reaching out, visiting the bar.

Driven through `HerNow` taken from the assembled backend, on a clock the tests move and the
real database, her jobs saved through the API as the producer saves them."""

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import httpx

from eidolon.affinity import JOB_DONE_STEP
from eidolon.config import Settings
from eidolon.her_now import Occasion
from eidolon.producer import Birthday, ProducerProfile
from tests.conftest import CharacterConfig, ClientFactory
from tests.fakes import FAKE_JUDGE, FakeClock, FakeLLM
from tests.test_affinity import keep
from tests.test_delete_account import user_id
from tests.test_her_days import IN_PERIOD, PERIOD_EARLY, a_key_when, in_period
from tests.test_reach_outs import backend_of
from tests.test_schedule_saving import WEEK, placed, publish, save
from tests.test_schedule_she_knows import ABOUT_THEM, EARLY_MONDAY, HER_JOBS, UNDER_WAY
from tests.test_schedule_weeks import live_in
from tests.test_world_setting import write_world

HER_BIRTHDAY = "今天是你的生日。"
TOKYO_MIDNIGHT = datetime(2026, 4, 24, 15, 30, tzinfo=UTC)
"""Mano's birthday (04-25, the fixture's) at 00:30 in Tokyo; still 04-24, 23:30 in Shanghai,
where the producer is."""
SHANGHAI = "Asia/Shanghai"
LOS_ANGELES = "America/Los_Angeles"


async def told(
    client: httpx.AsyncClient,
    occasion: Occasion = "apart",
    character: str = "mano",
    *,
    profile: ProducerProfile = ProducerProfile(),
    timezone: str = SHANGHAI,
    last_contact: datetime | None = None,
    affinity_lines: Sequence[str] = (),
) -> list[str]:
    """What the producer's `character` is told of now on `occasion`, the producer in
    `timezone`, their device reporting it: by default reaching out, where she is told all of
    it (typing and in a call she looks some of it up, `test_look_ups`)."""
    backend = backend_of(client)
    her_now = backend.her_now
    known = await her_now.read(
        user_id(backend.settings.database_path, "producer"), character,
        None if occasion == "apart" else timezone, occasion,
    )
    return her_now.lines(
        known, occasion, backend.clock(), timezone, profile, last_contact, affinity_lines
    )


def section(lines: Sequence[str]) -> str:
    return "\n".join(lines)


async def test_her_birthday_begins_at_midnight_in_tokyo_whatever_the_producers_day(
    make_client: ClientFactory,
):
    clock = FakeClock(TOKYO_MIDNIGHT - timedelta(hours=1))
    client = make_client(FakeLLM(), clock=clock)

    before = section(await told(client))
    clock.advance(hours=1)
    on_the_day = section(await told(client))

    assert HER_BIRTHDAY not in before
    [line] = [line for line in on_the_day.splitlines() if HER_BIRTHDAY in line]
    assert "不要每句都提" in line and "不向制作人要礼物" in line and "祝福你就接受" in line
    assert on_the_day.startswith("# 此刻\n现在是 2026年4月24日")  # the producer's day still


async def test_on_others_birthdays_she_is_told_whose_herself_not_among_them(
    make_client: ClientFactory, characters: CharacterConfig
):
    """Kogane's birthday is 02-25 (the fixture's); the clerk counts among the others."""
    characters.add("hazuki", "七草はづき", "sheet", idol_id=91, birthday="02-25")
    characters.add("meguru", "八宮めぐる", "sheet", idol_id=3, birthday="02-25")
    client = make_client(FakeLLM(), clock=lambda: datetime(2026, 2, 25, 3, tzinfo=UTC))

    with_mano = section(await told(client, character="mano"))
    with_kogane = section(await told(client, character="kogane"))

    others = "今天是八宮めぐる、七草はづき、月岡恋鐘的生日。你知道这件事，制作人提起时能接上；不用主动提。"
    assert others in with_mano and HER_BIRTHDAY not in with_mano
    assert "今天是八宮めぐる、七草はづき的生日。" in with_kogane and HER_BIRTHDAY in with_kogane


async def test_on_her_unit_mates_birthday_she_may_bring_it_up_on_the_others_only_know_of_it(
    make_client: ClientFactory, characters: CharacterConfig
):
    """Hiori is in Mano's unit, Kogane (02-25, the fixture's) in another (`write_world`)."""
    write_world(characters)
    characters.add("hiori", "風野灯織", "sheet", idol_id=2, birthday="02-25")
    client = make_client(FakeLLM(), clock=lambda: datetime(2026, 2, 25, 3, tzinfo=UTC))

    lines = await told(client)

    assert (
        "今天是你的组合伙伴風野灯織的生日。可以顺口提一句，不要替她们向制作人要祝福，"
        "也不要催制作人做什么。"
    ) in lines
    assert "今天是月岡恋鐘的生日。你知道这件事，制作人提起时能接上；不用主动提。" in lines


async def test_on_a_holiday_she_is_told_which_right_after_the_time(make_client: ClientFactory):
    client = make_client(FakeLLM(), clock=lambda: datetime(2026, 11, 3, 3, tzinfo=UTC))

    now, *rest = await told(client)

    assert now.startswith("# 此刻\n现在是 2026年11月3日")
    assert rest == ["今天是日本的节假日：文化の日。制作人提起再说，不用主动提。"]


ON_THE_DAY = "今天是2年前你站上「THE IDOLM@STER SHINY COLORS 6thLIVE」第1天的日子（2024年3月2日，ベルーナドーム）。"
"""Mano's line on 03-02 two years after (`write_world`'s 6thLIVE)."""


async def test_on_the_day_of_a_live_she_stood_on_years_ago_she_is_told_it_is_past(
    make_client: ClientFactory, characters: CharacterConfig
):
    """In Tokyo 2026-03-02, 09:00; she stood on 6thLIVE's first day, 2024-03-02, and on no
    other live on the day."""
    write_world(characters)
    client = make_client(FakeLLM(), clock=lambda: datetime(2026, 3, 2, 0, tzinfo=UTC))

    [line] = [line for line in await told(client) if "年前你站上" in line]

    assert line.startswith(ON_THE_DAY)
    assert "今天没有这场演出" in line and "当回忆" in line


async def test_on_the_day_of_a_live_she_was_absent_from_or_still_to_come_she_is_told_nothing_of_it(
    make_client: ClientFactory, characters: CharacterConfig
):
    """6thLIVE's second day, 03-03, her CV absent; and 8thLIVE's first day, 2026-11-07,
    which is today, not years ago."""
    write_world(characters)
    absent = make_client(FakeLLM(), clock=lambda: datetime(2026, 3, 3, 0, tzinfo=UTC))
    to_come = make_client(FakeLLM(), clock=lambda: datetime(2026, 11, 7, 0, tzinfo=UTC))

    assert "年前你站上" not in section(await told(absent))
    assert "年前你站上" not in section(await told(to_come))


async def test_on_a_day_that_is_nothing_she_is_told_nothing_of_it(
    make_client: ClientFactory, characters: CharacterConfig
):
    """No one's birthday nor a holiday in Tokyo, nor a live she stood on: the day before
    文化の日, 21:00 there."""
    write_world(characters)
    client = make_client(FakeLLM(), clock=lambda: datetime(2026, 11, 2, 12, tzinfo=UTC))

    lines = await told(client)

    assert len(lines) == 1 and lines[0].startswith("# 此刻\n")


def jobs_told(lines: list[str]) -> list[str]:
    """The lines from those of her jobs on (`schedule_lines`), the last but her cycle's."""
    return lines[lines.index(HER_JOBS):]


async def scheduling(
    make_client: ClientFactory, settings: Settings, *jobs: tuple[str, int, int, int],
    character: str = "mano", deployment: Settings | None = None, llm: FakeLLM | None = None,
) -> tuple[httpx.AsyncClient, FakeClock]:
    """A client of the producer's that saved the character's `jobs` of `WEEK`, each its name,
    length, day and slot, on Monday early in the morning, and its clock; the deployment as
    `settings` has it unless `deployment` is given, its chat model `llm` if given."""
    clock = FakeClock(EARLY_MONDAY)
    client = make_client(llm or FakeLLM(), clock=clock, settings=deployment or settings)
    publish(
        settings.database_path, WEEK, *((name, length, None) for name, length, _, _ in jobs),
        character=character,
    )
    res = await save(client, WEEK, *(placed(name, day, slot) for name, _, day, slot in jobs))
    assert len(res.json()["saved"]) == len(jobs), res.text
    return client, clock


async def test_she_is_told_her_jobs_by_day_from_today_the_one_under_way_apart(
    make_client: ClientFactory, settings: Settings
):
    client, clock = await scheduling(
        make_client, settings,
        ("声乐课", 1, 0, 0), ("拍摄广告", 2, 1, 0), ("开会", 1, 2, 1), ("外景", 3, 3, 0),
        ("访谈", 1, 4, 1), ("晚饭", 1, 6, 2),
    )
    publish(settings.database_path, WEEK, ("组合排练", 1, None), character="kogane")
    await save(client, WEEK, placed("组合排练", 4, 0))
    clock.advance(days=2, hours=13)  # Wednesday 14:00

    lines = await told(client)

    assert lines[0].startswith("# 此刻\n")
    assert jobs_told(lines) == [
        HER_JOBS,
        "周一（前天）上午：声乐课——说明（做完了）",
        "周二（昨天）上午到下午：拍摄广告——说明（做完了）",
        "周四（明天）一整天：外景——说明",
        "周五（后天）下午：访谈——说明",
        "周日晚上：晚饭——说明",
        f"现在（下午 12–18 点）你正在开会：说明。{UNDER_WAY}",
        ABOUT_THEM,
    ]


async def test_west_of_beijing_she_knows_next_week_saved_already_on_their_sunday(
    make_client: ClientFactory, settings: Settings
):
    """Beijing's Monday 01:00 is Los Angeles' Sunday 10:00: this week there is the one
    before Beijing's."""
    clock = FakeClock(EARLY_MONDAY)
    client = make_client(FakeLLM(), clock=clock)
    await live_in(client, LOS_ANGELES)
    publish(settings.database_path, WEEK, ("声乐课", 1, None), ("晚饭", 1, None))
    await save(client, WEEK, placed("声乐课", 4, 0), placed("晚饭", 6, 2))
    clock.advance(days=7)
    publish(settings.database_path, "2026-09-28", ("录音", 1, None), ("访谈", 1, None))
    await save(client, "2026-09-28", placed("录音", 0, 2), placed("访谈", 3, 1))

    lines = await told(client, timezone=LOS_ANGELES)

    assert jobs_told(lines) == [
        HER_JOBS,
        "周五（前天）上午：声乐课——说明（做完了）",
        "周日（今天）晚上：晚饭——说明",
        "下周一（明天）晚上：录音——说明",
        "下周四下午：访谈——说明",
        ABOUT_THEM,
    ]


async def test_before_6_in_the_morning_no_job_is_under_way(
    make_client: ClientFactory, settings: Settings
):
    client, clock = await scheduling(
        make_client, settings, ("拍摄广告", 1, 1, 2), ("声乐课", 1, 2, 0)
    )
    clock.advance(days=2, hours=2)  # Wednesday 03:00

    lines = await told(client)

    assert jobs_told(lines) == [
        HER_JOBS,
        "周二（昨天）晚上：拍摄广告——说明（做完了）",
        "周三（今天）上午：声乐课——说明",
        ABOUT_THEM,
    ]


async def test_with_only_the_one_under_way_she_is_told_it_stands_all_the_same(
    make_client: ClientFactory, settings: Settings
):
    client, clock = await scheduling(make_client, settings, ("拍摄广告", 2, 0, 1))
    clock.advance(hours=18)  # Monday 19:00, its second slot

    lines = await told(client)

    assert jobs_told(lines) == [
        HER_JOBS, f"现在（晚上 18–24 点）你正在拍摄广告：说明。{UNDER_WAY}", ABOUT_THEM,
    ]


async def test_with_none_of_hers_saved_she_is_told_nothing_of_a_schedule(
    make_client: ClientFactory, settings: Settings
):
    client, clock = await scheduling(
        make_client, settings, ("组合排练", 1, 0, 1), character="kogane"
    )
    clock.advance(hours=12)  # Monday 13:00, Kogane's job under way

    lines = await told(client)

    assert HER_JOBS not in lines and "组合排练" not in section(lines)


async def test_last_weeks_jobs_are_not_told(make_client: ClientFactory, settings: Settings):
    client, clock = await scheduling(make_client, settings, ("晚饭", 1, 6, 2))
    clock.advance(days=7)

    lines = await told(client)

    assert HER_JOBS not in lines and "晚饭" not in section(lines)


async def test_with_schedules_off_she_is_told_nothing_of_what_was_saved(
    make_client: ClientFactory, settings: Settings
):
    _, clock = await scheduling(make_client, settings, ("声乐课", 1, 0, 2))
    clock.advance(hours=12)
    off = make_client(FakeLLM(), clock=clock, settings=replace(settings, schedule=False))

    lines = await told(off)

    assert HER_JOBS not in lines and "声乐课" not in section(lines)


FEELS = ["（好感度那几行）", "（判断后的那一行）"]
"""Affinity lines as the caller hands them in."""
HOLIDAY = "今天是日本的节假日：敬老の日。制作人提起再说，不用主动提。"
"""What she is told on `WEEK`'s Monday, a holiday."""
MONDAY_AFTERNOON = EARLY_MONDAY + timedelta(hours=13)
"""Monday 14:00 in Shanghai, 15:00 in Tokyo."""


async def in_her_period(
    make_client: ClientFactory, settings: Settings, *jobs: tuple[str, int, int, int]
) -> httpx.AsyncClient:
    """A client of the producer's, who saved Mano's `jobs` early on `WEEK`'s Monday, at
    `MONDAY_AFTERNOON`, cycles on with a secret key that has her in her period then."""
    make_client(FakeLLM())  # the producer, signed up
    cycling = replace(settings, cycles=True)
    keyed = replace(
        cycling, secret_key=a_key_when(cycling, MONDAY_AFTERNOON, in_period(early=True))
    )
    client, clock = await scheduling(make_client, settings, *jobs, deployment=keyed)
    clock.now = MONDAY_AFTERNOON
    return client


async def test_how_she_feels_ends_the_time_part_her_cycle_the_whole_after_her_jobs(
    make_client: ClientFactory, settings: Settings
):
    client = await in_her_period(make_client, settings, ("声乐课", 1, 2, 0))

    lines = await told(client, affinity_lines=FEELS)

    now, *rest = lines
    assert now.startswith("# 此刻\n") and now.endswith("\n".join(["", *FEELS]))
    assert rest == [
        HOLIDAY, HER_JOBS, "周三（后天）上午：声乐课——说明", ABOUT_THEM, PERIOD_EARLY, IN_PERIOD,
    ]


async def test_visiting_the_bar_she_is_told_only_how_she_feels_and_the_day_in_tokyo(
    make_client: ClientFactory, settings: Settings
):
    """The producer's birthday, a job of hers under way, her period, a last contact: none of
    them told her at the bar, though in a typed turn all are."""
    client = await in_her_period(make_client, settings, ("声乐课", 1, 0, 1))

    async def told_on(occasion: Occasion) -> list[str]:
        return await told(
            client, occasion, profile=ProducerProfile(birthday=Birthday(9, 21)),
            last_contact=MONDAY_AFTERNOON - timedelta(days=1), affinity_lines=FEELS,
        )

    typing = section(await told_on("typing"))
    visiting = await told_on("visit")

    assert all(
        told in typing
        for told in ("现在是", "今天是制作人的生日", "上次和制作人说话是", "你正在声乐课", PERIOD_EARLY)
    )
    assert visiting == [*FEELS, HOLIDAY]


async def test_visiting_the_bar_her_cycle_is_not_read_as_it_is_not_told(
    make_client: ClientFactory, settings: Settings
):
    """In her period, typing she is where her cycle has her; reading for a visit, nowhere."""
    client = await in_her_period(make_client, settings, ("声乐课", 1, 2, 0))
    backend = backend_of(client)
    producer = user_id(settings.database_path, "producer")

    typing = await backend.her_now.read(producer, "mano", SHANGHAI, "typing")
    visiting = await backend.her_now.read(producer, "mano", SHANGHAI, "visit")

    assert typing.her_days(MONDAY_AFTERNOON, SHANGHAI) is not None
    assert visiting.her_days(MONDAY_AFTERNOON, SHANGHAI) is None


async def test_jobs_done_are_counted_before_her_affinity_is_read_after_the_first_step(
    make_client: ClientFactory, settings: Settings
):
    """Her affinity just short of close, by less than a job done raises it."""
    affinity_on = replace(settings, judge=FAKE_JUDGE, affinity_and_gifts=True)
    client, clock = await scheduling(
        make_client, settings, ("声乐课", 1, 0, 0), deployment=affinity_on
    )
    keep(settings.database_path, "producer", 65 - JOB_DONE_STEP / 2, clock())
    clock.now = MONDAY_AFTERNOON
    her_now = backend_of(client).her_now

    known = await her_now.read(user_id(settings.database_path, "producer"), "mano", None, "visit")

    assert known.affinity is not None and known.affinity.tier == "close"


async def test_her_job_done_today_is_the_latest_of_those_done_today(
    make_client: ClientFactory, settings: Settings
):
    """Monday evening's is done, but not today; Tuesday's afternoon one is today's latest,
    the evening's still to come."""
    client, clock = await scheduling(
        make_client, settings,
        ("晚饭", 1, 0, 2), ("声乐课", 1, 1, 0), ("拍摄广告", 1, 1, 1), ("访谈", 1, 1, 2),
    )
    her_now = backend_of(client).her_now
    producer = user_id(settings.database_path, "producer")

    clock.now = EARLY_MONDAY + timedelta(days=1, hours=6)  # Tuesday 07:00
    early = await her_now.read(producer, "mano", None, "typing")
    clock.now = EARLY_MONDAY + timedelta(days=1, hours=18)  # Tuesday 19:00
    evening = await her_now.read(producer, "mano", None, "typing")

    assert early.done_today is None
    assert evening.done_today is not None and evening.done_today.name == "拍摄广告"
