"""Letters on the days that come round (GLOSSARY.md「信」): the producer's birthday, written
on by the one she is closest to; her birthday, if she is close or above; and the day they
first talked come round, 100 days on and every year after. Each is kept as a letter to be
written from the first tick of its day where the producer is, once, only for producers in
touch within the last 30 days; a day gone by without a tick is not made up for.

Driven through the backend's external API, the letters' ticks taken by hand
(`Letters.run_due`), the clock moved, and her affinity, the first turn and the last contact
set in the database directly."""

import sqlite3
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import pytest

from eidolon.config import Settings
from tests.conftest import ClientFactory
from tests.fakes import FakeClock, FakeIdentityProvider, FakeLLM
from tests.test_achievements import turns
from tests.test_admin_users import ADMIN, admin_beside
from tests.test_affinity import keep
from tests.test_letters import (  # noqa: F401
    LETTERS,
    REPLY,
    characters,
    close_with_mano,
    letters,
    settings,
    written,
)
from tests.test_reach_outs import backend_of, last_contact
from tests.test_text_turn import start_conversation

SHANGHAI = ZoneInfo("Asia/Shanghai")
TODAY = "2026-09-25"


def at(day: str, hour: int = 9) -> datetime:
    """`hour` o'clock on `day` in Shanghai, the producer's time zone unset."""
    return datetime.combine(date.fromisoformat(day), time(hour), SHANGHAI).astimezone(UTC)


async def producer(
    make_client: ClientFactory,
    settings: Settings,
    day: str = TODAY,
    *,
    hers: dict[str, int],
    birthday: str | None = None,
    then: Sequence[list[str]] = (written(),),
) -> tuple[httpx.AsyncClient, FakeLLM, FakeClock]:
    """A client whose user, at 9 o'clock on `day`, has just taken `hers` turns with each
    character, and has their birthday on `birthday` (MM-DD) if any; her chat model then
    replying `then`, a letter by default."""
    clock = FakeClock(at(day))
    llm = FakeLLM(*[REPLY] * sum(hers.values()), *then)
    client = make_client(llm, clock=clock, settings=settings)
    if birthday is not None:
        month, of = birthday.split("-")
        res = await client.put(
            "/api/profile", json={"birthday": {"month": int(month), "day": int(of)}}
        )
        assert res.status_code == 200, res.text
    for character, count in hers.items():
        await turns(client, await start_conversation(client, character), count)
    with sqlite3.connect(settings.database_path) as db:  # as the store writes the time as it is
        db.execute("UPDATE messages SET created_at = ?", (clock.now.isoformat(),))
    return client, llm, clock


def first_talked(database: Path, character: str, day: str) -> None:
    """Have the producer have first talked to her on `day`, in a conversation of its own, as
    one imported has it."""
    with sqlite3.connect(database) as db:
        [user] = db.execute("SELECT id FROM users WHERE name = 'producer'").fetchone()
        db.execute(
            "INSERT INTO conversations (id, user_id, character_id, created_at, title)"
            " VALUES ('imported', ?, ?, ?, NULL)",
            (user, character, at(day).isoformat()),
        )
        db.execute(
            "INSERT INTO messages (conversation_id, role, text, ja, zh, segments, created_at)"
            " VALUES ('imported', 'user', '初次见面', NULL, NULL, NULL, ?)",
            (at(day).isoformat(),),
        )


async def written_on(client: httpx.AsyncClient) -> list[tuple[str, list[str], str]]:
    """Whose each of the user's letters is, on what, and the day, the latest first."""
    return [(each["character_id"], each["occasions"], each["day"]) for each in await letters(client)]


@pytest.mark.parametrize(
    ("mano", "kogane", "writer"),
    [
        ((2, 50), (1, 70), "kogane"),  # highest in tier
        ((1, 50), (2, 50), "kogane"),  # in the same tier, with the most turns
        ((1, 50), (1, 50), "mano"),  # then first in idol order
        ((1, 50), (2, 30), "mano"),  # not one distant
    ],
)
async def test_on_the_producers_birthday_the_one_she_is_closest_to_writes_alone(
    make_client: ClientFactory,
    settings: Settings,
    mano: tuple[int, float],
    kogane: tuple[int, float],
    writer: str,
):
    client, llm, clock = await producer(
        make_client, settings, hers={"mano": mano[0], "kogane": kogane[0]}, birthday="09-25"
    )
    keep(settings.database_path, "producer", mano[1], clock.now)
    keep(settings.database_path, "producer", kogane[1], clock.now, character="kogane")

    await backend_of(client).letters.run_due()

    assert await written_on(client) == [(writer, ["producer_birthday"], TODAY)]
    assert "今天是制作人的生日" in llm.prompts[-1][2].content


async def test_where_affinity_is_off_the_one_with_the_most_turns_writes_on_the_birthday(
    make_client: ClientFactory, settings: Settings
):
    off = replace(settings, affinity_and_gifts=False)
    client, _, clock = await producer(
        make_client, off, hers={"mano": 2, "kogane": 1}, birthday="09-25"
    )
    keep(settings.database_path, "producer", 30, clock.now)  # kept, but no matter

    await backend_of(client).letters.run_due()

    assert await written_on(client) == [("mano", ["producer_birthday"], TODAY)]


@pytest.mark.parametrize("birthday", [None, "09-26"])
async def test_without_their_birthday_today_none_writes(
    make_client: ClientFactory, settings: Settings, birthday: str | None
):
    client, _, _ = await producer(make_client, settings, hers={"mano": 1}, birthday=birthday)

    await backend_of(client).letters.run_due()

    assert await letters(client) == []


@pytest.mark.parametrize(("value", "writes"), [(65, True), (64, False)])
async def test_on_her_birthday_she_writes_if_close_or_above(
    make_client: ClientFactory, settings: Settings, value: float, writes: bool
):
    client, llm, clock = await producer(make_client, settings, "2027-04-25", hers={"mano": 1})
    keep(settings.database_path, "producer", value, clock.now)

    await backend_of(client).letters.run_due()

    assert await written_on(client) == ([("mano", ["her_birthday"], "2027-04-25")] if writes else [])
    if writes:
        assert "今天是你的生日" in llm.prompts[-1][2].content


async def test_where_affinity_is_off_there_is_no_her_birthday(
    make_client: ClientFactory, settings: Settings
):
    off = replace(settings, affinity_and_gifts=False)
    client, _, _ = await producer(make_client, off, "2027-04-25", hers={"mano": 1})

    await backend_of(client).letters.run_due()

    assert await letters(client) == []


@pytest.mark.parametrize(
    ("first", "since"),
    [
        ("2026-06-17", "满 100 天"),
        ("2025-09-25", "满一年"),
        ("2024-09-25", "满 2 年"),
        ("2026-06-16", None),  # 101 days
        ("2025-09-26", None),
    ],
)
async def test_the_day_they_first_talked_comes_round_100_days_on_and_every_year(
    make_client: ClientFactory, settings: Settings, first: str, since: str | None
):
    """Counted from an imported conversation as from any."""
    client, llm, _ = await producer(make_client, settings, hers={"mano": 1})
    first_talked(settings.database_path, "mano", first)

    await backend_of(client).letters.run_due()

    if since is None:
        assert await letters(client) == []
    else:
        assert await written_on(client) == [("mano", ["anniversary"], TODAY)]
        assert f"今天是你们认识{since}的日子" in llm.prompts[-1][2].content


async def test_she_distant_writes_on_no_day_they_first_talked(
    make_client: ClientFactory, settings: Settings
):
    client, _, clock = await producer(make_client, settings, hers={"mano": 1})
    first_talked(settings.database_path, "mano", "2025-09-25")
    keep(settings.database_path, "producer", 39, clock.now)

    await backend_of(client).letters.run_due()

    assert await letters(client) == []


async def test_february_29_falls_on_february_28_in_a_year_without_it(
    make_client: ClientFactory, settings: Settings
):
    """The producer's birthday and the day they first talked on the same day: one letter."""
    client, llm, _ = await producer(
        make_client, settings, "2027-02-28", hers={"mano": 1}, birthday="02-29"
    )
    first_talked(settings.database_path, "mano", "2024-02-29")

    await backend_of(client).letters.run_due()

    assert await written_on(client) == [
        ("mano", ["producer_birthday", "anniversary"], "2027-02-28")
    ]
    assert "认识满 3 年" in llm.prompts[-1][2].content


@pytest.mark.parametrize(
    ("contact", "days_before", "writes"),
    [("turn", 29, True), ("turn", 31, False), ("call", 29, True)],
)
async def test_only_a_producer_in_touch_within_30_days_is_written_to_on_a_day(
    make_client: ClientFactory, settings: Settings, contact: str, days_before: int,
    writes: bool,
):
    """A turn with anyone, or a call that connected."""
    client, _, clock = await producer(
        make_client, settings, hers={"mano": 1}, birthday="09-25"
    )
    database = settings.database_path
    with sqlite3.connect(database) as db:
        [conversation] = db.execute("SELECT id FROM conversations").fetchone()
    in_touch = clock.now - timedelta(days=days_before)
    last_contact(database, conversation, in_touch - timedelta(days=30 if contact == "call" else 0))
    if contact == "call":
        with sqlite3.connect(database) as db:
            db.execute(
                "INSERT INTO calls (conversation_id, connected_at, duration_s) VALUES (?, ?, 60)",
                (conversation, in_touch.isoformat()),
            )

    await backend_of(client).letters.run_due()

    assert await written_on(client) == (
        [("mano", ["producer_birthday"], TODAY)] if writes else []
    )


async def test_reaching_close_on_their_birthday_is_one_letter_on_both(
    make_client: ClientFactory, settings: Settings
):
    client, llm, _, _ = await close_with_mano(make_client, settings, written())
    await client.put("/api/profile", json={"birthday": {"month": 9, "day": 25}})

    await backend_of(client).letters.run_due()

    assert await written_on(client) == [("mano", ["close", "producer_birthday"], TODAY)]
    context = llm.prompts[-1][2].content
    assert "第一次比平时更近了一步" in context and "今天是制作人的生日" in context


async def test_the_day_is_kept_for_once_and_another_occasion_put_off_to_the_next_day(
    make_client: ClientFactory, settings: Settings
):
    client, _, clock = await producer(
        make_client, settings, "2027-04-25", hers={"mano": 1}, then=(written(), REPLY, written())
    )
    database = settings.database_path
    keep(database, "producer", 70, clock.now)
    letters_of = backend_of(client).letters
    await letters_of.run_due()
    clock.advance(hours=6)
    keep(database, "producer", 85, clock.now)
    await turns(client, await start_conversation(client), 1)  # intimate, the same day
    await letters_of.run_due()
    that_day = await written_on(client)
    clock.advance(hours=9)  # the next day in Shanghai
    await letters_of.run_due()

    assert that_day == [("mano", ["her_birthday"], "2027-04-25")]
    assert await written_on(client) == [
        ("mano", ["intimate", "close"], "2027-04-26"),
        ("mano", ["her_birthday"], "2027-04-25"),
    ]


@pytest.mark.parametrize("why", ["down", "off"])
async def test_a_day_gone_by_without_a_tick_is_not_made_up_for(
    make_client: ClientFactory, settings: Settings, github: FakeIdentityProvider, why: str
):
    """The backend down through it, or letters off."""
    on = replace(settings, admins=frozenset({ADMIN}))
    client, _, clock = await producer(make_client, on, hers={"mano": 1}, birthday="09-26")
    letters_of = backend_of(client).letters
    await letters_of.run_due()
    clock.advance(days=1)
    if why == "off":
        async with admin_beside(client, github) as admin:
            await admin.put(LETTERS, json={"enabled": False})
            await letters_of.run_due()
            clock.advance(days=1)
            await admin.put(LETTERS, json={"enabled": True})
    else:
        clock.advance(days=1)

    await letters_of.run_due()

    assert await letters(client) == []


@pytest.mark.parametrize(("days", "writes"), [(1, True), (2, False)])
async def test_one_whose_day_is_over_a_day_gone_is_passed_over(
    make_client: ClientFactory, settings: Settings, days: int, writes: bool
):
    client, _, clock, _ = await close_with_mano(make_client, settings, written())
    clock.advance(days=days)

    await backend_of(client).letters.run_due()

    assert await written_on(client) == ([("mano", ["close"], TODAY)] if writes else [])
