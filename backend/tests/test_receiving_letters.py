"""Receiving letters (GLOSSARY.md「信」「没读过的信」): a letter popped up is marked so, on every
device, so it does not pop up again; the user deletes a letter, its voice with it; each line of
the conversation list says whether she has a letter the user has not read. Another's letter,
or none, is none (404).

Letters are written as `test_letters.py` writes them: her affinity first reaching close, the
letters' tick taken by hand (`Letters.run_due`)."""

import sqlite3

import httpx

from eidolon.config import Settings
from tests.conftest import ClientFactory
from tests.fakes import FakeFishAudio
from tests.test_concurrent_calls import another_user
from tests.test_letters import close_with_mano, letters, read, written
from tests.test_letters import settings  # noqa: F401
from tests.test_reach_outs import backend_of
from tests.test_read_aloud import faked
from tests.test_text_turn import start_conversation


async def unread(client: httpx.AsyncClient) -> dict[str, bool]:
    """Whose line in the conversation list has a letter the user has not read."""
    res = await client.get("/api/conversations/latest")
    assert res.status_code == 200, res.text
    return {s["character_id"]: s["unread_letter"] for s in res.json()}


async def test_a_letter_popped_up_is_so_on_every_device_and_another_cannot_mark_it(
    make_client: ClientFactory, settings: Settings
):
    client, _, _, _ = await close_with_mano(make_client, settings, written())
    await backend_of(client).letters.run_due()
    [letter] = await letters(client)
    someone = another_user(client, "someone")

    by_them = await someone.put(f"/api/letters/{letter['id']}/popped")
    none = await client.put(f"/api/letters/{letter['id'] + 1}/popped")
    after_them = await letters(client)
    popped = await client.put(f"/api/letters/{letter['id']}/popped")
    again = await client.put(f"/api/letters/{letter['id']}/popped")

    assert (by_them.status_code, none.status_code) == (404, 404)
    assert [each["popped"] for each in after_them] == [False]
    assert (popped.status_code, again.status_code) == (204, 204)
    [shown] = await letters(another_user(client, "producer"))
    assert (shown["popped"], shown["read"]) == (True, False)


async def test_the_user_deletes_a_letter_unread_and_its_voice_and_none_but_theirs(
    make_client: ClientFactory, settings: Settings
):
    client, _, _, _ = await close_with_mano(
        make_client, settings, written(), fish_transport=faked(FakeFishAudio())
    )
    await backend_of(client).letters.run_due()
    [letter] = await letters(client)
    voice = (await read(client, letter["id"])).json()["voice"]
    someone = another_user(client, "someone")

    by_them = await someone.delete(f"/api/letters/{letter['id']}")
    still = await letters(client)
    deleted = await client.delete(f"/api/letters/{letter['id']}")
    again = await client.delete(f"/api/letters/{letter['id']}")

    assert by_them.status_code == 404
    assert [each["id"] for each in still] == [letter["id"]]
    assert (deleted.status_code, again.status_code) == (204, 404)
    assert await letters(client) == []
    assert await unread(client) == {"mano": False}
    assert (await read(client, letter["id"])).status_code == 404
    assert (await client.get(voice[0])).status_code == 404
    with sqlite3.connect(settings.database_path) as db:
        assert db.execute("SELECT COUNT(*) FROM letter_voices").fetchone() == (0,)


async def test_her_line_in_the_conversation_list_has_an_unread_letter_till_it_is_read(
    make_client: ClientFactory, settings: Settings
):
    client, _, _, _ = await close_with_mano(make_client, settings, written())
    await start_conversation(client, "kogane")
    before = await unread(client)

    await backend_of(client).letters.run_due()
    [letter] = await letters(client)
    written_one = await unread(client)
    others = await unread(another_user(client, "someone"))
    await client.put(f"/api/letters/{letter['id']}/popped")
    popped = await unread(client)
    await client.put(f"/api/letters/{letter['id']}/read")

    assert before == {"mano": False, "kogane": False}
    assert written_one == {"mano": True, "kogane": False}
    assert others == {}
    assert popped == {"mano": True, "kogane": False}
    assert await unread(client) == {"mano": False, "kogane": False}

