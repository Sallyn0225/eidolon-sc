"""The weather she knows of as she talks (GLOSSARY.md「此刻」): typing, in a call or reaching out,
Tokyo's, where she is, and, where the producer has a city in their profile and the deployer a
QWeather account, the producer's: the weather now, whether it rains or snows later in the day,
the day's highest and lowest beside yesterday's (`weather.Today`; Tokyo's from Open-Meteo, the
producer's from QWeather, `qweather`), and there the weather warnings in force. What cannot be
had in `WAIT` she is not told, nor is she told it is missing.

She may bring it up herself only if they have not been in touch for `LONG_APART` (in a call,
until it connected), or the day stands out where either of them is (`weather.Today.stands_out`),
or a warning is in force where the producer is; Tokyo's and the producer's each on its own, so
that a day that stands out on one side frees her to bring up that side's alone. Where the
producer is in Tokyo too (within `SAME_PLACE`), Tokyo's weather is told once, as both of
theirs.

Reaching out, she is always told it, and whether she may bring it up (`weather_lines`). Typing
and in a call (`HerWeather.told`), she is told a side's only as she may bring it up, and once in
a stretch of their being in touch, which begins after they have been apart for `LONG_APART` (in
a call, as it connected); again only for a warning in force there not told of yet in it. Which sides she
was told of in which stretch is kept in memory alone: after a restart she may be told one once
more. Otherwise she looks it up (GLOSSARY.md「查看」), as `looked_up` tells it."""

import asyncio
import math
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from eidolon.producer import City
from eidolon.qweather import QWeather
from eidolon.weather import NAMES, SWING, TOKYO, Spot, Today, Weathers

WAIT = 1.5
"""How long a turn waits on the weather it does not have yet, in seconds."""

LONG_APART = timedelta(hours=3)
"""How long out of touch has her free to bring up the weather."""

SAME_PLACE = 30.0
"""How near Tokyo, in kilometres, the producer's city is to be Tokyo's weather too."""

MAY_BRING_UP = (
    "天气可以当个话头：这段对话里还没聊过天气的话，可以在合适的时候自然地提一次，"
    "比如关心一句；已经聊过就不要再提。"
)
KEEP_IN_MIND = "天气只是让你心里有数：制作人问起时可以说，平时不要主动提。"
TOLD_TO_BRING_UP = "天气可以当个话头：可以在合适的时候自然地提一次，比如关心一句。"
"""Told with the weather she is told typing or in a call: that it is told her once in a
while is for the server to keep, not her."""
NOT_SEEN = "现在看不到天气。不要编造天气，可以坦率地说没看到。"
"""What she reads looking up the weather when none of it could be had."""


def may_bring_up_only(free: str, kept: str) -> str:
    """She may bring up the weather on the `free` side only, not on the `kept` one."""
    return (
        f"{free}的天气可以当个话头：这段对话里还没聊过天气的话，可以在合适的时候自然地提一次，"
        f"比如关心一句；已经聊过就不要再提。{kept}的天气只是让你心里有数，制作人问起时可以说，平时不要主动提。"
    )


TOKYO_SIDE = "东京"
THERE_SIDE = "制作人那边"
_LATER = {"rain": "今天晚些时候还会下雨", "snow": "今天晚些时候还会下雪"}


@dataclass(frozen=True)
class KnownWeather:
    """The weather she knows of: Tokyo's day (None if unknown); the producer's city (None
    without one, or without the deployer's account), and its day (None if unknown) and the
    warnings in force there; whether the producer is in Tokyo too; whether she may bring up
    Tokyo's herself, and the producer's (both of theirs in Tokyo's, in Tokyo too)."""

    tokyo: Today | None
    city: City | None
    there: Today | None
    warnings: tuple[str, ...]
    same_place: bool
    tokyo_free: bool
    there_free: bool


@dataclass(frozen=True)
class _Stretch:
    """What of the weather she was told in a conversation's stretch of their being in touch:
    as of its latest turn `touched`, whether Tokyo's, whether the producer's, and the
    warnings told with them."""

    touched: datetime
    tokyo: bool = False
    there: bool = False
    warnings: frozenset[str] = frozenset()


class HerWeather:
    """Tokyo's weather from `weathers`; the producer's city, and its weather and warnings,
    from `qweather` (None without)."""

    def __init__(self, weathers: Weathers, qweather: QWeather | None = None) -> None:
        self._weathers = weathers
        self._qweather = qweather
        self._stretches: dict[str, _Stretch] = {}

    async def told(
        self, conversation_id: str, city: City | None, now: datetime, last_apart: datetime | None
    ) -> KnownWeather:
        """What she knows of the weather at `now` typing or in a call in the conversation
        (`known`), whether she may bring up either side now as whether she is told it now:
        only if she may (`known`), and only if not told of it yet in this stretch of their
        being in touch, or, on the side the warnings are for, with a warning not told of yet
        in it. Taken as told."""
        known = await self.known(city, now, last_apart)
        self._stretches = {
            k: s for k, s in self._stretches.items() if now - s.touched < LONG_APART
        }
        stretch = self._stretches.get(conversation_id, _Stretch(now))
        # Long apart since a turn of the stretch kept: this is another (in a call, they were
        # last in touch before it connected, so its turns go on the stretch it began).
        if last_apart is not None and now - last_apart >= LONG_APART and (
            stretch.touched <= last_apart
        ):
            stretch = _Stretch(now)
        warned = bool(set(known.warnings) - stretch.warnings)
        tokyo = known.tokyo_free and (not stretch.tokyo or (known.same_place and warned))
        there = known.there_free and (not stretch.there or warned)
        warnings_told = tokyo if known.same_place else there
        self._stretches[conversation_id] = _Stretch(
            now, stretch.tokyo or tokyo, stretch.there or there,
            stretch.warnings | set(known.warnings) if warnings_told else stretch.warnings,
        )
        return replace(known, tokyo_free=tokyo, there_free=there)

    async def known(
        self, city: City | None, now: datetime, last_apart: datetime | None
    ) -> KnownWeather:
        """What she knows of the weather at `now`, the producer in `city` (None for nowhere
        set), they last in touch at `last_apart` (None if never), waiting no longer than
        `WAIT` on what is not kept."""
        if self._qweather is None or not self._qweather.on:
            city = None
        same = city is not None and _km(city.spot, TOKYO) <= SAME_PLACE
        there = city if city is not None and not same else None
        tokyo, there_day, warnings = await asyncio.gather(
            self._weathers.today(TOKYO, WAIT),
            self._qweather.today(there.spot, WAIT) if there and self._qweather else _none(),
            self._qweather.warnings(city.spot, WAIT) if city and self._qweather else _none(),
        )
        warnings = warnings or ()
        apart = last_apart is None or now - last_apart >= LONG_APART
        tokyo_free = tokyo is not None and (
            apart or tokyo.stands_out or (same and bool(warnings))
        )
        there_free = (there_day is not None or bool(warnings)) and not same and (
            apart or bool(warnings) or (there_day is not None and there_day.stands_out)
        )
        return KnownWeather(tokyo, city, there_day, warnings, same, tokyo_free, there_free)


async def _none() -> None:
    return None


def weather_lines(known: KnownWeather) -> list[str]:
    """The lines of now, reaching out, telling her where the producer is, if she knows, then
    the weather, and whether she may bring it up; nothing of the weather if she knows none."""
    whereabouts = _whereabouts(known)
    lines = _days(known, tokyo=True, there=True)
    if not lines:
        return whereabouts
    return [*whereabouts, *lines, _bring_up(known)]


def told_lines(known: KnownWeather) -> list[str]:
    """The lines of now, typing or in a call, telling her where the producer is, if she
    knows, then the weather of the sides she is told now (`HerWeather.told`), and that she
    may bring it up; nothing of the weather if she is told none."""
    lines = _days(known, tokyo=known.tokyo_free, there=known.there_free)
    return [*_whereabouts(known), *lines, *([TOLD_TO_BRING_UP] if lines else [])]


def is_told(known: KnownWeather) -> bool:
    """Whether she is told any of the weather typing or in a call (`told_lines`)."""
    return bool(_days(known, tokyo=known.tokyo_free, there=known.there_free))


def looked_up(known: KnownWeather | None) -> str:
    """What she reads looking up the weather (GLOSSARY.md「查看」): where the producer is,
    if she knows, and all she knows of the weather, but not whether she may bring it up;
    or, with none of it to be had (None for no weather at all), that she sees none."""
    lines = _days(known, tokyo=True, there=True) if known is not None else []
    if known is None or not lines:
        return NOT_SEEN
    return "\n".join([*_whereabouts(known), *lines])


def _whereabouts(known: KnownWeather) -> list[str]:
    return [city_line(known.city)] if known.city is not None else []


def _days(known: KnownWeather, *, tokyo: bool, there: bool) -> list[str]:
    """The lines of the weather on the sides asked for, as far as it is known: Tokyo's, the
    producer's, and the warnings in force there with the side they are for."""
    lines: list[str] = []
    if tokyo and known.tokyo is not None:
        where = "你和制作人都在东京一带，东京" if known.same_place else "东京（你这边）"
        lines.append(f"{where}这会儿：{_day(known.tokyo)}")
    if there and known.city is not None and known.there is not None:
        lines.append(f"制作人那边（{known.city.name}）这会儿：{_day(known.there)}")
    if known.warnings and (tokyo if known.same_place else there):
        lines.append(f"制作人那边正生效的气象预警：{'；'.join(known.warnings)}。")
    return lines


def _bring_up(known: KnownWeather) -> str:
    """Whether she may bring up the weather herself, of either side she knows of."""
    there_known = not known.same_place and (known.there is not None or bool(known.warnings))
    sides = [
        (TOKYO_SIDE, known.tokyo_free) if known.tokyo is not None else None,
        (THERE_SIDE, known.there_free) if there_known else None,
    ]
    free = [name for name, on in filter(None, sides) if on]
    kept = [name for name, on in filter(None, sides) if not on]
    if not free:
        return KEEP_IN_MIND
    if not kept:
        return MAY_BRING_UP
    return may_bring_up_only(free[0], kept[0])


def city_line(city: City) -> str:
    """The line telling her where the producer is."""
    return (
        f"制作人在{city.told}，这是制作人自己在档案里填的；记忆里如果有不一样的说法，以这里为准。"
        "被问起时可以回答，平时不要主动提起。"
    )


def _day(today: Today) -> str:
    said = f"{NAMES[today.now.kind]}，{today.now.temperature}°C；今天 {today.low}～{today.high}°C"
    if today.later is not None:
        said += f"，{_LATER[today.later]}"
    if (change := _change(today)) is not None:
        said += f"，{change}"
    return said + "。"


def _change(today: Today) -> str | None:
    """How much colder or warmer than yesterday, if by `weather.SWING` or more."""
    found = [
        (name, c) for name, c in (("最高", today.high_change), ("最低", today.low_change))
        if c is not None and abs(c) >= SWING
    ]
    if not found:
        return None
    name, c = max(found, key=lambda f: abs(f[1]))
    return f"比昨天{'冷' if c < 0 else '热'}了不少（{name}气温{'低' if c < 0 else '高'}了 {abs(c)}°C）"


def _km(a: Spot, b: Spot) -> float:
    """How far apart the two spots are, in kilometres, near enough."""
    dy = (a.latitude - b.latitude) * 111.2
    dx = (a.longitude - b.longitude) * 111.2 * math.cos(math.radians(b.latitude))
    return math.hypot(dx, dy)
