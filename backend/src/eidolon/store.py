"""Relational storage (SQLite) for users, their sessions, producer profiles, conversations,
their messages and events, her reach-outs, the photos she sent with her replies, and the
calls in them;
memories are kept by `memory`, recent usage by `usage`."""

import hashlib
import json
import secrets
import sqlite3
import uuid
from collections import Counter, deque
from collections.abc import Callable, Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal

from eidolon.affinity import Change
from eidolon.data_access import Database
from eidolon.database import (
    by_name,
    delete_conversation_data,
    delete_user_data,
    tables,
)
from eidolon.delivery_cues import without_cues
from eidolon.producer import Birthday, City, ProducerProfile
from eidolon.reply_format import Segment

Admit = Callable[[sqlite3.Connection, str], None]
"""Run in the write that makes a new user, given their id, to let them sign up: whatever it
raises makes no one (`Store.create_user_signing_in_with`)."""

Role = Literal["user", "character"]
EventKind = Literal["hung_up", "gift", "ended", "unwell"]
PhotoStatus = Literal["pending", "ready", "failed"]
"""A photo being generated, sent, or not sent after all."""
PhotoFailure = Literal["timeout", "service_error", "bad_image", "own_key_failed", "used_up"]
"""Why a photo was not sent: the image service took too long, waiting its turn included;
it failed, or could not be reached; it answered with what is not one picture of the size
asked for; the user's own key to it failed; or the photos of the hour were used up as it
was about to be generated."""

_SCHEMA = """
-- `name` only tells users apart on the admin command line; it need not be unique.
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    consented_at TEXT,
    banned_at TEXT,
    ban_note TEXT
);
-- Only a hash of each session's token is kept; the times are epoch seconds.
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    last_active_at REAL NOT NULL,
    expires_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_by_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS sessions_by_expiry ON sessions(expires_at);
-- A Google or GitHub identity a user signs in with; each belongs to one user only.
CREATE TABLE IF NOT EXISTS sign_in_methods (
    user_id TEXT NOT NULL REFERENCES users(id),
    provider TEXT NOT NULL,
    subject TEXT NOT NULL,
    display_name TEXT NOT NULL,
    email TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (provider, subject)
);
CREATE INDEX IF NOT EXISTS sign_in_methods_by_user ON sign_in_methods(user_id);
CREATE TABLE IF NOT EXISTS producer_profiles (
    user_id TEXT PRIMARY KEY REFERENCES users(id),
    form_of_address TEXT,
    gender TEXT,
    timezone TEXT,
    updated_at TEXT NOT NULL,
    birthday_month INTEGER,
    birthday_day INTEGER,
    -- Where the producer is, as QWeather found it (`producer.City`): NULL for nowhere set.
    city_name TEXT,
    city_adm2 TEXT,
    city_adm1 TEXT,
    city_country TEXT,
    city_latitude REAL,
    city_longitude REAL
);
-- `title` is its conversation title (`titles`), NULL until it is named, if ever.
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    character_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    title TEXT
);
-- A user's conversations, with each character, newest last: listing them, finding the
-- current one, and every join from a user to what is in their conversations.
CREATE INDEX IF NOT EXISTS conversations_by_user
    ON conversations(user_id, character_id, created_at);
-- `hurt` and `out_of_line`, on the user's message of a typed turn (`Typed`), are what the
-- turn hurt her (`affinity.hurt`) and whether it was out of line; NULL for a turn of a call, or
-- one recorded before typed turns were counted.
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    role TEXT NOT NULL CHECK (role IN ('user', 'character')),
    text TEXT,
    ja TEXT,
    zh TEXT,
    segments TEXT,
    created_at TEXT NOT NULL,
    affinity TEXT,
    hurt REAL,
    out_of_line INTEGER
);
CREATE INDEX IF NOT EXISTS messages_by_conversation ON messages(conversation_id, id);
CREATE TABLE IF NOT EXISTS conversation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    kind TEXT NOT NULL,
    created_at TEXT NOT NULL,
    affinity TEXT,
    gift_id TEXT,
    liked INTEGER NOT NULL DEFAULT 0,
    first_day TEXT,
    days_ago INTEGER
);
CREATE INDEX IF NOT EXISTS conversation_events_by_conversation
    ON conversation_events(conversation_id, created_at);
-- A photo she sent with a reply (GLOSSARY.md「照片」, ADR-0024), one at most to a reply: the
-- photo tag she wrote for it, as she wrote it; whether it is being generated, was sent or was
-- not, and why not (`reason`); and once sent the picture itself, a WebP, read only on its own.
CREATE TABLE IF NOT EXISTS photos (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    message_id INTEGER NOT NULL UNIQUE REFERENCES messages(id),
    tag TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'ready', 'failed')),
    reason TEXT,
    image BLOB,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS photos_by_conversation ON photos(conversation_id);
-- Each call that connected in a conversation (GLOSSARY.md「接通」), for stats alone: when it
-- connected and how long it lasted once it had, as its activity record says; nothing of what
-- was said. Not in the conversation's record: she knows nothing of it (ADR-0021).
CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    connected_at TEXT NOT NULL,
    duration_s REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS calls_by_conversation ON calls(conversation_id);
-- What she said first in a conversation (GLOSSARY.md「搭话」), as the model wrote it, delivery
-- cues and all, as her replies are kept; whether the user has seen it (GLOSSARY.md「没看过的
-- 搭话」); and the id of its activity record, which outlives neither the user's name on it nor
-- 90 days, so no reference.
CREATE TABLE IF NOT EXISTS reach_outs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    ja TEXT NOT NULL,
    zh TEXT NOT NULL,
    segments TEXT NOT NULL,
    created_at TEXT NOT NULL,
    seen INTEGER NOT NULL DEFAULT 0,
    record_id INTEGER
);
CREATE INDEX IF NOT EXISTS reach_outs_by_conversation ON reach_outs(conversation_id, created_at);
-- The identities banned users signed in with, kept when those users were deleted so that
-- deleting is not unbanning; only a keyed hash of each (`accounts.identity_hash`), no one's.
CREATE TABLE IF NOT EXISTS banned_identities (
    identity_hash TEXT PRIMARY KEY,
    added_at TEXT NOT NULL
);
"""

_CURRENT = (
    "c.rowid = (SELECT n.rowid FROM conversations n"
    " WHERE n.user_id = c.user_id AND n.character_id = c.character_id"
    " ORDER BY n.created_at DESC, n.rowid DESC LIMIT 1)"
)
"""That the conversation `c` is its user's current one with its character: their newest."""

SESSION_LIFETIME = timedelta(days=30)
"""How long a session lasts after it was last used."""
SESSION_RENEWAL = timedelta(hours=1)
"""How long after its last renewal a session in use is renewed again, rather than on
every request."""


@dataclass(frozen=True)
class User:
    id: str
    name: str
    created_at: str
    consented_at: str | None = None
    """When they agreed to the privacy policy and terms of use; None until they do."""
    banned_at: str | None = None
    ban_note: str | None = None
    """Why they were banned, as the admin who banned them wrote; only admins see it."""


@dataclass(frozen=True)
class Session:
    """A signed-in browser's session. `renewed` says this use renewed it, so the browser's
    cookie should be renewed too."""

    user: User
    renewed: bool


@dataclass(frozen=True)
class SignInMethod:
    """An identity at a provider (Google or GitHub) that signs a user in; `subject` is the
    provider's id for it."""

    provider: str
    subject: str
    display_name: str
    email: str | None
    created_at: str


class IdentityTaken(Exception):
    """The identity already belongs to a user."""


class LastSignInMethod(Exception):
    """Removing it would leave the user no way to sign in."""


class ConversationEnded(Exception):
    """She has ended the conversation (GLOSSARY.md「已结束的对话」): nothing more is recorded
    in it."""


class ReachOutRefused(Exception):
    """What she said first is not recorded (GLOSSARY.md「搭话」): the user and she were in touch
    as she was thinking it, or it is no longer the conversation she was to say it in."""


class IsCurrent(Exception):
    """It is her current conversation (GLOSSARY.md「当前对话」), which is not deleted."""


class NotFound(LookupError):
    pass


@dataclass(frozen=True)
class Conversation:
    id: str
    user_id: str
    character_id: str
    created_at: str
    title: str | None = None
    """Its title (GLOSSARY.md「对话标题」), as it was when read; None until it is named, if
    ever."""


@dataclass(frozen=True)
class Photo:
    """The photo she sent with a reply (GLOSSARY.md「照片」): whether it is being generated, was
    sent or was not, and why not; and the photo tag she wrote for it, which only her prompt
    reads."""

    id: str
    status: PhotoStatus
    reason: PhotoFailure | None
    tag: str

    def shown(self) -> dict:
        """As the browser is told it: not the tag."""
        return {"id": self.id, "status": self.status, "reason": self.reason}


@dataclass(frozen=True)
class NewPhoto:
    """A photo she is sending with the reply being recorded, by its id, and the tag she
    wrote for it."""

    id: str
    tag: str


@dataclass(frozen=True)
class Message:
    """A user's input (`text`) or a character's reply.

    A reply keeps its full Japanese text (`ja`) and Chinese subtitle (`zh`), plus
    the segments that pair each Japanese line with its own subtitle, how the turn
    changed her affinity, if it did (`affinity`), and the photo she sent with it, if any.
    """

    id: int
    role: Role
    text: str | None
    ja: str | None
    zh: str | None
    created_at: str
    segments: list[Segment] = field(default_factory=list)
    affinity: Change | None = None
    photo: Photo | None = None

    @property
    def photo_sent(self) -> bool:
        """Whether she sent a photo with it, and it is out."""
        return self.photo is not None and self.photo.status == "ready"

    @property
    def photo_failed(self) -> bool:
        """Whether she sent a photo with it that was not sent after all."""
        return self.photo is not None and self.photo.status == "failed"

    def without_cues(self) -> "Message":
        """The message as people see it: a reply is kept as the model wrote it, delivery
        cues and all (ADR-0007)."""
        if self.role != "character":
            return self
        return Message(
            self.id, self.role, self.text,
            None if self.ja is None else without_cues(self.ja),
            None if self.zh is None else without_cues(self.zh),
            self.created_at,
            [Segment(without_cues(s.ja), without_cues(s.zh)) for s in self.segments],
            self.affinity,
            self.photo,
        )

    def shown(self) -> dict:
        """The message as the browser is told it: as people see it, with its photo's id,
        status and reason if it has one, no key for it if not."""
        shown = asdict(self.without_cues())
        del shown["photo"]
        return shown | ({"photo": self.photo.shown()} if self.photo else {})


@dataclass(frozen=True)
class Typed:
    """What a typed turn, one taken outside calls, comes to for her ending the conversation
    (GLOSSARY.md「已结束的对话」): how much it hurt her (`affinity.hurt`), and
    whether it was out of line."""

    hurt: float = 0.0
    out_of_line: bool = False


@dataclass(frozen=True)
class ConversationEvent:
    """Something that happened in a conversation that is not a turn (GLOSSARY.md「对话事件」):
    her hanging up on the user (`hung_up`), her ending the conversation (`ended`), after which
    it can only be read, the user giving her a gift (`gift`), which
    one (`gift_id`) and whether she liked it as it was given (`liked`), kept as it was
    should what she likes change, or her being unwell (`unwell`), for the user alone: from
    the first day of her period (`first_day`, ISO), `days_ago` days before the day it was
    recorded on. It can carry how it changed her affinity (`affinity`)."""

    id: int
    kind: EventKind
    created_at: str
    affinity: Change | None = None
    gift_id: str | None = None
    liked: bool = False
    first_day: str | None = None
    days_ago: int | None = None
    type: Literal["event"] = field(default="event", init=False)

    def shown(self) -> dict:
        """As the browser is told it: whether she liked the gift is for her prompt alone;
        which gift, for a gift's only; since when she is unwell, for her being unwell's."""
        hidden = {"liked"} | ({"gift_id"} if self.gift_id is None else set()) | (
            {"first_day", "days_ago"} if self.kind != "unwell" else set()
        )
        return {k: v for k, v in asdict(self).items() if k not in hidden}


@dataclass(frozen=True)
class ReachOut:
    """What she said first in a conversation, the user not talking to her (GLOSSARY.md
    「搭话」): neither a turn nor an event (ADR-0026), but said as she replies, in segments,
    each Japanese with its subtitle, kept as the model wrote them, delivery cues and all."""

    id: int
    ja: str
    zh: str
    segments: list[Segment]
    created_at: str
    type: Literal["reach_out"] = field(default="reach_out", init=False)

    def as_reply(self) -> Message:
        """As those reading only the messages read it: as her reply. Its id is the
        reach-out's, no message's."""
        return Message(
            self.id, "character", None, self.ja, self.zh, self.created_at, self.segments
        )

    def without_cues(self) -> "ReachOut":
        """As people see it."""
        return ReachOut(
            self.id, without_cues(self.ja), without_cues(self.zh),
            [Segment(without_cues(s.ja), without_cues(s.zh)) for s in self.segments],
            self.created_at,
        )

    def shown(self) -> dict:
        """As the browser is told it: as people see it."""
        return asdict(self.without_cues())


Recorded = Message | ConversationEvent | ReachOut
"""What a conversation's record holds."""


def told_her(entry: Recorded) -> bool:
    """Whether she is told of the entry in her prompts: of all but her being unwell, which
    she knows herself, and which is for the user alone."""
    return not (isinstance(entry, ConversationEvent) and entry.kind == "unwell")


@dataclass(frozen=True)
class CurrentConversation:
    """Her current conversation with a user (GLOSSARY.md「当前对话」) as reach-outs go by it:
    whether it has a turn yet; when the user and she were last in touch in it (the last turn
    recorded, or a call that connected ending; None before either), when she last reached out
    in it (None if never), and whether she has ended it."""

    conversation: Conversation
    has_turns: bool
    last_contact: datetime | None
    reached_out_at: datetime | None
    ended: bool


@dataclass(frozen=True)
class InTouch:
    """How a user and a character are in touch, over all their conversations, as moments go
    by it (GLOSSARY.md「朋友圈」): whether they have had a turn; when they were last in touch
    (`read_last_contact`; None before either)."""

    user_id: str
    character_id: str
    has_turns: bool
    last_contact: datetime | None


@dataclass(frozen=True)
class Contact:
    """A turn the user took with a character (the time of their message) or a gift they
    gave her, and whether she liked it as it was given, as stats count them."""

    character_id: str
    kind: Literal["turn", "gift"]
    at: datetime
    liked: bool = False


@dataclass(frozen=True)
class KeptCall:
    """A call the user had with a character that connected, when it did, and how long it
    lasted once it had, in seconds, as stats count them."""

    character_id: str
    connected_at: datetime
    duration_s: float


@dataclass(frozen=True)
class KeptPhoto:
    """The photo she sent with a reply, as kept but for its picture, as a data package carries
    it: `id` is its id where it was exported, a key in the package only."""

    id: str
    tag: str
    status: PhotoStatus
    reason: PhotoFailure | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class KeptMessage:
    """A message as kept, all of it, as a data package carries it (GLOSSARY.md「数据包」): her
    reply as the model wrote it, delivery cues and all (ADR-0007), and for the user's message
    of a typed turn what it came to (`hurt`, `out_of_line`; None as for `Typed`)."""

    role: Role
    text: str | None
    ja: str | None
    zh: str | None
    segments: list[Segment]
    created_at: str
    affinity: Change | None
    hurt: float | None
    out_of_line: bool | None
    photo: KeptPhoto | None = None
    """The photo she sent with the reply, if any."""


@dataclass(frozen=True)
class KeptEvent:
    """A conversation event as kept, as a data package carries it."""

    kind: EventKind
    created_at: str
    affinity: Change | None
    gift_id: str | None
    liked: bool
    first_day: str | None = None
    days_ago: int | None = None


@dataclass(frozen=True)
class ConnectedCall:
    """A call kept in a conversation (`keep_call`), as a data package carries it."""

    connected_at: str
    duration_s: float


@dataclass(frozen=True)
class KeptReachOut:
    """A reach-out as kept, as a data package carries it: as the model wrote it, delivery cues
    and all (ADR-0007); not whether the user has seen it."""

    ja: str
    zh: str
    segments: list[Segment]
    created_at: str


@dataclass(frozen=True)
class WholeConversation:
    """A conversation and everything kept under it, as a data package carries it: its
    messages in their order, its events, the calls kept in it and her reach-outs. `id` is its
    id where it was exported, a key in the package only."""

    id: int | str
    character_id: str
    created_at: str
    title: str | None
    messages: list[KeptMessage]
    events: list[KeptEvent]
    calls: list[ConnectedCall]
    reach_outs: list[KeptReachOut]


class Store:
    """Users, their sessions, sign-in methods, producer profiles and bans, and their
    conversations with all that is kept in them, read and written through the data access
    layer, `db` (ADR-0028)."""

    def __init__(self, db: Database) -> None:
        self._db = db
        db.prepare(_open)
        self._taking_turns: Counter[str] = Counter()
        """How many text turns are under way in each conversation: counted on the event loop
        only, looked at anywhere (`is_taking_turn`)."""

    async def create_user(self, name: str) -> User:
        user = User(uuid.uuid4().hex, name, _now())
        await self._db.write(_insert_user, user)
        return user

    async def list_users(self) -> list[User]:
        return await self._db.read(_users)

    async def get_user(self, user_id: str) -> User:
        user = await self._db.read(_user, user_id)
        if user is None:
            raise NotFound(f"用户 {user_id} 不存在")
        return user

    async def first_user_named(self, name: str) -> User | None:
        """The earliest user with this name, if any; names are not unique."""
        return await self._db.read(_first_user_named, name)

    async def find_users(
        self,
        query: str,
        offset: int,
        limit: int,
        ranking: tuple[str, list[Any]] | None = None,
    ) -> tuple[list[User], int]:
        """A page of the users whose id starts with `query`, or whose name, or the name or
        email of an identity they sign in with, has it in it, in any case; all users for
        an empty query. Newest first, or highest first by `ranking`, an SQL expression
        over a row of `users` with its parameters (as `ActivityLog.ranking`), then newest;
        with how many there are in all."""
        return await self._db.read(_find_users, query, offset, limit, ranking)

    async def last_active(self, user_ids: list[str]) -> dict[str, datetime]:
        """When each of the users, of those signed in anywhere, was last active: the
        latest renewal of any of their sessions."""
        return await self._db.read(_last_active, user_ids)

    async def set_banned(
        self, user_id: str, banned_at: datetime | None, note: str | None = None
    ) -> None:
        """Ban the user as of `banned_at`, with a note only admins see, signing them out
        everywhere; None lifts the ban, and the note with it. Raises NotFound for no such
        user."""
        await self._db.write(_set_banned, user_id, banned_at, note)

    async def active_users(self, user_ids: set[str]) -> set[str]:
        """Those of the users who still exist and are not banned."""
        return await self._db.read(_active_users, user_ids) if user_ids else set()

    async def consent(self, user_id: str, now: datetime) -> None:
        """Record that the user agreed to the privacy policy and terms of use."""
        await self._db.write(_consent, user_id, now)

    async def user_signing_in_with(self, provider: str, subject: str) -> str | None:
        """The id of the user this identity belongs to, if any."""
        return await self._db.read(_user_signing_in_with, provider, subject)

    async def create_user_signing_in_with(
        self,
        name: str,
        method: SignInMethod,
        admit: Admit | None = None,
    ) -> User:
        """A new user, whose one sign-in method is `method`, let sign up by `admit` if given.
        Raises IdentityTaken, making no one, if the identity already belongs to someone."""
        user = User(uuid.uuid4().hex, name, _now())
        try:
            await self._db.write(_insert_user_signing_in_with, user, method, admit)
        except sqlite3.IntegrityError:
            raise IdentityTaken from None
        return user

    async def add_sign_in_method(self, user_id: str, method: SignInMethod) -> None:
        """Raises IdentityTaken if the identity already belongs to someone."""
        try:
            await self._db.write(_insert_sign_in_method, user_id, method)
        except sqlite3.IntegrityError:
            raise IdentityTaken from None

    async def update_sign_in_method(
        self, provider: str, subject: str, display_name: str, email: str | None
    ) -> None:
        """Keep the name and email the provider now gives for the identity."""
        await self._db.write(_update_sign_in_method, provider, subject, display_name, email)

    async def sign_in_methods(self, user_id: str) -> list[SignInMethod]:
        """In the order they were added."""
        return (await self.sign_in_methods_of([user_id]))[user_id]

    async def sign_in_methods_of(self, user_ids: list[str]) -> dict[str, list[SignInMethod]]:
        """Each of the users' sign-in methods, in the order they were added."""
        return await self._db.read(_sign_in_methods_of, user_ids)

    async def remove_sign_in_method(self, user_id: str, provider: str) -> bool:
        """Remove the user's sign-in method at `provider`; False if they have none there.
        Raises LastSignInMethod, removing nothing, if it is the only one they have."""
        return await self._db.write(_remove_sign_in_method, user_id, provider)

    async def delete_user(self, user_id: str, identities: Sequence[str] = ()) -> None:
        """Delete the user and everything of theirs, for good, all at once (see
        `database.delete_user_data`), first putting `identities`, hashes of the identities
        they signed in with, on the ban list if they are banned; the write-ahead log is
        emptied of the pages as they were soon after (`Database.checkpoint`)."""
        if identities:
            await self._db.write(_ban_identities_if_banned, user_id, identities)
        await self._db.write(delete_user_data, user_id)
        await self._db.checkpoint()

    async def is_banned_identity(self, identity_hash: str) -> bool:
        """Whether a banned user since deleted signed in with the identity of this hash."""
        return await self._db.read(_is_banned_identity, identity_hash)

    async def create_session(self, user_id: str, now: datetime) -> str:
        """Start a session for the user; returns its token, which is not stored. Every
        session that has expired, whoever's it is, is deleted meanwhile, so that a user who
        does not come back leaves none behind."""
        token = secrets.token_urlsafe(32)
        await self._db.write(_create_session, _hash(token), user_id, now)
        return token

    async def use_session(self, token: str, now: datetime) -> Session | None:
        """The session with this token, renewed for another `SESSION_LIFETIME` if it has
        not been for a while; None if there is none or it has expired. Only read, but
        when it is to be renewed or deleted."""
        token_hash = _hash(token)
        found = await self._db.read(_session, token_hash)
        if found is None:
            return None
        last_active_at, expires_at, user = found
        if expires_at > now.timestamp() and not _renewal_due(last_active_at, now):
            return Session(user, False)
        # Looked at again as it is written: another request may have renewed it meanwhile.
        return await self._db.write(_use_session, token_hash, now)

    async def end_session(self, token: str) -> None:
        await self._db.write(_end_session, _hash(token))

    async def end_sessions(self, user_id: str) -> None:
        """Sign the user out everywhere."""
        await self._db.write(_end_sessions, user_id)

    async def get_profile(self, user_id: str) -> ProducerProfile:
        """The user's producer profile; all defaults until they save one."""
        return await self._db.read(read_profile, user_id)

    async def save_profile(self, user_id: str, profile: ProducerProfile) -> None:
        await self._db.write(write_profile, user_id, profile)

    async def create_conversation(self, user_id: str, character_id: str) -> Conversation:
        conversation = Conversation(uuid.uuid4().hex, user_id, character_id, _now())
        await self._db.write(_insert_conversation, conversation)
        return conversation

    async def get_conversation(self, conversation_id: str) -> Conversation | None:
        return await self._db.read(_conversation, conversation_id)

    async def list_conversations(
        self, user_id: str, character_id: str
    ) -> list[tuple[Conversation, Recorded | None, bool]]:
        """The user's conversations with the character, newest first (the first is her
        current one, GLOSSARY.md「当前对话」), each with the last thing in its record as
        `latest_conversations` gives it, and whether she has ended it; for the past
        conversations panel."""
        return await self._db.read(_list_conversations, user_id, character_id)

    async def name_conversation(self, conversation_id: str, title: str) -> None:
        """Give the conversation its title (GLOSSARY.md「对话标题」), unless it has one: it is
        named once."""
        await self._db.write(_name_conversation, conversation_id, title)

    async def delete_conversation(self, conversation: Conversation) -> None:
        """Delete a past conversation (GLOSSARY.md「历史对话」) and its record, for good, all
        at once; the memories written in it are kept, no longer saying where. Her current one
        is not deleted: `IsCurrent`. See `database.delete_conversation_data`."""
        await self._db.write(_delete_conversation, conversation)

    async def contacts(self, user_id: str) -> list[Contact]:
        """Every turn the user took and gift they gave, in what is left of their
        conversations, as stats count them (GLOSSARY.md「统计」); in no order."""
        return await self._db.read(_contacts, user_id)

    async def kept_calls(self, user_id: str) -> list[KeptCall]:
        """Every call kept in what is left of the user's conversations; in no order."""
        return await self._db.read(_kept_calls, user_id)

    async def first_records(self, user_id: str) -> dict[str, datetime]:
        """When the first thing still in the user's conversations with each character, a
        message, an event or a call kept, was recorded; only those with anything left."""
        return await self._db.read(_first_records, user_id)

    async def latest_conversations(
        self, user_id: str
    ) -> list[tuple[Conversation, Recorded | None, bool]]:
        """Each character's newest conversation with the user, the last thing in its record,
        a message, an event or a reach-out, as `record` orders them (None while it has none),
        and whether it has a reach-out the user has not seen (GLOSSARY.md「没看过的搭话」); for
        the conversation list."""
        return await self._db.read(_latest_conversations, user_id)

    async def finish_photo(
        self, photo_id: str, image: bytes | None, reason: PhotoFailure | None
    ) -> bool:
        """Keep how the photo being generated came out: sent, as `image`, or not, for
        `reason`. False, keeping nothing, if it is no longer there, its conversation
        deleted meanwhile, say, or no longer being generated."""
        return await self._db.write(_finish_photo, photo_id, image, reason)

    def give_up_photos(self, reason: PhotoFailure) -> int:
        """Keep every photo still being generated as not sent, for `reason`: nothing is
        generating it any more, the server having stopped meanwhile. How many there were.
        Waited for here, blocking, as the server starts."""
        return self._db.prepare(_give_up_photos, reason)

    async def photo(self, photo_id: str, user_id: str) -> Photo | None:
        """The photo, if it is in one of the user's conversations; None if not."""
        return await self._db.read(_photo, photo_id, user_id)

    async def photo_image(self, photo_id: str, user_id: str) -> bytes | None:
        """The picture of the photo, sent, in one of the user's conversations; None if there
        is none such."""
        return await self._db.read(_photo_image, photo_id, user_id)

    async def reply_said(self, conversation_id: str, message_id: int) -> list[Segment] | None:
        """The segments of her reply `message_id`, as the model wrote them, delivery cues and
        all; None unless it is a reply of hers in the conversation."""
        return await self._db.read(_reply_said, conversation_id, message_id)

    async def reach_out_said(
        self, conversation_id: str, reach_out_id: int
    ) -> list[Segment] | None:
        """The segments of her reach-out `reach_out_id`, as the model wrote them; None unless
        it is one in the conversation."""
        return await self._db.read(_reach_out_said, conversation_id, reach_out_id)

    async def hang_up(self, conversation_id: str) -> ConversationEvent:
        """Record that she hung up on the user in the conversation, now (`hung_up`), unless
        she has ended it: then nothing more is recorded, and it is her ending it that is
        returned."""
        return await self._db.write(_hang_up, conversation_id)

    async def ended(self, conversation_id: str) -> ConversationEvent | None:
        """Her ending the conversation (GLOSSARY.md「已结束的对话」), as recorded; None while
        it is not ended."""
        return await self._db.read(read_ended, conversation_id)

    async def typed_turns(self, conversation_id: str, latest: int) -> list[Typed]:
        """What the conversation's `latest` typed turns came to, oldest first; turns of calls,
        and those recorded before typed turns were counted, are not among them."""
        return await self._db.read(_typed_turns, conversation_id, latest)

    async def list_messages(self, conversation_id: str) -> list[Message]:
        """The conversation's messages, each reply with its photo, if any, but not its
        picture."""
        return await self._db.read(_list_messages, conversation_id)

    async def record(self, conversation_id: str) -> list[Recorded]:
        """The conversation's record, as `read_record` reads it."""
        return await self._db.read(read_record, conversation_id)

    async def read_by_user(self, conversation_id: str) -> list[Recorded]:
        """The conversation's record as `record` gives it, read by the user: every reach-out
        in it is seen from now on (GLOSSARY.md「没看过的搭话」); one made after it was read, not.
        Only read, but when one of them was not seen yet."""
        entries, unseen = await self._db.read(_record_and_unseen, conversation_id)
        if unseen is not None:
            await self._db.write(_see_reach_outs, conversation_id, unseen)
        return entries

    async def current_conversations(self) -> list[CurrentConversation]:
        """Every user's current conversation with each character they have one with, as
        reach-outs go by it, but for banned users'; in no order."""
        return await self._db.read(_current_conversations)

    @contextmanager
    def taking_turn(self, conversation_id: str) -> Iterator[None]:
        """A text turn is under way in the conversation, from when it reads the record till
        it is recorded or fails; meanwhile she reaches out in it not (`add_reach_out`). On
        the event loop only."""
        self._taking_turns[conversation_id] += 1
        try:
            yield
        finally:
            self._taking_turns[conversation_id] -= 1
            if not self._taking_turns[conversation_id]:
                del self._taking_turns[conversation_id]

    def is_taking_turn(self, conversation_id: str) -> bool:
        """Whether a text turn is under way in the conversation (`taking_turn`); on a thread
        too, as it only looks."""
        return conversation_id in self._taking_turns

    async def add_reach_out(
        self, conversation_id: str, said: list[Segment], contact: datetime, in_call: bool
    ) -> ReachOut:
        """Record what she said first in the conversation, now, as she thought it after the
        user and she were last in touch at `contact`; not seen yet. It is not,
        `ReachOutRefused`, with a text turn under way in it or a call, as `in_call` says,
        looked at on the event loop as it is handed in; nor unless, looked at again as it
        is recorded, the conversation is still her current one, not ended, last in touch at
        `contact`, without a reach-out since."""
        if in_call or self.is_taking_turn(conversation_id):
            raise ReachOutRefused()
        return await self._db.write(_add_reach_out, conversation_id, said, contact, _now())

    async def reach_out_recorded_as(self, reach_out_id: int, record_id: int | None) -> None:
        """Keep the id of the activity record of the reach-out, once it is written; answered
        already, should the user and she have been in touch since it was recorded."""
        await self._db.write(_reach_out_recorded_as, reach_out_id, record_id)


_USER_COLUMNS = "id, name, created_at, consented_at, banned_at, ban_note"
_MESSAGE_COLUMNS = (
    "m.id AS id, role, text, ja, zh, segments, m.created_at AS created_at, affinity"
)
_MESSAGE_WITH_PHOTO = (
    f"{_MESSAGE_COLUMNS}, p.id AS photo_id, p.status AS photo_status,"
    " p.reason AS photo_reason, p.tag AS photo_tag"
    " FROM messages m LEFT JOIN photos p ON p.message_id = m.id"
)
"""A message with its photo, if any, but not its picture (`_message_with_photo`)."""
_EVENT_COLUMNS = "id, kind, created_at, affinity, gift_id, liked, first_day, days_ago"
_REACH_OUT_COLUMNS = "id, ja, zh, segments, created_at"

def _open(db: sqlite3.Connection) -> None:
    """Make the store's tables, and bring those an older version made up to date."""
    db.executescript(_SCHEMA)
    columns = _columns(db, "users")
    if "name" not in columns:
        # Before access keys, users had no name; the one default user keeps its id as name.
        db.execute("ALTER TABLE users ADD COLUMN name TEXT")
        db.execute("UPDATE users SET name = id")
    _add_missing_columns(db, "users", ("consented_at", "banned_at", "ban_note"), "TEXT")
    _add_missing_columns(db, "producer_profiles", ("birthday_month", "birthday_day"), "INTEGER")
    _add_missing_columns(
        db, "producer_profiles", ("city_name", "city_adm2", "city_adm1", "city_country"), "TEXT"
    )
    _add_missing_columns(db, "producer_profiles", ("city_latitude", "city_longitude"), "REAL")
    _add_missing_columns(db, "messages", ("affinity",), "TEXT")
    _add_missing_columns(db, "messages", ("hurt",), "REAL")
    _add_missing_columns(db, "messages", ("out_of_line",), "INTEGER")
    _add_missing_columns(db, "conversations", ("title",), "TEXT")
    _add_missing_columns(db, "conversation_events", ("gift_id",), "TEXT")
    _add_missing_columns(db, "conversation_events", ("liked",), "INTEGER NOT NULL DEFAULT 0")
    _add_missing_columns(db, "conversation_events", ("first_day",), "TEXT")
    _add_missing_columns(db, "conversation_events", ("days_ago",), "INTEGER")
    # Whether she has responded to an event is whether she has replied since; never kept.
    if "responded" in _columns(db, "conversation_events"):
        db.execute("ALTER TABLE conversation_events DROP COLUMN responded")
    # Access keys are gone (ADR-0006), and with them unique names.
    db.execute("DROP INDEX IF EXISTS users_by_name")
    db.execute("DROP TABLE IF EXISTS access_keys")
    # Users' own keys stay in their browsers (ADR-0017); those kept here, encrypted, go.
    db.execute("DROP TABLE IF EXISTS own_keys")


def _columns(db: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in by_name(db).execute(f"PRAGMA table_info({table})")}


def _add_missing_columns(
    db: sqlite3.Connection, table: str, columns: tuple[str, ...], kind: str
) -> None:
    """Add the columns a table made by an older version lacks; existing rows get NULL."""
    present = _columns(db, table)
    for column in columns:
        if column not in present:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {kind}")


def _insert_user(db: sqlite3.Connection, user: User) -> None:
    db.execute(
        "INSERT INTO users (id, name, created_at) VALUES (?, ?, ?)",
        (user.id, user.name, user.created_at),
    )


def _users(db: sqlite3.Connection) -> list[User]:
    rows = by_name(db).execute(
        f"SELECT {_USER_COLUMNS} FROM users ORDER BY created_at, rowid"
    ).fetchall()
    return [User(**row) for row in rows]


def _user(db: sqlite3.Connection, user_id: str) -> User | None:
    row = by_name(db).execute(
        f"SELECT {_USER_COLUMNS} FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    return User(**row) if row else None


def _first_user_named(db: sqlite3.Connection, name: str) -> User | None:
    row = by_name(db).execute(
        f"SELECT {_USER_COLUMNS} FROM users WHERE name = ? ORDER BY created_at, rowid",
        (name,),
    ).fetchone()
    return User(**row) if row else None


def _find_users(
    db: sqlite3.Connection,
    query: str,
    offset: int,
    limit: int,
    ranking: tuple[str, list[Any]] | None,
) -> tuple[list[User], int]:
    where, params = "", []
    if query := query.strip():
        # Taken as it is: `%` and `_` are not wildcards here.
        escaped = query.replace("!", "!!").replace("%", "!%").replace("_", "!_")
        inside = f"%{escaped}%"
        where = (
            "WHERE id LIKE ? ESCAPE '!' OR name LIKE ? ESCAPE '!' OR EXISTS ("
            "SELECT 1 FROM sign_in_methods m WHERE m.user_id = users.id"
            " AND (m.display_name LIKE ? ESCAPE '!' OR m.email LIKE ? ESCAPE '!'))"
        )
        params = [f"{escaped}%", inside, inside, inside]
    rows = by_name(db).execute(
        f"SELECT {_USER_COLUMNS} FROM users {where}"
        f" ORDER BY {f'{ranking[0]} DESC, ' if ranking else ''}"
        "created_at DESC, rowid DESC LIMIT ? OFFSET ?",
        [*params, *(ranking[1] if ranking else []), limit, offset],
    ).fetchall()
    [(total,)] = db.execute(f"SELECT COUNT(*) FROM users {where}", params)
    return [User(**row) for row in rows], total


def _last_active(db: sqlite3.Connection, user_ids: list[str]) -> dict[str, datetime]:
    rows = db.execute(
        "SELECT user_id, MAX(last_active_at) FROM sessions WHERE user_id IN"
        f" ({','.join('?' * len(user_ids))}) GROUP BY user_id",
        user_ids,
    ).fetchall()
    return {user_id: datetime.fromtimestamp(at, UTC) for user_id, at in rows}


def _set_banned(
    db: sqlite3.Connection, user_id: str, banned_at: datetime | None, note: str | None
) -> None:
    cursor = db.execute(
        "UPDATE users SET banned_at = ?, ban_note = ? WHERE id = ?",
        (banned_at.isoformat() if banned_at else None,
         note if banned_at else None, user_id),
    )
    if cursor.rowcount == 0:
        raise NotFound(f"用户 {user_id} 不存在")
    if banned_at is not None:
        db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))


def _active_users(db: sqlite3.Connection, user_ids: set[str]) -> set[str]:
    return {
        user_id
        for (user_id,) in db.execute(
            f"SELECT id FROM users WHERE banned_at IS NULL AND id IN"
            f" ({','.join('?' * len(user_ids))})",
            list(user_ids),
        )
    }


def _consent(db: sqlite3.Connection, user_id: str, now: datetime) -> None:
    db.execute("UPDATE users SET consented_at = ? WHERE id = ?", (now.isoformat(), user_id))


def _user_signing_in_with(db: sqlite3.Connection, provider: str, subject: str) -> str | None:
    row = db.execute(
        "SELECT user_id FROM sign_in_methods WHERE provider = ? AND subject = ?",
        (provider, subject),
    ).fetchone()
    return row[0] if row else None


def _insert_user_signing_in_with(
    db: sqlite3.Connection,
    user: User,
    method: SignInMethod,
    admit: Admit | None,
) -> None:
    _insert_user(db, user)
    _insert_sign_in_method(db, user.id, method)
    if admit is not None:
        admit(db, user.id)


def _insert_sign_in_method(db: sqlite3.Connection, user_id: str, method: SignInMethod) -> None:
    db.execute(
        "INSERT INTO sign_in_methods"
        " (user_id, provider, subject, display_name, email, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, method.provider, method.subject, method.display_name, method.email,
         method.created_at),
    )


def _update_sign_in_method(
    db: sqlite3.Connection, provider: str, subject: str, display_name: str, email: str | None
) -> None:
    db.execute(
        "UPDATE sign_in_methods SET display_name = ?, email = ?"
        " WHERE provider = ? AND subject = ?",
        (display_name, email, provider, subject),
    )


def _sign_in_methods_of(
    db: sqlite3.Connection, user_ids: list[str]
) -> dict[str, list[SignInMethod]]:
    return {
        user_id: [
            SignInMethod(**row)
            for row in by_name(db).execute(
                "SELECT provider, subject, display_name, email, created_at FROM sign_in_methods"
                " WHERE user_id = ? ORDER BY created_at, rowid",
                (user_id,),
            )
        ]
        for user_id in user_ids
    }


def _remove_sign_in_method(db: sqlite3.Connection, user_id: str, provider: str) -> bool:
    providers = [
        p for (p,) in db.execute(
            "SELECT provider FROM sign_in_methods WHERE user_id = ?", (user_id,)
        )
    ]
    if provider not in providers:
        return False
    if len(providers) == 1:
        raise LastSignInMethod
    db.execute(
        "DELETE FROM sign_in_methods WHERE user_id = ? AND provider = ?", (user_id, provider)
    )
    return True


def _ban_identities_if_banned(
    db: sqlite3.Connection, user_id: str, identity_hashes: Sequence[str]
) -> None:
    user = _user(db, user_id)
    if user is None or user.banned_at is None:
        return
    db.executemany(
        "INSERT OR IGNORE INTO banned_identities (identity_hash, added_at) VALUES (?, ?)",
        [(h, _now()) for h in identity_hashes],
    )


def _is_banned_identity(db: sqlite3.Connection, identity_hash: str) -> bool:
    return db.execute(
        "SELECT 1 FROM banned_identities WHERE identity_hash = ?", (identity_hash,)
    ).fetchone() is not None


def _create_session(
    db: sqlite3.Connection, token_hash: str, user_id: str, now: datetime
) -> None:
    db.execute("DELETE FROM sessions WHERE expires_at <= ?", (now.timestamp(),))
    db.execute(
        "INSERT INTO sessions (token_hash, user_id, last_active_at, expires_at)"
        " VALUES (?, ?, ?, ?)",
        (token_hash, user_id, now.timestamp(), (now + SESSION_LIFETIME).timestamp()),
    )


def _session(db: sqlite3.Connection, token_hash: str) -> tuple[float, float, User] | None:
    """When the session with this token hash was last renewed and when it expires, epoch
    seconds, and whose it is; None if there is none."""
    row = db.execute(
        "SELECT user_id, last_active_at, expires_at FROM sessions WHERE token_hash = ?",
        (token_hash,),
    ).fetchone()
    if row is None:
        return None
    user_id, last_active_at, expires_at = row
    user = _user(db, user_id)
    assert user is not None
    return last_active_at, expires_at, user


def _use_session(db: sqlite3.Connection, token_hash: str, now: datetime) -> Session | None:
    found = _session(db, token_hash)
    if found is None:
        return None
    last_active_at, expires_at, user = found
    if expires_at <= now.timestamp():
        db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
        return None
    renewed = _renewal_due(last_active_at, now)
    if renewed:
        db.execute(
            "UPDATE sessions SET last_active_at = ?, expires_at = ? WHERE token_hash = ?",
            (now.timestamp(), (now + SESSION_LIFETIME).timestamp(), token_hash),
        )
    return Session(user, renewed)


def _renewal_due(last_active_at: float, now: datetime) -> bool:
    """Whether a session last renewed at `last_active_at`, epoch seconds, is to be renewed
    again `now`."""
    return now.timestamp() - last_active_at >= SESSION_RENEWAL.total_seconds()


def _end_session(db: sqlite3.Connection, token_hash: str) -> None:
    db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))


def _end_sessions(db: sqlite3.Connection, user_id: str) -> None:
    db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))


def read_profile(db: sqlite3.Connection, user_id: str) -> ProducerProfile:
    """The user's producer profile, read through `db`: what `Store.get_profile` reads, and
    what other modules read in their own transactions; all defaults until they save one."""
    row = by_name(db).execute(
        "SELECT form_of_address, gender, timezone, birthday_month, birthday_day, city_name,"
        " city_adm2, city_adm1, city_country, city_latitude, city_longitude"
        " FROM producer_profiles WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if not row:
        return ProducerProfile()
    birthday = (
        Birthday(row["birthday_month"], row["birthday_day"])
        if row["birthday_month"] is not None and row["birthday_day"] is not None
        else None
    )
    city = (
        City(
            row["city_name"], row["city_adm2"] or "", row["city_adm1"] or "",
            row["city_country"] or "", row["city_latitude"], row["city_longitude"],
        )
        if row["city_name"] is not None and row["city_latitude"] is not None
        and row["city_longitude"] is not None
        else None
    )
    return ProducerProfile(
        row["form_of_address"], row["gender"], row["timezone"], birthday, city
    )


def write_profile(db: sqlite3.Connection, user_id: str, profile: ProducerProfile) -> None:
    """Save the user's whole producer profile through `db`, in the caller's transaction: what
    `Store.save_profile` does, and importing a data package in its write task."""
    birthday, city = profile.birthday, profile.city
    db.execute(
        "INSERT INTO producer_profiles"
        " (user_id, form_of_address, gender, timezone, birthday_month, birthday_day,"
        " city_name, city_adm2, city_adm1, city_country, city_latitude, city_longitude,"
        " updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        " ON CONFLICT (user_id) DO UPDATE SET form_of_address = excluded.form_of_address,"
        " gender = excluded.gender, timezone = excluded.timezone,"
        " birthday_month = excluded.birthday_month, birthday_day = excluded.birthday_day,"
        " city_name = excluded.city_name, city_adm2 = excluded.city_adm2,"
        " city_adm1 = excluded.city_adm1, city_country = excluded.city_country,"
        " city_latitude = excluded.city_latitude, city_longitude = excluded.city_longitude,"
        " updated_at = excluded.updated_at",
        (
            user_id,
            profile.form_of_address,
            profile.gender,
            profile.timezone,
            birthday and birthday.month,
            birthday and birthday.day,
            city and city.name,
            city and city.adm2,
            city and city.adm1,
            city and city.country,
            city and city.latitude,
            city and city.longitude,
            _now(),
        ),
    )


def _conversation(db: sqlite3.Connection, conversation_id: str) -> Conversation | None:
    row = by_name(db).execute(
        "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
    ).fetchone()
    return Conversation(**row) if row else None


def _conversations(db: sqlite3.Connection, user_id: str, character_id: str) -> list[Conversation]:
    rows = by_name(db).execute(
        "SELECT * FROM conversations WHERE user_id = ? AND character_id = ?"
        " ORDER BY created_at DESC, rowid DESC",
        (user_id, character_id),
    ).fetchall()
    return [Conversation(**row) for row in rows]


def _insert_conversation(db: sqlite3.Connection, conversation: Conversation) -> None:
    db.execute(
        "INSERT INTO conversations (id, user_id, character_id, created_at)"
        " VALUES (?, ?, ?, ?)",
        (conversation.id, conversation.user_id, conversation.character_id,
         conversation.created_at),
    )


def _list_conversations(
    db: sqlite3.Connection, user_id: str, character_id: str
) -> list[tuple[Conversation, Recorded | None, bool]]:
    return [
        (c, _last(db, c.id), read_ended(db, c.id) is not None)
        for c in _conversations(db, user_id, character_id)
    ]


def _name_conversation(db: sqlite3.Connection, conversation_id: str, title: str) -> None:
    db.execute(
        "UPDATE conversations SET title = ? WHERE id = ? AND title IS NULL",
        (title, conversation_id),
    )


def _delete_conversation(db: sqlite3.Connection, conversation: Conversation) -> None:
    hers = _conversations(db, conversation.user_id, conversation.character_id)
    if hers[0].id == conversation.id:
        raise IsCurrent()
    delete_conversation_data(db, conversation.id)


def read_whole_conversations(db: sqlite3.Connection, user_id: str) -> list[WholeConversation]:
    """Every one of the user's conversations, with every character, the oldest first, and
    all that is kept under each, read through `db`, for a data package; not the pictures of
    photos, read one at a time (`Store.photo_image`)."""
    named = by_name(db)
    conversations = named.execute(
        "SELECT * FROM conversations WHERE user_id = ? ORDER BY created_at, rowid",
        (user_id,),
    ).fetchall()
    return [
        WholeConversation(
            c["id"], c["character_id"], c["created_at"], c["title"],
            [
                KeptMessage(
                    m["role"], m["text"], m["ja"], m["zh"],
                    [Segment(**s) for s in json.loads(m["segments"] or "[]")],
                    m["created_at"], _change(m["affinity"]), m["hurt"],
                    None if m["out_of_line"] is None else bool(m["out_of_line"]),
                    None if m["photo_id"] is None else KeptPhoto(
                        m["photo_id"], m["photo_tag"], m["photo_status"],
                        m["photo_reason"], m["photo_created_at"], m["photo_updated_at"],
                    ),
                )
                for m in named.execute(
                    "SELECT m.*, p.id AS photo_id, p.tag AS photo_tag,"
                    " p.status AS photo_status, p.reason AS photo_reason,"
                    " p.created_at AS photo_created_at, p.updated_at AS photo_updated_at"
                    " FROM messages m LEFT JOIN photos p ON p.message_id = m.id"
                    " WHERE m.conversation_id = ? ORDER BY m.id",
                    (c["id"],),
                ).fetchall()
            ],
            [
                KeptEvent(
                    e["kind"], e["created_at"], _change(e["affinity"]), e["gift_id"],
                    bool(e["liked"]), e["first_day"], e["days_ago"],
                )
                for e in named.execute(
                    f"SELECT {_EVENT_COLUMNS} FROM conversation_events"
                    " WHERE conversation_id = ? ORDER BY id",
                    (c["id"],),
                ).fetchall()
            ],
            [
                ConnectedCall(k["connected_at"], k["duration_s"])
                for k in named.execute(
                    "SELECT connected_at, duration_s FROM calls"
                    " WHERE conversation_id = ? ORDER BY id",
                    (c["id"],),
                ).fetchall()
            ],
            [
                KeptReachOut(
                    r["ja"], r["zh"], [Segment(**s) for s in json.loads(r["segments"])],
                    r["created_at"],
                )
                for r in named.execute(
                    "SELECT ja, zh, segments, created_at FROM reach_outs"
                    " WHERE conversation_id = ? ORDER BY id",
                    (c["id"],),
                ).fetchall()
            ],
        )
        for c in conversations
    ]


def _contacts(db: sqlite3.Connection, user_id: str) -> list[Contact]:
    rows = by_name(db).execute(
        "SELECT c.character_id, 'turn' AS kind, m.created_at, 0 AS liked FROM messages m"
        " JOIN conversations c ON c.id = m.conversation_id"
        " WHERE c.user_id = ? AND m.role = 'user'"
        " UNION ALL"
        " SELECT c.character_id, 'gift' AS kind, e.created_at, e.liked"
        " FROM conversation_events e JOIN conversations c ON c.id = e.conversation_id"
        " WHERE c.user_id = ? AND e.kind = 'gift'",
        (user_id, user_id),
    ).fetchall()
    return [
        Contact(r["character_id"], r["kind"], _at(r["created_at"]), bool(r["liked"]))
        for r in rows
    ]


def keep_call(
    db: sqlite3.Connection, conversation_id: str, connected_at: datetime, duration_s: float
) -> bool:
    """Keep a call in the conversation that connected at `connected_at` and lasted
    `duration_s` seconds once it had, for stats, through `db`, in the transaction what it
    comes to is kept in (`Happenings.call_ended`); not into its record. It answers her
    latest reach-out in it (`_answer_reach_out`). Nothing is kept if the conversation is
    gone meanwhile, deleted with the user, say. Whether it was kept."""
    kept = db.execute(
        "INSERT INTO calls (conversation_id, connected_at, duration_s)"
        " SELECT id, ?, ? FROM conversations WHERE id = ?",
        (connected_at.astimezone(UTC).isoformat(), duration_s, conversation_id),
    ).rowcount
    _answer_reach_out(db, conversation_id)
    return bool(kept)


def _kept_calls(db: sqlite3.Connection, user_id: str) -> list[KeptCall]:
    rows = by_name(db).execute(
        "SELECT c.character_id, k.connected_at, k.duration_s FROM calls k"
        " JOIN conversations c ON c.id = k.conversation_id WHERE c.user_id = ?",
        (user_id,),
    ).fetchall()
    return [KeptCall(r["character_id"], _at(r["connected_at"]), r["duration_s"]) for r in rows]


def _first_records(db: sqlite3.Connection, user_id: str) -> dict[str, datetime]:
    # Each from the user's conversations, so as to read only what is in them.
    rows = by_name(db).execute(
        "SELECT character_id, MIN(at) AS first FROM ("
        " SELECT c.character_id, m.created_at AS at FROM conversations c"
        "  JOIN messages m ON m.conversation_id = c.id WHERE c.user_id = :user"
        " UNION ALL SELECT c.character_id, e.created_at FROM conversations c"
        "  JOIN conversation_events e ON e.conversation_id = c.id WHERE c.user_id = :user"
        " UNION ALL SELECT c.character_id, k.connected_at FROM conversations c"
        "  JOIN calls k ON k.conversation_id = c.id WHERE c.user_id = :user"
        ") GROUP BY character_id",
        {"user": user_id},
    ).fetchall()
    return {r["character_id"]: _at(r["first"]) for r in rows}


def _latest_conversations(
    db: sqlite3.Connection, user_id: str
) -> list[tuple[Conversation, Recorded | None, bool]]:
    rows = by_name(db).execute(
        "SELECT * FROM conversations WHERE user_id = ?"
        " ORDER BY created_at DESC, rowid DESC",
        (user_id,),
    ).fetchall()
    newest: dict[str, Conversation] = {}
    for row in rows:
        newest.setdefault(row["character_id"], Conversation(**row))
    return [(c, _last(db, c.id), _unseen(db, c.id)) for c in newest.values()]


def _unseen(db: sqlite3.Connection, conversation_id: str) -> bool:
    """Whether the conversation has a reach-out the user has not seen."""
    return db.execute(
        "SELECT EXISTS (SELECT 1 FROM reach_outs WHERE conversation_id = ? AND seen = 0)",
        (conversation_id,),
    ).fetchone()[0] == 1


def _last(db: sqlite3.Connection, conversation_id: str) -> Recorded | None:
    """The last thing in the record, but her ending it, as `read_record` orders them: the
    list shows her last line, and whether she sent a photo with it."""
    named = by_name(db)
    row = named.execute(
        f"SELECT {_MESSAGE_WITH_PHOTO} WHERE m.conversation_id = ?"
        " ORDER BY m.id DESC LIMIT 1",
        (conversation_id,),
    ).fetchone()
    message = _message_with_photo(row) if row else None
    event = named.execute(
        f"SELECT {_EVENT_COLUMNS} FROM conversation_events WHERE conversation_id = ?"
        " AND kind != 'ended' ORDER BY created_at DESC, id DESC LIMIT 1",
        (conversation_id,),
    ).fetchone()
    reach_out = named.execute(
        f"SELECT {_REACH_OUT_COLUMNS} FROM reach_outs WHERE conversation_id = ?"
        " ORDER BY created_at DESC, id DESC LIMIT 1",
        (conversation_id,),
    ).fetchone()
    between: list[ConversationEvent | ReachOut] = []
    if event is not None:
        between.append(_event(event))
    if reach_out is not None:
        between.append(_reach_out(reach_out))
    latest = max(between, key=_placed, default=None)
    if latest is None or message is None:
        return latest or message
    said = db.execute(
        "SELECT created_at FROM messages WHERE conversation_id = ? AND role = 'user'"
        " ORDER BY id DESC LIMIT 1",
        (conversation_id,),
    ).fetchone()
    last_turn_said = said[0] if said else message.created_at
    after = _at(latest.created_at) >= _at(last_turn_said)  # as `read_record` places it
    return latest if after else message


def add_turn(
    db: sqlite3.Connection,
    conversation_id: str,
    text: str,
    reply: list[Segment],
    affinity: Change | None = None,
    said_at: str | None = None,
    typed: Typed | None = None,
    ends: bool = False,
    photo: NewPhoto | None = None,
) -> Message:
    """Record the user's input, said at `said_at` (as `timestamp` gives it; now by
    default), and the character's reply together, through `db`, in the transaction the
    turn is recorded in with what it changes (`ConversationEngine`), with how the turn
    changed her affinity, if it did, and for a typed turn what it came to (`typed`);
    returns the reply. The photo she sends with it, if any, is recorded being generated.
    Should she end the conversation after it (`ends`), that is recorded with it, after it
    (`ended`). It answers her latest reach-out in it (`_answer_reach_out`). Into a
    conversation she has ended already, nothing is recorded: `ConversationEnded`."""
    if read_ended(db, conversation_id) is not None:
        raise ConversationEnded()
    _insert_message(db, conversation_id, "user", text=text, created_at=said_at, typed=typed)
    replied = _insert_message(db, conversation_id, "character", segments=reply, affinity=affinity)
    if photo is not None:
        now = _now()
        db.execute(
            "INSERT INTO photos (id, conversation_id, message_id, tag, status,"
            " created_at, updated_at) VALUES (?, ?, ?, ?, 'pending', ?, ?)",
            (photo.id, conversation_id, replied.id, photo.tag, now, now),
        )
        replied = replace(replied, photo=Photo(photo.id, "pending", None, photo.tag))
    if ends:
        _insert_event(db, conversation_id, "ended", _now())
    _answer_reach_out(db, conversation_id)
    return replied


def _finish_photo(
    db: sqlite3.Connection, photo_id: str, image: bytes | None, reason: PhotoFailure | None
) -> bool:
    cursor = db.execute(
        "UPDATE photos SET status = ?, reason = ?, image = ?, updated_at = ?"
        " WHERE id = ? AND status = 'pending'",
        ("ready" if image is not None else "failed", reason, image, _now(), photo_id),
    )
    return cursor.rowcount > 0


def _give_up_photos(db: sqlite3.Connection, reason: PhotoFailure) -> int:
    cursor = db.execute(
        "UPDATE photos SET status = 'failed', reason = ?, updated_at = ?"
        " WHERE status = 'pending'",
        (reason, _now()),
    )
    return cursor.rowcount


def _photo(db: sqlite3.Connection, photo_id: str, user_id: str) -> Photo | None:
    row = by_name(db).execute(
        "SELECT p.id, p.status, p.reason, p.tag FROM photos p"
        " JOIN conversations c ON c.id = p.conversation_id"
        " WHERE p.id = ? AND c.user_id = ?",
        (photo_id, user_id),
    ).fetchone()
    return Photo(**row) if row else None


def _photo_image(db: sqlite3.Connection, photo_id: str, user_id: str) -> bytes | None:
    row = db.execute(
        "SELECT p.image FROM photos p JOIN conversations c ON c.id = p.conversation_id"
        " WHERE p.id = ? AND c.user_id = ? AND p.status = 'ready'",
        (photo_id, user_id),
    ).fetchone()
    return row[0] if row else None


def _reply_said(
    db: sqlite3.Connection, conversation_id: str, message_id: int
) -> list[Segment] | None:
    row = db.execute(
        "SELECT segments FROM messages WHERE id = ? AND conversation_id = ? AND role = 'character'",
        (message_id, conversation_id),
    ).fetchone()
    return [Segment(**s) for s in json.loads(row[0] or "[]")] if row else None


def _reach_out_said(
    db: sqlite3.Connection, conversation_id: str, reach_out_id: int
) -> list[Segment] | None:
    row = db.execute(
        "SELECT segments FROM reach_outs WHERE id = ? AND conversation_id = ?",
        (reach_out_id, conversation_id),
    ).fetchone()
    return [Segment(**s) for s in json.loads(row[0])] if row else None


def add_gift(
    db: sqlite3.Connection,
    user_id: str,
    character_id: str,
    gift_id: str,
    liked: bool,
    affinity: Change | None,
) -> Conversation:
    """Record the user's giving the character the gift, now, whether she liked it, with how
    it changed her affinity, if it did, through `db`, in the transaction the gift is given
    in (`Happenings.give`); returns the conversation it is recorded in: her newest, her
    current one (GLOSSARY.md「当前对话」), if she has not ended it, else one begun for it,
    which is her current one from then on. Where it goes is chosen in the same transaction
    it is recorded in, so it never goes into one she ends meanwhile."""
    hers = _conversations(db, user_id, character_id)
    conversation = hers[0] if hers and read_ended(db, hers[0].id) is None else None
    if conversation is None:
        conversation = Conversation(uuid.uuid4().hex, user_id, character_id, _now())
        _insert_conversation(db, conversation)
    _insert_event(db, conversation.id, "gift", _now(), affinity, gift_id, liked)
    return conversation


def add_unwell(
    db: sqlite3.Connection, conversation: Conversation, first_day: date, days_ago: int,
    said_at: str,
) -> ConversationEvent | None:
    """Record her being unwell in the conversation, from `first_day`, `days_ago` days before
    today, just before the user's words said at `said_at`, so that it comes before their
    turn; through `db`, in the transaction the turn is recorded in, before it. Once a period:
    nothing if one from `first_day` is in any of the user's conversations with her already,
    which is None."""
    recorded = db.execute(
        "SELECT EXISTS (SELECT 1 FROM conversation_events e"
        " JOIN conversations c ON c.id = e.conversation_id"
        " WHERE c.user_id = ? AND c.character_id = ? AND e.kind = 'unwell'"
        " AND e.first_day = ?)",
        (conversation.user_id, conversation.character_id, first_day.isoformat()),
    ).fetchone()[0]
    if recorded:
        return None
    before = (_at(said_at) - timedelta(microseconds=1)).isoformat()
    return _insert_event(
        db, conversation.id, "unwell", before, first_day=first_day.isoformat(),
        days_ago=days_ago,
    )


def _hang_up(db: sqlite3.Connection, conversation_id: str) -> ConversationEvent:
    return read_ended(db, conversation_id) or _insert_event(
        db, conversation_id, "hung_up", _now()
    )


def read_ended(db: sqlite3.Connection, conversation_id: str) -> ConversationEvent | None:
    """Her ending the conversation (GLOSSARY.md「已结束的对话」), as recorded, read through
    `db`; None while it is not ended."""
    row = by_name(db).execute(
        f"SELECT {_EVENT_COLUMNS} FROM conversation_events"
        " WHERE conversation_id = ? AND kind = 'ended' ORDER BY id LIMIT 1",
        (conversation_id,),
    ).fetchone()
    return _event(row) if row else None


def _typed_turns(db: sqlite3.Connection, conversation_id: str, latest: int) -> list[Typed]:
    rows = db.execute(
        "SELECT hurt, out_of_line FROM messages WHERE conversation_id = ?"
        " AND role = 'user' AND hurt IS NOT NULL ORDER BY id DESC LIMIT ?",
        (conversation_id, latest),
    ).fetchall()
    return [Typed(hurt, bool(out_of_line)) for hurt, out_of_line in reversed(rows)]


def _list_messages(db: sqlite3.Connection, conversation_id: str) -> list[Message]:
    rows = by_name(db).execute(
        f"SELECT {_MESSAGE_WITH_PHOTO} WHERE m.conversation_id = ? ORDER BY m.id",
        (conversation_id,),
    ).fetchall()
    return [_message_with_photo(row) for row in rows]


def read_record(db: sqlite3.Connection, conversation_id: str) -> list[Recorded]:
    """The conversation's messages, events and reach-outs, read through `db`, in the order
    things happened: a turn where the user's words were said, its two messages together, an
    event or a reach-out where it happened; so one written while a turn was under way comes
    after the turn."""
    messages = _list_messages(db, conversation_id)
    named = by_name(db)
    events = named.execute(
        f"SELECT {_EVENT_COLUMNS} FROM conversation_events WHERE conversation_id = ?",
        (conversation_id,),
    ).fetchall()
    reach_outs = named.execute(
        f"SELECT {_REACH_OUT_COLUMNS} FROM reach_outs WHERE conversation_id = ?",
        (conversation_id,),
    ).fetchall()
    pending: deque[ConversationEvent | ReachOut] = deque(
        sorted([*map(_event, events), *map(_reach_out, reach_outs)], key=_placed)
    )
    merged: list[Recorded] = []
    for message in messages:
        if message.role == "user":
            while pending and _at(pending[0].created_at) < _at(message.created_at):
                merged.append(pending.popleft())
        merged.append(message)
    return merged + list(pending)


def _record_and_unseen(
    db: sqlite3.Connection, conversation_id: str
) -> tuple[list[Recorded], int | None]:
    """The conversation's record, and the id of the last reach-out in it should one of them
    not have been seen; None if all have."""
    entries = read_record(db, conversation_id)
    given = [entry.id for entry in entries if isinstance(entry, ReachOut)]
    if not given:
        return entries, None
    [(unseen,)] = db.execute(
        "SELECT EXISTS (SELECT 1 FROM reach_outs WHERE conversation_id = ? AND id <= ?"
        " AND seen = 0)",
        (conversation_id, max(given)),
    ).fetchall()
    return entries, max(given) if unseen else None


def _see_reach_outs(db: sqlite3.Connection, conversation_id: str, up_to: int) -> None:
    db.execute(
        "UPDATE reach_outs SET seen = 1 WHERE conversation_id = ? AND id <= ? AND seen = 0",
        (conversation_id, up_to),
    )


def _current_conversations(db: sqlite3.Connection) -> list[CurrentConversation]:
    rows = by_name(db).execute(
        "SELECT c.*,"
        " (SELECT MAX(m.created_at) FROM messages m WHERE m.conversation_id = c.id)"
        "  AS last_turn,"
        " (SELECT MAX(r.created_at) FROM reach_outs r WHERE r.conversation_id = c.id)"
        "  AS reached_out_at,"
        " EXISTS (SELECT 1 FROM conversation_events e WHERE e.conversation_id = c.id"
        "  AND e.kind = 'ended') AS ended"
        " FROM conversations c JOIN users u ON u.id = c.user_id AND u.banned_at IS NULL"
        f" WHERE {_CURRENT}"
    ).fetchall()
    calls: dict[str, list[tuple[str, float]]] = {}
    # The calls in the same conversations, picked out the same way: as many ids as there
    # are conversations would be more than a statement may bind.
    for conversation_id, connected_at, duration_s in db.execute(
        "SELECT k.conversation_id, k.connected_at, k.duration_s FROM calls k"
        f" JOIN conversations c ON c.id = k.conversation_id WHERE {_CURRENT}"
    ):
        calls.setdefault(conversation_id, []).append((connected_at, duration_s))
    return [
        CurrentConversation(
            Conversation(
                row["id"], row["user_id"], row["character_id"], row["created_at"],
                row["title"],
            ),
            row["last_turn"] is not None,
            _last_contact(row["last_turn"], calls.get(row["id"], [])),
            _at(row["reached_out_at"]) if row["reached_out_at"] else None,
            bool(row["ended"]),
        )
        for row in rows
    ]


def read_in_touch(db: sqlite3.Connection, user_id: str | None = None) -> list[InTouch]:
    """How every user, but banned users, or only `user_id` if not banned, is in touch with
    each character they have a conversation with, read through `db`; in no order."""
    only = " AND c.user_id = :user" if user_id is not None else ""
    users = f"JOIN users u ON u.id = c.user_id AND u.banned_at IS NULL{only}"
    turns = db.execute(
        "SELECT c.user_id, c.character_id, MAX(m.created_at) FROM conversations c"
        f" {users} LEFT JOIN messages m ON m.conversation_id = c.id"
        " GROUP BY c.user_id, c.character_id",
        {"user": user_id},
    ).fetchall()
    calls: dict[tuple[str, str], list[tuple[str, float]]] = {}
    for user, character, connected_at, duration_s in db.execute(
        "SELECT c.user_id, c.character_id, k.connected_at, k.duration_s FROM calls k"
        f" JOIN conversations c ON c.id = k.conversation_id {users}",
        {"user": user_id},
    ):
        calls.setdefault((user, character), []).append((connected_at, duration_s))
    return [
        InTouch(user, character, last_turn is not None,
                _last_contact(last_turn, calls.get((user, character), [])))
        for user, character, last_turn in turns
    ]


def read_current_conversation(
    db: sqlite3.Connection, user_id: str, character_id: str
) -> Conversation | None:
    """The user's current conversation with the character (GLOSSARY.md「当前对话」), read
    through `db`; None without one."""
    row = by_name(db).execute(
        f"SELECT c.* FROM conversations c WHERE c.user_id = ? AND c.character_id = ?"
        f" AND {_CURRENT}",
        (user_id, character_id),
    ).fetchone()
    if row is None:
        return None
    return Conversation(
        row["id"], row["user_id"], row["character_id"], row["created_at"], row["title"]
    )


def read_last_contact(
    db: sqlite3.Connection, user_id: str, character_id: str, before: datetime | None = None
) -> datetime | None:
    """When the user and the character were last in touch, in any of their conversations,
    read through `db`: her last turn recorded, or a call that connected ending, whichever
    was later, and earlier than `before` if given; None before either."""
    until = () if before is None else (before.astimezone(UTC).isoformat(),)
    [last_turn] = db.execute(
        "SELECT MAX(m.created_at) FROM messages m"
        " JOIN conversations c ON c.id = m.conversation_id"
        " WHERE c.user_id = ? AND c.character_id = ?"
        + ("" if before is None else " AND m.created_at < ?"),
        (user_id, character_id, *until),
    ).fetchone()
    calls = db.execute(
        "SELECT k.connected_at, k.duration_s FROM calls k"
        " JOIN conversations c ON c.id = k.conversation_id"
        " WHERE c.user_id = ? AND c.character_id = ?",
        (user_id, character_id),
    ).fetchall()
    if before is not None:
        calls = [call for call in calls if _call_ended(*call) < before]
    return _last_contact(last_turn, calls)


def _add_reach_out(
    db: sqlite3.Connection,
    conversation_id: str,
    said: list[Segment],
    contact: datetime,
    created_at: str,
) -> ReachOut:
    ja, zh = "".join(s.ja for s in said), "".join(s.zh for s in said)
    current = db.execute(
        "SELECT n.id FROM conversations c JOIN conversations n"
        " ON n.user_id = c.user_id AND n.character_id = c.character_id"
        " WHERE c.id = ? ORDER BY n.created_at DESC, n.rowid DESC LIMIT 1",
        (conversation_id,),
    ).fetchone()
    [reached_out_at] = db.execute(
        "SELECT MAX(created_at) FROM reach_outs WHERE conversation_id = ?",
        (conversation_id,),
    ).fetchone()
    if (
        current is None or current[0] != conversation_id
        or read_ended(db, conversation_id) is not None
        or _last_contact_in(db, conversation_id) != contact
        or (reached_out_at is not None and _at(reached_out_at) >= contact)
    ):
        raise ReachOutRefused()
    cursor = db.execute(
        "INSERT INTO reach_outs (conversation_id, ja, zh, segments, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (conversation_id, ja, zh, _stored_segments(said), created_at),
    )
    assert cursor.lastrowid is not None
    return ReachOut(cursor.lastrowid, ja, zh, list(said), created_at)


def _reach_out_recorded_as(
    db: sqlite3.Connection, reach_out_id: int, record_id: int | None
) -> None:
    db.execute("UPDATE reach_outs SET record_id = ? WHERE id = ?", (record_id, reach_out_id))
    row = db.execute(
        "SELECT conversation_id, created_at FROM reach_outs WHERE id = ?", (reach_out_id,)
    ).fetchone()
    if row is None:  # deleted meanwhile
        return
    conversation_id, created_at = row
    contact = _last_contact_in(db, conversation_id)
    if record_id is not None and contact is not None and contact > _at(created_at):
        _mark_answered(db, record_id)


def _answer_reach_out(db: sqlite3.Connection, conversation_id: str) -> None:
    """Mark her latest reach-out in the conversation answered, the user and she being in
    touch in it now: a turn recorded, or a call connected, after it and before the next.
    One whose record is not kept yet is marked as it is (`_reach_out_recorded_as`)."""
    latest = db.execute(
        "SELECT record_id FROM reach_outs WHERE conversation_id = ?"
        " ORDER BY created_at DESC, id DESC LIMIT 1",
        (conversation_id,),
    ).fetchone()
    if latest is not None and latest[0] is not None:
        _mark_answered(db, latest[0])


def _mark_answered(db: sqlite3.Connection, record_id: int) -> None:
    """Mark a reach-out's activity record answered. The record is the activity log's;
    none in a database without one."""
    if "activity_records" in tables(db):
        db.execute("UPDATE activity_records SET answered = 1 WHERE id = ?", (record_id,))


def _last_contact_in(db: sqlite3.Connection, conversation_id: str) -> datetime | None:
    """When the user and she were last in touch in the conversation, as
    `current_conversations` has it."""
    [last_turn] = db.execute(
        "SELECT MAX(created_at) FROM messages WHERE conversation_id = ?", (conversation_id,)
    ).fetchone()
    calls = db.execute(
        "SELECT connected_at, duration_s FROM calls WHERE conversation_id = ?",
        (conversation_id,),
    ).fetchall()
    return _last_contact(last_turn, calls)


def _insert_message(
    db: sqlite3.Connection,
    conversation_id: str,
    role: Role,
    text: str | None = None,
    segments: list[Segment] | None = None,
    affinity: Change | None = None,
    created_at: str | None = None,
    typed: Typed | None = None,
) -> Message:
    created_at = created_at or _now()
    ja = zh = None
    if segments is not None:
        ja = "".join(s.ja for s in segments)
        zh = "".join(s.zh for s in segments)
    cursor = db.execute(
        "INSERT INTO messages (conversation_id, role, text, ja, zh, segments, created_at,"
        " affinity, hurt, out_of_line) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            conversation_id, role, text, ja, zh, _stored_segments(segments), created_at,
            _stored_change(affinity),
            typed and typed.hurt, typed and int(typed.out_of_line),
        ),
    )
    assert cursor.lastrowid is not None
    return Message(cursor.lastrowid, role, text, ja, zh, created_at, segments or [], affinity)


def _insert_event(
    db: sqlite3.Connection,
    conversation_id: str,
    kind: EventKind,
    created_at: str,
    affinity: Change | None = None,
    gift_id: str | None = None,
    liked: bool = False,
    first_day: str | None = None,
    days_ago: int | None = None,
) -> ConversationEvent:
    cursor = db.execute(
        "INSERT INTO conversation_events"
        " (conversation_id, kind, created_at, affinity, gift_id, liked, first_day, days_ago)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (conversation_id, kind, created_at, _stored_change(affinity), gift_id, int(liked),
         first_day, days_ago),
    )
    assert cursor.lastrowid is not None
    return ConversationEvent(
        cursor.lastrowid, kind, created_at, affinity, gift_id, liked, first_day, days_ago
    )


def add_carried_conversation(
    db: sqlite3.Connection,
    user_id: str,
    conversation: WholeConversation,
    picture_of: Callable[[str], bytes],
) -> tuple[str, bool]:
    """Add the conversation a data package carries to the user's through `db`, in the
    caller's transaction, under an id of its own, its messages in their order and its events
    and calls as they were, her reach-outs as seen, each photo under an id of its own with its
    picture, if sent, as `picture_of` its id in the package reads it; its id here, and whether
    it is new. One the user already has with her, begun at the same time, is taken for it and
    left as it is, nothing of it merged. Which is her current one is as ever: the newest
    begun."""
    begun = _at(conversation.created_at)
    for row in db.execute(
        "SELECT id, created_at FROM conversations WHERE user_id = ? AND character_id = ?",
        (user_id, conversation.character_id),
    ).fetchall():
        if _at(row[1]) == begun:
            return row[0], False
    conversation_id = uuid.uuid4().hex
    db.execute(
        "INSERT INTO conversations (id, user_id, character_id, created_at, title)"
        " VALUES (?, ?, ?, ?, ?)",
        (conversation_id, user_id, conversation.character_id, conversation.created_at,
         conversation.title),
    )
    for m in conversation.messages:
        message_id = db.execute(
            "INSERT INTO messages (conversation_id, role, text, ja, zh, segments, created_at,"
            " affinity, hurt, out_of_line) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                conversation_id, m.role, m.text, m.ja, m.zh,
                _stored_segments(m.segments if m.segments or m.role == "character" else None),
                m.created_at, _stored_change(m.affinity), m.hurt,
                None if m.out_of_line is None else int(m.out_of_line),
            ),
        ).lastrowid
        if (photo := m.photo) is not None:
            db.execute(
                "INSERT INTO photos (id, conversation_id, message_id, tag, status, reason,"
                " image, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    uuid.uuid4().hex, conversation_id, message_id, photo.tag, photo.status,
                    photo.reason,
                    picture_of(photo.id) if photo.status == "ready" else None,
                    photo.created_at, photo.updated_at,
                ),
            )
    db.executemany(
        "INSERT INTO conversation_events"
        " (conversation_id, kind, created_at, affinity, gift_id, liked, first_day, days_ago)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (conversation_id, e.kind, e.created_at, _stored_change(e.affinity), e.gift_id,
             int(e.liked), e.first_day, e.days_ago)
            for e in conversation.events
        ],
    )
    db.executemany(
        "INSERT INTO calls (conversation_id, connected_at, duration_s) VALUES (?, ?, ?)",
        [(conversation_id, k.connected_at, k.duration_s) for k in conversation.calls],
    )
    db.executemany(
        "INSERT INTO reach_outs (conversation_id, ja, zh, segments, created_at, seen)"
        " VALUES (?, ?, ?, ?, ?, 1)",
        [
            (conversation_id, r.ja, r.zh, _stored_segments(r.segments), r.created_at)
            for r in conversation.reach_outs
        ],
    )
    return conversation_id, True


def _change(stored: str | None) -> Change | None:
    return Change(**json.loads(stored)) if stored else None


def _stored_change(change: Change | None) -> str | None:
    return change and json.dumps(asdict(change))


def _stored_segments(segments: list[Segment] | None) -> str | None:
    """A reply's segments as kept; None for the user's message, which has none."""
    if segments is None:
        return None
    return json.dumps([asdict(s) for s in segments], ensure_ascii=False)


def _message(row: sqlite3.Row) -> Message:
    return Message(
        row["id"], row["role"], row["text"], row["ja"], row["zh"], row["created_at"],
        [Segment(**s) for s in json.loads(row["segments"] or "[]")],
        _change(row["affinity"]),
    )


def _message_with_photo(row: sqlite3.Row) -> Message:
    if row["photo_id"] is None:
        return _message(row)
    return replace(_message(row), photo=Photo(
        row["photo_id"], row["photo_status"], row["photo_reason"], row["photo_tag"]
    ))


def _event(row: sqlite3.Row) -> ConversationEvent:
    return ConversationEvent(
        row["id"], row["kind"], row["created_at"], _change(row["affinity"]),
        row["gift_id"], bool(row["liked"]), row["first_day"], row["days_ago"],
    )


def _reach_out(row: sqlite3.Row) -> ReachOut:
    return ReachOut(
        row["id"], row["ja"], row["zh"],
        [Segment(**s) for s in json.loads(row["segments"])], row["created_at"],
    )


def _placed(entry: ConversationEvent | ReachOut) -> tuple[datetime, bool, int]:
    """Where an event or a reach-out comes among the others: by when it happened, events
    first at the same time."""
    return _at(entry.created_at), isinstance(entry, ReachOut), entry.id


def _at(timestamp: str) -> datetime:
    return datetime.fromisoformat(timestamp)


def _call_ended(connected_at: str, duration_s: float) -> datetime:
    """When a call that connected at `connected_at` and lasted `duration_s` ended."""
    return _at(connected_at) + timedelta(seconds=duration_s)


def _last_contact(
    last_turn: str | None, calls: Iterable[tuple[str, float] | sqlite3.Row]
) -> datetime | None:
    """When a user and a character were last in touch: their last turn recorded, at
    `last_turn`, or the end of one of their `calls` that connected (when, and how long it
    lasted), whichever was later; None before either."""
    contacts = [_call_ended(at, seconds) for at, seconds in calls]
    if last_turn is not None:
        contacts.append(_at(last_turn))
    return max(contacts, default=None)


def _hash(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def timestamp() -> str:
    """Now, as the store writes when things happened."""
    return _now()


def _now() -> str:
    return datetime.now(UTC).isoformat()
