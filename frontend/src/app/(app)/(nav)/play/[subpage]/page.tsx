import type { ReactNode } from "react";

import { AchievementsSubpage } from "@/components/play/AchievementsSubpage";
import { CalendarSubpage } from "@/components/play/CalendarSubpage";
import { LettersWallB } from "@/components/letter/prototype/LettersWallB";
import { CyclesSubpage } from "@/components/play/CyclesSubpage";
import { GiftsSubpage } from "@/components/play/GiftsSubpage";
import { giftsFor } from "@/lib/gifts";
import { PLAY_SUBPAGES, type PlaySubpage } from "@/lib/playRoute";
import { calendarWho } from "@/lib/schedule";

type SearchParams = { [key: string]: string | string[] | undefined };

/** 这个路由画的子页：酒吧有自己的路由（`play/bar`），代码和字体只在那一页加载。 */
type SharedSubpage = Exclude<PlaySubpage, "bar">;

// 只有这几个子页；不认识的 `/play/<xxx>` 在 proxy 里就换成了 `/play`，到不了这里。
export const dynamicParams = false;

export function generateStaticParams() {
  return PLAY_SUBPAGES.filter((subpage) => subpage !== "bar").map((subpage) => ({ subpage }));
}

/**
 * 玩法的子页（`/play/<子页>`）：礼物在 `/play/gifts`，从对话页跳来时地址里带着预选的她；
 * 成就在 `/play/achievements`（旧的 `/play/tasks` 在 proxy 里跳过来），日历在 `/play/calendar`，
 * 周期在 `/play/cycles`（地址带 `?who=` 选中的她）。
 * 页首返回键回玩法页（DESIGN.md「玩法页」）。
 */
export default async function PlaySubpageRoute({
  params,
  searchParams,
}: {
  params: Promise<{ subpage: string }>;
  searchParams: Promise<SearchParams>;
}) {
  const { subpage } = (await params) as { subpage: SharedSubpage };
  return SUBPAGES[subpage](await searchParams);
}

/** 每个子页画什么：加一张卡就在这里加一行。 */
const SUBPAGES: Record<SharedSubpage, (search: SearchParams) => ReactNode> = {
  gifts: (search) => <GiftsSubpage pick={giftsFor(search)} />,
  achievements: () => <AchievementsSubpage />,
  calendar: (search) => <CalendarSubpage who={calendarWho(search)} />,
  cycles: (search) => <CyclesSubpage who={calendarWho(search)} />,
  letters: () => <LettersWallB />, // PROTOTYPE（prototype/letters-ui）
};
