// What is said while she looks something up in a turn (GLOSSARY.md「查看」, DESIGN.md「Chat bubbles」
// 「台词卡」): her reply under way in the conversation, and the call layer's line card, say what.

import { copy } from "@/i18n";
import type { Look } from "@/lib/api";

const t = copy.conversation;

/** 「櫻木真乃正在看天气、翻日程」：她的全名，看的几样按她看的顺序用「、」连起来。 */
export function lookingUpText(name: string, what: readonly Look[]): string {
  return t.lookingUp(name, what.map((look) => t.looks[look]).join("、"));
}
