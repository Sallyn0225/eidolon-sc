import { cn } from "@/lib/utils";

/** 她颜色的封蜡，压着一颗星：拆信这一层的信封上，和列表里的小信封上。 */
export function Seal({ className }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={cn("grid shrink-0 place-items-center rounded-full bg-her-seal text-her-seal-fg shadow-md ring-2 ring-her-seal/30", className)}
    >
      <svg viewBox="0 0 24 24" className="size-5/12 fill-current">
        <path d="M12 2.5l2.9 6.1 6.6.8-4.9 4.6 1.3 6.5L12 17.3l-5.9 3.2 1.3-6.5L2.5 9.4l6.6-.8z" />
      </svg>
    </span>
  );
}
