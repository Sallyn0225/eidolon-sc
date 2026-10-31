"use client";

// PROTOTYPE, throwaway（prototype/letters-ui 分支）：方案 C，信跟着她走。
// 她的对话页页首、电话键左边一个信封键（她写过信才有），有没读过的时右上角一个点；点了是她的信：宽屏居中的 Dialog、
// 窄屏底部的 Drawer（同「历史对话」面板），只列她写的，最新的在上。信收起时飞回这个键。
// 对话列表上她那一行，名字后面一个小信封标出她有没读过的信。

import { useState } from "react";

import { useWide } from "@/components/conversations/ConversationDirectory";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle } from "@/components/ui/drawer";
import type { Character } from "@/lib/api";
import { cn } from "@/lib/utils";
import { herVars } from "@/theme/herVars";
import { LetterIcon } from "@/theme/icons";

import { useLetters } from "../LetterProvider";
import { MiniEnvelope } from "./MiniEnvelope";

export function HerLettersC({ character, className }: { character: Character; className?: string }) {
  const box = useLetters();
  const isWide = useWide();
  const [isOpen, setOpen] = useState(false);
  if (!box || box.variant !== "C") return null;
  const hers = box.letters.filter((l) => l.characterId === character.id);
  if (hers.length === 0) return null;
  const hasUnread = hers.some((l) => l.isUnread);
  const key = `her:${character.id}`;
  const title = `${character.name}的信`;
  const list = (
    <ol className="flex flex-col gap-2 overflow-y-auto px-1 pt-1 pb-4">
      {hers.map((letter) => (
        <li key={letter.id}>
          <MiniEnvelope
            letter={letter}
            shape="strip"
            onClick={() => {
              setOpen(false);
              box.open(letter.id, key);
            }}
          />
        </li>
      ))}
    </ol>
  );
  return (
    <>
      <Button
        ref={box.target(key)}
        variant="ghost"
        size="icon-lg"
        aria-label={hasUnread ? `${title}，有没读过的` : title}
        className={cn("relative", className)}
        onClick={() => setOpen(true)}
      >
        <LetterIcon className="size-5 text-her-mark" />
        {hasUnread && <span aria-hidden className="absolute top-1.5 right-1.5 size-1.5 rounded-full bg-foreground" />}
      </Button>
      {isWide ? (
        <Dialog open={isOpen} onOpenChange={setOpen}>
          <DialogContent style={herVars(character.color)} className="flex max-h-[80dvh] flex-col sm:max-w-sm">
            <DialogHeader>
              <DialogTitle>{title}</DialogTitle>
            </DialogHeader>
            {list}
          </DialogContent>
        </Dialog>
      ) : (
        <Drawer open={isOpen} onOpenChange={setOpen} showSwipeHandle>
          <DrawerContent style={herVars(character.color)}>
            <DrawerHeader>
              <DrawerTitle>{title}</DrawerTitle>
            </DrawerHeader>
            <div className="px-3">{list}</div>
          </DrawerContent>
        </Drawer>
      )}
    </>
  );
}

/** 对话列表上她那一行名字后面的小信封：她有没读过的信时才有。 */
export function HerUnreadMarkC({ characterId }: { characterId: string }) {
  const box = useLetters();
  if (!box || box.variant !== "C") return null;
  if (!box.letters.some((l) => l.characterId === characterId && l.isUnread)) return null;
  return (
    <>
      <LetterIcon aria-hidden className="size-3.5 shrink-0 self-center text-foreground" />
      <span className="sr-only">有没读过的信</span>
    </>
  );
}
