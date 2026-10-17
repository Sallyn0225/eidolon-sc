"use client";

import type { Ref } from "react";

import { copy } from "@/i18n";
import { showTime } from "@/lib/callTime";
import type { LiveCall } from "@/lib/liveConversation";
import { cn } from "@/lib/utils";
import { ForwardIcon, PhotoIcon } from "@/theme/icons";

import { useCallTime } from "./useCallTime";

/**
 * 通话层收起后的通话条（DESIGN.md「Call layer」的「收起后：通话条」，取代上一版的便利贴）：
 * 40px 高、铺满所在那一块的宽，底是她的 `--her-call-deep`、白字；左边一个白色小圆点（呼叫中闪烁），
 * 接着「通话中 mm:ss」或「正在呼叫…」，右端「回到通话 ›」。整条是一个按钮，点了展开通话层；
 * 收起后焦点落在这里（useFocusBack），回车或空格再展开。
 * 两处用它：她的对话页首下面（不带名字），别的外壳页面最顶上（带 `name`，ADR-0018），她的颜色由用的那一处注入。
 * 收起时她发来了照片，外壳顶上那条在状态后面加相机图标和「新照片」（`newPhoto`）；对话页首下面那条不提示，照片就在记录里。
 */
export function CallBar({
  call,
  name,
  newPhoto = false,
  onExpand,
  ref,
}: {
  call: LiveCall;
  /** 在和谁通话：不在她的对话页上时写在状态前面。 */
  name?: string;
  /** 收起时到了她的照片，还没看。 */
  newPhoto?: boolean;
  onExpand: () => void;
  ref?: Ref<HTMLButtonElement>;
}) {
  const time = useCallTime(call);
  return (
    <button
      ref={ref}
      type="button"
      onClick={onExpand}
      className="flex h-call-bar w-full shrink-0 items-center gap-2 bg-her-call-deep px-4 text-left text-white outline-none focus-visible:ring-3 focus-visible:ring-white/60 focus-visible:ring-inset"
    >
      <span
        aria-hidden
        className={cn("size-2 shrink-0 rounded-full bg-white", !time && "motion-safe:animate-pulse")}
      />
      <span className="flex min-w-0 flex-1 gap-2 text-sm font-medium tabular-nums">
        {name && <span className="truncate">{name}</span>}
        <span className="shrink-0">{time ? copy.call.listConnected(showTime(time)) : copy.call.dialing}</span>
        {newPhoto && (
          <span className="flex shrink-0 items-center gap-1">
            <PhotoIcon aria-hidden className="size-4" />
            {copy.call.photo.newPhoto}
          </span>
        )}
      </span>
      <span className="flex shrink-0 items-center text-sm text-white/80">
        {copy.call.expand}
        <ForwardIcon aria-hidden className="size-4" />
      </span>
    </button>
  );
}
