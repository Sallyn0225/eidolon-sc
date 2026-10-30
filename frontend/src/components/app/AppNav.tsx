"use client";

import NextLink from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type MouseEvent } from "react";

import { opensNewTab, useDirectory } from "@/components/conversations/ConversationDirectory";
import { Button } from "@/components/ui/button";
import { copy } from "@/i18n";
import { hasUnseen } from "@/lib/conversationList";
import { currentNavItem, FIRST_LEVEL, isTyping, NAV_ITEMS, navDestination, navDots, type NavItem } from "@/lib/navShell";
import { REPOSITORY_URL } from "@/lib/repository";
import { cn } from "@/lib/utils";
import { Aperture as MomentsIcon } from "lucide-react";
import { useEntry, useHasNew } from "@/components/play/moments-prototype/store";
import { ConversationsIcon, GitHubIcon, PlayIcon, SettingsIcon } from "@/theme/icons";

// PROTOTYPE：入口是导航时多一项「朋友圈」（.scratch/moments/issues/05）。
type ProtoItem = NavItem | "moments";
const MOMENTS_HREF = "/play/moments";

const ICONS: Record<ProtoItem, typeof SettingsIcon> = {
  moments: MomentsIcon,
  conversations: ConversationsIcon,
  play: PlayIcon,
  settings: SettingsIcon,
};

/** 带点时读屏读的名字。 */
const DOTTED: Partial<Record<ProtoItem, string>> = {
  moments: "朋友圈，有新动态",
  conversations: copy.nav.conversationsUnseen,
  play: copy.nav.playRewarded,
};

/**
 * 导航栏（电脑）：最左一条 72px，右边一条细线，不能收起；对话、玩法、设置从上往下，GitHub 仓库链接在最底下
 * （DESIGN.md「Layout」）。窄屏由 CSS 藏起来，换成 dock。通话层只盖住它右边，展开时它照样能点（见 NavLinks）。
 */
export function NavRail() {
  return (
    <nav
      aria-label={copy.nav.label}
      className="flex w-18 shrink-0 flex-col items-center gap-2 border-r bg-background py-3 max-md:hidden"
    >
      <NavLinks className="w-16 gap-1 rounded-lg py-1" />
      <div className="flex-1" />
      {/* 新标签页打开：通话照常（外壳的去处规则）。 */}
      <Button
        variant="ghost"
        size="icon-lg"
        aria-label={copy.app.repositoryLabel}
        nativeButton={false}
        render={<a href={REPOSITORY_URL} target="_blank" rel="noopener noreferrer" />}
      >
        <GitHubIcon />
      </Button>
    </nav>
  );
}

/**
 * dock（手机）：底部一条，项目同导航栏，实底、上沿一条细线、留出 safe-area；宽屏由 CSS 藏起来。
 * 输入框拿到焦点（键盘弹起）时藏起来，失去焦点后回来。
 */
export function NavDock({ isInert }: { isInert: boolean }) {
  const typing = useTyping();
  return (
    <nav
      aria-label={copy.nav.label}
      inert={isInert}
      className={cn(
        "grid shrink-0 auto-cols-fr grid-flow-col border-t bg-background pb-[env(safe-area-inset-bottom)] md:hidden",
        typing && "hidden",
      )}
    >
      <NavLinks className="h-14 gap-0.5" />
    </nav>
  );
}

/**
 * 导航的每一项：图标在上、字在下；当前项（按网址，外壳的去处规则）图标铺中性的 bg-muted 圆角底、字 foreground 加 medium，
 * 标 `aria-current="page"`。点别的项去那一项的第一级；在二级页面上（她的对话页）再点当前项回到第一级，已在第一级时不动。
 * 通话层展开着（只有电脑上点得到，手机上它盖住 dock）时先收起，结束卡就放下，通话照常，去处顶上是通话条。
 * 对话列表里有一行有没看过的搭话（正开着的那段对话除外）时，「对话」图标右上角一个前景色的小点，和公告铃铛上的一样；
 * 有新到的抽奖次数（lib/rewards）时「玩法」上同样一个点，在玩法页的任何一级上都不出（卡片上的点说是哪张卡）。
 */
function NavLinks({ className }: { className: string }) {
  const pathname = usePathname();
  const { guard, held, characters, latest, preferences, onScreen, newRewards } = useDirectory();
  const entry = useEntry();
  const hasNewMoments = useHasNew();
  const onMoments = entry === "nav" && pathname === MOMENTS_HREF;
  const current: ProtoItem | null = onMoments ? "moments" : currentNavItem(pathname);
  const unseen = characters !== null && hasUnseen(characters, latest, { preferences, onScreen });
  const realDots = navDots(current === "moments" ? null : current, { conversations: unseen, rewards: newRewards });
  const dots: Record<ProtoItem, boolean> = {
    ...realDots,
    play: realDots.play || (entry === "card" && hasNewMoments && current !== "play"),
    moments: hasNewMoments && current !== "moments",
  };
  const items: readonly ProtoItem[] =
    entry === "nav" ? ["conversations", "moments", "play", "settings"] : NAV_ITEMS;
  return items.map((item) => {
    const Icon = ICONS[item];
    const isCurrent = item === current;
    const onClick = (event: MouseEvent<HTMLAnchorElement>) => {
      const to = item === "moments" ? (onMoments ? null : MOMENTS_HREF) : navDestination(item, pathname);
      if (to === null) event.preventDefault();
      else guard(to)(event);
      if (!opensNewTab(event) && held?.snapshot().layer?.collapsed === false) {
        held.collapse();
        held.dismissEnd();
      }
    };
    return (
      <NextLink
        key={item}
        href={item === "moments" ? MOMENTS_HREF : FIRST_LEVEL[item]}
        onClick={onClick}
        aria-current={isCurrent ? "page" : undefined}
        aria-label={dots[item] ? DOTTED[item] : undefined}
        className={cn(
          "group flex flex-col items-center justify-center text-meta outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
          className,
        )}
      >
        <span
          className={cn(
            "relative flex h-8 w-12 items-center justify-center rounded-full transition-colors",
            isCurrent ? "bg-muted text-foreground" : "text-muted-foreground group-hover:bg-muted/60",
          )}
        >
          <Icon aria-hidden className="size-5" />
          {dots[item] && (
            <span aria-hidden className="absolute top-1 right-2.5 size-1.5 rounded-full bg-foreground" />
          )}
        </span>
        <span className={isCurrent ? "font-medium text-foreground" : "text-muted-foreground"}>{item === "moments" ? "朋友圈" : copy.nav[item]}</span>
      </NextLink>
    );
  });
}

/** 手机上在打字（焦点在输入框里），大致就是键盘弹起来了。失去焦点那一刻焦点还没落下，等它落下再看。 */
function useTyping(): boolean {
  const [typing, setTyping] = useState(false);
  useEffect(() => {
    let settling: ReturnType<typeof setTimeout> | undefined;
    const check = () => setTyping(isTyping(document.activeElement as HTMLInputElement | null));
    const checkOnceSettled = () => {
      clearTimeout(settling);
      settling = setTimeout(check, 0);
    };
    document.addEventListener("focusin", check);
    document.addEventListener("focusout", checkOnceSettled);
    return () => {
      clearTimeout(settling);
      document.removeEventListener("focusin", check);
      document.removeEventListener("focusout", checkOnceSettled);
    };
  }, []);
  return typing;
}
