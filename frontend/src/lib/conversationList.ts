// 消息列表每一行的内容：她最新一次对话的最后一句和时间（spec「信息架构」）；以及显示哪些行、按什么顺序排。
// 只给出结构，文字由界面按当前语言拼（`copy.conversationList`）。

import type { LatestConversation } from "@/lib/api";
import { matchesSearch, type Searchable } from "@/lib/characterSearch";
import { type EventShown, unwellOf } from "@/lib/conversationEvents";
import { NO_PREFERENCES, type ListPreferences } from "@/lib/listPreferences";

/** 列表里的一行预览。`from` 为 null 表示对话已经开了但还没有话；她的话带着发出来了的照片时 `photo`
 * 为 true，界面在前面加相机；`event` 是一条对话事件，那句话见 `eventText`。 */
export type Preview =
  | { from: "her"; text: string; at: string; photo: boolean }
  | { from: "you" | null; text: string; at: string }
  | ({ from: "event"; at: string } & EventShown);

/** 她最新一次对话的预览（`previewOf` 一段对话）；从没聊过的角色没有预览。 */
export function previewOf(latest: LatestConversation | undefined): Preview | null {
  return latest ? previewOfOne(latest) : null;
}

/** 一段对话的预览：她说的显示字幕（没有字幕时退回日语原文），那条回复带着发出来了的照片时标上照片；
 * 自己说的原样，对话事件是这件事；还没有话时是对话开始的时间。对话列表和历史对话面板的每一行都这么写。 */
export function previewOfOne(conversation: Pick<LatestConversation, "created_at" | "last_message">): Preview {
  const last = conversation.last_message;
  if (!last) return { from: null, text: "", at: conversation.created_at };
  if ("type" in last) {
    return { from: "event", event: last.kind, gift: last.gift_name ?? null, unwell: unwellOf(last), at: last.created_at };
  }
  if (last.role === "user") return { from: "you", text: last.text ?? "", at: last.created_at };
  return { from: "her", text: last.zh || last.ja || "", at: last.created_at, photo: last.photo === true };
}

/** 列表里的一行：哪位角色，她是不是置顶的、是不是隐藏的（行菜单和图钉据此显示），有没有没看过的搭话
 * （GLOSSARY.md「没看过的搭话」，时间前面的圆点据此显示），有没有没读过的信（GLOSSARY.md「没读过的信」，名字后面的小信封据此显示）。 */
export type ListRow<C> = { character: C; isPinned: boolean; isHidden: boolean; isUnseen: boolean; hasUnreadLetter: boolean };

export type ArrangeOptions = {
  /** 这台设备上的隐藏和置顶。 */
  preferences?: ListPreferences;
  /** 搜索框里的文字。 */
  query?: string;
  /** 始终留下的角色：当前打开的那位、正在通话的那位，隐藏了也不去掉。 */
  keep?: readonly string[];
  /** 她的当前对话正显示在对话页上的那位：搭话在那一页上直接出现、算看过，她那一行不标。 */
  onScreen?: string | null;
  /** 有没读过的信的那几位（lib/letter 的 `unreadFrom`）。信不随对话显示，正显示着她的对话也照样标。 */
  unreadLetters?: ReadonlySet<string>;
};

/**
 * 列表显示哪些角色、按什么顺序（spec「排序」「隐藏和置顶」）：
 * - 没有搜索时去掉隐藏的人，`keep` 里的不去掉；有搜索时在所有人里搜（`matchesSearch`），隐藏的照样出现。
 * - 置顶的排在前面；置顶的之间、其余的之间都按最近往来排，往来的时间就是这一行显示的时间（`previewOf`）；
 *   时间相同的、从没聊过的（排在最后）都保持 `characters` 原来的顺序，即原作的偶像顺序。
 * - 她最新的对话里有没看过的搭话的那一行标出来（`isUnseen`），当前对话正显示着的那位（`onScreen`）除外；
 *   她有没读过的信的那一行也标出来（`hasUnreadLetter`）。
 * `hiddenCount` 是这台设备上隐藏的人数，只数 `characters` 里还有的。
 */
export function arrange<C extends Searchable & { id: string }>(
  characters: C[],
  latest: Record<string, LatestConversation>,
  { preferences = NO_PREFERENCES, query = "", keep = [], onScreen = null, unreadLetters }: ArrangeOptions = {},
): { rows: ListRow<C>[]; hiddenCount: number } {
  const hidden = new Set(preferences.hidden);
  const pinned = new Set(preferences.pinned);
  const isSearching = query.trim() !== "";
  const lastTalked = (c: C) => {
    const preview = previewOf(latest[c.id]);
    return preview ? Date.parse(preview.at) : -Infinity;
  };
  // sort 是稳定的：时间相同的保持原来的先后。
  const rows = characters
    .filter((c) => (isSearching ? matchesSearch(c, query) : !hidden.has(c.id) || keep.includes(c.id)))
    .map((c) => ({
      row: {
        character: c,
        isPinned: pinned.has(c.id),
        isHidden: hidden.has(c.id),
        isUnseen: c.id !== onScreen && latest[c.id]?.unseen_reach_out === true,
        hasUnreadLetter: unreadLetters?.has(c.id) ?? false,
      },
      at: lastTalked(c),
    }))
    .sort((a, b) => Number(b.row.isPinned) - Number(a.row.isPinned) || (a.at === b.at ? 0 : b.at > a.at ? 1 : -1))
    .map(({ row }) => row);
  return { rows, hiddenCount: characters.filter((c) => hidden.has(c.id)).length };
}

/** 导航「对话」上的点：没有搜索时的列表里，有一行有没看过的搭话（`arrange` 的 `isUnseen`）。隐藏了的不在列表里，不算。 */
export function hasUnseen<C extends Searchable & { id: string }>(
  characters: C[],
  latest: Record<string, LatestConversation>,
  { preferences, onScreen }: Pick<ArrangeOptions, "preferences" | "onScreen"> = {},
): boolean {
  return arrange(characters, latest, { preferences, onScreen }).rows.some((row) => row.isUnseen);
}

/** 筛选面板的一组：组合名（null 是最后的「其他」），和组里的人。 */
export type UnitGroup<C> = { unit: string | null; members: C[] };

/**
 * 按组合分组（spec「筛选面板」）：组合按官方顺序（`unit_order`），组内保持 `characters` 原来的顺序；
 * 没有组合、或者对不上官方顺序的角色放在最后一组。
 */
export function unitsOf<C extends { unit: string | null; unit_order: number | null }>(characters: C[]): UnitGroup<C>[] {
  const units = new Map<number, UnitGroup<C>>();
  const others: C[] = [];
  for (const c of characters) {
    if (c.unit === null || c.unit_order === null) {
      others.push(c);
      continue;
    }
    const group = units.get(c.unit_order) ?? { unit: c.unit, members: [] };
    group.members.push(c);
    units.set(c.unit_order, group);
  }
  const groups = [...units.entries()].sort(([a], [b]) => a - b).map(([, group]) => group);
  return others.length ? [...groups, { unit: null, members: others }] : groups;
}

/** 时间按哪一种写法显示：今天只写时刻，昨天写「昨天」，今年写月日，更早写年月日。按本地日历算。 */
export type Day = "today" | "yesterday" | "thisYear" | "earlier";

export function dayOf(at: Date, now: Date): Day {
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfYesterday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);
  if (at >= startOfToday) return "today";
  if (at >= startOfYesterday) return "yesterday";
  if (at.getFullYear() === now.getFullYear()) return "thisYear";
  return "earlier";
}
