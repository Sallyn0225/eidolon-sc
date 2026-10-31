import type { AffinityChange, AffinityStatus } from "@/lib/affinity";
import type { Provider } from "@/lib/signIn";
import {
  forgetOwnKeys,
  readAloudModel,
  readAloudOwnKeys,
  turnOwnKeys,
  type BailianRegion,
  type FishAudioModel,
  type LLMProtocol,
  type LocalImage,
  type LocalLLM,
  type LocalModel,
  type OwnService,
  type SttProvider,
} from "@/lib/localOwnKeys";
import type { LLMOffer, LLMProvider } from "@/lib/llmProviders";
import type { EffortHint } from "@/lib/reasoningEffort";
import type { ServedBody } from "@/lib/barMixer";
import type { VisitEvent } from "@/lib/barVisit";
import type { Letter, LetterSummary } from "@/lib/letter";
import type { Rewarded } from "@/lib/rewards";
import { detectTimezone } from "@/lib/timezone";
import type { Speaking } from "@/lib/call";
import type { Said } from "@/lib/readAloud";
import type { Emotion, Nod } from "@/lib/standAnimations";
import type { Stats, StatsRange } from "@/lib/stats";

export type Character = {
  id: string;
  name: string;
  intro: string;
  avatar_url: string | null;
  /** Her avatar in SCSP's set, which settings can switch the app's avatars to (lib/appearance); null when not configured. */
  scsp_avatar_url: string | null;
  /** Her image colour, `#rrggbb`; the interface only uses what `herVars()` derives from it. */
  color: string;
  /** Her birthday in the original, `MM-DD`; February 29 falls on February 28 in a year without it. */
  birthday: string;
  background_url: string | null;
  /** Her Spine stand on the call layer; null (her call background alone) unless the deployment
   * configures her idol, her default outfit and where the stands are served from. */
  stand: Stand | null;
  /** Her idol number in the original; the list comes in their order, those without one last. */
  idol_id: number | null;
  /** What the original calls her, the end of her name (真乃), for where there is room for little: the
   * calendar's job blocks; null when not configured, and her name is shown there. */
  short_name: string | null;
  /** Her name in simplified Chinese as the community writes it (八宫巡); null when not configured. */
  name_zh: string | null;
  /** Her full name in hiragana, family and given name a space apart (さくらぎ まの); null when not configured. */
  name_kana: string | null;
  /** Her full name in romaji, family name first, a space apart (Sakuragi Mano); null when not configured. */
  name_romaji: string | null;
  /** The name of her unit, from the world setting; null when there is none or it does not say. */
  unit: string | null;
  /** Her unit's name in hiragana, from the world setting; null along with `unit`. */
  unit_reading: string | null;
  /** Where her unit is in the units' official order, from 0; null along with `unit`. */
  unit_order: number | null;
  /** What she says to a visitor on the landing page; null when she has no greeting. */
  greeting: Greeting | null;
  /** What she says first once a visitor answers her call in the landing page's demo; null when
   * she has none (only she who calls there needs one). */
  call_opener: CallOpener | null;
  /** Her card on the incoming call in the landing page's demo, a portrait WebP in the stands'
   * bucket; null unless the deployment serves the stand assets. The server does not check that it
   * was put there: when it fails to load, show her colour and name instead. */
  call_poster_url: string | null;
  /** Her voxel figure in the landing page's act about memory, a JSON file in the stands' bucket
   * (`Voxels` in `scripts/glb-voxelize.mts`); null unless the deployment serves the stand assets. The
   * server does not check that it was put there: when it fails to load, show her colour and name
   * instead. */
  voxels_url: string | null;
};

/** A character's greeting (GLOSSARY.md「招呼」). */
export type Greeting = {
  /** What she says in Japanese, without its delivery cues. */
  ja: string;
  /** Its Chinese subtitle. */
  subtitle: string;
  /** Its audio, an mp3 in the stands' bucket; null unless the deployment serves the stand assets
   * and she has a voice. The server does not check that it was uploaded: when it fails to load, show
   * the subtitle alone. */
  audio_url: string | null;
};

/** A character's call opener (GLOSSARY.md「开场白」), given as her greeting is, its audio at an
 * address of its own. */
export type CallOpener = Greeting;

/** Where a character's stand comes from. */
export type Stand = {
  /** The outfit she wears unless the user picks another. */
  default_outfit: Outfit;
  /** Her outfit list: `{idol_id, cards}`, each card with its `everyday` clothes and `stage`
   * costume (either may be null), whose `url` and `thumbnail` are relative to the list
   * (docs/deploy.md「立绘素材」). */
  outfits_url: string;
};

/** One outfit of her stand: `id` is `stand/<enzaId>` or `stand_costume/<enzaId>`, and `url` the
 * directory (ending in `/`) holding its `data.json`, `data.atlas` and `data.png`. */
export type Outfit = { id: string; url: string };

export type Conversation = {
  id: string;
  character_id: string;
  created_at: string;
};

/** The last thing in a conversation as a list shows it, a message (without delivery cues),
 * marked `photo` when it is her reply with a photo she sent (not one being generated or not sent
 * after all), or her reach-out, shown as her reply is, marked `reach_out`; or a conversation event
 * other than her ending it; null while it has none. */
export type LastMessage =
  | (Pick<Message, "role" | "text" | "ja" | "zh" | "created_at"> & { photo?: true; reach_out?: true })
  | Pick<ConversationEvent, "type" | "kind" | "created_at" | "gift_name" | "first_day" | "days_ago">
  | null;

/** A character's newest conversation with the user, the last thing in it, whether it has a
 * reach-out the user has not seen (GLOSSARY.md「没看过的搭话」), and whether she has a letter to the
 * user they have not read (GLOSSARY.md「没读过的信」), for the conversation list. */
export type LatestConversation = {
  character_id: string;
  conversation_id: string;
  created_at: string;
  last_message: LastMessage;
  unseen_reach_out: boolean;
  unread_letter: boolean;
};

/** One of her conversations as the past conversations panel lists it; `title` is its conversation
 * title (GLOSSARY.md「对话标题」), null until it is named, if ever. */
export type ListedConversation = Conversation & {
  title: string | null;
  last_message: LastMessage;
  ended: boolean;
};

export type Segment = { ja: string; zh: string };

export type Message = {
  id: number;
  role: "user" | "character";
  text: string | null;
  ja: string | null;
  zh: string | null;
  segments: Segment[];
  created_at: string;
  /** How the turn changed her affinity, on her reply; null where it did not (and always on the user's). */
  affinity: AffinityChange | null;
  /** The photo she sent with her reply (GLOSSARY.md「照片」); none on a reply without one. */
  photo?: Photo;
};

/** How a photo she sent is coming along: being generated, sent, or not sent after all, and why not. */
export type PhotoStatus = { status: "pending" | "ready" | "failed"; reason: string | null };

/** A photo she sent with a reply. */
export type Photo = PhotoStatus & { id: string };

/** Where the picture of a photo she sent is read, once it is sent: only by the user it was sent to. */
export function photoImageUrl(id: string): string {
  return `/api/photos/${encodeURIComponent(id)}/image`;
}

/** How the photo is coming along now, for waiting on one being generated. */
export async function getPhoto(id: string): Promise<PhotoStatus> {
  return json(await api(`/api/photos/${encodeURIComponent(id)}`));
}

/** The kinds of conversation event (GLOSSARY.md「对话事件」): she hung up on the user; the user
 * gave her a gift; she ended the conversation, which can then only be read (GLOSSARY.md「已结束的对话」);
 * she seems unwell, for the user alone. */
export type EventKind = "hung_up" | "gift" | "ended" | "unwell";

/** Something that happened in a conversation that is not a turn, recorded among its messages. */
export type ConversationEvent = {
  type: "event";
  id: number;
  kind: EventKind;
  created_at: string;
  affinity: AffinityChange | null;
  /** A gift record's gift, and its name; other events have none. */
  gift_id?: string;
  gift_name?: string;
  /** Her being unwell's: the first day of her period (ISO date), and how many days before the day
   * it was recorded on; other events have none. */
  first_day?: string;
  days_ago?: number;
};

/** What she said first in a conversation, the user not talking to her (GLOSSARY.md「搭话」): neither a
 * turn nor an event, said as she replies, without delivery cues. */
export type ReachOut = {
  type: "reach_out";
  id: number;
  ja: string;
  zh: string;
  segments: Segment[];
  created_at: string;
};

/** What a conversation's record holds, in order. */
export type Recorded = Message | ConversationEvent | ReachOut;

/** A turn's events: `user`, then `photo` if she sends one (its id, before her first words), any
 * `delta`s, then `photos-used-up` if the user asked for a photo with this hour's used up (when they
 * may ask again, ISO), and `done`, or `error`. `done` says too where the turn left her affinity, null
 * while affinity is off, her ending the conversation after it, recorded after her reply, if she
 * did, what the turn was rewarded with (lib/rewards), null if nothing, and her being unwell,
 * recorded before the user's words, if it was. */
export type TurnEvent =
  | { type: "user"; text: string }
  | { type: "photo"; id: string; status: "pending" }
  | { type: "delta"; segment: number; lang: "ja" | "zh"; text: string }
  | { type: "photos-used-up"; retry_at: string }
  | {
      type: "done";
      message: Message;
      affinity: AffinityStatus | null;
      ended?: ConversationEvent | null;
      rewarded?: Rewarded | null;
      unwell?: ConversationEvent | null;
    }
  | { type: "error"; message: string };

export type Gender = "male" | "female";

/** How the characters treat the user; a field left null keeps its default. */
export type ProducerProfile = {
  form_of_address: string | null;
  gender: Gender | null;
  timezone: string | null;
  birthday: Birthday | null;
  /** Where the producer is, as `/api/cities` found it (GLOSSARY.md「制作人档案」). */
  city?: City | null;
};

/** The profile as the backend answers with it, and whether the deployer can find cities
 * (has a QWeather account): without, the city is neither shown nor any use. */
export type SavedProfile = ProducerProfile & { finds_cities: boolean };

/** A city, district or county, as QWeather names it in Chinese, and where it is. */
export type City = {
  name: string;
  adm2: string;
  adm1: string;
  country: string;
  latitude: number;
  longitude: number;
};

/** The producer's birthday: month and day only, no year. */
export type Birthday = { month: number; day: number };

/** Something a character remembers about the user, with the character it was told to;
 * the name is null for a character no longer configured. */
export type Memory = {
  id: number;
  text: string;
  source_character_id: string;
  source_character_name: string | null;
  created_at: string;
  /** 已被后来的记忆取代：角色不会再想起，删掉取代它的那条就恢复（ADR-0014）。 */
  superseded: boolean;
};

/** During a call each utterance, spoken or typed, is a turn; the backend also says when each
 * segment of her voice starts playing, her emotion in each, who starts and stops speaking,
 * and, when it is about to hang up (the call reached its time or turn limit, a voice service
 * or an own key failed, she hung up), why, and whether the call counted towards the hourly
 * limit. She hanging up, it gives the event that she did, just recorded in the conversation,
 * and for a cooldown when it ends. */
export type CallEvent =
  | Exclude<TurnEvent, { type: "user" | "photo" }>
  | CallUserEvent
  | CallPhotoEvent
  | SegmentPlaying
  | SegmentEmotion
  | Speaking
  | {
      type: "ended";
      reason: BackendEndReason;
      message: string;
      counts: boolean;
      cooldown_until?: string | null;
      event?: ConversationEvent;
    };

/** A call's turn opens with `user` as any turn does, saying too which of her replies in the call
 * it opens, numbered from 1 (a turn replied to afresh opens again, with the next number). */
type CallUserEvent = Extract<TurnEvent, { type: "user" }> & { reply: number };

/** A photo she sends in reply `reply` of the call (GLOSSARY.md「照片」): `pending` as her tag closes,
 * before her first words, as in a typed turn; then, if it comes out while the call is on, once
 * more saying how. One that comes out after the call is over is told of no more: the record has it. */
export type CallPhotoEvent =
  | (Extract<TurnEvent, { type: "photo" }> & { reply: number })
  | { type: "photo"; reply: number; id: string; status: "ready" | "failed"; reason: string | null };

/** Her voice has started playing segment `segment` of reply `reply`, replies being numbered
 * from 1 within the call. Sent as the segment's first audio goes out, so it arrives a little
 * before it is heard; a segment cut off before it is voiced gets none. */
export type SegmentPlaying = { type: "segment-playing"; reply: number; segment: number };

/** How she feels in segment `segment` of reply `reply`, and whether she nods (`yes`) or shakes
 * her head (`no`) at it; `calm` when it could not be told for sure. Sent once the segment is
 * complete and judged, which may be before or after it starts playing; a segment that could
 * not be judged in time gets none. */
export type SegmentEmotion = {
  type: "emotion";
  reply: number;
  segment: number;
  emotion: Emotion;
  nod: Nod["kind"] | null;
};

/** Why the backend hung up (`EndReason` in `call_outcome.py`). */
export type BackendEndReason =
  | "not_connected"
  | "dropped"
  | "duration_limit"
  | "turn_limit"
  | "own_key"
  | "she_hung_up"
  | "cooldown";

export class ApiError extends Error {
  /** Refused because she is in a cooldown with the user (GLOSSARY.md「冷却」) until this time
   * (ISO); null for any other refusal. */
  readonly cooldownUntil: string | null;
  /** Refused because affinity and gifts are not open (GLOSSARY.md「礼物」): the play page shows
   * them closed. */
  readonly giftsClosed: boolean;
  /** Refused because schedules are off (GLOSSARY.md「日程」): the calendar shows the month
   * alone. */
  readonly scheduleClosed: boolean;
  /** What the refusal was, where the backend says so beside its reason (a data package's
   * `broken`, `too_new`, `used_up`…); null where it does not. */
  readonly code: string | null;
  /** Refused for a limit used up until this time (ISO, the 429's `retry_at`); null for any
   * other refusal, or one with no time to wait for. */
  readonly retryAt: string | null;

  constructor(
    message: string,
    readonly status: number,
    {
      cooldownUntil = null,
      giftsClosed = false,
      scheduleClosed = false,
      code = null,
      retryAt = null,
    }: {
      cooldownUntil?: string | null;
      giftsClosed?: boolean;
      scheduleClosed?: boolean;
      code?: string | null;
      retryAt?: string | null;
    } = {},
  ) {
    super(message);
    this.cooldownUntil = cooldownUntil;
    this.giftsClosed = giftsClosed;
    this.scheduleClosed = scheduleClosed;
    this.code = code;
    this.retryAt = retryAt;
  }

  /** The browser is not signed in, or its session has expired. */
  get unauthorized(): boolean {
    return this.status === 401;
  }

  /** Refused for the limit: the user has no turns or calls left this hour, or may take them
   * only on their own keys (GLOSSARY.md「限额」「免限额密钥」). */
  get overLimit(): boolean {
    return this.status === OVER_LIMIT;
  }
}

/** The status of a turn or call refused for the limit. */
const OVER_LIMIT = 429;

/** The status of a turn or call refused while she is in a cooldown with the user, and of what
 * is done with gifts while they are not open, told apart by their bodies. */
const CONFLICT = 409;

/** The status of a request from a user who has not yet agreed to the privacy policy and
 * terms of use. */
export const CONSENT_REQUIRED = 428;

/** The page a response sends the browser to before it can go on, if any: the landing page,
 * to sign in there, when it is not signed in; agreeing to the terms when the user has not yet. */
export function redirectFor(status: number): string | null {
  if (status === 401) return "/";
  if (status === CONSENT_REQUIRED) return "/consent";
  return null;
}

export async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    let message = describe(body?.detail) ?? `请求失败（${res.status}）`;
    if (res.status === OVER_LIMIT) message = overLimit(message, body?.retry_at);
    // Refused while she is in a cooldown, told apart from the limit's 429.
    const cooldownUntil = res.status === CONFLICT && typeof body?.cooldown_until === "string" ? body.cooldown_until : null;
    const giftsClosed = res.status === CONFLICT && body?.gifts_closed === true;
    const scheduleClosed = res.status === CONFLICT && body?.schedule_closed === true;
    const code = typeof body?.code === "string" ? body.code : null;
    const retryAt = res.status === OVER_LIMIT && typeof body?.retry_at === "string" ? body.retry_at : null;
    throw new ApiError(message, res.status, { cooldownUntil, giftsClosed, scheduleClosed, code, retryAt });
  }
  return res.json();
}

/** The user has used up this hour's turns or calls: say when they can go on, in local time.
 * A user an admin set to their own keys only has no time to wait for (`retry_at` null). */
function overLimit(reason: string, retryAt: unknown): string {
  if (retryAt === null) return `${reason}。`;
  const exact = typeof retryAt === "string" ? Date.parse(retryAt) : NaN;
  if (isNaN(exact)) return `${reason}，请稍后再试。`;
  const at = new Date(Math.ceil(exact / 60_000) * 60_000); // shown to the minute, never early
  const time = at.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  const sameDay = at.toDateString() === new Date().toDateString();
  const day = sameDay ? "" : `${at.getMonth() + 1}月${at.getDate()}日 `;
  return `${reason}，${day}${time} 之后可以再用。`;
}

/** The backend's reason for a failure. A rejected request body lists its problems;
 * the first one's message says what to fix. */
function describe(detail: unknown): string | undefined {
  if (typeof detail === "string") return detail;
  const first = Array.isArray(detail) ? detail[0]?.msg : undefined;
  return typeof first === "string" ? first.replace(/^Value error, /, "") : undefined;
}

/** The headers every backend request carries besides the session cookie: the time zone
 * this browser reports. */
export function apiHeaders(init?: HeadersInit): Headers {
  const headers = new Headers(init);
  headers.set("x-timezone", detectTimezone());
  return headers;
}

/** Sends the browser to the page a response says it must go to first, unless it is there. */
export function followRedirect(res: Response): void {
  const to = redirectFor(res.status);
  if (to && window.location.pathname !== to) window.location.assign(to);
}

/** fetch() for the backend API, which every request from the browser goes through: it carries
 * the time zone header, and sends the browser on when it has to sign in, or agree to the terms,
 * first. Read the response with `json` or `expectNoContent` for the backend's reason on failure. */
export async function api(path: string, init: RequestInit = {}): Promise<Response> {
  const res = await fetch(path, { ...init, headers: apiHeaders(init.headers) });
  followRedirect(res);
  return res;
}

/** The ways to sign in the backend offers, and how to reach the deployer (null if the
 * deployer gave none), which a banned user is told. */
export type SignInOptions = { providers: Provider[]; dev_login: boolean; contact: string | null };

/** What the landing page shows that belongs to no one character. `memory_still_url`: its act about
 * memory as one picture, for visitors who see no animation, in the stands' bucket; null unless the
 * deployment serves the stand assets. The server does not check that it was put there: when it
 * fails to load, show only the words. */
export type LandingAssets = { memory_still_url: string | null };

export async function getSignInOptions(): Promise<SignInOptions> {
  return json(await api("/api/auth/providers"));
}

/** An identity the user signs in with. */
export type SignInMethod = { provider: Provider; display_name: string; email: string | null };

/** `id`: who the user is, which this browser keeps their own keys apart by (see `localOwnKeys`).
 * `is_admin`: the user may enter the admin console (`/admin`).
 * `exempting_keys`: the services a call must bring the user's own keys for, all of them, to count
 * towards no limit (GLOSSARY.md「免限额密钥」), in the order of `OWN_SERVICES`; at least one.
 * `reach_outs`: the user's own switch for reach-outs (GLOSSARY.md「搭话」); null where the deployer
 * has them off.
 * `cycles`: the user's own switch for cycles (GLOSSARY.md「周期」); null where the deployer has them
 * off.
 * `moments`: the user's own switch for moments (GLOSSARY.md「朋友圈」); null where the deployer has
 * them off.
 * `sponsor_version`: the version of the deployer's sponsor code (GLOSSARY.md「赞赏」), when it was
 * uploaded, for `sponsorImageUrl`; null when users are not shown it (switched off, or no code). */
export type Account = {
  id: string;
  name: string;
  sign_in_methods: SignInMethod[];
  is_admin: boolean;
  exempting_keys: OwnService[];
  reach_outs: boolean | null;
  cycles: boolean | null;
  moments: boolean | null;
  /** Whether the deployer has letters on (GLOSSARY.md「信」); the letters written stay to be read either way. */
  letters: boolean;
  sponsor_version: string | null;
  /** Whether the deployer has a key for speech synthesis now: her words are read aloud on it for those
   * who keep none of their own in this browser (GLOSSARY.md「朗读」). */
  deployer_tts: boolean;
};

/** Where the deployer's sponsor code of `version` (`Account.sponsor_version`) is read: a new address for
 * each code uploaded, so a browser keeps each for good. */
export function sponsorImageUrl(version: string): string {
  return `/api/sponsor/image?${new URLSearchParams({ v: version })}`;
}

/** Whether this browser is signed in, as one who has yet to agree to the terms too; unlike `api`, it
 * sends the browser nowhere when it is not. */
export async function isSignedInHere(): Promise<boolean> {
  const res = await fetch("/api/account", { headers: apiHeaders() });
  return res.ok || res.status === CONSENT_REQUIRED;
}

/** The signed-in user; sends the browser to sign in, or to agree to the terms, first. */
export async function getAccount(): Promise<Account> {
  return json(await api("/api/account"));
}

/** Turn the user's own switch for reach-outs on or off, for all the characters; refused where the
 * deployer has them off. */
export async function switchReachOuts(on: boolean): Promise<void> {
  await expectNoContent(
    await api("/api/account/reach-outs", {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ on }),
    }),
  );
}

/** Turn the user's own switch for moments on or off, for all the characters; refused where the
 * deployer has them off. */
export async function switchMoments(on: boolean): Promise<void> {
  await expectNoContent(
    await api("/api/account/moments", {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ on }),
    }),
  );
}

/** Turn the user's own switch for cycles on or off, for all the characters; refused where the deployer
 * has them off. */
export async function switchCycles(on: boolean): Promise<void> {
  await expectNoContent(
    await api("/api/account/cycles", {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ on }),
    }),
  );
}

/** Stop signing in with the identity at `provider`; refused for the last one. */
export async function unlinkSignInMethod(provider: Provider): Promise<void> {
  await expectNoContent(await api(`/api/account/sign-in-methods/${provider}`, { method: "DELETE" }));
}

/**
 * Try the user's own LLM, which the server does not keep; fails with what the service said if
 * the try fails. Its address and model as this browser is to keep them.
 */
export async function checkOwnLLM(llm: LocalLLM): Promise<Pick<LocalLLM, "base_url" | "model">> {
  return checkOwnModel("/api/account/keys/llm/check", llm);
}

/** Try the user's own model for memories at its effort, as `checkOwnLLM` does their
 * LLM; what the service said, if the try fails, comes after saying it was this one. */
export async function checkOwnMemoryLLM(llm: LocalModel): Promise<Pick<LocalModel, "base_url" | "model">> {
  return checkOwnModel("/api/account/keys/memory-llm/check", llm);
}

async function checkOwnModel(path: string, model: LocalModel): Promise<Pick<LocalModel, "base_url" | "model">> {
  return json(
    await api(path, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(model),
    }),
  );
}

/** How the model at `baseUrl` named `model` thinks, as models.dev lists it, for the efforts
 * `protocol` sends; null when it is not listed. A hint only (ADR-0019), for the deployer's model
 * and the user's own alike: no key is sent. */
export async function getEffortHint(
  protocol: string,
  baseUrl: string,
  model: string,
  signal?: AbortSignal,
): Promise<EffortHint | null> {
  const query = new URLSearchParams({ protocol, base_url: baseUrl, model });
  return json(await api(`/api/account/keys/llm/efforts?${query}`, { signal }));
}

/** The providers an LLM may be picked from, as models.dev lists them (ADR-0027); none before the
 * server has fetched the catalog. No key is sent. */
export async function getLLMProviders(): Promise<LLMProvider[]> {
  return (await json<{ providers: LLMProvider[] }>(await api("/api/account/keys/llm/providers"))).providers;
}

/** The models the service at `base_url` offers the user's key, as it lists them (ADR-0027); nothing is
 * kept. Fails with what the service said, or with when to ask again if asked too often. */
export async function listOwnLLMModels(protocol: LLMProtocol, base_url: string, api_key: string): Promise<string[]> {
  const listed = await api("/api/account/keys/llm/models", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ protocol, base_url, api_key }),
  });
  return (await json<{ models: string[] }>(listed)).models;
}

/** The models `provider` serves that an LLM may be picked from, each with its own address and protocol. */
export async function getLLMProviderModels(provider: string): Promise<LLMOffer[]> {
  const path = `/api/account/keys/llm/providers/${encodeURIComponent(provider)}/models`;
  return (await json<{ models: LLMOffer[] }>(await api(path))).models;
}

/**
 * Try the user's own key for speech synthesis ("tts") or recognition ("stt", by the service
 * `provider` names), which the server does not keep; fails with what the service said if the try
 * fails. For speech recognition, the region a DashScope key works in, for this browser to keep
 * with it (null for Soniox).
 */
export async function checkOwnSpeechKey(
  service: "tts" | "stt",
  apiKey: string,
  { provider, model }: { provider?: SttProvider; model?: FishAudioModel } = {},
): Promise<{ region?: BailianRegion | null }> {
  return json(
    await api(`/api/account/keys/${service}/check`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ api_key: apiKey, provider, model }),
    }),
  );
}

/**
 * Try the user's own image generation, which the server does not keep, by having it generate one
 * picture at the user's expense; fails with what the service said if the try fails, or because the
 * deployment cannot send photos. Its address and model as this browser is to keep them.
 */
export async function checkOwnImage(image: LocalImage): Promise<Pick<LocalImage, "base_url" | "model">> {
  return json(
    await api("/api/account/keys/image/check", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(image),
    }),
  );
}

/** Delete the user and all their data for good, signing them out everywhere; then forget the own
 * keys this browser keeps for them. */
export async function deleteAccount(userId: string): Promise<void> {
  await expectNoContent(
    await api("/api/account/delete", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ confirm: true }),
    }),
  );
  forgetOwnKeys(userId);
}

/** Sign the user out on every device, this one included, forgetting the own keys this browser
 * keeps for them (none to forget without `userId`); other devices keep theirs. */
export async function logoutEverywhere(userId?: string): Promise<void> {
  await expectNoContent(await api("/api/account/logout-everywhere", { method: "POST" }));
  if (userId) forgetOwnKeys(userId);
}

/** Agree to the privacy policy and terms of use, saying the user is 13 or older. */
export async function agreeToTerms(): Promise<void> {
  await expectNoContent(
    await api("/api/account/consent", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ agree_to_terms: true, at_least_13: true }),
    }),
  );
}

/** Sign in as the user with this name (development only). */
export async function devLogin(name: string): Promise<void> {
  await expectNoContent(
    await api("/api/auth/dev-login", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ name }),
    }),
  );
}

/** Sign this browser out, forgetting the own keys it keeps for the user. Without `userId`, as
 * before the user has agreed to the terms, there are none: keys are only kept after. */
export async function logout(userId?: string): Promise<void> {
  await expectNoContent(await api("/api/auth/logout", { method: "POST" }));
  if (userId) forgetOwnKeys(userId);
}

/** A drink's flavor and kind (GLOSSARY.md「饮品」), as the recipe book's categories. */
export type DrinkFlavor = "sweet" | "bitter" | "sour" | "spicy" | "bubbly";
export type DrinkKind = "girly" | "manly" | "classic" | "classy" | "promo";

type DrinkNames = { id: string; name: string; short_name: string; flavor: DrinkFlavor; kind: DrinkKind };

/** A drink of the catalog (GLOSSARY.md「饮品」「材料」), as the bar counter and the recipe book read it:
 * mixed of parts of each ingredient (Karmotrine `"optional"` when any number will do), on ice or not,
 * aged or not, mixed or blended, big of itself or not, with its recipe card's `page` (null for the
 * few without a card); or bottled, with
 * its line of description and its parts of Karmotrine. No Japanese name, no character's tastes. */
export type Drink =
  | (DrinkNames & {
      method: "mix" | "blend";
      adelhyde: number;
      bronson_extract: number;
      powdered_delta: number;
      flanergide: number;
      karmotrine: number | "optional";
      ice: boolean;
      aged: boolean;
      big: boolean;
      page: number | null;
    })
  | (DrinkNames & { method: "bottle"; description: string; karmotrine: number });

/** `GET /api/bar`: closed, or open with the drinks in catalog order and whether a visit done today
 * would be rewarded (none done yet today, Beijing time, and affinity and gifts open). */
export type BarState = { enabled: false } | { enabled: true; drinks: Drink[]; reward_today: boolean };

export async function getBar(): Promise<BarState> {
  return json(await api("/api/bar"));
}

/** Tokyo's weather as a moment came out: one of seven kinds. */
export type WeatherKind = "clear" | "cloudy" | "overcast" | "fog" | "rain" | "snow" | "thunder";

/** A post of hers in the user's moments (GLOSSARY.md「动态」): her Japanese, its subtitle, when it
 * came out (ISO, with its offset), where she was (GLOSSARY.md「地点」), its Japanese name with a
 * link to it on the map the deployer chooses, null for nowhere, and Tokyo's weather then, its kind
 * and temperature in whole degrees Celsius, null if it could not be had; the other idols who have
 * liked it so far, by character id, in the order they did, and their comments so far, in order.
 * Those yet to show are not there. `image` is where its picture is read (GLOSSARY.md「配图」), the
 * user's alone, null for none. `producer_liked`: whether the user likes it now; `producer_comment`:
 * his comment on it, null for none; `reply`: her reply to that, null until it shows (and for none:
 * which of the two is never told). */
export type Moment = {
  id: number;
  character_id: string;
  ja: string;
  zh: string;
  image: string | null;
  place: { name: string; map: string } | null;
  weather: { kind: WeatherKind; temperature: number } | null;
  posted_at: string;
  likes: string[];
  comments: MomentComment[];
  producer_liked: boolean;
  producer_comment: ProducerComment | null;
  reply: { ja: string; zh: string } | null;
};

/** A comment on a moment by another idol: her Japanese and its subtitle. */
export type MomentComment = { character_id: string; ja: string; zh: string };

/** The user's comment on a moment: as he wrote it, but for the spaces around it, and when (ISO). */
export type ProducerComment = { text: string; commented_at: string };

/** How many characters his comment may have at most, but for the spaces around it; the backend says
 * so too (422). */
export const COMMENT_LENGTH = 140;

/** Likes one of his moments, or no longer, however he did. Gone (another's, or over 30 days old): 404. */
export async function likeMoment(id: number, liked: boolean): Promise<void> {
  await expectNoContent(await api(`/api/moments/${id}/like`, { method: liked ? "PUT" : "DELETE" }));
}

/** Comments on one of his moments, once (409 again): what is kept of it. */
export async function commentOnMoment(id: number, text: string): Promise<ProducerComment> {
  return json(
    await api(`/api/moments/${id}/comment`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text }),
    }),
  );
}

/** Deletes his comment on one of his moments, her reply to it with it. */
export async function deleteMomentComment(id: number): Promise<void> {
  await expectNoContent(await api(`/api/moments/${id}/comment`, { method: "DELETE" }));
}

/** The user's moments of the last 30 days that have come out, newest first, all at once. Refused while
 * the deployer or the user has moments off (409). */
export async function getMoments(): Promise<Moment[]> {
  const body: { moments: Moment[] } = await json(await api("/api/moments"));
  return body.moments;
}

/** The user's letters (GLOSSARY.md「信」), the latest first. */
export async function listLetters(): Promise<LetterSummary[]> {
  const body: { letters: LetterSummary[] } = await json(await api("/api/letters"));
  return body.letters;
}

/** One of the user's letters, to read. */
export async function getLetter(id: number): Promise<Letter> {
  return json(await api(`/api/letters/${id}`));
}

/** Has the letter read, on every device. */
export async function markLetterRead(id: number): Promise<void> {
  const res = await api(`/api/letters/${id}/read`, { method: "PUT" });
  if (!res.ok) await json(res);
}

/** Has the letter popped up, on every device, so it does not again. */
export async function markLetterPopped(id: number): Promise<void> {
  await expectNoContent(await api(`/api/letters/${id}/popped`, { method: "PUT" }));
}

/** Deletes the letter, and her voice reading it, for good. */
export async function deleteLetter(id: number): Promise<void> {
  await expectNoContent(await api(`/api/letters/${id}`, { method: "DELETE" }));
}

/** Whether a moment, or her reply to the user's comment, has come out since they last read the
 * timeline (`getMoments`), on any device. Refused while the deployer or the user has moments off (409). */
export async function getMomentsUnseen(): Promise<boolean> {
  const body: { unseen: boolean } = await json(await api("/api/moments/unseen"));
  return body.unseen;
}

/** Comes into the bar, bringing the user's own LLM (as `own_keys`) as a text turn does. Once the
 * server took it, the visit's first call, to be followed as it comes: `visit` first, then her lines
 * up to her order. Refused while the bar is closed (409), or over the limit (429, `retryAt` saying
 * when). Aborting `signal` closes the call, and the server leaves the visit. */
export async function enterBar(userId: string, signal?: AbortSignal): Promise<AsyncGenerator<VisitEvent>> {
  const res = await api("/api/bar/visits", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ own_keys: turnOwnKeys(userId) }),
    signal,
  });
  if (!res.ok) await json(res);
  return serverSentEvents<VisitEvent>(res);
}

/** Serves her what the bar counter holds (lib/barMixer `served`). Once the server took it, the
 * call it set off, to be followed as it comes: the producer's 「请慢用」, her reaction, and her next
 * order or her goodbye. Refused if it is none of the drinks (422 `broken_drink`), while she is not
 * waiting for one (409, a double tap), or with the visit gone (410 `visit_gone`). */
export async function serveBarDrink(
  visitId: string,
  served: ServedBody,
  signal?: AbortSignal,
): Promise<AsyncGenerator<VisitEvent>> {
  const res = await api(`/api/bar/visits/${encodeURIComponent(visitId)}/serves`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(served),
    signal,
  });
  if (!res.ok) await json(res);
  return serverSentEvents<VisitEvent>(res);
}

/** Tries again the call the visit stopped before, failing (a `failed` event). Once the server took
 * it, the call to be followed as it comes, from its first line on, without the producer's 「请慢用」
 * of a drink served. Refused while no call failed (409 `not_failed`), or with the visit gone (410
 * `visit_gone`, as after her farewell failed to be written down). */
export async function retryBarVisit(visitId: string, signal?: AbortSignal): Promise<AsyncGenerator<VisitEvent>> {
  const res = await api(`/api/bar/visits/${encodeURIComponent(visitId)}/retry`, { method: "POST", signal });
  if (!res.ok) await json(res);
  return serverSentEvents<VisitEvent>(res);
}

/** Leaves the visit: over, not to be come back to. `keepalive` as the page goes away. */
export async function leaveBarVisit(visitId: string, { keepalive = false } = {}): Promise<void> {
  const path = `/api/bar/visits/${encodeURIComponent(visitId)}`;
  await expectNoContent(await api(path, { method: "DELETE", keepalive }));
}

/** The user's stats (GLOSSARY.md「统计」), in the producer's time zone, the lower part over
 * `range` (all of it unless given). */
export async function getStats(range: StatsRange = "all"): Promise<Stats> {
  return json(await api(`/api/stats?range=${range}`));
}

/** What importing a data package added (`data_package.Imported`). */
export type DataPackageImported = {
  conversations: number;
  photos: number;
  memories: number;
  /** Whether the producer profile was overwritten. */
  profile: boolean;
  /** Her conversations not imported: she is not on this deployment. */
  skipped: { character_name: string; conversations: number }[];
  /** The periods written down that were imported (GLOSSARY.md「周期」). */
  cycles: number;
  /** Those not: of a character not here, out of bounds, after today, or overlapping another. */
  cycles_skipped: number;
};

/** Import a data package, the file itself as the body, streamed: the categories `include` names
 * and the package holds. Refusals carry the backend's `code` (`ApiError.code`). */
export async function importDataPackage(file: Blob, include: readonly string[]): Promise<DataPackageImported> {
  const query = new URLSearchParams({ include: include.join(",") });
  return json(
    await api(`/api/account/data-package?${query}`, {
      method: "POST",
      headers: { "Content-Type": "application/zip" },
      body: file,
    }),
  );
}

/** Ask before downloading a data package whether the user could export one now, refused as the
 * export would be (signed out, `busy`), so the page can say so: a refused download shows the browser
 * only JSON. Not refused here, the download can still fail in the browser, beaten to it in between or
 * failing as the package is written. */
export async function checkDataPackageExport(include: readonly string[]): Promise<void> {
  const query = new URLSearchParams({ include: include.join(",") });
  await expectNoContent(await api(`/api/account/data-package/export-check?${query}`));
}

export async function getProfile(): Promise<SavedProfile> {
  return json(await api("/api/profile"));
}

/** The cities by `name`, the likeliest first, on the deployer's QWeather account. */
export async function searchCities(name: string): Promise<City[]> {
  const query = new URLSearchParams({ q: name });
  return (await json<{ cities: City[] }>(await api(`/api/cities?${query}`))).cities;
}

/** The city nearest where the browser says the user is; null if none. The spot is not kept. */
export async function nearestCity(latitude: number, longitude: number): Promise<City | null> {
  const query = new URLSearchParams({ latitude: String(latitude), longitude: String(longitude) });
  return (await json<{ city: City | null }>(await api(`/api/cities/nearest?${query}`))).city;
}

export async function saveProfile(profile: ProducerProfile): Promise<SavedProfile> {
  return json(
    await api("/api/profile", {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(profile),
    }),
  );
}

/** Newest first. */
export async function listMemories(): Promise<Memory[]> {
  return json(await api("/api/memories"));
}

export async function deleteMemory(id: number): Promise<void> {
  await expectNoContent(await api(`/api/memories/${id}`, { method: "DELETE" }));
}

export async function clearMemories(): Promise<void> {
  await expectNoContent(await api("/api/memories", { method: "DELETE" }));
}

/** Checks a response that carries no body. */
export async function expectNoContent(res: Response): Promise<void> {
  if (!res.ok) await json(res);
}

export async function listCharacters(): Promise<Character[]> {
  return json(await api("/api/characters"));
}

/** Her conversations with the user, newest first: the first is her current one
 * (GLOSSARY.md「当前对话」). */
export async function listConversations(characterId: string): Promise<ListedConversation[]> {
  return json(await api(`/api/conversations?character_id=${encodeURIComponent(characterId)}`));
}

/** Deletes a past conversation for good (GLOSSARY.md「历史对话」); her current one is refused (409). */
export async function deleteConversation(id: string): Promise<void> {
  await expectNoContent(await api(`/api/conversations/${encodeURIComponent(id)}`, { method: "DELETE" }));
}

/** Each character's newest conversation with the user, with its last message; characters
 * the user has never talked to are left out. */
export async function listLatestConversations(): Promise<LatestConversation[]> {
  return json(await api("/api/conversations/latest"));
}

export async function createConversation(characterId: string): Promise<Conversation> {
  return json(
    await api("/api/conversations", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ character_id: characterId }),
    }),
  );
}

/** The conversation's record: its messages and conversation events, in order. */
export async function listMessages(conversationId: string): Promise<Recorded[]> {
  return json(await api(`/api/conversations/${conversationId}/messages`));
}

/** Whether the user's text turns and calls would count towards nothing (on their own keys alone),
 * as the server counts them: GLOSSARY.md「限额」「自带密钥」. */
export type LimitExemption = { turns: boolean; calls: boolean };

/** Asks the server whether keeping the user's own keys for `own` exempts their turns and calls
 * from the hourly limit, naming those services but bringing none of the keys. */
export async function getLimitExemption(own: readonly OwnService[]): Promise<LimitExemption> {
  const path = "/api/account/keys/exemption";
  return json(await api(own.length ? `${path}?own=${own.join(",")}` : path));
}

/** What a call needs before it starts: the STUN/TURN servers, how long it may last in seconds
 * (null for no limit), and whether it is exempt from the hourly limit (on the user's own keys
 * alone). Fails with the reason when calls are unavailable. */
export type CallSetup = { iceServers: RTCIceServer[]; maxCallSeconds: number | null; callExempt: boolean };

/** Asked before a call into `conversationId` that is to bring the user's own keys for `own`,
 * naming those services but bringing none of the keys: the call itself brings them. Refused, as
 * the call would be, while she is in a cooldown. */
export async function getCallSetup(conversationId: string, own: readonly OwnService[]): Promise<CallSetup> {
  const path = `/api/ice-servers?conversation=${encodeURIComponent(conversationId)}`;
  return json(await api(own.length ? `${path}&own=${own.join(",")}` : path));
}

/**
 * Sends one text turn, bringing the user's own LLM (as `own_keys`) if this browser keeps one for
 * them, and the model of their own key for speech synthesis, without the key, for her to write her
 * delivery cues as it reads them (`read_aloud_model`, GLOSSARY.md「朗读」); and yields the reply's
 * server-sent events as they arrive.
 */
export async function* sendTurn(conversationId: string, text: string, userId: string): AsyncGenerator<TurnEvent> {
  const res = await api(`/api/conversations/${conversationId}/turns`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ text, own_keys: turnOwnKeys(userId), read_aloud_model: readAloudModel(userId) }),
  });
  yield* serverSentEvents<TurnEvent>(res);
}

/**
 * Her line read aloud (GLOSSARY.md「朗读」), as mp3, on the user's own key for speech synthesis if this
 * browser keeps one for them (as `own_keys`), else on the deployer's. Throws as `json` does when it is
 * not: a failure on the user's own key has the code `own_key`.
 */
export async function readAloud(said: Said, userId: string): Promise<ArrayBuffer> {
  const line = said.kind === "reply" ? `messages/${said.id}` : `reach-outs/${said.id}`;
  const res = await api(`/api/conversations/${said.conversationId}/${line}/read-aloud`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ own_keys: readAloudOwnKeys(userId) }),
  });
  if (!res.ok) await json(res);
  return res.arrayBuffer();
}

/** The server-sent events of a response, each as it arrives; a refusal thrown as `json` throws it. */
async function* serverSentEvents<T>(res: Response): AsyncGenerator<T> {
  if (!res.ok || !res.body) {
    await json(res);
    return;
  }
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    let end;
    while ((end = buffer.indexOf("\n\n")) >= 0) {
      const frame = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      const data = frame
        .split("\n")
        .filter((line) => line.startsWith("data: "))
        .map((line) => line.slice(6))
        .join("\n");
      if (data) yield JSON.parse(data) as T;
    }
  }
}
