"use client";

import { Klee_One } from "next/font/google";
import { useCallback, useEffect, useMemo, useRef, useState, type RefObject } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { copy } from "@/i18n";
import type { Character } from "@/lib/api";
import {
  VOICE_WAIT_MS,
  finishesAt,
  partsOf,
  signsAt,
  tick,
  timerClock,
  voiceClock,
  written,
  type Letter,
  type LetterClock,
  type Part,
} from "@/lib/letter";
import { cn } from "@/lib/utils";
import { letterVars } from "@/theme/herVars";
import { LetterMutedIcon, LetterSoundIcon } from "@/theme/icons";

import { LetterSound } from "./letterSound";
import { Seal } from "./Seal";

// 信上她的字：Klee One（SIL OFL 1.1），构建时下载、自托管、按 unicode-range 切片。不预载：只有拆信的人才要，
// 信封出来时开始取，拆开之前基本就到了；没到之前字先不显示（display: block），免得写到一半换字体。
const klee = Klee_One({
  weight: "600",
  subsets: ["latin"],
  variable: "--font-klee",
  display: "block",
  preload: false,
  adjustFontFallback: false,
});

const t = copy.letter;

/** 信封 → 拆开（封口翻开、信封落下）→ 信纸上一个字一个字写、她念 → 收起（信纸收回信封、信封飞回存放它的键）。 */
type Stage = "envelope" | "opening" | "letter" | "closing";

/** 拆开的动画多久以后换成信纸：封口翻开，信封落下。 */
const OPENING_MS = 800;
/** 用户自己滚过信纸后，这么久之内不自动跟着写到的地方滚。 */
const HANDS_OFF_MS = 4000;
/** 收起时她的声音和配乐淡出多久。 */
const FADE_OUT_MS = 600;

type Props = {
  writer: Character;
  letter: Letter;
  /** 存放这封信的键：收起时信封飞进它里面；它不在屏幕上时信封原地淡出。 */
  target: RefObject<HTMLElement | null>;
  /** 信纸展开了：算读过。 */
  onRead: () => void;
  /** 收起的动画放完了。 */
  onClosed: () => void;
};

/**
 * 拆信这一层（GLOSSARY.md「信」，lib/letter），沿用停服前「她的信」的做法：整屏压暗，中间是她的信封，点了拆开。
 * 信纸上的字跟着她念到哪里写到哪里，每段写完，下面淡出这段的中文字幕；念完以后，信末写上她的签名。
 * 右上角是静音和跳过；签完名信末出现「收好」，点了信收起来、飞回存放它的键。系统要求减少动态效果时，拆开就是整封信，声音照放。
 * 时间轴（lib/letter 的 `partsOf`）按每块语音解码出来的时长排，信纸展开后先等语音（最多 `VOICE_WAIT_MS`），
 * 没有语音、取不到或解码不了时按字数估；字跟着音频时钟写，音频时钟停住时改按时钟写并停掉声音（`tick`）。
 * 底下铺着这个场合的配乐，高潮落在签名上（`musicPlan`）；取不到时安静地没有配乐。静音键同时静掉她的声音和配乐。
 */
export function LetterLayer({ writer, letter, target, onRead, onClosed }: Props) {
  const isReducedMotion = useMediaQuery("(prefers-reduced-motion: reduce)", false);
  // 每块语音的时长：undefined 是还在等（取、解码；只有配乐时等音频的上下文跑起来），null 是没有她的声音、按字数估。
  const hasSound = letter.voice !== null || letter.music !== null;
  const [durations, setDurations] = useState<number[] | null | undefined>(hasSound ? undefined : null);
  const parts = useMemo(() => partsOf(letter, durations), [letter, durations]);
  const total = useMemo(() => parts.reduce((n, p) => n + p.chars.length, 0), [parts]);
  const finish = finishesAt(parts);
  const signing = signsAt(parts);
  const [stage, setStage] = useState<Stage>("envelope");
  const [count, setCount] = useState(0);
  const [isSigned, setSigned] = useState(false);
  const [isDone, setDone] = useState(false);
  // 出不出静音键：她的声音或者配乐放起来了。
  const [isAudible, setAudible] = useState(false);
  const [isMuted, setMuted] = useState(false);
  const sound = useRef<LetterSound | null>(null);
  const clock = useRef<LetterClock | null>(null);
  const popup = useRef<HTMLDivElement>(null);
  const envelope = useRef<HTMLButtonElement>(null);
  const backdrop = useRef<HTMLDivElement>(null);
  const sheet = useRef<HTMLDivElement>(null);
  const paper = useRef<HTMLDivElement>(null);
  const done = useRef<HTMLButtonElement>(null);
  const handsOffSince = useRef(-Infinity);
  const wasRead = useRef(false);

  // 信封一出来就开始取字体、她的声音和配乐。
  useEffect(() => {
    document.fonts?.load(`600 1em ${klee.style.fontFamily}`).catch(() => {});
  }, []);
  useEffect(() => {
    if (!letter.voice && !letter.music) return;
    const s = new LetterSound(letter.voice, letter.music);
    sound.current = s;
    return () => {
      s.close();
      if (sound.current === s) sound.current = null;
    };
  }, [letter.voice, letter.music]);

  // 拆开：声音要在这一下点击里解锁，浏览器才让它出声。语音最多等 VOICE_WAIT_MS，等不到就按字数估。
  function open() {
    if (stage !== "envelope") return;
    const s = sound.current;
    if (s) void s.unlock(VOICE_WAIT_MS).then(setDurations);
    else setDurations(null);
    setStage("opening");
  }

  useEffect(() => {
    if (stage !== "opening") return;
    const id = window.setTimeout(() => setStage("letter"), isReducedMotion ? 0 : OPENING_MS);
    return () => window.clearTimeout(id);
  }, [stage, isReducedMotion]);

  // 信纸展开：算读过。减少动态效果时整封信一下子出来。
  useEffect(() => {
    if (stage !== "letter") return;
    if (!wasRead.current) {
      wasRead.current = true;
      onRead();
    }
    paper.current?.focus({ preventScroll: true });
    if (isReducedMotion) {
      setCount(total);
      setSigned(true);
      setDone(true);
    }
  }, [stage, isReducedMotion, total, onRead]);

  // 开口：信纸展开、语音也定了（解码好了，或者不要了）以后，按时间轴把每块语音和配乐排上音频时钟，只排一次。
  // 有她的声音、或者配乐放起来了，才出静音键。
  useEffect(() => {
    if (stage !== "letter" || durations === undefined || clock.current) return;
    const now = performance.now();
    const s = sound.current;
    const base = s?.play(durations ? parts.map((p) => p.start) : null, signing, finish) ?? null;
    clock.current = base === null ? timerClock(now) : voiceClock(base, now);
    if (base === null) {
      s?.close();
      return;
    }
    if (durations) setAudible(true);
    void s?.musicPlaying.then((isPlaying) => {
      if (isPlaying && clock.current?.by === "voice") setAudible(true);
    });
  }, [stage, durations, parts, signing, finish]);

  // 写：每一帧看写到第几秒、该有几个字；字数变了才重画。音频时钟停住时改按时钟写，停掉声音。
  useEffect(() => {
    if (stage !== "letter" || durations === undefined || isReducedMotion) return;
    let frame = 0;
    const step = () => {
      const current = clock.current;
      if (!current) {
        frame = requestAnimationFrame(step);
        return;
      }
      const next = tick(current, performance.now(), sound.current?.time() ?? 0);
      if (current.by === "voice" && next.clock.by === "timer") {
        sound.current?.stop();
        setAudible(false);
      }
      clock.current = next.clock;
      setCount(parts.reduce((n, p) => n + written(p, next.at), 0));
      if (next.at >= signing) setSigned(true);
      if (next.at >= finish) {
        setDone(true);
        return;
      }
      frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [stage, durations, isReducedMotion, parts, signing, finish]);

  // 跟着写到的地方滚：写到的字落到信纸下面四分之一时，把它滚回四成高的地方。用户刚自己滚过就不动。
  useEffect(() => {
    const box = paper.current;
    if (!box || count === 0 || isDone || performance.now() - handsOffSince.current < HANDS_OFF_MS) return;
    const char = box.querySelector<HTMLElement>(`[data-c="${count - 1}"]`);
    if (!char) return;
    const bottom = char.offsetTop + char.offsetHeight;
    if (bottom > box.scrollTop + box.clientHeight * 0.75) {
      box.scrollTo({ top: bottom - box.clientHeight * 0.4, behavior: isReducedMotion ? "auto" : "smooth" });
    }
  }, [count, isDone, isReducedMotion]);

  useEffect(() => {
    if (!isDone || stage !== "letter") return;
    done.current?.focus({ preventScroll: true });
    done.current?.scrollIntoView({ block: "nearest", behavior: isReducedMotion ? "auto" : "smooth" });
  }, [isDone, stage, isReducedMotion]);

  const close = useCallback(() => setStage((s) => (s === "closing" ? s : "closing")), []);

  // 收起：信纸收回、信封合上，信封飞进存放它的键（它不在屏幕上时原地淡出），然后告诉外面放完了。
  useEffect(() => {
    if (stage !== "closing") return;
    let isCancelled = false;
    const ms = (n: number) => (isReducedMotion ? Math.min(n, 150) : n);
    const play = async (el: Element | null, frames: Keyframe[], duration: number, easing = "ease-in-out") => {
      if (!el) return;
      try {
        await el.animate(frames, { duration: ms(duration), easing, fill: "forwards" }).finished;
      } catch {
        // 元素被卸掉、动画被取消：照样往下走。
      }
    };
    sound.current?.fadeOut(ms(FADE_OUT_MS));
    (async () => {
      if (wasRead.current) {
        await play(sheet.current, [{ opacity: 1, transform: "none" }, { opacity: 0, transform: "translateY(2rem) scale(0.92)" }], 320, "ease-in");
        await play(envelope.current, [{ opacity: 0, transform: "scale(0.9)" }, { opacity: 1, transform: "none" }], 260, "ease-out");
      }
      const to = target.current;
      const from = envelope.current;
      if (!isReducedMotion && to && from && isOnScreen(to)) {
        const a = from.getBoundingClientRect();
        const b = to.getBoundingClientRect();
        const dx = b.left + b.width / 2 - (a.left + a.width / 2);
        const dy = b.top + b.height / 2 - (a.top + a.height / 2);
        void play(backdrop.current, [{ opacity: 1 }, { opacity: 0 }], 650, "ease-in");
        await play(
          from,
          [
            { opacity: 1, transform: "none" },
            { opacity: 0.5, transform: `translate(${dx}px, ${dy}px) scale(${b.width / a.width})` },
          ],
          650,
          "cubic-bezier(0.55, 0, 0.7, 0.4)",
        );
        to.animate([{ transform: "scale(1)" }, { transform: "scale(1.3)" }, { transform: "scale(1)" }], {
          duration: 380,
          easing: "ease-out",
        });
      } else {
        void play(backdrop.current, [{ opacity: 1 }, { opacity: 0 }], 300);
        await play(from, [{ opacity: 1, transform: "none" }, { opacity: 0, transform: "scale(0.85)" }], 300);
      }
      if (!isCancelled) onClosed();
    })();
    return () => {
      isCancelled = true;
    };
  }, [stage, isReducedMotion, target, onClosed]);

  function toggleMute() {
    sound.current?.setMuted(!isMuted);
    setMuted(!isMuted);
  }

  const handsOff = () => {
    handsOffSince.current = performance.now();
  };

  const isReading = stage === "letter" || (stage === "closing" && wasRead.current);
  const showsEnvelope = stage === "envelope" || stage === "opening" || stage === "closing";

  let offset = 0;
  return (
    <Dialog open onOpenChange={(open) => !open && close()} disablePointerDismissal>
      {/* 打开时聚焦整层，不聚焦信封：信封上一圈焦点环太显眼；用键盘的人按 Tab 就到信封上。 */}
      <DialogContent
        ref={popup}
        variant="letter"
        showCloseButton={false}
        initialFocus={popup}
        className={cn("letter-layer", klee.variable)}
        style={letterVars(writer.color)}
      >
        <DialogTitle className="sr-only">{t.title(writer.name)}</DialogTitle>
        <div ref={backdrop} className="absolute inset-0 bg-black/75 backdrop-blur-sm animate-in fade-in-0 duration-500" />

        {showsEnvelope && (
          <div className="absolute inset-0 flex items-center justify-center p-6">
            <button
              ref={envelope}
              type="button"
              aria-label={t.open(writer.name)}
              onClick={open}
              disabled={stage !== "envelope"}
              className={cn(
                "group flex flex-col items-center gap-5 rounded-lg outline-none focus-visible:ring-3 focus-visible:ring-white/60",
                stage === "envelope" && "animate-in fade-in-0 slide-in-from-bottom-6 duration-700",
                stage === "opening" && "translate-y-1/4 opacity-0 transition-[translate,opacity] delay-300 duration-500 ease-in",
                stage === "closing" && wasRead.current && "opacity-0",
              )}
            >
              <Envelope writer={writer} salutation={letter.salutation} isOpen={stage === "opening"} />
              <span className={cn("text-sm text-white/70", stage !== "envelope" && "invisible")}>{t.openHint}</span>
            </button>
          </div>
        )}

        {isReading && (
          <div
            ref={sheet}
            className="absolute inset-x-0 top-16 bottom-0 flex justify-center px-3 pb-3 animate-in fade-in-0 slide-in-from-bottom-8 duration-500 md:pb-8"
          >
            <div
              ref={paper}
              tabIndex={-1}
              onWheel={handsOff}
              onTouchMove={handsOff}
              onKeyDown={handsOff}
              className="letter-paper relative h-full w-full max-w-xl overflow-y-auto overscroll-contain rounded-sm px-6 shadow-2xl outline-none md:px-12"
            >
              <div lang="ja" className="font-letter text-letter font-semibold text-letter-ink">
                {parts.map((part, i) => {
                  const from = offset;
                  offset += part.chars.length;
                  return <Block key={i} part={part} from={from} count={count - from} isReducedMotion={isReducedMotion} />;
                })}
                <Signature
                  image={letter.signature.image}
                  text={letter.signature.text}
                  isSigned={isSigned}
                  isReducedMotion={isReducedMotion}
                />
                {isDone && (
                  <section className="flex justify-center animate-in fade-in-0 duration-700">
                    <Button ref={done} variant="letter" size="call" onClick={close}>
                      {t.done}
                    </Button>
                  </section>
                )}
              </div>
            </div>
          </div>
        )}

        {stage !== "closing" && (
          <div className="absolute top-0 right-0 flex items-center gap-2 p-3">
            {isAudible && isReading && (
              <Button variant="call-round" size="icon-call" aria-label={t.mute} aria-pressed={isMuted} onClick={toggleMute}>
                {isMuted ? <LetterMutedIcon /> : <LetterSoundIcon />}
              </Button>
            )}
            {!isDone && (
              <Button variant="call-glass" size="call-sm" onClick={close}>
                {t.skip}
              </Button>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

/** 信上的一块：抬头或一段正文（写完后淡出字幕）。每个字一个 span，没写到的先占着位置、看不见，
 * 版面从头到尾不跳；写到的字带一次「洇墨」的动画。`count` 是这一块写出了几个字（可以小于 0、大于字数）。 */
function Block({ part, from, count, isReducedMotion }: { part: Part; from: number; count: number; isReducedMotion: boolean }) {
  const n = Math.max(0, Math.min(part.chars.length, count));
  const chars = part.chars.map((char, j) => (
    <span key={j} data-c={from + j} className={j < n ? (isReducedMotion ? undefined : "animate-ink") : "opacity-0"}>
      {char}
    </span>
  ));
  return (
    <section>
      <p>{chars}</p>
      {part.zh && (
        <p
          lang="zh-CN"
          className={cn(
            "font-sans text-letter-zh font-normal text-letter-muted transition-opacity duration-700",
            n < part.chars.length && "opacity-0",
          )}
        >
          {part.zh}
        </p>
      )}
    </section>
  );
}

/** 信末她的签名，靠右，从左到右显出来；版面一开始就留着它的位置。有她手写的签名图时用图（透明底），
 * 没有或者取不到时，用她的颜色、用信上的字体把名字写出来。 */
function Signature({
  image,
  text,
  isSigned,
  isReducedMotion,
}: {
  image: string | null;
  text: string;
  isSigned: boolean;
  isReducedMotion: boolean;
}) {
  const [hasImage, setHasImage] = useState(image !== null);
  const shown = isSigned ? (isReducedMotion ? undefined : "animate-sign") : "invisible";
  return (
    <section className="flex justify-end">
      {hasImage ? (
        <img
          src={image ?? undefined}
          alt={text}
          onError={() => setHasImage(false)}
          className={cn("letter-signature w-auto max-w-[70%] object-contain object-right", shown)}
        />
      ) : (
        <p className={cn("text-letter-signature text-her-letter-ink", shown)}>{text}</p>
      )}
    </section>
  );
}

/** 她的信封：信封背面，封口上一枚她颜色的封蜡（压着一颗星），下半写着抬头，右下角是她的名字。拆开时封口往上翻开。 */
function Envelope({ writer, salutation, isOpen }: { writer: Character; salutation: string; isOpen: boolean }) {
  return (
    <span className="block perspective-normal">
      <span className="relative block aspect-[8/5] w-[min(84vw,24rem)] rounded-md bg-letter-envelope shadow-2xl ring-1 ring-letter-envelope-edge transition-transform duration-300 group-enabled:group-hover:-translate-y-1">
        <svg aria-hidden viewBox="0 0 160 100" preserveAspectRatio="none" className="absolute inset-0 size-full">
          <path
            d="M0 100 L66 52 M160 100 L94 52"
            fill="none"
            strokeWidth="1"
            vectorEffect="non-scaling-stroke"
            className="stroke-letter-envelope-edge"
          />
        </svg>
        <span lang="ja" className="absolute inset-x-0 bottom-[17%] text-center font-letter text-xl font-semibold text-letter-ink">
          {salutation}
        </span>
        <span lang="ja" className="absolute right-[7%] bottom-[6%] font-letter text-sm font-semibold text-her-letter-ink">
          {writer.name}
        </span>
        <span
          className={cn(
            "absolute inset-x-0 top-0 block h-[55%] origin-top transition-transform duration-500 ease-in-out transform-3d",
            isOpen && "rotate-x-180",
          )}
        >
          <svg aria-hidden viewBox="0 0 160 55" preserveAspectRatio="none" className="absolute inset-0 size-full">
            <path
              d="M0 0 H160 L80 55 Z"
              strokeWidth="1"
              vectorEffect="non-scaling-stroke"
              className="fill-letter-envelope stroke-letter-envelope-edge"
            />
          </svg>
          <Seal className="absolute top-full left-1/2 size-12 -translate-1/2 ring-4" />
        </span>
      </span>
    </span>
  );
}

/** 这个元素现在在不在屏幕上看得见的地方（不在页面里、被藏起来的都不算）。 */
function isOnScreen(el: HTMLElement): boolean {
  if (!el.isConnected) return false;
  const r = el.getBoundingClientRect();
  return r.width > 0 && r.height > 0 && r.bottom > 0 && r.right > 0 && r.top < window.innerHeight && r.left < window.innerWidth;
}
