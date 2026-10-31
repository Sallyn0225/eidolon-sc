import type { ReactNode } from "react";

import { NavShell } from "@/components/app/NavShell";
import { DirectoryProvider } from "@/components/conversations/ConversationDirectory";
import { LetterProvider } from "@/components/letter/LetterProvider";

/**
 * 导航外壳：对话（列表和她的对话页）和设置共用的 layout（.scratch/app-navigation「路由和外壳」）。
 * 对话目录由这里持有，整个外壳只载入一次，在对话和设置之间换页时不重新载入。
 * 通话也由这里持有（ADR-0018）：在外壳里换页不挂断，不在她的对话页上时顶上一条通话条（NavShell）。
 * 记忆是设置的一类，在外壳里；后台、`/about`、隐私政策、使用条款、登录、同意条款在外壳外面。
 */
export default function NavLayout({ children }: { children: ReactNode }) {
  return (
    <DirectoryProvider>
      {/* PROTOTYPE（prototype/letters-ui）：信箱原型的假数据源和切换条。 */}
      <LetterProvider>
        <NavShell>{children}</NavShell>
      </LetterProvider>
    </DirectoryProvider>
  );
}
