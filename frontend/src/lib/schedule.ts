// 日程（GLOSSARY.md「工作」「日程」「时间段」，.scratch/schedule spec「日程的规则」「界面」）：排日程的规则全在这里，
// 页面只管画。一周 7 天（0 是周一）× 3 段（0 是上午 6–12，1 是下午 12–18，2 是晚上 18–24），按制作人的有效时区
// （读日程接口给的 `timezone`，档案优先于设备）；0–6 点不属于任何一段。一格只放一项，不管是谁的；已过和进行中的格子
// 不能排。哪格能放、为什么不能（`whyNot`）和后端 `schedule.why_not` 是同一套，原因的话也一样。
//
// 周号是那个周一的日期（`YYYY-MM-DD`）；每周的工作在北京时间那个周一 0 点发布。制作人的「本周」是他那边的周一到周日，
// 拿同一个周号的工作：北京以西周日就能排下周，北京以东周一凌晨本周还没发布。

import { copy } from "@/i18n";
import { api, json } from "@/lib/api";
import { addDays, type DayJob, partsOf } from "@/lib/calendar";
import { playHref } from "@/lib/playRoute";

const t = copy.play.schedule;

/** 四类工作：练习、出镜、事务、私人。 */
export type JobCategory = "practice" | "appearance" | "business" | "private";

/** 三个时间段，按下标是 0、1、2。 */
export const SLOTS = ["morning", "afternoon", "evening"] as const;

export type SlotName = (typeof SLOTS)[number];

/** 一周的一项工作（实例 id 是「周号-清单 id」）：谁的、名字、一句说明、类别、占几段（1–3）、只能排在哪几段（null 是哪段都行）。 */
export type Job = {
  id: string;
  character_id: string;
  name: string;
  note: string;
  category: JobCategory;
  length: number;
  slots: SlotName[] | null;
};

/** 排进日程的一项：周几（0 是周一）、从哪一段开始（0 是上午）。 */
export type Placement = { job_id: string; day: number; slot: number };

/** 读日程接口给的一周：周号、发布了没有、发布时刻（ISO），这周的工作和这位用户保存过的放置（没发布时都是空的）。 */
export type Week = { id: string; published: boolean; published_at: string; jobs: Job[]; placements: Placement[] };

/** 日程开着时读到的：有效时区（`timeOf` 按它算），本周和已发布的下周。 */
export type OpenSchedule = {
  enabled: true;
  timezone: string;
  this_week: Week;
  next_week: Week | null;
  /** 最早保存过日程的那一周；没保存过是 null。 */
  first_week: string | null;
};

/** 读日程接口给的；部署关着日程时只有 `enabled: false`。 */
export type Schedule = { enabled: false } | OpenSchedule;

/** 保存时服务器退回的一项，带着原因。 */
export type Returned = Placement & { reason: string };

/** 保存接口给的：存下的和退回的。 */
export type Saved = { saved: Placement[]; returned: Returned[] };

/** 读日程；后端读的时候顺带抽出这周的工作、补算做完的工作的好感度。带着设备时区（`api`）。 */
export async function getSchedule(): Promise<Schedule> {
  return json(await api("/api/schedule"));
}

/** 读往周：`from` 所在的那一周到 `to` 所在的那一周里本周以前的（最多 6 周，月视图一屏那么多），早的在前；每周只有保存过的
 * 放置和它们的工作。只读，不抽工作、不算好感度。日程关着时抛 `scheduleClosed` 的 ApiError。 */
export async function getPastWeeks(from: string, to: string): Promise<Week[]> {
  const read: { weeks: Week[] } = await json(await api(`/api/schedule/weeks?${new URLSearchParams({ from, to })}`));
  return read.weeks;
}

/** 保存 `week` 这次新加的几项；能放的存下，其余带原因退回。日程关着时抛 `scheduleClosed` 的 ApiError。 */
export async function saveSchedule(week: string, placements: readonly Placement[]): Promise<Saved> {
  return json(
    await api(`/api/schedule/weeks/${encodeURIComponent(week)}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ placements }),
    }),
  );
}

/** 排日程时看的一周：读到的这一周（工作和保存过的放置）、这台设备上的草稿，和此刻在制作人那边。 */
export type Board = { week: Week; drafts: readonly Placement[]; now: LocalNow };

/** 占着一格的那一项：放在哪、哪项工作、保存过的还是草稿。 */
export type Occupant = { placement: Placement; job: Job; isSaved: boolean };

/** 一周几天。 */
const DAYS = 7;

/** 北京在 UTC 东边几小时（没有夏令时）。 */
const BEIJING_HOURS = 8;

/** 此刻在制作人那边：日期、所在那一周的周号、周几（0 是周一）和几点。 */
export type LocalNow = { date: string; week: string; day: number; hour: number };

/** 一个时间段已过、进行中还是还没到。 */
export type When = "past" | "now" | "future";

/** 一段几点开始；第一段之前的几个小时不属于任何一段。 */
const SLOT_HOURS = 6;

/** 此刻（`now`）在 `timeZone` 那边是哪天、哪一周、周几、几点。 */
export function localNow(timeZone: string, now: Date): LocalNow {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat("en-CA", {
      timeZone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      hourCycle: "h23",
    })
      .formatToParts(now)
      .map((part) => [part.type, part.value]),
  );
  const date = `${parts.year}-${parts.month}-${parts.day}`;
  const day = (partsOf(date).weekday + DAYS - 1) % DAYS;
  return { date, week: addDays(date, -day), day, hour: Number(parts.hour) };
}

/** `week` 那一周周几（`day`）的第 `slot` 段，在此刻（`now`）是已过、进行中还是还没到：不是本周的整周一样；
 * 本周里早于今天的已过、晚于今天的还没到；今天 0–6 点时三段都还没到，否则看此刻落在哪一段。 */
export function timeOf(now: LocalNow, week: string, day: number, slot: number): When {
  if (week !== now.week) return week < now.week ? "past" : "future";
  if (day !== now.day) return day < now.day ? "past" : "future";
  if (now.hour < SLOT_HOURS) return "future";
  const current = Math.floor(now.hour / SLOT_HOURS) - 1;
  return slot < current ? "past" : slot === current ? "now" : "future";
}

/** 占着 `board` 上周几（`day`）第 `slot` 段的那一项；空着是 null。保存过的在草稿前面。 */
export function occupantOf(board: Pick<Board, "week" | "drafts">, day: number, slot: number): Occupant | null {
  for (const [placements, isSaved] of [
    [board.week.placements, true],
    [board.drafts, false],
  ] as const) {
    for (const placement of placements) {
      const job = jobOf(board.week, placement.job_id);
      if (job && placement.day === day && placement.slot <= slot && slot < placement.slot + job.length) {
        return { placement, job, isSaved };
      }
    }
  }
  return null;
}

/** `job` 能不能从 `board` 上周几（`day`）的第 `slot` 段开始排；不能就给一句原因（和后端一样）。先看当天放不放得下，
 * 再逐格看：已过、进行中、时段限制、格子里有别的工作（保存过的和草稿都算，自己占着的不算）。 */
export function whyNot(board: Board, job: Job, day: number, slot: number): string | null {
  if (slot + job.length > SLOTS.length) {
    return job.length === SLOTS.length ? t.reasons.wholeDayFromMorning : t.reasons.noRoomThatDay;
  }
  for (let s = slot; s < slot + job.length; s++) {
    const when = timeOf(board.now, board.week.id, day, s);
    if (when === "past") return t.reasons.past;
    if (when === "now") return t.reasons.underWay;
    if (job.slots && !job.slots.includes(SLOTS[s])) return t.reasons.onlyIn(slotList(job.slots));
    const occupant = occupantOf(board, day, s);
    if (occupant && occupant.job.id !== job.id) return t.reasons.taken;
  }
  return null;
}

/** 一周的一格：周几、哪一段。 */
export type Cell = { day: number; slot: number };

/** 一周的 21 格，按周几、哪一段排。 */
const CELLS: Cell[] = Array.from({ length: DAYS * SLOTS.length }, (_, i) => ({
  day: Math.floor(i / SLOTS.length),
  slot: i % SLOTS.length,
}));

/** `job` 能从 `board` 上哪几格开始排（`whyNot` 没有原因的），按周几、哪一段排。 */
export function startsFor(board: Board, job: Job): Cell[] {
  return CELLS.filter(({ day, slot }) => whyNot(board, job, day, slot) === null);
}

/** 「还能排 n 格」：`board` 这一周还没到、也没被占的格子有几个。 */
export function freeSlots(board: Board): number {
  return CELLS.filter(
    ({ day, slot }) => timeOf(board.now, board.week.id, day, slot) === "future" && !occupantOf(board, day, slot),
  ).length;
}

/** 待排：`board` 这一周的工作去掉草稿和保存过的，按接口给的顺序（同一位的挨在一起）。 */
export function pendingJobs(board: Board): Job[] {
  const placed = new Set([...board.week.placements, ...board.drafts].map((p) => p.job_id));
  return board.week.jobs.filter((job) => !placed.has(job.id));
}

/** 放在 `placement` 的 `job` 占的每一格。 */
function cellsOf(placement: Placement, job: Job): Cell[] {
  return Array.from({ length: job.length }, (_, k) => ({ day: placement.day, slot: placement.slot + k }));
}

/** 保存时：草稿里任一格已经不是还没到的（`started`）不存，退回待排；其余（`saving`）照草稿的顺序存。 */
export function toSave(board: Board): { saving: Placement[]; started: Placement[] } {
  const saving: Placement[] = [];
  const started: Placement[] = [];
  for (const placement of board.drafts) {
    const job = jobOf(board.week, placement.job_id);
    if (!job) continue;
    const hasStarted = cellsOf(placement, job).some(
      ({ day, slot }) => timeOf(board.now, board.week.id, day, slot) !== "future",
    );
    (hasStarted ? started : saving).push(placement);
  }
  return { saving, started };
}

/** 一格：「周三 下午」。 */
export function cellText({ day, slot }: Cell): string {
  return t.when(t.weekdays[day], t.slots[slot]);
}

/** 一项占的时间：「周三 下午」「周三 上午到下午」「周三 一整天」。 */
export function whenText(placement: Placement, job: Job): string {
  return t.when(t.weekdays[placement.day], slotsText(placement, job));
}

/** 一项占哪几段：「下午」「上午到下午」「一整天」。 */
function slotsText(placement: Placement, job: Job): string {
  if (job.length === SLOTS.length) return t.wholeDay;
  const last = placement.slot + job.length - 1;
  return job.length === 1 ? t.slots[placement.slot] : t.span(t.slots[placement.slot], t.slots[last]);
}

/** 月视图上的日程：`weeks`（本周和已发布的下周，各带这台设备上的草稿）里保存过的和草稿，按日期、时间段排；
 * `who` 不是 null 时只留她的（「只看她」）。`characterOf` 给角色。 */
export function dayJobs<C>(
  weeks: readonly Pick<Board, "week" | "drafts">[],
  characterOf: (id: string) => C,
  who: string | null,
): DayJob<C>[] {
  return weeks
    .flatMap(({ week, drafts }) =>
      [
        ...week.placements.map((placement) => ({ placement, isSaved: true })),
        ...drafts.map((placement) => ({ placement, isSaved: false })),
      ].flatMap(({ placement, isSaved }) => {
        const job = jobOf(week, placement.job_id);
        if (!job || !isShown(job, who)) return [];
        const day: DayJob<C> = {
          date: addDays(week.id, placement.day),
          character: characterOf(job.character_id),
          jobId: job.id,
          name: job.name,
          slotsText: slotsText(placement, job),
          isSaved,
        };
        return [{ day, slot: placement.slot }];
      }),
    )
    .sort((a, b) => a.day.date.localeCompare(b.day.date) || a.slot - b.slot)
    .map(({ day }) => day);
}

/** 确认框的列表：`placements` 一行一项（哪项工作、哪天哪几段），按周几、哪一段排。 */
export function confirmRows(
  board: Board,
  placements: readonly Placement[],
): { placement: Placement; job: Job; when: string }[] {
  return [...placements]
    .sort((a, b) => a.day - b.day || a.slot - b.slot)
    .flatMap((placement) => {
      const job = jobOf(board.week, placement.job_id);
      return job ? [{ placement, job, when: whenText(placement, job) }] : [];
    });
}

/** 保存时剔掉的已开始的那几项，确认框列表下面那一句；没有是 null。`nameOf` 给角色的名字。 */
export function startedNote(
  board: Board,
  started: readonly Placement[],
  nameOf: (characterId: string) => string,
): string | null {
  const jobs = whoseJobs(board, started, nameOf);
  return jobs ? t.startedBack(jobs) : null;
}

/** 服务器退回的几项，页上方那一句：过了、进行中的和已开始的一样说，别的照原因各说一句；没有是 null。 */
export function returnedNote(
  board: Board,
  returned: readonly Returned[],
  nameOf: (characterId: string) => string,
): string | null {
  const started = returned.filter((r) => r.reason === t.reasons.past || r.reason === t.reasons.underWay);
  const sentences = [startedNote(board, started, nameOf)];
  const others = returned.filter((r) => !started.includes(r));
  for (const reason of new Set(others.map((r) => r.reason))) {
    const jobs = whoseJobs(
      board,
      others.filter((r) => r.reason === reason),
      nameOf,
    );
    if (jobs) sentences.push(t.returnedBack(jobs, reason));
  }
  const said = sentences.filter((s) => s !== null);
  return said.length > 0 ? said.join("") : null;
}

/** 「櫻木真乃的拍摄广告、風野灯織的吃饭」；一项也没有是空的。 */
function whoseJobs(board: Board, placements: readonly Placement[], nameOf: (characterId: string) => string): string {
  return placements
    .flatMap((p) => {
      const job = jobOf(board.week, p.job_id);
      return job ? [t.whose(nameOf(job.character_id), job.name)] : [];
    })
    .join(t.slotList.separator);
}

/** 待排后面那句：没排的到制作人那边的周日 24 点作废；他那边已经是本周的周日时说「今晚」（`isTonight`）。 */
export function expiry(board: Board): { text: string; isTonight: boolean } {
  const isTonight = board.week.id === board.now.week && board.now.day === DAYS - 1;
  return { text: isTonight ? t.pending.tonight : t.pending.expires, isTonight };
}

/** 一个工作块：保存过的做完了（每一格都已过）、正在进行、还没开始；草稿已经开始了（存不了）、还没开始。 */
export type BlockState = "done" | "now" | "saved" | "started" | "draft";

/** 周视图的一格：一个工作块（横跨它占的几段）、一个空格（已过、进行中或还没到），或者「只看她」时别人占着的一格。 */
export type GridItem =
  | { kind: "block"; occupant: Occupant; state: BlockState }
  | { kind: "empty"; cell: Cell; when: When }
  | { kind: "hidden"; cell: Cell };

/** 日程里写她的地方（周视图的块、点格子的抽屉、月视图的清单）用的名字：短名，没有时全名。 */
export function shortName(character: { name: string; short_name: string | null }): string {
  return character.short_name ?? character.name;
}

/** 对话页更多菜单的「她的日程」去的地方：日历子页，「只看她」。 */
export function herScheduleHref(characterId: string): string {
  return `${playHref("calendar")}?${new URLSearchParams({ who: characterId })}`;
}

/** 日历子页地址里「只看她」的角色 id；没有 `who`（或者不止一个、是空的）是看全部。是不是真有这位角色由子页判断。 */
export function calendarWho(query: Record<string, string | string[] | undefined>): string | null {
  const { who } = query;
  return typeof who === "string" && who !== "" ? who : null;
}

/** 「只看她」：`who` 是她的角色 id 时只留她的工作，null 时都留。 */
export function isShown(job: Job, who: string | null): boolean {
  return who === null || job.character_id === who;
}

/** 周视图的 7 行（周一起），每行按哪一段排：多段的块只在开始的那一段出现一次；`who` 不是 null 时别人的块换成占着的空位。 */
export function weekGrid(board: Board, who: string | null): GridItem[][] {
  return Array.from({ length: DAYS }, (_, day) => {
    const row: GridItem[] = [];
    for (let slot = 0; slot < SLOTS.length; ) {
      const occupant = occupantOf(board, day, slot);
      if (!occupant) {
        row.push({ kind: "empty", cell: { day, slot }, when: timeOf(board.now, board.week.id, day, slot) });
        slot += 1;
      } else if (isShown(occupant.job, who)) {
        row.push({ kind: "block", occupant, state: blockState(board, occupant) });
        slot = occupant.placement.slot + occupant.job.length;
      } else {
        row.push({ kind: "hidden", cell: { day, slot } });
        slot += 1;
      }
    }
    return row;
  });
}

function blockState(board: Board, { placement, job, isSaved }: Occupant): BlockState {
  const whens = cellsOf(placement, job).map(({ day, slot }) => timeOf(board.now, board.week.id, day, slot));
  if (!isSaved) return whens.every((when) => when === "future") ? "draft" : "started";
  if (whens.every((when) => when === "past")) return "done";
  return whens.includes("now") ? "now" : "saved";
}

/** 读回来的草稿里还算数的：这一周的工作、没保存过、一项只放一次、放得进这一天，也不和保存过的或前面的草稿撞上。
 * 已经开始了的留着（块上描红，保存时剔掉）。 */
export function draftsOf(week: Week, stored: readonly Placement[]): Placement[] {
  const saved = new Set(week.placements.map((p) => p.job_id));
  const kept: Placement[] = [];
  for (const placement of stored) {
    const job = jobOf(week, placement.job_id);
    const fits =
      job &&
      !saved.has(job.id) &&
      !kept.some((p) => p.job_id === job.id) &&
      Number.isInteger(placement.day) &&
      placement.day >= 0 &&
      placement.day < DAYS &&
      Number.isInteger(placement.slot) &&
      placement.slot >= 0 &&
      placement.slot + job.length <= SLOTS.length &&
      cellsOf(placement, job).every(({ day, slot }) => !occupantOf({ week, drafts: kept }, day, slot));
    if (fits) kept.push(placement);
  }
  return kept;
}

/** 保存以后的草稿：去掉这次试过的（`attempted`，连同剔掉的已开始的）；存下的重读回来是保存过的，退回的回到待排。 */
export function afterSave(drafts: readonly Placement[], attempted: readonly Placement[]): Placement[] {
  const tried = new Set(attempted.map((p) => p.job_id));
  return drafts.filter((p) => !tried.has(p.job_id));
}

/** 这一周 id 是 `id` 的那项工作；不在这一周是 undefined。 */
function jobOf(week: Week, id: string): Job | undefined {
  return week.jobs.find((job) => job.id === id);
}

/** 待排一行的说明：「2 段 · 只能下午、晚上」，哪段都行的只写几段。 */
export function jobNote(job: Job): string {
  const length = t.pending.length(job.length);
  return job.slots ? `${length} · ${t.pending.only(slotNames(job.slots).join(t.slotList.separator))}` : length;
}

/** 几个时间段连成一句：「晚上」「下午和晚上」。 */
function slotList(slots: readonly SlotName[]): string {
  const names = slotNames(slots);
  const { separator, last } = t.slotList;
  return names.length === 1 ? names[0] : names.slice(0, -1).join(separator) + last + names[names.length - 1];
}

/** 几个时间段的名字，按上午、下午、晚上排。 */
function slotNames(slots: readonly SlotName[]): string[] {
  return SLOTS.filter((slot) => slots.includes(slot)).map((slot) => t.slots[SLOTS.indexOf(slot)]);
}

/** `date` 那一周的周一。 */
export function mondayOf(date: string): string {
  return addDays(date, -((partsOf(date).weekday + DAYS - 1) % DAYS));
}

/** 周视图正在看的那一周和怎么翻：哪一周（周号）、这一周（往周还没取到是 null）、是不是往周、标题前面的名字（没有是 null）、
 * 两边能不能翻、翻到哪（选的周，null 是本周）、有没有「回到本周」（往周才有）。 */
export type WeekPage = {
  id: string;
  week: Week | null;
  isPast: boolean;
  title: string | null;
  hasPrevious: boolean;
  hasNext: boolean;
  previous: string | null;
  next: string | null;
  hasBackToThisWeek: boolean;
};

/** 选了 `chosen`（null 是本周）时周视图看哪一周、怎么翻；往周从取过的 `past` 里拿。 */
export function weekPage(chosen: string | null, read: OpenSchedule, past: ReadonlyMap<string, Week>): WeekPage {
  const thisWeek = read.this_week.id;
  const id = weekShown(chosen, read);
  const isPast = id < thisWeek;
  const pick = (week: string) => (week === thisWeek ? null : week);
  return {
    id,
    week: isPast ? (past.get(id) ?? null) : id === thisWeek ? read.this_week : read.next_week,
    isPast,
    title: weekName(id, thisWeek),
    hasPrevious: hasPrevious(id, read),
    hasNext: isPast || (id === thisWeek && read.next_week !== null),
    previous: pick(addDays(id, -DAYS)),
    next: pick(addDays(id, DAYS)),
    hasBackToThisWeek: isPast,
  };
}

/** 月视图画的几周：取过的往周（只有保存过的），本周，和已发布的下周。 */
export function calendarWeeks(read: OpenSchedule, past: ReadonlyMap<string, Week>): Week[] {
  return [
    ...[...past.values()].filter((week) => week.id < read.this_week.id),
    read.this_week,
    ...(read.next_week ? [read.next_week] : []),
  ];
}

/** `date` 落在还没取到的往周里：月视图的清单先写「正在读取」，不说「这一天没有事」。 */
export function awaitsPast(date: string, read: OpenSchedule, past: ReadonlyMap<string, Week>): boolean {
  return pastWeeksIn(date, date, read).some((week) => !past.has(week));
}

/** 周视图标题前面的名字：本周、下周、上周；再往前没有名字，只写日期。 */
function weekName(week: string, thisWeek: string): string | null {
  if (week === thisWeek) return t.thisWeek;
  if (week === addDays(thisWeek, DAYS)) return t.nextWeek;
  if (week === addDays(thisWeek, -DAYS)) return t.lastWeek;
  return null;
}

/** 周视图看的是哪一周：选过的（`chosen`）还看得到就是它，否则本周。看得到的是已发布的下周，和最早保存过日程的那一周
 * 到本周之间的往周。 */
function weekShown(chosen: string | null, read: OpenSchedule): string {
  const thisWeek = read.this_week.id;
  if (chosen === null || chosen === thisWeek) return thisWeek;
  if (chosen === read.next_week?.id) return chosen;
  return read.first_week !== null && read.first_week <= chosen && chosen < thisWeek ? chosen : thisWeek;
}

/** 周视图能不能从 `week` 往前翻：下周能翻回本周；本周和往周要最早保存过日程的那一周早于它。 */
function hasPrevious(week: string, read: OpenSchedule): boolean {
  if (week > read.this_week.id) return true;
  return read.first_week !== null && read.first_week < week;
}

/** `from` 到 `to` 这几天碰到的往周（周号），早的在前：最早保存过日程的那一周起、本周以前；没保存过是空的。 */
export function pastWeeksIn(from: string, to: string, read: OpenSchedule): string[] {
  if (read.first_week === null) return [];
  const weeks: string[] = [];
  const start = mondayOf(from) > read.first_week ? mondayOf(from) : read.first_week;
  for (let week = start; week <= to && week < read.this_week.id; week = addDays(week, DAYS)) weeks.push(week);
  return weeks;
}

/** 这一周保存过的工作里有没有 `who`（null 是全部）的：往周一项也没有时不画格子。 */
export function hasSavedShown(week: Week, who: string | null): boolean {
  return week.placements.some((placement) => {
    const job = jobOf(week, placement.job_id);
    return job !== undefined && isShown(job, who);
  });
}

/** `week` 的工作什么时候发布：那个周一的北京时间 0 点。 */
export function publishedAt(week: string): Date {
  const [year, month, day] = week.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day, -BEIJING_HOURS));
}

/** 此刻在 `timeZone` 那边的本周、本周的工作发布了没有，和已经发布了的下周（没有是 null）。 */
export function weeksAt(
  timeZone: string,
  now: Date,
): { thisWeek: string; isPublished: boolean; nextWeek: string | null } {
  const thisWeek = localNow(timeZone, now).week;
  const nextWeek = addDays(thisWeek, DAYS);
  return {
    thisWeek,
    isPublished: now >= publishedAt(thisWeek),
    nextWeek: now >= publishedAt(nextWeek) ? nextWeek : null,
  };
}

/** 读到的日程在此刻是不是过时了：制作人那边换了周，或者本周、下周的工作在读过以后发布了。 */
export function isOutdated(read: OpenSchedule, now: Date): boolean {
  const weeks = weeksAt(read.timezone, now);
  return (
    weeks.thisWeek !== read.this_week.id ||
    weeks.isPublished !== read.this_week.published ||
    weeks.nextWeek !== (read.next_week?.id ?? null)
  );
}


// 草稿只存在这台设备上（.scratch/schedule spec「日程的规则」）：localStorage 里按用户、按周号一个键
// （eidolon.scheduleDrafts.<用户 ID>.<周号>），值是放置的列表；读的时候把这位用户别的周的键删掉。存不进去（隐私模式等）时
// 不抛错，只在这次页面里记着。

const DRAFTS_KEY = "eidolon.scheduleDrafts";

function draftsKey(userId: string, week: string): string {
  return `${DRAFTS_KEY}.${userId}.${week}`;
}

/** 存不进去时，这次页面里记着的，按键。 */
const draftsThisPage = new Map<string, Placement[]>();

/** 这位用户在这台设备上 `weeks` 这几周的草稿（没有的是空的）；别的周的草稿丢掉。 */
export function readDrafts(userId: string, weeks: readonly string[]): Map<string, Placement[]> {
  const prefix = `${DRAFTS_KEY}.${userId}.`;
  const wanted = new Set(weeks.map((week) => draftsKey(userId, week)));
  try {
    for (let i = localStorage.length - 1; i >= 0; i--) {
      const key = localStorage.key(i);
      if (key?.startsWith(prefix) && !wanted.has(key)) localStorage.removeItem(key);
    }
  } catch {
    // 存储不可用：只有这次页面里记着的。
  }
  for (const key of draftsThisPage.keys()) if (key.startsWith(prefix) && !wanted.has(key)) draftsThisPage.delete(key);
  return new Map(weeks.map((week) => [week, storedDrafts(draftsKey(userId, week))]));
}

/** 存下这位用户 `week` 的草稿；没有草稿时删掉这个键。 */
export function keepDrafts(userId: string, week: string, placements: readonly Placement[]): void {
  const key = draftsKey(userId, week);
  try {
    if (placements.length === 0) localStorage.removeItem(key);
    else localStorage.setItem(key, JSON.stringify(placements));
    draftsThisPage.delete(key);
  } catch {
    // 存储不可用：只在这次页面里记着。
    draftsThisPage.set(key, [...placements]);
  }
}

function storedDrafts(key: string): Placement[] {
  const kept = draftsThisPage.get(key);
  if (kept) return kept;
  let stored: unknown;
  try {
    stored = JSON.parse(localStorage.getItem(key) ?? "[]");
  } catch {
    return [];
  }
  return Array.isArray(stored) && stored.every(isPlacement) ? stored : [];
}

function isPlacement(value: unknown): value is Placement {
  if (typeof value !== "object" || value === null) return false;
  const { job_id, day, slot } = value as Record<string, unknown>;
  return typeof job_id === "string" && typeof day === "number" && typeof slot === "number";
}
