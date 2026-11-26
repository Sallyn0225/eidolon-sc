"""Her emotion in each segment of her replies during a call, judged by the deployer's Jev
(spec「情绪判断」), at the Pipecat stage that wraps the conversation engine: what the
browser is sent (`emotion` server messages) and what Jev is asked. Jev answers from a
`FakeJudge`'s script; how the real one is asked is in `test_emotion_judge.py`."""

import pytest
from pipecat.tests.utils import SleepFrame

from eidolon.config import EmotionSettings
from tests.fakes import HANG, FakeJudge, FakeLLM, feeling
from tests.test_call_turns import (
    INTERRUPTED_REPLY,
    INTERRUPTING,
    MANO_REPLY,
    SLOW_REPLY,
    CallUnderTest,
    mano_call,  # noqa: F401  # the fixture
    spoken,
    typed,
    wait_done,
    wait_spoken,
)

SETTLE = SleepFrame(0.2)
"""Time for Jev's last answers to come back before the call ends."""


def emotions(messages: list[dict]) -> list[tuple]:
    return [
        (m["reply"], m["segment"], m["emotion"], m["nod"]) for m in messages if m["type"] == "emotion"
    ]


async def test_each_segment_of_each_reply_gets_its_emotion(mano_call: CallUnderTest):
    llm = FakeLLM(MANO_REPLY, ["<ja>うん。</ja><zh>嗯。</zh>"])
    judge = FakeJudge(emotions=[feeling("happy"), feeling("shy"), feeling("thinking", nod="yes")])

    _, messages = await mano_call.run(
        llm, [spoken("早上好"), wait_done(), spoken("在吗"), wait_done(), SETTLE], judge=judge
    )

    assert emotions(messages) == [
        (1, 0, "happy", None), (1, 1, "shy", None), (2, 0, "thinking", "yes")
    ]


async def test_an_answer_jev_is_unsure_of_is_calm_without_a_nod(mano_call: CallUnderTest):
    judge = FakeJudge(
        emotions=[feeling("happy", 0.45, nod="no"), feeling("sad", 0.5, nod="yes", nod_probability=0.4)]
    )

    _, messages = await mano_call.run(
        FakeLLM(MANO_REPLY), [spoken("早上好"), wait_done(), SETTLE], judge=judge,
        emotion=EmotionSettings(min_probability=0.5),
    )

    assert emotions(messages) == [(1, 0, "calm", "no"), (1, 1, "sad", None)]


@pytest.mark.parametrize("answer", [None, HANG], ids=["failed", "too slow"])
async def test_a_segment_jev_cannot_judge_in_time_gets_no_emotion(
    mano_call: CallUnderTest, answer: object
):
    judge = FakeJudge(emotions=[answer, feeling("shy")])

    _, messages = await mano_call.run(
        FakeLLM(MANO_REPLY), [spoken("早上好"), wait_done(), SleepFrame(0.3)], judge=judge,
        emotion=EmotionSettings(timeout=0.2),
    )

    assert emotions(messages) == [(1, 1, "shy", None)]
    assert len(judge.segments) == 2  # not asked again


async def test_text_only_replies_are_judged_all_the_same(mano_call: CallUnderTest):
    judge = FakeJudge(emotions=[feeling("happy"), feeling("surprised")])

    spoken_text, messages = await mano_call.run(
        FakeLLM(MANO_REPLY), [spoken("早上好"), wait_done(), SETTLE], judge=judge, muted=True
    )

    assert spoken_text == []
    assert emotions(messages) == [(1, 0, "happy", None), (1, 1, "surprised", None)]


async def test_jev_reads_the_segment_with_its_cues_after_those_before_it(mano_call: CallUnderTest):
    llm = FakeLLM(
        ["<ja>[shyly] ほわっ、</ja><zh>哇，</zh><ja>ありがとう", "ございます！</ja><zh>谢谢！</zh>"]
    )
    judge = FakeJudge()

    await mano_call.run(llm, [spoken("你今天很可爱"), wait_done(), SETTLE], judge=judge)

    first, second = judge.segments
    assert (first.character, first.user_said) == ("櫻木真乃", "你今天很可爱")
    assert (first.before, first.ja, first.zh) == ("（这是回复的第一段）", "[shyly]ほわっ、", "哇，")
    assert second.before == ["[shyly]ほわっ、（哇，）"]
    assert (second.ja, second.zh) == ("ありがとうございます！", "谢谢！")


async def test_segments_left_incomplete_by_an_interruption_are_not_judged(
    mano_call: CallUnderTest,
):
    judge = FakeJudge(emotions=[feeling("happy")])

    _, messages = await mano_call.run(
        FakeLLM(INTERRUPTED_REPLY), [spoken("早上好"), *INTERRUPTING, wait_done(), SETTLE],
        judge=judge,
    )

    assert emotions(messages) == [(1, 0, "happy", None)]
    assert len(judge.segments) == 1


async def test_a_reply_dropped_for_a_follow_on_is_judged_no_further_and_numbers_stay_with_replies(
    mano_call: CallUnderTest,
):
    """What the user said in a call, and the emotions of a reply's segments, carry the
    number of the reply they are of."""
    llm = FakeLLM(SLOW_REPLY, ["<ja>うん。</ja><zh>嗯。</zh>"], ["<ja>ええ。</ja><zh>嗯。</zh>"])
    judge = FakeJudge(emotions=[feeling("happy"), feeling("sad")])

    _, messages = await mano_call.run(
        llm,
        [
            spoken("早上好"), wait_spoken("ほわっ"), typed("在吗"),
            wait_done(), spoken("好"), wait_done(), SETTLE,
        ],
        judge=judge,
    )

    # The first reply had no complete segment when it was dropped.
    assert emotions(messages) == [(2, 0, "happy", None), (3, 0, "sad", None)]
    assert [s.user_said for s in judge.segments] == ["早上好\n在吗", "好"]
    assert [(m["text"], m["reply"]) for m in messages if m["type"] == "user"] == [
        ("早上好", 1), ("早上好\n在吗", 2), ("好", 3)
    ]
