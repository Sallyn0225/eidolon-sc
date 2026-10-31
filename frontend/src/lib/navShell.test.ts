import { describe, expect, it } from "vitest";

import {
  currentNavItem,
  departure,
  isConversationPage,
  isGiftsSubpageInView,
  isInShell,
  isTyping,
  navDestination,
  navDots,
  navItems,
  showsNav,
  showsShellCallBar,
} from "@/lib/navShell";

describe("在不在导航外壳里", () => {
  it.each([
    "/conversations",
    "/conversation/mano",
    "/conversation/mano?x=1",
    "/moments",
    "/settings",
    "/settings?tab=own-keys",
    "/settings/own-keys",
    "/play",
    "/play/gifts",
    "/play/gifts?to=mano",
    "/play/achievements",
  ])("%s 在外壳里", (href) => {
    expect(isInShell(href)).toBe(true);
  });

  it.each([
    "/",
    "/about",
    "/privacy",
    "/terms",
    "/admin",
    "/admin/users/1",
    "/login",
    "/consent",
    "/conversation",
    "/conversations-old",
    "/settingsx",
    "/moments/1",
    "/momentsx",
    "/gifts",
    "/gifts?to=mano",
    "/gifts/cake",
    "/player",
    "/play/xxx",
    "/api/auth/link/google",
  ])("%s 在外壳外面", (href) => {
    expect(isInShell(href)).toBe(false);
  });

  it("别的网站上的网址不算，哪怕路径一样", () => {
    expect(isInShell("https://github.com/conversations")).toBe(false);
  });
});

describe("是不是她的对话页（信不在上面弹）", () => {
  it("她的对话页是，别的页面不是", () => {
    expect(isConversationPage("/conversation/mano")).toBe(true);
    expect(isConversationPage("/conversations")).toBe(false);
  });
});

describe("外壳顶上的通话条", () => {
  it("没在通话时哪里都没有", () => {
    expect(showsShellCallBar("/settings", null)).toBe(false);
    expect(showsShellCallBar("/conversations", null)).toBe(false);
  });

  it("通话中在设置、玩法页和它的子页、对话列表、别人的对话页上出现", () => {
    expect(showsShellCallBar("/settings", "mano")).toBe(true);
    expect(showsShellCallBar("/play", "mano")).toBe(true);
    expect(showsShellCallBar("/play/gifts", "mano")).toBe(true);
    expect(showsShellCallBar("/play/achievements", "mano")).toBe(true);
    expect(showsShellCallBar("/settings?tab=call", "mano")).toBe(true);
    expect(showsShellCallBar("/conversations", "mano")).toBe(true);
    expect(showsShellCallBar("/conversation/hiori", "mano")).toBe(true);
    expect(showsShellCallBar("/moments", "mano")).toBe(true);
  });

  it("她自己的对话页上不出现：那里有页首下面那条", () => {
    expect(showsShellCallBar("/conversation/mano", "mano")).toBe(false);
  });

  it("外壳外面不出现", () => {
    expect(showsShellCallBar("/admin", "mano")).toBe(false);
  });
});

describe("去某个网址时通话怎么样", () => {
  it("没在通话时哪里都直接走", () => {
    for (const to of ["/conversations", "/conversation/hiori", "/settings", "/admin", "/about"])
      expect(departure(to, null), to).toBe("go");
  });

  it("通话中在外壳里换页，通话留着", () => {
    expect(departure("/conversations", "mano")).toBe("keep");
    expect(departure("/settings", "mano")).toBe("keep");
    expect(departure("/settings?tab=own-keys", "mano")).toBe("keep");
    expect(departure("/settings/memories", "mano")).toBe("keep");
    expect(departure("/play", "mano")).toBe("keep");
    expect(departure("/play/gifts?to=hiori", "mano")).toBe("keep");
    expect(departure("/play/achievements", "mano")).toBe("keep");
    expect(departure("/moments", "mano")).toBe("keep");
  });

  it("通话中回她自己的对话页，通话留着", () => {
    expect(departure("/conversation/mano", "mano")).toBe("keep");
  });

  it("通话中打开另一位角色的对话，先问再挂断", () => {
    expect(departure("/conversation/hiori", "mano")).toBe("ask");
  });

  it("通话中离开外壳，先问再挂断", () => {
    for (const to of ["/admin", "/about", "/privacy", "/terms", "/", "/api/auth/link/google"])
      expect(departure(to, "mano"), to).toBe("ask");
  });
});

describe("导航栏和 dock 的当前项", () => {
  it.each([
    ["/conversation/mano", "conversations"],
    ["/moments", "moments"],
    ["/settings", "settings"],
    ["/settings/own-keys", "settings"],
    ["/play", "play"],
    ["/play/gifts?to=mano", "play"],
    ["/play/achievements", "play"],
  ] as const)("%s 的当前项是 %s", (href, item) => {
    expect(currentNavItem(href)).toBe(item);
  });

  it("外壳外面没有当前项", () => {
    expect(currentNavItem("/admin")).toBeNull();
  });
});

describe("导航栏和 dock 上有哪几项", () => {
  it("朋友圈开着时四项：对话、朋友圈、玩法、设置", () => {
    expect(navItems(true)).toEqual(["conversations", "moments", "play", "settings"]);
  });

  it("账号里朋友圈为空（部署者关着）、用户关了或账号还没读到时没有「朋友圈」", () => {
    for (const moments of [null, false, undefined])
      expect(navItems(moments), String(moments)).toEqual(["conversations", "play", "settings"]);
  });

  it("「朋友圈」去 /moments", () => {
    expect(navDestination("moments", "/conversations")).toBe("/moments");
    expect(navDestination("moments", "/moments")).toBeNull();
  });
});

describe("礼物子页在不在眼前（到账当场记成看过）", () => {
  it("在礼物子页上就在眼前，带着预选的也是", () => {
    expect(isGiftsSubpageInView("/play/gifts", false)).toBe(true);
    expect(isGiftsSubpageInView("/play/gifts?to=mano", false)).toBe(true);
  });

  it("通话层展开着盖住礼物子页时不在眼前", () => {
    expect(isGiftsSubpageInView("/play/gifts", true)).toBe(false);
  });

  it("玩法页第一级和成就子页不算", () => {
    expect(isGiftsSubpageInView("/play", false)).toBe(false);
    expect(isGiftsSubpageInView("/play/achievements", false)).toBe(false);
  });

  it("别的页面上不在眼前", () => {
    expect(isGiftsSubpageInView("/conversation/mano", false)).toBe(false);
    expect(isGiftsSubpageInView("/gifts", false)).toBe(false);
  });
});

describe("导航栏、dock 上的点", () => {
  const both = { conversations: true, rewards: true, moments: false };

  it("「对话」有没看过的搭话、「玩法」有新到的抽奖次数时各亮各的", () => {
    expect(navDots("settings", both)).toEqual({ conversations: true, moments: false, play: true, settings: false });
    expect(navDots("settings", { conversations: false, rewards: true, moments: false })).toEqual({
      conversations: false,
      moments: false,
      play: true,
      settings: false,
    });
    expect(navDots("settings", { conversations: true, rewards: false, moments: false }).play).toBe(false);
  });

  it("当前项是「玩法」时「玩法」不亮，别的照旧", () => {
    expect(navDots("play", both)).toEqual({ conversations: true, moments: false, play: false, settings: false });
  });

  it("在外壳外面（没有当前项）时照常", () => {
    expect(navDots(null, both).play).toBe(true);
  });

  it("有新的动态或她的回复时「朋友圈」上有点，别的照旧", () => {
    expect(navDots("conversations", { conversations: false, rewards: false, moments: true })).toEqual({
      conversations: false,
      moments: true,
      play: false,
      settings: false,
    });
  });

  it("在朋友圈页上「朋友圈」不亮，别的照旧", () => {
    expect(navDots("moments", { ...both, moments: true })).toEqual({
      conversations: true,
      moments: false,
      play: true,
      settings: false,
    });
  });
});

describe("点导航栏、dock 里的一项去哪", () => {
  it("点别的项，去那一项的第一级", () => {
    expect(navDestination("settings", "/conversation/mano")).toBe("/settings");
    expect(navDestination("play", "/settings/call")).toBe("/play");
  });

  it("在二级页面上（她的对话页、玩法的子页、设置的一类）再点当前那一项，回到这一项的第一级", () => {
    expect(navDestination("conversations", "/conversation/mano")).toBe("/conversations");
    expect(navDestination("play", "/play/gifts")).toBe("/play");
    expect(navDestination("play", "/play/achievements?x=1")).toBe("/play");
    expect(navDestination("settings", "/settings/call")).toBe("/settings");
  });

  it("已经在第一级时再点当前那一项，不动", () => {
    expect(navDestination("conversations", "/conversations")).toBeNull();
    expect(navDestination("play", "/play")).toBeNull();
  });
});

describe("手机上在打字（dock 藏起来）", () => {
  it.each([
    ["textarea", { tagName: "TEXTAREA" }],
    ["搜索框", { tagName: "INPUT", type: "search" }],
    ["可编辑元素", { tagName: "DIV", isContentEditable: true }],
  ])("焦点在%s上算", (_, focused) => {
    expect(isTyping(focused)).toBe(true);
  });

  it.each([
    ["没有焦点", null],
    ["勾选框", { tagName: "INPUT", type: "checkbox" }],
    ["按钮", { tagName: "BUTTON" }],
  ])("%s不算", (_, focused) => {
    expect(isTyping(focused)).toBe(false);
  });
});

describe("导航栏和 dock", () => {
  it("外壳里别的页上都有", () => {
    expect(showsNav("/play/cycles")).toBe(true);
  });

  it("酒吧盖住它们，通话条照旧在最上面", () => {
    expect(showsNav("/play/bar")).toBe(false);
    expect(isInShell("/play/bar")).toBe(true);
    expect(showsShellCallBar("/play/bar", "mano")).toBe(true);
    expect(departure("/play/bar", "mano")).toBe("keep");
  });
});
