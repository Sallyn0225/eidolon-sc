"""Turns during a voice call, at the Pipecat stage that wraps the conversation engine.

Speech recognition, TTS and the transport are left out: the stage is fed what Soniox
and the browser's data channel would deliver, and what it sends on is inspected where
Fish Audio (text frames) and the browser (server messages) would receive it.

What is a follow-on and what interrupts the character is `TurnTaking`'s, tested in
`test_turn_taking.py`; here are the frames and the engine it is wired to.
"""

import asyncio
import sqlite3
from collections.abc import Callable, Sequence
from contextlib import closing
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from functools import partial

import httpx
import pytest
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    CancelFrame,
    EndFrame,
    Frame,
    InterruptionFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    StartFrame,
    TextFrame,
    TranscriptionFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineWorker
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.processors.frameworks.rtvi.frames import (
    RTVIClientMessageFrame,
    RTVIServerMessageFrame,
)
from pipecat.tests.utils import SleepFrame, run_test
from pipecat.workers.runner import WorkerRunner

from eidolon.call import (
    SONIOX_FOLLOW_ON_TIMEOUT,
    Call,
    CallTurns,
    SegmentCompleteFrame,
    SegmentTextFrame,
)
from eidolon.call_outcome import CallLimits, CallOutcome
from eidolon.config import EmotionSettings, Settings
from eidolon.engine import MAX_INPUT_LENGTH
from eidolon.own_keys import BroughtKeys
from eidolon.store import Conversation
from tests.conftest import ClientFactory, store_in
from tests.fakes import (
    FAKE_JUDGE,
    HANG,
    FakeBackgroundLLM,
    FakeEmbedder,
    FakeJudge,
    FakeLLM,
    FakeReranker,
    FakeServiceClients,
    Judging,
    build_faked,
    level,
)
from tests.test_affinity_prompt import FEELINGS, about_now
from tests.test_affinity_turns import value
from tests.test_text_turn import start_conversation

NOW = datetime(2026, 9, 25, 12, 30, tzinfo=UTC)
MANO_REPLY = ["<ja>ほわっ、", "おはようございます！</ja><zh>哇，早上好！</zh><ja>今日も</ja><zh>今天也</zh>"]


class CallUnderTest:
    """One call into a fresh conversation with Mano, and the API to read its record."""

    def __init__(
        self, settings: Settings, client: httpx.AsyncClient, conversation: Conversation
    ):
        self._settings = settings
        self._client = client
        self.conversation = conversation

    @classmethod
    async def of(
        cls, settings: Settings, client: httpx.AsyncClient, conversation_id: str
    ) -> "CallUnderTest":
        """One into the conversation `conversation_id`."""
        async with store_in(settings.database_path) as store:
            conversation = await store.get_conversation(conversation_id)
        assert conversation is not None
        return cls(settings, client, conversation)

    async def run(
        self,
        llm: FakeLLM,
        frames: Sequence["ScriptStep"],
        *,
        muted: bool = False,
        limits: CallLimits = CallLimits(),
        memory: FakeBackgroundLLM | None = None,
        retrieval_judge: FakeJudge | None = None,
        embedder: FakeEmbedder | None = None,
        connected: bool = True,
        judge: FakeJudge | None = None,
        emotion: EmotionSettings | None = None,
        follow_on_timeout: float = SONIOX_FOLLOW_ON_TIMEOUT,
        affinity: Sequence[Judging] | None = None,
    ) -> tuple[list[str], list[dict]]:
        """Run the frames through; returns the text sent to TTS and the messages sent to the browser."""
        down = await self.run_frames(
            llm, frames, muted=muted, limits=limits, memory=memory,
            retrieval_judge=retrieval_judge, embedder=embedder, connected=connected,
            judge=judge, emotion=emotion, follow_on_timeout=follow_on_timeout,
            affinity=affinity,
        )
        spoken = [f.text for f in down if isinstance(f, SegmentTextFrame)]
        messages = [f.data for f in down if isinstance(f, RTVIServerMessageFrame)]
        return spoken, messages

    async def run_frames(
        self,
        llm: FakeLLM,
        frames: Sequence["ScriptStep"],
        *,
        muted: bool = False,
        limits: CallLimits = CallLimits(),
        memory: FakeBackgroundLLM | None = None,
        retrieval_judge: FakeJudge | None = None,
        embedder: FakeEmbedder | None = None,
        connected: bool = True,
        judge: FakeJudge | None = None,
        emotion: EmotionSettings | None = None,
        follow_on_timeout: float = SONIOX_FOLLOW_ON_TIMEOUT,
        affinity: Sequence[Judging] | None = None,
    ) -> Sequence[Frame]:
        """Run the frames through a call that, unless told otherwise, connects as it starts,
        remembering with the background model `memory`, if given, and retrieving with
        `retrieval_judge` and `embedder` (new ones unless given), with `judge` as the deployer's Jev judging
        each segment's emotion, if given, as `emotion` says, and its speech recognition
        taking `follow_on_timeout` at most to transcribe a follow-on. Given `affinity`, affinity is on, the judge model judging
        each turn's as it says (`FakeJudgeModel.judgings`)."""
        remembering = {} if memory is None else {
            "background_llm": memory, "retrieval_judge": retrieval_judge or FakeJudge(),
            "embedder": embedder or FakeEmbedder(),
            "reranker": FakeReranker(),
        }
        settings = self._settings if emotion is None else replace(self._settings, emotion=emotion)
        clients = FakeServiceClients()
        if affinity is not None:
            settings = replace(settings, judge=FAKE_JUDGE, affinity_and_gifts=True)
            clients.judge.judgings = list(affinity)
        backend = build_faked(
            settings, llm, clients=clients, clock=lambda: NOW, emotion_judge=judge,
            **remembering,
        )
        try:
            mano = backend.characters["mano"]
            admission = await backend.admissions.call(
                self.conversation.user_id, "mano", BroughtKeys()
            )
            call = Call(self.conversation, mano, admission.llms, muted, "standard")
            outcome = CallOutcome(
                admission, limits, backend.clock,
                partial(
                    backend.happenings.call_ended,
                    self.conversation.id, self.conversation.user_id, "mano",
                ),
            )
            turns = CallTurns(
                backend.engine, backend.store, call, outcome, follow_on_timeout,
                admission.keys.emotions,
            )
            if connected:
                turns.connected()
            if isinstance(frames, OneByOne):
                down = await run_one_by_one(turns, frames)
            elif any(isinstance(step, WaitFor | WaitEvent | Do) for step in frames):
                down = await run_script(turns, frames)
            else:
                plain = [step for step in frames if isinstance(step, Frame)]
                down, _ = await run_test(turns, frames_to_send=plain)
            await outcome.settle()
        finally:
            await backend.aclose()
        return down

    async def fail_while_cancelling_is_held_up(
        self, llm: FakeLLM, said: str, cancel_timeout: float
    ) -> None:
        """Take a turn, the user having said `said`, then have a voice service fail and
        the call end, as `_LiveCall` ends it, while its reply is in progress; something
        upstream of `CallTurns` holds the cancelling up past `cancel_timeout` seconds, so
        the call is settled before the turn is over."""
        backend = build_faked(self._settings, llm, clock=lambda: NOW)
        try:
            mano = backend.characters["mano"]
            admission = await backend.admissions.call(
                self.conversation.user_id, "mano", BroughtKeys()
            )
            call = Call(self.conversation, mano, admission.llms, False, "standard")
            outcome = CallOutcome(
                admission, CallLimits(), backend.clock,
                partial(
                    backend.happenings.call_ended,
                    self.conversation.id, self.conversation.user_id, "mano",
                ),
            )
            turns = CallTurns(
                backend.engine, backend.store, call, outcome, SONIOX_FOLLOW_ON_TIMEOUT
            )
            worker = PipelineWorker(
                Pipeline([HoldsUpCancelling(), turns]),
                cancel_timeout_secs=cancel_timeout,
                cancel_on_idle_timeout=False,
            )
            started = asyncio.Event()

            @worker.event_handler("on_pipeline_started")
            async def on_started(worker: PipelineWorker, frame: Frame) -> None:
                started.set()

            running = asyncio.create_task(WorkerRunner(handle_sigint=False).run(worker))
            await asyncio.wait_for(started.wait(), timeout=1)
            turns.connected()
            await worker.queue_frame(spoken(said))
            await asyncio.sleep(0.3)  # the reply is in progress

            assert outcome.service_failed(None) is not None
            await worker.cancel()
            await running
            await outcome.settle()
        finally:
            await backend.aclose()

    def turn_records(self) -> list[tuple[str, float | None]]:
        """Each turn's activity record: how it turned out, and how long the character
        took to start speaking, in milliseconds (「到开口」)."""
        with closing(sqlite3.connect(self._settings.database_path)) as db:
            return db.execute(
                "SELECT result, time_to_speak_ms FROM activity_records WHERE kind = 'turn'"
                " ORDER BY id"
            ).fetchall()

    async def record(self) -> list[tuple]:
        res = await self._client.get(f"/api/conversations/{self.conversation.id}/messages")
        return [(m["role"], m["text"], m["ja"], m["zh"]) for m in res.json()]

    async def said(self) -> list[str | None]:
        """What the user said in each recorded turn, None for the character's replies."""
        return [row[1] for row in await self.record()]


class HoldsUpCancelling(FrameProcessor):
    """Never passes on a `CancelFrame`, as a processor stuck cancelling would not."""

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if isinstance(frame, CancelFrame):
            await asyncio.Event().wait()
        await self.push_frame(frame, direction)


@pytest.fixture
async def mano_call(make_client: ClientFactory, settings: Settings):
    client = make_client(FakeLLM())
    return await CallUnderTest.of(settings, client, await start_conversation(client, "mano"))


class OneByOne(tuple[Frame, ...]):
    """Frames sent as a person would send them: see `run_one_by_one`."""


def one_by_one(*frames: Frame) -> OneByOne:
    return OneByOne(frames)


async def run_one_by_one(turns: CallTurns, frames: Sequence[Frame]) -> list[Frame]:
    """Run `frames` through `turns` as `run_test` does, sending each only once the turn
    the one before it set off, if any, is over, its reply done and the call's limits
    checked. Spaced out by time instead, a client message, being a system frame, could
    overtake a transcription still queued, and what came before the turn was over would
    be a follow-on to it. Returns the frames that reached the end of the pipeline."""
    received = Received()
    worker = PipelineWorker(
        Pipeline([turns, received]), cancel_on_idle_timeout=False, enable_rtvi=False
    )
    started = asyncio.Event()

    @worker.event_handler("on_pipeline_started")
    async def on_started(worker: PipelineWorker, frame: Frame) -> None:
        started.set()

    async def send() -> None:
        await asyncio.wait_for(started.wait(), timeout=1)
        turns_set_off = 0
        for frame in frames:
            if turns_set_off:  # (none waited for after the last: it may set none off)
                await asyncio.wait_for(received.replies_over(turns_set_off), timeout=5)
                await turns._inputs.join()  # over once the call's limits are checked
            await worker.queue_frame(frame)
            if isinstance(frame, TranscriptionFrame) or (
                isinstance(frame, RTVIClientMessageFrame) and frame.type == "user-text"
            ):
                turns_set_off += 1
        await worker.queue_frame(EndFrame())

    runner = WorkerRunner(handle_sigint=False)
    await runner.add_workers(worker)
    await asyncio.gather(runner.run(), send())
    return received.frames


class WaitFor:
    """Pause a call script until a downstream frame matching `predicate` arrives."""

    def __init__(self, predicate: Callable[[Frame], bool], description: str) -> None:
        self.predicate = predicate
        self.description = description


class WaitEvent:
    """Pause a call script until `event` is set."""

    def __init__(self, event: asyncio.Event, description: str) -> None:
        self.event = event
        self.description = description


class Do:
    """Invoke a callback against `CallTurns` at this point in a call script."""

    def __init__(self, action: Callable[[CallTurns], None]) -> None:
        self.action = action


ScriptStep = Frame | WaitFor | WaitEvent | Do


def wait_spoken(text: str) -> WaitFor:
    return WaitFor(
        lambda f: isinstance(f, SegmentTextFrame) and f.text == text,
        f"spoken {text!r}",
    )


def wait_frame(kind: type[Frame]) -> WaitFor:
    return WaitFor(lambda f: isinstance(f, kind), kind.__name__)


def wait_done() -> WaitFor:
    return WaitFor(
        lambda f: isinstance(f, RTVIServerMessageFrame) and f.data["type"] in ("done", "error"),
        "reply done",
    )


def wait_ended() -> WaitFor:
    return WaitFor(
        lambda f: isinstance(f, RTVIServerMessageFrame) and f.data["type"] == "ended",
        "call ended",
    )


def wait_event(event: asyncio.Event, description: str = "event") -> WaitEvent:
    return WaitEvent(event, description)


def cool(until: datetime) -> Do:
    return Do(lambda turns: turns.cooled(until))


async def run_script(turns: CallTurns, steps: Sequence[ScriptStep]) -> list[Frame]:
    """Run `steps` through `turns`, pausing at each `WaitFor` / `WaitEvent` / `SleepFrame`
    and executing each `Do` synchronously at that exact point in the stream."""
    received = Received()
    worker = PipelineWorker(
        Pipeline([turns, received]), cancel_on_idle_timeout=False, enable_rtvi=False
    )
    started = asyncio.Event()

    @worker.event_handler("on_pipeline_started")
    async def on_started(worker: PipelineWorker, frame: Frame) -> None:
        started.set()

    async def send() -> None:
        await asyncio.wait_for(started.wait(), timeout=1)
        cursor = 0
        for step in steps:
            if isinstance(step, WaitFor):
                try:
                    cursor = await asyncio.wait_for(
                        received.wait_until(step.predicate, cursor), timeout=5
                    )
                except TimeoutError:
                    raise TimeoutError(f"timed out waiting for {step.description}") from None
            elif isinstance(step, WaitEvent):
                try:
                    await asyncio.wait_for(step.event.wait(), timeout=5)
                except TimeoutError:
                    raise TimeoutError(f"timed out waiting for {step.description}") from None
            elif isinstance(step, Do):
                step.action(turns)
            elif isinstance(step, SleepFrame):
                await asyncio.sleep(step.sleep)
            else:
                await worker.queue_frame(step)
        await worker.queue_frame(EndFrame())

    runner = WorkerRunner(handle_sigint=False)
    await runner.add_workers(worker)
    await asyncio.gather(runner.run(), send())
    return received.frames


class Received(FrameProcessor):
    """The end of the pipeline: keeps what reaches it downstream, as `run_test` does, and
    notifies waiters on every frame and completed reply."""

    def __init__(self) -> None:
        super().__init__(enable_direct_mode=True)
        self.frames: list[Frame] = []
        self._replies_over = 0
        self._arrived = asyncio.Event()

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if direction is FrameDirection.DOWNSTREAM and not isinstance(frame, StartFrame | EndFrame):
            self.frames.append(frame)
            if isinstance(frame, RTVIServerMessageFrame) and frame.data["type"] in ("done", "error"):
                self._replies_over += 1
            self._arrived.set()
        await self.push_frame(frame, direction)

    async def replies_over(self, n: int) -> None:
        """Wait till `n` replies are over."""
        while self._replies_over < n:
            self._arrived.clear()
            await self._arrived.wait()

    async def wait_until(self, predicate: Callable[[Frame], bool], start: int) -> int:
        """Wait until a downstream frame at index >= `start` matches `predicate`."""
        index = start
        while True:
            while index < len(self.frames):
                if predicate(self.frames[index]):
                    return index + 1
                index += 1
            self._arrived.clear()
            await self._arrived.wait()


def spoken(text: str) -> TranscriptionFrame:
    return TranscriptionFrame(text, "user", "2026-09-25T00:00:00Z", finalized=True)


def typed(text: str) -> RTVIClientMessageFrame:
    return RTVIClientMessageFrame(msg_id="m1", type="user-text", data={"text": text})


def mute(muted: bool) -> RTVIClientMessageFrame:
    return RTVIClientMessageFrame(msg_id="m2", type="mute", data={"muted": muted})


async def test_each_reply_is_one_tts_response(mano_call: CallUnderTest):
    down = await mano_call.run_frames(FakeLLM(MANO_REPLY), [spoken("早上好")])

    voiced = [type(f) for f in down if not isinstance(f, RTVIServerMessageFrame)]
    assert voiced[0] is LLMFullResponseStartFrame and voiced[-1] is LLMFullResponseEndFrame
    assert LLMFullResponseStartFrame not in voiced[1:-1]


def to_tts(down: Sequence[Frame]) -> list[tuple]:
    """What went to TTS: the replies, and each segment's Japanese under its reply and
    segment, till it was complete."""
    sent: list[tuple] = []
    for frame in down:
        if isinstance(frame, SegmentTextFrame):
            sent.append((frame.text, frame.reply, frame.segment))
        elif isinstance(frame, SegmentCompleteFrame):
            sent.append(("complete", frame.reply, frame.segment))
        elif isinstance(frame, LLMFullResponseStartFrame):
            sent.append(("reply",))
        elif isinstance(frame, TextFrame) and not isinstance(frame, TranscriptionFrame):
            sent.append((frame.text,))  # Japanese sent under no segment
    return sent


async def test_each_segment_of_each_reply_goes_to_tts_under_its_numbers(
    mano_call: CallUnderTest,
):
    llm = FakeLLM(MANO_REPLY, ["<ja>うん。</ja><zh>嗯。</zh>"])

    down = await mano_call.run_frames(llm, one_by_one(spoken("早上好"), spoken("在吗")))

    assert to_tts(down) == [
        ("reply",),
        ("ほわっ、", 1, 0), ("おはようございます！", 1, 0), ("complete", 1, 0),
        ("今日も", 1, 1), ("complete", 1, 1),
        ("reply",),
        ("うん。", 2, 0), ("complete", 2, 0),
    ]


async def test_muted_call_sends_subtitles_but_nothing_to_voice(mano_call: CallUnderTest):
    llm = FakeLLM(["<ja>一</ja><zh>一</zh>"], ["<ja>二</ja><zh>二</zh>"], ["<ja>三</ja><zh>三</zh>"])

    spoken_text, messages = await mano_call.run(
        llm,
        one_by_one(spoken("第一句"), mute(False), spoken("第二句"), mute(True), typed("第三句")),
        muted=True,
    )

    assert spoken_text == ["二"]
    assert [m["message"]["ja"] for m in messages if m["type"] == "done"] == ["一", "二", "三"]


async def test_blank_input_is_ignored(mano_call: CallUnderTest):
    spoken_text, messages = await mano_call.run(FakeLLM(), [spoken("  "), typed("")])

    assert spoken_text == [] and messages == []
    assert await mano_call.record() == []


INTERRUPTED_REPLY = ["<ja>ほわっ</ja><zh>哇</zh>", "<ja>今日", HANG]
"""A reply with one complete segment, then half of the next, then nothing, ever."""
INTERRUPTIBLE: list[ScriptStep] = [
    wait_spoken("今日"), BotStartedSpeakingFrame(), wait_frame(BotStartedSpeakingFrame),
]
"""Once both the complete segment and the half-spoken second segment have reached TTS,
the character is speaking and can be interrupted."""
INTERRUPTING: list[ScriptStep] = [
    *INTERRUPTIBLE, InterruptionFrame(), wait_frame(InterruptionFrame),
]
"""The user interrupts her then."""


async def test_an_interruption_stops_the_reply_which_is_recorded_with_its_complete_segments(
    mano_call: CallUnderTest,
):
    memory = FakeBackgroundLLM()

    spoken_text, messages = await mano_call.run(
        FakeLLM(INTERRUPTED_REPLY), [spoken("早上好"), *INTERRUPTING],
        memory=memory, limits=CallLimits(turns=1),
    )
    messages = without_emotions(messages)

    assert spoken_text == ["ほわっ", "今日"]
    assert kinds(messages) == ["user", "done", "ended"]  # it counts as a turn
    assert (messages[-2]["message"]["ja"], messages[-2]["message"]["zh"]) == ("ほわっ", "哇")
    assert await mano_call.record() == [
        ("user", "早上好", None, None), ("character", None, "ほわっ", "哇"),
    ]
    assert len(memory.prompts) == 1


async def test_what_interrupts_the_character_is_taken_up_at_once(mano_call: CallUnderTest):
    llm = FakeLLM(INTERRUPTED_REPLY, MANO_REPLY)

    _, messages = await mano_call.run(
        llm, [spoken("早上好"), *INTERRUPTING, spoken("在吗")]
    )

    assert said(messages) == ["早上好", "在吗"]
    assert await mano_call.said() == ["早上好", None, "在吗", None]


async def test_what_is_typed_once_the_reply_can_be_interrupted_interrupts_the_character(
    mano_call: CallUnderTest,
):
    llm = FakeLLM(INTERRUPTED_REPLY, MANO_REPLY)

    down = await mano_call.run_frames(llm, [spoken("早上好"), *INTERRUPTIBLE, typed("在吗")])

    messages = [f.data for f in down if isinstance(f, RTVIServerMessageFrame)]
    assert said(messages) == ["早上好", "在吗"]
    assert InterruptionFrame in frame_types(down)
    assert await mano_call.record() == [
        ("user", "早上好", None, None), ("character", None, "ほわっ", "哇"),
        ("user", "在吗", None, None),
        ("character", None, "ほわっ、おはようございます！今日も", "哇，早上好！今天也"),
    ]


SLOW_REPLY = ["<ja>ほわっ", HANG]
"""A reply that starts speaking a first segment and pauses before completing it, so a
follow-on or hang-up can drop it deterministically once `wait_spoken("ほわっ")` fires."""


def said(messages: list[dict]) -> list[str]:
    return [m["text"] for m in messages if m["type"] == "user"]


def without_emotions(messages: list[dict]) -> list[dict]:
    """The messages but her emotions, judged in calls that remember, the judge model
    retrieval asks being at hand (see `test_call_emotions.py`)."""
    return [m for m in messages if m["type"] != "emotion"]


async def test_what_is_said_before_the_character_speaks_joins_the_turn(mano_call: CallUnderTest):
    llm = FakeLLM(SLOW_REPLY, MANO_REPLY)
    memory = FakeBackgroundLLM()

    _, messages = await mano_call.run(
        llm,
        [
            spoken("早上好"), wait_spoken("ほわっ"),
            InterruptionFrame(), wait_frame(InterruptionFrame), spoken("在吗"),
        ],
        memory=memory,
    )
    messages = without_emotions(messages)

    assert said(messages) == ["早上好", "早上好\n在吗"]
    assert kinds(messages) == ["user", "user", "done"]
    assert llm.prompts[-1][-1].content == "早上好\n在吗"
    assert await mano_call.record() == [
        ("user", "早上好\n在吗", None, None),
        ("character", None, "ほわっ、おはようございます！今日も", "哇，早上好！今天也"),
    ]
    assert len(memory.prompts) == 1  # the reply dropped was not written down


async def test_a_follow_on_drops_what_the_turn_was_looking_up_and_looks_up_the_whole_of_it(
    mano_call: CallUnderTest,
):
    llm, judge, embedder = FakeLLM(MANO_REPLY), FakeJudge(), FakeEmbedder()
    judge.hold("早上好")  # still judging, and looking up, when the user goes on
    embedder.hanging = {"早上好"}

    _, messages = await mano_call.run(
        llm,
        [
            spoken("早上好"),
            wait_event(judge.holding, "judge holding"),
            wait_event(embedder.hung, "embedder hanging"),
            InterruptionFrame(), wait_frame(InterruptionFrame), spoken("在吗"),
        ],
        memory=FakeBackgroundLLM(), retrieval_judge=judge, embedder=embedder,
    )

    assert said(without_emotions(messages)) == ["早上好", "早上好\n在吗"]
    assert [text for _, text in judge.asked] == ["早上好", "早上好\n在吗"]
    assert embedder.abandoned == ["早上好"]
    assert embedder.queries == ["早上好", "早上好\n在吗"]
    assert len(llm.prompts) == 1
    assert await mano_call.said() == ["早上好\n在吗", None]


async def test_a_turn_with_a_follow_on_changes_affinity_as_the_whole_of_it_is_judged(
    mano_call: CallUnderTest, settings: Settings
):
    llm = FakeLLM(SLOW_REPLY, MANO_REPLY)

    _, messages = await mano_call.run(
        llm,
        [
            spoken("早上好"), wait_spoken("ほわっ"),
            InterruptionFrame(), wait_frame(InterruptionFrame), spoken("在吗"),
        ],
        affinity=[level(0), level(4)],
    )
    done = without_emotions(messages)[-1]

    # The reply dropped, what it was judged at went with it: she knew it as it was judged.
    assert value(settings.database_path) == pytest.approx(50.2)
    assert FEELINGS[0] in about_now(llm, 0)
    assert FEELINGS[4] in about_now(llm, 1)
    assert FEELINGS[0] not in about_now(llm, 1)
    assert done["message"]["affinity"] == {
        "up": True, "tier_changed": False, "tier": "trust", "cooldown": False, "thawed": False
    }
    assert done["affinity"] == {"tier": "trust", "cooldown_until": None}


async def test_what_is_typed_before_the_character_speaks_joins_the_turn_and_stops_its_voice(
    mano_call: CallUnderTest,
):
    """The turn is replied to afresh, going to TTS under a number of its own."""
    llm = FakeLLM(SLOW_REPLY, ["<ja>うん。</ja><zh>嗯。</zh>"])

    down = await mano_call.run_frames(
        llm, [spoken("早上好"), wait_spoken("ほわっ"), typed("在吗")]
    )

    messages = [f.data for f in down if isinstance(f, RTVIServerMessageFrame)]
    assert said(messages) == ["早上好", "早上好\n在吗"]
    assert await mano_call.said() == ["早上好\n在吗", None]
    voiced = [type(f) for f in down if not isinstance(f, RTVIServerMessageFrame)]
    assert voiced[:4] == [
        LLMFullResponseStartFrame, SegmentTextFrame, LLMFullResponseEndFrame, InterruptionFrame
    ]
    assert to_tts(down) == [
        ("reply",), ("ほわっ", 1, 0), ("reply",), ("うん。", 2, 0), ("complete", 2, 0)
    ]


async def test_a_follow_on_never_transcribed_has_the_turn_replied_to_again_in_time(
    mano_call: CallUnderTest,
):
    llm = FakeLLM(SLOW_REPLY, MANO_REPLY)

    _, messages = await mano_call.run(
        llm,
        [spoken("早上好"), wait_spoken("ほわっ"), InterruptionFrame(), wait_frame(InterruptionFrame)],
        follow_on_timeout=0.3,
    )

    assert said(messages) == ["早上好", "早上好"]
    assert await mano_call.said() == ["早上好", None]


def frame_types(frames: Sequence[Frame]) -> list[type[Frame]]:
    return [type(f) for f in frames]


def kinds(messages: list[dict]) -> list[str]:
    return [m["type"] for m in messages if m["type"] != "delta"]


async def test_call_hangs_up_after_its_last_allowed_turn(mano_call: CallUnderTest):
    llm = FakeLLM(MANO_REPLY, MANO_REPLY)

    spoken_text, messages = await mano_call.run(
        llm,
        one_by_one(spoken("早上好"), typed("在吗"), spoken("还在吗")),
        limits=CallLimits(turns=2),
    )

    assert kinds(messages) == ["user", "done", "user", "done", "ended"]
    assert messages[-1]["reason"] == "turn_limit"
    assert "".join(spoken_text).count("ほわっ") == 2  # the last reply is still voiced
    assert len(await mano_call.record()) == 4


async def test_call_hangs_up_when_time_is_up_once_the_reply_in_progress_is_done(
    mano_call: CallUnderTest,
):
    llm = FakeLLM(MANO_REPLY, delay=0.2)

    _, messages = await mano_call.run(
        llm,
        [spoken("早上好"), SleepFrame(0.6), spoken("还在吗")],
        limits=CallLimits(duration=timedelta(seconds=0.1)),
    )

    assert kinds(messages) == ["user", "done", "ended"]
    assert messages[-1]["reason"] == "duration_limit"
    assert len(await mano_call.record()) == 2


async def test_a_calls_time_is_counted_from_when_it_connects(mano_call: CallUnderTest):
    """The call screen counts from 接通 (GLOSSARY.md), so the time limit does too."""
    _, messages = await mano_call.run(
        FakeLLM(MANO_REPLY),
        [SleepFrame(0.3), spoken("早上好")],
        limits=CallLimits(duration=timedelta(seconds=0.1)),
        connected=False,
    )

    assert kinds(messages) == ["user", "done"]  # never connected, so time never ran out


async def test_turns_that_fail_or_are_rejected_do_not_count_and_the_call_goes_on(
    mano_call: CallUnderTest,
):
    llm = FakeLLM(["  "], MANO_REPLY)  # the first reply is empty
    too_long = "啊" * (MAX_INPUT_LENGTH + 1)

    spoken_text, messages = await mano_call.run(
        llm,
        one_by_one(spoken(too_long), typed(too_long), spoken("在吗"), spoken("在吗？")),
        limits=CallLimits(turns=1),
    )

    assert kinds(messages) == ["user", "error"] * 3 + ["user", "done", "ended"]
    assert messages[-1]["reason"] == "turn_limit"
    assert len(llm.prompts) == 2  # what was too long never reached the model
    assert "".join(spoken_text).count("ほわっ") == 1
    assert await mano_call.said() == ["在吗？", None]

