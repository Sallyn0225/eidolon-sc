// Where the navigation shell's rules send the call (.scratch/app-navigation spec「外壳持有的东西」
// 「通话条」, ADR-0018): the conversations, the moments, the play page and the settings share one shell, and
// the call belongs to it, not to her conversation page. Given a URL and whom the call under way
// is with (or no one), these say whether that URL is in the shell, whether the call bar shows
// across its top, and whether going there keeps the call, asks first and then hangs up, or just
// goes. They also say which item of the rail (desktop) and the dock (phone) is current and where
// clicking one goes (spec「电脑导航栏」「手机 dock」).

import { PLAY_ROOT, playSubpage } from "@/lib/playRoute";

/** Going somewhere, with or without a call under way:
 * - `keep`: a page in the shell; the call goes on;
 * - `ask`: another character's conversation, or out of the shell; ask first, hang up if confirmed;
 * - `go`: no call under way; nothing to ask. */
export type Departure = "keep" | "ask" | "go";

/** The path of a URL, and whether it is on this site: the app links within itself by path, so
 * a URL with a host of its own is taken to be another site. */
function pathOf(href: string): { path: string; local: boolean } {
  const url = new URL(href, "http://shell.invalid");
  return { path: url.pathname, local: url.host === "shell.invalid" };
}

/** Whose conversation page this path is, or null if it is not one. */
function conversationOf(path: string): string | null {
  const match = /^\/conversation\/([^/]+)\/?$/.exec(path);
  return match ? decodeURIComponent(match[1]) : null;
}

/** Whether `href` is a character's conversation page (her letter does not pop up over it, lib/letter). */
export function isConversationPage(href: string): boolean {
  return conversationOf(pathOf(href).path) !== null;
}

/** The play page: its first level and each of its subpages. */
function isPlay(path: string): boolean {
  return path === PLAY_ROOT || playSubpage(path) !== null;
}

/** The conversations (list and each character's page), the moments, the play page (the first level
 * and each subpage) and the settings (memories among them) are in the shell; the admin console, `/about`, the privacy policy, the
 * terms, sign-in and consent are out of it, and so is anything on another site. */
export function isInShell(href: string): boolean {
  const { path, local } = pathOf(href);
  if (!local) return false;
  return (
    path === "/conversations" ||
    conversationOf(path) !== null ||
    path === MOMENTS ||
    isPlay(path) ||
    path === "/settings" ||
    path.startsWith("/settings/")
  );
}

/** The call bar across the top of the shell: while a call is under way, on a page in the shell
 * other than her own conversation page, which has its own bar under its header. Whether the
 * call layer is folded away is the caller's to add. */
export function showsShellCallBar(href: string, callee: string | null): boolean {
  if (callee === null || !isInShell(href)) return false;
  return conversationOf(pathOf(href).path) !== callee;
}

/** Whether the rail (desktop) and the dock (phone) are drawn at `href`: everywhere in the shell but
 * the bar, which covers them with its screen (.scratch/bar-room spec「入口、路由和外壳」); the
 * call bar still runs across the top there, and the bar takes the block under it. */
export function showsNav(href: string): boolean {
  return playSubpage(pathOf(href).path) !== "bar";
}

/** What going to `href` in this tab does to the call with `callee` (null for no call): one
 * character at a time, so another character's conversation asks, as does leaving the shell.
 * Links that open in a new tab never come here. */
export function departure(href: string, callee: string | null): Departure {
  if (callee === null) return "go";
  if (!isInShell(href)) return "ask";
  const other = conversationOf(pathOf(href).path);
  return other !== null && other !== callee ? "ask" : "keep";
}

/** The moments (GLOSSARY.md「朋友圈」): a first level of its own, with no second. */
const MOMENTS = "/moments";

/** The items of the rail and the dock, top to bottom (left to right on the dock). */
export const NAV_ITEMS = ["conversations", "moments", "play", "settings"] as const;
export type NavItem = (typeof NAV_ITEMS)[number];

/** The items drawn for a user: the moments only where the account has them (`Account.moments`; null
 * while the deployer has them off, or the account is not read yet). */
export function navItems(moments: boolean | null | undefined): NavItem[] {
  return NAV_ITEMS.filter((item) => item !== "moments" || moments === true);
}

/** Each item's first level; her conversation page, a play subpage and a settings category below it
 * are its second. */
export const FIRST_LEVEL: Record<NavItem, string> = {
  conversations: "/conversations",
  moments: MOMENTS,
  play: PLAY_ROOT,
  settings: "/settings",
};

/** The item the URL is under, marked current on the rail and the dock; null out of the shell. */
export function currentNavItem(href: string): NavItem | null {
  const { path } = pathOf(href);
  if (!isInShell(href)) return null;
  if (isPlay(path)) return "play";
  if (path === MOMENTS) return "moments";
  return path === "/settings" || path.startsWith("/settings/") ? "settings" : "conversations";
}

/** Whether the gifts subpage is before the user at `href`: it is shown, and no call layer covers it
 * (`isCallLayerOpen`). Draw chances that come meanwhile are seen as they come. The play page's
 * first level and the achievements subpage do not count: the cards there show them. */
export function isGiftsSubpageInView(href: string, isCallLayerOpen: boolean): boolean {
  return playSubpage(pathOf(href).path) === "gifts" && !isCallLayerOpen;
}

/** The dots on the rail and the dock: 「对话」 when a row of the list has a reach-out not yet seen,
 * 「朋友圈」 when a moment or her reply has shown since the moments were last opened, except on
 * the moments page itself, 「玩法」 when draw chances have come that are not yet seen, except while
 * the current item is the play page itself (its cards say which one). */
export function navDots(
  current: NavItem | null,
  { conversations, rewards, moments }: { conversations: boolean; rewards: boolean; moments: boolean },
): Record<NavItem, boolean> {
  return {
    conversations,
    moments: moments && current !== "moments",
    play: rewards && current !== "play",
    settings: false,
  };
}

/** Where clicking `item` from `href` goes: another item goes to its first level, and so does
 * the current one from its second level; the current one on its first level stays (null). */
export function navDestination(item: NavItem, href: string): string | null {
  const to = FIRST_LEVEL[item];
  return currentNavItem(href) === item && pathOf(href).path === to ? null : to;
}

/** What has the focus, as far as telling typing goes (an Element will do). */
export type Focused = { tagName: string; type?: string; isContentEditable?: boolean } | null;

/** Typing on a phone, near enough the keyboard being up, which hides the dock: the focus is in a
 * textarea, an input other than a checkbox, or something editable. */
export function isTyping(focused: Focused): boolean {
  if (!focused) return false;
  if (focused.tagName === "TEXTAREA" || focused.isContentEditable) return true;
  return focused.tagName === "INPUT" && focused.type !== "checkbox";
}
