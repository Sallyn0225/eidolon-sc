"""Fetching the stands from ShinyColorsDB (ADR-0011): `eidolon stand fetch`.

For every character with an `idol_id`, ShinyColorsDB's API is asked for her dresses each
time (new cards come out every week or two), and the files of their everyday clothes
(`stand`) and stage costumes (`stand_costume`) that the source in the build directory
lacks are downloaded from its CDN, as they are: about half the textures are WebP under a
`.png` name, which browsers read all the same. An outfit's files never change, so one
already fetched is not asked for again. A few atlases name their texture page something
other than `data.png` (`date.png`), a slip under which the CDN serves the identical image;
those are pointed back at `data.png`, the name the texture is kept and served under, so
that the browser and the thumbnail renderer find it.

The source's `spine_manifest.json` (laid out as the old Spine mirror's, which can seed
it) lists every outfit fetched and only ever grows: a card the API stops listing, or
leaves out of an answer once, keeps its place in the outfit picker. An outfit the API
lists without a place on the CDN, or whose files the CDN does not have or sends broken,
is left out and reported, and asked for again next time. When ShinyColorsDB cannot be
reached, or answers unlike it used to, what was fetched until then is kept and listed.

A file the CDN lacks is asked of the game's asset server (`Mirror.stand_file`), so is an
outfit the API lists without a place: the server keeps every outfit where the CDN would,
`spine/idols/{category}/{enza_id}/`.

Given the game's own listing (`game_catalog`, ADR-0034), the dresses are its instead of
the API's: every card and costume with a stand on the game's asset server, under the
name and kind the manifest already gives it, if it has one.
"""

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from eidolon.characters import Character
from eidolon.game_catalog import GameCatalog
from eidolon.mirror import Dress, Mirror, MirrorError
from eidolon.stand_outfits import (
    CATEGORIES,
    MANIFEST,
    OUTFIT_FILES,
    is_webp,
    outfit_directory,
    outfit_path,
    read_manifest,
    source_directory,
    write_atomically,
    write_json,
)

log = logging.getLogger(__name__)


@dataclass
class FetchReport:
    fetched: list[str] = field(default_factory=list)
    """The outfits downloaded this time, e.g. `stand/1030010010`."""
    fetched_bytes: int = 0
    skipped: list[str] = field(default_factory=list)
    """Why outfits ShinyColorsDB lists were left out this time."""
    error: str | None = None
    """Why ShinyColorsDB could not be asked for the rest, if it could not."""


async def fetch_stands(
    build: Path, characters: Iterable[Character], mirror: Mirror, game: GameCatalog | None = None
) -> FetchReport:
    """Fetch the stands of each character's dresses that the source lacks: the dresses
    `game` lists, if given, or else those ShinyColorsDB's API does."""
    source = source_directory(build)
    manifest = read_manifest(source)
    entries = {entry.get("path"): entry for entry in manifest or []}
    known = {
        str(entry["enzaId"]): (str(entry.get("dressName", "")), str(entry.get("dressType", "")))
        for entry in manifest or []
        if entry.get("enzaId")
    }
    report = FetchReport()
    try:
        for character in characters:
            if character.idol_id is None:
                continue
            dresses = (
                game.dresses(character.idol_id, known)
                if game is not None
                else await mirror.dresses(character.idol_id)
            )
            for dress in dresses:
                for category in CATEGORIES:
                    if category not in dress.stands:
                        continue
                    outfit_id = f"{category}/{dress.enza_id}"
                    cdn_path = dress.stands[category] or f"spine/idols/{outfit_id}/"
                    if await _fetch_outfit(mirror, source, outfit_id, cdn_path, dress, report):
                        entries[outfit_path(outfit_id)] = {
                            "path": outfit_path(outfit_id),
                            "category": category,
                            "idolId": character.idol_id,
                            "idolName": character.name,
                            "enzaId": dress.enza_id,
                            "dressName": dress.name,
                            "dressType": dress.type,
                        }
    except MirrorError as e:
        report.error = str(e)
    finally:
        if manifest is not None or entries:  # having fetched nothing ever is not an empty source
            write_json(source / MANIFEST, [entries[path] for path in sorted(entries, key=str)])
    return report


async def _fetch_outfit(
    mirror: Mirror, source: Path, outfit_id: str, cdn_path: str, dress: Dress, report: FetchReport
) -> bool:
    """Whether the outfit's files are all in the source, having fetched those it lacked
    from `cdn_path` on the CDN."""
    directory = outfit_directory(source, outfit_id)
    downloaded = 0
    for name in OUTFIT_FILES:
        target = directory / name
        if target.is_file() and _looks_valid(name, _start_of(target)):
            continue
        content = await mirror.stand_file(f"{cdn_path}{name}")
        if content is None or not _looks_valid(name, content):
            problem = "没有" if content is None else "发来的不像是"
            report.skipped.append(
                f"ShinyColorsDB 和官方 CDN {problem} {outfit_id}（{dress.name}）的 {name}，下次同步再试"
            )
            return False
        write_atomically(target, content)
        downloaded += len(content)
    if not await _point_atlas_at_its_texture(mirror, directory, cdn_path, outfit_id, dress.name, report):
        return False
    if downloaded:
        log.info("拉取了 %s（%s）", outfit_id, dress.name)
        report.fetched.append(outfit_id)
        report.fetched_bytes += downloaded
    return True


def _start_of(path: Path) -> bytes:
    with path.open("rb") as file:
        return file.read(64)


async def _point_atlas_at_its_texture(
    mirror: Mirror, directory: Path, cdn_path: str, outfit_id: str, dress_name: str, report: FetchReport
) -> bool:
    """Rewrite the outfit's atlas so the page it names is `data.png`, the name its texture is
    fetched and uploaded under, when ShinyColorsDB names it something else. A few of its
    atlases say `date.png` — a slip, under which the CDN serves the identical image — which
    would otherwise leave the browser and the thumbnail renderer asking for a file that is
    never fetched, and an outfit shown with no texture at all. A named page that is not that
    same image is left as it is, and the outfit is passed over until it is."""
    atlas = directory / "data.atlas"
    try:
        text = atlas.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return True
    lines = text.splitlines(keepends=True)
    named = {line.strip() for index, line in enumerate(lines) if _names_a_page(lines, index)}
    renamed = sorted(named - {"data.png"})
    if not renamed:
        return True
    texture = (directory / "data.png").read_bytes()
    for page in renamed:
        if await mirror.stand_file(f"{cdn_path}{page}") != texture:
            report.skipped.append(
                f"ShinyColorsDB 的 {outfit_id}（{dress_name}）图集里的贴图页 {page} 和 data.png 对不上，"
                "下次同步再试"
            )
            return False
    for index, line in enumerate(lines):
        if _names_a_page(lines, index) and line.strip() in renamed:
            lines[index] = line.replace(line.strip(), "data.png", 1)
    write_atomically(atlas, "".join(lines).encode("utf-8"))
    log.info("把 %s（%s）图集里的贴图页 %s 指回 data.png", outfit_id, dress_name, "、".join(renamed))
    return True


def _names_a_page(lines: list[str], index: int) -> bool:
    """Whether a line of a spine atlas names a texture page (the line before its `size:`
    header) rather than a region."""
    name = lines[index].strip()
    if not name or ":" in name:
        return False
    following = next((later.strip() for later in lines[index + 1 :] if later.strip()), "")
    return following.startswith("size:")


def _looks_valid(name: str, content: bytes) -> bool:
    """Whether the start of a file is what its name says, and not an error page."""
    if name.endswith(".json"):
        return content.lstrip()[:1] == b"{"
    if name.endswith(".png"):
        return content[:8] == b"\x89PNG\r\n\x1a\n" or is_webp(content)
    return bool(content.strip()) and not content.lstrip().startswith(b"<")
