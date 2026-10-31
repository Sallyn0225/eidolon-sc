"use client";

// PROTOTYPE, throwaway（prototype/letters-ui 分支）：信箱方案的切换条。浮在底部中间，左右箭头切 A/B/C（← → 键也行，
// 焦点在输入框里时不拦），「重置读过」回到一开始的读没读过、再弹一次信封。只在开发和 NEXT_PUBLIC_PROTOTYPE=1 的构建里有。

import { useEffect } from "react";

import { BackIcon, ForwardIcon } from "@/theme/icons";

import { VARIANTS, type Variant } from "./prototypeLetters";

export function PrototypeSwitcher({
  variant,
  onChange,
  onReset,
}: {
  variant: Variant;
  onChange: (variant: Variant) => void;
  onReset: () => void;
}) {
  const index = VARIANTS.findIndex((v) => v.key === variant);
  const step = (by: number) => onChange(VARIANTS[(index + by + VARIANTS.length) % VARIANTS.length].key);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (el?.closest("input, textarea, [contenteditable=''], [contenteditable='true']")) return;
      if (e.key === "ArrowLeft") step(-1);
      if (e.key === "ArrowRight") step(1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const current = VARIANTS[index];
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-20 z-40 flex justify-center md:bottom-4">
      <div className="pointer-events-auto flex items-center gap-1 rounded-full bg-foreground p-1 text-meta text-background shadow-lg">
        <button type="button" aria-label="上一个方案" onClick={() => step(-1)} className="grid size-8 place-items-center rounded-full hover:bg-background/15">
          <BackIcon className="size-4" />
        </button>
        <span className="min-w-28 text-center tabular-nums">
          {current.key} {current.name}
        </span>
        <button type="button" aria-label="下一个方案" onClick={() => step(1)} className="grid size-8 place-items-center rounded-full hover:bg-background/15">
          <ForwardIcon className="size-4" />
        </button>
        <button type="button" onClick={onReset} className="rounded-full px-3 py-1.5 hover:bg-background/15">
          重置读过
        </button>
      </div>
    </div>
  );
}
