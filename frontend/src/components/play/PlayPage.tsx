"use client";

import { FailureNotice } from "@/components/app/FailureNotice";
import { useDirectory } from "@/components/conversations/ConversationDirectory";
import { PlayCardLink } from "@/components/play/PlayCardLink";
import { PlayHeader, PlayShell } from "@/components/play/PlayShell";
import { useBar } from "@/components/play/useBar";
import { useCalendar } from "@/components/play/useCalendar";
import { useCycles } from "@/components/play/useCycles";
import { usePlayState } from "@/components/play/usePlayState";
import { useEntry, useHasNew } from "@/components/play/moments-prototype/store";
import { achievementsSeenUpTo, OF_ALL } from "@/lib/achievements";
import { partsOf } from "@/lib/calendar";
import { playCards } from "@/lib/playCards";
import { pendingJobs, shortName } from "@/lib/schedule";

/** 「日历」卡要的节假日：今年和明年。 */
function calendarYears(today: string): number[] {
  const { year } = partsOf(today);
  return [year, year + 1];
}

/**
 * 玩法页第一级（`/play`，DESIGN.md「玩法页」）：页首「玩法」大标题，下面一张张入口卡；第一张（礼物）铺满一行，其余两列网格、窄屏一列。
 * 读到状态之前卡片就在、状态那一行先空着；读到好感度和礼物没开放时只剩「日历」卡。
 * 「日历」卡要角色、制作人档案和今年、明年的节假日（跨年时找得到明年的），都读到之前状态空着；日程开着时前面加本周还有几项待排。
 * 「周期」卡要周期和角色（短名），开关都开着、两样都读到了才出现，读不到时也不出现。
 * 「VA-283」卡要 `GET /api/bar`，读到开着才出现，读不到时也不出现。
 * 卡的内容（名字、去哪、状态、点）由 `lib/playCards` 管，这里只管顺序和版式。
 * 只进这一级不算看过：「礼物」卡上的点留着，进了礼物子页才没有；「成就」卡上的点留到离开那个子页。
 */
export function PlayPage() {
  const { account, newRewards, characters } = useDirectory();
  const { state, failure } = usePlayState({ withCatalog: false });
  const achievementsSeenAt = account && state ? achievementsSeenUpTo(account.id, OF_ALL) : null;
  const { calendar, holidaysRead, schedule, scheduleNow, draftsOn } = useCalendar({ years: calendarYears });
  // 本周还没排的工作，草稿算排了（同日历子页的待排）；没发布的一周没有工作。
  const thisWeek = schedule?.enabled ? schedule.this_week : null;
  const schedulePending =
    thisWeek && scheduleNow ? pendingJobs({ week: thisWeek, drafts: draftsOn(thisWeek.id), now: scheduleNow }).length : 0;
  const { view: cycles } = useCycles();
  const { bar } = useBar();
  // PROTOTYPE：朋友圈的卡（入口是玩法卡时），排在网格第一张。
  const entry = useEntry();
  const hasNewMoments = useHasNew();
  const byId = new Map((characters ?? []).map((character) => [character.id, character]));
  const [first, ...rest] = playCards({
    state,
    newRewards,
    achievementsSeenAt,
    calendar: holidaysRead ? calendar : null,
    schedulePending,
    cycles:
      cycles?.enabled && characters
        ? {
            today: cycles.today,
            hers: cycles.characters,
            nameOf: (id) => {
              const character = byId.get(id);
              return character ? shortName(character) : id;
            },
          }
        : null,
    bar: bar?.enabled ? { rewardToday: bar.reward_today } : null,
  });
  if (entry === "card") {
    rest.unshift({
      id: "moments",
      name: "朋友圈",
      href: "/play/moments",
      status: hasNewMoments ? "八宮めぐる发了新动态" : "她们最近的动态",
      hasDot: hasNewMoments,
      dotLabel: "有新动态",
    });
  }
  return (
    <PlayShell header={<PlayHeader />}>
      {failure && <FailureNotice failure={failure} />}
      <PlayCardLink card={first} isFilled />
      {rest.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2">
          {rest.map((card) => (
            <PlayCardLink key={card.id} card={card} />
          ))}
        </div>
      )}
    </PlayShell>
  );
}
