"use client";

// PROTOTYPE（.scratch/moments/issues/05-entry-and-page-prototype.md）：朋友圈页面的假数据和内存状态，扔掉用的。
// 赞和评论带「露出时刻」（相对打开页面的秒数），到点才出现，模拟「陆续露出来」；制作人评论后她的回复 20 秒后露出。
// 入口（玩法卡 / 导航第四项）和「有没有新动态」存在 localStorage，换页不丢，切换条上能重置。

import { useEffect, useState, useSyncExternalStore } from "react";

export type Weather = "sunny" | "cloudy" | "rain" | "clear-night" | "snow";

export type Comment = {
  id: string;
  /** 角色 id；"producer" 是制作人。 */
  by: string;
  text: string;
  /** 回复谁（只有她回制作人时有）。 */
  to?: string;
  /** 相对打开页面的秒数，负数是早就露出了。 */
  revealAt: number;
};

export type Post = {
  id: string;
  by: string;
  text: string | null;
  /** 配图：真图的地址，或占位块上的说明。 */
  image: { src: string } | { placeholder: string } | null;
  place: { name: string; lat: number; lon: number };
  weather: { kind: Weather; temp: number } | null;
  /** 几分钟前发的。 */
  minutesAgo: number;
  likes: { by: string; revealAt: number }[];
  comments: Comment[];
};

const POSTS: Post[] = [
  {
    id: "p1",
    by: "meguru",
    text: "今天的拍摄提前结束了！回家路上看到超大的晚霞，忍不住在桥上停下来看了好久～明天也要加油哦！",
    image: { placeholder: "风景：河边的晚霞（待配图实测）" },
    place: { name: "二子玉川河川敷", lat: 35.6117, lon: 139.6268 },
    weather: { kind: "sunny", temp: 17 },
    minutesAgo: 12,
    likes: [
      { by: "mano", revealAt: -60 },
      { by: "hiori", revealAt: 8 },
      { by: "kaho", revealAt: 25 },
    ],
    comments: [
      { id: "c1", by: "mano", text: "好漂亮…！下次也想一起看呢。", revealAt: -30 },
      { id: "c2", by: "hiori", text: "别光顾着看，记得早点休息。", revealAt: 15 },
    ],
  },
  {
    id: "p2",
    by: "chiyuki",
    text: "早上在常去的咖啡店。新出的南瓜拿铁，有一点点秋天的味道。",
    image: { src: "/prototype-moments/photo0.webp" },
    place: { name: "代官山 蔦屋書店", lat: 35.6488, lon: 139.6997 },
    weather: { kind: "cloudy", temp: 14 },
    minutesAgo: 95,
    likes: [
      { by: "amana", revealAt: -3000 },
      { by: "tenka", revealAt: -2800 },
      { by: "kogane", revealAt: -900 },
      { by: "sakuya", revealAt: -400 },
    ],
    comments: [
      { id: "c3", by: "amana", text: "千雪姐今天的毛衣好可爱☆ 下次带我们去！", revealAt: -2900 },
      { id: "c4", by: "tenka", text: "甜花…也想喝…", revealAt: -2500 },
      { id: "c5", by: "producer", text: "看起来很好喝。", revealAt: -2000 },
      { id: "c6", by: "chiyuki", to: "producer", text: "制作人也来尝尝吧，我请客哦。", revealAt: -1500 },
    ],
  },
  {
    id: "p3",
    by: "madoka",
    text: "收工。",
    image: null,
    place: { name: "赤坂", lat: 35.6764, lon: 139.7365 },
    weather: { kind: "clear-night", temp: 12 },
    minutesAgo: 60 * 5,
    likes: [
      { by: "koito", revealAt: -9000 },
      { by: "hinana", revealAt: -8000 },
    ],
    comments: [{ id: "c7", by: "hinana", text: "小円～一起吃宵夜吗～♪", revealAt: -8500 }],
  },
  {
    id: "p4",
    by: "mano",
    text: "休息日的早上，在家慢慢喝了杯红茶。下午和小灯、小巡约好去看银杏 ♪",
    image: { src: "/prototype-moments/photo1.webp" },
    place: { name: "吉祥寺", lat: 35.7033, lon: 139.5797 },
    weather: { kind: "sunny", temp: 19 },
    minutesAgo: 60 * 26,
    likes: [
      { by: "meguru", revealAt: -90000 },
      { by: "hiori", revealAt: -89000 },
    ],
    comments: [
      { id: "c8", by: "meguru", text: "因为太开心了嘛！！", revealAt: -90000 },
      { id: "c9", by: "hiori", text: "……下次请等一下我们。", revealAt: -88000 },
    ],
  },
  {
    id: "p5",
    by: "kogane",
    text: "长崎老家寄来的蛋糕到了！！大家明天来事务所一起吃～",
    image: { placeholder: "物品和食物：桌上的长崎蛋糕（待配图实测）" },
    place: { name: "283 事务所", lat: 35.6595, lon: 139.7005 },
    weather: { kind: "rain", temp: 15 },
    minutesAgo: 60 * 30,
    likes: [
      { by: "mamimi", revealAt: -100000 },
      { by: "sakuya", revealAt: -99000 },
      { by: "yuika", revealAt: -98000 },
      { by: "kiriko", revealAt: -97000 },
      { by: "chiyoko", revealAt: -96000 },
    ],
    comments: [
      { id: "c10", by: "chiyoko", text: "我会准时到的！！", revealAt: -99000 },
      { id: "c11", by: "mamimi", text: "那就勉强去一下吧～", revealAt: -98500 },
      { id: "c12", by: "sakuya", text: "替我向恋钟的家人道谢。", revealAt: -97500 },
    ],
  },
  {
    id: "p6",
    by: "hana",
    text: null,
    image: { src: "/prototype-moments/photo2.webp" },
    place: { name: "代々木公園", lat: 35.6717, lon: 139.6949 },
    weather: { kind: "sunny", temp: 16 },
    minutesAgo: 60 * 50,
    likes: [{ by: "luca", revealAt: -180000 }],
    comments: [],
  },
  {
    id: "p7",
    by: "meguru",
    text: "早安！！今天也是好天气～",
    image: { src: "/prototype-moments/photo4.webp" },
    place: { name: "八宮家附近的商店街", lat: 35.7062, lon: 139.6656 },
    weather: { kind: "sunny", temp: 15 },
    minutesAgo: 60 * 52,
    likes: [{ by: "mano", revealAt: -185000 }],
    comments: [],
  },
];

type State = {
  posts: Post[];
  producerLikes: Set<string>;
  /** 打开页面的时刻（毫秒），revealAt 相对它算。 */
  openedAt: number;
};

let state: State = { posts: POSTS, producerLikes: new Set(), openedAt: Date.now() };
const listeners = new Set<() => void>();
const emit = () => listeners.forEach((listener) => listener());

export function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export const snapshot = () => state;

export function useMoments() {
  return useSyncExternalStore(subscribe, snapshot, snapshot);
}

/** 每秒刷新一次「现在」，到点的赞和评论露出来。 */
export function useNowSeconds(): number {
  const [now, setNow] = useState(() => (Date.now() - state.openedAt) / 1000);
  useEffect(() => {
    const timer = setInterval(() => setNow((Date.now() - state.openedAt) / 1000), 1000);
    return () => clearInterval(timer);
  }, []);
  return now;
}

export function toggleLike(postId: string) {
  const likes = new Set(state.producerLikes);
  if (likes.has(postId)) likes.delete(postId);
  else likes.add(postId);
  state = { ...state, producerLikes: likes };
  emit();
}

/** 制作人评论：马上露出；她的回复 20 秒后露出（真东西里是「过一阵」）。 */
export function addComment(postId: string, text: string) {
  const now = (Date.now() - state.openedAt) / 1000;
  state = {
    ...state,
    posts: state.posts.map((post) => {
      if (post.id !== postId) return post;
      const id = `${post.id}-${post.comments.length}`;
      return {
        ...post,
        comments: [
          ...post.comments,
          { id: `${id}-p`, by: "producer", text, revealAt: now - 1 },
          { id: `${id}-r`, by: post.by, to: "producer", text: replyFor(post.by), revealAt: now + 20 },
        ],
      };
    }),
  };
  emit();
}

function replyFor(by: string): string {
  const replies: Record<string, string> = {
    meguru: "嘿嘿，被制作人看到了！下次一起去吧！",
    mano: "谢谢您…！看到制作人的留言好开心。",
    chiyuki: "呵呵，被您发现了呢。",
    madoka: "……您还没睡吗。",
    kogane: "制作人也要来吃哦！给你留最大的一块～",
  };
  return replies[by] ?? "谢谢制作人～";
}

/** 这条现在露出的赞和评论。 */
export function revealed(post: Post, now: number) {
  return {
    likes: post.likes.filter((like) => like.revealAt <= now),
    comments: post.comments.filter((comment) => comment.revealAt <= now),
    /** 制作人评论了、她的回复还没露出。 */
    pendingReply: post.comments.some((c) => c.to === "producer" && c.revealAt > now),
  };
}

export function timeText(minutesAgo: number): string {
  if (minutesAgo < 60) return `${minutesAgo} 分钟前`;
  if (minutesAgo < 60 * 24) return `${Math.floor(minutesAgo / 60)} 小时前`;
  if (minutesAgo < 60 * 48) return "昨天";
  return `${Math.floor(minutesAgo / 60 / 24)} 天前`;
}

export function osmHref({ lat, lon }: { lat: number; lon: number }): string {
  return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=16/${lat}/${lon}`;
}

// ---- 入口和新动态（跨页面，存 localStorage）----

export type Entry = "card" | "nav";
const ENTRY_KEY = "prototype-moments-entry";
const SEEN_KEY = "prototype-moments-seen";
const prefListeners = new Set<() => void>();

function subscribePrefs(listener: () => void) {
  prefListeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    prefListeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

export function useEntry(): Entry {
  return useSyncExternalStore(
    subscribePrefs,
    () => (localStorage.getItem(ENTRY_KEY) === "nav" ? "nav" : "card"),
    () => "card",
  );
}

export function setEntry(entry: Entry) {
  localStorage.setItem(ENTRY_KEY, entry);
  prefListeners.forEach((listener) => listener());
}

/** 有没看过的新动态（原型里：没进过朋友圈页就算有）。 */
export function useHasNew(): boolean {
  return useSyncExternalStore(
    subscribePrefs,
    () => localStorage.getItem(SEEN_KEY) !== "1",
    () => false,
  );
}

export function markSeen() {
  localStorage.setItem(SEEN_KEY, "1");
  prefListeners.forEach((listener) => listener());
}

export function resetNew() {
  localStorage.removeItem(SEEN_KEY);
  prefListeners.forEach((listener) => listener());
}
