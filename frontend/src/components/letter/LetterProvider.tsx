"use client";

// PROTOTYPE, throwaway（prototype/letters-ui 分支）：信箱界面原型的假数据源。
// 由导航外壳持有：一组假信（prototype/prototypeLetters），读没读过存在这台设备上（eidolon.prototypeLetters.*）；
// 进外壳时有没读过的信，就弹最早一封的信封（每次载入只弹一次，跳过的以后不再弹）；三种信箱方案（A/B/C）由切换条切。

import { usePathname } from "next/navigation";
import {
  createContext,
  lazy,
  Suspense,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react";

import { useDirectory } from "@/components/conversations/ConversationDirectory";
import type { Character } from "@/lib/api";
import type { Letter } from "@/lib/letter";
import { showsNav } from "@/lib/navShell";

import { PrototypeSwitcher } from "./prototype/PrototypeSwitcher";
import { PROTOTYPE_LETTERS, SHOWS_PROTOTYPE, VARIANTS, type PrototypeLetter, type Variant } from "./prototype/prototypeLetters";

const LetterLayer = lazy(() => import("./LetterLayer").then((m) => ({ default: m.LetterLayer })));

/** 信箱里的一封：假信加上写信的人。 */
export type BoxLetter = PrototypeLetter & { writer: Character; isUnread: boolean };

type LetterContextValue = {
  variant: Variant;
  setVariant: (variant: Variant) => void;
  /** 信箱里的信，最新的在前；角色还没读到时是空的。 */
  letters: BoxLetter[];
  unreadCount: number;
  /** 拆开一封：信收起时飞回 `targetKey` 登记的那个元素（不在屏幕上时原地淡出）。 */
  open: (id: string, targetKey: string) => void;
  /** 登记信收起时飞回去的元素。 */
  target: (key: string) => (el: HTMLElement | null) => void;
  /** 切换条的「重置读过」：回到一开始的读没读过，再弹一次。 */
  reset: () => void;
};

const LetterContext = createContext<LetterContextValue | null>(null);

export function useLetters(): LetterContextValue | null {
  return useContext(LetterContext);
}

const READ_KEY = "eidolon.prototypeLetters.read";
const SKIPPED_KEY = "eidolon.prototypeLetters.skipped";
const VARIANT_KEY = "eidolon.prototypeLetters.variant";

function readSet(key: string, fallback: string[]): Set<string> {
  try {
    const raw = localStorage.getItem(key);
    return new Set(raw ? (JSON.parse(raw) as string[]) : fallback);
  } catch {
    return new Set(fallback);
  }
}

function writeSet(key: string, set: Set<string>) {
  try {
    localStorage.setItem(key, JSON.stringify([...set]));
  } catch {
    // 原型：存不了就算了。
  }
}

const READ_AT_START = PROTOTYPE_LETTERS.filter((l) => l.readAtStart).map((l) => l.id);

/** 每种方案下，自己弹出来的信收起时飞去哪：A 页首信封键，B 墙上那一枚，C 她对话页页首的信封键。 */
function autoTarget(variant: Variant, letter: PrototypeLetter): string {
  if (variant === "A") return "box";
  if (variant === "B") return `tile:${letter.id}`;
  return `her:${letter.characterId}`;
}

export function LetterProvider({ children }: { children: ReactNode }) {
  const { characters, call } = useDirectory();
  const pathname = usePathname();
  const [variant, setVariantState] = useState<Variant>("A");
  const [read, setRead] = useState<Set<string>>(() => new Set(READ_AT_START));
  const [skipped, setSkipped] = useState<Set<string>>(() => new Set());
  const [opened, setOpened] = useState<{ id: string; targetKey: string } | null>(null);
  const [popAttempt, setPopAttempt] = useState(0);
  const popped = useRef(-1);
  const targets = useRef(new Map<string, HTMLElement>());
  const data = useRef<Record<string, Letter> | null>(null);
  const [hasData, setHasData] = useState(false);

  // 载入：读没读过、方案（网址的 ?letters= 优先），正文和音频。
  useEffect(() => {
    setRead(readSet(READ_KEY, READ_AT_START));
    setSkipped(readSet(SKIPPED_KEY, []));
    const asked = new URLSearchParams(window.location.search).get("letters");
    let stored: string | null = null;
    try {
      stored = localStorage.getItem(VARIANT_KEY);
    } catch {
      // 原型：存不了就用默认。
    }
    const known = (v: string | null): v is Variant => VARIANTS.some((x) => x.key === v);
    if (known(asked)) setVariantState(asked);
    else if (known(stored)) setVariantState(stored);
    import("./letters.json").then((m) => {
      data.current = m.default as unknown as Record<string, Letter>;
      setHasData(true);
    });
  }, []);

  const setVariant = useCallback((next: Variant) => {
    setVariantState(next);
    try {
      localStorage.setItem(VARIANT_KEY, next);
    } catch {
      // 原型：存不了就算了。
    }
    const url = new URL(window.location.href);
    url.searchParams.set("letters", next);
    window.history.replaceState(window.history.state, "", url);
  }, []);

  const letters = useMemo<BoxLetter[]>(() => {
    const byId = new Map((characters ?? []).map((c) => [c.id, c]));
    return PROTOTYPE_LETTERS.flatMap((l) => {
      const writer = byId.get(l.characterId);
      return writer ? [{ ...l, writer, isUnread: !read.has(l.id) }] : [];
    }).reverse();
  }, [characters, read]);
  const unreadCount = letters.filter((l) => l.isUnread).length;

  const open = useCallback((id: string, targetKey: string) => setOpened({ id, targetKey }), []);

  const target = useCallback(
    (key: string) => (el: HTMLElement | null) => {
      if (el) targets.current.set(key, el);
      else if (targets.current.get(key)) targets.current.delete(key);
    },
    [],
  );

  // 进外壳时弹最早一封没读过、也没跳过的信。通话中、酒吧页上不弹，等到能弹的那一页再弹。
  const isBlocked = call !== null || !showsNav(pathname);
  useEffect(() => {
    if (!hasData || letters.length === 0 || isBlocked || opened || popped.current === popAttempt) return;
    popped.current = popAttempt;
    const first = [...letters].reverse().find((l) => l.isUnread && !skipped.has(l.id));
    if (first) setOpened({ id: first.id, targetKey: autoTarget(variant, first) });
  }, [hasData, letters, isBlocked, opened, popAttempt, skipped, variant]);

  const reset = useCallback(() => {
    const fresh = new Set(READ_AT_START);
    setRead(fresh);
    writeSet(READ_KEY, fresh);
    setSkipped(new Set());
    writeSet(SKIPPED_KEY, new Set());
    setPopAttempt((n) => n + 1);
  }, []);

  const shown = opened ? letters.find((l) => l.id === opened.id) : undefined;
  const wasOpened = useRef(false);
  const onOpened = useCallback(() => {
    if (!opened) return;
    wasOpened.current = true;
    setRead((prev) => {
      const next = new Set(prev).add(opened.id);
      writeSet(READ_KEY, next);
      return next;
    });
  }, [opened]);
  const onClosed = useCallback(() => {
    if (opened && !wasOpened.current) {
      // 没拆就跳过：还算没读过，以后不再自己弹出。
      setSkipped((prev) => {
        const next = new Set(prev).add(opened.id);
        writeSet(SKIPPED_KEY, next);
        return next;
      });
    }
    wasOpened.current = false;
    setOpened(null);
  }, [opened]);

  const targetRef = useMemo<RefObject<HTMLElement | null>>(() => {
    const key = opened?.targetKey ?? "";
    return {
      get current() {
        return targets.current.get(key) ?? null;
      },
    } as RefObject<HTMLElement | null>;
  }, [opened]);

  return (
    <LetterContext.Provider value={{ variant, setVariant, letters, unreadCount, open, target, reset }}>
      {children}
      {shown && data.current?.[shown.characterId] && (
        <Suspense fallback={null}>
          <LetterLayer
            key={shown.id}
            writer={shown.writer}
            letter={data.current[shown.characterId]}
            target={targetRef}
            onOpened={onOpened}
            onClosed={onClosed}
          />
        </Suspense>
      )}
      {SHOWS_PROTOTYPE && <PrototypeSwitcher variant={variant} onChange={setVariant} onReset={reset} />}
    </LetterContext.Provider>
  );
}
