"use client";

import { usePathname } from "next/navigation";
import { useSyncExternalStore, type ReactNode } from "react";

import { NavDock, NavRail } from "@/components/app/AppNav";
import { CallBar } from "@/components/conversations/CallBar";
import { LiveCallLayer } from "@/components/conversations/CallLayer";
import { useDirectory, useWide } from "@/components/conversations/ConversationDirectory";
import { useFocusBack } from "@/components/conversations/useFocusBack";
import { useStandOutfits } from "@/components/conversations/useStandOutfits";
import type { Character } from "@/lib/api";
import { NOT_OPEN, type LiveConversation } from "@/lib/liveConversation";
import { showsShellCallBar } from "@/lib/navShell";
import { herVars } from "@/theme/herVars";

const notOpen = () => NOT_OPEN;
const noSubscription = () => () => {};

/**
 * 导航外壳的页框（DESIGN.md「Layout」「Call layer」，ADR-0018）：
 * - 电脑上最左一条导航栏，手机上底部一条 dock，只靠 CSS 断点分宽窄，手机首屏（不跑脚本）直接是单栏加 dock。
 * 通话由外壳持有，不在她的对话页上时由这里画。
 * - 通话中、通话层收着、当前页不是她的对话页（外壳的去处规则，lib/navShell）：最顶上一条带她名字的通话条，
 *   横跨整宽、在页首之上；点了在当前页展开通话层。她的对话页上没有这一条，那里页首下面有自己的。
 * - 通话层在当前页展开：手机上铺满整屏（盖住 dock），电脑上盖住导航栏右边的内容区；展开时底下的 dock、页面都 inert，
 *   导航栏没被盖住，照样能点，点了先收起（AppNav）。收起后还在原来的页面。她的对话页上的通话层由那一页画，
 *   手机上同样盖住 dock，dock 也 inert。
 * 下面的页面占满导航栏、dock、通话条以外的那一块（PageShell 的 `isInShell`）。
 */
export function NavShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { held, isHeldShown, call, characters } = useDirectory();
  const snapshot = useSyncExternalStore(held?.subscribe ?? noSubscription, held?.snapshot ?? notOpen, notOpen);
  const character = held && !isHeldShown ? characters?.find((c) => c.id === held.characterId) : undefined;
  const layer = character ? snapshot.layer : null;
  // 外壳持有的通话层展开着，不论是这里画的还是她的对话页画的（手机上铺满整屏，同样盖住 dock）。
  const isLayerOpen = held !== null && snapshot.layer !== null && !snapshot.layer.collapsed;
  const isCovered = layer !== null && isLayerOpen;
  const barShown = call !== null && layer?.collapsed === true && showsShellCallBar(pathname, call.characterId);
  const focus = useFocusBack({ layerOpen: isCovered, noteShown: barShown });

  return (
    <div className="flex h-dvh flex-col md:flex-row">
      <NavRail />
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        {barShown && character && held && (
          <div style={herVars(character.color)} className="shrink-0">
            <CallBar
              ref={focus.note}
              call={call.state}
              name={character.name}
              newPhoto={snapshot.newPhoto}
              onExpand={() => held.expand()}
            />
          </div>
        )}
        <div className="relative min-h-0 flex-1">
          <div inert={isCovered} className="h-full">
            {children}
          </div>
          {character && held && <HeldLayer live={held} character={character} layerRef={focus.layer} />}
        </div>
      </div>
      <NavDock isInert={isLayerOpen} />
    </div>
  );
}

/** 当前页上的通话层：注入她的颜色，盖住内容区（手机上铺满整屏）。 */
function HeldLayer({
  live,
  character,
  layerRef,
}: {
  live: LiveConversation;
  character: Character;
  layerRef: ReturnType<typeof useFocusBack>["layer"];
}) {
  const { go, account } = useDirectory();
  const outfits = useStandOutfits(character);
  const isFullScreen = !useWide();
  return (
    <div style={herVars(character.color)} className="contents">
      <LiveCallLayer
        live={live}
        character={character}
        standOutfits={outfits?.toTry ?? []}
        layerRef={layerRef}
        isFullScreen={isFullScreen}
        go={go}
        exemptingKeys={account?.exempting_keys ?? null}
      />
    </div>
  );
}
