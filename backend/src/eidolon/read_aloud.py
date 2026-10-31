"""Reading her words aloud (GLOSSARY.md「朗读」): one reply of hers in a conversation's record,
or one reach-out, said in her voice as the user asks for it on the conversation page, as mp3
for their browser to play and keep a while. Nothing of it is kept here: the same words asked
for again are voiced again.

A call voices her as she replies, a sentence at a time, to start speaking soon
(`call.FishTTS`); here all she said is there already, so it is voiced in one request to Fish
Audio's HTTP API, as the greetings are (`greetings`), at its best quality (`LATENCY`), each
sentence said with the rest in view. Her segments go one to a line, each with its delivery
cues as the model voicing it reads them (`delivery_cues.spoken_by`), the names as the
readings have them (`readings`).

On the user's own key for Fish Audio, where their browser brings it, with the model they
chose, counting towards nothing; else on the deployer's, with the model the live
configuration has now, counting towards the user's limit on read-alouds (GLOSSARY.md「限额」),
given back if it was not voiced (`own_keys.OwnKeys.for_read_aloud`). A letter she wrote she
says in her voice the same way, a block at a time, though it is kept, as no read-aloud is, and
on the deployer's key whatever the user brings, counting towards nothing
(`ReadAloud.said_on_deployers`, `letters`). Each is one service call
of speech synthesis, recorded on its own, under no turn (`activity.timed`), billed for what
Fish Audio was given as a call's speech synthesis is (`call.CallMeter`); it has no activity
record of its own. Fish Audio failing on the user's own key says why, the key masked
(`OwnKeyFailed`); on the deployer's, only that it failed (`ReadAloudFailed`)."""

import logging
from collections.abc import Sequence

import httpx

from eidolon.activity import ActivityLog, Origin, host, timed
from eidolon.billing import bill
from eidolon.config import CHARACTER_BILLED_FISH_AUDIO_MODELS, OWN_KEYS_PROXIED, FishAudioModel
from eidolon.delivery_cues import spoken_by, voiced
from eidolon.greetings import FISH_TTS_HTTP_URL
from eidolon.own_keys import (
    BroughtKeys,
    OwnKeyFailed,
    OwnKeys,
    ReadAloudKeys,
    masked_cause,
)
from eidolon.proxy import ProxyRoutes
from eidolon.readings import Reading, pronunciation_dictionary
from eidolon.reply_format import Segment
from eidolon.usage import UsageLimiter

log = logging.getLogger(__name__)

LATENCY = "normal"
"""Fish Audio's best quality, slower to start than the calls' `balanced`: nobody is waiting
on the line."""
SAMPLE_RATE = 44100
MP3_BITRATE = 128
_TIMEOUT = httpx.Timeout(60, connect=10)
"""A reply is a few sentences, voiced in some seconds."""


class ReadAloudFailed(Exception):
    """Fish Audio did not voice it on the deployer's key."""

    def __init__(self) -> None:
        super().__init__("没能合成语音，过一会儿再试")


class NoVoice(Exception):
    """She has no voice to be read aloud in: the character configuration gives her none."""

    def __init__(self) -> None:
        super().__init__("她还没有配置音色，朗读不了")


class _NotVoiced(Exception):
    """Fish Audio answered with no audio, or could not be reached; says how, as `activity`
    tells failures apart (`activity.error_kind`)."""


def fish_text(segments: Sequence[Segment], model: FishAudioModel) -> str:
    """What Fish Audio is told to say of her `segments`, voicing with `model`: each one's
    Japanese with its delivery cues as `model` reads them, a line each."""
    lines = (spoken_by(voiced(s.ja), model) for s in segments)
    return "\n".join(line for line in lines if line.strip())


class ReadAloud:
    """Has her words read aloud, on whoever's key it is to be (`OwnKeys.for_read_aloud`),
    counted in `usage` and recorded in `activity`, through the proxy or direct as `routes`
    have the user's own key or the deployer's go; on `transport` instead, in tests."""

    def __init__(
        self,
        own_keys: OwnKeys,
        usage: UsageLimiter,
        activity: ActivityLog,
        readings: Sequence[Reading] = (),
        routes: ProxyRoutes | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._own_keys = own_keys
        self._usage = usage
        self._activity = activity
        self._dictionary = pronunciation_dictionary(readings)
        self._routes = routes
        self._transport = transport

    async def voice(
        self, user_id: str, voice_id: str, segments: Sequence[Segment], brought: BroughtKeys
    ) -> bytes:
        """Her `segments` said in her voice `voice_id`, as mp3, for the user, bringing
        `brought`. Raises NoVoice if she has none; NoSpeechSynthesis if there is no key for it;
        OverLimit, voicing nothing, if the user has no read-alouds left this hour;
        OwnKeyFailed or ReadAloudFailed, giving the read-aloud back, if Fish Audio fails."""
        if not voice_id.strip():
            raise NoVoice()
        keys = self._own_keys.for_read_aloud(brought)
        try:
            use = await self._usage.take(user_id, "read_aloud", exempt=keys.own)
            try:
                return await self._voice(keys, voice_id, fish_text(segments, keys.tts_model))
            except Exception:
                await use.give_back()
                raise
        finally:
            keys.release()

    async def said_on_deployers(
        self, tts: str, model: FishAudioModel, voice_id: str, ja: str
    ) -> bytes:
        """`ja`, her Japanese with its delivery cues, said in her voice `voice_id` on the
        deployer's key `tts` with `model`, as mp3, as a read-aloud is but counting towards
        nothing: for what she wrote outside any turn, its service call recorded under the
        record current. Raises ReadAloudFailed if Fish Audio fails."""
        text = spoken_by(voiced(ja), model)
        return await self._voice(ReadAloudKeys(tts, model, own=False), voice_id, text)

    async def _voice(self, keys: ReadAloudKeys, voice_id: str, text: str) -> bytes:
        origin = Origin("tts", host(FISH_TTS_HTTP_URL), keys.tts_model, keys.own)
        try:
            return await timed(self._activity, origin, self._request(keys, voice_id, text))
        except _NotVoiced as e:
            if keys.own:
                raise OwnKeyFailed("tts", masked_cause(str(e), keys.tts)) from None
            log.warning("reading aloud failed on the deployer's key for Fish Audio: %s", e)
            raise ReadAloudFailed() from None

    async def _request(self, keys: ReadAloudKeys, voice_id: str, text: str) -> bytes:
        body: dict[str, object] = {
            "text": text,
            "reference_id": voice_id,
            "format": "mp3",
            "sample_rate": SAMPLE_RATE,
            "mp3_bitrate": MP3_BITRATE,
            "latency": LATENCY,
        }
        if self._dictionary is not None:
            body["pronunciation_dictionary"] = self._dictionary
        try:
            async with self._client(keys.own) as client:
                response = await client.post(
                    FISH_TTS_HTTP_URL,
                    headers={"Authorization": f"Bearer {keys.tts}", "model": keys.tts_model},
                    json=body,
                )
        except httpx.HTTPError as e:
            raise _NotVoiced(f"连不上 Fish Audio：{e!r}") from e
        if response.is_error:
            raise _NotVoiced(f"Fish Audio 返回 {response.status_code}：{response.text[:200]}")
        if not response.content:
            raise _NotVoiced("Fish Audio 没有返回音频")
        if keys.tts_model in CHARACTER_BILLED_FISH_AUDIO_MODELS:
            bill("characters", len(text))
        else:
            bill("bytes", len(text.encode()))
        return response.content

    def _client(self, own: bool) -> httpx.AsyncClient:
        """A client for one request to Fish Audio, through the proxy or direct as the settings
        in effect have the user's `own` key or the deployer's go."""
        transport = self._transport
        if transport is None and self._routes is not None:
            transport = self._routes.transport(OWN_KEYS_PROXIED["tts"] if own else "tts")
        return httpx.AsyncClient(transport=transport, timeout=_TIMEOUT, trust_env=False)
