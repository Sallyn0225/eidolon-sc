"use client";

import { usePathname } from "next/navigation";
import { createContext, lazy, Suspense, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode, type RefObject } from "react";

import { useDirectory } from "@/components/conversations/ConversationDirectory";
import { ApiError, deleteLetter, getLetter, listLetters, markLetterPopped, markLetterRead, type Character } from "@/lib/api";
import { letterToPop, lettersBehind, type Letter, type LetterSummary } from "@/lib/letter";
import { isConversationPage } from "@/lib/navShell";

// 拆信这一层连同它的字体只在拆信时才载入。
const LetterLayer = lazy(() => import("./LetterLayer").then((m) => ({ default: m.LetterLayer })));

type LettersValue = {
  /** 所有的信，最新的在前；还没拉到时为 null。 */
  letters: LetterSummary[] | null;
  /** 写信的人，按角色 id。 */
  writers: Map<string, Character>;
  /** 拆开一封：取到信以后整屏出现她的信封；收起时信飞回 `target`（不在屏幕上时原地淡出）。 */
  open: (letter: LetterSummary, target: RefObject<HTMLElement | null>) => void;
  /** 删掉一封，连她念的语音（确认由调用的一方先问过）；删不掉时抛出，已经没有了算删掉了。 */
  remove: (letter: LetterSummary) => Promise<void>;
  /** 对话列表页首的信封键：自动弹出的信收起时飞回这里。 */
  home: RefObject<HTMLButtonElement | null>;
};

const LettersContext = createContext<LettersValue | null>(null);

/** 这次打开网站弹过信了没有。记在模块里：去一趟外壳外面（隐私政策、后台）再回来，外壳重新挂载，也不再弹。 */
let poppedThisVisit = false;

export function useLetters(): LettersValue {
  const value = useContext(LettersContext);
  if (!value) throw new Error("useLetters 要在 LetterProvider 里面用");
  return value;
}

/**
 * 信（GLOSSARY.md「信」）由导航外壳持有：所有的信的列表，和正在拆的那一封。列表载入时拉一次，切回这个标签页时、
 * 外壳每分钟拉回的最新对话列表和手上的信对不上时（`lettersBehind`）、离开对话页时再拉；拉不到就保持上一次的。
 * 拆开（信纸展开）就标读过，换一台设备也算读过。
 *
 * 自动弹出（GLOSSARY.md「没读过的信」）：进入外壳时、离开对话页时各是一个时机，到了时机就弹最早一封没读过也没弹过的
 * （`letterToPop`），收起时飞回页首信封键；在对话页上、通话中不弹，时机留着，等离开、挂断再弹。每次打开网站最多弹一封。
 * 信封一出现就标弹过，跳过的不再弹，换设备也一样。
 */
export function LetterProvider({ children }: { children: ReactNode }) {
  const { characters, latest, call } = useDirectory();
  const pathname = usePathname();
  const [letters, setLetters] = useState<LetterSummary[] | null>(null);
  const [opened, setOpened] = useState<{ letter: Letter; target: RefObject<HTMLElement | null> } | null>(null);
  const opening = useRef(false);
  const home = useRef<HTMLButtonElement>(null);
  // 给回调在拉回列表、换页这一刻读。
  const lettersRef = useRef<LetterSummary[] | null>(null);
  const where = { onConversationPage: isConversationPage(pathname), inCall: call !== null };
  const whereRef = useRef(where);
  const writers = useMemo(() => new Map((characters ?? []).map((c) => [c.id, c])), [characters]);
  const writersRef = useRef(writers);
  // 写在别的 effect 前面：它们这一次读到的就是这一次渲染的。
  useEffect(() => {
    whereRef.current = where;
    writersRef.current = writers;
  });
  // 等着弹的时机（进入外壳时就有一个）。
  const popMoment = useRef(true);

  const putLetters = useCallback((next: LetterSummary[] | ((all: LetterSummary[] | null) => LetterSummary[] | null)) => {
    const value = typeof next === "function" ? next(lettersRef.current) : next;
    lettersRef.current = value;
    setLetters(value);
  }, []);

  const show = useCallback(
    (summary: LetterSummary, target: RefObject<HTMLElement | null>, popped: boolean) => {
      if (opening.current) return;
      opening.current = true;
      getLetter(summary.id).then(
        (letter) => {
          setOpened({ letter, target });
          if (!popped) return;
          putLetters((all) => all && all.map((l) => (l.id === summary.id ? { ...l, popped: true } : l)));
          markLetterPopped(summary.id).catch(() => {}); // 没记上的话，下次打开网站还会再弹一次
        },
        () => {
          opening.current = false; // 取不到就不拆，再点一次再取
        },
      );
    },
    [putLetters],
  );

  /** 到了时机：不在对话页上、没在通话就弹（时机用掉，没有要弹的也用掉）；否则时机留着。信和角色都载入了才看。 */
  const popIfDue = useCallback(
    (all: LetterSummary[] | null) => {
      if (all === null || writersRef.current.size === 0) return;
      if (!popMoment.current || poppedThisVisit || opening.current) return;
      const now = whereRef.current;
      if (now.onConversationPage || now.inCall) return;
      popMoment.current = false;
      // 写信的人不在角色配置里的拆不开，不弹。
      const letter = letterToPop(all.filter((l) => writersRef.current.has(l.character_id)), now);
      if (!letter) return;
      poppedThisVisit = true;
      show(letter, home, true);
    },
    [show],
  );

  const load = useCallback(
    () =>
      listLetters().then(
        (all) => {
          putLetters(all);
          return all;
        },
        () => lettersRef.current, // 信不是要紧的事，拉不到就保持上一次的
      ),
    [putLetters],
  );

  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === "visible") load();
    };
    load().then(popIfDue);
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, [load, popIfDue]);

  // 离开对话页是一个时机：先拉一遍（在那一页上时可能刚写好一封），再看弹不弹。挂断了、角色载入了，等着的时机就看弹不弹。
  const wasOnConversationPage = useRef(where.onConversationPage);
  useEffect(() => {
    const left = wasOnConversationPage.current && !where.onConversationPage;
    wasOnConversationPage.current = where.onConversationPage;
    if (left) {
      popMoment.current = true;
      load().then(popIfDue);
    } else {
      popIfDue(lettersRef.current);
    }
  }, [where.onConversationPage, where.inCall, writers, load, popIfDue]);

  // 外壳每分钟拉回的最新对话列表说某位有没读过的信、手上的信里却没有（或者反过来）：重新拉，页首的点和她那一行的小信封跟着变。
  useEffect(() => {
    if (lettersBehind(lettersRef.current, latest)) load();
  }, [latest, load]);

  const open = useCallback(
    (summary: LetterSummary, target: RefObject<HTMLElement | null>) => show(summary, target, false),
    [show],
  );

  const remove = useCallback(
    async (letter: LetterSummary) => {
      try {
        await deleteLetter(letter.id);
      } catch (e) {
        if (!(e instanceof ApiError && e.status === 404)) throw e; // 已经删掉了
      }
      putLetters((all) => all && all.filter((l) => l.id !== letter.id));
    },
    [putLetters],
  );

  const onRead = useCallback(() => {
    if (!opened) return;
    const id = opened.letter.id;
    putLetters((all) => all && all.map((l) => (l.id === id ? { ...l, read: true } : l)));
    markLetterRead(id).catch(() => {}); // 没记上的话，下次拉列表时还是没读过
  }, [opened, putLetters]);

  const onClosed = useCallback(() => {
    opening.current = false;
    setOpened(null);
  }, []);

  const writer = opened ? writers.get(opened.letter.character_id) : undefined;
  const value = useMemo(() => ({ letters, writers, open, remove, home }), [letters, writers, open, remove]);

  return (
    <LettersContext.Provider value={value}>
      {children}
      {opened && writer && (
        <Suspense fallback={null}>
          <LetterLayer
            key={opened.letter.id}
            writer={writer}
            letter={opened.letter}
            target={opened.target}
            onRead={onRead}
            onClosed={onClosed}
          />
        </Suspense>
      )}
    </LettersContext.Provider>
  );
}
