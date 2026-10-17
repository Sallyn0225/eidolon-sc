"""The conversation engine: one conversation turn in, the character's reply out.

It knows nothing about voice. Given a conversation and the user's input text it
retrieves what the turn calls for, assembles the prompt, streams the chat model's structured reply as per-segment
deltas, and records both sides of the turn once the reply is complete.

Every turn, typed or spoken, speaks the same protocol: `user` (the input as taken up),
then any `delta`s, then `done` or `error`. Among the deltas, `SegmentComplete` says
when a segment is complete; it stays on the server. Input that is blank or too long is rejected
before the model is asked; a turn that is rejected or fails part-way leaves no record,
and what went wrong stays in the server log.

When retrieval is available the chat model is offered the recall-story tool on every
turn, but forbidden to call it in one that already recalled an episode. Its calls are
answered and the model asked again, once at most since every round costs the model's
time to first token; whatever it says along the way is part of the reply, and only the
reply is recorded.

Every turn carries the world setting, when there is one, after the character sheet: the
office and its units, and the character's own songs and lives, each release and live
told as past or still to come by the day it is where the user is, the day the prompt about now tells.
The two open the prompt, with how she is to format her reply, as a system message of their
own, the same for every user's turns with her that day, marked for the service to cache;
who the producer is follows in another, then the conversation so far. What changes from
turn to turn (the time, her affinity, what retrieval found) comes after the conversation,
in a system message just before what the user is saying now, and is not carried into the
turns after it: so each turn's prompt opens as the one before it did, up to the end of the
conversation so far, marked for the service to cache too (ADR-0020).

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
turn's to wait for: `photo_came_out` tells, once it has.

She learns of the conversation's events (GLOSSARY.md「对话事件」) from a line of narration
before the user's words that came next, or before what the user is saying now; it leaves
her prompt with those words. Until she has replied after a gift, she is also told to respond
to it, once, however many came. Retrieval, memory and the judge model read only the messages.
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from typing import Literal, ParamSpec, TypeVar

from eidolon.affinity import (
    FED_UP_TURNS,
    Affinities,
    Change,
    EndsFor,
    Judged,
    Parting,
    Status,
    affinity_prompt,
    ends,
    hurt,
    warns,
)
from eidolon.affinity_judge import AffinityJudge
from eidolon.characters import Character
from eidolon.clock import Clock
from eidolon.config import FishAudioModel, ImageSettings
from eidolon.gift_catalog import Gift
from eidolon.judge import JudgeError
from eidolon.llm import ChatMessage, Reasoning, Tool, ToolCall, TurnLLMs
from eidolon.memory import Memories
from eidolon.own_keys import OwnKeyFailed
from eidolon.photos import NOT_RECEIVED, Eligibility, Photos, photo_turn
from eidolon.producer import effective_timezone, local_date, now_prompt, producer_prompt
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
    Recorded,
    Store,
    Typed,
    timestamp,
)
from eidolon.titles import Titles
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


@dataclass(frozen=True)
class PhotosUsedUp:
    """The user asked for a photo with their photos this hour used up: they may ask again
    at `retry_at` (ISO). Comes just before `done`."""

    retry_at: str
    type: Literal["photos-used-up"] = field(default="photos-used-up", init=False)


@dataclass(frozen=True)
class TurnDone:
    """The recorded reply, with how the turn changed her affinity if it did; her affinity
    after it (`Status.shown`), None where affinity is off; and her ending the conversation
    after it (`ConversationEvent.shown`), None if she did not. The turn succeeded."""

    message: Message
    affinity: dict[str, str | None] | None = None
    ended: dict | None = None
    type: Literal["done"] = field(default="done", init=False)



@dataclass(frozen=True)
class InCall:
    """The turn is taken in a call, in which the user has been out of line (GLOSSARY.md
    「不该说的话」) `out_of_line` times so far, in turns recorded, which took `hurts` each off
    her affinity (`affinity.hurt`), the latest last."""

    out_of_line: int = 0
    hurts: tuple[float, ...] = ()


@dataclass(frozen=True)
class CallTurnRecorded:
    """What a turn of a call, now recorded, comes to for the call: whether the user was out
    of line in it, and whether she hangs up after it and why; if for a cooldown, when it
    ends (None should the cooldown not have begun after all, another turn recorded
    meanwhile); how much it took off her affinity (`affinity.hurt`). Comes just before
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
"""A turn's events: `user`, then `photo` if she sends one, any `delta`s, then
`photos-used-up` if the user's photos are, and `done`, or `error`. `shown(event)` is the
event as it goes out to the browser, except `SpeechDelta`, `SegmentComplete`,
`CallTurnRecorded` and `TurnJudged`, which do not."""


def shown(event: TurnEvent) -> dict:
    """The event as it goes out to the browser: `done`'s reply as `Message.shown` has it."""
    if isinstance(event, TurnDone):
        return asdict(event) | {"message": event.message.shown()}
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


async def _judged(
    judge: AffinityJudge,
    character: Character,
    history: list[Message],
    text: str,
    affinity: bool,
    photo: bool,
) -> tuple[Judged | None, bool]:
    """Asked about `affinity`, what saying `text` does to her affinity (None if not, or if it
    cannot be told); asked about `photo`, whether it asks her for one (no if not, or if it
    cannot be told)."""
    try:
        return await judge.judge(character, history, text, affinity, photo)
    except JudgeError:
        log.warning("judging apart failed; affinity stays as it is, and no photo", exc_info=True)
        return None, False


@dataclass
class _Photo:
    """The photo a turn sends, on the user's `own` image generation if the turn brings it:
    once it begins one, its id and the tag she wrote for it, and whether her reply is
    recorded with it."""

    own: ImageSettings | None = None
    id: str | None = None
    tag: str = ""
    recorded: bool = False


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


def _narration(event: ConversationEvent, gift_catalog: Mapping[str, Gift]) -> str:
    """What she is told of `event`, as it was."""
    if event.kind == "hung_up":
        return "（你挂断了制作人的电话。）"
    if event.kind == "ended":  # only read by a turn it will reject
        return "（你结束了和制作人的对话。）"
    assert event.gift_id is not None
    liked = "这是你喜欢的东西。" if event.liked else ""
    return f"（制作人送给你一份{gift_catalog[event.gift_id].name}。{liked}）"


def narrations(
    record: list[Recorded], gift_catalog: Mapping[str, Gift]
) -> dict[int | None, str]:
    """The narration of the events in `record`, by the id of the user message each comes
    before, None for those after them all: one line for each event, then, if she has not
    replied since a gift, `RESPOND_TO_GIFTS`."""
    lines: list[str] = []
    told: dict[int | None, str] = {}
    unanswered = False
    for entry in record:
        if isinstance(entry, ConversationEvent):
            lines.append(f"{_narration(entry, gift_catalog)}\n")
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


class ConversationEngine:
    def __init__(
        self,
        store: Store,
        characters: dict[str, Character],
        gift_catalog: Mapping[str, Gift],
        memory: Memories,
        titles: Titles,
        clock: Clock,
        retrieval: Retrieval | None = None,
        history_turns: Callable[[], int | None] = lambda: None,
        world: World | None = None,
        affinities: Affinities | None = None,
        affinity_judge: AffinityJudge | None = None,
        photos: Photos | None = None,
    ) -> None:
        """Without `retrieval`, turns carry no story or character facts and find no
        memories. Each turn reads only the conversation's latest turns, as many as
        `history_turns` says as it begins, or all of them if None; the chat model reads
        at least as many (`chat_history`). Without `world`, turns
        carry no world setting. Without `affinities`, turns change no affinity; with them,
        retrieval's judge judges what turns do to it, or without retrieval
        `affinity_judge`, which judges whether turns ask for a photo too. Without `photos`,
        or without the judge model, no turn has a photo."""
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
        self._ended_listeners: list[Callable[[str, EndsFor], None]] = []

    def on_ended(self, listener: Callable[[str, EndsFor], None]) -> None:
        """Have `listener` told the conversation's id, and why, as she ends one, once it is
        recorded."""
        self._ended_listeners.append(listener)

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
    ) -> AsyncIterator[TurnEvent]:
        """Take one turn on `llms`, `in_call` if it is taken in one, its reply voiced with
        `voiced_by` (None for a text turn's), which has her write delivery cues as it reads
        them, her photo on the user's `own_image` generation if it brings it. `device_timezone`
        is the time zone the user's device reports, used unless the producer profile sets
        one. Once `stop` is set, the turn goes no further and is recorded with the segments
        complete by then."""
        text = text.strip()
        yield UserSaid(text)
        if not text or len(text) > MAX_INPUT_LENGTH:
            yield TurnRejected(TOO_LONG if text else BLANK)
            return
        photo = _Photo(own_image)
        try:
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
            if photo.id is not None and not photo.recorded and self._photos is not None:
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
        if self._store.ended(conversation.id) is not None:
            yield TurnRejected(ENDED)
            return
        character = self._characters[conversation.character_id]
        record = self._store.record(conversation.id)
        # Said after reading the record, so an event this turn's prompt does not tell of
        # comes before the turn, and is told of with its words from the next turn on.
        said_at = timestamp()
        messages = [entry for entry in record if isinstance(entry, Message)]
        turns = self._history_turns()
        history = latest_turns(messages, turns)  # what all but the chat model read
        affinity = self._affinity(conversation)
        judging = affinity is not None and not affinity.cooling
        eligibility = self._photo_eligibility(conversation, character, photo.own)
        asking_photo = eligibility is not None
        judged_apart = None
        if (judging or asking_photo) and self._retrieval is None and self._affinity_judge:
            judged_apart = asyncio.ensure_future(
                _judged(self._affinity_judge, character, history, text, judging, asking_photo)
            )
        try:
            profile = self._store.get_profile(conversation.user_id)
            timezone = effective_timezone(profile, device_timezone)
            memory = await self._memory.begin(
                conversation, timezone, llms.background, llms.hold_background
            )
            retrieved = (
                await self._retrieval.retrieve(
                    character, history, text, memory, judging, asking_photo
                )
                if self._retrieval
                else Retrieved(None)
            )
            judged, asked_photo = (
                await judged_apart if judged_apart is not None
                else (retrieved.judged, retrieved.photo)
            )
        finally:
            if judged_apart is not None and not judged_apart.done():
                judged_apart.cancel()
        now = self._clock()
        cools = self._cools(conversation, judged)
        if in_call is not None:
            out_of_line_before, hurt_before = in_call.out_of_line, in_call.hurts
        else:
            # As many as are weighed, so that whether she warns is told against the latest
            # before this one; out of line is counted in the latest with this one among them.
            earlier = self._store.typed_turns(conversation.id, FED_UP_TURNS)
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
        prompt = self._prompt(
            character, world_prompt, producer_prompt(profile),
            chat_history(messages, turns), narrations(record, self._gift_catalog),
            now_prompt(
                profile, now, timezone, in_call=in_call is not None, affinity_lines=affinity_lines
            ),
            retrieved, text, voiced_by, photo_asked and photo_asked.prompt,
        )

        # Offered on every turn, so that what goes before the history (the tools, with
        # many services) opens every turn's prompt alike, for the service to cache it.
        tools: list[Tool] = [RECALL_STORY_TOOL] if self._retrieval else []
        parser = ReplyParser()
        try:
            for step in range(MAX_TOOL_ROUNDS + 1):
                # The last round offers the same tools, as some models drop what they thought
                # once the tools change, but forbids calling them; so does a turn that
                # already recalled an episode, its one round its last.
                forbidden = step == MAX_TOOL_ROUNDS or retrieved.recalled
                said = ""
                calls: list[ToolCall] = []
                reasoning: list[Reasoning] = []
                stream = llms.chat.stream(prompt, tools, forbid_calls=forbidden)
                try:
                    while (item := await _unless_stopped(stop, anext, stream, None)) is not None:
                        if isinstance(item, ToolCall):
                            calls.append(item)
                            continue
                        if isinstance(item, Reasoning):
                            reasoning.append(item)
                            continue
                        said += item
                        for event in parser.feed(item):
                            if isinstance(event, PhotoTagged):
                                if photo_asked and photo_asked.keeps_tag:
                                    yield self._begin_photo(
                                        character, event.tag, conversation.user_id, photo
                                    )
                                continue
                            yield event
                finally:
                    if (close := getattr(stream, "aclose", None)) is not None:
                        await close()  # a stream left part-way lets go of its connection
                for event in parser.finish():
                    if not isinstance(event, PhotoTagged):  # never: a tag closes as it is fed
                        yield event
                # A call to a tool not offered, or made when forbidden, goes unanswered.
                if not calls or not tools or forbidden:
                    break
                prompt = [
                    *prompt,
                    ChatMessage("assistant", said, tuple(calls), reasoning=tuple(reasoning)),
                ]
                last_round = step + 1 == MAX_TOOL_ROUNDS
                for call in calls:
                    result = await _unless_stopped(stop, self._call_tool, character, call)
                    if last_round:
                        result = f"{result}\n\n{LAST_ROUND_NOTE}"
                    prompt.append(ChatMessage("tool", result, tool_call_id=call.id))
        except _Stopped:
            pass

        if not parser.complete:
            raise EmptyReply("对话模型没有返回任何内容")
        typed = (
            None if in_call is not None
            else Typed(hurt(judged), judged is not None and judged.out_of_line)
        )
        ends_conversation = typed is not None and ending is not None
        try:
            reply, affinity = self._record(
                conversation, text, said_at, parser.complete, judged, affinity, typed,
                ends_conversation, NewPhoto(photo.id, photo.tag) if photo.id else None,
            )
        except ConversationEnded:  # elsewhere, as the turn was under way
            yield TurnRejected(ENDED)
            return
        if photo.id is not None and self._photos is not None:
            photo.recorded = True
            self._photos.recorded(photo.id)
        memory.write_down(history, text, reply, retrieved.query_vector)
        turn = sum(m.role == "user" for m in messages) + 1
        self._titles.after_turn(conversation, turn, llms.background, llms.hold_background)
        ended = self._store.ended(conversation.id) if ends_conversation else None
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
        yield TurnDone(reply.without_cues(), affinity and affinity.shown(), ended and ended.shown())

    def _photo_eligibility(
        self,
        conversation: Conversation,
        character: Character,
        own: ImageSettings | None,
    ) -> Eligibility | None:
        """What a turn with her may send, bringing the user's `own` image generation if any,
        if it could have a photo, and so the judge model is asked whether it asks for one:
        there being the judge model to ask, typed or in a call alike."""
        has_judge = self._retrieval is not None or self._affinity_judge is not None
        if not has_judge or self._photos is None:
            return None
        return self._photos.eligibility(character, conversation.user_id, own)

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

    def _affinity(self, conversation: Conversation) -> Status | None:
        """Her affinity with the user as the turn begins; None where affinity is off."""
        if self._affinities is None:
            return None
        return self._affinities.status(conversation.user_id, conversation.character_id)

    def _cools(self, conversation: Conversation, judged: Judged | None) -> bool:
        """Whether the turn, as `judged`, would begin a cooldown; never if not judged."""
        if judged is None or self._affinities is None:
            return False
        return self._affinities.cools(conversation.user_id, conversation.character_id, judged)

    def _record(
        self,
        conversation: Conversation,
        text: str,
        said_at: str,
        reply: list[Segment],
        judged: Judged | None,
        affinity: Status | None,
        typed: Typed | None,
        ends_conversation: bool,
        photo: NewPhoto | None,
    ) -> tuple[Message, Status | None]:
        """Record the turn, as said at `said_at`, changing her affinity as `judged` says, if
        judged, with what a typed turn came to, her ending the conversation after it if she
        does, and the photo she sends with it if any: the reply, and her affinity after it
        (`affinity`, as the turn began, if not judged)."""

        def add_turn(change: Change | None) -> Message:
            return self._store.add_turn(
                conversation.id, text, reply, change, said_at, typed, ends_conversation, photo
            )

        if judged is None or self._affinities is None:
            return add_turn(None), affinity
        return self._affinities.change(
            conversation.user_id, conversation.character_id, judged, add_turn
        )

    async def _call_tool(self, character: Character, call: ToolCall) -> str:
        """The tool's result, or what went wrong, for the model to read."""
        if call.name != RECALL_STORY_TOOL.name or self._retrieval is None:
            return f"没有 {call.name} 这个工具。"
        query = (call.arguments or {}).get("query")
        if not isinstance(query, str) or not query.strip():
            return "调用参数有误：需要 query（要回顾的事，一句概括）。"
        return await self._retrieval.recall_story(character, query.strip())

    def _prompt(
        self,
        character: Character,
        world_prompt: str | None,
        about_producer: str,
        history: list[Message],
        narration: dict[int | None, str],
        about_now: str,
        retrieved: Retrieved,
        text: str,
        voiced_by: FishAudioModel | None,
        about_photo: str | None,
    ) -> list[ChatMessage]:
        # What every user's turns with her that day open with, apart, for a service to cache.
        shared = [character.sheet]
        if world_prompt:
            shared.append(world_prompt)
        shared.append(format_instructions(voiced_by))
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
        context = [about_now]
        if about_photo:
            context.append(about_photo)
        if any(m.photo_failed for m in history):
            context.append(NOT_RECEIVED)
        if retrieved.memories_prompt:
            context.append(retrieved.memories_prompt)
        if retrieved.prompt:
            context.append(retrieved.prompt)
        prompt.append(ChatMessage("system", "\n\n".join(context)))
        prompt.append(ChatMessage("user", f"{narration.get(None, '')}{text}"))
        return prompt
