"use client";

import { useRef, useState } from "react";

import { FailureNotice } from "@/components/app/FailureNotice";
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
import { ContextMenu, ContextMenuContent, ContextMenuItem, ContextMenuTrigger } from "@/components/ui/context-menu";
import { Empty, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { copy } from "@/i18n";
import type { Character } from "@/lib/api";
import { toFailure, type Failure } from "@/lib/failure";
import { groupLetters, letterDay, letterMonth, type LetterSummary } from "@/lib/letter";
import { letterVars } from "@/theme/herVars";
import { TrashIcon } from "@/theme/icons";

import { useLetters } from "./LetterProvider";
import { Seal } from "./Seal";

const t = copy.letter;

/**
 * 信的列表（GLOSSARY.md「信」，DESIGN.md「信」）：页首信封键点开的所有的信（`grouped`：没读过的在最上面，其余按月分组），
 * 和她的对话页页首信封键点开的她的信（不分组）；都从新到旧，写信的人不在角色配置里的不列。点一行拆开；电脑上右键、
 * 手机上长按出「删除这封信」，确认后删（照删历史对话的确认框）。确认框嵌在列表所在的浮层里，删完浮层还开着。
 */
export function LetterList({
  letters,
  grouped,
  onPick,
}: {
  letters: LetterSummary[];
  grouped: boolean;
  onPick: (letter: LetterSummary) => void;
}) {
  const { writers, remove } = useLetters();
  // 要删的那封。确认框关上时只把 confirming 置成 false，pending 留着，关闭动画里的文字不会闪成空白。
  const [pending, setPending] = useState<{ letter: LetterSummary; writer: Character } | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [failure, setFailure] = useState<Failure | null>(null);
  const thisYear = new Date().getFullYear();

  const shown = letters.filter((l) => writers.has(l.character_id));
  if (shown.length === 0) {
    return (
      <Empty>
        <EmptyHeader>
          <EmptyTitle>{t.none}</EmptyTitle>
        </EmptyHeader>
      </Empty>
    );
  }

  const sections: { title: string | null; letters: LetterSummary[] }[] = grouped
    ? (() => {
        const { unread, months } = groupLetters(shown);
        return [
          ...(unread.length > 0 ? [{ title: t.unread, letters: unread }] : []),
          ...months.map((m) => ({ title: letterMonth(m.month, thisYear), letters: m.letters })),
        ];
      })()
    : [{ title: null, letters: shown }];

  async function confirmRemove() {
    if (!pending) return;
    setConfirming(false);
    setFailure(null);
    try {
      await remove(pending.letter);
    } catch (e) {
      setFailure(toFailure(e));
    }
  }

  return (
    <div className="flex flex-col gap-4 py-1">
      {failure && <FailureNotice failure={failure} />}
      {sections.map((section) => (
        <section key={section.title ?? ""} className="flex flex-col gap-2">
          {section.title && <h3 className="text-meta text-muted-foreground">{section.title}</h3>}
          <ul className="flex flex-col gap-2">
            {section.letters.map((letter) => {
              const writer = writers.get(letter.character_id)!;
              return (
                <li key={letter.id}>
                  <LetterRow
                    letter={letter}
                    writer={writer}
                    thisYear={thisYear}
                    onClick={() => onPick(letter)}
                    onRemove={() => {
                      setPending({ letter, writer });
                      setConfirming(true);
                    }}
                  />
                </li>
              );
            })}
          </ul>
        </section>
      ))}
      <AlertDialog open={confirming} onOpenChange={setConfirming}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{pending ? t.removeTitle(pending.writer.name) : ""}</AlertDialogTitle>
            <AlertDialogDescription>{t.removeDescription}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{copy.common.cancel}</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={confirmRemove}>
              {t.removeConfirm}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

/** 列表里的一枚小信封：固定浅色，她的颜色只在封蜡和名字上；写着她、场合和日期，没读过的右边一个墨色的点。 */
function LetterRow({
  letter,
  writer,
  thisYear,
  onClick,
  onRemove,
}: {
  letter: LetterSummary;
  writer: Character;
  thisYear: number;
  onClick: () => void;
  onRemove: () => void;
}) {
  // 长按打开菜单后，松手时浏览器可能还会补发一次点击；菜单打开之后、下一次按下之前的点击不拆信。
  const openedMenu = useRef(false);
  const occasion = letter.occasions.map((o) => t.occasions[o]).join("、");
  const day = letterDay(letter.day, thisYear);
  const isUnread = !letter.read;
  return (
    <ContextMenu
      onOpenChange={(open) => {
        if (open) openedMenu.current = true;
      }}
    >
      <ContextMenuTrigger
        render={<button type="button" />}
        aria-label={t.row(writer.name, occasion, day, isUnread)}
        onPointerDown={() => (openedMenu.current = false)}
        onKeyDown={() => (openedMenu.current = false)}
        onClick={() => {
          if (!openedMenu.current) onClick();
        }}
        style={letterVars(writer.color)}
        className="flex h-16 w-full items-center gap-3 rounded-md bg-letter-envelope px-3 text-left text-letter-ink ring-1 ring-letter-envelope-edge outline-none transition-transform select-none hover:-translate-y-0.5 focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        <Seal className="size-9 shadow-sm" />
        <span className="flex min-w-0 flex-1 flex-col">
          <span lang="ja" className="truncate font-japanese text-row-name text-her-letter-ink">
            {writer.name}
          </span>
          <span className="truncate text-meta text-letter-muted">
            {occasion} · {day}
          </span>
        </span>
        {isUnread && <span aria-hidden className="size-2 shrink-0 rounded-full bg-letter-ink" />}
      </ContextMenuTrigger>
      <ContextMenuContent>
        <ContextMenuItem variant="destructive" onClick={onRemove}>
          <TrashIcon aria-hidden />
          {t.remove}
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  );
}
