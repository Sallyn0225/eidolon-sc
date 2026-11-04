"""Each week's jobs and each producer's schedule (GLOSSARY.md「工作」「日程」「时间段」).

**Weeks.** A week begins at Monday 0:00 Beijing time (`affinity.DAY_TIMEZONE`) and is named
by that Monday's date; its jobs are published then, and cannot be read before. They are drawn
from the job list (`job_list`) as the week is first read, and kept: the same for everyone,
and as the list was then, so a change to the list changes only the weeks not drawn yet.

**Drawing.** Four weeks make a round (`ROTATION`), counted from `FIRST_WEEK`: the round's
number shuffles every idol (the characters in idol order, but the office's staff, as the
world setting tells them) into four groups, the first ones a member more where they do not
divide evenly, and each week of the round takes its group, so every idol has a week in each
round. The week's name then draws each of its idols two or three jobs (`JOBS_EACH`), no job
twice in the week, at least one of work and at most one private each, `LENGTH_IN_ALL` slots
in all; drawn again until they are, up to `DRAW_TRIES` times, and failing that it is the job
list's fault (`ScheduleError`), which a test of the repository's list rules out.

**Schedules.** A producer's week is Monday to Sunday where they are (their effective time
zone, as「此刻」has it), each day three slots, 上午 6–12, 下午 12–18, 晚上 18–24; the hours
before 6 are in none. Their week takes the jobs of the week of the same name: west of
Beijing, the next is published on their Sunday already; east of it, their Monday begins
before their week is published. A job is placed at a day of the week and the slot it starts
in, taking as many slots in a row as it is long, within the day; kept so, not as a time, so
that it stays on the same day and slot should the producer move. Each slot holds one job,
whoever's; a slot begun or past takes none (`why_not`). Placing is saving: what is saved is
neither moved nor taken back, and there is no way to. The browser keeps the drafts.

**Weeks gone.** The producer reads back their weeks before this one where they are, as many
as `PAST_AT_ONCE` at a time (`past`): only to look at, each with what they saved of it and the
jobs of it they saved, not the others; nothing is drawn or counted for it. With their week
comes the earliest they saved anything of (`ScheduleView.first_week`), as far back as there
is anything to read.

**What she knows.** She is told her jobs the producer saved of their week and the next, in
what she is told of now (`schedule_lines`), typing, in a call or reaching out alike; nothing
of last week's, nor of the others'. A job is done as its last slot ends, where the producer
is then; each done raises her affinity once (`Affinities.job_done`), as their schedule is
next read, for a turn's prompt or by them, while both affinity and schedules are on: nothing
runs to count them, and those done while either is off are counted once both are on again.

The weeks' jobs are no one's; each producer's schedule is theirs, deleted with them
(`database.USER_DATA`), not in their data package. Nothing here calls a model or leaves an
activity record.
"""

import json
import random
import sqlite3
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal, TypeVar
from zoneinfo import ZoneInfo

from eidolon.affinity import DAY_TIMEZONE, Affinities, day_of
from eidolon.characters import Character, in_idol_order
from eidolon.clock import Clock
from eidolon.data_access import Database
from eidolon.job_list import SLOTS, WORK, Category, ListedJob, Slot
from eidolon.producer import effective_timezone
from eidolon.store import read_profile
from eidolon.today import tokyo_date
from eidolon.world import World

_SCHEMA = """
-- Each week's jobs, drawn as the week was first read and kept as the job list had them then:
-- the week (its Monday's date), the order drawn, whose, which listed job, and its fields.
CREATE TABLE IF NOT EXISTS weekly_jobs (
    id TEXT PRIMARY KEY,
    week TEXT NOT NULL,
    position INTEGER NOT NULL,
    character_id TEXT NOT NULL,
    listed_id TEXT NOT NULL,
    name TEXT NOT NULL,
    note TEXT NOT NULL,
    category TEXT NOT NULL,
    length INTEGER NOT NULL,
    slots TEXT
);
CREATE INDEX IF NOT EXISTS weekly_jobs_by_week ON weekly_jobs (week, position);
-- One row per job each user saved in their schedule: the day of the week (0 for Monday) and
-- the slot (0 for the morning) it starts in, when saved, and when her affinity was raised for
-- it being done (none yet).
CREATE TABLE IF NOT EXISTS schedule_placements (
    user_id TEXT NOT NULL REFERENCES users(id),
    week TEXT NOT NULL,
    job_id TEXT NOT NULL REFERENCES weekly_jobs(id),
    day INTEGER NOT NULL,
    slot INTEGER NOT NULL,
    saved_at TEXT NOT NULL,
    counted_at TEXT,
    PRIMARY KEY (user_id, week, job_id)
);
CREATE INDEX IF NOT EXISTS schedule_placements_by_week ON schedule_placements (week);
"""

FIRST_WEEK = date(2026, 1, 5)
"""The Monday the rounds are counted from: its week is the first of a round."""

ROTATION = 4
"""How many weeks make a round, in which every idol has one."""

JOBS_EACH = (2, 3)
"""How many jobs each idol of the week may be given."""

LENGTH_IN_ALL = (24, 27)
"""How many slots a week's jobs take in all, at least and at most: more than the 21 a week
has, so that not all fit."""

DRAW_TRIES = 100
"""How many times a week is drawn before the job list is blamed."""

DAYS = 7
PAST_AT_ONCE = 6
"""How many weeks gone the producer reads back at a time: as many as the month view shows."""

SLOT_HOURS = 6
"""How long a slot is; the first begins at this hour too, the hours before in none."""

SLOT_NAMES: dict[Slot, str] = {"morning": "上午", "afternoon": "下午", "evening": "晚上"}

When = Literal["past", "now", "future"]

T = TypeVar("T")

# Why a job cannot be placed where asked: the browser's own reasons (`why_not`), then the
# server's alone.
WHOLE_DAY_FROM_MORNING = "一整天的工作只能从上午排"
NO_ROOM_THAT_DAY = "当天排不下"
PAST = "已经过了"
UNDER_WAY = "正在进行"
TAKEN = "格子里有别的工作"
NOT_PUBLISHED = "这一周的工作还没有发布"
NOT_THIS_WEEK = "这项工作不在这一周"
ALREADY_SAVED = "这项工作已经保存过了"

_WEEKDAYS = "一二三四五六日"
_DAYS_FROM_TODAY = {-2: "前天", -1: "昨天", 0: "今天", 1: "明天", 2: "后天"}

_HER_JOBS = "制作人给你排了这些工作（日程定了就不会再变；制作人在对话里说取消或改期，你还是按日程上的来）："
_UNDER_WAY = "说话可以带着这个状态（抽空回、在休息），不用每句都提，说过就不再反复说。"
_ABOUT_HER_JOBS = (
    "这些是你的制作人排的，你可以按你们的关系抱怨或期待；私人的安排也算他给你留出的时间。"
    "做完的工作你可以自己说过程和感受（顺不顺、累不累、小插曲），"
    "不要编后续的安排和结果（补拍、播出日期、因此接到的新工作、和别人的合作）。"
    "只在相关的时候提起，不在开头就说；同一项在这段对话里说过就不再主动提。别的偶像的安排你不清楚。"
)


class ScheduleError(RuntimeError):
    """The job list cannot give a week its jobs."""


class ScheduleClosed(Exception):
    """The deployment has schedules off: none can be saved."""

    def __init__(self) -> None:
        super().__init__("日程暂时没有开放")


@dataclass(frozen=True)
class Job:
    """One of a week's jobs: whose, and the listed job's fields as they were drawn."""

    id: str
    character_id: str
    name: str
    note: str
    category: Category
    length: int
    slots: tuple[Slot, ...] | None

    def shown(self) -> dict:
        return {
            "id": self.id, "character_id": self.character_id, "name": self.name,
            "note": self.note, "category": self.category, "length": self.length,
            "slots": self.slots and list(self.slots),
        }


@dataclass(frozen=True)
class Placement:
    """A job placed in a schedule: the day of the week (0 for Monday) and the slot (0 for the
    morning) it starts in."""

    job_id: str
    day: int
    slot: int

    def shown(self) -> dict:
        return {"job_id": self.job_id, "day": self.day, "slot": self.slot}


@dataclass(frozen=True)
class Week:
    """A week as the producer reads it: its jobs and what they saved of it, none before it is
    published."""

    id: date
    published_at: datetime
    jobs: list[Job]
    placements: list[Placement]
    published: bool

    def shown(self) -> dict:
        return {
            "id": self.id.isoformat(), "published": self.published,
            "published_at": self.published_at.isoformat(),
            "jobs": [j.shown() for j in self.jobs],
            "placements": [p.shown() for p in self.placements],
        }


@dataclass(frozen=True)
class ScheduleView:
    """The producer's week, and the next once published, in their time zone, and the
    earliest week they saved anything of (None if none)."""

    timezone: str
    this_week: Week
    next_week: Week | None
    first_week: date | None

    def shown(self) -> dict:
        return {
            "enabled": True,
            "timezone": self.timezone,
            "this_week": self.this_week.shown(),
            "next_week": self.next_week and self.next_week.shown(),
            "first_week": self.first_week and self.first_week.isoformat(),
        }


class TooManyWeeks(ValueError):
    """More weeks gone asked for at once than `PAST_AT_ONCE`."""

    def __init__(self) -> None:
        super().__init__(f"一次最多读 {PAST_AT_ONCE} 周")


@dataclass(frozen=True)
class HerJob:
    """A job of hers the producer saved: of which week, at which day and slot."""

    job: Job
    week: date
    day: int
    slot: int


@dataclass(frozen=True)
class HerSchedule:
    """Her jobs the producer saved of their week and the next, in order, it being `local`
    where they are, in their `this_week`."""

    local: datetime
    this_week: date
    jobs: list[HerJob]

    def time_of(self, week: date, day: int, slot: int) -> When:
        """Whether the slot of `week`'s day is past, under way or to come (`time_of`)."""
        return time_of(self.local, self.this_week, week, day, slot)

    def done(self, her: HerJob) -> bool:
        """Whether `her` job is done (`is_done`)."""
        return is_done(self.local, self.this_week, her.week, her.day, her.slot, her.job.length)

    def done_today(self) -> Job | None:
        """Her job the producer scheduled today where they are and she has done, the latest
        if more than one; None without."""
        done = [
            her for her in self.jobs
            if her.week == self.this_week and her.day == self.local.weekday() and self.done(her)
        ]
        return done[-1].job if done else None


@dataclass(frozen=True)
class DayJob:
    """One of her jobs the producer saved, as of the day in Tokyo it is done on: the job,
    when it is done (`done_at`), and the kinds of place it takes her to, as the job list has
    them now (`ListedJob.places`)."""

    job: Job
    done_at: datetime
    places: tuple[str, ...] | None


@dataclass(frozen=True)
class Saved:
    """What saving placed, and what it handed back, each with why."""

    saved: list[Placement]
    returned: list[tuple[Placement, str]]

    def shown(self) -> dict:
        return {
            "saved": [p.shown() for p in self.saved],
            "returned": [p.shown() | {"reason": why} for p, why in self.returned],
        }


def idols_of(characters: dict[str, Character], world: World | None) -> list[str]:
    """Who has jobs: the characters in idol order, but the office's staff."""
    return [
        c.id for c in in_idol_order(characters.values())
        if world is None or not world.is_staff(c.name)
    ]


def monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def week_of(now: datetime) -> date:
    """The week published last by `now`: the one Beijing is in."""
    return monday_of(day_of(now))


def published_at(week: date) -> datetime:
    """When `week`'s jobs are published: its Monday's 0:00 in Beijing, in UTC."""
    return datetime.combine(week, time(), ZoneInfo(DAY_TIMEZONE)).astimezone(UTC)


def draw_week(
    week: date, idols: Sequence[str], jobs: Sequence[ListedJob]
) -> list[tuple[str, ListedJob]]:
    """`week`'s idols, from `idols` in idol order, and the jobs from `jobs` each is given, in
    order. Raises ScheduleError if no draw gives a good week."""
    round_number, group = divmod((week - FIRST_WEEK).days // DAYS, ROTATION)
    shuffled = list(idols)
    random.Random(f"round {round_number}").shuffle(shuffled)
    size, more = divmod(len(shuffled), ROTATION)
    start = group * size + min(group, more)
    of_the_week = shuffled[start:start + size + (group < more)]
    drawing = random.Random(f"week {week.isoformat()}")
    least, most = LENGTH_IN_ALL
    for _ in range(DRAW_TRIES):
        drawn = _draw_once(drawing, of_the_week, jobs)
        if drawn is not None and least <= sum(j.length for _, j in drawn) <= most:
            return drawn
    raise ScheduleError(
        f"工作清单抽不出 {week} 这一周的工作：每位 {JOBS_EACH[0]} 到 {JOBS_EACH[1]} 项、"
        f"至少一项工作类、最多一项私人、总时长 {least} 到 {most} 段，试了 {DRAW_TRIES} 次都不行"
    )


def _draw_once(
    drawing: random.Random, idols: Sequence[str], jobs: Sequence[ListedJob]
) -> list[tuple[str, ListedJob]] | None:
    """Each of `idols` given jobs from `jobs` once, each job once, at least one of work and
    at most one private each, in any length; None if the jobs run out."""
    left = list(jobs)
    drawing.shuffle(left)
    drawn = []
    for idol in idols:
        work = next((j for j in left if j.category in WORK), None)
        if work is None:
            return None
        left.remove(work)
        given = [work]
        for _ in range(drawing.choice(JOBS_EACH) - 1):
            private = any(j.category == "private" for j in given)
            more = next((j for j in left if not (private and j.category == "private")), None)
            if more is None:
                return None
            left.remove(more)
            given.append(more)
        drawn.extend((idol, j) for j in given)
    return drawn


def time_of(local: datetime, this_week: date, week: date, day: int, slot: int) -> When:
    """Whether the slot of `week`'s day is past, under way or to come, it being `local` where
    the producer is, in their `this_week`. Before the first slot of a day, all its slots are
    to come."""
    if week != this_week:
        return "past" if week < this_week else "future"
    today = local.weekday()
    if day != today:
        return "past" if day < today else "future"
    if local.hour < SLOT_HOURS:
        return "future"
    current = local.hour // SLOT_HOURS - 1
    return "past" if slot < current else "now" if slot == current else "future"


def is_done(
    local: datetime, this_week: date, week: date, day: int, slot: int, length: int
) -> bool:
    """Whether a job `length` slots long, starting at the slot of `week`'s day, is done: its
    last slot past, it being `local` where the producer is, in their `this_week`. The one
    place a job is told done: for raising her affinity, telling her her jobs, and her coming
    to the bar after one; `done_at` tells when, the same."""
    return time_of(local, this_week, week, day, slot + length - 1) == "past"


def done_at(week: date, day: int, slot: int, length: int, timezone: str) -> datetime:
    """When a job `length` slots long, starting at the slot of `week`'s day, is done: as its
    last slot ends, where the producer is (`timezone`)."""
    start = datetime.combine(week + timedelta(days=day), time(), ZoneInfo(timezone))
    return start + timedelta(hours=SLOT_HOURS * (slot + length + 1))


def why_not(
    job: Job,
    day: int,
    slot: int,
    when_of: Callable[[int, int], When],
    taken: Callable[[int, int], bool],
) -> str | None:
    """Why `job` cannot start at the slot of the day, or None if it can, as the browser
    tells it: `when_of` a day's slot is, and whether one is `taken` by another job."""
    if slot + job.length > len(SLOTS):
        return WHOLE_DAY_FROM_MORNING if job.length == len(SLOTS) else NO_ROOM_THAT_DAY
    for s in range(slot, slot + job.length):
        match when_of(day, s):
            case "past":
                return PAST
            case "now":
                return UNDER_WAY
        if job.slots is not None and SLOTS[s] not in job.slots:
            return f"只能排在{_joined([SLOT_NAMES[n] for n in job.slots])}"
        if taken(day, s):
            return TAKEN
    return None


def schedule_lines(schedule: HerSchedule) -> list[str]:
    """What she is told of her jobs in `schedule`, in what she is told of now: that they
    stand whatever the producer says, then each but the one under way, its day as from
    today, its slots, and whether done; the one under way, if any, apart; and how to go by
    them. Nothing without any."""
    if not schedule.jobs:
        return []
    listed = [
        f"{_day_named(schedule, her.week, her.day)}{_slots_named(her.slot, her.job.length)}："
        f"{her.job.name}——{her.job.note}{'（做完了）' if schedule.done(her) else ''}"
        for her in schedule.jobs if not _under_way(schedule, her)
    ]
    return [_HER_JOBS, *listed, *under_way_lines(schedule), _ABOUT_HER_JOBS]


def under_way_lines(schedule: HerSchedule) -> list[str]:
    """What she is told of her job under way in `schedule`, if any, as `schedule_lines`
    tells it: what she is doing now, and that she may talk as one doing it."""
    current = schedule.local.hour // SLOT_HOURS - 1
    return [
        f"现在（{SLOT_NAMES[SLOTS[current]]} {SLOT_HOURS * (current + 1)}–"
        f"{SLOT_HOURS * (current + 2)} 点）你正在{her.job.name}：{her.job.note}。{_UNDER_WAY}"
        for her in schedule.jobs if _under_way(schedule, her)
    ]


def _under_way(schedule: HerSchedule, her: HerJob) -> bool:
    return any(
        schedule.time_of(her.week, her.day, s) == "now"
        for s in range(her.slot, her.slot + her.job.length)
    )


def _day_named(schedule: HerSchedule, week: date, day: int) -> str:
    """The day of `week`, as from today where the producer is if it is near: 周三（昨天）,
    下周一."""
    named = ("下周" if week > schedule.this_week else "周") + _WEEKDAYS[day]
    near = _DAYS_FROM_TODAY.get((week + timedelta(days=day) - schedule.local.date()).days)
    return f"{named}（{near}）" if near else named


def _slots_named(slot: int, length: int) -> str:
    """The slots a job takes, from `slot`: 上午, 上午到下午, 一整天."""
    if length == len(SLOTS):
        return "一整天"
    first, last = SLOT_NAMES[SLOTS[slot]], SLOT_NAMES[SLOTS[slot + length - 1]]
    return first if length == 1 else f"{first}到{last}"


def _joined(names: list[str]) -> str:
    return names[0] if len(names) == 1 else "、".join(names[:-1]) + "和" + names[-1]


class Schedules:
    """Each week's jobs and every producer's schedule, kept in the database."""

    def __init__(
        self,
        db: Database,
        clock: Clock,
        is_on: Callable[[], bool],
        idols: Sequence[str],
        job_list: Sequence[ListedJob],
        affinities: Affinities | None = None,
    ) -> None:
        """`is_on` tells whether schedules are on now (the live configuration's switch);
        weeks are drawn for `idols` from `job_list`. Jobs done raise `affinities`, if any,
        while they are on."""
        self._db = db
        self._clock = clock
        self._is_on = is_on
        self._idols = list(idols)
        self._job_list = list(job_list)
        self._places = {j.id: j.places for j in job_list}
        self._affinities = affinities
        db.prepare(_open)

    async def read(self, user_id: str, device_timezone: str | None) -> ScheduleView | None:
        """The user's week and the next once published, their jobs drawn if not yet, and
        the jobs done counted (`_counted`); None while schedules are off. Read first, and
        written only to draw a week or count a job."""
        return await self._read_first(
            lambda db, now, counting, writing:
            self._read(db, user_id, device_timezone, now, counting, writing)
        )

    async def past(
        self, user_id: str, first: date, last: date, device_timezone: str | None
    ) -> list[Week] | None:
        """The user's weeks from the one `first` is in to the one `last` is in that are
        before their week, earliest first, each with what they saved of it and only the jobs
        of it they saved; none if `last` is before `first`. None while schedules are off.
        Reads only: draws and counts none. Raises TooManyWeeks for more than
        `PAST_AT_ONCE`."""
        start, end = monday_of(first), monday_of(last)
        if (end - start).days // DAYS + 1 > PAST_AT_ONCE:
            raise TooManyWeeks()
        if not self._is_on():
            return None
        return await self._db.read(
            self._past, user_id, start, end, device_timezone, self._clock()
        )

    def _past(
        self,
        db: sqlite3.Connection,
        user_id: str,
        start: date,
        end: date,
        device_timezone: str | None,
        now: datetime,
    ) -> list[Week]:
        _, local = _local(db, user_id, device_timezone, now)
        this_week = monday_of(local.date())
        weeks = []
        week = start
        while week <= end and week < this_week:
            placements = _placements(db, user_id, week)
            placed = {p.job_id for p in placements}
            jobs = [j for j in _jobs(db, week) if j.id in placed]
            weeks.append(Week(week, published_at(week), jobs, placements, True))
            week += timedelta(days=DAYS)
        return weeks

    async def hers(
        self, user_id: str, character_id: str, device_timezone: str | None
    ) -> HerSchedule | None:
        """Her jobs the user saved of their week and the next, as she is told them, the jobs
        done counted (`_counted`); None while schedules are off. Read first, and written only
        to count a job."""
        return await self._read_first(
            lambda db, now, counting, writing:
            self._hers(db, user_id, character_id, device_timezone, now, counting, writing)
        )

    async def done_on(self, user_id: str, day: date) -> dict[str, list[DayJob]]:
        """Each character's jobs the user saved that are done on `day` in Tokyo, where they
        are as their profile has it, done already or not yet, in the order they are done;
        none while schedules are off. Reads only: counts none."""
        if not self._is_on():
            return {}
        return await self._db.read(self._done_on, user_id, day)

    def _done_on(
        self, db: sqlite3.Connection, user_id: str, day: date
    ) -> dict[str, list[DayJob]]:
        timezone = effective_timezone(read_profile(db, user_id), None)
        # Their weeks are where they are: any of these may have a job done on `day` in Tokyo.
        weeks = sorted({monday_of(day + timedelta(days=d)).isoformat() for d in (-2, -1, 0, 1)})
        rows = db.execute(
            "SELECT j.id, j.character_id, j.name, j.note, j.category, j.length, j.slots,"
            " j.listed_id, p.week, p.day, p.slot FROM schedule_placements p"
            " JOIN weekly_jobs j ON j.id = p.job_id"
            f" WHERE p.user_id = ? AND p.week IN ({', '.join('?' * len(weeks))})",
            (user_id, *weeks),
        ).fetchall()
        done: list[DayJob] = []
        for *fields, listed_id, week, weekday, slot in rows:
            job = _job(*fields)
            at = done_at(date.fromisoformat(week), weekday, slot, job.length, timezone)
            if tokyo_date(at) == day:
                done.append(DayJob(job, at, self._places.get(listed_id)))
        by_character: dict[str, list[DayJob]] = {}
        for each in sorted(done, key=lambda d: d.done_at):
            by_character.setdefault(each.job.character_id, []).append(each)
        return by_character

    async def _read_first(
        self, body: Callable[[sqlite3.Connection, datetime, bool, bool], T | None]
    ) -> T | None:
        """What `body` reads now, counting the jobs done if affinity is on: read first, and
        if it has anything to write, which it tells by None, written; None while schedules
        are off."""
        if not self._is_on():
            return None
        now, counting = self._clock(), self._counting
        found = await self._db.read(body, now, counting, False)
        if found is None:
            found = await self._db.write(body, now, counting, True)
        assert found is not None
        return found

    async def save(
        self,
        user_id: str,
        week: date,
        placements: Sequence[Placement],
        device_timezone: str | None,
    ) -> Saved:
        """Save each of `placements` in the user's `week` that can be, in order, so that
        each finds the slots taken by those saved before it; hand back the others, with why.
        In one transaction, so that two saving at once take a slot once. Raises
        ScheduleClosed while schedules are off."""
        if not self._is_on():
            raise ScheduleClosed()
        return await self._db.write(
            self._save, user_id, week, list(placements), device_timezone, self._clock()
        )

    async def scheduled_this_week(self) -> int:
        """How many users have saved any of the week Beijing is in."""
        return await self._db.read(_count_scheduled, week_of(self._clock()))

    def _read(
        self,
        db: sqlite3.Connection,
        user_id: str,
        device_timezone: str | None,
        now: datetime,
        counting: bool,
        writing: bool,
    ) -> ScheduleView | None:
        """The user's weeks at `now`, read through `db`, if `writing` drawing a published
        week's jobs and counting the jobs done if `counting`; else None if there is either to
        do."""
        timezone, local = _local(db, user_id, device_timezone, now)
        this_week = monday_of(local.date())
        if counting and not self._counted(db, user_id, local, this_week, writing):
            return None
        weeks = []
        for week in (this_week, this_week + timedelta(days=DAYS)):
            published = now >= published_at(week)
            jobs = _jobs(db, week) if published else []
            if published and not jobs:
                if not writing:
                    return None
                jobs = self._draw(db, week)
            weeks.append(Week(
                week, published_at(week), jobs,
                _placements(db, user_id, week) if published else [], published,
            ))
        this, following = weeks
        return ScheduleView(
            timezone, this, following if following.published else None,
            _first_week(db, user_id),
        )

    def _hers(
        self,
        db: sqlite3.Connection,
        user_id: str,
        character_id: str,
        device_timezone: str | None,
        now: datetime,
        counting: bool,
        writing: bool,
    ) -> HerSchedule | None:
        """Her jobs the user saved of their week and the next at `now`, read through `db`,
        counting the jobs done if `counting` and `writing`; else None if there are any to."""
        _, local = _local(db, user_id, device_timezone, now)
        this_week = monday_of(local.date())
        if counting and not self._counted(db, user_id, local, this_week, writing):
            return None
        rows = db.execute(
            "SELECT j.id, j.character_id, j.name, j.note, j.category, j.length, j.slots,"
            " p.week, p.day, p.slot FROM schedule_placements p"
            " JOIN weekly_jobs j ON j.id = p.job_id"
            " WHERE p.user_id = ? AND j.character_id = ? AND p.week IN (?, ?)"
            " ORDER BY p.week, p.day, p.slot",
            (user_id, character_id, this_week.isoformat(),
             (this_week + timedelta(days=DAYS)).isoformat()),
        ).fetchall()
        return HerSchedule(local, this_week, [
            HerJob(_job(*job), date.fromisoformat(week), day, slot)
            for *job, week, day, slot in rows
        ])

    def _counted(
        self,
        db: sqlite3.Connection,
        user_id: str,
        local: datetime,
        this_week: date,
        writing: bool,
    ) -> bool:
        """Whether every job done in the user's schedule has raised her affinity, it being
        `local` where they are, in their `this_week`, read through `db`: if `writing`, having
        it raised for each that has not, once, marked counted in the same transaction."""
        rows = db.execute(
            "SELECT p.week, p.job_id, p.day, p.slot, j.character_id, j.length"
            " FROM schedule_placements p JOIN weekly_jobs j ON j.id = p.job_id"
            " WHERE p.user_id = ? AND p.counted_at IS NULL",
            (user_id,),
        ).fetchall()
        done = [
            (week, job_id, character_id)
            for week, job_id, day, slot, character_id, length in rows
            if is_done(local, this_week, date.fromisoformat(week), day, slot, length)
        ]
        if not done:
            return True
        if not writing:
            return False
        assert self._affinities is not None
        for week, job_id, character_id in done:
            self._affinities.job_done(db, user_id, character_id)
            db.execute(
                "UPDATE schedule_placements SET counted_at = ?"
                " WHERE user_id = ? AND week = ? AND job_id = ?",
                (local.astimezone(UTC).isoformat(), user_id, week, job_id),
            )
        return True

    @property
    def _counting(self) -> bool:
        """Whether jobs done raise her affinity now: affinity is on. Told on the event loop,
        as affinity is."""
        return self._affinities is not None and self._affinities.on

    def _draw(self, db: sqlite3.Connection, week: date) -> list[Job]:
        """Draw `week`'s jobs and keep them, through `db`."""
        drawn = draw_week(week, self._idols, self._job_list)
        db.executemany(
            "INSERT INTO weekly_jobs (id, week, position, character_id, listed_id, name, note,"
            " category, length, slots) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (f"{week.isoformat()}-{j.id}", week.isoformat(), n, idol, j.id, j.name, j.note,
                 j.category, j.length, j.slots and json.dumps(j.slots))
                for n, (idol, j) in enumerate(drawn)
            ],
        )
        return _jobs(db, week)

    def _save(
        self,
        db: sqlite3.Connection,
        user_id: str,
        week: date,
        placements: list[Placement],
        device_timezone: str | None,
        now: datetime,
    ) -> Saved:
        _, local = _local(db, user_id, device_timezone, now)
        this_week = monday_of(local.date())
        published = now >= published_at(week)
        # Saved into before anyone read it, the week is drawn here.
        jobs = {j.id: j for j in (_jobs(db, week) or self._draw(db, week))} if published else {}
        placed = _placements(db, user_id, week)
        saved_ids = {p.job_id for p in placed}
        taken = {cell for p in placed for cell in _cells(p, jobs[p.job_id])}
        saved: list[Placement] = []
        returned: list[tuple[Placement, str]] = []
        for p in placements:
            job = jobs.get(p.job_id)
            if not published:
                why = NOT_PUBLISHED
            elif job is None:
                why = NOT_THIS_WEEK
            elif p.job_id in saved_ids:
                why = ALREADY_SAVED
            else:
                why = why_not(
                    job, p.day, p.slot,
                    lambda day, slot: time_of(local, this_week, week, day, slot),
                    lambda day, slot: (day, slot) in taken,
                )
            if why is not None:
                returned.append((p, why))
                continue
            assert job is not None
            db.execute(
                "INSERT INTO schedule_placements (user_id, week, job_id, day, slot, saved_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, week.isoformat(), p.job_id, p.day, p.slot, now.isoformat()),
            )
            saved.append(p)
            saved_ids.add(p.job_id)
            taken.update(_cells(p, job))
        return Saved(saved, returned)


def _local(
    db: sqlite3.Connection, user_id: str, device_timezone: str | None, now: datetime
) -> tuple[str, datetime]:
    """The user's effective time zone, read through `db`, and `now` there."""
    timezone = effective_timezone(read_profile(db, user_id), device_timezone)
    return timezone, now.astimezone(ZoneInfo(timezone))


def _cells(placement: Placement, job: Job) -> list[tuple[int, int]]:
    """The day and slot of each slot `job` takes, placed at `placement`."""
    return [(placement.day, s) for s in range(placement.slot, placement.slot + job.length)]


def _open(db: sqlite3.Connection) -> None:
    db.executescript(_SCHEMA)


def _jobs(db: sqlite3.Connection, week: date) -> list[Job]:
    """`week`'s jobs as drawn, in order; none if not drawn yet."""
    rows = db.execute(
        "SELECT id, character_id, name, note, category, length, slots FROM weekly_jobs"
        " WHERE week = ? ORDER BY position",
        (week.isoformat(),),
    ).fetchall()
    return [_job(*row) for row in rows]


def _job(
    id: str,
    character_id: str,
    name: str,
    note: str,
    category: Category,
    length: int,
    slots: str | None,
) -> Job:
    """A job as `weekly_jobs` keeps it."""
    kept = None if slots is None else tuple(json.loads(slots))
    return Job(id, character_id, name, note, category, length, kept)


def _placements(db: sqlite3.Connection, user_id: str, week: date) -> list[Placement]:
    """What the user saved of `week`, in the order of the days and slots."""
    rows: Iterable[tuple[str, int, int]] = db.execute(
        "SELECT job_id, day, slot FROM schedule_placements WHERE user_id = ? AND week = ?"
        " ORDER BY day, slot",
        (user_id, week.isoformat()),
    )
    return [Placement(*row) for row in rows]


def _first_week(db: sqlite3.Connection, user_id: str) -> date | None:
    """The earliest week the user saved anything of; None if none."""
    (first,) = db.execute(
        "SELECT MIN(week) FROM schedule_placements WHERE user_id = ?", (user_id,)
    ).fetchone()
    return first and date.fromisoformat(first)


def _count_scheduled(db: sqlite3.Connection, week: date) -> int:
    (count,) = db.execute(
        "SELECT COUNT(DISTINCT user_id) FROM schedule_placements WHERE week = ?",
        (week.isoformat(),),
    ).fetchone()
    return count
