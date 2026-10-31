"use client";

// PROTOTYPE, throwaway（prototype/letters-ui 分支）：信箱里的一枚信封。信封固定浅色（同拆信层），
// 她的颜色只在封蜡和名字上（letterVars）；上面写她、场合和日期，没读过的右上角一个墨色的点。

import { forwardRef, type ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";
import { letterVars } from "@/theme/herVars";

import type { BoxLetter } from "../LetterProvider";
import { letterDay, OCCASION_LABELS } from "./prototypeLetters";

type Props = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "type"> & {
  letter: BoxLetter;
  /** strip：一长条（A 的一叠、C 的列表）；tile：一枚完整的信封（B 的墙）。 */
  shape: "strip" | "tile";
  /** tile 上不写她的名字（墙按她分组，组名已经写了）。 */
  hideName?: boolean;
};

function Seal({ className }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={cn("grid shrink-0 place-items-center rounded-full bg-her-seal text-her-seal-fg shadow-sm ring-2 ring-her-seal/30", className)}
    >
      <svg viewBox="0 0 24 24" className="size-1/2 fill-current">
        <path d="M12 2.5l2.9 6.1 6.6.8-4.9 4.6 1.3 6.5L12 17.3l-5.9 3.2 1.3-6.5L2.5 9.4l6.6-.8z" />
      </svg>
    </span>
  );
}

export const MiniEnvelope = forwardRef<HTMLButtonElement, Props>(function MiniEnvelope(
  { letter, shape, hideName = false, className, style, ...props },
  ref,
) {
  const occasion = OCCASION_LABELS[letter.occasion];
  const day = letterDay(letter.date);
  const label = `${letter.writer.name}的信，${occasion}，${day}${letter.isUnread ? "，没读过" : ""}`;
  const dot = letter.isUnread && (
    <span aria-hidden className="absolute top-2 right-2 size-1.5 rounded-full bg-letter-ink" />
  );

  if (shape === "strip") {
    return (
      <button
        ref={ref}
        type="button"
        aria-label={label}
        style={{ ...letterVars(letter.writer.color), ...style }}
        className={cn(
          "relative flex h-16 w-full items-center gap-3 rounded-md bg-letter-envelope px-3 text-left text-letter-ink ring-1 ring-letter-envelope-edge outline-none transition-transform hover:-translate-y-0.5 focus-visible:ring-3 focus-visible:ring-ring/50",
          className,
        )}
        {...props}
      >
        <Seal className="size-9" />
        <span className="flex min-w-0 flex-1 flex-col">
          <span lang="ja" className="truncate font-japanese text-row-name text-her-letter-ink">
            {letter.writer.name}
          </span>
          <span className="truncate text-meta text-letter-muted">
            {occasion} · {day}
          </span>
        </span>
        {letter.isUnread && <span aria-hidden className="size-2 shrink-0 rounded-full bg-letter-ink" />}
      </button>
    );
  }

  return (
    <button
      ref={ref}
      type="button"
      aria-label={label}
      style={{ ...letterVars(letter.writer.color), ...style }}
      className={cn(
        "group relative block aspect-[8/5] w-full rounded-md bg-letter-envelope text-letter-ink ring-1 ring-letter-envelope-edge outline-none transition-transform hover:-translate-y-1 focus-visible:ring-3 focus-visible:ring-ring/50",
        className,
      )}
      {...props}
    >
      <svg aria-hidden viewBox="0 0 160 100" preserveAspectRatio="none" className="absolute inset-0 size-full">
        <path
          d="M0 0 L80 46 L160 0 M0 100 L66 52 M160 100 L94 52"
          fill="none"
          strokeWidth="1"
          vectorEffect="non-scaling-stroke"
          className="stroke-letter-envelope-edge"
        />
      </svg>
      <Seal className="absolute top-[46%] left-1/2 size-8 -translate-1/2" />
      <span className="absolute inset-x-3 bottom-2 flex items-baseline justify-between gap-2">
        <span className="truncate text-subtitle">{occasion}</span>
        <span className="shrink-0 text-meta text-letter-muted tabular-nums">{day}</span>
      </span>
      {!hideName && (
        <span lang="ja" className="absolute top-2 left-3 truncate font-japanese text-meta text-her-letter-ink">
          {letter.writer.name}
        </span>
      )}
      {dot}
    </button>
  );
});
