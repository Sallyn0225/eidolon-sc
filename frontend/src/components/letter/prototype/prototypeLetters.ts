// PROTOTYPE, throwaway（prototype/letters-ui 分支，不合进 dev/main）：信箱界面原型用的假信。
// 正文和音频借 last-letter 那 29 封（components/letter/letters.json），场合、日期、读没读过都是假的；
// 同一位角色的几封信正文一样，原型只看信箱长什么样，不看内容。

/** 写信的场合（GLOSSARY.md「信」）。 */
export type Occasion = "close" | "intimate" | "complete" | "producer_birthday" | "her_birthday" | "anniversary_100";

/** 信封上写的场合，越短越好。 */
export const OCCASION_LABELS: Record<Occasion, string> = {
  close: "更近一步",
  intimate: "特别的人",
  complete: "一路走来",
  producer_birthday: "你的生日",
  her_birthday: "她的生日",
  anniversary_100: "相识 100 天",
};

export type PrototypeLetter = {
  id: string;
  characterId: string;
  occasion: Occasion;
  /** 写信那天，`YYYY-MM-DD`。 */
  date: string;
  /** 一开始就算读过的（重置以后回到这个状态）。 */
  readAtStart: boolean;
};

/** 按时间从早到晚。最近的三封一开始没读过。 */
export const PROTOTYPE_LETTERS: PrototypeLetter[] = [
  { id: "l1", characterId: "mano", occasion: "close", date: "2026-10-04", readAtStart: true },
  { id: "l2", characterId: "hiori", occasion: "close", date: "2026-10-09", readAtStart: true },
  { id: "l3", characterId: "kaho", occasion: "intimate", date: "2026-10-12", readAtStart: true },
  { id: "l4", characterId: "meguru", occasion: "her_birthday", date: "2026-10-15", readAtStart: true },
  { id: "l5", characterId: "madoka", occasion: "close", date: "2026-10-20", readAtStart: true },
  { id: "l6", characterId: "mano", occasion: "anniversary_100", date: "2026-10-24", readAtStart: true },
  { id: "l7", characterId: "hazuki", occasion: "producer_birthday", date: "2026-10-27", readAtStart: false },
  { id: "l8", characterId: "kaho", occasion: "her_birthday", date: "2026-10-29", readAtStart: false },
  { id: "l9", characterId: "mano", occasion: "complete", date: "2026-10-31", readAtStart: false },
];

/** 信封上的日期：「10月31日」。 */
export function letterDay(date: string): string {
  const [, month, day] = date.split("-").map(Number);
  return `${month}月${day}日`;
}

export type Variant = "A" | "B" | "C";

export const VARIANTS: { key: Variant; name: string }[] = [
  { key: "A", name: "页首信封键" },
  { key: "B", name: "玩法里的信" },
  { key: "C", name: "她的对话页" },
];

/** 切换条只在开发和原型构建（NEXT_PUBLIC_PROTOTYPE=1）里出现。 */
export const SHOWS_PROTOTYPE = process.env.NODE_ENV !== "production" || process.env.NEXT_PUBLIC_PROTOTYPE === "1";
