"use client";

// PROTOTYPE（.scratch/moments/issues/05-entry-and-page-prototype.md）：朋友圈页面的三种做法，`?variant=A|B|C` 切换。
// A 时间线：一栏，赞和评论直接铺在每条下面（等回复时没有任何痕迹）。
// B 卡片 + 详情：上面一排头像筛选，卡片只露数字和头像，点开在面板里看评论、写评论（等回复时一行「正在输入」）。
// C 按她：左边一列发过动态的她，右边她一个人的时间线，铺她的壁纸（等回复时制作人的评论下面「已读」）。
// 入口（玩法卡 / 导航第四项）在底下切换条上切，存在 localStorage。扔掉用的，不进 main。

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Cloud,
  CloudRain,
  Heart,
  ImageIcon,
  MapPin,
  MessageCircle,
  Moon,
  MoreHorizontal,
  Snowflake,
  Sun,
} from "lucide-react";

import { ImageViewer } from "@/components/app/ImageViewer";
import { MarkedAvatar } from "@/components/app/MarkedAvatar";
import { PageShell } from "@/components/app/PageShell";
import { useDirectory, useWide } from "@/components/conversations/ConversationDirectory";
import { PlayShell, PlaySubpageHeader } from "@/components/play/PlayShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import type { Character } from "@/lib/api";
import { cn } from "@/lib/utils";
import { herVars } from "@/theme/herVars";

import {
  addComment,
  markSeen,
  osmHref,
  resetNew,
  revealed,
  setEntry,
  timeText,
  toggleLike,
  useEntry,
  useMoments,
  useNowSeconds,
  type Post,
  type Weather,
} from "./store";

const VARIANTS = [
  { key: "A", name: "时间线" },
  { key: "B", name: "卡片 + 详情" },
  { key: "C", name: "按她" },
] as const;

type Who = (id: string) => { name: string; avatar: string | null; character: Character | null };

function useWho(): Who {
  const { characters } = useDirectory();
  return (id) => {
    if (id === "producer") return { name: "制作人", avatar: null, character: null };
    const character = characters?.find((c) => c.id === id) ?? null;
    return { name: character?.name ?? id, avatar: character?.avatar_url ?? null, character };
  };
}

export function MomentsPrototype() {
  const params = useSearchParams();
  const variant = params.get("variant") ?? "A";
  const entry = useEntry();
  useEffect(() => markSeen(), []);
  const body = variant === "B" ? <VariantB /> : variant === "C" ? <VariantC /> : <VariantA />;
  const header =
    entry === "nav" ? <h1 className="text-list-title">朋友圈</h1> : <PlaySubpageHeader title="朋友圈" />;
  return (
    <>
      {variant === "C" ? (
        <PageShell width="full" isInShell header={header} isScrollable={false}>
          {body}
        </PageShell>
      ) : (
        <PlayShell header={header}>{body}</PlayShell>
      )}
      <PrototypeSwitcher current={variant} />
    </>
  );
}

// ---------------------------------------------------------------- 共用的小件

const WEATHER_ICONS: Record<Weather, typeof Sun> = {
  sunny: Sun,
  cloudy: Cloud,
  rain: CloudRain,
  "clear-night": Moon,
  snow: Snowflake,
};

/** 地名（点开 OSM）和天气小字。 */
function PlaceAndWeather({ post, className }: { post: Post; className?: string }) {
  const Icon = post.weather ? WEATHER_ICONS[post.weather.kind] : null;
  return (
    <span className={cn("flex min-w-0 items-center gap-2 text-meta text-muted-foreground", className)}>
      <a
        href={osmHref(post.place)}
        target="_blank"
        rel="noopener noreferrer"
        className="flex min-w-0 items-center gap-0.5 hover:underline"
      >
        <MapPin aria-hidden className="size-3 shrink-0" />
        <span className="truncate">{post.place.name}</span>
      </a>
      {Icon && post.weather && (
        <span className="flex shrink-0 items-center gap-0.5 tabular-nums">
          <Icon aria-hidden className="size-3" />
          {post.weather.temp}°
        </span>
      )}
    </span>
  );
}

function PostImage({ post, className }: { post: Post; className?: string }) {
  const [open, setOpen] = useState(false);
  if (!post.image) return null;
  if ("placeholder" in post.image) {
    return (
      <div
        className={cn(
          "flex aspect-[4/5] flex-col items-center justify-center gap-2 rounded-lg bg-muted p-4 text-center text-subtitle text-muted-foreground",
          className,
        )}
      >
        <ImageIcon aria-hidden className="size-6" />
        {post.image.placeholder}
      </div>
    );
  }
  return (
    <>
      <button type="button" onClick={() => setOpen(true)} className={cn("block overflow-hidden rounded-lg", className)}>
        <img src={post.image.src} alt="配图" className="size-full object-cover" />
      </button>
      <ImageViewer src={post.image.src} title="配图" alt="配图" open={open} onOpenChange={setOpen} />
    </>
  );
}

function CommentInput({ post, onDone, autoFocus }: { post: Post; onDone?: () => void; autoFocus?: boolean }) {
  const [text, setText] = useState("");
  const who = useWho();
  return (
    <form
      className="flex items-center gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        if (!text.trim()) return;
        addComment(post.id, text.trim());
        setText("");
        onDone?.();
      }}
    >
      <Input
        autoFocus={autoFocus}
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder={`评论${who(post.by).name}的动态`}
        className="h-9 flex-1"
      />
      <Button type="submit" size="lg" disabled={!text.trim()}>
        发送
      </Button>
    </form>
  );
}

function LikeButton({ post, withLabel }: { post: Post; withLabel?: boolean }) {
  const { producerLikes } = useMoments();
  const liked = producerLikes.has(post.id);
  return (
    <Button
      variant="ghost"
      size={withLabel ? "sm" : "icon-sm"}
      aria-pressed={liked}
      aria-label={liked ? "取消赞" : "赞"}
      onClick={() => toggleLike(post.id)}
    >
      <Heart aria-hidden className={cn(liked && "fill-foreground")} />
      {withLabel && (liked ? "已赞" : "赞")}
    </Button>
  );
}

/** 赞的人：她们的名字，制作人赞了排最前。 */
function likerNames(post: Post, now: number, liked: boolean, who: Who): string[] {
  const names = revealed(post, now).likes.map((like) => who(like.by).name);
  return liked ? ["制作人", ...names] : names;
}

// ---------------------------------------------------------------- A 时间线

function VariantA() {
  const { posts } = useMoments();
  return (
    <div className="flex flex-col divide-y">
      {posts.map((post) => (
        <TimelinePost key={post.id} post={post} />
      ))}
    </div>
  );
}

function TimelinePost({ post }: { post: Post }) {
  const who = useWho();
  const now = useNowSeconds();
  const { producerLikes } = useMoments();
  const [composing, setComposing] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const author = who(post.by);
  const { comments } = revealed(post, now);
  const likers = likerNames(post, now, producerLikes.has(post.id), who);
  return (
    <article className="flex gap-3 py-4">
      <MarkedAvatar name={author.name} src={author.avatar} size="lg" />
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <span className="text-row-name">{author.name}</span>
        {post.text && <p className="text-body whitespace-pre-wrap">{post.text}</p>}
        {post.image && <PostImage post={post} className="w-48 sm:w-60" />}
        <div className="flex items-center justify-between gap-2">
          <span className="flex min-w-0 items-center gap-2">
            <span className="shrink-0 text-meta text-muted-foreground">{timeText(post.minutesAgo)}</span>
            <PlaceAndWeather post={post} />
          </span>
          <Popover open={menuOpen} onOpenChange={setMenuOpen}>
            <PopoverTrigger render={<Button variant="secondary" size="icon-sm" aria-label="赞或评论" />}>
              <MoreHorizontal aria-hidden />
            </PopoverTrigger>
            <PopoverContent side="left" className="flex w-auto flex-row gap-1 p-1">
              <span onClick={() => setMenuOpen(false)}>
                <LikeButton post={post} withLabel />
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setComposing(true);
                  setMenuOpen(false);
                }}
              >
                <MessageCircle aria-hidden />
                评论
              </Button>
            </PopoverContent>
          </Popover>
        </div>
        {(likers.length > 0 || comments.length > 0) && (
          <div className="flex flex-col gap-1 rounded-lg bg-muted px-3 py-2 text-sm">
            {likers.length > 0 && (
              <p className="flex gap-1.5">
                <Heart aria-hidden className="mt-1 size-3.5 shrink-0" />
                <span className="font-medium">{likers.join("，")}</span>
              </p>
            )}
            {likers.length > 0 && comments.length > 0 && <div className="h-px bg-foreground/10" />}
            {comments.map((comment) => (
              <p key={comment.id}>
                <span className="font-medium">{who(comment.by).name}</span>
                {comment.to && (
                  <>
                    <span className="text-muted-foreground"> 回复 </span>
                    <span className="font-medium">{who(comment.to).name}</span>
                  </>
                )}
                <span>：{comment.text}</span>
              </p>
            ))}
          </div>
        )}
        {composing && <CommentInput post={post} autoFocus onDone={() => setComposing(false)} />}
      </div>
    </article>
  );
}

// ---------------------------------------------------------------- B 卡片 + 详情

function VariantB() {
  const { posts } = useMoments();
  const who = useWho();
  const [filter, setFilter] = useState<string | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);
  const authors = [...new Set(posts.map((post) => post.by))];
  const shown = filter ? posts.filter((post) => post.by === filter) : posts;
  const open = posts.find((post) => post.id === openId) ?? null;
  return (
    <>
      <div className="-mx-4 flex gap-3 overflow-x-auto px-4 pb-1">
        <FilterChip label="全部" isCurrent={filter === null} onClick={() => setFilter(null)} />
        {authors.map((id) => {
          const author = who(id);
          return (
            <FilterChip
              key={id}
              label={author.character?.short_name ?? author.name}
              avatar={<MarkedAvatar name={author.name} src={author.avatar} size="lg" />}
              isCurrent={filter === id}
              onClick={() => setFilter(filter === id ? null : id)}
            />
          );
        })}
      </div>
      <div className="flex flex-col gap-4">
        {shown.map((post) => (
          <FeedCard key={post.id} post={post} onOpen={() => setOpenId(post.id)} />
        ))}
      </div>
      <PostSheet post={open} onClose={() => setOpenId(null)} />
    </>
  );
}

function FilterChip({
  label,
  avatar,
  isCurrent,
  onClick,
}: {
  label: string;
  avatar?: ReactNode;
  isCurrent: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={isCurrent}
      className={cn(
        "flex w-16 shrink-0 flex-col items-center gap-1 rounded-xl py-1.5 text-meta",
        isCurrent ? "bg-muted font-medium text-foreground" : "text-muted-foreground hover:bg-muted/60",
      )}
    >
      {avatar ?? <span className="flex size-12 items-center justify-center rounded-full border text-subtitle">全部</span>}
      <span className="w-full truncate px-1">{label}</span>
    </button>
  );
}

function FeedCard({ post, onOpen }: { post: Post; onOpen: () => void }) {
  const who = useWho();
  const now = useNowSeconds();
  const { producerLikes } = useMoments();
  const author = who(post.by);
  const { likes, comments } = revealed(post, now);
  const likeCount = likes.length + (producerLikes.has(post.id) ? 1 : 0);
  return (
    <article className="flex flex-col gap-3 rounded-2xl border p-4">
      <header className="flex items-center gap-3">
        <MarkedAvatar name={author.name} src={author.avatar} size="bubble" />
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="text-row-name">{author.name}</span>
          <span className="flex items-center gap-2">
            <span className="shrink-0 text-meta text-muted-foreground">{timeText(post.minutesAgo)}</span>
            <PlaceAndWeather post={post} />
          </span>
        </span>
      </header>
      {post.image ? (
        <>
          <PostImage post={post} className="w-full sm:w-96" />
          {post.text && <p className="text-body whitespace-pre-wrap">{post.text}</p>}
        </>
      ) : (
        post.text && <p className="py-4 text-header font-normal whitespace-pre-wrap">{post.text}</p>
      )}
      <footer className="flex items-center gap-1">
        <LikeButton post={post} />
        <span className="min-w-4 text-subtitle text-muted-foreground tabular-nums">{likeCount || ""}</span>
        <Button variant="ghost" size="icon-sm" aria-label="评论" onClick={onOpen}>
          <MessageCircle aria-hidden />
        </Button>
        <span className="min-w-4 text-subtitle text-muted-foreground tabular-nums">{comments.length || ""}</span>
        <div className="flex-1" />
        <button type="button" onClick={onOpen} className="flex -space-x-1.5">
          {likes.slice(0, 5).map((like) => {
            const liker = who(like.by);
            return (
              <span key={like.by} className="rounded-full ring-2 ring-background">
                <MarkedAvatar name={liker.name} src={liker.avatar} size="sm" />
              </span>
            );
          })}
        </button>
      </footer>
    </article>
  );
}

function PostSheet({ post, onClose }: { post: Post | null; onClose: () => void }) {
  const wide = useWide();
  const who = useWho();
  const now = useNowSeconds();
  const { producerLikes } = useMoments();
  const revealedNow = post ? revealed(post, now) : null;
  return (
    <Sheet open={post !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side={wide ? "right" : "bottom"} className={cn(!wide && "max-h-[85dvh]")}>
        {post && revealedNow && (
          <>
            <SheetHeader>
              <SheetTitle>{who(post.by).name}的动态</SheetTitle>
            </SheetHeader>
            <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4">
              {post.text && <p className="text-body whitespace-pre-wrap">{post.text}</p>}
              <p className="flex gap-1.5 text-sm">
                <Heart aria-hidden className="mt-0.5 size-4 shrink-0" />
                <span>{likerNames(post, now, producerLikes.has(post.id), who).join("，") || "还没有人赞"}</span>
              </p>
              <div className="flex flex-col gap-3">
                {revealedNow.comments.map((comment) => {
                  const author = who(comment.by);
                  return (
                    <div key={comment.id} className="flex gap-2.5">
                      {comment.by === "producer" ? (
                        <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary text-meta text-primary-foreground">
                          P
                        </span>
                      ) : (
                        <MarkedAvatar name={author.name} src={author.avatar} size="sm" />
                      )}
                      <p className="text-sm">
                        <span className="font-medium">{author.name}</span>
                        {comment.to && <span className="text-muted-foreground"> 回复 {who(comment.to).name}</span>}
                        <br />
                        {comment.text}
                      </p>
                    </div>
                  );
                })}
                {revealedNow.pendingReply && (
                  <div className="flex items-center gap-2.5 text-subtitle text-muted-foreground">
                    <MarkedAvatar name={who(post.by).name} src={who(post.by).avatar} size="sm" />
                    {who(post.by).name}正在输入…
                  </div>
                )}
              </div>
            </div>
            <div className="border-t p-4">
              <CommentInput post={post} />
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}

// ---------------------------------------------------------------- C 按她

function VariantC() {
  const { posts } = useMoments();
  const who = useWho();
  const wide = useWide();
  const authors = [...new Set(posts.map((post) => post.by))];
  const [current, setCurrent] = useState<string | null>(null);
  const selected = current ?? (wide ? authors[0] : null);
  const list = (
    <ul className="flex flex-col overflow-y-auto md:w-80 md:shrink-0 md:border-r">
      {authors.map((id) => {
        const author = who(id);
        const latest = posts.find((post) => post.by === id)!;
        return (
          <li key={id}>
            <button
              type="button"
              onClick={() => setCurrent(id)}
              className={cn(
                "flex w-full items-center gap-3 px-4 py-2.5 text-left",
                selected === id && wide ? "bg-muted" : "hover:bg-muted/60",
              )}
            >
              <MarkedAvatar name={author.name} src={author.avatar} size="list" />
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="flex items-baseline justify-between gap-2">
                  <span className="truncate text-row-name">{author.name}</span>
                  <span className="shrink-0 text-meta text-muted-foreground">{timeText(latest.minutesAgo)}</span>
                </span>
                <span className="truncate text-preview text-muted-foreground">
                  {latest.text ?? "［配图］"}
                </span>
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
  if (!wide && selected === null) return list;
  return (
    <div className="flex min-h-0 flex-1">
      {wide && list}
      {selected && <HerTimeline id={selected} onBack={wide ? undefined : () => setCurrent(null)} />}
    </div>
  );
}

function HerTimeline({ id, onBack }: { id: string; onBack?: () => void }) {
  const { posts } = useMoments();
  const who = useWho();
  const her = who(id);
  const hers = posts.filter((post) => post.by === id);
  return (
    <div style={her.character ? herVars(her.character.color) : undefined} className="flex min-h-0 flex-1 flex-col bg-her-wall">
      <div className="flex min-h-14 shrink-0 items-center gap-2 px-2">
        {onBack && (
          <Button variant="ghost" size="icon-lg" aria-label="返回" onClick={onBack}>
            <ChevronLeft aria-hidden />
          </Button>
        )}
        <MarkedAvatar name={her.name} src={her.avatar} size="sm" />
        <span className="text-header">{her.name}</span>
      </div>
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 pb-24">
        <div className="mx-auto flex w-full max-w-2xl flex-col gap-6">
          {hers.map((post) => (
            <HerPost key={post.id} post={post} />
          ))}
        </div>
      </div>
    </div>
  );
}

function HerPost({ post }: { post: Post }) {
  const who = useWho();
  const now = useNowSeconds();
  const { producerLikes } = useMoments();
  const { comments, pendingReply } = revealed(post, now);
  const likers = likerNames(post, now, producerLikes.has(post.id), who);
  const lastProducer = [...comments].reverse().find((c) => c.by === "producer");
  return (
    <article className="flex flex-col gap-2">
      <span className="text-meta text-muted-foreground">{timeText(post.minutesAgo)}</span>
      <div className="flex flex-col gap-3 rounded-2xl bg-background p-4">
        {post.text && <p className="text-body whitespace-pre-wrap">{post.text}</p>}
        {post.image && <PostImage post={post} className="w-full max-w-80" />}
        <div className="flex items-center justify-between gap-2">
          <PlaceAndWeather post={post} />
          <LikeButton post={post} />
        </div>
        {likers.length > 0 && <p className="text-subtitle text-muted-foreground">♡ {likers.join("、")}</p>}
        {comments.length > 0 && (
          <div className="flex flex-col gap-2 border-t pt-3">
            {comments.map((comment) => (
              <div key={comment.id} className="flex flex-col">
                <p className="text-sm">
                  <span className="font-medium">{who(comment.by).name}</span>
                  {comment.to && <span className="text-muted-foreground"> → {who(comment.to).name}</span>}
                  ：{comment.text}
                </p>
                {pendingReply && comment === lastProducer && (
                  <span className="self-end text-meta text-muted-foreground">已读</span>
                )}
              </div>
            ))}
          </div>
        )}
        <CommentInput post={post} />
      </div>
    </article>
  );
}

// ---------------------------------------------------------------- 切换条

function PrototypeSwitcher({ current }: { current: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const entry = useEntry();
  const index = Math.max(
    0,
    VARIANTS.findIndex((variant) => variant.key === current),
  );
  const go = (step: number) => {
    const next = VARIANTS[(index + step + VARIANTS.length) % VARIANTS.length];
    const search = new URLSearchParams(params.toString());
    search.set("variant", next.key);
    router.replace(`${pathname}?${search}`);
  };
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable)) return;
      if (event.key === "ArrowLeft") go(-1);
      if (event.key === "ArrowRight") go(1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });
  // 只在 prototype/moments-page 分支上，不进 main，所以不按 NODE_ENV 藏：本地跑的是构建版。
  return (
    <div className="fixed bottom-20 left-1/2 z-50 flex -translate-x-1/2 items-center gap-0.5 rounded-full bg-foreground px-1.5 py-1 text-xs whitespace-nowrap text-background shadow-lg md:bottom-4 md:text-sm">
      <button type="button" aria-label="上一种" onClick={() => go(-1)} className="rounded-full p-1.5 hover:bg-background/20">
        <ChevronLeft className="size-4" />
      </button>
      <span className="min-w-20 text-center tabular-nums">
        {VARIANTS[index].key} {VARIANTS[index].name}
      </span>
      <button type="button" aria-label="下一种" onClick={() => go(1)} className="rounded-full p-1.5 hover:bg-background/20">
        <ChevronRight className="size-4" />
      </button>
      <span className="mx-1 h-4 w-px bg-background/30" />
      <button
        type="button"
        onClick={() => setEntry(entry === "card" ? "nav" : "card")}
        className="rounded-full px-2 py-1 hover:bg-background/20"
      >
        入口：{entry === "card" ? "玩法卡" : "导航"}
      </button>
      <button type="button" onClick={resetNew} className="rounded-full px-2 py-1 hover:bg-background/20">
        造新动态
      </button>
    </div>
  );
}
