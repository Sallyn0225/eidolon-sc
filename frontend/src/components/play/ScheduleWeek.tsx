"use client";

import { type CSSProperties, Fragment, type ReactNode, useState } from "react";

import { MarkedAvatar } from "@/components/app/MarkedAvatar";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Drawer, DrawerContent, DrawerDescription, DrawerHeader, DrawerTitle } from "@/components/ui/drawer";
import { Popover, PopoverContent, PopoverDescription, PopoverHeader, PopoverTitle, PopoverTrigger } from "@/components/ui/popover";
import { copy } from "@/i18n";
import type { Character } from "@/lib/api";
import { addDays, type CalendarData, type CalendarEvent, eventsOn, partsOf } from "@/lib/calendar";
import {
  type Board,
  type BlockState,
  type Cell,
  cellText,
  confirmRows,
  expiry,
  freeSlots,
  type GridItem,
  hasSavedShown,
  isShown,
  type Job,
  type JobCategory,
  jobNote,
  type Occupant,
  pendingJobs,
  type Placement,
  shortName,
  startedNote,
  startsFor,
  toSave,
  weekGrid,
  whenText,
  whyNot,
} from "@/lib/schedule";
import { cn } from "@/lib/utils";
import { herVars } from "@/theme/herVars";
import {
  AppearanceJobIcon,
  BusinessJobIcon,
  LockedIcon,
  NextMonthIcon,
  PracticeJobIcon,
  PreviousMonthIcon,
  PrivateJobIcon,
} from "@/theme/icons";

const t = copy.play.schedule;

const CATEGORY_ICONS = {
  practice: PracticeJobIcon,
  appearance: AppearanceJobIcon,
  business: BusinessJobIcon,
  private: PrivateJobIcon,
} satisfies Record<JobCategory, unknown>;

/** 工作块横跨几列。 */
const SPANS = ["col-span-1", "col-span-2", "col-span-3"];

/** 日程上的一位：不在名单里的（已经下线）名字是 id，没有短名、头像和颜色（`color` 是 null）。 */
export type ScheduledCharacter = Pick<Character, "id" | "name" | "short_name" | "avatar_url"> & { color: string | null };

/** 角色 id → 她。 */
export type CharacterOf = (id: string) => ScheduledCharacter;

/** 待排、抽屉里一行一项的按钮。 */
const ROW =
  "flex w-full min-w-0 items-center gap-2 rounded-lg px-2 py-2 text-left outline-none hover:bg-muted/60 focus-visible:ring-3 focus-visible:ring-ring/50";

/** 她的颜色，注入到一块上；没有颜色的不注入。 */
function herStyle({ color }: ScheduledCharacter): CSSProperties | undefined {
  return color ? herVars(color) : undefined;
}

/**
 * 日历子页的周视图和待排（DESIGN.md「玩法页」，.scratch/schedule spec「界面」）：一行一天、三列时间段，多段的工作块
 * 横着占几格；待排按偶像分组。怎么算都在 lib/schedule，这里只管画和接住点击，草稿交给 `onDrafts` 存。
 * 电脑（`isWide`）上左边一列待排、右边周视图：选中一项待排，能放的格子亮起来（她的 `--her-wall` 底、`--her-mark` 描边），
 * 别的格子淡下去，点亮着的放进去成草稿；点草稿块拿回待排并选中它；点保存过的块弹说明。
 * 手机上周视图在上、待排在下：点空格、点待排一项、点工作块各弹一个底部抽屉。
 * 本周的工作没发布时格子的位置写一句「本周的工作北京时间周一 0:00 发布」，不显示待排。
 * 往周（`isPast`）只看：只有保存过的块（都是做完了的），没有待排；一项也没有时格子的位置写「这周没有排日程」
 * （只看她时「这周没有她的日程」）；还没读到（`board` 是 null）时写「正在读取」。
 * `who` 是「只看她」的角色 id（null 是全部）：只画她的块和她的待排，别人占着的格子是空着的灰格。
 */
export function ScheduleWeek({
  week,
  board,
  isPast,
  nav,
  characterOf,
  calendar,
  who,
  isWide,
  onDrafts,
}: {
  /** 看的是哪一周（周号）。 */
  week: string;
  /** 这一周；往周还没读到是 null。 */
  board: Board | null;
  /** 是本周以前的往周：只看。 */
  isPast: boolean;
  nav: WeekNav;
  characterOf: CharacterOf;
  /** 行首的节假日和角色生日从这里来。 */
  calendar: CalendarData<Character>;
  who: string | null;
  isWide: boolean;
  onDrafts: (drafts: Placement[]) => void;
}) {
  // 电脑上选中的待排；手机上打开着的抽屉（收起的动画里内容不消失，所以收起时只改 `open`）。
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [cellSheet, setCellSheet] = useState<Opened<Cell>>(null);
  const [jobSheet, setJobSheet] = useState<Opened<Job>>(null);
  const [blockSheet, setBlockSheet] = useState<Opened<Occupant>>(null);

  const range = t.range(dateText(week), dateText(addDays(week, 6)));
  const heading = <WeekHeading range={range} nav={nav} />;
  const label = nav.title ?? range;
  if (board === null || (isPast && !hasSavedShown(board.week, who))) {
    return (
      <section aria-label={label} className="flex min-w-0 flex-col gap-3">
        {heading}
        <InPlaceOfGrid text={board === null ? copy.play.loading : who === null ? t.emptyWeek : t.emptyWeekHers} />
      </section>
    );
  }

  const pending = isPast ? [] : pendingJobs(board).filter((job) => isShown(job, who));
  const selected = isWide ? (pending.find((job) => job.id === selectedId) ?? null) : null;
  const isPublished = board.week.published;

  const { drafts } = board;
  function place(job: Job, { day, slot }: Cell) {
    onDrafts([...drafts.filter((p) => p.job_id !== job.id), { job_id: job.id, day, slot }]);
  }
  function takeBack(job: Job) {
    onDrafts(drafts.filter((p) => p.job_id !== job.id));
  }

  const grid = (
    <WeekGrid
      board={board}
      who={who}
      characterOf={characterOf}
      calendar={calendar}
      selected={selected}
      isWide={isWide}
      onEmpty={(cell) => {
        if (!isWide) setCellSheet({ value: cell, open: true });
        else if (selected) {
          place(selected, cell);
          setSelectedId(null);
        }
      }}
      onBlock={(occupant) => {
        if (isWide) {
          // 草稿拿回待排、选中它，好换个地方放；保存过的由块自己弹说明。
          takeBack(occupant.job);
          setSelectedId(occupant.job.id);
        } else setBlockSheet({ value: occupant, open: true });
      }}
    />
  );
  const pendingList = isPublished && !isPast && (
    <Pending
      board={board}
      pending={pending}
      characterOf={characterOf}
      selectedId={selected?.id ?? null}
      onJob={(job) =>
        isWide ? setSelectedId(job.id === selectedId ? null : job.id) : setJobSheet({ value: job, open: true })
      }
    />
  );

  return (
    <div className="flex flex-col gap-6 md:flex-row md:items-start">
      {isWide && pendingList && <div className="flex w-64 shrink-0 flex-col md:sticky md:top-0">{pendingList}</div>}
      <section aria-label={label} className="flex min-w-0 flex-1 flex-col gap-3">
        {heading}
        {isPublished ? (
          grid
        ) : (
          <InPlaceOfGrid text={t.unpublished} />
        )}
      </section>
      {!isWide && pendingList}
      {!isWide && (
        <>
          <CellDrawer
            sheet={cellSheet}
            board={board}
            pending={pending}
            characterOf={characterOf}
            onPlace={(job, cell) => {
              place(job, cell);
              setCellSheet((s) => s && { ...s, open: false });
            }}
            onClose={() => setCellSheet((s) => s && { ...s, open: false })}
          />
          <PlaceDrawer
            sheet={jobSheet}
            board={board}
            characterOf={characterOf}
            onPlace={(job, cell) => {
              place(job, cell);
              setJobSheet((s) => s && { ...s, open: false });
            }}
            onClose={() => setJobSheet((s) => s && { ...s, open: false })}
          />
          <BlockDrawer
            sheet={blockSheet}
            characterOf={characterOf}
            onTakeBack={(job) => {
              takeBack(job);
              setBlockSheet((s) => s && { ...s, open: false });
            }}
            onClose={() => setBlockSheet((s) => s && { ...s, open: false })}
          />
        </>
      )}
    </div>
  );
}

/** 一个抽屉：给它的那一项和开着没有；从没打开过是 null。 */
type Opened<T> = { value: T; open: boolean } | null;

/** 周视图标题怎么翻：标题前面的名字（本周、下周、上周，再往前没有）、两边能不能翻、翻到哪，和「回到本周」（只在往周有）。 */
export type WeekNav = {
  title: string | null;
  hasPrevious: boolean;
  hasNext: boolean;
  onPrevious: () => void;
  onNext: () => void;
  /** 翻到往周时才有。 */
  onThisWeek: (() => void) | null;
};

/** 格子的位置上一块描边，中间一句 muted 的话：本周的工作没发布、往周没排、还没取到。 */
function InPlaceOfGrid({ text }: { text: string }) {
  return <p className="rounded-lg border py-16 text-center text-body text-muted-foreground">{text}</p>;
}

/** 「本周 10月19日 – 10月25日」（`range` 是后面的日期），两边上周、下周：往前翻到最早保存过日程的那一周，往后只到已发布的
 * 下周；翻到往周时末尾一个「回到本周」。 */
function WeekHeading({ range, nav }: { range: string; nav: WeekNav }) {
  return (
    <div className="flex items-center gap-1">
      <Button variant="ghost" size="icon-sm" aria-label={t.previous} disabled={!nav.hasPrevious} onClick={nav.onPrevious}>
        <PreviousMonthIcon />
      </Button>
      <h2 className="flex min-w-0 items-baseline gap-2 text-header">
        {nav.title ?? <span className="truncate tabular-nums">{range}</span>}
        {nav.title && (
          <span className="truncate text-subtitle font-normal text-muted-foreground tabular-nums">{range}</span>
        )}
      </h2>
      <Button variant="ghost" size="icon-sm" aria-label={t.next} disabled={!nav.hasNext} onClick={nav.onNext}>
        <NextMonthIcon />
      </Button>
      {nav.onThisWeek && (
        <Button variant="ghost" size="sm" className="ml-auto" onClick={nav.onThisWeek}>
          {t.backToThisWeek}
        </Button>
      )}
    </div>
  );
}

/** 「10月19日」。 */
function dateText(date: string): string {
  const { month, day } = partsOf(date);
  return copy.play.calendar.date(month, day);
}

/**
 * 一周的格子：表头「上午 6–12」「下午 12–18」「晚上 18–24」，一行一天，行首周几、日期（今天的圆底）和当天的节假日、
 * 角色生日。空的还没到的格子描边；已过、进行中的空格铺 `bg-muted/40` 写「已过」「进行中」、不能点。
 */
function WeekGrid({
  board,
  who,
  characterOf,
  calendar,
  selected,
  isWide,
  onEmpty,
  onBlock,
}: {
  board: Board;
  who: string | null;
  characterOf: CharacterOf;
  calendar: CalendarData<Character>;
  /** 电脑上选中的待排；没选是 null。 */
  selected: Job | null;
  isWide: boolean;
  onEmpty: (cell: Cell) => void;
  onBlock: (occupant: Occupant) => void;
}) {
  const litVars = selected ? herStyle(characterOf(selected.character_id)) : undefined;
  return (
    <div className="grid grid-cols-[4.5rem_repeat(3,minmax(0,1fr))] gap-1">
      <span aria-hidden />
      {t.slotHeads.map((head) => (
        <span key={head} aria-hidden className="px-1 text-center text-meta text-muted-foreground">
          {head}
        </span>
      ))}
      {weekGrid(board, who).map((row, day) => {
        const date = addDays(board.week.id, day);
        return (
          <Fragment key={date}>
            <DayHead
              date={date}
              day={day}
              isToday={date === board.now.date}
              events={eventsOn(date, calendar, ["character", "holiday"])}
            />
            {row.map((item) => (
              <GridCell
                key={item.kind === "block" ? item.occupant.job.id : `${item.cell.slot}`}
                item={item}
                board={board}
                characterOf={characterOf}
                selected={selected}
                litVars={litVars}
                isWide={isWide}
                onEmpty={onEmpty}
                onBlock={onBlock}
              />
            ))}
          </Fragment>
        );
      })}
    </div>
  );
}

/** 行首：周几、日期（今天的中性圆底），下面 Meta 字号 muted 的节假日和角色生日（生日带她 16px 的头像）。 */
function DayHead({
  date,
  day,
  isToday,
  events,
}: {
  date: string;
  day: number;
  isToday: boolean;
  events: CalendarEvent<Character>[];
}) {
  return (
    <div className="flex min-w-0 flex-col justify-center gap-0.5 py-1">
      <span className="flex items-center gap-1 text-subtitle" aria-current={isToday ? "date" : undefined}>
        {t.weekdays[day]}
        <span
          className={cn(
            "flex size-6 items-center justify-center rounded-full tabular-nums",
            isToday && "bg-foreground text-background",
          )}
        >
          {partsOf(date).day}
        </span>
      </span>
      {events.map((event) =>
        event.kind === "character" ? (
          <span key={event.character.id} className="flex min-w-0 items-center gap-1 text-meta text-muted-foreground">
            <MarkedAvatar name={event.character.name} src={event.character.avatar_url} size="2xs" />
            <span className="truncate">{copy.play.cards.calendar.birthday(event.character.name)}</span>
          </span>
        ) : (
          event.kind === "holiday" && (
            <span key={event.name} className="truncate text-meta text-muted-foreground">
              {event.name}
            </span>
          )
        ),
      )}
    </div>
  );
}

/** 一格：工作块、别人占着的灰格（只看她时）、或者空格。 */
function GridCell({
  item,
  board,
  characterOf,
  selected,
  litVars,
  isWide,
  onEmpty,
  onBlock,
}: {
  item: GridItem;
  board: Board;
  characterOf: CharacterOf;
  selected: Job | null;
  litVars: CSSProperties | undefined;
  isWide: boolean;
  onEmpty: (cell: Cell) => void;
  onBlock: (occupant: Occupant) => void;
}) {
  const isDim = selected !== null;
  if (item.kind === "block") {
    return (
      <Block
        occupant={item.occupant}
        state={item.state}
        character={characterOf(item.occupant.job.character_id)}
        isDim={isDim}
        isWide={isWide}
        onClick={() => onBlock(item.occupant)}
      />
    );
  }
  if (item.kind === "hidden") return <span className={cn("min-h-16 rounded-lg bg-muted/40", isDim && "opacity-50")} />;
  const { cell, when } = item;
  if (when !== "future") {
    return (
      <span
        className={cn(
          "flex min-h-16 items-center justify-center rounded-lg bg-muted/40 text-meta text-muted-foreground",
          isDim && "opacity-50",
        )}
      >
        {when === "now" ? t.underWay : t.past}
      </span>
    );
  }
  const label = cellText(cell);
  const isLit = selected !== null && whyNot(board, selected, cell.day, cell.slot) === null;
  // 电脑上没选中待排、或者选中的放不进这一格时，空格只是一格，不能点。
  if (isWide && !isLit) {
    return <span aria-label={label} className={cn("min-h-16 rounded-lg border", isDim && "opacity-50")} />;
  }
  return (
    <button
      type="button"
      aria-label={label}
      style={isLit ? litVars : undefined}
      onClick={() => onEmpty(cell)}
      className={cn(
        "min-h-16 rounded-lg border outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
        isLit ? "border-her-mark bg-her-wall" : "hover:bg-muted/60",
      )}
    />
  );
}

/**
 * 一个工作块，横跨它占的几段：第一行她 20px 的头像和名字（保存过的末尾一个 14px 的锁），第二行类别图标和工作名。
 * 保存过的铺她的 `--her-wall`，草稿一圈中性虚线、不上色，正在进行的外面一圈 2px 的 `--her-mark`，做完的淡下去，
 * 已经开始了的草稿描红、写「开始了，存不了」。每一块单独注入一次她的颜色。电脑上保存过的块点了弹 Popover 看说明。
 */
function Block({
  occupant,
  state,
  character,
  isDim,
  isWide,
  onClick,
}: {
  occupant: Occupant;
  state: BlockState;
  character: ScheduledCharacter;
  /** 电脑上选中了待排，别的格子淡下去。 */
  isDim: boolean;
  isWide: boolean;
  onClick: () => void;
}) {
  const { job, isSaved } = occupant;
  const Icon = CATEGORY_ICONS[job.category];
  const className = cn(
    SPANS[job.length - 1],
    "flex min-h-16 min-w-0 flex-col justify-center gap-1 rounded-lg border px-2 py-1.5 text-left outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
    isSaved ? "border-transparent bg-her-wall" : "border-dashed border-foreground/40",
    state === "started" && "border-destructive",
    state === "now" && "ring-2 ring-her-mark ring-offset-2 ring-offset-background",
    state === "done" && "opacity-60",
    isDim && "opacity-50",
  );
  const face = (
    <>
      <span className="flex min-w-0 items-center gap-1">
        <MarkedAvatar name={character.name} src={character.avatar_url} size="xs" />
        <span className="truncate text-subtitle font-medium">{shortName(character)}</span>
        {isSaved && <LockedIcon aria-hidden className="ml-auto size-3.5 shrink-0 text-muted-foreground" />}
      </span>
      <span className="flex min-w-0 items-center gap-1 text-meta text-muted-foreground">
        <Icon aria-hidden className="size-3 shrink-0" />
        <span className="truncate">{job.name}</span>
      </span>
      {state === "started" && <span className="text-meta text-destructive">{t.states.started}</span>}
    </>
  );
  const label = t.block(character.name, job.name, t.states[state]);
  const style = herStyle(character);
  if (isSaved && isWide) {
    return (
      <Popover>
        <PopoverTrigger render={<button type="button" aria-label={label} style={style} className={className} />}>
          {face}
        </PopoverTrigger>
        <PopoverContent align="start">
          <JobAbout occupant={occupant} character={character} />
        </PopoverContent>
      </Popover>
    );
  }
  return (
    <button type="button" aria-label={label} style={style} className={className} onClick={onClick}>
      {face}
    </button>
  );
}

/** 电脑上保存过的块弹出的说明：她的头像、谁的哪项、哪天哪几段，和工作的说明。 */
function JobAbout({ occupant, character }: { occupant: Occupant; character: ScheduledCharacter }) {
  return (
    <>
      <PopoverHeader className="flex-row items-center gap-2">
        <MarkedAvatar name={character.name} src={character.avatar_url} size="sm" />
        <span className="flex min-w-0 flex-col">
          <PopoverTitle>{t.whose(character.name, occupant.job.name)}</PopoverTitle>
          <PopoverDescription>{whenText(occupant.placement, occupant.job)}</PopoverDescription>
        </span>
      </PopoverHeader>
      <p>{occupant.job.note}</p>
    </>
  );
}

/**
 * 待排：「待排 n 项」（Header 字号），后面 muted 的「还能排 n 格 · 周日 24 点后作废」（制作人那边已是周日时「今晚 24 点后作废」
 * 不再 muted）；按偶像分组，小标题是 24px 头像和全名，下面不带边框的行：类别图标、名字、Meta 字号 muted 的「2 段 · 只能下午、晚上」，
 * 选中的行铺中性 `bg-muted`。都排好了时一句 muted 的「本周的工作都排好了」。
 */
function Pending({
  board,
  pending,
  characterOf,
  selectedId,
  onJob,
}: {
  board: Board;
  pending: Job[];
  characterOf: CharacterOf;
  selectedId: string | null;
  onJob: (job: Job) => void;
}) {
  const { text, isTonight } = expiry(board);
  const groups = Map.groupBy(pending, (job) => job.character_id);
  return (
    <section aria-labelledby="schedule-pending" className="flex flex-col gap-3">
      <h2 id="schedule-pending" className="flex flex-wrap items-baseline gap-x-2 text-header">
        {t.pending.title(pending.length)}
        <span className="text-subtitle font-normal text-muted-foreground">
          {t.pending.left(freeSlots(board))} · <span className={cn(isTonight && "font-medium text-foreground")}>{text}</span>
        </span>
      </h2>
      {pending.length === 0 ? (
        <p className="text-body text-muted-foreground">{t.pending.allPlaced}</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {[...groups].map(([characterId, jobs]) => {
            const character = characterOf(characterId);
            return (
              <li key={characterId} className="flex flex-col gap-1">
                <span className="flex min-w-0 items-center gap-2 text-body font-medium">
                  <MarkedAvatar name={character.name} src={character.avatar_url} size="sm" />
                  <span className="truncate">{character.name}</span>
                </span>
                <ul className="flex flex-col">
                  {jobs.map((job) => (
                    <li key={job.id}>
                      <button
                        type="button"
                        aria-pressed={selectedId === null ? undefined : job.id === selectedId}
                        onClick={() => onJob(job)}
                        className={cn(ROW, job.id === selectedId && "bg-muted hover:bg-muted")}
                      >
                        <JobName job={job} />
                      </button>
                    </li>
                  ))}
                </ul>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

/** 待排一行的内容：类别图标、名字，后面 Meta 字号 muted 的几段和时段限制（或者 `aside` 给的排不了的原因）。 */
function JobName({ job, aside }: { job: Job; aside?: ReactNode }) {
  const Icon = CATEGORY_ICONS[job.category];
  return (
    <>
      <Icon aria-label={t.categories[job.category]} className="size-4 shrink-0 text-muted-foreground" />
      <span className="min-w-0 truncate text-body">{job.name}</span>
      <span className="ml-auto shrink-0 text-meta text-muted-foreground">{aside ?? jobNote(job)}</span>
    </>
  );
}

/** 抽屉的页首：她的头像、标题和一句说明；抽屉内容上注入她的颜色。 */
function HerDrawerHeader({
  character,
  title,
  description,
}: {
  character: ScheduledCharacter;
  title: string;
  description: string;
}) {
  return (
    <DrawerHeader className="flex-row items-center gap-3 pb-4">
      <MarkedAvatar name={character.name} src={character.avatar_url} size="bubble" />
      <span className="flex min-w-0 flex-col gap-0.5 text-left">
        <DrawerTitle>{title}</DrawerTitle>
        <DrawerDescription>{description}</DrawerDescription>
      </span>
    </DrawerHeader>
  );
}

/** 手机上点了一个空格：标题「周三 下午」，列出待排，能从这一格开始的排前面，排不了的淡下去、右边写原因。 */
function CellDrawer({
  sheet,
  board,
  pending,
  characterOf,
  onPlace,
  onClose,
}: {
  sheet: Opened<Cell>;
  board: Board;
  pending: Job[];
  characterOf: CharacterOf;
  onPlace: (job: Job, cell: Cell) => void;
  onClose: () => void;
}) {
  const cell = sheet?.value;
  const rows = cell
    ? pending
        .map((job) => ({ job, reason: whyNot(board, job, cell.day, cell.slot) }))
        .sort((a, b) => Number(a.reason !== null) - Number(b.reason !== null))
    : [];
  return (
    <Drawer open={sheet?.open ?? false} onOpenChange={(open) => !open && onClose()} showSwipeHandle>
      <DrawerContent>
        {cell && (
          <>
            <DrawerHeader className="pb-4">
              <DrawerTitle>{cellText(cell)}</DrawerTitle>
            </DrawerHeader>
            <ul className="flex flex-col overflow-y-auto px-4 pb-6">
              {rows.map(({ job, reason }) => {
                const character = characterOf(job.character_id);
                return (
                  <li key={job.id}>
                    <button
                      type="button"
                      disabled={reason !== null}
                      onClick={() => onPlace(job, cell)}
                      className={cn(ROW, "disabled:opacity-50 disabled:hover:bg-transparent")}
                    >
                      <MarkedAvatar name={character.name} src={character.avatar_url} size="sm" />
                      <span className="shrink-0 text-body">{shortName(character)}</span>
                      <JobName job={job} aside={reason ?? undefined} />
                    </button>
                  </li>
                );
              })}
            </ul>
          </>
        )}
      </DrawerContent>
    </Drawer>
  );
}

/** 手机上点了待排一项：「拍摄广告 排到…」，列出放得下的时间段，一行一个，点了放进去。 */
function PlaceDrawer({
  sheet,
  board,
  characterOf,
  onPlace,
  onClose,
}: {
  sheet: Opened<Job>;
  board: Board;
  characterOf: CharacterOf;
  onPlace: (job: Job, cell: Cell) => void;
  onClose: () => void;
}) {
  const job = sheet?.value;
  const character = job && characterOf(job.character_id);
  const starts = job ? startsFor(board, job) : [];
  return (
    <Drawer open={sheet?.open ?? false} onOpenChange={(open) => !open && onClose()} showSwipeHandle>
      <DrawerContent style={character && herStyle(character)}>
        {job && character && (
          <>
            <HerDrawerHeader character={character} title={t.placeAt(job.name)} description={job.note} />
            <ul className="flex flex-col overflow-y-auto px-4 pb-6">
              {starts.length === 0 && <li className="px-2 py-2 text-body text-muted-foreground">{t.nowhere}</li>}
              {starts.map((cell) => (
                <li key={`${cell.day}-${cell.slot}`}>
                  <button
                    type="button"
                    onClick={() => onPlace(job, cell)}
                    className={cn(ROW, "text-body")}
                  >
                    {whenText({ job_id: job.id, ...cell }, job)}
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
      </DrawerContent>
    </Drawer>
  );
}

/** 手机上点了一个工作块：说明；草稿下面多一个「拿回待排」。 */
function BlockDrawer({
  sheet,
  characterOf,
  onTakeBack,
  onClose,
}: {
  sheet: Opened<Occupant>;
  characterOf: CharacterOf;
  onTakeBack: (job: Job) => void;
  onClose: () => void;
}) {
  const occupant = sheet?.value;
  const character = occupant && characterOf(occupant.job.character_id);
  return (
    <Drawer open={sheet?.open ?? false} onOpenChange={(open) => !open && onClose()} showSwipeHandle>
      <DrawerContent style={character && herStyle(character)}>
        {occupant && character && (
          <>
            <HerDrawerHeader
              character={character}
              title={t.whose(character.name, occupant.job.name)}
              description={whenText(occupant.placement, occupant.job)}
            />
            <div className="flex flex-col gap-4 px-4 pb-6">
              <p className="text-body">{occupant.job.note}</p>
              {!occupant.isSaved && (
                <Button variant="outline" onClick={() => onTakeBack(occupant.job)}>
                  {t.takeBack}
                </Button>
              )}
            </div>
          </>
        )}
      </DrawerContent>
    </Drawer>
  );
}

/**
 * 保存条：有草稿时固定在内容底部，「草稿 n 项 · 保存后她才知道」加「保存」。点了先把已经开始的剔掉（`toSave`）：都开始了就不弹框、
 * 直接退回；否则弹确认框，标题「保存这 n 项？」，每项一行（她 24px 的头像、「周三 下午」、名字、工作名），剔掉的在列表下面一句 muted 的话。
 * `onSave` 拿这次要存的和剔掉的，存完（不论成败）收起确认框。
 */
export function SaveBar({
  board,
  characterOf,
  isSaving,
  onSave,
}: {
  board: Board;
  characterOf: CharacterOf;
  isSaving: boolean;
  onSave: (saving: Placement[], started: Placement[]) => Promise<void>;
}) {
  const [asking, setAsking] = useState<{ saving: Placement[]; started: Placement[] } | null>(null);
  const [isOpen, setOpen] = useState(false);
  const nameOf = (id: string) => characterOf(id).name;

  function askFirst() {
    const split = toSave(board);
    if (split.saving.length === 0) {
      onSave([], split.started);
      return;
    }
    setAsking(split);
    setOpen(true);
  }

  async function save() {
    if (!asking) return;
    await onSave(asking.saving, asking.started);
    setOpen(false);
  }

  const startedText = asking && startedNote(board, asking.started, nameOf);
  return (
    <div className="mx-auto flex w-full max-w-3xl items-center gap-3">
      <p className="min-w-0 flex-1 text-body">
        {t.drafts(board.drafts.length)}
        <span className="text-muted-foreground"> · {t.draftsNote}</span>
      </p>
      <Button disabled={isSaving} onClick={askFirst}>
        {t.save}
      </Button>
      <AlertDialog open={isOpen} onOpenChange={(open) => !isSaving && setOpen(open)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t.confirm.title(asking?.saving.length ?? 0)}</AlertDialogTitle>
            <AlertDialogDescription>{t.confirm.description}</AlertDialogDescription>
          </AlertDialogHeader>
          <ul className="flex flex-col gap-2">
            {asking &&
              confirmRows(board, asking.saving).map(({ job, when }) => {
                const character = characterOf(job.character_id);
                return (
                  <li key={job.id} className="flex min-w-0 items-center gap-2 text-body">
                    <MarkedAvatar name={character.name} src={character.avatar_url} size="sm" />
                    <span className="shrink-0">{when}</span>
                    <span className="shrink-0">{character.name}</span>
                    <span className="truncate">{job.name}</span>
                  </li>
                );
              })}
          </ul>
          {startedText && <p className="text-subtitle text-muted-foreground">{startedText}</p>}
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isSaving}>{t.confirm.cancel}</AlertDialogCancel>
            <AlertDialogAction disabled={isSaving} onClick={save}>
              {t.confirm.save}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
