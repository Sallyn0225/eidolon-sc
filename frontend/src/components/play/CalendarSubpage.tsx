"use client";

import { useRouter } from "next/navigation";
import { type ReactNode, useState } from "react";

import { FailureNotice } from "@/components/app/FailureNotice";
import { MarkedAvatar } from "@/components/app/MarkedAvatar";
import { useDirectory, useWide } from "@/components/conversations/ConversationDirectory";
import { HerStrip } from "@/components/play/HerStrip";
import { PlayShell, PlaySubpageHeader } from "@/components/play/PlayShell";
import { type CharacterOf, SaveBar, ScheduleWeek, type WeekNav } from "@/components/play/ScheduleWeek";
import { useCalendar } from "@/components/play/useCalendar";
import { Alert, AlertAction, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { copy } from "@/i18n";
import { ApiError, type Character } from "@/lib/api";
import {
  addDays,
  CALENDAR_KINDS,
  type CalendarCell,
  type CalendarData,
  type CalendarEvent,
  type CalendarKind,
  type CalendarMode,
  type CalendarMonth,
  calendarKinds,
  calendarMode,
  type DayJob,
  cellLines,
  eventsOn,
  keepCalendarMode,
  monthCells,
  monthOf,
  partsOf,
  shiftMonth,
} from "@/lib/calendar";
import { type Failure, toFailure } from "@/lib/failure";
import { playTitle } from "@/lib/playCards";
import { playHref } from "@/lib/playRoute";
import {
  afterSave,
  type Board,
  awaitsPast,
  calendarWeeks,
  dayJobs,
  type Placement,
  pastWeeksIn,
  returnedNote,
  saveSchedule,
  shortName,
  startedNote,
  weekPage,
} from "@/lib/schedule";
import { cn } from "@/lib/utils";
import { herVars } from "@/theme/herVars";
import {
  BirthdayIcon,
  CloseIcon,
  FailureIcon,
  HolidayIcon,
  MonthViewIcon,
  NextMonthIcon,
  PreviousMonthIcon,
  ScheduleIcon,
  WeekViewIcon,
} from "@/theme/icons";

const t = copy.play.calendar;

/** 手机上一格最多几个记号。 */
const CELL_MARKS = 4;

const FILTER_ICONS = {
  character: BirthdayIcon,
  producer: BirthdayIcon,
  holiday: HolidayIcon,
  schedule: ScheduleIcon,
} satisfies Record<CalendarKind, unknown>;

/**
 * 「日历」子页（`/play/calendar`，DESIGN.md「玩法页」）：页首返回键回玩法页，日程开着时末端是月 / 周切换
 * （默认周视图，上次选的记在这台设备上，lib/calendar）；日程关着时没有切换、只有月视图。
 * 月视图从上到下是筛选、月视图和点中的那一天的清单（默认今天，制作人时区）。节假日按月视图和本周、下周上的那几年取，
 * 没回来之前先画生日，这一天所在的年没回来、又没有生日时先不说「这一天没有事」。
 * 周视图是本周（和已发布的下周）的日程和待排（components/play/ScheduleWeek），有草稿时内容底部一条保存条；
 * 保存时服务器退回了哪几项，页上方说一句。周视图能往前翻到最早保存过日程的那一周，往周只看；每次进来先看本周（选的周不记）。
 * 月视图翻到哪个月，就取那一屏碰到的往周，把保存过的工作画进去。日程读到之前整页先写「正在读取」，免得先画月视图再跳成周视图。
 * 地址带着 `who`（对话页更多菜单的「她的日程」）时「只看她」：两种视图都只画她的日程和她的待排，页首下面一条
 * 「只看〇〇的日程」，点 ✕ 地址去掉 `who`。角色不存在、或日程关着时当作没有。
 * 好感度和礼物没开放时照常有。
 */
export function CalendarSubpage({ who }: { who: string | null }) {
  const [month, setMonth] = useState<CalendarMonth | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  const [kept, setKept] = useState<{ userId: string; mode: CalendarMode } | null>(null);
  // 周视图选的那一周（周号）；null 是本周。
  const [chosenWeek, setChosenWeek] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [failure, setFailure] = useState<Failure | null>(null);
  const [isSaving, setSaving] = useState(false);
  const isWide = useWide();
  const router = useRouter();
  const { account, characters } = useDirectory();
  // 点过 ✕ 的「只看她」：地址换掉以前（重新渲染要等一下）就不再显示；地址里没有 `who` 以后忘掉。
  const [dropped, setDropped] = useState<string | null>(null);
  if (!who && dropped !== null) setDropped(null);
  const {
    calendar,
    hasHolidaysOf,
    keepShown,
    schedule,
    scheduleFailure,
    scheduleNow,
    draftsOn,
    keepDraftsOn,
    readSchedule,
    closeSchedule,
    past,
    pastFailure,
  } = useCalendar({
    // 月视图首尾两格所在的年，周视图本周、下周所在的年，和翻到的往周所在的年（跨年也给）。
    years: (today) => [
      ...yearsOn(monthCells(month ?? monthOf(today), today)),
      partsOf(addDays(today, -6)).year,
      partsOf(addDays(today, 13)).year,
      ...(chosenWeek ? [partsOf(chosenWeek).year, partsOf(addDays(chosenWeek, 6)).year] : []),
    ],
    // 月视图这一屏碰到的往周一组，周视图翻到的往周一组。
    pastWeeks: (read, today) => {
      const cells = monthCells(month ?? monthOf(today), today);
      const { id, isPast } = weekPage(chosenWeek, read, new Map());
      return [pastWeeksIn(cells[0].date, cells[cells.length - 1].date, read), ...(isPast ? [[id]] : [])];
    },
  });
  const header = (end?: ReactNode) => <PlaySubpageHeader title={playTitle("calendar")} end={end} />;
  if (!calendar || !schedule || !account) {
    return (
      <PlayShell header={header()}>
        <p className="text-body text-muted-foreground">{copy.play.loading}</p>
      </PlayShell>
    );
  }
  const { today, data, shown } = calendar;
  const userId = account.id;
  const mode: CalendarMode = !schedule.enabled ? "month" : kept?.userId === userId ? kept.mode : calendarMode(userId);
  const end = schedule.enabled ? (
    <ModeToggle
      mode={mode}
      onChange={(next) => {
        keepCalendarMode(userId, next);
        setKept({ userId, mode: next });
      }}
    />
  ) : undefined;
  const byId = new Map((characters ?? []).map((character) => [character.id, character]));
  const her = schedule.enabled && who !== null && who !== dropped ? byId.get(who) : undefined;
  const herId = her?.id ?? null;
  const failures = (
    <>
      {scheduleFailure && <FailureNotice failure={scheduleFailure} />}
      {pastFailure && <FailureNotice failure={pastFailure} />}
      {failure && <FailureNotice failure={failure} />}
      {her && (
        <HerStrip
          character={her}
          text={t.onlyHer(her.name)}
          closeLabel={t.showAll}
          onClose={() => {
            setDropped(her.id);
            router.replace(playHref("calendar"), { scroll: false });
          }}
        />
      )}
    </>
  );

  if (mode === "week" && schedule.enabled && scheduleNow) {
    const page = weekPage(chosenWeek, schedule, past);
    const weekId = page.id;
    const board: Board | null = page.week ? { week: page.week, drafts: draftsOn(weekId), now: scheduleNow } : null;
    const nav: WeekNav = {
      title: page.title,
      hasPrevious: page.hasPrevious,
      hasNext: page.hasNext,
      onPrevious: () => setChosenWeek(page.previous),
      onNext: () => setChosenWeek(page.next),
      onThisWeek: page.hasBackToThisWeek ? () => setChosenWeek(null) : null,
    };
    const characterOf: CharacterOf = (id) => byId.get(id) ?? { id, name: id, short_name: null, avatar_url: null, color: null };
    const nameOf = (id: string) => characterOf(id).name;

    const save = async (saving: Placement[], started: Placement[]) => {
      if (!board) return;
      setFailure(null);
      setNotice(null);
      if (saving.length === 0) {
        // 都已经开始了：不弹确认框，直接退回待排。
        keepDraftsOn(weekId, afterSave(board.drafts, started));
        setNotice(startedNote(board, started, nameOf));
        return;
      }
      setSaving(true);
      try {
        const { returned } = await saveSchedule(weekId, saving);
        // 先重读，存下的成了保存过的，再从草稿里去掉试过的，退回的回到待排；重读失败时草稿先不动，
        // 页上方说读不到，下次读到时存下的那几项自己从草稿里消失（lib/schedule 的 draftsOf）。
        if (await readSchedule()) keepDraftsOn(weekId, afterSave(board.drafts, [...saving, ...started]));
        setNotice(returnedNote(board, returned, nameOf));
      } catch (e) {
        if (e instanceof ApiError && e.scheduleClosed) closeSchedule();
        else setFailure(toFailure(e));
      } finally {
        setSaving(false);
      }
    };

    return (
      <PlayShell
        header={header(end)}
        footer={
          board && board.week.published && board.drafts.length > 0 ? (
            <SaveBar board={board} characterOf={characterOf} isSaving={isSaving} onSave={save} />
          ) : undefined
        }
      >
        {failures}
        {notice && <ScheduleNotice text={notice} onDismiss={() => setNotice(null)} />}
        <ScheduleWeek
          key={weekId}
          week={weekId}
          board={board}
          isPast={page.isPast}
          nav={nav}
          characterOf={characterOf}
          calendar={data}
          who={herId}
          isWide={isWide}
          onDrafts={(drafts) => keepDraftsOn(weekId, drafts)}
        />
      </PlayShell>
    );
  }

  const kinds = calendarKinds(data.producerBirthday, schedule.enabled);
  const visible = kinds.filter((kind) => shown.includes(kind));
  const day = picked ?? today;
  // 往周取过的都画上（只有保存过的，没有草稿）；月视图翻到哪儿，那一屏的往周就在里面。
  const weeks = !schedule.enabled
    ? []
    : calendarWeeks(schedule, past).map((week) => ({ week, drafts: draftsOn(week.id) }));
  const isDayRead = !schedule.enabled || !visible.includes("schedule") || !awaitsPast(day, schedule, past);
  const jobs = dayJobs(weeks, (id) => byId.get(id) ?? null, herId).flatMap(known);
  const withJobs: CalendarData<Character> = { ...data, jobs };
  const events = eventsOn(day, withJobs, visible);
  return (
    <PlayShell header={header(end)}>
      {failures}
      <Filters
        kinds={kinds}
        visible={visible}
        // 没有的那一类（制作人没生日时的「我的生日」）照原样存着。
        onChange={(next) =>
          keepShown(CALENDAR_KINDS.filter((kind) => (kinds.includes(kind) ? next.includes(kind) : shown.includes(kind))))
        }
      />
      <MonthView
        month={month ?? monthOf(today)}
        today={today}
        picked={day}
        data={withJobs}
        visible={visible}
        onMonth={setMonth}
        onPick={setPicked}
        onToday={() => {
          setMonth(null);
          setPicked(null);
        }}
      />
      {visible.length === 0 ? (
        <p className="text-body text-muted-foreground">{t.nothingShown}</p>
      ) : isDayRead && (events.length > 0 || hasHolidaysOf(partsOf(day).year)) ? (
        <DayEvents date={day} events={events} />
      ) : (
        <p className="text-body text-muted-foreground">{copy.play.loading}</p>
      )}
    </PlayShell>
  );
}

/** 页首末端的月 / 周切换：两项，图标加字，按下的中性 `bg-muted`。 */
function ModeToggle({ mode, onChange }: { mode: CalendarMode; onChange: (mode: CalendarMode) => void }) {
  return (
    <ToggleGroup
      aria-label={t.views.label}
      variant="outline"
      size="sm"
      value={[mode]}
      onValueChange={(next) => {
        const [chosen] = next;
        if (chosen === "month" || chosen === "week") onChange(chosen);
      }}
    >
      <ToggleGroupItem value="month">
        <MonthViewIcon aria-hidden />
        {t.views.month}
      </ToggleGroupItem>
      <ToggleGroupItem value="week">
        <WeekViewIcon aria-hidden />
        {t.views.week}
      </ToggleGroupItem>
    </ToggleGroup>
  );
}

/** 配置里已经没有的角色的日程不画。 */
function known(job: DayJob<Character | null>): DayJob<Character>[] {
  const { character } = job;
  return character ? [{ ...job, character }] : [];
}

/** 保存时没存下的几项：页上方一句，右边关掉。 */
function ScheduleNotice({ text, onDismiss }: { text: string; onDismiss: () => void }) {
  return (
    <Alert>
      <FailureIcon />
      <AlertTitle>{text}</AlertTitle>
      <AlertAction>
        <Button variant="ghost" size="icon-sm" aria-label={copy.common.close} onClick={onDismiss}>
          <CloseIcon />
        </Button>
      </AlertAction>
    </Alert>
  );
}

/** 月视图上出现的那几年（首尾补上的天可能落在前后一年）。 */
function yearsOn(cells: CalendarCell[]): number[] {
  return [partsOf(cells[0].date).year, partsOf(cells[cells.length - 1].date).year];
}

/** 「10月27日 周二」。 */
function dayLabel(date: string): string {
  const { month, day, weekday } = partsOf(date);
  return `${t.date(month, day)} ${t.weekdays[weekday]}`;
}

/** 月视图上方的一排筛选：每类一个按钮，按下的（中性 `bg-muted`）是开着的；制作人没生日时没有「我的生日」。 */
function Filters({
  kinds,
  visible,
  onChange,
}: {
  kinds: CalendarKind[];
  visible: CalendarKind[];
  onChange: (visible: CalendarKind[]) => void;
}) {
  return (
    <ToggleGroup
      aria-label={t.filters.label}
      multiple
      variant="outline"
      size="sm"
      className="flex-wrap"
      value={visible}
      onValueChange={(next) => onChange(kinds.filter((kind) => next.includes(kind)))}
    >
      {kinds.map((kind) => {
        const Icon = FILTER_ICONS[kind];
        return (
          <ToggleGroupItem key={kind} value={kind}>
            <Icon aria-hidden />
            {t.filters[kind]}
          </ToggleGroupItem>
        );
      })}
    </ToggleGroup>
  );
}

/**
 * 月视图：标题「2026年10月」，两边上个月、下个月，不在当月时后面一个「今天」；周一到周日七列，非当月的格子淡下去、
 * 照常显示事。今天的日期数字一个中性圆底，点中的格子铺中性 `bg-muted`。电脑（≥ 768px）上一格最多三行字，
 * 手机上一排 6px 的记号。
 */
function MonthView({
  month,
  today,
  picked,
  data,
  visible,
  onMonth,
  onPick,
  onToday,
}: {
  month: CalendarMonth;
  today: string;
  picked: string;
  data: CalendarData<Character>;
  visible: CalendarKind[];
  onMonth: (month: CalendarMonth) => void;
  onPick: (date: string) => void;
  onToday: () => void;
}) {
  const thisMonth = monthOf(today);
  const isThisMonth = month.year === thisMonth.year && month.month === thisMonth.month;
  const title = t.month(month.year, month.month);
  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center gap-1">
        <Button variant="ghost" size="icon-sm" aria-label={t.previousMonth} onClick={() => onMonth(shiftMonth(month, -1))}>
          <PreviousMonthIcon />
        </Button>
        <h2 className="min-w-28 text-center text-header tabular-nums">{title}</h2>
        <Button variant="ghost" size="icon-sm" aria-label={t.nextMonth} onClick={() => onMonth(shiftMonth(month, 1))}>
          <NextMonthIcon />
        </Button>
        {!isThisMonth && (
          <Button variant="ghost" size="sm" onClick={onToday}>
            {t.today}
          </Button>
        )}
      </div>
      <div role="group" aria-label={title} className="grid grid-cols-7 gap-px overflow-hidden rounded-lg border bg-border">
        {t.weekHeads.map((head) => (
          <span key={head} aria-hidden className="bg-background py-1 text-center text-meta text-muted-foreground">
            {head}
          </span>
        ))}
        {monthCells(month, today).map((cell) => (
          <DayCell
            key={cell.date}
            cell={cell}
            events={eventsOn(cell.date, data, visible)}
            isPicked={cell.date === picked}
            onPick={() => onPick(cell.date)}
          />
        ))}
      </div>
    </section>
  );
}

function DayCell({
  cell,
  events,
  isPicked,
  onPick,
}: {
  cell: CalendarCell;
  events: CalendarEvent<Character>[];
  isPicked: boolean;
  onPick: () => void;
}) {
  const { events: lines, more } = cellLines(events);
  return (
    <button
      type="button"
      aria-label={t.cell(dayLabel(cell.date), events.length)}
      aria-pressed={isPicked}
      aria-current={cell.isToday ? "date" : undefined}
      onClick={onPick}
      className={cn(
        "flex min-h-14 min-w-0 flex-col bg-background p-1 text-left outline-none hover:bg-muted/60 focus-visible:z-10 focus-visible:ring-3 focus-visible:ring-ring/50 md:min-h-24",
        isPicked && "bg-muted hover:bg-muted",
      )}
    >
      <span className={cn("flex min-w-0 flex-col gap-1", !cell.isInMonth && "opacity-50")}>
        <span
          className={cn(
            "flex size-6 items-center justify-center rounded-full text-subtitle tabular-nums",
            cell.isToday && "bg-foreground text-background",
          )}
        >
          {partsOf(cell.date).day}
        </span>
        <span aria-hidden className="flex gap-0.5 px-0.5 md:hidden">
          {events.slice(0, CELL_MARKS).map((event) => (
            <Mark key={eventKey(event)} event={event} />
          ))}
        </span>
        <span aria-hidden className="flex min-w-0 flex-col gap-0.5 max-md:hidden">
          {lines.map((event) => (
            <span
              key={eventKey(event)}
              style={event.kind === "schedule" ? herVars(event.job.character.color) : undefined}
              className={cn(
                "flex min-w-0 items-center gap-1 text-meta",
                event.kind === "schedule" && event.job.isSaved && "rounded-sm bg-her-wall",
              )}
            >
              <EventIcon event={event} />
              <span className="truncate">{eventText(event)}</span>
            </span>
          ))}
          {more > 0 && <span className="text-meta text-muted-foreground">{t.more(more)}</span>}
        </span>
      </span>
    </button>
  );
}

/** 手机上格子里的一个 6px 记号：角色生日和日程是她的颜色（日程保存过的实心、草稿空心），别的中性。 */
function Mark({ event }: { event: CalendarEvent<Character> }) {
  if (event.kind === "character" || event.kind === "schedule") {
    const isHollow = event.kind === "schedule" && !event.job.isSaved;
    const color = event.kind === "character" ? event.character.color : event.job.character.color;
    return <span style={herVars(color)} className={cn("size-1.5", herDot(!isHollow))} />;
  }
  return <span className="size-1.5 rounded-full bg-muted-foreground" />;
}

/** 她颜色的圆点：实心（角色生日、保存过的日程）或空心（草稿）。要在注入了她的颜色的子树里。 */
function herDot(isSolid: boolean): string {
  return cn("rounded-full", isSolid ? "bg-her-mark" : "border border-her-mark");
}

/** 16px 的图标：角色生日是她颜色的蛋糕（每一项单独注入一次她的颜色），日程是她颜色的圆点（保存过的实心、草稿空心，
 * 注入在整行上），我的生日的蛋糕和节假日的旗子不上色。 */
function EventIcon({ event }: { event: CalendarEvent<Character> }) {
  if (event.kind === "schedule") {
    return (
      <span className="flex size-4 shrink-0 items-center justify-center">
        <span className={cn("size-2", herDot(event.job.isSaved))} />
      </span>
    );
  }
  if (event.kind === "character") {
    return (
      <span style={herVars(event.character.color)} className="flex shrink-0">
        <BirthdayIcon aria-hidden className="size-4 text-her-mark" />
      </span>
    );
  }
  const Icon = event.kind === "holiday" ? HolidayIcon : BirthdayIcon;
  return <Icon aria-hidden className="size-4 shrink-0 text-muted-foreground" />;
}

function eventText(event: CalendarEvent<Character>): string {
  if (event.kind === "character") return event.character.name;
  if (event.kind === "schedule") return event.job.name;
  return event.kind === "holiday" ? event.name : t.mine;
}

/**
 * 这一天的清单：Subtitle 字号 muted 的日期（「10月27日 周二」），下面一行一件。角色生日是她 24px 的头像、显示名和
 * Meta 字号 muted 的「生日」，前面一个她颜色的蛋糕（每一项单独注入一次她的颜色）；节假日是旗子加名字，我的生日是
 * 蛋糕加「我的生日」，都不上色。什么也没有时一句 muted 的「这一天没有事」。
 */
function DayEvents({ date, events }: { date: string; events: CalendarEvent<Character>[] }) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-subtitle text-muted-foreground">{dayLabel(date)}</h2>
      {events.length === 0 ? (
        <p className="text-body text-muted-foreground">{t.noEvents}</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {events.map((event) => (
            <li key={eventKey(event)} className="flex min-w-0 items-center gap-2 text-body">
              <EventRow event={event} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function EventRow({ event }: { event: CalendarEvent<Character> }) {
  if (event.kind === "schedule") {
    const { job } = event;
    return (
      <>
        <MarkedAvatar name={job.character.name} src={job.character.avatar_url} size="sm" />
        <span className="shrink-0">{shortName(job.character)}</span>
        <span className="truncate">{job.name}</span>
        <span className="shrink-0 text-meta text-muted-foreground">
          {[job.slotsText, job.isSaved ? copy.play.schedule.states.saved : copy.play.schedule.states.draft].join(
            copy.play.separator,
          )}
        </span>
      </>
    );
  }
  if (event.kind === "character") {
    const { character } = event;
    return (
      <>
        <MarkedAvatar name={character.name} src={character.avatar_url} size="sm" />
        <span className="truncate">{character.name}</span>
        <span style={herVars(character.color)} className="flex shrink-0 items-center gap-1">
          <BirthdayIcon aria-hidden className="size-3 text-her-mark" />
          <span className="text-meta text-muted-foreground">{t.birthday}</span>
        </span>
      </>
    );
  }
  return (
    <>
      <span className="flex size-6 shrink-0 items-center justify-center">
        <EventIcon event={event} />
      </span>
      <span className="truncate">{eventText(event)}</span>
    </>
  );
}

function eventKey(event: CalendarEvent<Character>): string {
  if (event.kind === "character") return `character:${event.character.id}`;
  if (event.kind === "schedule") return `schedule:${event.job.jobId}`;
  return event.kind === "holiday" ? `holiday:${event.name}` : "producer";
}
