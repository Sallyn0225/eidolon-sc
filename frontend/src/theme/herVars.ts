import type { CSSProperties } from "react";

import { imageColorScale, type ModePair } from "@/lib/imageColor";

/** 按系统明暗取一对颜色中的一个。 */
export const ld = (p: ModePair) => `light-dark(${p.light}, ${p.dark})`;

/**
 * 把她的印象色注入一个子树（DESIGN.md「The Scoped Colour Rule」）：shadcn 的 `--primary`/`--primary-foreground`
 * 换成她的 accent/onAccent，`--ring` 换成她的 mark（不碰 `--accent`，那是悬停底色）。
 * 另以 `--her-*` 给出 imageColorScale() 成对校验过的颜色。这是界面取用她颜色的唯一入口，不直接给出官方原色。
 * 通话层永远是深色，`--her-call-deep` 只有一份。
 *
 * 浮层（Dialog、DropdownMenu、Drawer 等）通过 portal 渲染到子树外面，拿不到这些变量：
 * 需要她的颜色时，把 portal 的 container 指到子树里，或在浮层内容上再展开一次 herVars()。
 */
export function herVars(color: string): CSSProperties {
  const s = imageColorScale(color);
  return {
    "--primary": ld(s.accent),
    "--primary-foreground": ld(s.onAccent),
    "--ring": ld(s.mark),
    "--her-wall": ld(s.wall),
    "--her-mark": ld(s.mark),
    "--her-bar": ld(s.bar),
    "--her-button": ld(s.button.bg),
    "--her-button-fg": ld(s.button.fg),
    "--her-call-deep": s.call.deep,
  } as CSSProperties;
}

/**
 * 信（last-letter 分支）上她的颜色：信纸、信封固定浅色，只有一份。封蜡用分享图色带的那一对（原色和上面的字），
 * 信封上她的名字和署名用浅色模式的 accent（在纸面上写她颜色的字，≥ 4.5）。
 */
export function letterVars(color: string): CSSProperties {
  const { share, accent } = imageColorScale(color);
  return {
    "--her-seal": share.banner,
    "--her-seal-fg": share.onBanner,
    "--her-letter-ink": accent.light,
  } as CSSProperties;
}

/**
 * 分享图（DESIGN.md「分享图」）里她的颜色：页首色带和上面的字（`--her-banner`、`--her-banner-fg`），
 * 和前 3 的排行条（`--her-bar`，按分享图条的底校验）。分享图固定浅色，只有一份。
 */
export function shareVars(color: string): CSSProperties {
  const { share } = imageColorScale(color);
  return {
    "--her-banner": share.banner,
    "--her-banner-fg": share.onBanner,
    "--her-bar": share.bar,
  } as CSSProperties;
}
