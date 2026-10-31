"use client";

import { useRef, useState, type ReactNode } from "react";

import { useDirectory, useWide } from "@/components/conversations/ConversationDirectory";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle } from "@/components/ui/drawer";
import { Popover, PopoverContent, PopoverHeader, PopoverTitle, PopoverTrigger } from "@/components/ui/popover";
import { copy } from "@/i18n";
import type { Character } from "@/lib/api";
import { hasUnread, hersOf, showsLetterButton, type LetterSummary } from "@/lib/letter";
import { cn } from "@/lib/utils";
import { herVars } from "@/theme/herVars";
import { LetterIcon } from "@/theme/icons";

import { LetterList } from "./LetterList";
import { useLetters } from "./LetterProvider";

const t = copy.letter;

/** 信封键右上角的点：有没读过的信（和公告铃铛的点一样）。 */
function Dot({ className }: { className?: string }) {
  return <span aria-hidden className={cn("absolute size-1.5 rounded-full bg-foreground", className)} />;
}

/**
 * 对话列表页首、服务状态旁边的信封键（GLOSSARY.md「信」，DESIGN.md「信」）：部署者开着信、或者用户已经有信时才出现；
 * 有没读过的信时右上角一个点。点开是所有的信：没读过的在最上面，其余按月分组、从新到旧，能滚动；宽屏是挂在键下面、
 * 固定高度的 Popover，窄屏是接近全屏的底部 Drawer。从这里拆的信、自动弹出的信，收起时都飞回这个键。
 */
export function LetterButton() {
  const { account } = useDirectory();
  const { letters, open, home } = useLetters();
  const wide = useWide();
  const [isOpen, setOpen] = useState(false);
  if (!showsLetterButton(account?.letters === true, letters)) return null;

  const unread = hasUnread(letters);
  const props = { ref: home, variant: "ghost", size: "icon-lg", "aria-label": unread ? t.boxUnread : t.box, className: "relative" } as const;
  const icon = (
    <>
      <LetterIcon />
      {unread && <Dot className="top-1.5 right-1.5" />}
    </>
  );
  const pick = (letter: LetterSummary) => {
    setOpen(false);
    open(letter, home);
  };
  const list = <LetterList letters={letters ?? []} grouped onPick={pick} />;

  if (wide) {
    return (
      <Popover open={isOpen} onOpenChange={setOpen}>
        <PopoverTrigger render={<Button {...props} />}>{icon}</PopoverTrigger>
        <PopoverContent align="end" className="h-[min(28rem,70dvh)] w-80">
          <PopoverHeader>
            <PopoverTitle>{t.listTitle}</PopoverTitle>
          </PopoverHeader>
          <div className="-mx-2.5 min-h-0 flex-1 overflow-y-auto px-2.5">{list}</div>
        </PopoverContent>
      </Popover>
    );
  }

  return (
    <>
      <Button {...props} onClick={() => setOpen(true)}>
        {icon}
      </Button>
      <Drawer open={isOpen} onOpenChange={setOpen} showSwipeHandle>
        <DrawerContent className="h-[90dvh]">
          <DrawerHeader>
            <DrawerTitle>{t.listTitle}</DrawerTitle>
          </DrawerHeader>
          <div className="min-h-0 flex-1 overflow-y-auto px-4 pt-2 pb-4">{list}</div>
        </DrawerContent>
      </Drawer>
    </>
  );
}

/**
 * 她的对话页页首、电话键旁边的信封键（方案 C）：她写过信才出现，有没读过的时右上角一个点。点开只列她写的信、从新到旧：
 * 宽屏居中的 Dialog，窄屏底部 Drawer（同「历史对话」面板），内容上注入她的颜色。从这里拆的信收起时飞回这个键。
 */
export function HerLetterButton({ character, className }: { character: Character; className?: string }) {
  const { letters, open } = useLetters();
  const wide = useWide();
  const [isOpen, setOpen] = useState(false);
  const button = useRef<HTMLButtonElement>(null);
  const hers = hersOf(letters, character.id);
  if (hers.length === 0) return null;

  const unread = hasUnread(hers);
  const title = t.hers(character.name);
  const pick = (letter: LetterSummary) => {
    setOpen(false);
    open(letter, button);
  };
  const list = <LetterList letters={hers} grouped={false} onPick={pick} />;
  const panel = (body: ReactNode) =>
    wide ? (
      <Dialog open={isOpen} onOpenChange={setOpen}>
        <DialogContent style={herVars(character.color)} className="flex max-h-[80dvh] flex-col sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>{title}</DialogTitle>
          </DialogHeader>
          <div className="-mx-1 min-h-0 overflow-y-auto px-1">{body}</div>
        </DialogContent>
      </Dialog>
    ) : (
      <Drawer open={isOpen} onOpenChange={setOpen} showSwipeHandle>
        <DrawerContent style={herVars(character.color)}>
          <DrawerHeader>
            <DrawerTitle>{title}</DrawerTitle>
          </DrawerHeader>
          <div className="min-h-0 overflow-y-auto px-4 pb-4">{body}</div>
        </DrawerContent>
      </Drawer>
    );

  return (
    <>
      <Button
        ref={button}
        variant="ghost"
        size="icon-lg"
        aria-label={unread ? t.hersUnread(character.name) : title}
        className={cn("relative", className)}
        onClick={() => setOpen(true)}
      >
        <LetterIcon className="size-5" />
        {unread && <Dot className="top-2 right-2" />}
      </Button>
      {panel(list)}
    </>
  );
}

/** 对话列表上她那一行名字后面的小信封：她有没读过的信时才有（`arrange` 的 `hasUnreadLetter`），读屏读「有没读过的信」。 */
export function UnreadLetterMark() {
  return (
    <>
      <LetterIcon aria-hidden className="size-3.5 shrink-0 self-center text-foreground" />
      <span className="sr-only">{t.unreadMark}</span>
    </>
  );
}
