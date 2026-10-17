"use client";

import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { copy } from "@/i18n";
import { photoImageUrl } from "@/lib/api";

const t = copy.conversation.photo;

/**
 * 点开放大的照片（DESIGN.md「Chat bubbles · 照片」）：整屏压 85% 黑，照片居中放到最大。
 * 对话记录里的照片块和通话层上的照片都用它。
 */
export function PhotoViewer({ id, open, onOpenChange }: { id: string; open: boolean; onOpenChange: (open: boolean) => void }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent variant="viewer">
        <DialogTitle className="sr-only">{t.viewer}</DialogTitle>
        <img src={photoImageUrl(id)} alt={t.sent} className="max-h-full max-w-full rounded-lg object-contain" />
      </DialogContent>
    </Dialog>
  );
}
