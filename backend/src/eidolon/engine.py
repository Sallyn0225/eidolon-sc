"""The conversation engine: one conversation turn in, the character's reply out.

It knows nothing about voice. Given a conversation and the user's input text it
retrieves what the turn calls for, assembles the prompt, streams the chat model's structured reply as per-segment
deltas, and records both sides of the turn once the reply is complete.

Every turn, typed or spoken, speaks the same protocol: `user` (the input as taken up),
then any `delta`s, then `done` or `error`. Among the deltas, `SegmentComplete` says
when a segment is complete; it stays on the server. Input that is blank or too long is rejected
before the model is asked; a turn that is rejected or fails part-way leaves no record,
and what went wrong stays in the server log.

The chat model is offered what she may look up (GLOSSARY.md「查看」) on every turn: the
recall-story tool when retrieval is available, and the weather and her schedule as `HerNow`
offers them (ADR-0033); but forbidden to call them in one that already recalled an episode.
Its calls are answered and the model asked again, once at most since every round costs the
model's time to first token; whatever it says along the way is part of the reply, and only
the reply is recorded. Should it write out a service's own tool-call markup instead (`MARKUP`),
the markup and all after it in the round go nowhere; a round with nothing shown before it is
asked again, once in a turn.

Every turn carries the world setting, when there is one, after the character sheet: the
office and its units, and the character's own songs and lives, each release and live
told as past or still to come by the day it is where the user is, the day the prompt about now tells.
The two open the prompt, with how she is to format her reply, as a system message of their
own, the same for every user's turns with her that day, marked for the service to cache;
who the producer is follows in another, then the conversation so far. What changes from
turn to turn (the time, her affinity, the letters she wrote the producer last, what retrieval
found) comes after the conversation, in a system message just before what the user is saying
now, and is not carried into the turns after it: so each turn's prompt opens as the one
before it did, up to the end of the conversation so far, marked for the service to cache too
(ADR-0020).

The chat model reads at least as many of the latest turns as the deployer says, but they
are cut back only every so often, so what it reads opens the same way for a while
(`chat_history`).

The user's memories that retrieval finds go into the prompt, and once a turn is
recorded memory writes down what the user revealed in it, when memory is on. Once the
conversation's third turn is recorded, the background model names the conversation
(`titles`), memory on or off; her prompt never carries the title.

A turn can be told to stop part-way (a call's user interrupting the character): the
model and any tool it is waiting on are abandoned at once, and the turn is recorded as
ever, with only the segments complete by then.

Each turn runs on the models it is given (see `OwnKeys.for_turn`): one plays the
character, the other (the background model) writes down memories and names the
conversation. When the user's own fails, the turn fails saying so. Retrieval is always the deployer's.

Where affinity is on as the turn begins (GLOSSARY.md「好感度」) and she is not in a cooldown,
the deployer's judge model judges what the user said to her before she replies: in the
same request as retrieval's judge, or, retrieval off, in one of its own while the turn gets
on with the rest. Once her reply is recorded affinity changes as it judged, and the change
is recorded with her reply; `done` tells it, and where it leaves her affinity. A turn not
recorded changes nothing; one the judge model could not judge leaves it as it is. She
replies in the tier the turn began in, knowing how what the user said made her feel, and
parting with the user if it is to begin a cooldown (GLOSSARY.md「冷却」); in one, she has no
turns (`Admissions`). What it judged of a turn recorded, and whether the turn began a
cooldown, the turn's activity record keeps (`TurnJudged`). In a call she parts by hanging
up, after that turn, after the user has been out of line once too often in the call, or
after the call's latest turns have taken too much off her affinity (`affinity.ends`),
warning the user first halfway there (`affinity.warns`): the turn is told it is in a call,
how often so far and how much each turn so far took, and once recorded tells the call what
came of it (`CallTurnRecorded`). Outside calls she parts the same way after the same turns,
counted over the conversation's latest typed turns, warning the user first that she will not
want to talk, and ends the conversation (GLOSSARY.md「已结束的对话」): each typed turn is
recorded with what it came to (`Typed`), the latest read back as the next begins; the one
she ends it after is recorded with her ending it, which `done` tells, and why, which the
activity record keeps, and those `on_ended` has are told then, for her to hang up a call in
it. A turn in a conversation she has ended is rejected, as is one that finds it ended,
elsewhere, as it is recorded.

In a turn that could have a photo (`photos`), typed or in a call, the judge model is asked whether the
user asks her for one, along with whatever else it is asked, or apart where it is asked
nothing else; failing, the turn has none. Asked, she is told so in the system message that
changes from turn to turn, and may write a photo tag at the front of her reply: unless her
affinity is in its coldest tier, the photo begins the moment it closes, and `photo` tells
the browser its id before her first words; any other turn's tag is dropped. The user's
photos this hour used up, she is told she cannot send one now, and `photos-used-up` tells
the browser when the user may ask again, just before `done`. Her reply is recorded with the
photo, being generated; a reply not recorded drops it. From then on her prompt carries the
tag before her reply, as she wrote it, so she knows what she sent; that of a photo not sent
after all marked failed, and she is told what that means (`photos.NOT_RECEIVED`).
Retrieval, memory and the judge model never read it. How the photo comes out is not the
turn's to wait for: `photo_came_out` tells, once it has. In a turn that could have no photo,
she is told in that system message that she cannot send photos (`photos.CANNOT_SEND`), the
judge model not asked.

She learns of the conversation's events (GLOSSARY.md「对话事件」) from a line of narration
before the user's words that came next, or before what the user is saying now; it leaves
her prompt with those words. Until she has replied or reached out after a gift, she is also
told to respond to it, once, however many came. Retrieval, memory and the judge model never
read the events.

She can also say something first, the user not talking to her (`reach_out`, GLOSSARY.md
「搭话」): not a turn (ADR-0026), but asked for as one is, on whichever model it is given, her
prompt laid out the same. From then on her prompt tells of it as of an event, by the time it
was where the producer is, followed by her words as her replies are written: so it goes with
the turn after it, and the roles keep the order every protocol takes. Retrieval, memory and
the judge model read those the user answers, after the last turn, as her latest words.
"""

import asyncio
import logging
import sqlite3
from copy import deepcopy
from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable, Mapping, Sequence
from contextlib import nullcontext
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Literal, ParamSpec, TypeVar

from eidolon.affinity import (
    FED_UP_TURNS,
    Affinities,
    Days,
    EndsFor,
    Judged,
    Parting,
    Status,
    affinity_prompt,
    ends,
    hurt,
    tier_prompt,
    warns,
)
from eidolon.affinity_judge import AffinityJudge
from eidolon.characters import Character
from eidolon.clock import Clock
from eidolon.config import FishAudioModel, ImageSettings
from eidolon.cycles import HerDays
from eidolon.data_access import Database
from eidolon.gift_catalog import Gift
from eidolon.happenings import Happenings, Open, Rewarded
from eidolon.her_cycle import HerDay, Period, Premenstrual
from eidolon.her_now import (
    LOOK_UP_SCHEDULE,
    LOOK_UP_WEATHER,
    LOOKED_UP_NOTE,
    HerNow,
    KnownNow,
    Occasion,
)
from eidolon.her_weather import KnownWeather
from eidolon.judge import JudgeError
from eidolon.letter_prompt import Earlier, letters_section, read_earlier
from eidolon.llm import ChatLLM, ChatMessage, Reasoning, Tool, ToolCall, TurnLLMs
from eidolon.memory import Memories, last_turn_query
from eidolon.own_keys import OwnKeyFailed
from eidolon.photos import CANNOT_SEND, NOT_RECEIVED, Eligibility, Photos, photo_turn
from eidolon.producer import ProducerProfile, effective_timezone, local_date, producer_prompt
from eidolon.recent_moments import moments_section
from eidolon.reply_format import (
    format_instructions,
    PhotoTagged,
    ReplyParser,
    Segment,
    SegmentComplete,
    SegmentDelta,
    SpeechDelta,
    format_reply,
)
from eidolon.retrieval import RECALL_STORY_TOOL, Retrieval, Retrieved
from eidolon.store import (
    Conversation,
    ConversationEnded,
    ConversationEvent,
    Message,
    NewPhoto,
    Photo,
    ReachOut,
    Recorded,
    Store,
    Typed,
    add_turn,
    add_unwell,
    read_ended,
    read_last_contact,
    read_profile,
    read_record,
    timestamp,
    told_her,
)
from eidolon.titles import Titles
from eidolon.today import always_known
from eidolon.world import World

MAX_INPUT_LENGTH = 2000
"""The longest thing a user can say in one turn, typed or spoken, in characters; longer
input is rejected, not cut short."""
MAX_TOOL_ROUNDS = 1
"""How many rounds of tool calls the chat model gets in one turn; after that it has to answer."""
LAST_ROUND_NOTE = (
    "（这一轮不能再调用任何工具了，请现在就回答制作人。上面想起来的内容如果答不上他的问题，"
    "就像一时记不清那样自然地说，不要提到查找、工具、记录或剧情库。）"
)
"""Added to each tool result the model reads just before the round that forbids tool calls.
Without it the model, still wanting to look something up, writes out its own tool-call
markup as the reply. Worded and verified against the real chat model; rewording it needs
that verification again."""


@dataclass(frozen=True)
class UserSaid:
    """What the user said, as the turn takes it up; every turn opens with it."""

    text: str
    type: Literal["user"] = field(default="user", init=False)


@dataclass(frozen=True)
class PhotoPending:
    """She is sending a photo with her reply, being generated (GLOSSARY.md「照片」): its id,
    to wait on. Comes before her first words."""

    id: str
    status: Literal["pending"] = field(default="pending", init=False)
    type: Literal["photo"] = field(default="photo", init=False)


Look = Literal["weather", "schedule", "story"]
"""What she looks up (GLOSSARY.md「查看」): the weather, her schedule, or the story, recalled."""
LOOKS: dict[str, Look] = {
    LOOK_UP_WEATHER.name: "weather", LOOK_UP_SCHEDULE.name: "schedule",
    RECALL_STORY_TOOL.name: "story",
}
"""What she looks up by each tool she may call."""


@dataclass(frozen=True)
class LookingUp:
    """She is looking up `what` (GLOSSARY.md「查看」), each once, in the order called: as the
    chat model's calls are answered, or as retrieval recalls the story for her before she
    speaks. Comes between `delta`s, or before the first; it is not recorded."""

    what: tuple[Look, ...]
    type: Literal["looking-up"] = field(default="looking-up", init=False)


@dataclass(frozen=True)
class PhotosUsedUp:
    """The user asked for a photo with their photos this hour used up: they may ask again
    at `retry_at` (ISO). Comes just before `done`."""

    retry_at: str
    type: Literal["photos-used-up"] = field(default="photos-used-up", init=False)


@dataclass(frozen=True)
class TurnDone:
    """The recorded reply, with how the turn changed her affinity if it did; her affinity
    after it (`Status.shown`), None where affinity is off; her ending the conversation
    after it (`ConversationEvent.shown`), None if she did not; what the turn was rewarded
    with (`Happenings.turn_recorded`), None if nothing; and her being unwell, recorded
    before it (`ConversationEvent.shown`), None if it was not. The turn succeeded."""

    message: Message
    affinity: dict[str, str | None] | None = None
    ended: dict | None = None
    rewarded: Rewarded | None = None
    unwell: dict | None = None
    type: Literal["done"] = field(default="done", init=False)



@dataclass(frozen=True)
class InCall:
    """The turn is taken in a call, in which the user has been out of line (GLOSSARY.md
    「不该说的话」) `out_of_line` times so far, in turns recorded, which took `hurts` each off
    her affinity (`affinity.hurt`), the latest last."""

    out_of_line: int = 0
    hurts: tuple[float, ...] = ()
    connected_at: datetime | None = None
    """When the call connected, as the clock told: they were last in touch before it."""


@dataclass(frozen=True)
class CallTurnRecorded:
    """What a turn of a call, now recorded, comes to for the call: whether the user was out
    of line in it, and whether she hangs up after it and why; if for a cooldown, when it
    ends (None should the cooldown not have begun after all, another turn recorded
    meanwhile); how much it hurt her (`affinity.hurt`). Comes just before
    `done`, in calls only; it stays on the server."""

    out_of_line: bool = False
    hangs_up: EndsFor | None = None
    cooldown_until: datetime | None = None
    hurt: float = 0.0
    type: Literal["call-turn-recorded"] = field(default="call-turn-recorded", init=False)


@dataclass(frozen=True)
class TurnJudged:
    """What the judge model made of a turn now recorded (GLOSSARY.md「好感度」), whether the
    turn began a cooldown, and why she ended the conversation after it, if she did, for its
    activity record. Comes just before `done`, in turns judged only; it stays on the server."""

    judged: Judged
    cooled: bool
    ended: EndsFor | None = None
    type: Literal["turn-judged"] = field(default="turn-judged", init=False)


@dataclass(frozen=True)
class TurnFailed:
    """Why the turn failed, for the user to read; it left no record."""

    message: str
    type: Literal["error"] = field(default="error", init=False)


@dataclass(frozen=True)
class TurnRejected:
    """Why the turn was rejected for its input, for the user to read; it left no record.
    The browser is told it as it is told a failure."""

    message: str
    type: Literal["error"] = field(default="error", init=False)


TurnEvent = (
    UserSaid
    | PhotoPending
    | LookingUp
    | SegmentDelta
    | SpeechDelta
    | SegmentComplete
    | CallTurnRecorded
    | TurnJudged
    | PhotosUsedUp
    | TurnDone
    | TurnFailed
    | TurnRejected
)
"""A turn's events: `user`, then `photo` if she sends one, any `delta`s, `looking-up`
among them as she looks something up, then `photos-used-up` if the user's photos are, and
`done`, or `error`. `shown(event)` is the
event as it goes out to the browser, except `SpeechDelta`, `SegmentComplete`,
`CallTurnRecorded` and `TurnJudged`, which do not."""


def shown(event: TurnEvent) -> dict:
    """The event as it goes out to the browser: `done`'s reply as `Message.shown` has it,
    and what the turn was rewarded with as `Rewarded.shown` has it."""
    if isinstance(event, TurnDone):
        return asdict(event) | {
            "message": event.message.shown(),
            "rewarded": event.rewarded and event.rewarded.shown(),
        }
    return asdict(event)

FAILED = "角色暂时无法回复，请稍后再试。"
"""What the user reads when a turn fails; the details stay in the server log."""
TOO_LONG = f"这句话太长了，最多 {MAX_INPUT_LENGTH} 字。"
"""What the user reads when a turn is rejected for input over `MAX_INPUT_LENGTH`."""
BLANK = "没有收到要说的话。"
"""What the user reads when a turn is rejected for blank input."""
ENDED = "她已经结束了对话"
"""What the user reads when a turn is rejected for the conversation she has ended."""

log = logging.getLogger(__name__)

class EmptyReply(RuntimeError):
    pass


MARKUP = ("<｜", "</｜")
"""How a service's own tool-call markup opens (DeepSeek's `<｜｜DSML｜｜invoke …>`,
`<｜tool▁calls▁begin｜>`), should the chat model write it out as text instead of calling: never
in her words, nor shown, nor voiced."""


class _Markup:
    """What a round's text may go on to the reply, as it streams: all before any `MARKUP`
    (`found` once it is), held back while what it ends with could be the start of one."""

    def __init__(self) -> None:
        self._held = ""
        self.found = False

    def feed(self, chunk: str) -> str:
        text = self._held + chunk
        at = [i for m in MARKUP if (i := text.find(m)) >= 0]
        if at:
            self.found, self._held = True, ""
            return text[: min(at)]
        keep = max(
            (n for m in MARKUP for n in range(1, len(m)) if text.endswith(m[:n])), default=0
        )
        self._held = text[len(text) - keep:]
        return text[: len(text) - keep]

    def finish(self) -> str:
        """What was held back, at the end of a round with none."""
        held, self._held = self._held, ""
        return held


class _Stopped(Exception):
    """The turn was told to stop."""


P = ParamSpec("P")
T = TypeVar("T")


async def _unless_stopped(
    stop: asyncio.Event | None, work: Callable[P, Awaitable[T]], *args: P.args, **kwargs: P.kwargs
) -> T:
    """What `work` comes to, unless `stop` is set first: then it is abandoned and this
    raises _Stopped."""
    if stop is None:
        return await work(*args, **kwargs)
    if stop.is_set():
        raise _Stopped
    working = asyncio.ensure_future(work(*args, **kwargs))
    stopped = asyncio.ensure_future(stop.wait())
    try:
        await asyncio.wait({working, stopped}, return_when=asyncio.FIRST_COMPLETED)
    finally:
        stopped.cancel()
        if not working.done():
            working.cancel()
            await asyncio.wait({working})
    if working.cancelled():
        raise _Stopped
    return working.result()


def _days(her_day: HerDay) -> Days | None:
    """Which of her days `her_day` has her in, that turns go by their numbers; None for
    neither."""
    if isinstance(her_day, Period):
        return "period"
    if isinstance(her_day, Premenstrual):
        return "premenstrual"
    return None


async def _judged(
    judge: AffinityJudge,
    character: Character,
    history: list[Message],
    text: str,
    affinity: bool,
    photo: bool,
    days: Days | None,
) -> tuple[Judged | None, bool]:
    """Asked about `affinity`, what saying `text` does to her affinity (None if not, or if it
    cannot be told), in her `days` if she is in them; asked about `photo`, whether it asks her
    for one (no if not, or if it cannot be told)."""
    try:
        return await judge.judge(character, history, text, affinity, photo, days)
    except JudgeError:
        log.warning("judging apart failed; affinity stays as it is, and no photo", exc_info=True)
        return None, False


@dataclass(frozen=True)
class _BeforeAsking:
    """What a turn, or her reaching out, reads from the database before she is asked:
    whether she has ended the conversation, her character, the conversation's record, when
    the user and she were last in touch (None in a call, where she knows they are talking),
    her affinity as it begins, what it may send for a photo (None for a reach-out), and the
    producer profile; and when they were last in touch apart, as the weather has it
    (`her_weather`): in a call, before it connected (None if never); and the letters she
    wrote the user last, the earliest first (`letter_prompt.read_earlier`)."""

    ended: bool
    character: Character
    record: list[Recorded]
    last_contact: datetime | None
    affinity: Status | None
    eligibility: Eligibility | None
    profile: ProducerProfile
    last_apart: datetime | None = None
    letters: Sequence[Earlier] = ()


@dataclass
class _Photo:
    """The photo a turn sends, on the user's `own` image generation if the turn brings it:
    once it begins one, its id and the tag she wrote for it, and whether her reply has been
    handed in to be recorded with it: from then on, recording it tells the photos what
    became of it (`ConversationEngine._keep`)."""

    own: ImageSettings | None = None
    id: str | None = None
    tag: str = ""
    handed_in: bool = False


def latest_turns(messages: list[Message], turns: int | None) -> list[Message]:
    """The messages from the `turns`th last user message on (from the first if None), so
    what the chat model reads always opens with the user."""
    starts = [i for i, m in enumerate(messages) if m.role == "user"]
    kept = starts if turns is None else starts[-turns:]
    return messages[kept[0]:] if kept else []


def chat_history(messages: list[Message], turns: int | None) -> list[Message]:
    """The latest turns of `messages` the chat model reads: at least `turns` (all if None),
    cut back to that many each time they reach half as many again, rather than one at a
    time, so what it reads opens the same way from turn to turn in between."""
    total = sum(m.role == "user" for m in messages)
    if turns is None or total <= turns:
        return latest_turns(messages, None)
    step = max(1, turns // 2)
    return latest_turns(messages, total - step * ((total - turns) // step))


RESPOND_TO_GIFTS = (
    "（先回应制作人说的话，再在合适的时候用你自己的方式回应收到的礼物，一次就够。）"
)
"""Told her after the gifts she has not replied since, once however many there are."""

WARMED = "这几天你不太舒服，收到暖的东西，你心里很暖。"
"""Told her of a warm gift given in her period or the days before it (GLOSSARY.md「周期」)."""


def _narration(
    event: ConversationEvent, gift_catalog: Mapping[str, Gift], her_days: HerDays,
    timezone: str,
) -> str:
    """What she is told of `event`, as it was: of a warm gift, whether `her_days` had her in
    her days as it was given, the producer in `timezone`, as that is kept nowhere."""
    if event.kind == "hung_up":
        return "（你挂断了制作人的电话。）"
    if event.kind == "ended":  # only read by a turn it will reject
        return "（你结束了和制作人的对话。）"
    assert event.gift_id is not None
    gift = gift_catalog[event.gift_id]
    liked = "这是你喜欢的东西。" if event.liked else ""
    given_at = datetime.fromisoformat(event.created_at)
    warmed = WARMED if gift.warm and her_days(given_at, timezone) is not None else ""
    return f"（制作人送给你一份{gift.name}。{liked}{warmed}）"


def _reached_out(reach_out: ReachOut, timezone: str) -> str:
    """What she is told of her `reach_out`, the producer in `timezone`: when, then her words
    as her replies are written in her prompt."""
    at = datetime.fromisoformat(reach_out.created_at).astimezone(ZoneInfo(timezone))
    said = format_reply(reach_out.segments)
    return f"（{at.month}月{at.day}日 {at:%H:%M}，你先给制作人发了：）{said}"


def _narration_line(
    entry: ConversationEvent | ReachOut, gift_catalog: Mapping[str, Gift], her_days: HerDays,
    timezone: str,
) -> str:
    """The line of narration telling her of `entry`, the producer in `timezone`, `her_days`
    telling where she was."""
    if isinstance(entry, ReachOut):
        return f"{_reached_out(entry, timezone)}\n"
    return f"{_narration(entry, gift_catalog, her_days, timezone)}\n"


def narrations(
    record: Sequence[Recorded], gift_catalog: Mapping[str, Gift], timezone: str,
    her_days: HerDays,
) -> dict[int | None, str]:
    """The narration of the events and reach-outs in `record`, by the id of the user message
    each comes before, None for those after them all: one line for each she is told of
    (`told_her`), then, if she has neither replied nor reached out since a
    gift, `RESPOND_TO_GIFTS`. The producer is in `timezone`; `her_days` tells where she was
    as each gift was given."""
    lines: list[str] = []
    told: dict[int | None, str] = {}
    unanswered = False
    for entry in record:
        if not told_her(entry):
            continue
        if not isinstance(entry, Message):
            lines.append(_narration_line(entry, gift_catalog, her_days, timezone))
            if isinstance(entry, ReachOut):
                unanswered = False  # reaching out, she has responded to the gifts before
            else:
                unanswered = unanswered or entry.kind == "gift"
        elif entry.role == "character":
            unanswered = False
        elif lines:
            told[entry.id], lines = "".join(lines), []
    if unanswered:
        lines.append(f"{RESPOND_TO_GIFTS}\n")
    if lines:
        told[None] = "".join(lines)
    return told


_REACH_OUT_RULES = """# 先开口
制作人这会儿没在和你说话，你想先给他发几句。
- 由头你自己挑：先接着你们最近聊过的事，或者他最近的近况；其次是你这周的工作（如果有）；{moments}再其次才是现在的时间、他的生日。
- 别人的生日、节假日、往年今天的演出不拿来当由头；组合伙伴的生日可以顺口提一句。
- 不要只发一句空的问候，比如「早安」「在吗」「想你了」，要有具体想说的事。
- 写一到两段。
- 别和你前几次先开口时用一样的开头、一样的由头。
- 说到你自己那边：日程里有的就说日程里的；没有的话只说练习、拍摄、事务所的工作这类平常的事，或者世界设定里快到的 live 和新歌，已经过去的只当回忆说，先对照现在的年份；不要编具体的剧情，也不要说别的偶像做了什么。
- 不发照片，也不说要给他发照片、要给他打电话。
- 让他好接话，但不必用问句结尾。"""

REACH_OUT_RULES = _REACH_OUT_RULES.format(moments="")
"""How she is to reach out (GLOSSARY.md「搭话」), told her last in what changes from turn to turn,
where what retrieval finds would be."""

REACH_OUT_RULES_WITH_MOMENTS = _REACH_OUT_RULES.format(
    moments="然后是你最近发的朋友圈（比如问他看到没有）；"
)
"""How she is to reach out with her latest moments to tell (`recent_moments`), as she may
reach out about them too."""

WANTS_TO_REACH_OUT = "（制作人这会儿没在和你说话。你想先给他发几句。）"
"""Where the user's words would be as she reaches out, after the events since the last turn:
so every protocol takes the prompt, ending with the user, as narration does."""


def _moments_told(
    known: KnownNow, now: datetime, timezone: str, affinity: Status | None
) -> list[str]:
    """The section telling her of her latest moments `known` (`recent_moments`), if any, at
    `now`, the producer in `timezone`, she as `affinity` has her."""
    section = moments_section(known.moments, now, timezone, affinity and affinity.tier)
    return [section] if section else []


def _letters_told(letters: Sequence[Earlier]) -> list[str]:
    """The section telling her of the letters she wrote the producer (`letters_section`), if
    any."""
    section = letters_section(letters)
    return [section] if section else []


def _since_last_turn(
    record: Sequence[Recorded], gift_catalog: Mapping[str, Gift], timezone: str,
    her_days: HerDays,
) -> str:
    """The narration of the events and reach-outs after the last turn, one line for each she
    is told of, the producer in `timezone`, `her_days` telling where she was."""
    lines: list[str] = []
    for entry in record:
        if isinstance(entry, Message):
            lines = []
        elif told_her(entry):
            lines.append(_narration_line(entry, gift_catalog, her_days, timezone))
    return "".join(lines)


def _answering(record: Sequence[Recorded]) -> list[Message]:
    """Her reach-outs after the last turn, which the user now answers, as those reading only
    the messages read them: as her replies, the latest last."""
    said: list[Message] = []
    for entry in record:
        if isinstance(entry, Message):
            said = []
        elif isinstance(entry, ReachOut):
            said.append(entry.as_reply())
    return said


class ConversationEngine:
    def __init__(
        self,
        db: Database,
        store: Store,
        characters: dict[str, Character],
        gift_catalog: Mapping[str, Gift],
        memory: Memories,
        titles: Titles,
        clock: Clock,
        her_now: HerNow,
        retrieval: Retrieval | None = None,
        history_turns: Callable[[], int | None] = lambda: None,
        world: World | None = None,
        affinities: Affinities | None = None,
        affinity_judge: AffinityJudge | None = None,
        photos: Photos | None = None,
        happenings: Happenings | None = None,
    ) -> None:
        """Without `retrieval`, turns carry no story or character facts and find no
        memories. Each turn reads only the conversation's latest turns, as many as
        `history_turns` says as it begins, or all of them if None; the chat model reads
        at least as many (`chat_history`). Without `world`, turns
        carry no world setting. Without `affinities`, turns change no affinity; with them,
        retrieval's judge judges what turns do to it, or without retrieval
        `affinity_judge`, which judges whether turns ask for a photo too. Without `photos`,
        or without the judge model, no turn has a photo. Each turn recorded is told to
        `happenings`, if any. What she knows of now, in turns and reaching out alike,
        `her_now` gives; where her cycle has her it reads too, for what she is judged by
        and told of gifts."""
        self._db = db
        self._store = store
        self._characters = characters
        self._gift_catalog = gift_catalog
        self._clock = clock
        self._retrieval = retrieval
        self._memory = memory
        self._titles = titles
        self._history_turns = history_turns
        self._world = world
        self._affinities = affinities
        self._affinity_judge = affinity_judge
        self._photos = photos
        self._happenings = happenings
        self._her_now = her_now
        self._ended_listeners: list[Callable[[str, EndsFor], None]] = []
        self._cooled_listeners: list[Callable[[str, str, datetime], None]] = []

    def on_ended(self, listener: Callable[[str, EndsFor], None]) -> None:
        """Have `listener` told the conversation's id, and why, as she ends one, once it is
        recorded."""
        self._ended_listeners.append(listener)

    def on_cooled(self, listener: Callable[[str, str, datetime], None]) -> None:
        """Have `listener` told the user, the character and when it ends as a turn begins a
        cooldown, once it is recorded, in the task that took the turn."""
        self._cooled_listeners.append(listener)

    async def turn(
        self,
        conversation: Conversation,
        text: str,
        llms: TurnLLMs,
        device_timezone: str | None = None,
        stop: asyncio.Event | None = None,
        in_call: InCall | None = None,
        voiced_by: FishAudioModel | None = None,
        own_image: ImageSettings | None = None,
    ) -> AsyncGenerator[TurnEvent, None]:
        """Take one turn on `llms`, `in_call` if it is taken in one, its reply voiced with
        `voiced_by` (for a text turn's, the model it would be read aloud with, GLOSSARY.md
        「朗读」; None if none), which has her write delivery cues as it reads them, her photo
        on the user's `own_image` generation if it brings it. `device_timezone` is the time
        zone the user's device reports, used unless the producer profile sets one. Once
        `stop` is set, the turn goes no further and is recorded with the segments complete by
        then."""
        text = text.strip()
        yield UserSaid(text)
        if not text or len(text) > MAX_INPUT_LENGTH:
            yield TurnRejected(TOO_LONG if text else BLANK)
            return
        photo = _Photo(own_image)
        # A text turn is under way, so that she does not reach out meanwhile; a call is, as
        # long as it lasts.
        taking = self._store.taking_turn(conversation.id) if in_call is None else nullcontext()
        try:
            with taking:
                async for event in self._reply(
                    conversation, text, llms, device_timezone, stop, in_call, voiced_by, photo
                ):
                    yield event
        except OwnKeyFailed as e:  # theirs to fix, so they are told what went wrong
            log.warning("turn failed on the user's own key in conversation %s: %s",
                        conversation.id, e.service)
            yield TurnFailed(e.message)
        except Exception:  # the turn has started; report instead of dropping it
            log.exception("turn failed in conversation %s", conversation.id)
            yield TurnFailed(FAILED)
        finally:
            if photo.id is not None and not photo.handed_in and self._photos is not None:
                self._photos.dropped(photo.id)

    async def _reply(
        self,
        conversation: Conversation,
        text: str,
        llms: TurnLLMs,
        device_timezone: str | None,
        stop: asyncio.Event | None,
        in_call: InCall | None,
        voiced_by: FishAudioModel | None,
        photo: _Photo,
    ) -> AsyncIterator[TurnEvent]:
        # The database is read and written on threads all through the turn: waiting on it
        # on the event loop would keep everyone's calls on it from going on meanwhile.
        occasion: Occasion = "typing" if in_call is None else "in_call"
        # Before her affinity is read, so that it is read with her jobs done counted.
        known = await self._her_now.read(
            conversation.user_id, conversation.character_id, device_timezone, occasion
        )
        read = await self._db.read(
            self._before_turn, conversation, in_call, photo.own, self._affinity_on
        )
        if read.ended:
            yield TurnRejected(ENDED)
            return
        character, record, last_contact, affinity, eligibility, profile = (
            read.character, read.record, read.last_contact, read.affinity, read.eligibility,
            read.profile,
        )
        # Fetched as she is retrieved for, and waited on only then.
        weather = asyncio.ensure_future(self._her_now.weather(
            occasion, profile.city, self._clock(), read.last_apart, conversation.id
        ))
        # Said after reading the record, so an event this turn's prompt does not tell of
        # comes before the turn, and is told of with its words from the next turn on.
        said_at = timestamp()
        messages = [entry for entry in record if isinstance(entry, Message)]
        turns = self._history_turns()
        # What all but the chat model read: her reach-outs the user answers her latest words.
        history = [*latest_turns(messages, turns), *_answering(record)]
        timezone = effective_timezone(profile, device_timezone)
        # Before she is judged, as where she is has her judged by these days' numbers; the
        # same for her being unwell. What she is told of now has her where she is as the
        # prompt is laid out, a day off only should midnight fall in between.
        her_days = known.her_days
        her_day = her_days(self._clock(), timezone)
        days = _days(her_day)
        judging = affinity is not None and not affinity.cooling
        asking_photo = eligibility is not None
        judged_apart = None
        if (judging or asking_photo) and self._retrieval is None and self._affinity_judge:
            judged_apart = asyncio.ensure_future(_judged(
                self._affinity_judge, character, history, text, judging, asking_photo, days
            ))
        try:
            memory = await self._memory.begin(
                conversation, timezone, llms.background, llms.hold_background
            )
            retrieved = Retrieved(None)
            if self._retrieval:
                recalling = asyncio.Event()
                retrieving = asyncio.ensure_future(self._retrieval.retrieve(
                    character, history, text, memory, judging, asking_photo, days,
                    recalling.set,
                ))
                try:
                    told = asyncio.ensure_future(recalling.wait())
                    await asyncio.wait({retrieving, told}, return_when=asyncio.FIRST_COMPLETED)
                    told.cancel()
                    if recalling.is_set():
                        yield LookingUp(("story",))
                    retrieved = await retrieving
                finally:
                    retrieving.cancel()
            judged, asked_photo = (
                await judged_apart if judged_apart is not None
                else (retrieved.judged, retrieved.photo)
            )
            known_weather = await weather
        finally:
            if judged_apart is not None and not judged_apart.done():
                judged_apart.cancel()
            if not weather.done():
                weather.cancel()
        now = self._clock()
        cools = await self._cools(conversation, judged)
        if in_call is not None:
            out_of_line_before, hurt_before = in_call.out_of_line, in_call.hurts
        else:
            # As many as are weighed, so that whether she warns is told against the latest
            # before this one; out of line is counted in the latest with this one among them.
            earlier = await self._store.typed_turns(conversation.id, FED_UP_TURNS)
            out_of_line_before = sum(t.out_of_line for t in earlier[-(FED_UP_TURNS - 1):])
            hurt_before = [t.hurt for t in earlier]
        ending = ends(judged, cools, out_of_line_before, hurt_before)
        way: Parting = "hangs_up" if in_call is not None else "parts"
        affinity_lines = (
            affinity_prompt(
                affinity.tier,
                judged,
                way if ending or cools else None,
                way if warns(judged, cools, out_of_line_before, hurt_before) else None,
            )
            if affinity is not None
            else []
        )
        world_prompt = (
            self._world.prompt(character.name, local_date(now, timezone)) if self._world else None
        )
        photo_asked = (
            photo_turn(asked_photo, affinity and affinity.tier, eligibility)
            if eligibility is not None else None
        )
        about_photo = CANNOT_SEND if eligibility is None else photo_asked and photo_asked.prompt
        prompt = self._prompt(
            character, world_prompt, producer_prompt(profile),
            chat_history(messages, turns),
            narrations(record, self._gift_catalog, timezone, her_days),
            [
                self._now_section(
                    known, occasion, now, timezone, profile, last_contact, affinity_lines,
                    known_weather,
                ),
                *_moments_told(known, now, timezone, affinity),
                *_letters_told(read.letters),
                *([about_photo] if about_photo else []),
            ],
            [p for p in (retrieved.memories_prompt, retrieved.prompt) if p],
            text, voiced_by,
        )

        # Offered on every turn, so that what goes before the history (the tools, with
        # many services) opens every turn's prompt alike, for the service to cache it.
        her_look_ups = self._her_now.look_ups(known, occasion)
        tools: list[Tool] = [*([RECALL_STORY_TOOL] if self._retrieval else []), *her_look_ups]
        parser = ReplyParser()
        step, asked_again = 0, False
        try:
            while True:
                # The last round offers the same tools, as some models drop what they thought
                # once the tools change, but forbids calling them; so does a turn that
                # already recalled an episode, its one round its last.
                forbidden = step == MAX_TOOL_ROUNDS or retrieved.recalled
                said = ""
                calls: list[ToolCall] = []
                reasoning: list[Reasoning] = []
                markup = _Markup()
                before, shown = deepcopy(parser), False
                stream = llms.chat.stream(prompt, tools, forbid_calls=forbidden)
                try:
                    while (item := await _unless_stopped(stop, anext, stream, None)) is not None:
                        if isinstance(item, ToolCall):
                            calls.append(item)
                            continue
                        if isinstance(item, Reasoning):
                            reasoning.append(item)
                            continue
                        let_through = markup.feed(item)
                        said += let_through
                        for event in parser.feed(let_through):
                            shown = True
                            if isinstance(event, PhotoTagged):
                                if photo_asked and photo_asked.keeps_tag:
                                    yield self._begin_photo(
                                        character, event.tag, conversation.user_id, photo
                                    )
                                continue
                            yield event
                        if markup.found:
                            break
                finally:
                    if (close := getattr(stream, "aclose", None)) is not None:
                        await close()  # a stream left part-way lets go of its connection
                if markup.found:
                    log.warning("the chat model wrote out tool-call markup in conversation %s",
                                conversation.id)
                    if not shown:  # none of the round shown: as if it never was
                        parser = before
                        if not asked_again:
                            asked_again = True
                            continue
                    # What she said before it stands; the round goes no further.
                    calls = []
                else:
                    said += (rest := markup.finish())
                    for event in parser.feed(rest):
                        if not isinstance(event, PhotoTagged):  # held back only before markup
                            yield event
                for event in parser.finish():
                    if not isinstance(event, PhotoTagged):  # never: a tag closes as it is fed
                        yield event
                # A call to a tool not offered, or made when forbidden, goes unanswered.
                if not calls or not tools or forbidden:
                    break
                offered = {t.name for t in tools}
                looks: list[Look] = []
                for call in calls:
                    if call.name in offered and call.name in LOOKS and LOOKS[call.name] not in looks:
                        looks.append(LOOKS[call.name])
                if looks:
                    yield LookingUp(tuple(looks))
                prompt = [
                    *prompt,
                    ChatMessage("assistant", said, tuple(calls), reasoning=tuple(reasoning)),
                ]
                last_round = step + 1 == MAX_TOOL_ROUNDS
                for call in calls:
                    result = await _unless_stopped(
                        stop, self._call_tool, character, call, known, known_weather
                    )
                    if last_round:
                        note = LOOKED_UP_NOTE if any(
                            call.name == t.name for t in her_look_ups
                        ) else LAST_ROUND_NOTE
                        result = f"{result}\n\n{note}"
                    prompt.append(ChatMessage("tool", result, tool_call_id=call.id))
                step += 1
        except _Stopped:
            pass

        if not parser.complete:
            raise EmptyReply("对话模型没有返回任何内容")
        typed = (
            None if in_call is not None
            else Typed(hurt(judged), judged is not None and judged.out_of_line)
        )
        ends_conversation = typed is not None and ending is not None
        # Once handed in, the turn is recorded whatever becomes of it, and what comes of that
        # is told all the same, should the turn be cancelled meanwhile, the user gone, say:
        # in a task of its own, which carries this one's context, so that a call taking the
        # turn is told it is the one.
        photo.handed_in = True
        keeping = asyncio.ensure_future(self._keep(
            conversation, text, said_at, parser.complete, judged, affinity, typed,
            ends_conversation, photo, her_day,
        ))
        try:
            reply, affinity, rewarded, unwell = await asyncio.shield(keeping)
        except ConversationEnded:  # elsewhere, as the turn was under way
            yield TurnRejected(ENDED)
            return
        memory.write_down(history, text, reply, retrieved.query_vector)
        turn = sum(m.role == "user" for m in messages) + 1
        self._titles.after_turn(conversation, turn, llms.background, llms.hold_background)
        ended = await self._store.ended(conversation.id) if ends_conversation else None
        if ended is not None and ending is not None:
            for listener in self._ended_listeners:
                listener(conversation.id, ending)
        if judged is not None and self._affinities is not None:
            yield TurnJudged(
                judged,
                reply.affinity is not None and reply.affinity.cooldown,
                ending if ends_conversation else None,
            )
        if in_call is not None:
            yield CallTurnRecorded(
                judged is not None and judged.out_of_line,
                ending,
                affinity and affinity.cooldown_until,
                hurt(judged),
            )
        if photo_asked and photo_asked.used_up_until is not None:
            yield PhotosUsedUp(photo_asked.used_up_until.isoformat())
        yield TurnDone(
            reply.without_cues(), affinity and affinity.shown(), ended and ended.shown(), rewarded,
            unwell and unwell.shown(),
        )

    async def reach_out(
        self, conversation: Conversation, llm: ChatLLM, voiced_by: FishAudioModel | None = None
    ) -> list[Segment]:
        """What she says first in `conversation`, the user not talking to her (GLOSSARY.md
        「搭话」), on `llm`: its segments, as the model wrote them, delivery cues and all, as
        `voiced_by` reads them, the model it would be read aloud with (None if none). Her
        prompt is laid out as a text turn's (ADR-0020), and opens as the next one's will, but
        for what changes from turn to turn: she is told what time it is and that they are not
        talking and when they last were, how she speaks in her tier, her latest moments, if any
        (`recent_moments`), the letters she wrote them last, if any, the memories she reaches
        out with (`Memories.for_reaching_out`), and how to reach out, about her moments too if
        told of any; then, where the user's words would be, the events and her reach-outs
        since the last turn and that she wants to say something first. Nothing else is retrieved, no tool offered, nothing judged.
        Raises EmptyReply if the model says nothing she could say, and whatever the model
        raises."""
        known = await self._her_now.read(
            conversation.user_id, conversation.character_id, None, "apart"
        )
        read = await self._db.read(self._before_reaching_out, conversation, self._affinity_on)
        character, record, affinity, last_contact, profile = (
            read.character, read.record, read.affinity, read.last_contact, read.profile
        )
        messages = [entry for entry in record if isinstance(entry, Message)]
        timezone = effective_timezone(profile, None)
        now = self._clock()
        known_weather = await self._her_now.weather("apart", profile.city, now, last_contact)
        world_prompt = (
            self._world.prompt(character.name, local_date(now, timezone)) if self._world else None
        )
        her_days = known.her_days
        told = narrations(record, self._gift_catalog, timezone, her_days)
        told[None] = _since_last_turn(record, self._gift_catalog, timezone, her_days)
        memories = await self._memory.for_reaching_out(
            conversation, timezone, last_turn_query(messages)
        )
        moments = _moments_told(known, now, timezone, affinity)
        prompt = self._prompt(
            character, world_prompt, producer_prompt(profile),
            chat_history(messages, self._history_turns()), told,
            [
                self._now_section(
                    known, "apart", now, timezone, profile, last_contact, tier_prompt(affinity),
                    known_weather,
                ),
                *moments,
                *_letters_told(read.letters),
            ],
            [
                *([memories] if memories else []),
                REACH_OUT_RULES_WITH_MOMENTS if moments else REACH_OUT_RULES,
            ],
            WANTS_TO_REACH_OUT, voiced_by,
        )
        parser = ReplyParser()
        stream = llm.stream(prompt)
        try:
            async for item in stream:
                if isinstance(item, str):
                    parser.feed(item)  # a photo tag is dropped: she sends none
        finally:
            if (close := getattr(stream, "aclose", None)) is not None:
                await close()
        parser.finish()
        if not parser.complete:
            raise EmptyReply("对话模型没有返回任何内容")
        return parser.complete

    def _before_turn(
        self,
        db: sqlite3.Connection,
        conversation: Conversation,
        in_call: InCall | None,
        own_image: ImageSettings | None,
        affinity_on: bool,
    ) -> _BeforeAsking:
        """What a turn of `conversation` reads before it is asked, through `db`, all in one
        read: `in_call` if it is taken in one, bringing the user's `own_image` generation if
        any, her affinity if `affinity_on`."""
        return self._read_before_asking(
            db, conversation, in_call=in_call is not None, own_image=own_image,
            sends_photo=True, affinity_on=affinity_on,
            connected_at=in_call.connected_at if in_call is not None else None,
        )

    def _before_reaching_out(
        self, db: sqlite3.Connection, conversation: Conversation, affinity_on: bool
    ) -> _BeforeAsking:
        """What her reaching out in `conversation` reads before she is asked, through `db`,
        as a typed turn would, all in one read; she sends no photo."""
        return self._read_before_asking(
            db, conversation, in_call=False, own_image=None, sends_photo=False,
            affinity_on=affinity_on,
        )

    def _read_before_asking(
        self,
        db: sqlite3.Connection,
        conversation: Conversation,
        *,
        in_call: bool,
        own_image: ImageSettings | None,
        sends_photo: bool,
        affinity_on: bool,
        connected_at: datetime | None = None,
    ) -> _BeforeAsking:
        """What a turn or a reach-out in `conversation` reads before she is asked, through
        `db`: what it may send for a photo only if it `sends_photo`, her affinity only if
        `affinity_on`, as told on the event loop as it was handed in; in a call that
        `connected_at` then, when they were last in touch before it."""
        character = self._characters[conversation.character_id]
        user_id, character_id = conversation.user_id, conversation.character_id
        last_contact = None if in_call else read_last_contact(db, user_id, character_id)
        last_apart = (
            read_last_contact(db, user_id, character_id, before=connected_at)
            if in_call and connected_at is not None else last_contact
        )
        return _BeforeAsking(
            read_ended(db, conversation.id) is not None,
            character,
            read_record(db, conversation.id),
            last_contact,
            self._affinity(db, conversation) if affinity_on else None,
            self._photo_eligibility(db, conversation, character, own_image)
            if sends_photo else None,
            read_profile(db, conversation.user_id),
            last_apart,
            read_earlier(db, user_id, character_id),
        )

    def _photo_eligibility(
        self,
        db: sqlite3.Connection,
        conversation: Conversation,
        character: Character,
        own: ImageSettings | None,
    ) -> Eligibility | None:
        """What a turn with her may send, bringing the user's `own` image generation if any,
        if it could have a photo, and so the judge model is asked whether it asks for one:
        there being the judge model to ask, typed or in a call alike; read through `db`."""
        has_judge = self._retrieval is not None or self._affinity_judge is not None
        if not has_judge or self._photos is None:
            return None
        return self._photos.eligibility(db, character, conversation.user_id, own)

    async def photo_came_out(self, photo_id: str, user_id: str) -> Photo | None:
        """The photo a turn of the user's sent (`photo`), once it has come out, sent or not,
        and is kept with her reply; None if it is not kept, its reply never recorded."""
        if self._photos is None:
            return None
        return await self._photos.came_out(photo_id, user_id)

    def _begin_photo(
        self, character: Character, tag: str, user_id: str, photo: _Photo
    ) -> PhotoPending:
        """Begin the photo her `tag` says, the turn's one, for the user."""
        assert self._photos is not None
        photo.id, photo.tag = self._photos.begin(character, tag, user_id, photo.own), tag
        return PhotoPending(photo.id)

    @property
    def _affinity_on(self) -> bool:
        """Whether turns go by affinity now: the engine has it, and it is on."""
        return self._affinities is not None and self._affinities.on

    def _affinity(self, db: sqlite3.Connection, conversation: Conversation) -> Status:
        """Her affinity with the user as the turn begins, read through `db`, affinity on."""
        assert self._affinities is not None
        return self._affinities.read_status(db, conversation.user_id, conversation.character_id)

    async def _cools(self, conversation: Conversation, judged: Judged | None) -> bool:
        """Whether the turn, as `judged`, would begin a cooldown; never if not judged."""
        if judged is None or self._affinities is None:
            return False
        return await self._affinities.cools(
            conversation.user_id, conversation.character_id, judged
        )

    async def _keep(
        self,
        conversation: Conversation,
        text: str,
        said_at: str,
        reply: list[Segment],
        judged: Judged | None,
        affinity: Status | None,
        typed: Typed | None,
        ends_conversation: bool,
        photo: _Photo,
        her_day: HerDay,
    ) -> tuple[Message, Status | None, Rewarded | None, ConversationEvent | None]:
        """Record the turn (`_record`), and tell what comes of it: should it begin a
        cooldown, those `on_cooled` has; the photos, whether her reply is recorded with the
        photo, if any; and the activity log, what the turn was rewarded for. The reply, her
        affinity after it, what it was rewarded with, and her being unwell, if recorded
        with it."""
        try:
            message, affinity, rewarded, unwell = await self._db.write(
                self._record,
                conversation, text, said_at, reply, judged, affinity, typed, ends_conversation,
                NewPhoto(photo.id, photo.tag) if photo.id else None,
                self._happenings and self._happenings.open, her_day,
            )
        except Exception:
            if photo.id is not None and self._photos is not None:
                self._photos.dropped(photo.id)
            raise
        until = affinity and affinity.cooldown_until
        if message.affinity is not None and message.affinity.cooldown and until is not None:
            # In the turn's context: her calls with the user hang up there and then, one this
            # turn is taken in after it.
            for cooled in self._cooled_listeners:
                cooled(conversation.user_id, conversation.character_id, until)
        if photo.id is not None and self._photos is not None:
            await self._photos.recorded(photo.id)
        if self._happenings is not None:
            await self._happenings.write_records(conversation.user_id, rewarded)
        return message, affinity, rewarded, unwell

    def _record(
        self,
        db: sqlite3.Connection,
        conversation: Conversation,
        text: str,
        said_at: str,
        reply: list[Segment],
        judged: Judged | None,
        affinity: Status | None,
        typed: Typed | None,
        ends_conversation: bool,
        photo: NewPhoto | None,
        happenings_open: Open | None,
        her_day: HerDay,
    ) -> tuple[Message, Status | None, Rewarded | None, ConversationEvent | None]:
        """Record the turn, as said at `said_at`, through `db`, in one transaction with all
        it changes: her being unwell before it, should `her_day` have her in her period and
        it be the user's first turn with her in it (`add_unwell`), her affinity as `judged`
        says, if judged, with what a typed turn came to, her ending the conversation after
        it if she does, the photo she sends with it if any, and what it counts towards
        (`Happenings.turn_recorded`), with what is `happenings_open` as it was handed in,
        all of it or none.
        The reply, her affinity after it (`affinity`, as the turn began, if not judged),
        what it was rewarded with, and her being unwell, if recorded."""
        unwell = (
            add_unwell(db, conversation, her_day.first_day, her_day.day - 1, said_at)
            if isinstance(her_day, Period) else None
        )
        change = None
        if judged is not None and self._affinities is not None:
            change, affinity = self._affinities.change(
                db, conversation.user_id, conversation.character_id, judged
            )
        message = add_turn(
            db, conversation.id, text, reply, change, said_at, typed, ends_conversation, photo
        )
        rewarded = (
            self._happenings.turn_recorded(
                db, conversation.user_id, conversation.character_id,
                affinity and affinity.tier, happenings_open,
            )
            if self._happenings is not None and happenings_open is not None else None
        )
        return message, affinity, rewarded, unwell

    async def _call_tool(
        self,
        character: Character,
        call: ToolCall,
        known: KnownNow,
        known_weather: KnownWeather | None,
    ) -> str:
        """The tool's result, or what went wrong, for the model to read: what she recalls,
        or looks up of what the turn read of now (`HerNow.look_up`)."""
        if call.name != RECALL_STORY_TOOL.name or self._retrieval is None:
            looked = self._her_now.look_up(call.name, known, known_weather)
            return looked if looked is not None else f"没有 {call.name} 这个工具。"
        query = (call.arguments or {}).get("query")
        if not isinstance(query, str) or not query.strip():
            return "调用参数有误：需要 query（要回顾的事，一句概括）。"
        return await self._retrieval.recall_story(character, query.strip())

    def _now_section(
        self,
        known: KnownNow,
        occasion: Occasion,
        now: datetime,
        timezone: str,
        profile: ProducerProfile,
        last_contact: datetime | None,
        affinity_lines: Sequence[str],
        known_weather: KnownWeather | None = None,
    ) -> str:
        """The prompt section of what she knows of now on `occasion` (`HerNow.lines`)."""
        return "\n".join(self._her_now.lines(
            known, occasion, now, timezone, profile, last_contact, affinity_lines,
            known_weather=known_weather,
        ))

    def _prompt(
        self,
        character: Character,
        world_prompt: str | None,
        about_producer: str,
        history: list[Message],
        narration: dict[int | None, str],
        about_turn: list[str],
        closing: list[str],
        text: str,
        voiced_by: FishAudioModel | None,
    ) -> list[ChatMessage]:
        """The prompt (ADR-0020): what changes from turn to turn tells first `about_turn`, then,
        should any photo of the history not have been sent, what that means, then `closing`:
        what retrieval found, or how she is to reach out."""
        # What every user's turns with her that day open with, apart, for a service to cache.
        shared = [*always_known(character, world_prompt), format_instructions(voiced_by)]
        prompt = [
            ChatMessage("system", "\n\n".join(shared), cache_breakpoint=True),
            ChatMessage("system", about_producer),
        ]
        for message in history:
            if message.role == "user":
                told = narration.get(message.id, "")
                prompt.append(ChatMessage("user", f"{told}{message.text or ''}"))
            else:
                prompt.append(ChatMessage("assistant", format_reply(
                    message.segments,
                    message.photo.tag if message.photo else None,
                    message.photo_failed,
                )))
        if history:  # what the next turn opens with too, for a service to cache
            prompt[-1] = replace(prompt[-1], cache_breakpoint=True)
        context = [*about_turn]
        if any(m.photo_failed for m in history):
            context.append(NOT_RECEIVED)
        context += closing
        prompt.append(ChatMessage("system", "\n\n".join(context)))
        prompt.append(ChatMessage("user", f"{narration.get(None, '')}{text}"))
        return prompt
