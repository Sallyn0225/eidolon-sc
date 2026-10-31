"""The music under a letter (GLOSSARY.md「信」): the list beside the character configuration,
`eidolon letter-music upload` putting the deployer's files in the stands' bucket under
`letters/music/`, and reading a letter telling the browser where its music is, when its
climax and fade are, and what stretch of it is played over, from the stands' address.

The upload is checked against the fake bucket of the stands' upload; the letters are driven
through the backend's external API as those of `test_letters`."""

from dataclasses import replace
from pathlib import Path

import httpx
import pytest

from eidolon.config import Settings
from eidolon.letter_music import (
    LetterMusicError,
    letter_music_path,
    load_letter_music,
    upload_letter_music,
)
from tests.conftest import REPO_LETTER_MUSIC, Admin, CharacterConfig, ClientFactory
from tests.fakes import FAKE_JUDGE, FakeClock, FakeLLM, level
from tests.test_achievements import turns
from tests.test_affinity import keep
from tests.test_letters import REPLY, close_with_mano, judged, letters, read, written
from tests.test_reach_outs import backend_of
from tests.test_stand_upload import FakeBucket
from tests.test_text_turn import start_conversation

STANDS = "https://stands.example.com"

LIST = """\
[close]
file = "升到亲近.m4a"
climax = 71

[her_birthday]
file = "her birthday.MP3"
climax = 64
loop = [3, 60]

[producer_birthday]
file = "生日.ogg"
"""


@pytest.fixture
def settings(settings: Settings) -> Settings:
    """With the judge model, affinity and gifts, letters on, and the stands' address."""
    return replace(
        settings, judge=FAKE_JUDGE, affinity_and_gifts=True, letters=True, stand_assets_url=STANDS
    )


@pytest.fixture
def music(tmp_path: Path) -> dict:
    path = tmp_path / "letter_music.toml"
    path.write_text(LIST, encoding="utf-8")
    return load_letter_music(path)


@pytest.fixture
def directory(tmp_path: Path) -> Path:
    """The deployer's directory, with every file the list names and one it does not."""
    found = tmp_path / "bgm"
    found.mkdir()
    for name in ("升到亲近.m4a", "her birthday.MP3", "生日.ogg", "listen.html"):
        (found / name).write_bytes(f"audio {name}".encode())
    return found


async def upload(directory: Path, music: dict, storage: FakeBucket):
    bucket = storage.bucket()
    try:
        return await upload_letter_music(directory, music, bucket)
    finally:
        await bucket.aclose()


async def test_uploads_each_occasions_file_the_list_names_under_letters_music(
    directory: Path, music: dict
):
    storage = FakeBucket()

    report = await upload(directory, music, storage)

    assert sorted(storage.objects) == [
        "letters/music/close.m4a",
        "letters/music/her_birthday.mp3",
        "letters/music/producer_birthday.ogg",
    ]
    assert storage.objects["letters/music/close.m4a"][0] == "audio 升到亲近.m4a".encode()

    def headers(key: str) -> tuple[str, str]:
        sent = storage.objects[key][1]
        return sent["content-type"], sent["cache-control"]

    # The same address whatever piece is there: checked each time it is downloaded.
    assert headers("letters/music/close.m4a") == ("audio/mp4", "public, no-cache")
    assert headers("letters/music/her_birthday.mp3") == ("audio/mpeg", "public, no-cache")
    assert headers("letters/music/producer_birthday.ogg") == ("audio/ogg", "public, no-cache")
    assert report.uploaded == ["close", "her_birthday", "producer_birthday"]
    assert report.missing == []


async def test_what_the_bucket_has_as_it_is_is_not_uploaded_again(directory: Path, music: dict):
    storage = FakeBucket()
    await upload(directory, music, storage)
    storage.puts.clear()
    (directory / "生日.ogg").write_bytes(b"another piece")

    report = await upload(directory, music, storage)

    assert storage.puts == ["letters/music/producer_birthday.ogg"]
    assert storage.objects["letters/music/producer_birthday.ogg"][0] == b"another piece"
    assert report.uploaded == ["producer_birthday"]
    assert report.unchanged == 2


async def test_a_missing_file_is_reported_and_the_rest_uploaded(directory: Path, music: dict):
    storage = FakeBucket()
    (directory / "升到亲近.m4a").unlink()

    report = await upload(directory, music, storage)

    assert report.missing == ["升到亲近.m4a"]
    assert sorted(storage.objects) == [
        "letters/music/her_birthday.mp3",
        "letters/music/producer_birthday.ogg",
    ]


async def test_a_bucket_that_fails_is_an_error(directory: Path, music: dict):
    from eidolon.s3 import S3Error

    storage = FakeBucket()
    storage.down = True

    with pytest.raises(S3Error, match="503"):
        await upload(directory, music, storage)


def test_the_repositorys_list_is_the_one_beside_the_character_configuration():
    assert letter_music_path(REPO_LETTER_MUSIC.parent / "characters.toml") == REPO_LETTER_MUSIC
    load_letter_music(REPO_LETTER_MUSIC)


@pytest.mark.parametrize(
    "broken",
    [
        '[birthday]\nfile = "a.m4a"\n',  # no such occasion
        "[close]\nclimax = 71\n",  # no file
        '[close]\nfile = "a.txt"\n',  # not audio
        '[close]\nfile = "a.m4a"\nclimax = "71"\n',
        '[close]\nfile = "a.m4a"\nclimax = 71\nfade = 60\n',  # a fade before it
        '[her_birthday]\nfile = "a.m4a"\nclimax = 64\nloop = [60, 3]\n',
        '[her_birthday]\nfile = "a.m4a"\nclimax = 50\nloop = [3, 60]\n',  # the climax in the loop
        '[close]\nfile = "a.m4a"\nclimax = 71\nloops = [3, 60]\n',  # a misspelling
        "[close\n",
    ],
)
def test_a_broken_list_is_an_error(tmp_path: Path, broken: str):
    path = tmp_path / "letter_music.toml"
    path.write_text(broken, encoding="utf-8")

    with pytest.raises(LetterMusicError, match="letter_music.toml"):
        load_letter_music(path)


def test_the_command_needs_the_directory(admin: Admin, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    for name, value in {
        "ENDPOINT": "http://storage.test",
        "BUCKET": "stands",
        "ACCESS_KEY_ID": "key-id",
        "SECRET_ACCESS_KEY": "secret",
    }.items():
        monkeypatch.setenv(f"EIDOLON_STAND_S3_{name}", value)
    (tmp_path / "letter_music.toml").write_text(LIST, encoding="utf-8")

    code, _, err = admin.invoke(
        "letter-music", "upload", str(tmp_path / "bgm-src"), "--characters", str(tmp_path / "characters.toml")
    )

    assert code == 1
    assert "bgm-src" in err


def test_the_command_needs_the_list(admin: Admin, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("EIDOLON_STAND_S3_BUCKET", "stands")

    code, _, err = admin.invoke("letter-music", "upload", str(tmp_path), "--characters", str(tmp_path / "characters.toml"))

    assert code == 1
    assert "letter_music.toml" in err


async def intimate_at_once(make_client: ClientFactory, settings: Settings) -> tuple[httpx.AsyncClient, dict]:
    """A client whose user's affinity with Mano has reached close and intimate at once, and
    the letter she wrote on both."""
    clock = FakeClock()
    client = make_client(FakeLLM(REPLY, REPLY, written()), clock=clock, clients=judged(level(4), level(4)))
    conversation = await start_conversation(client)
    await turns(client, conversation, 1)
    keep(settings.database_path, "producer", 84.9, clock.now)
    await turns(client, conversation, 1)
    await backend_of(client).letters.run_due()
    [listed] = await letters(client)
    assert listed["occasions"] == ["intimate", "close"]
    return client, listed


async def test_a_letter_on_several_occasions_has_the_music_of_the_first(
    make_client: ClientFactory, settings: Settings
):
    """Intimate before close: the order a letter of several names them."""
    client, listed = await intimate_at_once(make_client, settings)

    res = await read(client, listed["id"])

    assert res.json()["music"] == {
        "url": f"{STANDS}/letters/music/intimate.m4a",
        "climax": 101,
        "fade": 148,
        "loop": None,
    }


async def test_an_occasion_the_list_lacks_gives_way_to_the_next(
    make_client: ClientFactory, settings: Settings, characters: CharacterConfig
):
    characters.write("letter_music.toml", LIST)
    client, listed = await intimate_at_once(make_client, settings)

    res = await read(client, listed["id"])

    assert res.json()["music"] == {
        "url": f"{STANDS}/letters/music/close.m4a",
        "climax": 71,
        "fade": None,
        "loop": None,
    }


async def test_without_the_stands_address_a_letter_has_no_music(
    make_client: ClientFactory, settings: Settings
):
    nowhere, _, _, _ = await close_with_mano(make_client, replace(settings, stand_assets_url=None), written())
    await backend_of(nowhere).letters.run_due()
    [listed] = await letters(nowhere)

    assert (await read(nowhere, listed["id"])).json()["music"] is None


async def test_without_the_list_a_letter_has_no_music(
    make_client: ClientFactory, settings: Settings, characters: CharacterConfig
):
    letter_music_path(characters.path).unlink()
    client, _, _, _ = await close_with_mano(make_client, settings, written())
    await backend_of(client).letters.run_due()
    [listed] = await letters(client)

    assert (await read(client, listed["id"])).json()["music"] is None
