"""Fetching the stands from ShinyColorsDB (`eidolon stand fetch`, ADR-0011): the everyday
clothes and stage costumes of every configured character's cards, into the build
directory's `source/`, which `eidolon stand outfits` lists them from. Checked against a
fake ShinyColorsDB, through the command line."""

import json
from pathlib import Path

import httpx
import pytest

from eidolon.mirror import Mirror
from tests.conftest import Admin, CharacterConfig
from tests.fakes import FakeEnzaAssets, GameCatalogFile

MANO = "櫻木真乃"
PNG = b"\x89PNG\r\n\x1a\n texture"
WEBP = b"RIFF\x10\x00\x00\x00WEBPVP8 texture"


class FakeShinyColorsDB:
    """The spine part of ShinyColorsDB's API and its CDN, which keep the cards they are
    given and remember what they were asked for, and behind them the game's asset server
    (`official`), which has nothing unless given it."""

    def __init__(self) -> None:
        self.dresses: dict[int, list[dict]] = {}
        self.files: dict[str, bytes] = {}
        self.requests: list[str] = []
        self.down = False
        self.official = FakeEnzaAssets()

    def card(
        self,
        idol_id: int,
        enza_id: str,
        dress_name: str,
        dress_type: str = "P_SSR",
        *,
        categories: tuple[str, ...] = ("cb", "cb_costume", "stand", "stand_costume"),
        without_path: tuple[str, ...] = (),
        without_files: tuple[str, ...] = (),
        texture: bytes = PNG,
    ) -> "FakeShinyColorsDB":
        assets = []
        for category in categories:
            path = f"spine/idols/{category}/{enza_id}/"
            assets.append({"path": "" if category in without_path else path, "type": category})
            if category in without_path or category in without_files:
                continue
            self.outfit(category, enza_id, texture)
        self.dresses.setdefault(idol_id, []).append({
            "exist": True, "assets": {"idols": assets}, "idolId": idol_id, "dressName": dress_name,
            "dressType": dress_type, "enzaId": enza_id,
        })
        return self

    def outfit(self, category: str, enza_id: str, texture: bytes = PNG) -> None:
        """The CDN has the stand's files, whether or not the API lists it."""
        path = f"spine/idols/{category}/{enza_id}/"
        self.files[f"{path}data.json"] = b'{"skeleton": {"spine": "3.6.53"}}'
        self.files[f"{path}data.atlas"] = b"\ndata.png\nsize: 2048,2048\n"
        self.files[f"{path}data.png"] = texture + f" {category} {enza_id}".encode()

    def withdraw(self, idol_id: int, enza_id: str) -> None:
        self.dresses[idol_id] = [d for d in self.dresses[idol_id] if d["enzaId"] != enza_id]

    def handle(self, request: httpx.Request) -> httpx.Response:
        if self.down:
            raise httpx.ConnectError("down", request=request)
        url = request.url
        if url.host == "shinycolors.enza.fun":
            return self.official.handle(request)
        self.requests.append(str(url))
        if url.host == "api.shinycolors.moe" and url.path == "/spine/dresslist":
            return httpx.Response(200, json=self.dresses.get(int(url.params["idolId"]), []))
        if url.host == "cf-static.shinycolors.moe" and url.path.lstrip("/") in self.files:
            return httpx.Response(200, content=self.files[url.path.lstrip("/")])
        return httpx.Response(404, text="<html>Not Found</html>")

    def mirror(self) -> Mirror:
        return Mirror(httpx.AsyncClient(transport=httpx.MockTransport(self.handle)), interval=0)


@pytest.fixture
def site(monkeypatch: pytest.MonkeyPatch) -> FakeShinyColorsDB:
    site = FakeShinyColorsDB()
    monkeypatch.setattr("eidolon.mirror.Mirror", lambda: site.mirror())
    return site


class Stands:
    """`eidolon stand fetch` and `eidolon stand outfits` on one build directory, for Mano
    (idol 1) and Kogane (no idol)."""

    def __init__(self, admin: Admin, characters: CharacterConfig, build: Path) -> None:
        self._admin = admin
        self._characters = characters
        self.build = build

    def _args(self, action: str) -> list[str]:
        return ["stand", action, "--build", str(self.build), "--characters", str(self._characters.path)]

    def fetch(self, *args: str) -> tuple[int, str, str]:
        return self._admin.invoke(*self._args("fetch"), *args)

    def manifest(self) -> dict[str, tuple[str, str]]:
        """Each outfit the source's manifest lists, with its name and kind."""
        entries = json.loads((self.build / "source" / "spine_manifest.json").read_text(encoding="utf-8"))
        return {f"{e['category']}/{e['enzaId']}": (e["dressName"], e["dressType"]) for e in entries}

    def outfits(self) -> list[str]:
        """The outfits Mano's outfit list names, after `eidolon stand outfits`."""
        self._admin.run(*self._args("outfits"))
        cards = json.loads((self.build / "outfits" / "1.json").read_text(encoding="utf-8"))["cards"]
        return [card[kind]["id"] for card in cards for kind in ("everyday", "stage") if card[kind]]

    def file(self, outfit: str, name: str) -> Path:
        return self.build / "source" / "assets" / "spine" / "idols" / outfit / name


@pytest.fixture
def stands(admin: Admin, characters: CharacterConfig, tmp_path: Path) -> Stands:
    return Stands(admin, characters, tmp_path / "build")


def test_the_stands_of_the_configured_characters_cards_are_fetched_and_listed(
    stands: Stands, site: FakeShinyColorsDB
):
    site.card(1, "1030010010", f"【ナチュラルモード】{MANO}", "P_SR")
    site.card(4, "1030040010", "【】月岡恋鐘", "P_SR")

    code, out, err = stands.fetch()

    assert code == 0, err
    assert stands.outfits() == ["stand/1030010010", "stand_costume/1030010010"]
    assert stands.file("stand/1030010010", "data.png").read_bytes() == site.files[
        "spine/idols/stand/1030010010/data.png"
    ]
    assert not any("/spine/idols/cb" in url for url in site.requests)
    assert not any("idolId=4" in url for url in site.requests)
    assert "2 套" in out


def test_what_was_fetched_before_is_not_downloaded_again(stands: Stands, site: FakeShinyColorsDB):
    site.card(1, "1030010010", f"【ナチュラルモード】{MANO}", "P_SR")
    stands.fetch()
    site.card(1, "1030010020", f"【ぐうぜんBOOKS】{MANO}", "P_SR")
    site.requests.clear()

    code, _, err = stands.fetch()

    assert code == 0, err
    downloads = [url for url in site.requests if "cf-static" in url]
    assert downloads and all("1030010020" in url for url in downloads)
    assert stands.outfits() == [
        "stand/1030010010", "stand_costume/1030010010", "stand/1030010020", "stand_costume/1030010020",
    ]


def test_a_card_the_list_no_longer_has_stays(stands: Stands, site: FakeShinyColorsDB):
    site.card(1, "1030010010", f"【ナチュラルモード】{MANO}", "P_SR")
    site.card(1, "1030010020", f"【ぐうぜんBOOKS】{MANO}", "P_SR")
    stands.fetch()
    site.withdraw(1, "1030010010")

    stands.fetch()

    assert "stand/1030010010" in stands.outfits()


def test_an_outfit_listed_without_its_files_is_skipped_until_they_are_there(
    stands: Stands, site: FakeShinyColorsDB
):
    site.card(1, "1030010010", f"【ナチュラルモード】{MANO}", "P_SR", without_path=("stand_costume",))
    site.card(1, "1030010020", f"【ぐうぜんBOOKS】{MANO}", "P_SR", without_files=("stand",))

    code, _, err = stands.fetch()

    assert code == 0, err
    assert "stand_costume/1030010010" in err and "stand/1030010020" in err
    assert stands.outfits() == ["stand/1030010010", "stand_costume/1030010020"]
    assert not stands.file("stand/1030010020", "data.json").exists()

    site.dresses[1].clear()
    site.card(1, "1030010010", f"【ナチュラルモード】{MANO}", "P_SR")
    site.card(1, "1030010020", f"【ぐうぜんBOOKS】{MANO}", "P_SR")
    stands.fetch()

    assert stands.outfits() == [
        "stand/1030010010", "stand_costume/1030010010", "stand/1030010020", "stand_costume/1030010020",
    ]


def test_an_outfit_shinycolorsdb_has_no_files_of_comes_from_the_games_asset_server(
    stands: Stands, site: FakeShinyColorsDB
):
    site.card(1, "1030010010", f"【ナチュラルモード】{MANO}", "P_SR", without_path=("stand_costume",))
    costume = "spine/idols/stand_costume/1030010010/"
    site.official.files.update({
        f"{costume}data.json": b'{"skeleton": {"spine": "3.6.53"}}',
        f"{costume}data.atlas": b"\ndata.png\nsize: 2048,2048\n",
        f"{costume}data.png": PNG + b" stand_costume",
    })

    code, _, err = stands.fetch()

    assert code == 0, err
    assert stands.outfits() == ["stand/1030010010", "stand_costume/1030010010"]
    assert stands.file("stand_costume/1030010010", "data.png").read_bytes() == PNG + b" stand_costume"


def test_a_file_that_is_not_what_it_says_is_not_kept(stands: Stands, site: FakeShinyColorsDB):
    site.card(1, "1030010010", f"【ナチュラルモード】{MANO}", "P_SR")
    site.files["spine/idols/stand/1030010010/data.png"] = b"<html>error page</html>"

    code, _, err = stands.fetch()

    assert code == 0, err
    assert "stand/1030010010" in err
    assert not stands.file("stand/1030010010", "data.png").exists()
    assert stands.outfits() == ["stand_costume/1030010010"]


def test_a_texture_in_webp_is_kept_as_it_is(stands: Stands, site: FakeShinyColorsDB):
    site.card(1, "1030010010", f"【ナチュラルモード】{MANO}", "P_SR", texture=WEBP)

    stands.fetch()

    assert stands.file("stand/1030010010", "data.png").read_bytes().startswith(WEBP)


def test_an_atlas_naming_another_texture_page_is_pointed_back_at_data_png(stands: Stands, site: FakeShinyColorsDB):
    site.card(1, "1030010010", f"【ナチュラルモード】{MANO}", "P_SR")
    # Some of ShinyColorsDB's atlases name their page `date.png`, and it serves the same
    # image under both names: the texture is kept as data.png and the atlas points at it.
    stand = "spine/idols/stand/1030010010/"
    site.files[f"{stand}data.atlas"] = b"\ndate.png\nsize: 2048,2048\n"
    site.files[f"{stand}date.png"] = site.files[f"{stand}data.png"]

    code, _, err = stands.fetch()

    assert code == 0, err
    assert stands.file("stand/1030010010", "data.atlas").read_bytes() == b"\ndata.png\nsize: 2048,2048\n"
    assert "stand/1030010010" in stands.outfits()


def test_an_atlas_fetched_before_the_fix_is_pointed_at_data_png_too(stands: Stands, site: FakeShinyColorsDB):
    site.card(1, "1030010010", f"【ナチュラルモード】{MANO}", "P_SR")
    stands.fetch()
    # What a source fetched before this fix looks like: the atlas still names `date.png`.
    stands.file("stand/1030010010", "data.atlas").write_bytes(b"\ndate.png\nsize: 2048,2048\n")
    site.files["spine/idols/stand/1030010010/date.png"] = site.files["spine/idols/stand/1030010010/data.png"]
    site.requests.clear()

    stands.fetch()

    assert stands.file("stand/1030010010", "data.atlas").read_bytes() == b"\ndata.png\nsize: 2048,2048\n"


def test_an_atlas_page_that_is_not_the_same_image_is_passed_over(stands: Stands, site: FakeShinyColorsDB):
    site.card(1, "1030010010", f"【ナチュラルモード】{MANO}", "P_SR")
    stand = "spine/idols/stand/1030010010/"
    site.files[f"{stand}data.atlas"] = b"\ndate.png\nsize: 2048,2048\n"
    site.files[f"{stand}date.png"] = PNG + b" a different image"

    code, _, err = stands.fetch()

    assert code == 0, err
    assert "stand/1030010010" in err
    assert stands.outfits() == ["stand_costume/1030010010"]


def test_when_shinycolorsdb_cannot_be_reached_what_was_fetched_before_stays(
    stands: Stands, site: FakeShinyColorsDB
):
    site.card(1, "1030010010", f"【ナチュラルモード】{MANO}", "P_SR")
    stands.fetch()
    site.down = True

    code, _, err = stands.fetch()

    assert code == 2
    assert "ShinyColorsDB" in err
    assert stands.outfits() == ["stand/1030010010", "stand_costume/1030010010"]


def test_what_was_fetched_before_shinycolorsdb_broke_off_is_listed(stands: Stands, site: FakeShinyColorsDB):
    site.card(1, "1030010010", f"【ナチュラルモード】{MANO}", "P_SR")
    site.card(1, "1030010020", f"【ぐうぜんBOOKS】{MANO}", "P_SR")
    handle = site.handle

    def break_off(request: httpx.Request) -> httpx.Response:
        if "1030010020" in str(request.url):
            raise httpx.ReadTimeout("timeout", request=request)
        return handle(request)

    site.handle = break_off  # type: ignore[method-assign]

    code, _, _ = stands.fetch()

    assert code == 2
    assert stands.outfits() == ["stand/1030010010", "stand_costume/1030010010"]


def test_a_source_seeded_from_an_old_mirror_is_kept_and_added_to(
    stands: Stands, site: FakeShinyColorsDB
):
    seeded = stands.file("stand/1030010010", "")
    seeded.mkdir(parents=True)
    for name, content in (("data.json", b"{}"), ("data.atlas", b"data.png"), ("data.png", PNG)):
        (seeded / name).write_bytes(content)
    (stands.build / "source" / "spine_manifest.json").write_text(json.dumps([
        {"path": "spine/idols/stand/1030010010/", "category": "stand", "idolId": 1, "idolName": MANO,
         "enzaId": "1030010010", "dressName": f"【ナチュラルモード】{MANO}", "dressType": "P_SR"},
        {"path": "spine/idols/cb/1030010010/", "category": "cb", "idolId": 1, "idolName": MANO,
         "enzaId": "1030010010", "dressName": f"【ナチュラルモード】{MANO}", "dressType": "P_SR"},
    ], ensure_ascii=False), encoding="utf-8")
    site.card(1, "1030010010", f"【ナチュラルモード】{MANO}", "P_SR", categories=("stand",))
    site.card(1, "1030010020", f"【ぐうぜんBOOKS】{MANO}", "P_SR", categories=("stand",))

    stands.fetch()

    assert not any("1030010010" in url for url in site.requests if "cf-static" in url)
    assert stands.file("stand/1030010010", "data.png").read_bytes() == PNG
    assert stands.outfits() == ["stand/1030010010", "stand/1030010020"]


def test_with_a_fresh_game_catalog_its_cards_and_costumes_with_stands_are_fetched(
    stands: Stands, site: FakeShinyColorsDB, tmp_path: Path
):
    # Fetched from ShinyColorsDB before: a swimsuit of the series the game numbers 1.
    site.card(1, "3000010010", f"【シャイニーサマー】{MANO}", "Mizugi", categories=("stand_costume",))
    stands.fetch()
    for category, enza_id in (
        ("stand", "1040010010"), ("stand_costume", "1040010010"), ("stand_costume", "3000010020"), ("stand", "3000010030"),
    ):
        site.outfit(category, enza_id)
    game = (
        GameCatalogFile(tmp_path / "game.json")
        .card(1, "1040010010", "【ほわっとスマイル】櫻木 真乃")
        .costume(1, "3000010010", "【シャイニーサマー（水着）】櫻木 真乃", group="1")
        .costume(1, "3000010020", "【シャイニーサマー2】櫻木 真乃", group="1")
        .costume(1, "3000010030", "【はじめての衣装】櫻木 真乃", group="99")
        .costume(4, "3000040010", "【シャイニーサマー】月岡 恋鐘", group="1")  # Kogane has no idol
        .stand("1040010010", "stand", "stand_costume")
        .stand("3000010010", "stand_costume")
        .stand("3000010020", "stand_costume")
        .stand("3000010030", "stand")
        .stand("3000040010", "stand")
        .write()
    )
    site.requests.clear()

    code, out, err = stands.fetch("--game-catalog", str(game))

    assert code == 0, err
    assert stands.manifest() == {
        "stand_costume/3000010010": (f"【シャイニーサマー】{MANO}", "Mizugi"),  # as it was
        "stand/1040010010": (f"【ほわっとスマイル】{MANO}", "P_SSR"),
        "stand_costume/1040010010": (f"【ほわっとスマイル】{MANO}", "P_SSR"),
        "stand_costume/3000010020": (f"【シャイニーサマー2】{MANO}", "Mizugi"),  # its series'
        "stand/3000010030": (f"【はじめての衣装】{MANO}", "Special"),
    }
    # Only the stands the game's asset server has are asked for.
    assert not [url for url in site.requests if "stand/3000010020" in url or "costume/3000010030" in url]
    assert "卡牌和衣装先取自游戏目录" in out


def test_with_a_fresh_game_catalog_shinycolorsdbs_api_failing_is_only_noted(
    stands: Stands, site: FakeShinyColorsDB, tmp_path: Path
):
    site.outfit("stand", "1040010010")
    game = (
        GameCatalogFile(tmp_path / "game.json")
        .card(1, "1040010010", "【ほわっとスマイル】櫻木 真乃")
        .stand("1040010010", "stand")
        .write()
    )
    handle = site.handle

    def api_down(request: httpx.Request) -> httpx.Response:
        if "dresslist" in str(request.url):
            raise httpx.ConnectError("down", request=request)
        return handle(request)

    site.handle = api_down  # type: ignore[method-assign]

    code, _, err = stands.fetch("--game-catalog", str(game))

    assert code == 0, err
    assert "这次没能问 ShinyColorsDB" in err
    assert stands.outfits() == ["stand/1040010010"]


def test_when_nothing_was_ever_fetched_and_shinycolorsdb_cannot_be_reached_there_is_nothing_to_list(
    stands: Stands, site: FakeShinyColorsDB, admin: Admin, characters: CharacterConfig
):
    site.down = True

    code, _, _ = stands.fetch()

    assert code == 2
    err = admin.fails("stand", "outfits", "--build", str(stands.build), "--characters", str(characters.path))
    assert "eidolon stand fetch" in err
