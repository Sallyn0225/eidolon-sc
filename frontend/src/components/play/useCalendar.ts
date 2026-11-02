"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useDirectory } from "@/components/conversations/ConversationDirectory";
import { ApiError, type Character, getProfile, type ProducerProfile } from "@/lib/api";
import { type CalendarKind, type CalendarView, type Holiday, todayIn } from "@/lib/calendar";
import { keepShownKinds, shownKinds } from "@/lib/calendarFilter";
import { type Failure, toFailure } from "@/lib/failure";
import { getHolidays } from "@/lib/holidays";
import {
  draftsOf,
  getPastWeeks,
  getSchedule,
  isOutdated,
  keepDrafts,
  localNow,
  type OpenSchedule,
  type Placement,
  readDrafts,
  type Schedule,
  type Week,
} from "@/lib/schedule";
import { producerTimezone } from "@/lib/timezone";

const NO_PROFILE: Pick<ProducerProfile, "timezone" | "birthday"> = { timezone: null, birthday: null };

/** 「此刻」多久走一次：已过、进行中的格子和换周跟着它变。 */
const TICK_MS = 60_000;

const NO_DRAFTS: readonly Placement[] = [];

/**
 * 玩法页第一级的「日历」卡和日历子页共用的数据（.scratch/calendar spec「数据」）：角色用外壳已经载入的那一份
 * （带生日、头像按外观换好），制作人档案读一次（生日和时区；读不到当作没生日、用浏览器的时区），节假日按年取
 * （`years` 从制作人的今天给出要哪几年；取过的留着，翻回来不再等，lib/holidays）。开着的几类读这台设备上记着的，
 * `keepShown` 改了就存下、重画。
 * 角色、档案和登录的用户都读到之前 `calendar` 是 null；`years` 里的节假日没都回来之前里面先没有它们，`holidaysRead` 为假；
 * `hasHolidaysOf` 看某一年回来了没有。
 *
 * 日程（.scratch/schedule spec「界面」）也在这里：读一次日程接口（`schedule`，读到之前是 null；读不到时当作关着，
 * `scheduleFailure` 说原因），「此刻」每分钟走一次（`scheduleNow`，按接口给的有效时区），制作人那边换了周、或者本周、
 * 下周的工作发布了就重读。草稿只存在这台设备上（lib/schedule）：`draftsOn(周号)` 是那一周还算数的草稿，
 * `keepDraftsOn` 存下、重画；`readSchedule` 重读（保存以后；读到了是 true），`closeSchedule` 在保存时收到「日程没开放」后切成关着。
 * 往周（`past`，周号 → 那一周）按 `pastWeeks` 要的取：一组一次请求（每组不超过 6 周），取过的留着（往周不会再变），
 * 取不到时 `pastFailure` 说原因（再要的时候重取，同时收起这句），日程关了就切成关着。
 */
export function useCalendar({
  years,
  pastWeeks,
}: {
  years: (today: string) => readonly number[];
  /** 读到的日程开着时要哪几组往周（周号）。 */
  pastWeeks?: (read: OpenSchedule, today: string) => readonly (readonly string[])[];
}) {
  const { account, characters } = useDirectory();
  const [profile, setProfile] = useState<Pick<ProducerProfile, "timezone" | "birthday"> | null>(null);
  const [holidays, setHolidays] = useState<ReadonlyMap<number, Holiday[]>>(new Map());
  const [kept, setKept] = useState<{ userId: string; kinds: CalendarKind[] } | null>(null);

  useEffect(() => {
    let current = true;
    getProfile().then(
      (p) => current && setProfile(p),
      () => current && setProfile(NO_PROFILE),
    );
    return () => {
      current = false;
    };
  }, []);

  const today = profile ? todayIn(producerTimezone(profile.timezone), new Date()) : null;
  const wanted = today ? [...new Set(years(today))] : [];
  const wantedKey = wanted.join(",");

  useEffect(() => {
    if (!wantedKey) return;
    let current = true;
    for (const year of wantedKey.split(",").map(Number)) {
      // 取不到的那一年当作没有节假日，生日照画。
      getHolidays(year).then(
        (list) => current && setHolidays((read) => new Map(read).set(year, list)),
        () => current && setHolidays((read) => new Map(read).set(year, [])),
      );
    }
    return () => {
      current = false;
    };
  }, [wantedKey]);

  const userId = account?.id;
  const keepShown = useCallback(
    (kinds: readonly CalendarKind[]) => {
      if (!userId) return;
      keepShownKinds(userId, kinds);
      setKept({ userId, kinds: shownKinds(userId) });
    },
    [userId],
  );

  const [schedule, setSchedule] = useState<Schedule | null>(null);
  const [scheduleFailure, setScheduleFailure] = useState<Failure | null>(null);
  const [clock, setClock] = useState(() => new Date());
  // 草稿存进本机以后加一，重新从本机读。
  const [draftsKept, setDraftsKept] = useState(0);

  const readSchedule = useCallback(
    (): Promise<boolean> =>
      getSchedule().then(
        (read) => {
          setSchedule(read);
          setScheduleFailure(null);
          return true;
        },
        (e) => {
          // 读到过的留着；一次也没读到时当作关着，只有月视图。
          setSchedule((read) => read ?? { enabled: false });
          setScheduleFailure(toFailure(e));
          return false;
        },
      ),
    [],
  );
  const closeSchedule = useCallback(() => setSchedule({ enabled: false }), []);

  useEffect(() => {
    readSchedule();
    const timer = setInterval(() => setClock(new Date()), TICK_MS);
    return () => clearInterval(timer);
  }, [readSchedule]);

  // 过时了就重读；每走一次只试一次，服务器的钟和这里差一点时不会一直重读。
  const triedAt = useRef<Date | null>(null);
  useEffect(() => {
    if (!schedule?.enabled || triedAt.current === clock || !isOutdated(schedule, clock)) return;
    triedAt.current = clock;
    readSchedule();
  }, [schedule, clock, readSchedule]);

  const [past, setPast] = useState<ReadonlyMap<string, Week>>(new Map());
  const [pastFailure, setPastFailure] = useState<Failure | null>(null);
  // 取过和正在取的周，免得重复请求（后端没给的那几周也不再要）；取不到的放回去，下次要时再试。
  const asked = useRef(new Set<string>());
  const pastKey = schedule?.enabled && pastWeeks && today ? JSON.stringify(pastWeeks(schedule, today)) : "[]";
  useEffect(() => {
    const groups: string[][] = JSON.parse(pastKey);
    for (const group of groups) {
      const missing = group.filter((week) => !asked.current.has(week));
      if (missing.length === 0) continue;
      for (const week of missing) asked.current.add(week);
      setPastFailure(null);
      getPastWeeks(missing[0], missing[missing.length - 1]).then(
        (weeks) => {
          setPast((read) => new Map([...read, ...weeks.map((week) => [week.id, week] as const)]));
        },
        (e) => {
          for (const week of missing) asked.current.delete(week);
          if (e instanceof ApiError && e.scheduleClosed) setSchedule({ enabled: false });
          else setPastFailure(toFailure(e));
        },
      );
    }
  }, [pastKey]);

  const scheduleNow = schedule?.enabled ? localNow(schedule.timezone, clock) : null;
  const drafts = useMemo(() => {
    if (!schedule?.enabled || !userId) return new Map<string, Placement[]>();
    const weeks = schedule.next_week ? [schedule.this_week, schedule.next_week] : [schedule.this_week];
    const stored = readDrafts(userId, weeks.map((week) => week.id));
    return new Map(weeks.map((week) => [week.id, draftsOf(week, stored.get(week.id) ?? [])]));
    // draftsKept 不在里面用到：存下以后靠它重新从本机读。
  }, [schedule, userId, draftsKept]);
  const draftsOn = useCallback((week: string) => drafts.get(week) ?? NO_DRAFTS, [drafts]);
  const keepDraftsOn = useCallback(
    (week: string, placements: readonly Placement[]) => {
      if (!userId) return;
      keepDrafts(userId, week, placements);
      setDraftsKept((n) => n + 1);
    },
    [userId],
  );

  const calendar: CalendarView<Character> | null =
    today && profile && characters && account
      ? {
          today,
          data: {
            characters,
            producerBirthday: profile.birthday,
            holidays: [...holidays.keys()].sort().flatMap((year) => holidays.get(year) ?? []),
          },
          shown: kept?.userId === account.id ? kept.kinds : shownKinds(account.id),
        }
      : null;
  const holidaysRead = wanted.length > 0 && wanted.every((year) => holidays.has(year));
  const hasHolidaysOf = (year: number) => holidays.has(year);
  return {
    calendar,
    holidaysRead,
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
  };
}
