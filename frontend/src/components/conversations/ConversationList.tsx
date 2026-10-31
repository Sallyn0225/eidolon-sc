"use client";

import { useEffect, useRef, useState } from "react";

import { SignInButton } from "@/components/app/FailureNotice";
import { MarkedAvatar } from "@/components/app/MarkedAvatar";
import { Button } from "@/components/ui/button";
import { ContextMenu, ContextMenuContent, ContextMenuItem, ContextMenuTrigger } from "@/components/ui/context-menu";
import { LetterButton, UnreadLetterMark } from "@/components/letter/LetterButton";
import { useLetters } from "@/components/letter/LetterProvider";
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { copy } from "@/i18n";
import type { Character } from "@/lib/api";
import { showTime } from "@/lib/callTime";
import { arrange, dayOf, previewOf, type ListRow, type Preview } from "@/lib/conversationList";
import { unreadFrom } from "@/lib/letter";
import { pin, setShown, unpin } from "@/lib/listPreferences";
import { cn } from "@/lib/utils";
import { herVars } from "@/theme/herVars";
import { HideIcon, PinIcon, SearchIcon, ShowIcon, UnpinIcon } from "@/theme/icons";

import { Announcements } from "./Announcements";
import { PreviewText } from "./PreviewText";
import { ServiceStatusButton } from "./ServiceStatusButton";
import { useDirectory, type CallInList } from "./ConversationDirectory";
import { ListFilter } from "./ListFilter";
import { useCallTime } from "./useCallTime";

const t = copy.conversationList;

/**
 * 对话列表（DESIGN.md「Conversation list」）：顶上「对话」大标题、信封键（GLOSSARY.md「信」）、服务状态和公告铃铛，下面一个按名字
 * 或组合找人的搜索框，右边是筛选按钮（`ListFilter`）；每位角色一行（56px 头像、名字和时间一行，最后一句一行），
 * 选中行铺中性的 bg-muted；有人被隐藏时最后一行是「已隐藏 n 位」。她有没看过的搭话时，时间前面一个她颜色的小圆点，当前对话正显示着的那位不标；
 * 她有没读过的信时，名字后面一枚小信封。显示谁、按什么顺序由 `arrange` 决定：置顶的在前，最近有过往来的在上面；隐藏的不显示，
 * 但搜索时照样能搜到，当前打开的和正在通话的始终留下。一整列不按组合分段，换位置时直接跳过去、不做动画。
 * 列表栏是实底，不在她的子树里。宽屏时在左栏，窄屏时占满一页。
 */
export function ConversationList({ selectedId }: { selectedId: string | null }) {
  const { account, characters, latest, preferences, tidy, failure, reload, call, go, onScreen } = useDirectory();
  const now = useMinute();
  const [query, setQuery] = useState("");
  const [isFilterOpen, setFilterOpen] = useState(false);
  const { letters } = useLetters();
  const keep = [selectedId, call?.characterId].filter((id): id is string => !!id);
  const unreadLetters = unreadFrom(letters);
  const shown = characters && arrange(characters, latest, { preferences, query, keep, onScreen, unreadLetters });
  const hiddenCount = shown?.hiddenCount ?? 0;
  // 搜索时隐藏的人照样出现，「已隐藏 n 位」和全部隐藏的空状态只在没有搜索时出现。
  const showsHidden = query.trim() === "" && hiddenCount > 0;

  return (
    <div className="flex h-full flex-col bg-background text-foreground">
      <header className="flex shrink-0 items-center gap-2 pt-3 pr-2 pb-2 pl-4">
        <h1 className="flex-1 text-list-title">{t.title}</h1>
        <LetterButton />
        <ServiceStatusButton />
        <Announcements userId={account?.id ?? null} />
      </header>

      <div className="flex shrink-0 items-center gap-1 pr-2 pb-2 pl-4">
        <label className="flex h-9 min-w-0 flex-1 items-center gap-2 rounded-lg bg-muted px-3 text-muted-foreground has-focus-visible:ring-3 has-focus-visible:ring-ring/50">
          <SearchIcon aria-hidden className="size-4 shrink-0" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t.search}
            aria-label={t.search}
            className="min-w-0 flex-1 bg-transparent text-body text-foreground outline-none placeholder:text-muted-foreground"
          />
        </label>
        <ListFilter isOpen={isFilterOpen} onOpenChange={setFilterOpen} hiddenCount={hiddenCount} />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {failure ? (
          <Empty>
            <EmptyHeader>
              <EmptyTitle>{t.loadFailed}</EmptyTitle>
              <EmptyDescription>{failure.message}</EmptyDescription>
            </EmptyHeader>
            <EmptyContent>
              {failure.signedOut ? (
                <SignInButton />
              ) : (
                <Button variant="outline" onClick={reload}>
                  {t.retry}
                </Button>
              )}
            </EmptyContent>
          </Empty>
        ) : !shown ? (
          <Loading />
        ) : shown.rows.length === 0 && showsHidden ? (
          <Empty>
            <EmptyHeader>
              <EmptyTitle>{t.allHidden}</EmptyTitle>
            </EmptyHeader>
            <EmptyContent>
              <Button variant="outline" onClick={() => setFilterOpen(true)}>
                {t.chooseShown}
              </Button>
            </EmptyContent>
          </Empty>
        ) : shown.rows.length === 0 ? (
          <p className="px-4 py-6 text-center text-preview text-muted-foreground">{t.noMatch}</p>
        ) : (
          <>
            <ul aria-label={t.title}>
              {shown.rows.map((row) => {
                const c = row.character;
                return (
                  <li key={c.id}>
                    <Row
                      row={row}
                      preview={previewOf(latest[c.id])}
                      call={call?.characterId === c.id ? call : null}
                      isSelected={c.id === selectedId}
                      now={now}
                      onSelect={() => {
                        if (c.id === selectedId) return;
                        go(`/conversation/${c.id}`);
                      }}
                      onTogglePin={() => tidy((p) => (row.isPinned ? unpin(p, c.id) : pin(p, c.id)))}
                      onToggleHidden={() => tidy((p) => setShown(p, [c.id], row.isHidden))}
                    />
                  </li>
                );
              })}
            </ul>
            {showsHidden && (
              <button
                type="button"
                onClick={() => setFilterOpen(true)}
                className="w-full px-4 py-3 text-left text-meta text-muted-foreground outline-none hover:bg-muted/60 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:ring-inset"
              >
                {t.hiddenCount(String(hiddenCount))}
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}

/**
 * 列表里的一行：一整个按钮，选中时 `aria-current`，铺中性的 bg-muted（不用她的颜色）；置顶的时间旁边有个小图钉。
 * 有没看过的搭话时时间前面一个她颜色（`her-mark`）的小圆点：列表栏不在她的子树里，只在圆点上套她的颜色变量；
 * 名字和最后一句不加深。
 * 右键、触屏长按、菜单键或 Shift+F10 打开行菜单（中性色）：置顶或取消置顶，在列表中隐藏或显示。
 */
function Row({
  row: { character, isPinned, isHidden, isUnseen, hasUnreadLetter },
  preview,
  call,
  isSelected,
  now,
  onSelect,
  onTogglePin,
  onToggleHidden,
}: {
  row: ListRow<Character>;
  preview: Preview | null;
  call: CallInList;
  isSelected: boolean;
  now: Date;
  onSelect: () => void;
  onTogglePin: () => void;
  onToggleHidden: () => void;
}) {
  const time = useCallTime(call?.state);
  // 长按打开菜单后，松手时浏览器可能还会补发一次点击；菜单打开之后、下一次按下之前的点击不打开对话。
  const openedMenu = useRef(false);
  const description = call ? (
    time ? (
      copy.call.listConnected(showTime(time))
    ) : (
      copy.call.dialing
    )
  ) : !preview ? (
    t.neverTalked
  ) : (
    <PreviewText preview={preview} name={character.name} />
  );
  return (
    <ContextMenu
      onOpenChange={(open) => {
        if (open) openedMenu.current = true;
      }}
    >
      <ContextMenuTrigger
        render={<button type="button" />}
        onPointerDown={() => (openedMenu.current = false)}
        onKeyDown={() => (openedMenu.current = false)}
        onClick={() => {
          if (!openedMenu.current) onSelect();
        }}
        aria-current={isSelected ? "page" : undefined}
        className={cn(
          "flex w-full items-center gap-3 px-4 py-2.5 text-left outline-none focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:ring-inset",
          isSelected ? "bg-muted" : "hover:bg-muted/60",
        )}
      >
        <MarkedAvatar name={character.name} src={character.avatar_url} size="list" />
        <span className="flex min-w-0 flex-1 flex-col gap-0.5">
          <span className="flex items-baseline gap-2">
            <span className="flex min-w-0 flex-1 items-baseline gap-1.5">
              <span className="min-w-0 truncate text-row-name">{character.name}</span>
              {hasUnreadLetter && <UnreadLetterMark />}
            </span>
            {((preview && !call) || isPinned) && (
              <span className="flex shrink-0 items-center gap-1 text-meta text-muted-foreground tabular-nums">
                {isUnseen && preview && !call && (
                  <>
                    <span aria-hidden style={herVars(character.color)} className="size-2 shrink-0 rounded-full bg-her-mark" />
                    <span className="sr-only">{t.unseen}</span>
                  </>
                )}
                {preview && !call && listTime(new Date(preview.at), now)}
                {isPinned && (
                  <>
                    <PinIcon aria-hidden className="size-3" />
                    <span className="sr-only">{t.pinned}</span>
                  </>
                )}
              </span>
            )}
          </span>
          <span className="truncate text-preview text-muted-foreground tabular-nums">{description}</span>
        </span>
      </ContextMenuTrigger>
      <ContextMenuContent>
        {/* 菜单项里的图标默认 16px、跟着菜单文字的颜色（DESIGN.md「行菜单」） */}
        <ContextMenuItem onClick={onTogglePin}>
          {isPinned ? <UnpinIcon aria-hidden /> : <PinIcon aria-hidden />}
          {isPinned ? t.unpin : t.pin}
        </ContextMenuItem>
        <ContextMenuItem onClick={onToggleHidden}>
          {isHidden ? <ShowIcon aria-hidden /> : <HideIcon aria-hidden />}
          {isHidden ? t.show : t.hide}
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  );
}

/** 列表里的时间：今天写时刻（和气泡旁的时间一样写成 8:49），昨天写「昨天」，今年写月日，更早写年月日。 */
function listTime(at: Date, now: Date): string {
  const two = (n: number) => String(n).padStart(2, "0");
  switch (dayOf(at, now)) {
    case "today":
      return `${at.getHours()}:${two(at.getMinutes())}`;
    case "yesterday":
      return t.yesterday;
    case "thisYear":
      return t.monthDay(String(at.getMonth() + 1), String(at.getDate()));
    case "earlier":
      return t.fullDate(String(at.getFullYear()), String(at.getMonth() + 1), String(at.getDate()));
  }
}

/** 现在的时间，每分钟更新一次，过了午夜「今天」「昨天」会跟着变。 */
function useMinute(): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(timer);
  }, []);
  return now;
}

function Loading() {
  return (
    <div className="flex flex-col" aria-label={t.loading} aria-busy>
      {[0, 1].map((i) => (
        <div key={i} className="flex items-center gap-3 px-4 py-2.5">
          <Skeleton className="size-list-avatar shrink-0 rounded-full" />
          <div className="flex flex-1 flex-col gap-2">
            <Skeleton className="h-4 w-2/5" />
            <Skeleton className="h-3 w-3/4" />
          </div>
        </div>
      ))}
    </div>
  );
}
