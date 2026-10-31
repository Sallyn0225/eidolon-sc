"""A letter read aloud (GLOSSARY.md「信」): once written, its salutation and each paragraph
are voiced in her voice, a request each, on the deployer's speech synthesis with its model,
as a read-aloud is (cues as the model reads them, the readings, at its best quality); the
user reads where each block is with the letter, and the blocks, theirs alone, are the
browser's to keep. Without the deployer's speech synthesis, or Fish Audio failing, the letter
comes all the same, with no voice, its activity record saying so.

Driven through the backend's external API, Fish Audio faked at its transport, the letters'
ticks taken by hand (`Letters.run_due`)."""

import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import httpx
import pytest

from eidolon.config import Settings
from tests.conftest import CharacterConfig, ClientFactory
from tests.fakes import DEPLOYER_FISH_KEY, FakeFishAudio
from tests.test_concurrent_calls import another_user
from tests.test_letters import close_with_mano, letters, read, written
from tests.test_letters import settings  # noqa: F401
from tests.test_reach_outs import backend_of, records
from tests.test_read_aloud import DICTIONARY, READING, faked

LETTER = {
    "salutation": "[softly] 283プロのプロデューサーさんへ",
    "paragraphs": [
        {"ja": "[smiling] いつも<whisper>ありがとう</whisper>。", "zh": "一直以来谢谢你。"},
        {"ja": "これからもよろしくね。", "zh": "今后也请多关照。"},
    ],
    "sources": ["对话记录"],
}
SAID = ["[softly]283プロのプロデューサーさんへ", "[smiling]いつもありがとう。", "これからもよろしくね。"]
"""Each block as the deployer's model is given it: cues and all, no paired tags."""


def under_letters(database: Path) -> list[tuple[str, str, int, str, float]]:
    """Each service call of speech synthesis made under a letter's activity record: its
    model and provider, whether on the user's own key, and what it was billed for."""
    with sqlite3.connect(database) as db:
        return db.execute(
            "SELECT c.model, c.provider, c.own_key, c.usage_unit, c.usage_input"
            " FROM service_calls c JOIN activity_records r ON r.id = c.record_id"
            " WHERE r.kind = 'letter' AND c.service = 'tts' ORDER BY c.id"
        ).fetchall()


def not_voiced(database: Path) -> list[dict | None]:
    """What each letter's activity record says was made do without, oldest first."""
    with sqlite3.connect(database) as db:
        return [
            json.loads(d) if d else None
            for (d,) in db.execute(
                "SELECT degraded FROM activity_records WHERE kind = 'letter' ORDER BY id"
            )
        ]


async def test_each_block_is_voiced_on_the_deployers_key_and_read_by_the_user_alone(
    make_client: ClientFactory, settings: Settings, characters: CharacterConfig
):
    characters.write("readings.toml", READING)
    fish = FakeFishAudio()
    client, _, _, _ = await close_with_mano(
        make_client, settings, written(LETTER), fish_transport=faked(fish)
    )

    await backend_of(client).letters.run_due()
    [listed] = await letters(client)
    letter = (await read(client, listed["id"])).json()
    blocks = [await client.get(url) for url in letter["voice"]]
    beyond = await client.get(f"/api/letters/{listed['id']}/voice/3")
    theirs = await another_user(client, "someone").get(letter["voice"][0])

    assert fish.requests == [
        {
            "key": DEPLOYER_FISH_KEY, "model": "s2.1-pro-free", "text": said,
            "reference_id": "mano-voice", "format": "mp3", "sample_rate": 44100,
            "mp3_bitrate": 128, "latency": "normal", "pronunciation_dictionary": DICTIONARY,
        }
        for said in SAID
    ]
    assert letter["voice"] == [f"/api/letters/{listed['id']}/voice/{i}" for i in range(3)]
    assert [b.status_code for b in blocks] == [200] * 3
    assert [b.content for b in blocks] == [FakeFishAudio.audio(s, "mano-voice") for s in SAID]
    assert {b.headers["content-type"] for b in blocks} == {"audio/mpeg"}
    assert {b.headers["cache-control"] for b in blocks} == {"private, max-age=31536000, immutable"}
    assert (beyond.status_code, theirs.status_code) == (404, 404)
    assert under_letters(settings.database_path) == [
        ("s2.1-pro-free", FakeFishAudio.HOST, 0, "bytes", len(s.encode())) for s in SAID
    ]
    assert not_voiced(settings.database_path) == [None]


async def test_voiced_with_the_model_the_deployer_has(
    make_client: ClientFactory, settings: Settings
):
    fish = FakeFishAudio()
    drama = replace(settings, fish_audio_model="drama-3")
    client, _, _, _ = await close_with_mano(
        make_client, drama, written(LETTER), fish_transport=faked(fish)
    )

    await backend_of(client).letters.run_due()

    assert [(r["key"], r["model"]) for r in fish.requests] == [(DEPLOYER_FISH_KEY, "drama-3")] * 3


async def test_fish_audio_failing_at_a_paragraph_leaves_the_whole_letter_without_a_voice(
    make_client: ClientFactory, settings: Settings
):
    """Not a voice for some blocks and none for the rest: no voice at all, and no more asked
    for after the block it failed at."""
    fish = FakeFishAudio()

    def answer(request: httpx.Request) -> httpx.Response:
        if "ありがとう" in json.loads(request.content)["text"]:
            fish.requests.append({})
            return httpx.Response(503, json={"message": "overloaded"})
        return fish.handle(request)

    client, _, _, _ = await close_with_mano(
        make_client, settings, written(LETTER), fish_transport=httpx.MockTransport(answer)
    )

    await backend_of(client).letters.run_due()
    [listed] = await letters(client)

    assert (await read(client, listed["id"])).json()["voice"] is None
    assert len(fish.requests) == 2
    assert not_voiced(settings.database_path) == [{"voice": 1}]


@pytest.mark.parametrize("why", ["Fish Audio refusing", "no speech synthesis"])
async def test_without_a_voice_the_letter_comes_all_the_same_its_record_saying_so(
    make_client: ClientFactory, settings: Settings, why: str
):
    fish = FakeFishAudio()
    fish.refuses["mano-voice"] = 402
    client, _, _, _ = await close_with_mano(
        make_client, settings, written(LETTER), fish_transport=faked(fish),
        voice_configured=why != "no speech synthesis",
    )

    await backend_of(client).letters.run_due()
    [listed] = await letters(client)
    letter = (await read(client, listed["id"])).json()

    assert letter["voice"] is None
    assert letter["salutation"] == "283プロのプロデューサーさんへ"
    assert (await client.get(f"/api/letters/{listed['id']}/voice/0")).status_code == 404
    assert [r for r in records(settings.database_path) if r[0] == "letter"] == [
        ("letter", "mano", "success", 0)
    ]
    assert not_voiced(settings.database_path) == [{"voice": 1}]
    # Refused at the salutation, the paragraphs are not asked for.
    assert len(fish.requests) == (1 if why == "Fish Audio refusing" else 0)
