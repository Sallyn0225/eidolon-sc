import { describe, expect, it } from "vitest";

import {
  LEAD_IN,
  MUSIC_TAIL,
  STALL_MS,
  finishesAt,
  groupLetters,
  hasUnread,
  hersOf,
  letterDay,
  letterMonth,
  letterToPop,
  lettersBehind,
  musicPlan,
  partsOf,
  segmentsFrom,
  showsLetterButton,
  signsAt,
  tick,
  timerClock,
  unreadFrom,
  voiceClock,
  written,
  type LetterMusic,
  type LetterSummary,
} from "@/lib/letter";

/** 每块的起止，四舍五入到毫秒，免得浮点数的尾巴。 */
function spans(parts: { start: number; end: number }[]): number[][] {
  return parts.map((p) => [p.start, p.end].map((t) => Math.round(t * 1000) / 1000));
}

const letter = {
  salutation: "Pさんへ",
  paragraphs: [
    { ja: "ありがとう。", zh: "谢谢。" },
    { ja: "またね", zh: "再见" },
  ],
};

function summary(read: boolean): LetterSummary {
  return { id: 1, character_id: "mano", occasions: ["close"], day: "2026-10-31", read, popped: false };
}

describe("时间轴", () => {
  it("没有语音时按字数估：一个字 0.15 秒，一块至少 1 秒；抬头后停 0.6 秒，段与段之间停 0.9 秒", () => {
    const parts = partsOf(letter);
    expect(spans(parts)).toEqual([
      [1.2, 2.2], // 4 个字，不到 1 秒算 1 秒
      [2.8, 3.8], // 6 个字，0.9 秒，算 1 秒
      [4.7, 5.7],
    ]);
  });

  it("给了每块的实际时长就照它排", () => {
    const parts = partsOf(letter, [2, 3, 1.5]);
    expect(spans(parts)).toEqual([
      [1.2, 3.2],
      [3.8, 6.8],
      [7.7, 9.2],
    ]);
  });

  it("时长和块数对不上时当作没有，按字数估", () => {
    expect(partsOf(letter, [2, 3])).toEqual(partsOf(letter));
  });

  it("每个字的时刻在这一块之内、单调不减，标点后面多停", () => {
    const [, first] = partsOf(letter, [2, 3, 1.5]);
    expect(first.at[0]).toBe(first.start);
    expect(first.at.every((t, i) => i === 0 || t >= first.at[i - 1])).toBe(true);
    expect(first.at[first.at.length - 1]).toBeLessThan(first.end);
    // 「ありがとう。」：前五个字各一份，最后的「。」之后多停三份，所以「。」落在 5/9 处。
    expect(first.at[5]).toBeCloseTo(3.8 + (3 * 5) / 9);
  });

  it("写到第几秒有几个字，拆开时一个都没有", () => {
    const [salutation] = partsOf(letter);
    expect(written(salutation, 0)).toBe(0);
    expect(written(salutation, LEAD_IN)).toBe(1);
    expect(written(salutation, 100)).toBe(4);
  });

  it("签名在最后一块写完 0.8 秒后开始，写 1.6 秒", () => {
    const parts = partsOf(letter, [2, 3, 1.5]);
    expect(signsAt(parts)).toBeCloseTo(10);
    expect(finishesAt(parts)).toBeCloseTo(11.6);
  });

  it("按码点拆字，不拆坏代理对", () => {
    const [salutation] = partsOf({ salutation: "𠮷野さん", paragraphs: [] });
    expect(salutation.chars).toEqual(["𠮷", "野", "さ", "ん"]);
  });
});

describe("跟着她的声音写", () => {
  it("有语音时按每块的实际时长排：每个字落在她念这一块的时候，签名跟着最后一块念完", () => {
    const voiced = partsOf(letter, [2.5, 4, 0.5]);
    const estimated = partsOf(letter);
    expect(spans(voiced)).toEqual([
      [1.2, 3.7],
      [4.3, 8.3],
      [9.2, 9.7],
    ]);
    for (const part of voiced) {
      expect(part.at.every((t) => t >= part.start && t < part.end)).toBe(true);
    }
    expect(signsAt(voiced)).toBeCloseTo(10.5);
    expect(signsAt(voiced)).not.toBeCloseTo(signsAt(estimated));
  });

  it("写到第几秒跟着音频时钟走，开口那一刻是第 0 秒", () => {
    let clock = voiceClock(20, 1000);
    let at: number;
    ({ clock, at } = tick(clock, 1000, 20));
    expect(at).toBe(0);
    ({ clock, at } = tick(clock, 1500, 20.5));
    expect(at).toBeCloseTo(0.5);
    // 音频时钟走得比墙上的钟慢（设备忙），字照样跟着声音。
    ({ clock, at } = tick(clock, 3500, 21));
    expect(at).toBeCloseTo(1);
    expect(clock.by).toBe("voice");
  });

  it("音频时钟停住不到 STALL_MS 时字也停着，等声音", () => {
    let { clock } = tick(voiceClock(0, 0), 0, 3);
    let at: number;
    ({ clock, at } = tick(clock, STALL_MS, 3));
    expect(clock.by).toBe("voice");
    expect(at).toBe(3);
  });

  it("音频时钟停住超过 STALL_MS 就改按时钟，从停下的那一秒接着写", () => {
    let { clock } = tick(voiceClock(0, 0), 0, 3);
    let at: number;
    ({ clock, at } = tick(clock, STALL_MS + 1, 3));
    expect(clock.by).toBe("timer");
    expect(at).toBe(3);
    // 之后不再看音频时钟。
    ({ clock, at } = tick(clock, STALL_MS + 2001, 3));
    expect(at).toBeCloseTo(5);
  });

  it("没有声音时按时钟从第 0 秒写", () => {
    expect(tick(timerClock(1000), 2500, 0).at).toBeCloseTo(1.5);
  });
});

function music(climax: number | null, fade: number | null = null, loop: [number, number] | null = null): LetterMusic {
  return { url: "https://stands.example.com/letters/music/close.m4a", climax, fade, loop };
}

/** 她的生日那首：79 秒，3–60 秒那段循环，64 秒是高潮。 */
const herBirthday = music(64, null, [3, 60]);

describe("配乐对齐", () => {
  it("高潮在签名之后（P ≥ S）：从第 P − S 秒开始放，高潮正好落在签名上", () => {
    const plan = musicPlan(music(71), 40, 41.6);
    expect(plan).toEqual({ offset: 31, loops: 0, segments: [{ at: 0, from: 31, to: null }], fadeAt: null });
  });

  it("高潮在签名之前（P < S）：从头放，高潮早一点到", () => {
    const plan = musicPlan(music(71), 90, 91.6);
    expect(plan.offset).toBe(0);
    expect(plan.segments).toEqual([{ at: 0, from: 0, to: null }]);
  });

  it("没有高潮的从头放，签名写完 MUSIC_TAIL 秒后淡出", () => {
    const plan = musicPlan(music(null), 40, 41.6);
    expect(plan.segments).toEqual([{ at: 0, from: 0, to: null }]);
    expect(plan.fadeAt).toBeCloseTo(41.6 + MUSIC_TAIL);
  });

  it("签名之后放到淡出点淡出；淡出点早于签名写完时，等签名写完再淡出", () => {
    expect(musicPlan(music(101, 148), 60, 61.6).fadeAt).toBe(148 - 41);
    expect(musicPlan(music(101, 148), 120, 121.6).fadeAt).toBe(148);
    expect(musicPlan(music(101, 148), 160, 161.6).fadeAt).toBe(161.6);
  });

  it("她的生日那首够长时不循环，照样把高潮对在签名上", () => {
    const plan = musicPlan(herBirthday, 30, 31.6);
    expect(plan.loops).toBe(0);
    expect(plan.segments).toEqual([{ at: 0, from: 34, to: null }]);
  });

  it("她的生日那首不够长时，3–60 秒那段接回去循环，直到 64 秒的高潮落在签名上或之后，再接尾段", () => {
    const plan = musicPlan(herBirthday, 100, 101.6);
    // 循环一次：高潮挪到第 64 + 57 = 121 秒，从第 21 秒开始放。
    expect(plan.loops).toBe(1);
    expect(plan.offset).toBe(21);
    expect(plan.segments).toEqual([
      { at: 0, from: 21, to: 60 },
      { at: 39, from: 3, to: 60 },
      { at: 96, from: 60, to: null },
    ]);
    // 尾段从 60 秒放起，第 64 秒的高潮落在签名上。
    expect(plan.segments[2].at + 64 - 60).toBe(100);
  });

  it("签名越晚循环越多次；正好落在签名上时不多循环", () => {
    expect(musicPlan(herBirthday, 200, 201.6).loops).toBe(3);
    expect(musicPlan(herBirthday, 121, 122.6).loops).toBe(1);
    expect(musicPlan(herBirthday, 64, 65.6).loops).toBe(0);
    expect(musicPlan(herBirthday, 200, 201.6).segments.at(-1)).toEqual({ at: 200 - 4, from: 60, to: null });
  });

  it("配乐来晚了：从第 t 秒接着放，已经放过的段不再放", () => {
    const { segments } = musicPlan(herBirthday, 100, 101.6);
    expect(segmentsFrom(segments, 50)).toEqual([
      { at: 50, from: 14, to: 60 },
      { at: 96, from: 60, to: null },
    ]);
    expect(segmentsFrom(segments, 0)).toEqual(segments);
    expect(segmentsFrom([{ at: 0, from: 31, to: null }], 10)).toEqual([{ at: 10, from: 41, to: null }]);
  });
});

describe("页首的信封键", () => {
  it("开着信，或者已经有信时出现", () => {
    expect(showsLetterButton(true, [])).toBe(true);
    expect(showsLetterButton(false, [summary(true)])).toBe(true);
    expect(showsLetterButton(false, [])).toBe(false);
    expect(showsLetterButton(false, null)).toBe(false);
  });

  it("有没读过的信时带点", () => {
    expect(hasUnread([summary(true), summary(false)])).toBe(true);
    expect(hasUnread([summary(true)])).toBe(false);
    expect(hasUnread(null)).toBe(false);
  });
});

describe("信封上的日期", () => {
  it("今年的只写月日，别的年份带上年", () => {
    expect(letterDay("2026-10-31", 2026)).toBe("10月31日");
    expect(letterDay("2025-02-03", 2026)).toBe("2025年2月3日");
  });
});

/** 一封信：`id` 越大写得越晚；列表接口给的是从新到旧。 */
function one(id: number, day: string, { from = "mano", read = false, popped = false } = {}): LetterSummary {
  return { id, character_id: from, occasions: ["close"], day, read, popped };
}

describe("弹出", () => {
  const anywhere = { onConversationPage: false, inCall: false };
  // 从新到旧：4 读过了，3 没读过、弹过了（跳过了），2 和 1 没读过也没弹过。
  const letters = [
    one(4, "2026-10-31", { read: true, popped: true }),
    one(3, "2026-10-30", { popped: true }),
    one(2, "2026-10-29", { from: "kogane" }),
    one(1, "2026-10-28"),
  ];

  it("弹最早的那封没读过、也没弹过的", () => {
    expect(letterToPop(letters, anywhere)?.id).toBe(1);
    expect(letterToPop(letters.slice(0, 3), anywhere)?.id).toBe(2);
  });

  it("读过的、弹过的（跳过的）不再弹；没有信时不弹", () => {
    expect(letterToPop(letters.slice(0, 2), anywhere)).toBeNull();
    expect(letterToPop([], anywhere)).toBeNull();
    expect(letterToPop(null, anywhere)).toBeNull();
  });

  it("在对话页上、通话中都不弹", () => {
    expect(letterToPop(letters, { onConversationPage: true, inCall: false })).toBeNull();
    expect(letterToPop(letters, { onConversationPage: false, inCall: true })).toBeNull();
  });
});

describe("所有的信", () => {
  it("没读过的在最上面，其余按月分组，都从新到旧", () => {
    const grouped = groupLetters([
      one(6, "2026-11-01", { read: true }),
      one(5, "2026-10-31"),
      one(4, "2026-10-20", { read: true }),
      one(3, "2026-10-02", { read: true }),
      one(2, "2026-09-30"),
      one(1, "2025-12-24", { read: true }),
    ]);

    expect(grouped.unread.map((l) => l.id)).toEqual([5, 2]);
    expect(grouped.months.map((m) => [m.month, m.letters.map((l) => l.id)])).toEqual([
      ["2026-11", [6]],
      ["2026-10", [4, 3]],
      ["2025-12", [1]],
    ]);
  });

  it("没有信时什么组都没有", () => {
    expect(groupLetters([])).toEqual({ unread: [], months: [] });
  });

  it("月份：今年的只写月，别的年份带上年", () => {
    expect(letterMonth("2026-10", 2026)).toBe("10月");
    expect(letterMonth("2025-02", 2026)).toBe("2025年2月");
  });
});

describe("她的信", () => {
  const letters = [one(3, "2026-10-31", { from: "kogane" }), one(2, "2026-10-30"), one(1, "2026-10-29", { read: true })];

  it("只列她写的，从新到旧", () => {
    expect(hersOf(letters, "mano").map((l) => l.id)).toEqual([2, 1]);
    expect(hersOf(letters, "meguru")).toEqual([]);
    expect(hersOf(null, "mano")).toEqual([]);
  });

  it("谁有没读过的信：对话列表上她那一行名字后面一枚小信封", () => {
    expect(unreadFrom(letters)).toEqual(new Set(["kogane", "mano"]));
    expect(unreadFrom(null)).toEqual(new Set());
  });
});

describe("列表跟着轮询", () => {
  const latest = (unread: Record<string, boolean>) =>
    Object.fromEntries(Object.entries(unread).map(([id, unread_letter]) => [id, { unread_letter }]));

  it("最新对话列表说她有没读过的信、手上的信里却没有，或者反过来，信要重新拉", () => {
    const letters = [one(1, "2026-10-29")];
    expect(lettersBehind(letters, latest({ mano: true, kogane: false }))).toBe(false);
    expect(lettersBehind(letters, latest({ mano: true, kogane: true }))).toBe(true);
    expect(lettersBehind(letters, latest({ mano: false }))).toBe(true);
  });

  it("还没拉到信时不算落后（载入时本来就要拉）", () => {
    expect(lettersBehind(null, latest({ mano: true }))).toBe(false);
  });
});
