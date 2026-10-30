"use client";

import NextLink from "next/link";

import { useDirectory } from "@/components/conversations/ConversationDirectory";
import type { PlayCard } from "@/lib/playCards";
import type { PlaySubpage } from "@/lib/playRoute";
import { cn } from "@/lib/utils";
import { Aperture as MomentsIcon } from "lucide-react";

import { AchievementsIcon, BarCardIcon, CalendarIcon, CyclesCardIcon, ForwardIcon, GiftIcon } from "@/theme/icons";

/** 每张卡的图标：加一张卡就在这里加一行。 */
const ICONS: Record<PlaySubpage, typeof GiftIcon> = {
  gifts: GiftIcon,
  achievements: AchievementsIcon,
  calendar: CalendarIcon,
  cycles: CyclesCardIcon,
  bar: BarCardIcon,
  moments: MomentsIcon, // PROTOTYPE
};

/**
 * 玩法页第一级的一张卡（DESIGN.md「玩法页」）：整张是一个链接，最矮 44px；左边圆底图标，名字（Header 字号）旁在有新东西时一个 6px 的点，
 * 名字下面一行 muted 的状态（读到之前留空，高度先占着），右端 muted 的 ›。`isFilled`：铺 `bg-muted`、不描边（第一张），
 * 其余描边。点进去按外壳的去处规则走。
 */
export function PlayCardLink({ card, isFilled = false }: { card: PlayCard; isFilled?: boolean }) {
  const { guard } = useDirectory();
  const Icon = ICONS[card.id];
  return (
    <NextLink
      href={card.href}
      onClick={guard(card.href)}
      className={cn(
        "flex min-h-11 items-center gap-3 rounded-2xl p-4 outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
        isFilled ? "bg-muted hover:bg-muted/70" : "border hover:bg-muted/60",
      )}
    >
      <span
        className={cn(
          "flex size-10 shrink-0 items-center justify-center rounded-full",
          isFilled ? "bg-background" : "bg-muted",
        )}
      >
        <Icon aria-hidden className="size-5" />
      </span>
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="flex items-center gap-2 text-header">
          {card.name}
          {card.hasDot && (
            <span role="img" aria-label={card.dotLabel} className="size-1.5 shrink-0 rounded-full bg-foreground" />
          )}
        </span>
        <span className="min-h-lh text-subtitle text-muted-foreground">{card.status}</span>
      </span>
      <ForwardIcon aria-hidden className="size-5 shrink-0 text-muted-foreground" />
    </NextLink>
  );
}
