import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const textareaVariants = cva(
  "flex field-sizing-content w-full transition-colors outline-none placeholder:text-muted-foreground focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40",
  {
    variants: {
      variant: {
        // eidolon: 触屏上一律 16px，iOS Safari 字号不到 16px 的输入框拿到焦点会放大页面（#226）；
        // 原版按宽度（md:text-sm）判断，iPad 和横屏的 iPhone 也过了 md，改成只在电脑上（pointer-fine）缩到 14px。
        default:
          "min-h-16 rounded-lg border border-input bg-transparent px-2.5 py-2 text-base focus-visible:border-ring disabled:bg-input/50 md:pointer-fine:text-sm dark:bg-input/30 dark:disabled:bg-input/80",
        // eidolon: 对话页输入栏的输入框（DESIGN.md「composer-field」「Layout」）：bg-muted、22px 圆角、无边框，
        // 一行起、随字数长高（field-sizing），最多长到 8rem，再多就在框里滚动。触屏上 16px（同上，#226）。
        composer:
          "max-h-32 min-h-9 resize-none rounded-bubble border-0 bg-muted px-4 py-1.5 text-body leading-6 pointer-coarse:text-base",
        // eidolon: 通话层输入栏的输入框（DESIGN.md「Call layer」的「打字」）：15% 白底、白字，44px 高起，
        // 和两边的圆键齐平；同样随字数长高，最多 8rem。触屏上 16px（同上，#226）。
        call:
          "max-h-32 min-h-11 resize-none rounded-bubble border-0 bg-white/15 px-4 py-2.5 text-body leading-6 pointer-coarse:text-base text-white placeholder:text-white/60 focus-visible:ring-white/60",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Textarea({
  className,
  variant = "default",
  ...props
}: React.ComponentProps<"textarea"> & VariantProps<typeof textareaVariants>) {
  return (
    <textarea
      data-slot="textarea"
      data-variant={variant}
      className={cn(textareaVariants({ variant }), className)}
      {...props}
    />
  )
}

export { Textarea }
