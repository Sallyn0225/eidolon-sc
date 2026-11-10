/**
 * 游戏目录（ADR-0034）：用存下的登录态，在无界面的 Chromium 里打开游戏，进到 HOME 后借游戏自己的接口模块只读地查
 * 28 位偶像的卡、每张卡的剧情和标题、P デスク的衣装、相册里的活动，再从游戏已经载入的资源清单里读出哪些衣装有立绘，
 * 写成一份 JSON。`eidolon story sync` 和 `eidolon stand fetch` 在它 3 天内更新过时从这里取卡牌、剧情标题和衣装，
 * 不再依赖 ShinyColorsDB 的 API（backend/src/eidolon/game_catalog.py 读它）。
 *
 * 请求都走游戏自己的请求队列（加密、会话、版本号都由游戏处理），一个接一个，间隔至少 1 秒；只发 GET，不点卡、不读剧情。
 * 卡的剧情要一张一张查，每次最多查 --max-cards 张（新卡优先），查过的记在目录里，卡的数据没变就不再查。
 * 一个账号同时只能在一处登录：这里一登录，别处的会话就会掉线，所以用一个不拿来玩的账号。
 *
 *   node scripts/game-catalog.mts [--state <登录态>] [--out <游戏目录>] [--max-cards 40] [--if-older-than <小时>]
 *                                 [--if-signed-in]
 *   node scripts/game-catalog.mts --sign-in [--state <登录态>]
 *
 * --sign-in 打开一个有界面的浏览器，等你在里面登录游戏、点开始进到 HOME，再把登录态存下来（要在有桌面的电脑上运行，
 * 存下的文件拷到服务器上同样的位置）。登录态默认取环境变量 EIDOLON_GAME_LOGIN_PATH（没有时是 ../game-login.json），
 * 里面是账号的登录凭据，不要放进仓库或发给别人。游戏目录默认取 EIDOLON_GAME_CATALOG_PATH（没有时是
 * ../corpus/game/catalog.json）。--if-older-than：目录在这么多小时内更新过就不再查（同步脚本用它避免一周登录两次）。
 * --if-signed-in：没存过登录态时什么也不做（同步脚本用它，没用这个功能的部署照常同步）。
 *
 * 退出码：0 成功（或者目录还新，没有再查）；1 没有登录态、参数不对，或者打不开 Chromium；2 登录态失效了，要重新
 * --sign-in；3 游戏或接口出错（维护中、改版后找不到接口模块、接口没有回应），旧的目录原样保留。
 */
import { chmod, mkdir, readFile, rename, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { parseArgs } from "node:util";

import { chromium, type Browser, type BrowserContext, type Page } from "playwright";

const GAME_URL = "https://shinycolors.enza.fun/";
/** 游戏画面按这个大小铺满；标题画面的「TOUCH TO START」在下方正中。 */
const VIEWPORT = { width: 1136, height: 640 };
const START_TAP = { x: 568, y: 560 };
/** 等进到 HOME 最多多久（毫秒），--sign-in 时等人登录。 */
const HOME_TIMEOUT_MS = 180_000;
const SIGN_IN_TIMEOUT_MS = 600_000;
/** 一个接口请求最多等多久。游戏的请求出错后，之后的请求都不会再有回应，所以超时就放弃这次。 */
const REQUEST_TIMEOUT_MS = 30_000;
const REQUEST_INTERVAL_MS = 1_000;
const COSTUMES_PER_PAGE = 400; // 游戏自己也是每页 400
const CATALOG_VERSION = 1;

const { values: args } = parseArgs({
  options: {
    state: { type: "string" },
    out: { type: "string" },
    "max-cards": { type: "string", default: "40" },
    "if-older-than": { type: "string" },
    "if-signed-in": { type: "boolean", default: false },
    "sign-in": { type: "boolean", default: false },
  },
});
// `||`：.env 里留空（`EIDOLON_GAME_LOGIN_PATH=`）也用默认的位置。
const statePath = path.resolve(args.state || process.env.EIDOLON_GAME_LOGIN_PATH || "../game-login.json");
const outPath = path.resolve(args.out || process.env.EIDOLON_GAME_CATALOG_PATH || "../corpus/game/catalog.json");

/** 写进目录的卡：`episodes` 在查过之前是 null。 */
interface CatalogCard {
  id: string;
  characterId: number;
  name: string;
  kind: "produce" | "support";
  rarity: number;
  hash: string;
  openAt: number;
  eventCount: number;
  episodes: { id: string; title: string }[] | null;
}

interface Catalog {
  version: number;
  fetchedAt: string;
  characters: { id: number; name: string }[];
  cards: CatalogCard[];
  costumes: { id: string; characterId: number; name: string; group: string }[];
  stands: Record<string, string[]> | null;
  events: { id: string; name: string; episodes: { id: string; title: string }[] }[];
}

class LoginLapsed extends Error {}
class GameFailed extends Error {}

async function main(): Promise<number> {
  const maxCards = Number(args["max-cards"]);
  if (!Number.isInteger(maxCards) || maxCards < 0) {
    console.error(`--max-cards 应是不小于 0 的整数，而不是 ${args["max-cards"]}`);
    return 1;
  }
  if (args["sign-in"]) return signIn();
  const signedIn = await exists(statePath);
  if (!signedIn && args["if-signed-in"]) return 0;
  const previous = await readCatalog();
  const olderThan = args["if-older-than"] === undefined ? null : Number(args["if-older-than"]);
  if (olderThan !== null && previous) {
    const hours = (Date.now() - Date.parse(previous.fetchedAt)) / 3_600_000;
    if (hours < olderThan) {
      console.log(`游戏目录 ${hours.toFixed(1)} 小时前刚更新过，这次不查`);
      return 0;
    }
  }
  if (!signedIn) {
    console.error(`没有登录态 ${statePath}：先在有桌面的电脑上运行 npm run game:login，再把它拷到这里`);
    return 1;
  }
  const browser = await launch(true);
  if (!browser) return 1;
  try {
    const context = await browser.newContext({ storageState: statePath, viewport: VIEWPORT, locale: "ja-JP" });
    const page = await context.newPage();
    await enterHome(page, HOME_TIMEOUT_MS, true);
    const catalog = await collect(page, previous, maxCards);
    await writeAtomically(outPath, JSON.stringify(catalog, null, 1) + "\n");
    await saveState(context); // 登录凭据可能更新过
    report(catalog);
    return 0;
  } catch (error) {
    if (error instanceof LoginLapsed) {
      console.error(`登录态失效了（${error.message}）：在有桌面的电脑上重新运行 npm run game:login，再拷过来`);
      return 2;
    }
    console.error(`没能从游戏查到目录，旧的目录原样保留：${messageOf(error)}`);
    return 3;
  } finally {
    await browser.close();
  }
}

async function signIn(): Promise<number> {
  const browser = await launch(false);
  if (!browser) return 1;
  try {
    const context = await browser.newContext({ viewport: VIEWPORT, locale: "ja-JP" });
    const page = await context.newPage();
    console.log("在打开的窗口里登录游戏，点开始进到 HOME；进到 HOME 后会自动存下登录态（最多等 10 分钟）");
    await enterHome(page, SIGN_IN_TIMEOUT_MS, false);
    await page.waitForTimeout(3_000);
    await saveState(context);
    console.log(
      `登录态存到了 ${statePath}。里面是账号的登录凭据：不要放进仓库；在服务器上运行时把它拷到那边同样的位置。` +
        "这个账号别在别处玩：同一时间只能有一处登录。",
    );
    return 0;
  } catch (error) {
    console.error(`没有存下登录态：${messageOf(error)}`);
    return error instanceof LoginLapsed ? 2 : 3;
  } finally {
    await browser.close();
  }
}

async function launch(headless: boolean): Promise<Browser | null> {
  try {
    // 用 SwiftShader 画 WebGL，没有显卡的服务器上也一样；新版 Chromium 要明确允许。
    return await chromium.launch({ headless, args: ["--enable-unsafe-swiftshader", "--use-angle=swiftshader"] });
  } catch (error) {
    console.error(`打不开 Playwright 的 Chromium（先运行 npx playwright install --with-deps chromium）：${messageOf(error)}`);
    return null;
  }
}

/** 打开游戏，等它进到 HOME（地址变成 /home）。`tap` 时在标题画面替人点开始；被带去登录页就是登录态失效了。 */
async function enterHome(page: Page, timeout: number, tap: boolean): Promise<void> {
  await page.goto(GAME_URL, { waitUntil: "domcontentloaded" });
  const deadline = Date.now() + timeout;
  let waited = 0;
  while (!page.url().endsWith("/home")) {
    if (Date.now() > deadline) throw new GameFailed(`${timeout / 1000} 秒内没进到 HOME（可能在维护）`);
    await page.waitForTimeout(3_000);
    waited += 3_000;
    const host = new URL(page.url()).host;
    if (tap && host !== new URL(GAME_URL).host) throw new LoginLapsed(`被带到了 ${host}`);
    // 先等标题画面出来；进到 HOME 以后不能再点，会点到 HOME 上的按钮。
    if (tap && waited >= 6_000 && !page.url().endsWith("/home")) await page.mouse.click(START_TAP.x, START_TAP.y);
  }
  await page.waitForTimeout(2_000);
}

/** 在游戏页面里运行：找到接口模块和资源清单模块，挂在 window 上。游戏的模块加载器挂在一个名字混淆过的全局数组上，
 * 往里塞一个空块就能拿到它；再按源码里独有的字样认出这两个模块。 */
function findModules(): { api: boolean; assets: boolean } {
  const w = window as unknown as Record<string, unknown> & { __eidolon?: { api?: unknown; assets?: unknown } };
  const found: { api?: unknown; assets?: unknown } = w.__eidolon ?? {};
  for (const name of Object.getOwnPropertyNames(window)) {
    let value: unknown;
    try {
      value = w[name];
    } catch {
      continue;
    }
    if (name === "dataLayer" || !Array.isArray(value) || value.push === Array.prototype.push) continue;
    type Require = ((id: string) => Record<string, unknown>) & { m?: Record<string, unknown> };
    let require: Require | null = null;
    value.push([[`eidolon-${name}-${Date.now()}`], {}, (r: Require) => (require = r)]);
    const loader = require as Require | null;
    if (!loader?.m) continue;
    for (const id of Object.keys(loader.m)) {
      const source = Function.prototype.toString.call(loader.m[id]);
      if (!found.api && source.includes("x-sessionid") && source.includes("_encryptRequest")) found.api = loader(id).A;
      if (!found.assets && source.includes("asset-map.json") && source.includes("fetchHashMap"))
        found.assets = loader(id).A;
    }
  }
  w.__eidolon = found;
  return { api: Boolean(found.api), assets: Boolean(found.assets) };
}

/** 在游戏页面里运行：用游戏的接口模块发一个 GET，返回响应的 body。 */
function gameGet([apiPath, query, timeout]: [string, Record<string, unknown> | undefined, number]): Promise<unknown> {
  type Api = { get(p: string, q?: Record<string, unknown>): Promise<{ body: unknown }> };
  const api = (window as unknown as { __eidolon: { api: Api } }).__eidolon.api;
  return Promise.race([
    api.get(apiPath, query).then((response) => response.body),
    new Promise((_, reject) => setTimeout(() => reject(new Error(`${apiPath} 没有回应`)), timeout)),
  ]);
}

/** 在游戏页面里运行：游戏载入的资源清单里，每个衣装编号有哪几种立绘（stand、stand_costume）。 */
function standsInAssetMap(): Record<string, string[]> | null {
  type AssetMap = { getUrls(): string[] };
  const assets = (window as unknown as { __eidolon: { assets?: AssetMap } }).__eidolon.assets;
  if (!assets) return null;
  const stands: Record<string, string[]> = {};
  for (const url of assets.getUrls()) {
    const match = /^spine\/idols\/(stand|stand_costume)\/(\d+)\/data\.json$/.exec(url);
    if (match) (stands[match[2]] ??= []).push(match[1]);
  }
  return Object.keys(stands).length > 0 ? stands : null;
}

async function collect(page: Page, previous: Catalog | null, maxCards: number): Promise<Catalog> {
  const modules = await page.evaluate(findModules);
  if (!modules.api) throw new GameFailed("游戏改版了，找不到接口模块");
  if (!modules.assets) console.warn("注意：找不到资源清单模块，这次不知道哪些衣装有立绘，eidolon stand fetch 会两种都试");
  let last = 0;
  const get = async <T,>(apiPath: string, query?: Record<string, unknown>): Promise<T> => {
    const wait = last + REQUEST_INTERVAL_MS - Date.now();
    if (wait > 0) await page.waitForTimeout(wait);
    try {
      return (await page.evaluate(gameGet, [apiPath, query, REQUEST_TIMEOUT_MS] as [
        string,
        Record<string, unknown> | undefined,
        number,
      ])) as T;
    } finally {
      last = Date.now();
    }
  };

  const characters = (await get<{ id: string; name: string }[]>("characters")).map((c) => ({
    id: Number(c.id),
    name: c.name,
  }));
  const album = await get<{ gameEvents: GameEvent[] }>("album/top");
  const events = album.gameEvents.map((event) => ({
    id: String(event.id),
    name: event.name,
    episodes: (event.communications ?? []).map((e) => ({ id: String(e.id), title: e.title ?? "" })),
  }));

  const known = new Map((previous?.cards ?? []).map((card) => [card.id, card]));
  const cards: CatalogCard[] = [];
  for (const character of characters) {
    const desk = await get<{ idols: DeskIdol[] }>(`producerDesk/characters/${character.id}`);
    for (const idol of desk.idols) {
      const card: CatalogCard = {
        id: String(idol.id),
        characterId: Number(idol.characterId),
        name: idol.name,
        kind: idol.idolType === "support_idol" ? "support" : "produce",
        rarity: Number(idol.rarity),
        hash: idol.hash ?? "",
        openAt: Number(idol.openAt ?? 0),
        eventCount: Number(idol.subtotalEventCount ?? 0),
        episodes: null,
      };
      const before = known.get(card.id);
      if (card.eventCount === 0) card.episodes = [];
      else if (before?.episodes && before.hash === card.hash) card.episodes = before.episodes;
      cards.push(card);
    }
  }
  // 还没查过剧情的卡，新的先查。
  const pending = cards.filter((card) => card.episodes === null).sort((a, b) => b.openAt - a.openAt);
  for (const card of pending.slice(0, maxCards)) card.episodes = await episodesOf(get, card);

  const costumes = new Map<string, Catalog["costumes"][number]>();
  for (let pageNumber = 1; ; pageNumber++) {
    const answer = await get<{ producerDeskCostumes: DeskCostume[]; totalCount: number }>("v2/producerDesk/costumes", {
      page: pageNumber,
      per: COSTUMES_PER_PAGE,
    });
    for (const group of answer.producerDeskCostumes) {
      const variants = [group, ...(group.unitCostumes ?? []), ...(group.characterGroupCostumes ?? []), ...(group.themeGroupCostumes ?? [])];
      for (const costume of variants) {
        if (!costume.idolId || costume.idolId === "0" || costumes.has(costume.idolId)) continue;
        costumes.set(costume.idolId, {
          id: costume.idolId,
          characterId: Number(costume.characterId),
          name: costume.name,
          group: String(costume.groupId ?? group.groupId ?? ""),
        });
      }
    }
    if (pageNumber * COSTUMES_PER_PAGE >= answer.totalCount || answer.producerDeskCostumes.length === 0) break;
  }

  return {
    version: CATALOG_VERSION,
    fetchedAt: new Date().toISOString(),
    characters,
    cards,
    costumes: [...costumes.values()],
    stands: modules.assets ? await page.evaluate(standsInAssetMap) : null,
    events,
  };
}

async function episodesOf(
  get: <T>(apiPath: string, query?: Record<string, unknown>) => Promise<T>,
  card: CatalogCard,
): Promise<{ id: string; title: string }[]> {
  const pick = (events: { id: string; title?: string }[] | undefined) =>
    (events ?? []).map((e) => ({ id: String(e.id), title: e.title ?? "" }));
  if (card.kind === "produce") {
    const status = await get<{ idol: { produceIdolEvents?: GameEpisode[]; produceAfterEvents?: GameEpisode[] } }>(
      "userIdols/statusMax",
      { idolId: card.id },
    );
    return [...pick(status.idol.produceIdolEvents), ...pick(status.idol.produceAfterEvents)];
  }
  const status = await get<{ supportIdol: { produceSupportIdolEvents?: GameEpisode[] } }>("userSupportIdols/statusMax", {
    supportIdolId: card.id,
  });
  return pick(status.supportIdol.produceSupportIdolEvents);
}

interface GameEpisode {
  id: string;
  title?: string;
}
interface GameEvent {
  id: string;
  name: string;
  communications?: GameEpisode[];
}
interface DeskIdol {
  id: string;
  characterId: string;
  name: string;
  idolType: string;
  rarity: number;
  hash?: string;
  openAt?: number;
  subtotalEventCount?: number;
}
interface DeskCostume {
  idolId: string;
  characterId: string;
  name: string;
  groupId?: string;
  unitCostumes?: DeskCostume[];
  characterGroupCostumes?: DeskCostume[];
  themeGroupCostumes?: DeskCostume[];
}

function report(catalog: Catalog): void {
  const pending = catalog.cards.filter((card) => card.episodes === null).length;
  console.log(
    `游戏目录：${catalog.characters.length} 位偶像，${catalog.cards.length} 张卡` +
      (pending ? `（还有 ${pending} 张没查剧情，下次接着查）` : "") +
      `，${catalog.costumes.length} 套衣装，${catalog.events.length} 个活动` +
      (catalog.stands ? `，${Object.keys(catalog.stands).length} 个衣装编号有立绘` : "") +
      `；写进了 ${outPath}`,
  );
}

async function readCatalog(): Promise<Catalog | null> {
  try {
    const catalog = JSON.parse(await readFile(outPath, "utf8")) as Catalog;
    return catalog.version === CATALOG_VERSION ? catalog : null;
  } catch {
    return null;
  }
}

async function saveState(context: BrowserContext): Promise<void> {
  const state = await context.storageState();
  await writeAtomically(statePath, JSON.stringify(state));
  await chmod(statePath, 0o600).catch(() => {}); // Windows 上没有这种权限位
}

async function writeAtomically(file: string, content: string): Promise<void> {
  await mkdir(path.dirname(file), { recursive: true });
  const partial = `${file}.part`;
  await writeFile(partial, content, { mode: 0o600 });
  await rename(partial, file);
}

async function exists(file: string): Promise<boolean> {
  try {
    await stat(file);
    return true;
  } catch {
    return false;
  }
}

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

process.exitCode = await main();
