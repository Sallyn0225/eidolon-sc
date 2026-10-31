// 信（GLOSSARY.md「信」）：她在特别的日子写给制作人的一封信。这里管接口上的信长什么样、页首信封键有没有点、
// 拆开以后每个字什么时候写出来（时间轴）、配乐从哪里放起才让高潮落在签名上。时间轴的常量沿用停服前「她的信」。

/** 写信的场合（后端 letter_prompt.Occasion）。几个场合合在一封时按这个顺序列出。 */
export type Occasion =
  | "intimate"
  | "close"
  | "complete"
  | "her_birthday"
  | "producer_birthday"
  | "anniversary";

/** 所有的信列表里的一封：读没读过、弹没弹过在每台设备上都一样。 */
export type LetterSummary = {
  id: number;
  character_id: string;
  occasions: Occasion[];
  /** 写信那天（制作人那边的日期），`YYYY-MM-DD`。 */
  day: string;
  read: boolean;
  popped: boolean;
};

/**
 * 这封信的配乐（后端 letter_music.py）：曲子的地址（在立绘素材的存储桶里，部署者没上传时取不到），
 * 高潮从第几秒开始（没有为 null）、高潮之后放到第几秒淡出（null 是放到结束）、太短的那首循环哪一段。
 */
export type LetterMusic = {
  url: string;
  climax: number | null;
  fade: number | null;
  loop: [number, number] | null;
};

/** 读一封：抬头和各段（日语已去掉语气提示）、信末的签名、每块语音的地址；没有语音、配乐时为 null。 */
export type Letter = {
  id: number;
  character_id: string;
  occasions: Occasion[];
  day: string;
  salutation: string;
  paragraphs: { ja: string; zh: string }[];
  /** 她手写的签名图（透明底），没有时 `image` 为 null，照 `text` 用信上的字体写出来。 */
  signature: { image: string | null; text: string };
  /** 她念这封信的 mp3，一块一个：第 0 块是抬头，之后每段一块。部署者没有语音合成、合成失败时为 null。 */
  voice: string[] | null;
  /** 部署者没配立绘素材地址、配乐清单里没有这些场合时为 null。 */
  music: LetterMusic | null;
};

/** 页首的信封键：部署者开着信，或者用户已经有信时才出现。 */
export function showsLetterButton(lettersOn: boolean, letters: LetterSummary[] | null): boolean {
  return lettersOn || (letters?.length ?? 0) > 0;
}

/** 页首的信封键带不带点：有没读过的信。 */
export function hasUnread(letters: LetterSummary[] | null): boolean {
  return letters?.some((l) => !l.read) ?? false;
}

/** 谁有没读过的信（GLOSSARY.md「没读过的信」）：对话列表上她那一行名字后面一枚小信封。 */
export function unreadFrom(letters: LetterSummary[] | null): Set<string> {
  return new Set((letters ?? []).filter((l) => !l.read).map((l) => l.character_id));
}

/** 她的对话页页首的信封键点开的：只有她写的，从新到旧（列表接口给的顺序）。 */
export function hersOf(letters: LetterSummary[] | null, characterId: string): LetterSummary[] {
  return (letters ?? []).filter((l) => l.character_id === characterId);
}

/**
 * 手上的信落后了：最新对话列表（每分钟轮询一次）上某一行说她有没读过的信，手上的信里却没有，或者反过来
 * （她又写了一封、在别的设备上读了、删了）。还没拉到信时不算，载入时本来就要拉。
 */
export function lettersBehind(
  letters: LetterSummary[] | null,
  latest: Record<string, { unread_letter: boolean }>,
): boolean {
  if (letters === null) return false;
  const unread = unreadFrom(letters);
  return Object.entries(latest).some(([id, row]) => row.unread_letter !== unread.has(id));
}

/** 现在在哪：在对话页上、通话中都不弹信。 */
export type PopWhere = { onConversationPage: boolean; inCall: boolean };

/**
 * 该弹哪一封（GLOSSARY.md「没读过的信」）：没读过、也没弹过的里最早的一封；跳过的已经弹过，不再弹。
 * 在对话页上（正和谁聊着）、通话中都不弹，等离开再弹。什么时候问它（进入外壳、离开对话页，每次打开网站最多弹一封）由 `LetterProvider` 管。
 */
export function letterToPop(letters: LetterSummary[] | null, where: PopWhere): LetterSummary | null {
  if (where.onConversationPage || where.inCall) return null;
  const waiting = (letters ?? []).filter((l) => !l.read && !l.popped);
  return waiting.at(-1) ?? null; // 列表从新到旧，最早的在最后
}

/** 所有的信，分好组：没读过的在最上面；其余按写信那天的月份分组（`YYYY-MM`）。组和组里都从新到旧。 */
export type GroupedLetters = { unread: LetterSummary[]; months: { month: string; letters: LetterSummary[] }[] };

export function groupLetters(letters: LetterSummary[]): GroupedLetters {
  const unread = letters.filter((l) => !l.read);
  const months = new Map<string, LetterSummary[]>();
  const read = letters.filter((l) => l.read).sort((a, b) => (a.day === b.day ? 0 : a.day < b.day ? 1 : -1));
  for (const letter of read) {
    const month = letter.day.slice(0, 7);
    months.set(month, [...(months.get(month) ?? []), letter]);
  }
  return { unread, months: [...months].map(([month, letters]) => ({ month, letters })) };
}

/** 分组的月份：「10月」，不是今年的带上年份。 */
export function letterMonth(month: string, thisYear: number): string {
  const [year, m] = month.split("-").map(Number);
  return year === thisYear ? `${m}月` : `${year}年${m}月`;
}

/** 信封上的日期：「10月31日」，不是今年的带上年份。 */
export function letterDay(day: string, thisYear: number): string {
  const [year, month, date] = day.split("-").map(Number);
  return year === thisYear ? `${month}月${date}日` : `${year}年${month}月${date}日`;
}

/** 信纸展开后，留多久才开始写（秒）：她这时还没开口。 */
export const LEAD_IN = 1.2;

/** 抬头之后、段与段之间停多久（秒）。 */
export const PAUSES = { afterSalutation: 0.6, betweenParagraphs: 0.9 };

/** 最后一块写完以后隔多久签名（秒），和签名从左到右写出来要多久。 */
export const SIGNATURE_DELAY = 0.8;
export const SIGNATURE_SECONDS = 1.6;

/** 没有语音时，估一个字念多久（秒）。 */
export const SECONDS_PER_CHAR = 0.15;

/** 信上的一块：抬头或一段正文（带字幕），和它在时间轴上从几秒写到几秒。 */
export type Part = {
  kind: "salutation" | "paragraph";
  /** 一个字一项（按码点拆，不拆坏代理对）。 */
  chars: string[];
  zh: string | null;
  start: number;
  end: number;
  /** 每个字从第几秒起显出来，和 `chars` 一一对应，单调不减。 */
  at: number[];
};

/** 写完一个字之后，下一个字要多等的份量（一个字算 1）：念到标点时停一下。 */
function pauseAfter(char: string): number {
  if ("。！？!?".includes(char)) return 3;
  if ("、，,".includes(char)) return 1.5;
  if ("…‥".includes(char)) return 0.8;
  return 0;
}

/** 把一块字摊到 [start, end] 上：每个字占 1 份，标点后面多停几份，最后一个字在 end 之前写出来。 */
function spread(chars: string[], start: number, end: number): number[] {
  const offsets: number[] = [];
  let total = 0;
  for (const char of chars) {
    offsets.push(total);
    total += 1 + pauseAfter(char);
  }
  const span = Math.max(0, end - start);
  return offsets.map((o) => start + (total > 0 ? (span * o) / total : 0));
}

/**
 * 信上的各块，按写的顺序，带时间轴：信纸展开后留 `LEAD_IN`，一块接一块，抬头之后、段与段之间各停一下。
 * 每块写多久：给了 `durations`（每块语音的实际时长，秒，和块数一样多）就照它，没给时按字数估。
 */
export function partsOf(letter: Pick<Letter, "salutation" | "paragraphs">, durations?: number[] | null): Part[] {
  const blocks: Omit<Part, "start" | "end" | "at">[] = [
    { kind: "salutation", chars: Array.from(letter.salutation), zh: null },
    ...letter.paragraphs.map((p) => ({ kind: "paragraph" as const, chars: Array.from(p.ja), zh: p.zh })),
  ];
  const lengths =
    durations?.length === blocks.length
      ? durations
      : blocks.map((b) => Math.max(1, b.chars.length * SECONDS_PER_CHAR));
  let at = LEAD_IN;
  return blocks.map((block, i) => {
    const start = at;
    const end = start + lengths[i];
    at = end + (i === 0 ? PAUSES.afterSalutation : PAUSES.betweenParagraphs);
    return { ...block, start, end, at: spread(block.chars, start, end) };
  });
}

/** 到第 `t` 秒，这一块写出了几个字。 */
export function written(part: Part, t: number): number {
  let n = 0;
  while (n < part.at.length && part.at[n] <= t) n++;
  return n;
}

/** 第几秒开始签名：最后一块写完之后。 */
export function signsAt(parts: Part[]): number {
  return (parts.length > 0 ? parts[parts.length - 1].end : 0) + SIGNATURE_DELAY;
}

/** 整封信在第几秒写完：签名写完。 */
export function finishesAt(parts: Part[]): number {
  return signsAt(parts) + SIGNATURE_SECONDS;
}

/** 拆开以后，语音最多等这么久取下、解码好（毫秒）；等的时候信纸上的字停着，等她开口再写。等不到就不要声音，按字数估。 */
export const VOICE_WAIT_MS = 10000;

/** 跟着声音写时，音频的时钟这么久没往前走（被系统打断、挂起）就改按时钟写，并且停掉声音，免得声音和字对不上（毫秒）。 */
export const STALL_MS = 4000;

/**
 * 写到第几秒怎么算。跟着声音：音频时钟上 `base` 是开口算起的第 0 秒，`heard` 是上一次读到的音频时钟，
 * `movedAt` 是它上一次往前走的时刻（毫秒，performance.now）。按时钟：从第 `from` 秒、`since` 毫秒时接着走。
 */
export type LetterClock =
  | { by: "voice"; base: number; heard: number; movedAt: number }
  | { by: "timer"; from: number; since: number };

/** 跟着声音写，开口那一刻在音频时钟的 `base` 秒，现在是 `now` 毫秒。 */
export function voiceClock(base: number, now: number): LetterClock {
  return { by: "voice", base, heard: Number.NaN, movedAt: now };
}

/** 按时钟写，从第 0 秒、现在（`now` 毫秒）起。 */
export function timerClock(now: number): LetterClock {
  return { by: "timer", from: 0, since: now };
}

/**
 * 到 `now` 毫秒写到第几秒；跟着声音时 `audioTime` 是这时的音频时钟（秒）。音频时钟超过 `STALL_MS` 没往前走，
 * 就改成按时钟、从停下的那一秒接着走（返回的 `clock.by` 变成 "timer"，调用的一方据此停掉声音）。
 */
export function tick(clock: LetterClock, now: number, audioTime: number): { clock: LetterClock; at: number } {
  if (clock.by === "timer") return { clock, at: clock.from + (now - clock.since) / 1000 };
  const at = Math.max(0, audioTime - clock.base);
  if (audioTime !== clock.heard) return { clock: { ...clock, heard: audioTime, movedAt: now }, at };
  if (now - clock.movedAt > STALL_MS) return { clock: { by: "timer", from: at, since: now }, at };
  return { clock, at };
}

/** 没有高潮的那首，签名写完以后再放多久才淡出（秒）。 */
export const MUSIC_TAIL = 4;

/** 曲子的一段排在时间轴上：信纸展开算起第 `at` 秒，放曲子的第 `from` 秒到第 `to` 秒（null 是放到曲子结束）。 */
export type MusicSegment = { at: number; from: number; to: number | null };

/**
 * 配乐怎么放：从曲子（循环展开以后）的第 `offset` 秒放起，循环段多放 `loops` 遍；排成时间轴上的几段；
 * 时间轴上第 `fadeAt` 秒开始淡出（null 是放到结束）。
 */
export type MusicPlan = { offset: number; loops: number; segments: MusicSegment[]; fadeAt: number | null };

/**
 * 配乐对齐（时间轴的第 0 秒是信纸展开，配乐这时开始放）：签名时刻 `signsAt` 为 S、高潮起点为 P。P ≥ S 时从第
 * P − S 秒放起，高潮正好落在签名上；P < S 时从头放，高潮早一点到，不硬对；没有高潮的从头放。有循环段 [a, b] 的那首
 * （高潮在 b 之后）放到 b 再接回 a，一遍一遍，直到高潮能落在签名上或之后，再接尾段，照样把高潮对在签名上。
 * 签名之后放到淡出点淡出，淡出点早于签名写完（`finishesAt`）时等写完再淡出；没有高潮的那首签名写完 `MUSIC_TAIL` 秒后淡出。
 */
export function musicPlan(music: Pick<LetterMusic, "climax" | "fade" | "loop">, signsAt: number, finishesAt: number): MusicPlan {
  const { climax, fade, loop } = music;
  if (climax === null) {
    return { offset: 0, loops: 0, segments: [{ at: 0, from: 0, to: null }], fadeAt: finishesAt + MUSIC_TAIL };
  }
  const length = loop ? loop[1] - loop[0] : 0;
  const loops = loop && length > 0 ? Math.max(0, Math.ceil((signsAt - climax) / length)) : 0;
  const offset = Math.max(0, climax + loops * length - signsAt);
  // 循环展开以后的曲子：放到 b，接回 a 再放 loops 遍，然后是尾段。
  const pieces: { from: number; to: number | null }[] =
    loop && loops > 0
      ? [{ from: 0, to: loop[1] }, ...Array.from({ length: loops }, () => ({ from: loop[0], to: loop[1] })), { from: loop[1], to: null }]
      : [{ from: 0, to: null }];
  const segments: MusicSegment[] = [];
  let at = 0 - offset;
  for (const piece of pieces) {
    segments.push({ at, ...piece });
    if (piece.to !== null) at += piece.to - piece.from;
  }
  return {
    offset,
    loops,
    segments: segmentsFrom(segments, 0),
    fadeAt: fade === null ? null : Math.max(fade + loops * length - offset, finishesAt),
  };
}

/** 从时间轴的第 `t` 秒起还要放的几段：已经放完的不要，正放到一半的从这一秒接着放。 */
export function segmentsFrom(segments: MusicSegment[], t: number): MusicSegment[] {
  return segments
    .filter((s) => s.to === null || s.at + (s.to - s.from) > t)
    .map((s) => (s.at >= t ? s : { at: t, from: s.from + (t - s.at), to: s.to }));
}
