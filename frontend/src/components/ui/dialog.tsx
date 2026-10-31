"use client"

import * as React from "react"
import { Dialog as DialogPrimitive } from "@base-ui/react/dialog"
import { cn } from "@/lib/utils"

import { Button } from "@/components/ui/button"
import { XIcon } from "lucide-react"

function Dialog({ ...props }: DialogPrimitive.Root.Props) {
  return <DialogPrimitive.Root data-slot="dialog" {...props} />
}

function DialogTrigger({ ...props }: DialogPrimitive.Trigger.Props) {
  return <DialogPrimitive.Trigger data-slot="dialog-trigger" {...props} />
}

function DialogPortal({ ...props }: DialogPrimitive.Portal.Props) {
  return <DialogPrimitive.Portal data-slot="dialog-portal" {...props} />
}

function DialogClose({ ...props }: DialogPrimitive.Close.Props) {
  return <DialogPrimitive.Close data-slot="dialog-close" {...props} />
}

function DialogOverlay({
  className,
  ...props
}: DialogPrimitive.Backdrop.Props) {
  return (
    <DialogPrimitive.Backdrop
      data-slot="dialog-overlay"
      className={cn(
        "fixed inset-0 isolate z-50 bg-black/10 duration-100 supports-backdrop-filter:backdrop-blur-xs data-open:animate-in data-open:fade-in-0 data-closed:animate-out data-closed:fade-out-0",
        className
      )}
      {...props}
    />
  )
}

function DialogContent({
  className,
  children,
  showCloseButton = true,
  container,
  variant = "default",
  ...props
}: DialogPrimitive.Popup.Props & {
  showCloseButton?: boolean
  // eidolon: container 透传给 Portal。浮层默认渲染到 body，拿不到对话子树上她的颜色（herVars）和 .dark；
  // 需要时把它指到子树里（DESIGN.md「The Scoped Colour Rule」）。
  container?: DialogPrimitive.Portal.Props["container"]
  // eidolon: viewer 是点开放大的照片（DESIGN.md「Chat bubbles · 照片」）：整屏压 85% 黑，内容居中放到最大，
  // 右上角白色 ✕。内容以外不接点击，点在压暗的底上就是点了外面，照常关掉。
  // eidolon: letter 是拆信这一层（GLOSSARY.md「信」，components/letter）：整屏，压暗的底和进出场的动画
  // 都由信自己画（要跟着信封、信纸一起动），这里的底透明，也没有 ✕。
  variant?: "default" | "viewer" | "letter"
}) {
  const viewer = variant === "viewer"
  const letter = variant === "letter"
  return (
    <DialogPortal container={container}>
      {/* eidolon: viewer 的底和照片一样淡 150ms。底先淡完会在照片卸掉前弹回不透明，关的时候整屏闪一下黑。 */}
      <DialogOverlay
        className={cn(
          viewer && "bg-black/85 duration-150 supports-backdrop-filter:backdrop-blur-none",
          letter && "bg-transparent supports-backdrop-filter:backdrop-blur-none"
        )}
      />
      <DialogPrimitive.Popup
        data-slot="dialog-content"
        className={cn(
          letter
            ? "fixed inset-0 z-50 outline-none"
            : viewer
            ? "pointer-events-none fixed inset-0 z-50 flex items-center justify-center p-4 outline-none duration-150 md:p-10 data-open:animate-in data-open:fade-in-0 data-open:zoom-in-95 data-closed:animate-out data-closed:fade-out-0 *:pointer-events-auto"
            // eidolon: dark:ring-overlay-edge，深色模式下浮层带一条边线（DESIGN.md「The Night Edge Rule」）。
            : "fixed top-1/2 left-1/2 z-50 grid w-full max-w-[calc(100%-2rem)] -translate-x-1/2 -translate-y-1/2 gap-4 rounded-xl bg-popover p-4 text-sm text-popover-foreground ring-1 ring-foreground/10 dark:ring-overlay-edge duration-100 outline-none sm:max-w-sm data-open:animate-in data-open:fade-in-0 data-open:zoom-in-95 data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-95",
          className
        )}
        {...props}
      >
        {children}
        {showCloseButton && !letter && (
          <DialogPrimitive.Close
            data-slot="dialog-close"
            render={
              <Button
                variant="ghost"
                className={cn(
                  "absolute top-2 right-2",
                  viewer && "top-3 right-3 size-11 rounded-full text-white hover:bg-white/15 hover:text-white [&_svg:not([class*='size-'])]:size-6"
                )}
                size={viewer ? "icon-lg" : "icon-sm"}
              />
            }
          >
            <XIcon
            />
            <span className="sr-only">Close</span>
          </DialogPrimitive.Close>
        )}
      </DialogPrimitive.Popup>
    </DialogPortal>
  )
}

function DialogHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="dialog-header"
      className={cn("flex flex-col gap-2", className)}
      {...props}
    />
  )
}

function DialogFooter({
  className,
  showCloseButton = false,
  children,
  ...props
}: React.ComponentProps<"div"> & {
  showCloseButton?: boolean
}) {
  return (
    <div
      data-slot="dialog-footer"
      className={cn(
        "-mx-4 -mb-4 flex flex-col-reverse gap-2 rounded-b-xl border-t bg-muted/50 p-4 sm:flex-row sm:justify-end",
        className
      )}
      {...props}
    >
      {children}
      {showCloseButton && (
        <DialogPrimitive.Close render={<Button variant="outline" />}>
          Close
        </DialogPrimitive.Close>
      )}
    </div>
  )
}

function DialogTitle({ className, ...props }: DialogPrimitive.Title.Props) {
  return (
    <DialogPrimitive.Title
      data-slot="dialog-title"
      className={cn(
        "font-heading text-base leading-none font-medium",
        className
      )}
      {...props}
    />
  )
}

function DialogDescription({
  className,
  ...props
}: DialogPrimitive.Description.Props) {
  return (
    <DialogPrimitive.Description
      data-slot="dialog-description"
      className={cn(
        "text-sm text-muted-foreground *:[a]:underline *:[a]:underline-offset-3 *:[a]:hover:text-foreground",
        className
      )}
      {...props}
    />
  )
}

export {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogOverlay,
  DialogPortal,
  DialogTitle,
  DialogTrigger,
}
