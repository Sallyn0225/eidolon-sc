"""The music under a letter (GLOSSARY.md「信」), and putting it where browsers hear it:
`eidolon letter-music upload`.

The music is the deployer's and may not go in the repository; what is in it is the list
beside the character configuration (`letter_music.toml`): for each occasion, the file the
deployer has it in, the second its climax starts at, if it has one, that the signature is
timed to fall on; the second it fades out at after that, if not at its end; and, for a
piece too short for the letter, the stretch played over again until the climax falls on the
signature or after. Each file goes up from the deployer's directory as
`letters/music/<occasion><suffix>` in the stands' bucket, and browsers download it from the
stands' address, as they do the stands; one not uploaded is not found there, and the letter
is read without music. A file the list names that the directory lacks is reported and the
rest uploaded; one the bucket already has as it is (its ETag is the file's MD5) is not
uploaded again. Its address being the same whatever it is, it is checked every time it is
downloaded.

Without the list, no letter has music; one broken keeps the backend from starting."""

import hashlib
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from eidolon.letter_prompt import OCCASIONS, Occasion
from eidolon.s3 import Bucket

LETTER_MUSIC_FILE = "letter_music.toml"
"""The list's name, in the directory of the character configuration."""
PREFIX = "letters/music/"
MUSIC_CACHE = "public, no-cache"
"""Its address is the occasion's, whatever piece the deployer puts there: a browser asks
whether it changed, and downloads it again only if it did."""

CONTENT_TYPES = {
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
    ".aac": "audio/aac",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
}


class LetterMusicError(RuntimeError):
    """The list is broken."""


@dataclass(frozen=True)
class Music:
    """The piece under a letter on one occasion: the deployer's file, in seconds of it the
    climax, if any, the fade after it, if not at its end, and the stretch played over again,
    if any (before the climax)."""

    occasion: Occasion
    file: str
    climax: float | None = None
    fade: float | None = None
    loop: tuple[float, float] | None = None

    @property
    def suffix(self) -> str:
        """The file's suffix, in lower case: what kind of audio it is (`CONTENT_TYPES`)."""
        return Path(self.file).suffix.lower()

    @property
    def key(self) -> str:
        """Where it is in the bucket."""
        return f"{PREFIX}{self.occasion}{self.suffix}"

    def shown(self, assets_url: str) -> dict:
        """As the browser is told it, with the stands' address."""
        return {
            "url": f"{assets_url}/{self.key}",
            "climax": self.climax,
            "fade": self.fade,
            "loop": list(self.loop) if self.loop else None,
        }


def letter_music_path(characters_path: Path) -> Path:
    """Where the list is: beside the character configuration."""
    return characters_path.parent / LETTER_MUSIC_FILE


def load_letter_music(path: Path) -> dict[Occasion, Music]:
    """The music of each occasion the list at `path` has; none without the list. Raises
    LetterMusicError if it is broken."""
    try:
        config = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as e:
        raise LetterMusicError(f"信的配乐清单 {path} 格式有误：{e}") from None
    music: dict[Occasion, Music] = {}
    for occasion, entry in config.items():
        if occasion not in OCCASIONS:
            raise LetterMusicError(
                f"信的配乐清单 {path} 里的 [{occasion}] 不是场合，应当是 {'、'.join(OCCASIONS)} 之一"
            )
        music[occasion] = _parse(path, occasion, entry)
    return music


def _parse(path: Path, occasion: Occasion, entry: object) -> Music:
    def wrong(why: str) -> LetterMusicError:
        return LetterMusicError(f"信的配乐清单 {path} 里的 [{occasion}] {why}")

    if not isinstance(entry, dict):
        raise wrong("应当是一段")
    file = entry.get("file")
    if not isinstance(file, str) or not file.strip():
        raise wrong("缺 file（部署者目录里这首的文件名）")
    if Path(file).suffix.lower() not in CONTENT_TYPES:
        raise wrong(f"的 file 应当是 {'、'.join(CONTENT_TYPES)} 之一")
    unknown = set(entry) - {"file", "climax", "fade", "loop"}
    if unknown:
        raise wrong(f"里有不认识的项：{'、'.join(sorted(unknown))}")
    climax, fade = (_seconds(entry.get(name), wrong, name) for name in ("climax", "fade"))
    loop = entry.get("loop")
    if loop is not None:
        if (
            not isinstance(loop, list)
            or len(loop) != 2
            or not all(isinstance(s, int | float) and not isinstance(s, bool) for s in loop)
            or not 0 <= loop[0] < loop[1]
        ):
            raise wrong("的 loop 应当是 [起点, 终点] 两个秒数，起点在前")
        if climax is None or climax < loop[1]:
            raise wrong("有 loop 时，climax 应当在循环段之后")
    if fade is not None and (climax is None or fade <= climax):
        raise wrong("的 fade 应当在 climax 之后（没有高潮的不写 fade）")
    return Music(occasion, file, climax, fade, (float(loop[0]), float(loop[1])) if loop else None)


def _seconds(value: object, wrong, name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float) or value < 0:
        raise wrong(f"的 {name} 应当是秒数")
    return float(value)


def music_of(occasions: tuple[Occasion, ...], music: Mapping[Occasion, Music]) -> Music | None:
    """The music under a letter on `occasions`: of the first, in `OCCASIONS` order, that the
    list has."""
    return next((music[o] for o in OCCASIONS if o in occasions and o in music), None)


@dataclass
class LetterMusicReport:
    uploaded: list[Occasion] = field(default_factory=list)
    uploaded_bytes: int = 0
    unchanged: int = 0
    missing: list[str] = field(default_factory=list)
    """Files the list names that the directory lacks, so were not uploaded."""


async def upload_letter_music(
    directory: Path, music: Mapping[Occasion, Music], bucket: Bucket
) -> LetterMusicReport:
    """Upload each file `music` names, from `directory`, to `bucket`, one after another (a
    few large files). Raises S3Error if the bucket fails, having uploaded what it could
    before; running it again picks up from there."""
    report = LetterMusicReport()
    etags = await bucket.etags(PREFIX)
    for each in music.values():
        try:
            body = (directory / each.file).read_bytes()
        except FileNotFoundError:
            report.missing.append(each.file)
            continue
        if etags.get(each.key) == hashlib.md5(body).hexdigest():
            report.unchanged += 1
            continue
        await bucket.put(each.key, body, CONTENT_TYPES[each.suffix], MUSIC_CACHE)
        report.uploaded.append(each.occasion)
        report.uploaded_bytes += len(body)
    return report
