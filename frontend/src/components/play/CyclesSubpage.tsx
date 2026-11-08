"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { FailureNotice } from "@/components/app/FailureNotice";
import { MarkedAvatar } from "@/components/app/MarkedAvatar";
import { useDirectory, useWide } from "@/components/conversations/ConversationDirectory";
import { CycleGuide, guideAnchor } from "@/components/play/CycleGuide";
import { PlayShell, PlaySubpageHeader } from "@/components/play/PlayShell";
import { useCycles } from "@/components/play/useCycles";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle } from "@/components/ui/drawer";
import { Popover, PopoverContent, PopoverHeader, PopoverTitle, PopoverTrigger } from "@/components/ui/popover";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { copy } from "@/i18n";
import type { Character } from "@/lib/api";
import { type CalendarMonth, monthCells, monthOf, partsOf, shiftMonth } from "@/lib/calendar";
import { IRREGULAR_BLOCK_ID } from "@/lib/cycleGuide";
import {
  addCycleRecord,
  canShowNextMonth,
  changeCycleRecord,
  clampDays,
  CYCLE_FILTERS,
  type CycleDayKind,
  type CycleEstimate,
  type CycleFilter,
  type CycleRecord,
  cyclesWho,
  dayBar,
  defaultDays,
  deleteCycleRecord,
  FEWEST_DAYS,
  filterCounts,
  fullDate,
  type Her,
  herLine,
  isCyclesOff,
  isPickable,
  MOST_DAYS,
  monthDay,
  monthMarks,
  shownRecords,
  stripOf,
  withHer,
} from "@/lib/cycles";
import { toFailure } from "@/lib/failure";
import { playTitle } from "@/lib/playCards";
import { closedPlayRedirect, playHref } from "@/lib/playRoute";
import { shortName } from "@/lib/schedule";
import { cn } from "@/lib/utils";
import { herVars } from "@/theme/herVars";
import {
  EditRecordIcon,
  FewerDaysIcon,
  FilterIcon,
  MoreDaysIcon,
  NextMonthIcon,
  PreviousMonthIcon,
  SearchIcon,
  TrashIcon,
} from "@/theme/icons";

const t = copy.play.cycles;
const tc = copy.play.calendar;

/** 正在记、改的那一次：`record` 是改的那条（记新的时为 null）。 */
type Editing = { record: CycleRecord | null; firstDay: string; days: number };

/**
 * 「周期」子页（`/play/cycles`，DESIGN.md「玩法页 · 周期子页」，.scratch/cycle-page spec「周期子页（版式 D）」）：
 * 从上到下一行说明、搜索框加筛选、头像条，然后是选中的她的一块（电脑上左栏一句话、月历、图例、
 * 点中那一天的一条，右栏 15rem 放三个数字、变淡的原因和记过的经期，高度跟着左栏；手机上叠成一栏），
 * 最下面通栏的讲解七块，最后一行免责。
 * 她的颜色只注入月历、图例（记号）和弹窗（primary），其余中性。地址带着 `?who=`，换人时替换历史；没带或不认识时选名单第一位。两个开关任一关着时回到玩法页。
 */
export function CyclesSubpage({ who }: { who: string | null }) {
  const router = useRouter();
  const { characters } = useDirectory();
  const { view, setView, failure } = useCycles();
  const [chosen, setChosen] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<CycleFilter>("all");
  const [month, setMonth] = useState<CalendarMonth | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  const [editing, setEditing] = useState<Editing | null>(null);
  const [isDialogOpen, setDialogOpen] = useState(false);
  const [dialogKey, setDialogKey] = useState(0);
  const [guideOpen, setGuideOpen] = useState<string | null>(null);

  const redirect = view ? closedPlayRedirect("cycles", { cyclesOn: view.enabled }) : null;
  useEffect(() => {
    if (redirect) router.replace(redirect);
  }, [redirect, router]);

  const header = <PlaySubpageHeader title={playTitle("cycles")} />;
  if (failure) {
    return (
      <PlayShell header={header}>
        <FailureNotice failure={failure} />
      </PlayShell>
    );
  }
  if (!view?.enabled || !characters) {
    return (
      <PlayShell header={header}>
        <p className="text-body text-muted-foreground">{copy.play.loading}</p>
      </PlayShell>
    );
  }

  const { today } = view;
  const hers = view.characters;
  const herId = cyclesWho(chosen ?? who, characters.map((c) => c.id));
  const character = characters.find((c) => c.id === herId);
  if (!character) return <PlayShell header={header}>{null}</PlayShell>;
  const her: Her = hers.find((h) => h.character_id === character.id) ?? {
    character_id: character.id,
    records: [],
    estimate: null,
  };

  const pick = (id: string) => {
    if (id === character.id) return;
    setChosen(id);
    setPicked(null);
    setMonth(null);
    router.replace(`${playHref("cycles")}?who=${encodeURIComponent(id)}`, { scroll: false });
  };
  const open = (next: Editing) => {
    setEditing(next);
    setDialogKey((k) => k + 1);
    setDialogOpen(true);
  };
  const openNew = (firstDay: string) => open({ record: null, firstDay, days: defaultDays(her.estimate) });
  const openEdit = (record: CycleRecord) => open({ record, firstDay: record.first_day, days: record.days });
  /** 「长短不一」那句的链接：展开讲解的「青春期」，等它渲染出来再滚过去。 */
  const showIrregular = () => {
    setGuideOpen(IRREGULAR_BLOCK_ID);
    requestAnimationFrame(() =>
      document.getElementById(guideAnchor(IRREGULAR_BLOCK_ID))?.scrollIntoView({ behavior: "smooth", block: "start" }),
    );
  };

  return (
    <PlayShell
      header={header}
      overlays={
        <Dialog open={isDialogOpen} onOpenChange={setDialogOpen}>
          {editing && (
            <RecordForm
              key={dialogKey}
              character={character}
              editing={editing}
              today={today}
              onDone={(next) => {
                setView(withHer(view, next));
                setDialogOpen(false);
              }}
              onOff={() => {
                setDialogOpen(false);
                setView({ enabled: false });
              }}
              onCancel={() => setDialogOpen(false)}
            />
          )}
        </Dialog>
      }
    >
      <p className="text-body text-muted-foreground">{t.lead}</p>
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-1">
          <label className="flex h-9 min-w-0 flex-1 items-center gap-2 rounded-lg bg-muted px-3 text-muted-foreground has-focus-visible:ring-3 has-focus-visible:ring-ring/50">
            <SearchIcon aria-hidden className="size-4 shrink-0" />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={copy.conversationList.search}
              aria-label={copy.conversationList.search}
              className="min-w-0 flex-1 bg-transparent text-body text-foreground outline-none placeholder:text-muted-foreground pointer-coarse:text-base"
            />
          </label>
          <ShownFilter filter={filter} counts={filterCounts(hers)} onChange={setFilter} />
        </div>
        <AvatarStrip
          characters={stripOf(characters, hers, { filter, query, picked: character.id })}
          picked={character.id}
          noMatch={query.trim() !== "" && stripOf(characters, hers, { filter, query, picked: null }).length === 0}
          onPick={pick}
        />
      </div>
      <div className="grid items-start gap-6 md:grid-cols-[1fr_15rem]">
        <div className="flex flex-col gap-3">
          <p className="text-body">{herLine(her, today)}</p>
          <MonthGrid
            color={character.color}
            her={her}
            today={today}
            month={month ?? monthOf(today)}
            picked={picked}
            onMonth={setMonth}
            onPick={setPicked}
          />
          <Legend color={character.color} />
          <DayLine her={her} date={picked} today={today} onFirst={openNew} onEdit={openEdit} />
        </div>
        {/* 电脑上右栏不比左栏高：高度跟着左栏，记录展开后在栏里滚。 */}
        <div className="md:relative md:self-stretch">
          <div className="flex flex-col gap-4 md:absolute md:inset-0">
            <Stats estimate={her.estimate} />
            <FadeNotes estimate={her.estimate} onIrregular={showIrregular} />
            <Records key={character.id} records={her.records} onEdit={openEdit} />
          </div>
        </div>
      </div>
      <CycleGuide open={guideOpen} onOpenChange={setGuideOpen} />
      <p className="text-meta text-muted-foreground">{t.disclaimer}</p>
    </PlayShell>
  );
}

/** 搜索框右边的筛选键（同对话列表：36px ghost 图标键，电脑 Popover、手机 Drawer）：单选四类，每类后面几位；
 * 不是「全部」时右上角一个中性小点。只记在这次页面里。 */
function ShownFilter({
  filter,
  counts,
  onChange,
}: {
  filter: CycleFilter;
  counts: Record<CycleFilter, number>;
  onChange: (filter: CycleFilter) => void;
}) {
  const isWide = useWide();
  const [isOpen, setOpen] = useState(false);
  const label = filter === "all" ? t.filter.label : t.filter.only(t.filter[filter]);
  const button = { variant: "ghost", size: "icon-lg", "aria-label": label, className: "relative" } as const;
  const icon = (
    <>
      <FilterIcon />
      {filter !== "all" && (
        <span aria-hidden className="absolute top-1.5 right-1.5 size-1.5 rounded-full bg-muted-foreground" />
      )}
    </>
  );
  const choices = (
    <RadioGroup
      value={filter}
      onValueChange={(value) => {
        const next = CYCLE_FILTERS.find((f) => f === value);
        if (next) onChange(next);
        setOpen(false);
      }}
      className="gap-1"
    >
      {CYCLE_FILTERS.map((f) => (
        <label key={f} className="flex min-h-10 items-center gap-3 rounded-lg px-2 text-body hover:bg-muted/60">
          <RadioGroupItem value={f} />
          <span className="flex-1">{t.filter[f]}</span>
          <span className="text-meta text-muted-foreground tabular-nums">{t.filter.count(counts[f])}</span>
        </label>
      ))}
    </RadioGroup>
  );
  if (isWide) {
    return (
      <Popover open={isOpen} onOpenChange={setOpen}>
        <PopoverTrigger render={<Button {...button} />}>{icon}</PopoverTrigger>
        <PopoverContent align="end">
          <PopoverHeader>
            <PopoverTitle>{t.filter.title}</PopoverTitle>
          </PopoverHeader>
          {choices}
        </PopoverContent>
      </Popover>
    );
  }
  return (
    <>
      <Button {...button} onClick={() => setOpen(true)}>
        {icon}
      </Button>
      <Drawer open={isOpen} onOpenChange={setOpen} showSwipeHandle>
        <DrawerContent>
          <DrawerHeader>
            <DrawerTitle>{t.filter.title}</DrawerTitle>
          </DrawerHeader>
          <div className="px-4 pb-6">{choices}</div>
        </DrawerContent>
      </Drawer>
    </>
  );
}

/** 一排可横滑的头像条：48px 头像加短名，选中的铺中性 `bg-muted`。 */
function AvatarStrip({
  characters,
  picked,
  noMatch,
  onPick,
}: {
  characters: Character[];
  picked: string;
  noMatch: boolean;
  onPick: (id: string) => void;
}) {
  return (
    <div className="-mx-4 flex gap-1 overflow-x-auto px-4 pb-1">
      {characters.map((c) => (
        <button
          key={c.id}
          type="button"
          aria-pressed={c.id === picked}
          aria-label={c.name}
          onClick={() => onPick(c.id)}
          className={cn(
            "flex w-16 shrink-0 flex-col items-center gap-1 rounded-xl py-2 outline-none hover:bg-muted/60 focus-visible:ring-3 focus-visible:ring-ring/50",
            c.id === picked && "bg-muted hover:bg-muted",
          )}
        >
          <MarkedAvatar name={c.name} src={c.avatar_url} />
          <span className="w-full truncate px-1 text-center text-meta">{shortName(c)}</span>
        </button>
      ))}
      {noMatch && <p className="self-center px-2 text-body text-muted-foreground">{copy.conversationList.noMatch}</p>}
    </div>
  );
}

/**
 * 她的月历：一个月一页，能翻前后月，周一在前。记下的经期整格铺 `--her-wall`、日期外一圈 2px `--her-mark`；
 * 推算的经期日期外一圈虚线 `--her-mark`；推算的经前整格铺 `bg-muted/60`，每段第一天底部写「经前」（只在电脑上）；
 * 变淡时推算的记号淡一半。今天和点中的格子照日历子页（中性）。不画排卵日、易孕期。
 */
function MonthGrid({
  color,
  her,
  today,
  month,
  picked,
  onMonth,
  onPick,
}: {
  color: string;
  her: Her;
  today: string;
  month: CalendarMonth;
  picked: string | null;
  onMonth: (month: CalendarMonth) => void;
  onPick: (date: string) => void;
}) {
  const title = tc.month(month.year, month.month);
  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center gap-1">
        <Button variant="ghost" size="icon-sm" aria-label={tc.previousMonth} onClick={() => onMonth(shiftMonth(month, -1))}>
          <PreviousMonthIcon />
        </Button>
        <h2 className="min-w-28 text-center text-header tabular-nums">{title}</h2>
        <Button variant="ghost" size="icon-sm" aria-label={tc.nextMonth} onClick={() => onMonth(shiftMonth(month, 1))}>
          <NextMonthIcon />
        </Button>
      </div>
      <div
        role="group"
        aria-label={title}
        style={herVars(color)}
        className="grid grid-cols-7 gap-px overflow-hidden rounded-lg border bg-border"
      >
        {tc.weekHeads.map((head) => (
          <span key={head} aria-hidden className="bg-background py-1 text-center text-meta text-muted-foreground">
            {head}
          </span>
        ))}
        {monthMarks(month, today, her).map(({ date, isInMonth, isToday, mark }) => {
          const isPicked = date === picked;
          return (
            <button
              key={date}
              type="button"
              aria-label={mark.kind ? `${monthDay(date)}，${t.kinds[mark.kind]}` : monthDay(date)}
              aria-pressed={isPicked}
              aria-current={isToday ? "date" : undefined}
              onClick={() => onPick(date)}
              className={cn(
                "flex min-h-12 min-w-0 flex-col items-start bg-background p-1 text-left outline-none hover:bg-muted/60 focus-visible:z-10 focus-visible:ring-3 focus-visible:ring-ring/50 md:min-h-16",
                mark.kind === "recorded" && "bg-her-wall hover:bg-her-wall",
                mark.kind === "premenstrual" && (mark.isFaded ? "bg-muted/30" : "bg-muted/60"),
                isPicked && "bg-muted hover:bg-muted",
              )}
            >
              <span
                className={cn(
                  "flex size-6 items-center justify-center rounded-full text-subtitle tabular-nums",
                  !isInMonth && "opacity-50",
                  isToday && "bg-foreground text-background",
                  mark.kind === "recorded" && "ring-2 ring-her-mark",
                  mark.kind === "estimated" &&
                    cn("outline-1 outline-dashed", mark.isFaded ? "outline-her-mark/50" : "outline-her-mark"),
                )}
              >
                {partsOf(date).day}
              </span>
              {mark.isPremenstrualStart && (
                <span className={cn("mt-auto text-meta text-muted-foreground max-md:hidden", mark.isFaded && "opacity-50")}>
                  {t.premenstrualMark}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </section>
  );
}

/** 月历下面一行图例：记下的经期、推算的经期、推算的经前。 */
function Legend({ color }: { color: string }) {
  const marks: Record<CycleDayKind, string> = {
    recorded: "rounded-full bg-her-wall ring-2 ring-her-mark",
    estimated: "rounded-full outline-1 outline-dashed outline-her-mark",
    premenstrual: "rounded-sm bg-muted ring-1 ring-border",
  };
  return (
    <ul style={herVars(color)} className="flex flex-wrap gap-x-4 gap-y-1 text-meta text-muted-foreground">
      {(Object.keys(marks) as CycleDayKind[]).map((kind) => (
        <li key={kind} className="flex items-center gap-1.5">
          <span aria-hidden className={cn("size-3", marks[kind])} />
          {t.kinds[kind]}
        </li>
      ))}
    </ul>
  );
}

/** 点中那一天的一条：日期和它是什么，右端「这天是第一天」「不能记未来」或「改这次」；没点时一句提示。 */
function DayLine({
  her,
  date,
  today,
  onFirst,
  onEdit,
}: {
  her: Her;
  date: string | null;
  today: string;
  onFirst: (date: string) => void;
  onEdit: (record: CycleRecord) => void;
}) {
  const { text, action } = dayBar(date, her, today);
  return (
    <div className="flex min-h-11 items-center gap-2 rounded-xl border px-3 py-2">
      <span className={cn("flex-1 text-body", !action && "text-muted-foreground")}>{text}</span>
      {action?.kind === "edit" && (
        <Button variant="outline" size="sm" onClick={() => onEdit(action.record)}>
          <EditRecordIcon />
          {t.day.edit}
        </Button>
      )}
      {(action?.kind === "first" || action?.kind === "future") && (
        <Button size="sm" disabled={action.kind === "future"} onClick={() => date && onFirst(date)}>
          {action.kind === "future" ? t.day.future : t.day.first}
        </Button>
      )}
    </div>
  );
}

/** 右栏的三行：周期、经期、过去的估算平均差；只记一次时周期、经期后面标粗略估计。 */
function Stats({ estimate }: { estimate: CycleEstimate | null }) {
  const rough = estimate?.reasons.includes("once") ? ` · ${t.stats.rough}` : "";
  const rows: [string, string][] = [
    [t.stats.cycle, estimate ? `${t.stats.days(estimate.cycle)}${rough}` : "—"],
    [t.stats.period, estimate ? `${t.stats.days(estimate.period)}${rough}` : "—"],
    [
      t.stats.offBy,
      !estimate ? "—" : estimate.off_by !== null ? t.stats.days(String(estimate.off_by)) : t.stats.compareLater,
    ],
  ];
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-body">
      {rows.map(([name, value]) => (
        <div key={name} className="contents">
          <dt className="text-muted-foreground">{name}</dt>
          <dd className="tabular-nums">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

/** 变淡的原因，每种一句；「长短不一」那句末尾链到讲解的「青春期」。 */
function FadeNotes({ estimate, onIrregular }: { estimate: CycleEstimate | null; onIrregular: () => void }) {
  if (!estimate || estimate.reasons.length === 0) return null;
  return (
    <ul className="flex flex-col gap-0.5 text-subtitle text-muted-foreground">
      {estimate.reasons.map((reason) => (
        <li key={reason}>
          {t.reasons[reason]}
          {reason === "irregular" && (
            <a
              href={`#${guideAnchor(IRREGULAR_BLOCK_ID)}`}
              onClick={(e) => {
                e.preventDefault();
                onIrregular();
              }}
              className="underline underline-offset-2 hover:text-foreground"
            >
              {t.reasons.irregularLink}
            </a>
          )}
        </li>
      ))}
    </ul>
  );
}

/** 记过的经期：新的在上，每行第一天、「5 天 · 隔 29 天」和右端的铅笔；只露最近 3 次，下面「展开全部 n 次 / 收起」。 */
function Records({ records, onEdit }: { records: CycleRecord[]; onEdit: (record: CycleRecord) => void }) {
  const [isExpanded, setExpanded] = useState(false);
  if (records.length === 0) return null;
  const { rows, toggle } = shownRecords(records, isExpanded);
  return (
    <section className="flex min-h-0 flex-col gap-1 md:flex-1">
      <h2 className="pb-1 text-header">{t.records.title}</h2>
      <ul className="flex min-h-0 flex-col gap-1 overflow-y-auto">
        {rows.map(({ record, text }) => (
          <li key={record.id} className="flex min-h-11 items-center gap-3 px-1">
            <span className="w-16 shrink-0 text-body tabular-nums">{monthDay(record.first_day)}</span>
            <span className="flex-1 text-subtitle text-muted-foreground tabular-nums">{text}</span>
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={t.records.edit(monthDay(record.first_day))}
              onClick={() => onEdit(record)}
            >
              <EditRecordIcon />
            </Button>
          </li>
        ))}
      </ul>
      {toggle && (
        <Button variant="ghost" size="sm" className="self-start" onClick={() => setExpanded(!isExpanded)}>
          {toggle}
        </Button>
      )}
    </section>
  );
}

/**
 * 记一次、改一次的弹窗内容：第一天是写着「2026年10月25日 周日」的 outline 按钮，点开小月历（今天以后不能选）；
 * 天数 −/+ 夹着「n 天」，1–10。primary 用她的颜色；改的时候左下多一个「删除这次」，不二次确认。
 * 服务器退回时在弹窗里写一句原因；写的时候服务器说周期关着时 `onOff`。
 */
function RecordForm({
  character,
  editing,
  today,
  onDone,
  onOff,
  onCancel,
}: {
  character: Character;
  editing: Editing;
  today: string;
  onDone: (her: Her) => void;
  onOff: () => void;
  onCancel: () => void;
}) {
  const [firstDay, setFirstDay] = useState(editing.firstDay);
  const [days, setDays] = useState(editing.days);
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setBusy] = useState(false);
  const { record } = editing;

  const send = async (writing: () => Promise<Her>) => {
    setBusy(true);
    setError(null);
    try {
      onDone(await writing());
    } catch (e) {
      if (isCyclesOff(e)) onOff();
      else setError(toFailure(e).message);
    } finally {
      setBusy(false);
    }
  };
  const input = { first_day: firstDay, days };

  return (
    <DialogContent style={herVars(character.color)}>
      <DialogHeader>
        <DialogTitle>{t.dialog.title(character.name)}</DialogTitle>
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
      </DialogHeader>
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <span className="text-sm font-medium">{t.dialog.firstDay}</span>
          <DayPicker value={firstDay} today={today} onChange={setFirstDay} />
        </div>
        <div className="flex flex-col gap-1.5">
          <span className="text-sm font-medium">{t.dialog.days}</span>
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="icon-lg"
              aria-label={t.dialog.fewer}
              disabled={days <= FEWEST_DAYS}
              onClick={() => setDays(clampDays(days - 1))}
            >
              <FewerDaysIcon />
            </Button>
            <span className="min-w-12 text-center text-header tabular-nums">{t.stats.days(days)}</span>
            <Button
              variant="outline"
              size="icon-lg"
              aria-label={t.dialog.more}
              disabled={days >= MOST_DAYS}
              onClick={() => setDays(clampDays(days + 1))}
            >
              <MoreDaysIcon />
            </Button>
          </div>
        </div>
      </div>
      <DialogFooter>
        {record && (
          <Button
            variant="ghost-destructive"
            className="sm:mr-auto"
            disabled={isBusy}
            onClick={() => send(() => deleteCycleRecord(record.id))}
          >
            <TrashIcon />
            {t.dialog.delete}
          </Button>
        )}
        <Button variant="outline" onClick={onCancel}>
          {t.dialog.cancel}
        </Button>
        <Button
          disabled={isBusy}
          onClick={() =>
            send(() => (record ? changeCycleRecord(record.id, input) : addCycleRecord(character.id, input)))
          }
        >
          {record ? t.dialog.save : t.dialog.add}
        </Button>
      </DialogFooter>
    </DialogContent>
  );
}

/** 第一天：outline 按钮写着日期，点开小月历（周一在前），今天以后不能选，选中的铺中性 `bg-muted`。不用原生日期框。 */
function DayPicker({ value, today, onChange }: { value: string; today: string; onChange: (date: string) => void }) {
  const [isOpen, setOpen] = useState(false);
  const [month, setMonth] = useState<CalendarMonth>(monthOf(value));
  const title = tc.month(month.year, month.month);
  return (
    <Popover
      open={isOpen}
      onOpenChange={(next) => {
        if (next) setMonth(monthOf(value));
        setOpen(next);
      }}
    >
      <PopoverTrigger render={<Button variant="outline" size="lg" className="justify-start tabular-nums" />}>
        {fullDate(value)}
      </PopoverTrigger>
      <PopoverContent align="start" className="w-72">
        <div className="flex items-center justify-between">
          <Button variant="ghost" size="icon-sm" aria-label={tc.previousMonth} onClick={() => setMonth(shiftMonth(month, -1))}>
            <PreviousMonthIcon />
          </Button>
          <span className="text-sm font-medium tabular-nums">{title}</span>
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label={tc.nextMonth}
            disabled={!canShowNextMonth(month, today)}
            onClick={() => setMonth(shiftMonth(month, 1))}
          >
            <NextMonthIcon />
          </Button>
        </div>
        <div role="group" aria-label={title} className="grid grid-cols-7 gap-0.5">
          {tc.weekHeads.map((head) => (
            <span key={head} aria-hidden className="py-1 text-center text-meta text-muted-foreground">
              {head}
            </span>
          ))}
          {monthCells(month, today).map((cell) => (
            <button
              key={cell.date}
              type="button"
              disabled={!isPickable(cell.date, today)}
              aria-pressed={cell.date === value}
              aria-label={fullDate(cell.date)}
              onClick={() => {
                onChange(cell.date);
                setOpen(false);
              }}
              className={cn(
                "flex size-9 items-center justify-center rounded-full text-sm tabular-nums outline-none hover:bg-muted/60 focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-30",
                !cell.isInMonth && "text-muted-foreground",
                cell.isToday && "ring-1 ring-foreground",
                cell.date === value && "bg-muted font-medium hover:bg-muted",
              )}
            >
              {partsOf(cell.date).day}
            </button>
          ))}
        </div>
      </PopoverContent>
    </Popover>
  );
}
