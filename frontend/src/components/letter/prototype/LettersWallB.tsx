"use client";

// PROTOTYPE, throwaway（prototype/letters-ui 分支）：方案 B，玩法页的「信」卡和它的子页（/play/letters）。
// 子页是一整面信封墙：按写信的人分组，最近写过信的那位在上；组里是一枚枚完整的信封，按时间新的在前。
// 点一枚拆开，信收起时落回墙上那一枚。

import { MarkedAvatar } from "@/components/app/MarkedAvatar";
import { PlayCardLink } from "@/components/play/PlayCardLink";
import { PlayShell, PlaySubpageHeader } from "@/components/play/PlayShell";
import { playHref } from "@/lib/playRoute";

import { useLetters, type BoxLetter } from "../LetterProvider";
import { MiniEnvelope } from "./MiniEnvelope";

/** 玩法页第一级的「信」卡：只在方案 B。 */
export function LettersCardB() {
  const box = useLetters();
  if (!box || box.variant !== "B" || box.letters.length === 0) return null;
  return (
    <PlayCardLink
      card={{
        id: "letters",
        name: "信",
        href: playHref("letters"),
        status: box.unreadCount > 0 ? `${box.unreadCount} 封没读过` : `${box.letters.length} 封`,
        hasDot: box.unreadCount > 0,
        dotLabel: "有没读过的信",
      }}
    />
  );
}

export function LettersWallB() {
  const box = useLetters();
  const groups: BoxLetter[][] = [];
  for (const letter of box?.letters ?? []) {
    const group = groups.find((g) => g[0].characterId === letter.characterId);
    if (group) group.push(letter);
    else groups.push([letter]);
  }
  return (
    <PlayShell header={<PlaySubpageHeader title="信" />}>
      {box && box.variant !== "B" && <p className="text-subtitle text-muted-foreground">切到方案 B 再看这一页。</p>}
      {groups.map((group) => {
        const writer = group[0].writer;
        return (
          <section key={writer.id} className="flex flex-col gap-3 pb-4">
            <h2 className="flex items-center gap-2 text-header">
              <MarkedAvatar name={writer.name} src={writer.avatar_url} size="sm" />
              {writer.name}
            </h2>
            <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {group.map((letter) => (
                <li key={letter.id}>
                  <MiniEnvelope
                    ref={box?.target(`tile:${letter.id}`)}
                    letter={letter}
                    shape="tile"
                    hideName
                    onClick={() => box?.open(letter.id, `tile:${letter.id}`)}
                  />
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </PlayShell>
  );
}
