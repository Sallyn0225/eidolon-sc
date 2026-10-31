"use client";

// PROTOTYPE, throwaway（prototype/letters-ui 分支）：方案 A，对话列表页首的信封键。
// 公告铃铛左边一个 ghost 图标键，有没读过的信时右上角一个点（同铃铛）；点了在下面弹出 Popover，信封一枚压一枚，
// 最新的在上。点一枚拆开，信收起时飞回这个键。

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverHeader, PopoverTitle, PopoverTrigger } from "@/components/ui/popover";
import { LetterIcon } from "@/theme/icons";

import { useLetters } from "../LetterProvider";
import { MiniEnvelope } from "./MiniEnvelope";

export function BoxButtonA() {
  const box = useLetters();
  const [isOpen, setOpen] = useState(false);
  if (!box || box.variant !== "A" || box.letters.length === 0) return null;
  return (
    <Popover open={isOpen} onOpenChange={setOpen}>
      <PopoverTrigger
        render={
          <Button
            ref={box.target("box")}
            variant="ghost"
            size="icon-lg"
            aria-label={box.unreadCount > 0 ? "信，有没读过的" : "信"}
            className="relative"
          />
        }
      >
        <LetterIcon />
        {box.unreadCount > 0 && <span aria-hidden className="absolute top-1.5 right-1.5 size-1.5 rounded-full bg-foreground" />}
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80">
        <PopoverHeader>
          <PopoverTitle>信</PopoverTitle>
        </PopoverHeader>
        <ol className="-mx-1 flex max-h-[60dvh] flex-col overflow-y-auto px-1 pt-1 pb-2">
          {box.letters.map((letter, i) => (
            <li key={letter.id} className={i > 0 ? "-mt-3" : undefined} style={{ zIndex: box.letters.length - i }}>
              <MiniEnvelope
                letter={letter}
                shape="strip"
                className="shadow-sm"
                onClick={() => {
                  setOpen(false);
                  box.open(letter.id, "box");
                }}
              />
            </li>
          ))}
        </ol>
      </PopoverContent>
    </Popover>
  );
}
