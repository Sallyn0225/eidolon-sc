"""What she knows of now (GLOSSARY.md「此刻」), each time she speaks, whatever the occasion:
typing, in a call, reaching out (GLOSSARY.md「搭话」), visiting the bar (GLOSSARY.md「光顾」),
posting a moment (GLOSSARY.md「朋友圈」).

`HerNow` gives it in two steps. The first reads: her jobs, counting those done, so that her
affinity read after it has them counted; where her cycle has her; her job done today; her
latest moments, where the occasion tells her of them; and, for a visit, her affinity too. The
second gives the lines of now for the occasion, as its table (`CARRIES`) has them, from what
the first read and what the caller read besides (the producer profile, when they were last in
touch, the affinity lines, the weather). The weather, typing, in a call or reaching out, the
caller reads on its own (`weather`), once it has the producer profile (`her_weather`). Her latest moments, as the first
read them, make a section of their own (`recent_moments.moments_section`). Where in the prompt
they go is the caller's to say (ADR-0020).

Typing and in a call, she is told of her jobs only the one under way, and of the weather only
what she may bring up, once (`HerWeather.told`); the rest she looks up (GLOSSARY.md「查看」,
ADR-0033) as the chat model calls the look-ups `look_ups` offers, `look_up` answering them
from what the turn read.

What every prompt of hers opens with (her sheet, her birthday, the world setting) is not now:
it stays the same all day, for a service to cache (`today.always_known`)."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from eidolon.affinity import Affinities, Status
from eidolon.characters import Character
from eidolon.cycles import Cycles, HerDays, always_neither, cycle_lines
from eidolon.her_weather import (
    HerWeather,
    KnownWeather,
    is_told,
    looked_up,
    told_lines,
    weather_lines,
)
from eidolon.llm import Tool
from eidolon.producer import City, ProducerProfile, Talking, now_prompt, posting_now_prompt
from eidolon.recent_moments import RecentMoment, RecentMoments
from eidolon.schedule import HerSchedule, Job, Schedules, schedule_lines, under_way_lines
from eidolon.today import today_lines
from eidolon.weather import Weather
from eidolon.world import World

Occasion = Talking | Literal["visit", "moments"]
"""Where she speaks: typing, in a call, reaching out (`apart`), visiting the bar, or posting
a moment."""

# Worded and tried against the real chat model (`.scratch/on-demand-context`, on the
# research/on-demand-context branch); rewording them needs that trial again.
LOOK_UP_WEATHER = Tool(
    name="look_up_weather",
    description="看天气：看一眼手机上的天气，返回东京（你这边）和制作人那边今天的天气。"
    "制作人问起天气、冷不冷、要不要带伞，或者话题真的需要知道今天的天气时使用；闲聊时不需要。",
    parameters={"type": "object", "properties": {}},
)
LOOK_UP_SCHEDULE = Tool(
    name="look_up_schedule",
    description="看日程：看制作人给你排的这周和下周的安排（哪天、哪个时段、做什么、做完没有）。"
    "制作人问起你的安排、忙不忙、哪天有空，或者话题真的需要知道你的安排时使用；闲聊时不需要。",
    parameters={"type": "object", "properties": {}},
)
LOOK_UP_BOTH = (
    "今天的天气和你这周、下周的日程，你要看一眼手机才知道：制作人问起或话题需要时用工具查，"
    "不要凭印象说。"
)
LOOK_UP_THE_SCHEDULE = (
    "你这周、下周的日程，你要看一眼手机才知道：制作人问起或话题需要时用工具查，不要凭印象说。"
)
LOOK_UP_THE_WEATHER = (
    "今天的天气你要看一眼手机才知道：制作人问起或话题需要时用工具查，不要凭印象说。"
)
LOOKED_UP_NOTE = (
    "（这一轮不能再调用任何工具了，请现在就回答制作人。可以像看了一眼手机那样自然地说，"
    "不要提到工具或记录。）"
)
"""Added to what she looked up, as `engine.LAST_ROUND_NOTE` is to what she recalled, just
before the round that forbids tool calls."""
NO_JOBS = "这两周没有安排。"
"""What she reads looking up her schedule with no jobs in it."""


@dataclass(frozen=True)
class Carries:
    """Which of what she knows of now an occasion tells her: the time, the producer's
    birthday and when they were last in touch (`now_prompt`); the day it is in Tokyo
    (`today_lines`); her jobs of this week and the next (`schedule_lines`); where her cycle
    has her (`cycle_lines`); how she feels toward the producer (the affinity lines); her
    latest moments (`recent_moments`), in a section of their own after the others; the
    weather, Tokyo's and the producer's, and where the producer is (`her_weather`), but
    for posting a moment, which is told Tokyo's weather its own way. Where she `looks_up`
    (GLOSSARY.md「查看」), she is told of her jobs only the one under way, of the weather
    only what she is to bring up (`HerWeather.told`), and that the rest she looks up."""

    time: bool
    today: bool
    schedule: bool
    cycle: bool
    affinity: bool
    moments: bool
    weather: bool
    looks_up: bool = False


CARRIES: dict[Occasion, Carries] = {
    "typing": Carries(
        time=True, today=True, schedule=True, cycle=True, affinity=True, moments=True,
        weather=True, looks_up=True,
    ),
    "in_call": Carries(
        time=True, today=True, schedule=True, cycle=True, affinity=True, moments=True,
        weather=True, looks_up=True,
    ),
    # Reaching out she is to find something to say: she is told all of it.
    "apart": Carries(
        time=True, today=True, schedule=True, cycle=True, affinity=True, moments=True,
        weather=True,
    ),
    # The bar's story is only ever on the night shift: no time, nor the producer's birthday;
    # her cycle does not follow her there, and her jobs only tell why she came.
    "visit": Carries(
        time=False, today=True, schedule=False, cycle=False, affinity=True, moments=False,
        weather=False,
    ),
    # Her moments go by Tokyo's day, as she lives there: the time is Tokyo's, and no jobs of
    # the week; when they were last in touch is not hers to post about. Her latest moments
    # she is told of as she posts, a few more of them (`moments.RECENT`).
    "moments": Carries(
        time=True, today=True, schedule=False, cycle=True, affinity=True, moments=False,
        weather=False,
    ),
}
"""What each occasion tells her of now. Anything more she is to know of now goes here, for
every occasion."""


@dataclass(frozen=True)
class KnownNow:
    """What the first step read of now (GLOSSARY.md「此刻」), for the user's `character`: her
    jobs of their week and the next, those done counted (None while schedules are off); where
    her cycle has her at any time (neither, whenever, while cycles are off, or on an occasion
    that does not tell her of it); her job done today, the latest if more than one (None
    without); for a visit, her affinity, read after her jobs (None otherwise, or while
    affinity is off); and her latest moments, the earliest first (none on an occasion that
    does not tell her of them, or while moments are off for the user)."""

    character: Character
    her_jobs: HerSchedule | None
    her_days: HerDays
    done_today: Job | None
    affinity: Status | None
    moments: tuple[RecentMoment, ...]


class HerNow:
    def __init__(
        self,
        characters: Mapping[str, Character],
        world: World | None = None,
        schedules: Schedules | None = None,
        cycles: Cycles | None = None,
        affinities: Affinities | None = None,
        moments: RecentMoments | None = None,
        weather: HerWeather | None = None,
    ) -> None:
        """Without `world`, she knows only the birthdays and holiday of the day; without
        `schedules`, no jobs; without `cycles`, no days of hers; without `affinities`, she
        reads no affinity for a visit; without `moments`, none of her moments; without
        `weather`, no weather, nor where the producer is."""
        self._characters = characters
        self._world = world
        self._schedules = schedules
        self._cycles = cycles
        self._affinities = affinities
        self._moments = moments
        self._weather = weather

    async def weather(
        self,
        occasion: Occasion,
        city: City | None,
        now: datetime,
        last_apart: datetime | None,
        conversation_id: str | None = None,
    ) -> KnownWeather | None:
        """The weather she knows of on `occasion` at `now` (`her_weather`), the producer in
        `city` (None for nowhere set), they last in touch at `last_apart` (in a call, before
        it connected; None if never); where she looks up, what of it she is told in the
        conversation (`HerWeather.told`). None on an occasion that does not tell her of it,
        or without the weather."""
        if not CARRIES[occasion].weather or self._weather is None:
            return None
        if CARRIES[occasion].looks_up and conversation_id is not None:
            return await self._weather.told(conversation_id, city, now, last_apart)
        return await self._weather.known(city, now, last_apart)

    def look_ups(self, known: KnownNow, occasion: Occasion) -> list[Tool]:
        """What she may look up on `occasion` (GLOSSARY.md「查看」), always in the same order:
        the weather, with the weather; her schedule, while schedules are on (`known`). None
        on an occasion she does not look up on."""
        if not CARRIES[occasion].looks_up:
            return []
        return [
            *([LOOK_UP_WEATHER] if self._weather is not None else []),
            *([LOOK_UP_SCHEDULE] if known.her_jobs is not None else []),
        ]

    def look_up(
        self, name: str, known: KnownNow, known_weather: KnownWeather | None
    ) -> str | None:
        """What she reads looking up `name`, of what the turn read: the weather she knows of
        (`her_weather.looked_up`), or her jobs of the week and the next as she was told them
        before she looked them up (`schedule_lines`). None for what she cannot look up."""
        if name == LOOK_UP_WEATHER.name and self._weather is not None:
            return looked_up(known_weather)
        if name == LOOK_UP_SCHEDULE.name and known.her_jobs is not None:
            return "\n".join(schedule_lines(known.her_jobs)) or NO_JOBS
        return None

    async def read(
        self, user_id: str, character_id: str, device_timezone: str | None, occasion: Occasion
    ) -> KnownNow:
        """The first step, for the user's character on `occasion`, their device in
        `device_timezone` (None reaching out): her jobs read, those done counted towards her
        affinity, her cycle where the occasion tells her of it, her job done today, her latest
        moments where it tells her of them, and for a visit her affinity. Whoever reads her
        affinity otherwise is to read it after this, so that it has her jobs done counted."""
        her_jobs = (
            await self._schedules.hers(user_id, character_id, device_timezone)
            if self._schedules is not None else None
        )
        her_days = (
            await self._cycles.her_days(user_id, character_id)
            if CARRIES[occasion].cycle and self._cycles is not None else always_neither
        )
        affinity = (
            await self._affinities.status(user_id, character_id)
            if occasion == "visit" and self._affinities is not None else None
        )
        moments = (
            await self._moments.hers(user_id, character_id)
            if CARRIES[occasion].moments and self._moments is not None else ()
        )
        return KnownNow(
            self._characters[character_id], her_jobs, her_days,
            her_jobs.done_today() if her_jobs is not None else None, affinity, moments,
        )

    def lines(
        self,
        known: KnownNow,
        occasion: Occasion,
        now: datetime,
        timezone: str,
        profile: ProducerProfile,
        last_contact: datetime | None,
        affinity_lines: Sequence[str],
        weather: Weather | None = None,
        replying: bool = False,
        known_weather: KnownWeather | None = None,
    ) -> list[str]:
        """The second step: the lines of now for `occasion` (`CARRIES`), at `now`, the
        producer in `timezone` with `profile`, last in touch at `last_contact` (None if never,
        or in a call), she feeling as `affinity_lines` say, posting a moment in `weather` (None
        for none known), or `replying` to the producer's comment on one; her cycle where it has
        her at `now`; typing, in a call or reaching out, `known_weather` (`weather`). Joined by
        new lines, they make one section: the time and the rest of `now_prompt`
        (`posting_now_prompt` posting a moment), the affinity lines last in it; where the
        producer is and the weather; the day in Tokyo; her jobs; her cycle; and where she
        looks up, what she is to look up, of what `look_ups` offers but the weather she is
        told."""
        carries = CARRIES[occasion]
        character = known.character
        felt = affinity_lines if carries.affinity else ()
        lines: list[str] = []
        if occasion == "moments":
            lines.append(posting_now_prompt(profile, now, timezone, felt, weather, replying))
        elif carries.time:
            assert occasion != "visit"
            lines.append(now_prompt(profile, now, timezone, occasion, felt, last_contact))
        else:
            lines += felt
        if carries.weather and known_weather is not None:
            lines += (told_lines if carries.looks_up else weather_lines)(known_weather)
        if carries.today:
            lines += today_lines(now, character, self._characters.values(), self._world)
        if carries.schedule and known.her_jobs is not None:
            lines += (under_way_lines if carries.looks_up else schedule_lines)(known.her_jobs)
        if carries.cycle:
            lines += cycle_lines(known.her_days(now, timezone))
        if carries.looks_up:
            lines += self._to_look_up(known, known_weather)
        return lines

    def _to_look_up(self, known: KnownNow, known_weather: KnownWeather | None) -> list[str]:
        """That she is to look up the weather and her schedule, of what she may look up,
        but the weather on a turn she is told it."""
        weather = self._weather is not None and not (
            known_weather is not None and is_told(known_weather)
        )
        schedule = known.her_jobs is not None
        if weather and schedule:
            return [LOOK_UP_BOTH]
        if schedule:
            return [LOOK_UP_THE_SCHEDULE]
        return [LOOK_UP_THE_WEATHER] if weather else []
