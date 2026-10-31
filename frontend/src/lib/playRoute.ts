// The play page's addresses (.scratch/play-hub spec「页面和路由」): `/play` is the first level, the
// cards; `/play/<subpage>` is a card's page, the second level, with nothing below it. A refresh or
// a shared link opens the same subpage. The old gifts page `/gifts` (with its `?to=` and any other
// parameters) is sent to `/play/gifts`, the old `/play/tasks` to `/play/achievements`, and play
// addresses we do not know to `/play`, before any page loads (the same as the settings' old
// addresses, lib/settingsCategory).

/** The subpages, one for each card of the first level. */
// PROTOTYPE（prototype/letters-ui）：加了 letters，信箱方案 B 的信封墙。
export const PLAY_SUBPAGES = ["gifts", "achievements", "calendar", "cycles", "bar", "letters"] as const;

export type PlaySubpage = (typeof PLAY_SUBPAGES)[number];

export const PLAY_ROOT = "/play";

/** The address of the play page's first level, or of one of its subpages. */
export function playHref(subpage?: PlaySubpage): string {
  return subpage ? `${PLAY_ROOT}/${subpage}` : PLAY_ROOT;
}

/** The subpage whose page the path is, or null for the first level and anything else. */
export function playSubpage(path: string): PlaySubpage | null {
  const match = /^\/play\/([^/]+)$/.exec(path);
  return PLAY_SUBPAGES.find((known) => known === match?.[1]) ?? null;
}

/** Where an old or unknown play address goes instead (replacing it in the history), or null if it
 * is fine as it is. The address's parameters stay. */
export function playRedirect(href: string): string | null {
  const url = new URL(href, "http://play.invalid");
  const path = url.pathname;
  let to: string;
  if (path === "/gifts") to = playHref("gifts");
  else if (path === `${PLAY_ROOT}/tasks`) to = playHref("achievements");
  else if (path.startsWith(`${PLAY_ROOT}/`) && playSubpage(path) === null) to = PLAY_ROOT;
  else return null;
  return `${to}${url.search}`;
}

/** Where a subpage that is closed goes instead (replacing it in the history), or null if it is
 * open: the cycles subpage goes to the first level while the deployment or the user has cycles
 * off (.scratch/cycle-page spec「玩法页的卡」). */
export function closedPlayRedirect(subpage: PlaySubpage, { cyclesOn }: { cyclesOn: boolean }): string | null {
  return subpage === "cycles" && !cyclesOn ? PLAY_ROOT : null;
}
