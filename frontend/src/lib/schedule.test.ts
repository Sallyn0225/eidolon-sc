import { afterEach, describe, expect, it, vi } from "vitest";

import {
  afterSave,
  awaitsPast,
  calendarWeeks,
  calendarWho,
  cellText,
  confirmRows,
  dayJobs,
  draftsOf,
  expiry,
  freeSlots,
  hasSavedShown,
  herScheduleHref,
  isOutdated,
  isShown,
  jobNote,
  keepDrafts,
  occupantOf,
  localNow,
  mondayOf,
  pastWeeksIn,
  pendingJobs,
  publishedAt,
  readDrafts,
  returnedNote,
  shortName,
  startedNote,
  startsFor,
  type Job,
  type OpenSchedule,
  type Week,
  timeOf,
  toSave,
  weekGrid,
  weekPage,
  weeksAt,
  whenText,
  whyNot,
} from "@/lib/schedule";

/** 2026-10-19 是周一。 */
const WEEK = "2026-10-19";
const NEXT = "2026-10-26";

/** 一项工作：默认一段、哪段都行。 */
function job(id: string, fields: Partial<Job> = {}): Job {
  return { id, character_id: "mano", name: id, note: "", category: "practice", length: 1, slots: null, ...fields };
}

/** 一周：已发布，默认没有工作和放置。 */
function weekOf(id: string, fields: Partial<Week> = {}): Week {
  return { id, published: true, published_at: publishedAt(id).toISOString(), jobs: [], placements: [], ...fields };
}

function scheduleOf(fields: Partial<OpenSchedule> = {}): OpenSchedule {
  return { enabled: true, timezone: "Asia/Shanghai", this_week: weekOf(WEEK), next_week: null, first_week: null, ...fields };
}

describe("此刻在制作人那边是哪一周、周几、几点", () => {
  it("按给的时区算，周一是 0", () => {
    // 北京 10月21日（周三）14:30。
    expect(localNow("Asia/Shanghai", new Date("2026-10-21T06:30:00Z"))).toEqual({
      date: "2026-10-21",
      week: WEEK,
      day: 2,
      hour: 14,
    });
    // 同一刻洛杉矶还是 10月20日（周二）23:30。
    expect(localNow("America/Los_Angeles", new Date("2026-10-21T06:30:00Z"))).toEqual({
      date: "2026-10-20",
      week: WEEK,
      day: 1,
      hour: 23,
    });
  });

  it("周日算进这一周的最后一天", () => {
    expect(localNow("Asia/Tokyo", new Date("2026-10-25T03:00:00Z"))).toMatchObject({ week: WEEK, day: 6, hour: 12 });
  });
});

describe("一个时间段是已过、进行中还是还没到", () => {
  // 周三下午 14 点。
  const now = { date: "2026-10-21", week: WEEK, day: 2, hour: 14 };

  it("下周全是还没到", () => {
    expect(timeOf(now, NEXT, 0, 0)).toBe("future");
  });

  it("早于今天的日子是已过，晚于今天的是还没到", () => {
    expect(timeOf(now, WEEK, 1, 2)).toBe("past");
    expect(timeOf(now, WEEK, 3, 0)).toBe("future");
  });

  it("今天早于当前段的已过，当前段进行中，之后的还没到", () => {
    expect(timeOf(now, WEEK, 2, 0)).toBe("past");
    expect(timeOf(now, WEEK, 2, 1)).toBe("now");
    expect(timeOf(now, WEEK, 2, 2)).toBe("future");
  });

  it("段的边界：12 点整是下午，18 点整是晚上", () => {
    expect(timeOf({ ...now, hour: 12 }, WEEK, 2, 1)).toBe("now");
    expect(timeOf({ ...now, hour: 18 }, WEEK, 2, 1)).toBe("past");
    expect(timeOf({ ...now, hour: 18 }, WEEK, 2, 2)).toBe("now");
  });

  it("今天 0–6 点时三段都还没到", () => {
    const early = { ...now, hour: 5 };
    expect(timeOf(early, WEEK, 2, 0)).toBe("future");
    expect(timeOf(early, WEEK, 2, 2)).toBe("future");
    expect(timeOf({ ...now, hour: 6 }, WEEK, 2, 0)).toBe("now");
  });
});

describe("制作人那边的本周、下周和发布", () => {
  it("工作在北京时间周一 0 点发布", () => {
    expect(publishedAt(WEEK).toISOString()).toBe("2026-10-18T16:00:00.000Z");
  });

  it("平常只有本周，下周还没发布", () => {
    // 北京周三下午。
    expect(weeksAt("Asia/Shanghai", new Date("2026-10-21T06:30:00Z"))).toEqual({
      thisWeek: WEEK,
      isPublished: true,
      nextWeek: null,
    });
  });

  it("北京以西周日就有下周", () => {
    // 洛杉矶周日 10 点，北京已是周一 1 点。
    expect(weeksAt("America/Los_Angeles", new Date("2026-10-25T17:00:00Z"))).toEqual({
      thisWeek: WEEK,
      isPublished: true,
      nextWeek: NEXT,
    });
  });

  it("北京以东周一凌晨本周还没发布", () => {
    // 奥克兰周一 0:30，北京还是周日 19:30。
    expect(weeksAt("Pacific/Auckland", new Date("2026-10-25T11:30:00Z"))).toEqual({
      thisWeek: NEXT,
      isPublished: false,
      nextWeek: null,
    });
  });

  it("换了周、或者该发布的发布了，读到的日程就过时了", () => {
    const read = scheduleOf({ this_week: weekOf(WEEK), next_week: null });
    expect(isOutdated(read, new Date("2026-10-21T06:30:00Z"))).toBe(false);
    // 上海已经到了下一周。
    expect(isOutdated(read, new Date("2026-10-26T01:00:00Z"))).toBe(true);
    // 洛杉矶那边下周发布了。
    const west = { ...read, timezone: "America/Los_Angeles" };
    expect(isOutdated(west, new Date("2026-10-25T15:59:00Z"))).toBe(false);
    expect(isOutdated(west, new Date("2026-10-25T16:00:00Z"))).toBe(true);
    // 奥克兰那边本周的工作发布了。
    const east = scheduleOf({ timezone: "Pacific/Auckland", this_week: { ...weekOf(NEXT), published: false } });
    expect(isOutdated(east, new Date("2026-10-25T15:59:00Z"))).toBe(false);
    expect(isOutdated(east, new Date("2026-10-25T16:00:00Z"))).toBe(true);
  });
});

describe("一项工作能不能从某一格开始排", () => {
  // 周三（2）下午 14 点。
  const now = { date: "2026-10-21", week: WEEK, day: 2, hour: 14 };
  const one = job("one");
  const two = job("two", { length: 2 });
  const whole = job("whole", { length: 3 });
  const evening = job("evening", { slots: ["evening"] });
  const late = job("late", { slots: ["afternoon", "evening"] });
  const other = job("other", { character_id: "hiori" });
  const board = {
    week: weekOf(WEEK, { jobs: [one, two, whole, evening, late, other], placements: [{ job_id: "other", day: 4, slot: 1 }] }),
    drafts: [{ job_id: "two", day: 5, slot: 0 }],
    now,
  };

  it("能放时没有原因", () => {
    expect(whyNot(board, one, 3, 0)).toBeNull();
    expect(whyNot(board, whole, 3, 0)).toBeNull();
    expect(whyNot(board, late, 3, 1)).toBeNull();
    expect(whyNot({ ...board, week: { ...board.week, id: NEXT } }, one, 0, 0)).toBeNull();
  });

  it("一整天的只能从上午排，多段的当天要放得下", () => {
    expect(whyNot(board, whole, 3, 1)).toBe("一整天的工作只能从上午排");
    expect(whyNot(board, two, 3, 2)).toBe("当天排不下");
  });

  it("占到已过或进行中的格子都不行", () => {
    expect(whyNot(board, one, 1, 2)).toBe("已经过了");
    expect(whyNot(board, one, 2, 1)).toBe("正在进行");
    expect(whyNot(board, two, 2, 0)).toBe("已经过了");
  });

  it("有时段限制的只能排在那几段", () => {
    expect(whyNot(board, evening, 3, 1)).toBe("只能排在晚上");
    expect(whyNot(board, late, 3, 0)).toBe("只能排在下午和晚上");
    // 先看过没过，再看时段。
    expect(whyNot(board, evening, 1, 0)).toBe("已经过了");
  });

  it("格子里有别的工作，保存过的和草稿都算，不管是谁的", () => {
    expect(whyNot(board, one, 4, 1)).toBe("格子里有别的工作");
    expect(whyNot(board, two, 4, 0)).toBe("格子里有别的工作");
    expect(whyNot(board, one, 5, 1)).toBe("格子里有别的工作");
  });

  it("自己占着的格子不挡自己", () => {
    expect(whyNot(board, two, 5, 0)).toBeNull();
  });

  it("占着某一格的是哪一项，保存过的还是草稿", () => {
    expect(occupantOf(board, 4, 1)).toEqual({ placement: { job_id: "other", day: 4, slot: 1 }, job: other, isSaved: true });
    expect(occupantOf(board, 5, 1)).toMatchObject({ job: two, isSaved: false });
    expect(occupantOf(board, 5, 2)).toBeNull();
  });
});

describe("能从哪些格子开始、还能排几格、还有哪些待排", () => {
  // 周六（5）晚上 19 点：只剩周日三格。
  const now = { date: "2026-10-24", week: WEEK, day: 5, hour: 19 };
  const one = job("one");
  const two = job("two", { length: 2 });
  const whole = job("whole", { length: 3 });
  const evening = job("evening", { slots: ["evening"] });
  const saved = job("saved");
  const board = {
    week: weekOf(WEEK, { jobs: [one, two, whole, evening, saved], placements: [{ job_id: "saved", day: 6, slot: 0 }] }),
    drafts: [{ job_id: "evening", day: 6, slot: 2 }],
    now,
  };

  it("一项能开始的格子按周几、哪一段排", () => {
    expect(startsFor(board, one)).toEqual([{ day: 6, slot: 1 }]);
    expect(startsFor(board, two)).toEqual([]);
    expect(startsFor({ ...board, drafts: [] }, two)).toEqual([{ day: 6, slot: 1 }]);
    expect(startsFor({ ...board, week: { ...board.week, id: NEXT, placements: [] }, drafts: [] }, whole)).toEqual(
      Array.from({ length: 7 }, (_, day) => ({ day, slot: 0 })),
    );
  });

  it("还能排几格数这一周还没到、也没被占的格子", () => {
    expect(freeSlots(board)).toBe(1);
    expect(freeSlots({ ...board, drafts: [] })).toBe(2);
    expect(freeSlots({ ...board, week: { ...board.week, id: NEXT, placements: [] }, drafts: [] })).toBe(21);
  });

  it("待排是这周的工作去掉草稿和保存过的，按接口的顺序", () => {
    expect(pendingJobs(board)).toEqual([one, two, whole]);
    expect(pendingJobs({ ...board, drafts: [] })).toEqual([one, two, whole, evening]);
  });
});

describe("保存：剔掉已开始的、确认框列哪几项、没存下的怎么说", () => {
  // 周三（2）下午 14 点。
  const now = { date: "2026-10-21", week: WEEK, day: 2, hour: 14 };
  const shoot = job("shoot", { name: "拍摄广告", length: 2 });
  const lesson = job("lesson", { name: "声乐课", character_id: "hiori" });
  const meeting = job("meeting", { name: "开会", length: 3 });
  const dinner = job("dinner", { name: "吃饭", character_id: "hiori" });
  const board = {
    week: weekOf(WEEK, { jobs: [shoot, lesson, meeting, dinner] }),
    drafts: [
      { job_id: "meeting", day: 4, slot: 0 },
      { job_id: "shoot", day: 2, slot: 1 },
      { job_id: "lesson", day: 3, slot: 2 },
    ],
    now,
  };
  const names: Record<string, string> = { mano: "櫻木真乃", hiori: "風野灯織" };
  const nameOf = (id: string) => names[id];

  it("任一格已经不是还没到的草稿算已开始，不存；其余照草稿的顺序存", () => {
    expect(toSave(board)).toEqual({
      saving: [
        { job_id: "meeting", day: 4, slot: 0 },
        { job_id: "lesson", day: 3, slot: 2 },
      ],
      started: [{ job_id: "shoot", day: 2, slot: 1 }],
    });
  });

  it("确认框按周几、哪一段一行一项，写哪天哪几段", () => {
    expect(confirmRows(board, toSave(board).saving)).toEqual([
      { placement: { job_id: "lesson", day: 3, slot: 2 }, job: lesson, when: "周四 晚上" },
      { placement: { job_id: "meeting", day: 4, slot: 0 }, job: meeting, when: "周五 一整天" },
    ]);
    expect(whenText({ job_id: "shoot", day: 0, slot: 1 }, shoot)).toBe("周一 下午到晚上");
    expect(cellText({ day: 2, slot: 2 })).toBe("周三 晚上");
  });

  it("已开始的那句列出谁的哪项", () => {
    expect(startedNote(board, toSave(board).started, nameOf)).toBe("櫻木真乃的拍摄广告：已经开始了，不保存，退回待排。");
    expect(
      startedNote(
        board,
        [
          { job_id: "shoot", day: 2, slot: 1 },
          { job_id: "dinner", day: 2, slot: 0 },
        ],
        nameOf,
      ),
    ).toBe("櫻木真乃的拍摄广告、風野灯織的吃饭：已经开始了，不保存，退回待排。");
    expect(startedNote(board, [], nameOf)).toBeNull();
  });

  it("服务器退回的：过了、进行中说成已经开始了，别的照原因说", () => {
    expect(
      returnedNote(
        board,
        [
          { job_id: "shoot", day: 2, slot: 1, reason: "正在进行" },
          { job_id: "dinner", day: 2, slot: 0, reason: "已经过了" },
          { job_id: "lesson", day: 3, slot: 2, reason: "格子里有别的工作" },
        ],
        nameOf,
      ),
    ).toBe(
      "櫻木真乃的拍摄广告、風野灯織的吃饭：已经开始了，不保存，退回待排。風野灯織的声乐课：格子里有别的工作，不保存，退回待排。",
    );
    expect(returnedNote(board, [], nameOf)).toBeNull();
  });
});

describe("没排的工作什么时候作废", () => {
  const board = { week: weekOf(WEEK), drafts: [], now: { date: "2026-10-24", week: WEEK, day: 5, hour: 23 } };

  it("周日以前写周日 24 点", () => {
    expect(expiry(board)).toEqual({ text: "周日 24 点后作废", isTonight: false });
  });

  it("制作人那边已经是周日时写今晚", () => {
    expect(expiry({ ...board, now: { date: "2026-10-25", week: WEEK, day: 6, hour: 1 } })).toEqual({
      text: "今晚 24 点后作废",
      isTonight: true,
    });
  });

  it("下周的照样写周日 24 点", () => {
    const sunday = { date: "2026-10-25", week: WEEK, day: 6, hour: 20 };
    expect(expiry({ ...board, week: weekOf(NEXT), now: sunday }).isTonight).toBe(false);
  });
});

describe("周视图一行一天怎么画", () => {
  // 周三（2）下午 14 点。
  const now = { date: "2026-10-21", week: WEEK, day: 2, hour: 14 };
  const done = job("done", { length: 2 });
  const underWay = job("under-way");
  const later = job("later", { length: 3, character_id: "hiori" });
  const started = job("started", { character_id: "hiori" });
  const draft = job("draft");
  const board = {
    week: weekOf(WEEK, {
      jobs: [done, underWay, later, started, draft],
      placements: [
        { job_id: "done", day: 1, slot: 0 },
        { job_id: "under-way", day: 2, slot: 1 },
        { job_id: "later", day: 3, slot: 0 },
      ],
    }),
    drafts: [
      { job_id: "started", day: 0, slot: 2 },
      { job_id: "draft", day: 4, slot: 2 },
    ],
    now,
  };

  it("多段的块占几格，后面的格子不再单列；块分做完、进行中、保存过、已开始的草稿、草稿", () => {
    const rows = weekGrid(board, null);
    expect(rows).toHaveLength(7);
    expect(rows[0]).toEqual([
      { kind: "empty", cell: { day: 0, slot: 0 }, when: "past" },
      { kind: "empty", cell: { day: 0, slot: 1 }, when: "past" },
      { kind: "block", occupant: occupantOf(board, 0, 2), state: "started" },
    ]);
    expect(rows[1].map((c) => (c.kind === "block" ? c.state : c.kind))).toEqual(["done", "empty"]);
    expect(rows[2]).toEqual([
      { kind: "empty", cell: { day: 2, slot: 0 }, when: "past" },
      { kind: "block", occupant: occupantOf(board, 2, 1), state: "now" },
      { kind: "empty", cell: { day: 2, slot: 2 }, when: "future" },
    ]);
    expect(rows[3].map((c) => (c.kind === "block" ? c.state : c.kind))).toEqual(["saved"]);
    expect(rows[4].map((c) => (c.kind === "block" ? c.state : c.kind))).toEqual(["empty", "empty", "draft"]);
  });

  it("只看她时别人的块换成占着的空位，待排也只剩她的", () => {
    const rows = weekGrid(board, "hiori");
    expect(rows[2]).toEqual([
      { kind: "empty", cell: { day: 2, slot: 0 }, when: "past" },
      { kind: "hidden", cell: { day: 2, slot: 1 } },
      { kind: "empty", cell: { day: 2, slot: 2 }, when: "future" },
    ]);
    expect(rows[1].map((c) => c.kind)).toEqual(["hidden", "hidden", "empty"]);
    expect(rows[3].map((c) => (c.kind === "block" ? c.state : c.kind))).toEqual(["saved"]);
    const pending = job("pending");
    const mine = job("mine", { character_id: "hiori" });
    expect([pending, mine, later].filter((j) => isShown(j, "hiori"))).toEqual([mine, later]);
    expect([pending, mine].filter((j) => isShown(j, null))).toEqual([pending, mine]);
  });
});

/** 这台浏览器的 localStorage，放在内存里。 */
function storage(initial: Record<string, string> = {}) {
  const items = new Map(Object.entries(initial));
  vi.stubGlobal("localStorage", {
    get length() {
      return items.size;
    },
    key: (i: number) => [...items.keys()][i] ?? null,
    getItem: (key: string) => items.get(key) ?? null,
    setItem: (key: string, value: string) => void items.set(key, value),
    removeItem: (key: string) => void items.delete(key),
  });
  return items;
}

describe("草稿存在这台设备上", () => {
  afterEach(() => vi.unstubAllGlobals());
  const a = { job_id: `${WEEK}-a`, day: 3, slot: 0 };
  const b = { job_id: `${NEXT}-b`, day: 0, slot: 1 };

  it("按用户、按周号一个键，读回来是存的那几项", () => {
    const items = storage();

    keepDrafts("user-1", WEEK, [a]);
    keepDrafts("user-1", NEXT, [b]);
    keepDrafts("user-2", WEEK, []);

    expect(readDrafts("user-1", [WEEK, NEXT])).toEqual(new Map([[WEEK, [a]], [NEXT, [b]]]));
    expect(readDrafts("user-2", [WEEK])).toEqual(new Map([[WEEK, []]]));
    expect(items.get(`eidolon.scheduleDrafts.user-1.${WEEK}`)).toBe(JSON.stringify([a]));
    expect(items.has(`eidolon.scheduleDrafts.user-2.${WEEK}`)).toBe(false);
  });

  it("读到的周号变了，这位用户别的周的草稿就丢掉", () => {
    const items = storage({
      [`eidolon.scheduleDrafts.user-1.2026-10-12`]: JSON.stringify([a]),
      [`eidolon.scheduleDrafts.user-1.${WEEK}`]: JSON.stringify([a]),
      [`eidolon.scheduleDrafts.user-2.2026-10-12`]: JSON.stringify([a]),
    });

    expect(readDrafts("user-1", [WEEK])).toEqual(new Map([[WEEK, [a]]]));
    expect([...items.keys()]).toEqual([
      `eidolon.scheduleDrafts.user-1.${WEEK}`,
      `eidolon.scheduleDrafts.user-2.2026-10-12`,
    ]);
  });

  it("存的不是一组放置时当作没有", () => {
    storage({
      [`eidolon.scheduleDrafts.user-1.${WEEK}`]: "{not json",
      [`eidolon.scheduleDrafts.user-1.${NEXT}`]: JSON.stringify([{ job_id: 3 }]),
    });

    expect(readDrafts("user-1", [WEEK, NEXT])).toEqual(new Map([[WEEK, []], [NEXT, []]]));
  });

  it("存不进去时只在这次页面里记着", () => {
    const unreachable = () => {
      throw new DOMException("denied", "SecurityError");
    };
    vi.stubGlobal("localStorage", {
      length: 0,
      key: unreachable,
      getItem: unreachable,
      setItem: unreachable,
      removeItem: unreachable,
    });

    expect(readDrafts("private-1", [WEEK])).toEqual(new Map([[WEEK, []]]));
    expect(() => keepDrafts("private-1", WEEK, [a])).not.toThrow();
    expect(readDrafts("private-1", [WEEK])).toEqual(new Map([[WEEK, [a]]]));
  });
});

describe("读回来的草稿和保存以后", () => {
  // 周三（2）下午 14 点。
  const now = { date: "2026-10-21", week: WEEK, day: 2, hour: 14 };
  const one = job("one");
  const two = job("two", { length: 2 });
  const saved = job("saved");
  const week = weekOf(WEEK, { jobs: [one, two, saved], placements: [{ job_id: "saved", day: 3, slot: 1 }] });

  it("不在这一周的、已经保存过的、放不进这一天的、和保存过的或前面的草稿撞上的都去掉，已开始的留着", () => {
    expect(
      draftsOf(week, [
        { job_id: "gone", day: 0, slot: 0 },
        { job_id: "saved", day: 5, slot: 0 },
        { job_id: "two", day: 3, slot: 0 },
        { job_id: "two", day: 4, slot: 2 },
        { job_id: "one", day: 9, slot: 0 },
        { job_id: "one", day: 1, slot: 0 },
        { job_id: "two", day: 1, slot: 0 },
      ]),
    ).toEqual([{ job_id: "one", day: 1, slot: 0 }]);
  });

  it("保存以后去掉这次试过的，存下的成了保存过的，退回的回到待排", () => {
    const drafts = [
      { job_id: "one", day: 4, slot: 0 },
      { job_id: "two", day: 5, slot: 0 },
    ];
    const left = afterSave(drafts, drafts);
    expect(left).toEqual([]);
    // 重读回来：one 存下了，two 被退回。
    const reread = { ...week, placements: [...week.placements, { job_id: "one", day: 4, slot: 0 }] };
    expect(pendingJobs({ week: reread, drafts: left, now })).toEqual([two]);
  });
});

describe("待排一行的说明", () => {
  it("写占几段，有时段限制的再写只能哪几段", () => {
    expect(jobNote(job("a", { length: 2, slots: ["evening", "afternoon"] }))).toBe("2 段 · 只能下午、晚上");
    expect(jobNote(job("b", { length: 3 }))).toBe("3 段");
  });
});

describe("月视图上的日程", () => {
  const shoot = job("shoot", { name: "拍摄广告", length: 2, character_id: "madoka" });
  const lesson = job("lesson", { name: "舞蹈课" });
  const dinner = job("dinner", { name: "吃饭", length: 3, character_id: "madoka" });
  const thisWeek = {
    week: weekOf(WEEK, { jobs: [shoot, lesson], placements: [{ job_id: "lesson", day: 2, slot: 2 }] }),
    drafts: [{ job_id: "shoot", day: 2, slot: 0 }],
  };
  const nextWeek = { week: weekOf(NEXT, { jobs: [dinner] }), drafts: [{ job_id: "dinner", day: 6, slot: 0 }] };
  const characterOf = (id: string) => ({ id });
  /** 一项写成「日期 谁 工作名 几段 保存过的还是草稿」。 */
  const text = (who: string | null) =>
    dayJobs([thisWeek, nextWeek], characterOf, who).map(
      (j) => `${j.date} ${j.character.id} ${j.name} ${j.slotsText} ${j.isSaved ? "已保存" : "草稿"}`,
    );

  it("本周和下周保存过的和草稿都有，按日期和时间段排，写占哪几段", () => {
    expect(text(null)).toEqual([
      "2026-10-21 madoka 拍摄广告 上午到下午 草稿",
      "2026-10-21 mano 舞蹈课 晚上 已保存",
      "2026-11-01 madoka 吃饭 一整天 草稿",
    ]);
  });

  it("只看她时只有她的", () => {
    expect(text("madoka")).toEqual(["2026-10-21 madoka 拍摄广告 上午到下午 草稿", "2026-11-01 madoka 吃饭 一整天 草稿"]);
    expect(text("nobody")).toEqual([]);
  });
});

describe("「只看她」的地址", () => {
  it("对话页的「她的日程」去日历子页，带着她", () => {
    expect(herScheduleHref("mano")).toBe("/play/calendar?who=mano");
  });

  it("地址里没有或是空的时是全部", () => {
    expect(calendarWho({ who: "mano" })).toBe("mano");
    for (const who of [undefined, ""]) expect(calendarWho({ who }), String(who)).toBeNull();
  });
});

describe("日程里她的名字", () => {
  it("写短名，没有短名时写全名", () => {
    expect(shortName({ name: "黛冬優子", short_name: "冬優子" })).toBe("冬優子");
    expect(shortName({ name: "七草はづき", short_name: null })).toBe("七草はづき");
  });
});

describe("往周", () => {
  const LAST = "2026-10-12";
  const EARLIER = "2026-10-05";
  const none = new Map<string, Week>();

  it("一天所在的那一周从周一算", () => {
    expect(mondayOf("2026-10-25")).toBe(WEEK);
  });

  it("本周：最早保存过的那一周早于本周时能往前翻，下周发布了才能往后翻，没有「回到本周」", () => {
    const page = weekPage(null, scheduleOf({ first_week: EARLIER }), none);
    expect(page).toEqual({
      id: WEEK,
      week: weekOf(WEEK),
      isPast: false,
      title: "本周",
      hasPrevious: true,
      hasNext: false,
      previous: LAST,
      next: NEXT,
      hasBackToThisWeek: false,
    });
    // 没保存过，或者只在本周保存过：本周就是头。
    expect(weekPage(null, scheduleOf(), none).hasPrevious).toBe(false);
    expect(weekPage(null, scheduleOf({ first_week: WEEK }), none).hasPrevious).toBe(false);
    expect(weekPage(null, scheduleOf({ next_week: weekOf(NEXT) }), none).hasNext).toBe(true);
  });

  it("下周：往前翻回本周（选的是 null）", () => {
    const page = weekPage(NEXT, scheduleOf({ next_week: weekOf(NEXT) }), none);
    expect([page.id, page.title, page.hasPrevious, page.previous, page.hasNext]).toEqual([NEXT, "下周", true, null, false]);
  });

  it("往周：只看、能往后翻、有「回到本周」，上周以前没有名字，最早的那一周不能再往前；还没取到时没有这一周", () => {
    const read = scheduleOf({ first_week: EARLIER });
    const last = weekPage(LAST, read, new Map([[LAST, weekOf(LAST)]]));
    expect(last).toMatchObject({ id: LAST, week: weekOf(LAST), isPast: true, title: "上周", hasPrevious: true });
    expect(last).toMatchObject({ hasNext: true, next: null, hasBackToThisWeek: true });
    const earliest = weekPage(EARLIER, read, none);
    expect(earliest).toMatchObject({ id: EARLIER, week: null, title: null, hasPrevious: false, next: LAST });
  });

  it("选的那一周看不到了（早过最早的那一周、下周没发布）就回本周", () => {
    const read = scheduleOf({ first_week: EARLIER });
    expect(weekPage("2026-09-28", read, none).id).toBe(WEEK);
    expect(weekPage(NEXT, read, none).id).toBe(WEEK);
  });

  it("月视图碰到的往周：最早保存过的那一周起、本周以前；没保存过时没有", () => {
    const read = scheduleOf({ first_week: EARLIER });
    // 九月、十月两屏。
    expect(pastWeeksIn("2026-08-31", "2026-10-04", read)).toEqual([]);
    expect(pastWeeksIn("2026-09-28", "2026-11-01", read)).toEqual([EARLIER, LAST]);
    expect(pastWeeksIn("2026-09-28", "2026-11-01", scheduleOf())).toEqual([]);
  });

  it("月视图画取过的往周、本周和下周；还没取到的往周里那几天先读着", () => {
    const read = scheduleOf({ first_week: EARLIER, next_week: weekOf(NEXT) });
    const past = new Map([
      [LAST, weekOf(LAST)],
      // 读的时候还是往周，现在已经是本周了。
      [WEEK, weekOf(WEEK, { jobs: [job("old")] })],
    ]);
    expect(calendarWeeks(read, past).map((week) => week.id)).toEqual([LAST, WEEK, NEXT]);
    expect(calendarWeeks(read, past)[1]).toBe(read.this_week);
    expect(awaitsPast("2026-10-07", read, past)).toBe(true);
    expect(awaitsPast("2026-10-13", read, past)).toBe(false);
    expect(awaitsPast("2026-10-20", read, past)).toBe(false);
  });

  it("往周里有没有要画的，「只看她」时只算她的", () => {
    const week = weekOf(LAST, {
      jobs: [job("lesson"), job("shoot", { character_id: "kogane" })],
      placements: [{ job_id: "shoot", day: 2, slot: 0 }],
    });
    expect(hasSavedShown(week, null)).toBe(true);
    expect(hasSavedShown(week, "mano")).toBe(false);
  });
});
