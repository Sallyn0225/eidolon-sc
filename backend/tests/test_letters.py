"""Letters (GLOSSARY.md「信」): what she writes to the producer on an occasion. This first
slice is the occasions the achievements already tell: her affinity first reaching close, first
reaching intimate, and her being complete. Each is kept, as it happens, in the transaction
that tells it, as a letter to be written; at the next tick it is written, on the deployer's
chat model, whoever's LLM the user brings, and the user reads it in their letters.

Driven through the backend's external API, the letters' ticks taken by hand
(`Letters.run_due`), the clock moved, and her affinity set in the database directly."""

import json
import sqlite3
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest

from eidolon.config import Settings
from eidolon.letter_prompt import SHORTER, WRITE
from eidolon.llm import LLMError
from tests.conftest import KOGANE_SHEET, MANO_SHEET, CharacterConfig, ClientFactory
from tests.fakes import (
    DEPLOYER_KEY,
    FAKE_JUDGE,
    FakeClock,
    FakeLLM,
    FakeIdentityProvider,
    FakeLLMService,
    FakeServiceClients,
    level,
)
from tests.test_achievements import goals, hers, turns, unlocked, with_goals
from tests.test_achievements_launch import History, history  # noqa: F401
from tests.test_activity_records import dashboard
from tests.test_admin_users import ADMIN, admin_beside, find
from tests.test_concurrent_calls import another_user
from tests.test_delete_account import DELETE
from tests.test_affinity import keep
from tests.test_affinity_prompt import FONDNESS
from tests.test_gift_giving import CAKE, catalog, draw_them, given, holding  # noqa: F401
from tests.test_own_llm import LLM as OWN_LLM
from tests.test_reach_outs import backend_of, records, remember
from tests.test_text_turn import send_turn, start_conversation
from tests.test_user_limits import set_limits

REPLY = ["<ja>はい</ja><zh>好的</zh>"]
LETTERS = "/api/admin/config/letters"
LETTER = {
    "salutation": "[softly] プロデューサーさんへ",
    "paragraphs": [
        {"ja": "[smiling] いつもありがとうございます。", "zh": "[smiling] 一直以来谢谢你。"},
        {"ja": "これからもよろしくお願いします。", "zh": "今后也请多关照。"},
    ],
    "sources": ["对话记录"],
}


def written(letter: dict = LETTER) -> list[str]:
    """The chat model's reply writing `letter`, as it writes one: a JSON object."""
    return [json.dumps(letter, ensure_ascii=False)]


@pytest.fixture
def settings(settings: Settings) -> Settings:
    """With the judge model, affinity and gifts, and letters on in `.env`."""
    return replace(settings, judge=FAKE_JUDGE, affinity_and_gifts=True, letters=True)


def judged(*judgings) -> FakeServiceClients:
    clients = FakeServiceClients()
    clients.judge.judgings = list(judgings)
    return clients


async def letters(client: httpx.AsyncClient) -> list[dict]:
    res = await client.get("/api/letters")
    assert res.status_code == 200, res.text
    return res.json()["letters"]


async def read(client: httpx.AsyncClient, letter_id: int) -> httpx.Response:
    return await client.get(f"/api/letters/{letter_id}")


async def close_with_mano(
    make_client: ClientFactory,
    settings: Settings,
    *replies: list[str] | LLMError,
    **services: Any,
) -> tuple[httpx.AsyncClient, FakeLLM, FakeClock, str]:
    """A client whose user's affinity with Mano has just first reached close, a turn after
    their first, in the conversation; her chat model then replying `replies`, and the judge
    model judging two turns more as it did those. Any keyword goes on to `make_client`."""
    clock = FakeClock()
    llm = FakeLLM(REPLY, REPLY, *replies)
    client = make_client(
        llm, clock=clock, clients=judged(*[level(4)] * 4), settings=settings, **services
    )
    conversation = await start_conversation(client)
    await turns(client, conversation, 1)
    keep(settings.database_path, "producer", 64.9, clock.now)
    done = await turns(client, conversation, 1)
    assert done["affinity"]["tier"] == "close"
    return client, llm, clock, conversation


async def test_first_reaching_close_she_writes_a_letter_the_user_reads(
    make_client: ClientFactory, settings: Settings, github: FakeIdentityProvider
):
    """Recorded in an activity record of its own, which no count of turns takes in."""
    on = replace(settings, admins=frozenset({ADMIN}))
    client, _, _, _ = await close_with_mano(make_client, on, written())
    before = await letters(client)

    await backend_of(client).letters.run_due()
    [listed] = await letters(client)
    res = await read(client, listed["id"])
    async with admin_beside(client, github) as admin:
        board = await dashboard(admin)

    assert before == []
    assert listed == {
        "id": listed["id"],
        "character_id": "mano",
        "occasions": ["close"],
        "day": "2026-09-25",  # in Shanghai, the producer's time zone unset
        "read": False,
        "popped": False,
    }
    assert res.status_code == 200, res.text
    assert res.json() == {
        "id": listed["id"],
        "character_id": "mano",
        "occasions": ["close"],
        "day": "2026-09-25",
        "salutation": "プロデューサーさんへ",
        "paragraphs": [
            {"ja": "いつもありがとうございます。", "zh": "一直以来谢谢你。"},
            {"ja": "これからもよろしくお願いします。", "zh": "今后也请多关照。"},
        ],
        "signature": {"image": None, "text": "櫻木真乃"},
        "voice": [f"/api/letters/{listed['id']}/voice/{block}" for block in range(3)],
        "music": None,
    }
    assert [r for r in records(settings.database_path) if r[0] == "letter"] == [
        ("letter", "mano", "success", 0)
    ]
    assert board["turns"]["total"] == 2
    assert sum(point["turns"] + point["calls"] for point in board["trend"]) == 2


FACTS = "# 经历\n真乃和制作人一起去看过鸽子。"


@pytest.fixture
def characters(tmp_path: Path) -> CharacterConfig:
    """Mano, with her facts, and Kogane."""
    return (
        CharacterConfig(tmp_path / "characters")
        .add("mano", "櫻木真乃", MANO_SHEET, birthday="04-25", facts=FACTS)
        .add("kogane", "月岡恋鐘", KOGANE_SHEET, birthday="02-25")
    )


async def test_she_writes_on_the_deployers_model_with_what_there_is_between_them(
    make_client: ClientFactory, settings: Settings, own_llm: FakeLLMService
):
    """Her sheet, birthday and facts; the producer; how she speaks in close; her own
    memories, the latest 30 still holding; their latest 60 messages across conversations;
    the rules, on her occasion and the day. Whatever LLM the user brings."""
    clock = FakeClock()
    llm = FakeLLM(written())
    own_llm.llm = FakeLLM(REPLY, REPLY)
    clients = judged(level(4), level(4))
    clients.llm = llm
    client = make_client(llm, clock=clock, clients=clients)
    res = await client.put("/api/profile", json={"form_of_address": "P君"})
    assert res.status_code == 200, res.text
    database = settings.database_path
    for i in range(31):
        remember(database, f"制作人说过第{i}件事", clock.now - timedelta(days=40 - i))
    remember(database, "制作人喜欢长崎", clock.now, told="kogane")
    remember(database, "制作人改主意了", clock.now, superseded_by=1)
    older = await start_conversation(client)
    with sqlite3.connect(database) as db:
        db.executemany(
            "INSERT INTO messages (conversation_id, role, text, ja, zh, segments, created_at)"
            " VALUES (?, 'user', ?, NULL, NULL, NULL, ?)",
            [(older, f"旧话{i}", (clock.now - timedelta(days=30, minutes=60 - i)).isoformat())
             for i in range(60)],
        )
    clock.advance(days=1)
    conversation = await start_conversation(client)
    await send_turn(client, conversation, "今天也去看鸽子吧", own_llm=OWN_LLM)
    keep(database, "producer", 64.9, clock.now)
    await send_turn(client, conversation, "谢谢你", own_llm=OWN_LLM)
    with sqlite3.connect(database) as db:  # as the store writes the time as it is
        db.execute(
            "UPDATE messages SET created_at = ? WHERE conversation_id = ?",
            (clock.now.isoformat(), conversation),
        )

    await backend_of(client).letters.run_due()

    assert llm.keys == [DEPLOYER_KEY]
    assert clients.efforts == [settings.chat_llm.reasoning_effort]  # as text turns
    [prompt] = llm.prompts
    assert [m.role for m in prompt] == ["system", "system", "system", "user"]
    assert prompt[-1].content == WRITE
    opening, producer, context = (m.content for m in prompt[:3])
    assert MANO_SHEET in opening and "4月25日" in opening and "一起去看过鸽子" in opening
    assert "「P君」" in producer
    assert FONDNESS["close"] in context
    memories = [line for line in context.splitlines() if line.startswith("- 记忆：")]
    assert memories == [f"- 记忆：制作人说过第{i}件事" for i in range(1, 31)]
    said = [line for line in context.splitlines() if line.startswith("[")]
    assert len(said) == 60
    assert said[-4:] == [
        "[2026年9月26日] 制作人：今天也去看鸽子吧",
        "[2026年9月26日] 你：はい",
        "[2026年9月26日] 制作人：谢谢你",
        "[2026年9月26日] 你：はい",
    ]
    assert said[0] == "[2026年8月26日] 制作人：旧话4"
    assert "你们第一次说话是 2026年8月26日；一共聊过 62 个回合" in context
    assert "第一次比平时更近了一步" in context and "今天是 2026年9月26日。" in context


async def test_her_affinity_falling_back_and_reaching_close_again_is_no_occasion_again(
    make_client: ClientFactory, settings: Settings
):
    clock = FakeClock()
    llm = FakeLLM(REPLY, REPLY, written(), REPLY, REPLY)
    client = make_client(llm, clock=clock, clients=judged(*[level(4)] * 4))
    conversation = await start_conversation(client)
    await turns(client, conversation, 1)
    database = settings.database_path
    keep(database, "producer", 64.9, clock.now)
    await turns(client, conversation, 1)
    await backend_of(client).letters.run_due()
    clock.advance(days=2)
    keep(database, "producer", 50, clock.now)
    await turns(client, conversation, 1)
    keep(database, "producer", 64.9, clock.now)

    again = await turns(client, conversation, 1)
    await backend_of(client).letters.run_due()

    assert again["affinity"]["tier"] == "close"
    assert [each["occasions"] for each in await letters(client)] == [["close"]]


async def test_reaching_intimate_at_once_is_one_letter_on_both(
    make_client: ClientFactory, settings: Settings
):
    clock = FakeClock()
    llm = FakeLLM(REPLY, REPLY, written())
    client = make_client(llm, clock=clock, clients=judged(level(4), level(4)))
    conversation = await start_conversation(client)
    await turns(client, conversation, 1)
    keep(settings.database_path, "producer", 84.9, clock.now)
    await turns(client, conversation, 1)

    await backend_of(client).letters.run_due()

    [letter] = await letters(client)
    assert letter["occasions"] == ["intimate", "close"]
    context = llm.prompts[-1][2].content
    assert FONDNESS["intimate"] in context
    assert "这次有几件事在同一天" in context and "非常特别、可以依靠的人" in context


async def test_she_complete_writes_a_letter(
    make_client: ClientFactory, settings: Settings, monkeypatch: pytest.MonkeyPatch
):
    clock = FakeClock()
    llm = FakeLLM(REPLY, written())
    client = holding(make_client, clock, CAKE, llm=llm)
    await draw_them(client, clock, 1)
    with_goals(monkeypatch, "PER_CHARACTER", turns=goals(1), gifts=goals(1))
    conversation = await start_conversation(client)
    await turns(client, conversation, 1)

    gift = await given(client, "cake")
    await backend_of(client).letters.run_due()

    assert gift["rewarded"]["completed"] == [{"character_id": "mano", "reset_cards": 1}]
    [letter] = await letters(client)
    assert letter["occasions"] == ["complete"]
    assert "回头看看这一路" in llm.prompts[-1][2].content


async def test_while_off_she_writes_none_nor_makes_up_for_it_once_on(
    make_client: ClientFactory, settings: Settings, github: FakeIdentityProvider
):
    off = replace(settings, letters=False, admins=frozenset({ADMIN}))
    client, llm, _, _ = await close_with_mano(make_client, off, written())
    await backend_of(client).letters.run_due()
    account_off = (await client.get("/api/account")).json()

    async with admin_beside(client, github) as admin:
        res = await admin.put(LETTERS, json={"enabled": True})
    await backend_of(client).letters.run_due()

    assert res.status_code == 200, res.text
    assert await letters(client) == []
    assert len(llm.prompts) == 2  # the two turns
    assert account_off["letters"] is False
    assert (await client.get("/api/account")).json()["letters"] is True


@pytest.mark.parametrize("why", ["cold", "cooldown", "banned", "no turns"])
async def test_she_does_not_write_and_what_was_to_be_is_passed_over(
    make_client: ClientFactory, settings: Settings, github: FakeIdentityProvider, why: str
):
    on = replace(settings, admins=frozenset({ADMIN}))
    client, _, clock, _ = await close_with_mano(make_client, on, written(), written())
    database = settings.database_path
    if why in ("cold", "distant", "cooldown"):
        keep(database, "producer", {"cold": 15, "cooldown": 5}[why], clock.now,
             cooling=why == "cooldown")
    elif why == "banned":
        with sqlite3.connect(database) as db:
            db.execute("UPDATE users SET banned_at = ? WHERE name = 'producer'",
                       (clock.now.isoformat(),))
    else:
        async with admin_beside(client, github) as admin:
            await set_limits(admin, (await find(admin, "producer"))["id"], turns_per_hour=0)

    await backend_of(client).letters.run_due()
    keep(database, "producer", 70, clock.now)
    with sqlite3.connect(database) as db:
        db.execute("UPDATE users SET banned_at = NULL")
        db.execute("DELETE FROM user_limits")
    await backend_of(client).letters.run_due()

    assert await letters(client) == []


async def test_a_second_occasion_the_day_she_wrote_one_is_put_off_to_the_next_day(
    make_client: ClientFactory, settings: Settings
):
    """Written with the letter she wrote before, not to be repeated."""
    client, llm, clock, conversation = await close_with_mano(
        make_client, settings, written(), REPLY, written()
    )
    letters_of = backend_of(client).letters
    await letters_of.run_due()
    keep(settings.database_path, "producer", 84.9, clock.now)
    await turns(client, conversation, 1)  # intimate, the same day

    await letters_of.run_due()
    clock.advance(hours=3, minutes=59)  # 23:59 in Shanghai
    await letters_of.run_due()
    that_day = await letters(client)
    clock.advance(minutes=1)
    await letters_of.run_due()

    assert [(each["occasions"], each["day"]) for each in that_day] == [
        (["close"], "2026-09-25")
    ]
    assert [(each["occasions"], each["day"]) for each in await letters(client)] == [
        (["intimate"], "2026-09-26"), (["close"], "2026-09-25"),
    ]
    context = llm.prompts[-1][2].content
    earlier = context[context.index("# 你以前写给这位制作人的信"):context.index("# 写信")]
    assert "不要重复以前写过的事" in earlier
    assert "## 2026年9月25日（第一次和他更近了一步）\nプロデューサーさんへ\nいつもありがとうございます。" in earlier
    assert "[smiling]" not in earlier


def body_of(length: int) -> dict:
    """A letter whose body is `length` characters long, but for a delivery cue and spaces."""
    half = length // 2
    return LETTER | {"paragraphs": [
        {"ja": "[softly] " + "あ" * half, "zh": "啊"},
        {"ja": "い " * (length - half), "zh": "咿"},
    ]}


async def test_a_body_too_long_she_writes_once_more_shorter_kept_as_it_is_if_still(
    make_client: ClientFactory, settings: Settings
):
    client, llm, clock, conversation = await close_with_mano(
        make_client, settings, written(body_of(330)),
        REPLY, written(body_of(331)), written(body_of(331)),
    )
    letters_of = backend_of(client).letters
    await letters_of.run_due()
    clock.advance(days=1)
    keep(settings.database_path, "producer", 84.9, clock.now)
    await turns(client, conversation, 1)

    await letters_of.run_due()

    intimate, _ = await letters(client)
    assert len(llm.prompts) == 2 + 1 + 1 + 2
    rewrite = llm.prompts[-1]
    assert [m.role for m in rewrite[-3:]] == ["user", "assistant", "user"]
    assert rewrite[-1].content == SHORTER
    assert rewrite[-2].content == written(body_of(331))[0]
    got = (await read(client, intimate["id"])).json()
    assert len("".join("".join(p["ja"].split()) for p in got["paragraphs"])) == 331


async def test_a_letter_rewritten_shorter_is_kept_shorter(
    make_client: ClientFactory, settings: Settings
):
    client, _, _, _ = await close_with_mano(
        make_client, settings, written(body_of(400)), written(body_of(200)),
    )

    await backend_of(client).letters.run_due()

    [letter] = await letters(client)
    got = (await read(client, letter["id"])).json()
    assert len("".join("".join(p["ja"].split()) for p in got["paragraphs"])) == 200


@pytest.mark.parametrize("fails", ["no letter", "the model"])
async def test_one_she_writes_no_letter_in_is_recorded_failed_and_tried_again_later(
    make_client: ClientFactory, settings: Settings, fails: str
):
    reply = ["我写不出来。"] if fails == "no letter" else LLMError("模型返回 503: overloaded")
    client, llm, clock, _ = await close_with_mano(make_client, settings, reply, written())
    letters_of = backend_of(client).letters

    await letters_of.run_due()
    clock.advance(minutes=9, seconds=59)
    await letters_of.run_due()
    before = await letters(client)
    clock.advance(seconds=1)
    await letters_of.run_due()

    assert before == []
    assert [each["occasions"] for each in await letters(client)] == [["close"]]
    assert len(llm.prompts) == 2 + 2
    assert [r for r in records(settings.database_path) if r[0] == "letter"] == [
        ("letter", "mano", "failed", 0), ("letter", "mano", "success", 0),
    ]


async def test_one_failing_each_time_is_tried_three_times_more_then_given_up(
    make_client: ClientFactory, settings: Settings
):
    """Once more after 10 minutes, after 30, and after 60, each failure recorded."""
    fails = LLMError("模型返回 503: overloaded")
    client, llm, clock, _ = await close_with_mano(
        make_client, settings, *[fails] * 4, written()
    )
    letters_of = backend_of(client).letters

    await letters_of.run_due()
    for minutes in (10, 30, 60, 24 * 60):
        clock.advance(minutes=minutes)
        await letters_of.run_due()

    assert await letters(client) == []
    assert len(llm.prompts) == 2 + 4
    assert [r for r in records(settings.database_path) if r[0] == "letter"] == [
        ("letter", "mano", "failed", 0)
    ] * 4


async def test_the_users_letters_are_theirs_alone_and_read_once_read_on_every_device(
    make_client: ClientFactory, settings: Settings
):
    client, _, _, _ = await close_with_mano(make_client, settings, written())
    await backend_of(client).letters.run_due()
    [letter] = await letters(client)
    someone = another_user(client, "someone")
    other_device = another_user(client, "producer")

    theirs = await read(someone, letter["id"])
    marked_by_them = await someone.put(f"/api/letters/{letter['id']}/read")
    none = await read(client, letter["id"] + 1)
    marked = await client.put(f"/api/letters/{letter['id']}/read")

    assert (theirs.status_code, marked_by_them.status_code, none.status_code) == (404, 404, 404)
    assert await letters(someone) == []
    assert marked.status_code == 204
    assert [each["read"] for each in await letters(other_device)] == [True]


async def test_turned_off_the_letters_written_stay_to_be_read(
    make_client: ClientFactory, settings: Settings, github: FakeIdentityProvider
):
    on = replace(settings, admins=frozenset({ADMIN}))
    client, _, _, _ = await close_with_mano(make_client, on, written())
    await backend_of(client).letters.run_due()

    async with admin_beside(client, github) as admin:
        res = await admin.put(LETTERS, json={"enabled": False})
    [letter] = await letters(client)

    assert res.status_code == 200, res.text
    assert (await read(client, letter["id"])).status_code == 200


async def test_deleting_the_user_deletes_their_letters(
    make_client: ClientFactory, settings: Settings
):
    client, _, _, _ = await close_with_mano(make_client, settings, written())
    await backend_of(client).letters.run_due()

    res = await client.post("/api/account/delete", json=DELETE)

    assert res.status_code == 204, res.text
    with sqlite3.connect(settings.database_path) as db:
        assert db.execute("SELECT COUNT(*) FROM letters").fetchone() == (0,)


async def test_what_was_reached_before_the_achievements_launched_is_no_occasion(
    make_client: ClientFactory, history: History
):
    history.turns(history.conversation(), 1, tier="intimate")

    client = history.launch()
    await backend_of(client).letters.run_due()

    assert unlocked(await hers(client), "tier") == [1, 2]
    assert await letters(client) == []
