"""Her moment's picture (GLOSSARY.md「配图」): where the deployer has image generation, she is
told last what compositions it may be in, and writes it as a photo tag is written; it is
generated on the deployer's image generation before the moment shows, in prompts fixed by its
composition, at its size, and kept with it as WebP without metadata, the user's alone to read.
Where she has no photo tags, only those no one is in; without image generation, none. One she
writes amiss, or that fails or takes too long, leaves the moment without a picture, posted all
the same. Pictures wait their turn with photos, each photo ahead of every picture waiting.

Driven as `test_moments.py` drives moments (`SteadyRandom(0)`: every moment has a picture), the
image service faked at its transport, where every request it is sent is seen."""

import asyncio
import io
import sqlite3
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import httpx
import pytest
from PIL import Image

import eidolon.moments
from eidolon.config import ImageSettings, Settings
from eidolon.moment_prompt import COMPOSITIONS_CLOSING, IMAGE
from eidolon.photo_prompt import NEGATIVE_PROMPT, read_picture, tag_fields
from tests.conftest import KOGANE_SHEET, MANO_PHOTO, MANO_SHEET, CharacterConfig, ClientFactory
from tests.fakes import (
    FAKE_JUDGE,
    FakeClock,
    FakeIdentityProvider,
    FakeImageService,
    FakeLLM,
    SteadyRandom,
    context_of,
)
from tests.test_activity_records import dashboard, health
from tests.test_admin_users import ADMIN, admin_beside
from tests.test_moment_places import degraded
from tests.test_moments import (
    FACTS,
    POST,
    REPLY,
    SEVEN,
    START,
    moment_records,
    talked,
    tick,
    timeline,
)
from tests.test_photos import IMAGE as NOVELAI
from tests.test_photos import SELFIE, WORDS, asking, photo_events, settled
from tests.test_reach_outs import backend_of, last_contact
from tests.test_text_turn import send_turn, start_conversation

HEAD = "1girl, solo, sakuragi mano, idolmaster shiny colors, brown hair, medium hair, brown eyes"
TAIL = "rating:general, very aesthetic, masterpiece, no text"
NO_HUMANS_NEGATIVE = f"{NEGATIVE_PROMPT}, 1girl, 1boy, people"

STREET = """
composition: scenery
framing: full body
place: street, dusk, outdoors
outfit: coat
action: sidewalk, power lines, vending machine
note: 回家路上的住宅街
"""
ELSEWHERE = ["<place>none</place>", "<likes></likes>"]
"""At none of the places, liked by no one."""


def pictured(image: str) -> list[str]:
    """What she writes to post with a picture `image`, at none of the places, liked by no
    one."""
    return [*POST, f"<image>{image}</image>", *ELSEWHERE]


@pytest.fixture
def characters(tmp_path: Path) -> CharacterConfig:
    """Mano, with facts and her photo tags; Kogane, without photo tags."""
    return (
        CharacterConfig(tmp_path / "characters")
        .add("mano", "櫻木真乃", MANO_SHEET, birthday="04-25", facts=FACTS, photo=MANO_PHOTO)
        .add("kogane", "月岡恋鐘", KOGANE_SHEET, birthday="02-25")
    )


@pytest.fixture
def settings(settings: Settings) -> Settings:
    """With moments on, the deployer's image generation and the judge model, affinity off; and
    an admin."""
    return replace(
        settings, moments=True, image=NOVELAI, judge=FAKE_JUDGE, affinity_and_gifts=False,
        admins=frozenset({ADMIN}),
    )


async def posted(
    make_client: ClientFactory, image: FakeImageService, *replies, **services
) -> tuple[httpx.AsyncClient, FakeLLM]:
    """A client whose user has had a turn with Mano, once she has posted, her chat model
    replying with `replies` after the turn."""
    client, llm, clock, _ = await talked(
        make_client, *replies, image_transport=image.transport(), **services
    )
    await tick(client, clock, START)
    await tick(client, clock, SEVEN)
    return client, llm


def image_calls(database: Path) -> list[tuple[str, int | None, str | None]]:
    """Each call to image generation: the kind of record it is under, and its error."""
    with sqlite3.connect(database) as db:
        return db.execute(
            "SELECT r.kind, c.record_id, c.error FROM service_calls c"
            " LEFT JOIN activity_records r ON r.id = c.record_id"
            " WHERE c.service = 'image' ORDER BY c.id"
        ).fetchall()


async def test_told_last_what_compositions_it_may_be_in_her_picture_shows_with_her_moment(
    make_client: ClientFactory, settings: Settings
):
    image = FakeImageService()
    client, llm = await posted(make_client, image, pictured(STREET))

    told = context_of(llm.prompts[-1])
    [moment] = await timeline(client)
    picture = await client.get(moment["image"])
    [request] = image.requests

    assert told.rindex("# 这次允许的构图") > told.index("# 地点候选")
    assert told.endswith(COMPOSITIONS_CLOSING)
    for composition in ("scenery", "food", "object", "selfie", "posed", "candid"):
        assert f"  - {composition}：" in told
    assert "group" not in told
    assert moment["image"] == f"/api/moments/{moment['id']}/image"
    assert moment["ja"] == "今日は公園でピーちゃんと日向ぼっこ(^^)"
    assert picture.status_code == 200
    assert picture.headers["content-type"] == "image/webp"
    assert picture.headers["cache-control"].startswith("private")
    assert FakeImageService.METADATA.encode() not in picture.content
    with Image.open(io.BytesIO(picture.content)) as webp:
        assert (webp.format, webp.size) == ("WEBP", (1216, 832))
    assert request["key"] == NOVELAI.api_key
    assert moment_records(settings.database_path) == [("moment", "mano", "success", 0)]
    assert [(kind, error) for kind, _, error in image_calls(settings.database_path)] == [
        ("moment", None)
    ]
    assert degraded(settings.database_path) == [None]


@pytest.mark.parametrize(
    ("written", "positive", "negative", "size"),
    [
        pytest.param(
            STREET,
            "no humans, scenery, japan, outdoors, street, dusk, sidewalk, power lines,"
            f" vending machine, {TAIL}",
            NO_HUMANS_NEGATIVE, (1216, 832), id="scenery",
        ),
        pytest.param(
            "composition: food\nframing: portrait\nplace: cafe, indoors\noutfit: coat\n"
            "action: parfait, coffee",
            f"no humans, food focus, parfait, coffee, cafe, indoors, depth of field, {TAIL}",
            NO_HUMANS_NEGATIVE, (832, 1216), id="food",
        ),
        pytest.param(
            "composition: food\nplace: cafe",
            f"no humans, food focus, food, cafe, depth of field, {TAIL}",
            NO_HUMANS_NEGATIVE, (832, 1216), id="food with nothing in it",
        ),
        pytest.param(
            "composition: object\nplace: bedroom, night\naction: flower, vase",
            f"no humans, object focus, flower, vase, bedroom, night, depth of field, {TAIL}",
            NO_HUMANS_NEGATIVE, (832, 1216), id="object",
        ),
        pytest.param(
            "composition: selfie\nframing: wide shot\nplace: cafe, indoors\n"
            "outfit: white shirt\naction: peace sign, smile",
            f"{HEAD}, selfie, looking at viewer, upper body, cafe, indoors, white shirt,"
            f" peace sign, smile, {TAIL}",
            NEGATIVE_PROMPT, (832, 1216), id="selfie",
        ),
        pytest.param(
            "composition: posed\nframing: wide shot\nplace: shrine, outdoors, day\n"
            "outfit: coat\naction: peace sign, smile",
            f"{HEAD}, wide shot, shrine, outdoors, day, coat, peace sign, smile,"
            f" looking at viewer, {TAIL}",
            NEGATIVE_PROMPT, (832, 1216), id="posed",
        ),
        pytest.param(
            "composition: candid\nframing: cowboy shot\nplace: street, day\noutfit: coat\n"
            "action: walking, looking at viewer, smile",
            f"{HEAD}, cowboy shot, street, day, coat, walking, smile, looking away,"
            f" depth of field, {TAIL}",
            f"{NEGATIVE_PROMPT}, looking at viewer", (832, 1216), id="candid",
        ),
        pytest.param(
            "composition: candid\nframing: full body\nplace: park\noutfit: coat\n"
            "action: reading, looking down",
            f"{HEAD}, full body, park, coat, reading, looking down, depth of field, {TAIL}",
            f"{NEGATIVE_PROMPT}, looking at viewer", (832, 1216), id="candid looking down",
        ),
    ],
)
async def test_each_composition_is_generated_in_prompts_of_its_own_at_its_size(
    make_client: ClientFactory,
    settings: Settings,
    written: str,
    positive: str,
    negative: str,
    size: tuple[int, int],
):
    image = FakeImageService()
    client, _ = await posted(make_client, image, pictured(written))

    [request] = image.requests
    parameters = request["body"]["parameters"]
    [moment] = await timeline(client)

    assert request["body"]["input"] == positive
    assert parameters["v4_prompt"]["caption"]["base_caption"] == positive
    assert parameters["negative_prompt"] == negative
    assert parameters["v4_negative_prompt"]["caption"]["base_caption"] == negative
    assert (parameters["width"], parameters["height"]) == size
    assert moment["image"] is not None
    assert degraded(settings.database_path) == [None]  # a framing not of it is no harm


async def test_in_openais_image_format_it_is_asked_for_and_checked_at_its_size(
    make_client: ClientFactory, settings: Settings
):
    relay = ImageSettings("relay-key", "https://relay.image.test/v1", "nai", api_format="openai")
    image = FakeImageService()
    client, _ = await posted(
        make_client, image, pictured(STREET), settings=replace(settings, image=relay)
    )

    [request] = image.requests
    [moment] = await timeline(client)
    picture = await client.get(moment["image"])

    assert request["body"]["size"] == "1216x832"
    with Image.open(io.BytesIO(picture.content)) as webp:
        assert webp.size == (1216, 832)


async def test_what_would_draw_anyone_in_is_stripped_and_what_crosses_the_line_counted(
    make_client: ClientFactory, settings: Settings, github: FakeIdentityProvider
):
    image = FakeImageService()
    nobody = (
        "composition: scenery\nplace: park, viewer holding phone, idolmaster shiny colors\n"
        "action: 1girl, solo, sakuragi mano, selfie, looking at viewer, holding umbrella,"
        " holding hands, cherry blossoms"
    )
    alone = (
        "composition: posed\nplace: park, no humans\noutfit: coat, solo focus\n"
        "action: holding hands, smile"
    )
    client, _, clock, _ = await talked(
        make_client, pictured(nobody), pictured(alone), image_transport=image.transport()
    )
    await tick(client, clock, START)
    await tick(client, clock, SEVEN)
    await tick(client, clock, START + timedelta(days=1))
    await tick(client, clock, SEVEN + timedelta(days=1))

    [scenery, posed] = (r["body"]["input"] for r in image.requests)
    async with admin_beside(client, github) as admin:
        image_row = health(await dashboard(admin), "image")

    assert scenery == f"no humans, scenery, japan, outdoors, park, cherry blossoms, {TAIL}"
    assert posed == f"{HEAD}, upper body, park, coat, smile, looking at viewer, {TAIL}"
    assert image_row is not None
    assert image_row["stripped_photos"] == 2
    assert image_row["stripped"] == {"people": 4}
    for written in ("viewer holding phone", "solo focus", "holding hands"):
        assert written not in str(image_row), written


async def test_she_without_photo_tags_is_let_choose_only_those_no_one_is_in(
    make_client: ClientFactory, settings: Settings
):
    image = FakeImageService()
    llm = FakeLLM(REPLY, pictured("composition: selfie\naction: smile"))
    clock = FakeClock(START)
    client = make_client(
        llm, clock=clock, random=SteadyRandom(0), image_transport=image.transport()
    )
    conversation = await start_conversation(client, "kogane")
    await send_turn(client, conversation, "我去练习了")
    last_contact(settings.database_path, conversation, START - timedelta(hours=1))
    await tick(client, clock, START)
    await tick(client, clock, SEVEN)

    told = context_of(llm.prompts[-1])
    [moment] = await timeline(client)

    for composition in ("scenery", "food", "object"):
        assert f"  - {composition}：" in told
    for composition in ("selfie", "posed", "candid", "group"):
        assert f"  - {composition}：" not in told
    assert image.requests == []
    assert moment["image"] is None
    assert degraded(settings.database_path) == [{IMAGE: 1}]


async def test_without_image_generation_every_moment_is_without_a_picture(
    make_client: ClientFactory, settings: Settings
):
    image = FakeImageService()
    client, llm = await posted(
        make_client, image, pictured(STREET), settings=replace(settings, image=None)
    )

    [moment] = await timeline(client)

    assert "# 这次允许的构图" not in context_of(llm.prompts[-1])
    assert image.requests == []
    assert moment["image"] is None
    assert degraded(settings.database_path) == [None]


@pytest.mark.parametrize(
    "written",
    [
        pytest.param([*POST, *ELSEWHERE], id="none written"),
        pytest.param(pictured("composition: group\naction: smile"), id="not allowed"),
        pytest.param(pictured("composition: object\nplace: desk"), id="an object of nothing"),
        pytest.param(pictured("composition: object\naction: 1girl, holding cup"),
                     id="an object of nothing once stripped"),
    ],
)
async def test_one_written_amiss_leaves_the_moment_without_a_picture_and_is_recorded(
    make_client: ClientFactory, settings: Settings, written: list[str]
):
    image = FakeImageService()
    client, _ = await posted(make_client, image, written)

    [moment] = await timeline(client)

    assert image.requests == []
    assert moment["image"] is None
    assert moment_records(settings.database_path) == [("moment", "mano", "success", 0)]
    assert degraded(settings.database_path) == [{IMAGE: 1}]


@pytest.mark.parametrize("answered", ["HTTP 503", "the wrong size", "too slow"])
async def test_one_not_had_leaves_the_moment_posted_without_it_its_call_failed(
    make_client: ClientFactory,
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    answered: str,
):
    image = FakeImageService()
    if answered == "HTTP 503":
        image.status = 503
    if answered == "the wrong size":
        image.size = (832, 1216)  # scenery is asked for at 1216×832
    if answered == "too slow":
        monkeypatch.setattr(eidolon.moments, "PICTURE_TIME_LIMIT", timedelta(seconds=0.2))
        image.gate = asyncio.Event()
    client, _ = await posted(make_client, image, pictured(STREET))
    if image.gate is not None:  # what comes after the time limit is left
        image.gate.set()

    [moment] = await timeline(client)

    assert moment["image"] is None
    assert moment["ja"] == "今日は公園でピーちゃんと日向ぼっこ(^^)"
    assert (await client.get(f"/api/moments/{moment['id']}/image")).status_code == 404
    assert moment_records(settings.database_path) == [("moment", "mano", "success", 0)]
    [(kind, _, error)] = image_calls(settings.database_path)
    assert kind == "moment" and error is not None
    assert len(image.requests) == 1  # never asked again


async def test_photos_go_ahead_of_pictures_waiting_one_being_generated_going_on(
    make_client: ClientFactory, settings: Settings
):
    image = FakeImageService()
    image.gate = asyncio.Event()
    photo_reply = [f"<photo>{SELFIE}</photo>", WORDS]
    client, _, clock, conversation = await talked(
        make_client, pictured(STREET), photo_reply, clients=asking(),
        image_transport=image.transport(),
    )
    await tick(client, clock, START)
    clock.now = SEVEN
    backend = backend_of(client)
    first = asyncio.create_task(backend.moments.run_due())
    while not image.requests:
        await asyncio.sleep(0.01)
    tag = read_picture(tag_fields("composition: food\naction: parfait"), ["food"])
    assert tag is not None
    until = asyncio.get_running_loop().time() + 60
    second = asyncio.create_task(
        backend.photos.picture(backend.characters["mano"], tag, until)
    )
    await asyncio.sleep(0.05)
    [photo] = photo_events(await send_turn(client, conversation, "发张自拍给我看看"))
    await asyncio.sleep(0.05)
    waiting = len(image.requests)
    image.gate.set()
    await first
    await second
    await settled(client, photo["id"])

    [street, selfie, parfait] = (r["body"]["input"] for r in image.requests)
    assert waiting == 1
    assert "sidewalk" in street
    assert "white shirt" in selfie
    assert "parfait" in parfait


async def test_one_that_waits_out_its_time_limit_in_the_queue_is_no_failed_call(
    make_client: ClientFactory, settings: Settings, monkeypatch: pytest.MonkeyPatch
):
    image = FakeImageService()
    image.gate = asyncio.Event()
    photo_reply = [f"<photo>{SELFIE}</photo>", WORDS]
    client, _, clock, conversation = await talked(
        make_client, photo_reply, pictured(STREET), clients=asking(),
        image_transport=image.transport(),
    )
    [photo] = photo_events(await send_turn(client, conversation, "发张自拍给我看看"))
    monkeypatch.setattr(eidolon.moments, "PICTURE_TIME_LIMIT", timedelta(seconds=0.2))
    await tick(client, clock, START)
    await tick(client, clock, SEVEN)
    image.gate.set()
    await settled(client, photo["id"])

    [moment] = await timeline(client)

    assert moment["image"] is None
    [request] = image.requests
    assert "white shirt" in request["body"]["input"]
    assert [kind for kind, _, _ in image_calls(settings.database_path)] == ["turn"]


async def test_she_recalls_her_latest_moments_by_their_pictures_notes(
    make_client: ClientFactory, settings: Settings
):
    image = FakeImageService()
    client, llm, clock, _ = await talked(
        make_client, pictured(STREET), [*POST, *ELSEWHERE],
        image_transport=image.transport(),
    )
    await tick(client, clock, START)
    await tick(client, clock, SEVEN)
    await tick(client, clock, START + timedelta(days=1))
    await tick(client, clock, SEVEN + timedelta(days=1))

    told = context_of(llm.prompts[-1])

    assert "- 今日は公園でピーちゃんと日向ぼっこ(^^)（配图：回家路上的住宅街）" in told


async def test_only_the_user_whose_moment_it_is_reads_its_picture(
    make_client: ClientFactory, settings: Settings, github: FakeIdentityProvider
):
    image = FakeImageService()
    client, _ = await posted(make_client, image, pictured(STREET))
    friend = make_client(FakeLLM(), user="friend", clock=FakeClock(SEVEN))
    signed_out = make_client(FakeLLM(), user=None, clock=FakeClock(SEVEN))

    [moment] = await timeline(client)
    path = moment["image"]

    assert (await client.get(path)).status_code == 200
    assert (await friend.get(path)).status_code == 404
    assert (await signed_out.get(path)).status_code == 401
    async with admin_beside(client, github) as admin:
        assert (await admin.get(path)).status_code == 404
    assert (await client.get(f"/api/moments/{moment['id'] + 1}/image")).status_code == 404
