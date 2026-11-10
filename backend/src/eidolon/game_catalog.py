"""What the game itself lists, as `npm run game:catalog` saved it from a logged-in game
(ADR-0034): every idol's cards and the episodes on them, the costumes, which outfits
have stands on the game's asset server, and the events with their names.

The story sync and the stand fetch take their cards, episodes and dresses from here
instead of ShinyColorsDB's API while the catalog is fresh (`FRESH_FOR`), so that new
cards keep coming in with their real names if the mirror stops: the files themselves
are still asked of the mirror first, then of the game's asset server (ADR-0032).

The game writes a name with a space between family and given name (【ほわっとスマイル】
櫻木 真乃); ShinyColorsDB, SCTranslationData's directories and the corpus run them
together, so names are read without whitespace after the 【】. A card's episodes are
looked up a few cards at a time (newest first), so a card listed without them yet is
left out until they are; one with no episodes at all is listed with none.

A dress already in the stands' manifest keeps the name and kind it has there. A new
costume takes the kind ShinyColorsDB gave the costumes of its series (the game's
`group`), which the game does not say itself, or `Special`, as most are.
"""

import json
import re
from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from eidolon.clock import utc_now
from eidolon.mirror import Card, CardEpisode, Dress

FRESH_FOR = timedelta(days=3)
"""How old the catalog may be and still be used; `game:catalog` runs before every sync,
so an older one means it has been failing (a lapsed login, maintenance)."""
VERSION = 1
CARD_PREFIX = "game/"
"""Before a card's enzaId in the story sync's cache, apart from ShinyColorsDB's UUIDs."""
STAND_CATEGORIES = ("stand", "stand_costume")
_RARITIES = {1: "N", 2: "R", 3: "SR", 4: "SSR", 5: "UR"}
_DEFAULT_COSTUME_KIND = "Special"
_NAMED = re.compile(r"(?P<card>【[^】]*】)?(?P<idol>.*)", re.DOTALL)
_EVENT_SCRIPT = re.compile(r"4001(?P<event>\d{3})\d{2}")


class GameCatalogError(RuntimeError):
    """The catalog file is not as `game:catalog` writes it."""


def shinycolorsdb_name(name: str) -> str:
    """A card's or costume's name as ShinyColorsDB writes it: no whitespace after the 【】."""
    match = _NAMED.fullmatch(name.strip())
    assert match is not None  # the pattern matches anything
    return (match["card"] or "") + re.sub(r"\s+", "", match["idol"])


@dataclass(frozen=True)
class _GameCard:
    id: str
    idol: int
    name: str
    type: str
    hash: str
    event_count: int
    episodes: tuple[CardEpisode, ...] | None
    """None until they are looked up."""


@dataclass(frozen=True)
class _Costume:
    id: str
    idol: int
    name: str
    group: str


class GameCatalog:
    def __init__(self, data: Mapping[str, Any]) -> None:
        try:
            if data.get("version") != VERSION:
                raise GameCatalogError(f"版本是 {data.get('version')!r}，这里只认 {VERSION}")
            self.fetched_at = datetime.fromisoformat(data["fetchedAt"])
            if self.fetched_at.tzinfo is None:
                raise GameCatalogError("fetchedAt 没有时区")
            self._idols = sorted({int(c["id"]) for c in data["characters"]})
            self._cards = [_card(card) for card in data["cards"]]
            self._costumes = [
                _Costume(str(c["id"]), int(c["characterId"]), shinycolorsdb_name(c["name"]), str(c.get("group") or ""))
                for c in data["costumes"]
            ]
            stands = data.get("stands")
            self._stands: dict[str, set[str]] | None = (
                None if stands is None else {str(i): set(categories) for i, categories in stands.items()}
            )
            self._events = [
                (str(event["name"]), [str(e["id"]) for e in event["episodes"]]) for event in data["events"]
            ]
        except GameCatalogError:
            raise
        except (KeyError, TypeError, ValueError, AttributeError) as e:
            raise GameCatalogError(f"格式和预期不同（{e!r}）") from e
        self._by_uuid = {CARD_PREFIX + card.id: card for card in self._cards}

    @classmethod
    def load(cls, path: Path) -> "GameCatalog | None":
        """The catalog at `path`; None if there is none. Raises GameCatalogError."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except OSError as e:  # not allowed to read it, a directory
            raise GameCatalogError(f"读不了 {path}（{e}）") from e
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise GameCatalogError(f"{path} 不是 JSON（{e}）") from e
        if not isinstance(data, dict):
            raise GameCatalogError(f"{path} 应是一个对象")
        try:
            return cls(data)
        except GameCatalogError as e:
            raise GameCatalogError(f"{path}：{e}") from None

    def age(self) -> timedelta:
        return utc_now() - self.fetched_at

    def is_fresh(self) -> bool:
        return self.age() <= FRESH_FOR

    @property
    def cards_pending(self) -> int:
        """Cards with episodes that have not been looked up yet, so are left out."""
        return sum(1 for card in self._cards if card.episodes is None and card.event_count)

    # As ShinyColorsDB's API answers, for the story sync.

    async def idols(self) -> list[int]:
        return list(self._idols)

    async def cards(self, idol_id: int) -> list[Card]:
        return [
            Card(CARD_PREFIX + card.id, card.name, card.type, f"{card.hash}/{len(card.episodes or ())}")
            for card in self._cards
            if card.idol == idol_id and (card.episodes is not None or not card.event_count)
        ]

    async def episodes(self, card: Card) -> list[CardEpisode]:
        found = self._by_uuid.get(card.uuid)
        return sorted(found.episodes or (), key=lambda e: e.script) if found else []

    def event_names(self) -> dict[int, str]:
        """Each event's name, by its number in its scripts' (`400109901` is event 099)."""
        names: dict[int, str] = {}
        for name, episodes in self._events:
            numbers = {int(m["event"]) for e in episodes if (m := _EVENT_SCRIPT.fullmatch(e))}
            if len(numbers) == 1 and name.strip():
                names[numbers.pop()] = name.strip()
        return names

    # For the stand fetch.

    def dresses(self, idol_id: int, known: Mapping[str, tuple[str, str]]) -> list[Dress]:
        """The idol's cards and costumes that have a stand on the game's asset server,
        each with the stands it has. `known` is the stands' manifest: an enzaId's name
        and kind there, which a dress already fetched keeps."""
        kinds = self._costume_kinds(known)
        dresses: dict[str, Dress] = {}
        cards = [(card.id, card.idol, card.name, card.type) for card in self._cards]
        costumes = [
            (c.id, c.idol, c.name, kinds.get(c.group, _DEFAULT_COSTUME_KIND)) for c in self._costumes
        ]
        for enza_id, idol, name, kind in [*cards, *costumes]:  # a card's own name first
            if idol != idol_id or enza_id in dresses:
                continue
            stands = self._stands_of(enza_id)
            if not stands:
                continue
            name, kind = known.get(enza_id, (name, kind))
            dresses[enza_id] = Dress(enza_id, name, kind, {category: None for category in stands})
        return list(dresses.values())

    def _stands_of(self, enza_id: str) -> list[str]:
        """Which stands the game's asset server has of the card or costume; none when the
        asset map was not read, rather than asking for both of every one every week."""
        stands = (self._stands or {}).get(enza_id, ())
        return [category for category in STAND_CATEGORIES if category in stands]

    def _costume_kinds(self, known: Mapping[str, tuple[str, str]]) -> dict[str, str]:
        """The kind most of each series' costumes have in the manifest."""
        counts: dict[str, Counter[str]] = defaultdict(Counter)
        for costume in self._costumes:
            if costume.group and costume.id in known and known[costume.id][1]:
                counts[costume.group][known[costume.id][1]] += 1
        return {group: count.most_common(1)[0][0] for group, count in counts.items()}


def _card(card: Mapping[str, Any]) -> _GameCard:
    side = {"produce": "P", "support": "S"}[card["kind"]]
    rarity = int(card["rarity"])
    episodes = card.get("episodes")
    return _GameCard(
        id=str(card["id"]),
        idol=int(card["characterId"]),
        name=shinycolorsdb_name(card["name"]),
        type=f"{side}_{_RARITIES.get(rarity, rarity)}",
        hash=str(card.get("hash") or ""),
        event_count=int(card.get("eventCount") or 0),
        episodes=None
        if episodes is None
        else tuple(CardEpisode(f"produce_events/{e['id']}", str(e.get("title") or "")) for e in episodes),
    )
