"""The producer's weeks gone (GLOSSARY.md「日程」): read back to look at, as many as six at a
time, each week with what they saved of it and only the jobs of it they saved; the weeks
before their week where they are, nothing drawn or counted for them. With their week comes
the earliest they saved anything of, as far back as there is anything to read.

Driven through the backend's external API, the week's jobs kept beforehand in the database
(`publish`), as the week's draw would have kept them; saved as the week was under way, then
read back once the clock has moved on."""

import sqlite3
from datetime import timedelta

import httpx

from eidolon.config import Settings
from tests.conftest import ClientFactory
from tests.fakes import FakeClock, FakeLLM
from tests.test_schedule_saving import WEDNESDAY_AFTERNOON, WEEK, placed, publish, save
from tests.test_schedule_weeks import MONDAY, schedule


async def past(
    client: httpx.AsyncClient, first: str, last: str, timezone: str | None = None
) -> httpx.Response:
    return await client.get(
        "/api/schedule/weeks", params={"from": first, "to": last},
        headers={"X-Timezone": timezone} if timezone else None,
    )


def job(name: str, length: int = 1) -> dict:
    """A job as `publish` keeps it, shown."""
    return {
        "id": name, "character_id": "mano", "name": name, "note": "说明",
        "category": "practice", "length": length, "slots": None,
    }


async def test_weeks_gone_are_read_back_with_only_the_jobs_saved_of_them(
    make_client: ClientFactory, settings: Settings
):
    clock = FakeClock(WEDNESDAY_AFTERNOON)
    client = make_client(FakeLLM(), clock=clock)
    publish(settings.database_path, WEEK, ("lesson", 1, None), ("shoot", 2, None), ("trip", 3, None))
    await save(client, WEEK, placed("shoot", 4, 0), placed("lesson", 3, 2))

    clock.advance(days=14)  # Wednesday of 2026-10-05's week
    res = await past(client, "2026-09-21", "2026-10-11")

    assert res.status_code == 200, res.text
    assert res.json() == {"weeks": [
        {
            "id": WEEK, "published": True, "published_at": "2026-09-20T16:00:00+00:00",
            "jobs": [job("lesson"), job("shoot", 2)],
            "placements": [placed("lesson", 3, 2), placed("shoot", 4, 0)],
        },
        {
            "id": "2026-09-28", "published": True, "published_at": "2026-09-27T16:00:00+00:00",
            "jobs": [], "placements": [],
        },
    ]}
    with sqlite3.connect(settings.database_path) as db:
        drawn = db.execute("SELECT DISTINCT week FROM weekly_jobs").fetchall()
    assert drawn == [(WEEK,)]  # 2026-09-28's was never drawn, nor is it by reading it back


async def test_their_week_comes_with_the_earliest_they_saved_anything_of(
    make_client: ClientFactory, settings: Settings
):
    clock = FakeClock(WEDNESDAY_AFTERNOON)
    client = make_client(FakeLLM(), clock=clock)
    publish(settings.database_path, WEEK, ("lesson", 1, None))
    publish(settings.database_path, "2026-09-28", ("talk", 1, None))
    publish(settings.database_path, "2026-10-12", ("dance", 1, None))
    nothing_saved = (await schedule(client))["first_week"]

    clock.advance(days=7)
    await save(client, "2026-09-28", placed("talk", 4, 0))
    only_this_week = (await schedule(client))["first_week"]
    clock.advance(days=-7)
    await save(client, WEEK, placed("lesson", 4, 0))
    clock.advance(days=21)
    later = (await schedule(client))["first_week"]
    other = (await schedule(make_client(FakeLLM(), "other", clock=clock)))["first_week"]

    assert (nothing_saved, only_this_week, later, other) == (None, "2026-09-28", WEEK, None)


async def test_any_day_names_its_week_and_six_at_a_time_at_most(
    make_client: ClientFactory, settings: Settings
):
    clock = FakeClock(WEDNESDAY_AFTERNOON + timedelta(days=70))
    client = make_client(FakeLLM(), clock=clock)

    some_days = await past(client, "2026-09-23", "2026-09-29")
    six = await past(client, "2026-09-21", "2026-11-01")
    seven = await past(client, "2026-09-21", "2026-11-02")
    backwards = await past(client, "2026-09-28", "2026-09-21")

    assert [w["id"] for w in some_days.json()["weeks"]] == [WEEK, "2026-09-28"]
    assert len(six.json()["weeks"]) == 6
    assert (seven.status_code, seven.json()) == (400, {"detail": "一次最多读 6 周"})
    assert backwards.json() == {"weeks": []}


async def test_gone_is_where_the_producer_is(make_client: ClientFactory, settings: Settings):
    # Monday 2026-09-28, 2:00 in Beijing: Sunday 14:00 in New York, still 2026-09-21's week.
    client = make_client(FakeLLM(), clock=FakeClock(MONDAY + timedelta(days=7, hours=2)))

    in_shanghai = await past(client, WEEK, "2026-09-28")
    in_new_york = await past(client, WEEK, "2026-09-28", "America/New_York")

    assert [w["id"] for w in in_shanghai.json()["weeks"]] == [WEEK]
    assert in_new_york.json() == {"weeks": []}

