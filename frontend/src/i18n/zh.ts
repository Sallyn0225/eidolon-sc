// 简体中文界面文案。新界面上的每一句话都从这里取（经 `@/i18n` 的 copy），不在组件里写死。
// 按界面分组；带参数的句子写成函数，参数的位置由各语言自己决定。
// 术语以 GLOSSARY.md 为准（对话、通话、通话层、麦克风静音、只看文字、印象色……）。

import type { Occasion } from "@/lib/letter";

/** 思考强度和额外请求参数的说明：后台的模型和设置页的自带 LLM 共用，措辞保持一致。 */
const reasoningEffortHints = {
  effort:
    "不设置时什么都不发，交给模型自己的默认；其他档原样发给服务，服务不支持时试调会报错。用额外请求参数控制思考时选「不设置」。",
  callEffort:
    "通话里的回合用这一档，文字对话用上面那一档。不设置时通话里什么都不发，不沿用文字那一档；想让她在通话里开口快一些，可以只把这一项设成「关闭」或「低」。两档不同时，保存时各试调一次。",
  extraBody:
    '一个 JSON 对象，深合并进每次请求，能覆盖思考强度生成的参数，例如 Qwen 的 {"enable_thinking": false}。不能包含 model、messages、tools 这类由服务器生成的字段。',
};

/** 思考强度和额外请求参数填错时的提示，`field` 是那一项的名字。后台和设置页共用。 */
const reasoningEffortProblems = {
  effort: (field: string) => `Anthropic 接口没有「极低」这一档，请给${field}换一档。`,
  json: (field: string) => `${field}不是合法的 JSON。`,
  jsonObject: (field: string) => `${field}需要是一个 JSON 对象（用 { } 括起来），留空表示不设置。`,
};

export const zh = {
  app: {
    name: "Eidolon-SC",
    description: "和 283 事务所的偶像说说话",
    /** 链到项目仓库的那个链接：落地页右上角的字，导航栏底部（电脑）图标键的读屏名字。 */
    repositoryLabel: "GitHub",
  },
  /** 导航外壳的导航栏（电脑）和 dock（手机），DESIGN.md「Layout」。 */
  nav: {
    label: "导航",
    conversations: "对话",
    /** 「对话」图标上有点时读屏读的名字：列表里有一行有没看过的搭话。 */
    conversationsUnseen: "对话，有没看过的搭话",
    moments: "朋友圈",
    /** 「朋友圈」图标上有点时读屏读的名字：上次打开以后露出了新动态或她的回复。 */
    momentsUnseen: "朋友圈，有新动态",
    play: "玩法",
    /** 「玩法」图标上有点时读屏读的名字：有新到的抽奖次数。 */
    playRewarded: "玩法，有新到的抽奖次数",
    settings: "设置",
  },
  /** 朋友圈页（GLOSSARY.md「朋友圈」，DESIGN.md「朋友圈页」）。 */
  moments: {
    title: "朋友圈",
    empty: "还没有动态",
    /** 时间线一行的时间（lib/moments 的 `postedText`）。 */
    justNow: "刚刚",
    minutesAgo: (n: number) => `${n} 分钟前`,
    hoursAgo: (n: number) => `${n} 小时前`,
    yesterday: "昨天",
    daysAgo: (n: number) => `${n} 天前`,
    /** 天气图标读屏读的档位名。 */
    weather: { clear: "晴", cloudy: "多云", overcast: "阴", fog: "雾", rain: "雨", snow: "雪", thunder: "雷雨" },
    /** 一条动态下面那一块：赞的人之间的分隔，心形读屏读的名字，评论里名字和日语之间。 */
    likersSeparator: "，",
    likedBy: "赞",
    commentedBy: (name: string) => `${name}：`,
    /** 赞的一行和评论区里制作人自己的名字；她回他的评论打头。 */
    producer: "制作人",
    repliedBy: (name: string) => `${name} 回复 制作人：`,
    /** 行尾「⋯」：读屏读的按钮名和里面的几项。 */
    actions: { open: "赞或评论", like: "赞", unlike: "取消赞", comment: "评论", uncomment: "删除评论" },
    /** 「删除评论」先确认：她的回复会一起删。 */
    uncomment: { title: "删除评论？", description: "她的回复也会一起删掉。", confirm: "删除" },
    /** 评论输入：输入框读屏读的名字、占位、发送键，几个字（超了才显示）。 */
    commentBox: {
      label: "评论",
      placeholder: (name: string) => `评论${name}的动态`,
      send: "发送",
      count: (n: number, most: number) => `${n}/${most}`,
    },
    /** 配图的缩略图：读屏读的按钮名、图的替代文字，放大后弹窗的名字。 */
    picture: { open: "放大配图", alt: "她的配图", viewer: "配图" },
  },
  /** 落地页的链接贴到聊天软件、社交网站时预览卡片上的文字（Open Graph、Twitter 卡片）。页面上不显示，不进字体子集。 */
  share: {
    title: "Eidolon-SC · 和 283 事务所的偶像说说话",
    description: "她们用自己的声音说日语，配中文字幕；可以给她打电话，她还会记得你说过的事。非官方粉丝作品，角色由 AI 扮演。",
  },
  common: {
    back: "返回",
    close: "关闭",
    more: "更多",
    cancel: "取消",
    optional: "可选",
  },
  /** 能自带密钥的几项服务（GLOSSARY.md「自带密钥」），列在一句话里时的名字。 */
  ownServices: { llm: "LLM", tts: "语音合成", stt: "语音识别", image: "生图" },
  /** 把几项服务列成一句：「LLM」「LLM 和语音识别」「LLM、语音合成和语音识别」。 */
  serviceList: { separator: "、", last: "和" },
  /** 思考强度（GLOSSARY.md「思考强度」）的各档：下拉框里中文名后面括号写发给服务的原值。 */
  reasoningEffort: {
    unset: "不设置",
    names: { none: "关闭", minimal: "极低", low: "低", medium: "中", high: "高", xhigh: "极高", max: "最高" } as Record<string, string>,
    option: (name: string, value: string) => `${name}（${value}）`,
    hints: reasoningEffortHints,
    problems: reasoningEffortProblems,
    /** 档位提示（ADR-0019）：models.dev 里查得到这个模型时，下拉框里目录没写的档位旁边的标注，和下拉框下面的一句话。 */
    catalog: {
      unlisted: "models.dev 未列出",
      source: (provider: string, model: string) => `据 models.dev 里 ${provider} 的 ${model}：`,
      efforts: (names: string) => `支持${names}`,
      separator: "、",
      noEfforts: "不按档位调节",
      turnsOff: {
        by_effort: "可以关闭思考",
        by_switch: "用它自己的开关关闭思考，「关闭」不一定管用，可以改用额外请求参数关",
        none: "不能关闭思考",
      },
      doesNotThink: "这个模型不思考",
      onlyAHint: "仅供参考，不影响保存。",
    },
  },
  /** 选 LLM 的服务商和模型（ADR-0027）：设置页的自带 LLM 和后台的模型共用。 */
  llmPicker: {
    provider: "服务商",
    providerHint: "选你用的服务商或编程套餐，接口类型和地址会自动填好。找不到就选「手动填写」。",
    manual: "手动填写",
    search: "搜索服务商，例如 DeepSeek、智谱、Coding Plan",
    noProvider: "没有找到这家，可以选「手动填写」",
    model: "选择模型",
    modelHint: "选了会填好下面的模型名和接口类型。列表里没有的，直接填模型名。",
    modelPlaceholder: "从列表里选",
    modelSearch: "搜索模型",
    noModel: "没有找到这个模型，可以直接在模型名里填",
    fetch: "获取可用模型",
    fetching: "获取中…",
    fetched: (n: number) => `服务商列出了 ${n} 个模型。`,
    fetchNeedsKey: "填好接口地址和 API key 后可以获取。",
  },
  conversationList: {
    title: "对话",
    noneSelected: "选一位偶像开始对话",
    resize: "调整对话列表宽度",
    /** 列表顶上的搜索框：按名字（原名、中文译名、假名、罗马字）或组合找偶像。 */
    search: "搜索名字或组合",
    noMatch: "没有找到这位偶像",
    /** 最后一句是制作人自己说的。 */
    you: (text: string) => `你：${text}`,
    /** 最后一句前的相机图标（她最后发来了照片），给读屏读的。 */
    photo: "照片：",
    neverTalked: "还没有对话",
    nothingSaidYet: "新的对话，还没有说话",
    yesterday: "昨天",
    monthDay: (month: string, day: string) => `${month}月${day}日`,
    fullDate: (year: string, month: string, day: string) => `${year}/${month}/${day}`,
    loading: "正在载入对话列表",
    loadFailed: "对话列表没能载入",
    retry: "重试",
    /** 一行的右键、长按菜单（GLOSSARY.md「隐藏 / 置顶」）。 */
    pin: "置顶",
    unpin: "取消置顶",
    hide: "在列表中隐藏",
    show: "在列表中显示",
    /** 置顶那一行时间旁边的图钉，给读屏读的。 */
    pinned: "已置顶",
    /** 时间前面她颜色的小圆点（GLOSSARY.md「没看过的搭话」），给读屏读的。 */
    unseen: "有没看过的搭话",
    /** 搜索框右边的筛选按钮；有人被隐藏时读出人数。 */
    filter: "筛选列表",
    filterHidden: (count: string) => `筛选列表，已隐藏 ${count} 位`,
    /** 筛选面板：按组合分组的勾选清单。 */
    filterTitle: "列表里显示谁",
    showAll: "全部显示",
    /** 没有组合的角色（事务员はづき）放在最后这一组。 */
    noUnit: "283プロ",
    /** 列表底部、免责声明上面那一行，点了打开筛选面板。 */
    hiddenCount: (count: string) => `已隐藏 ${count} 位`,
    allHidden: "所有角色都隐藏了",
    chooseShown: "选择显示谁",
    /** 页首的铃铛和它打开的公告弹窗（GLOSSARY.md「公告」「未读公告」）。 */
    announcements: "公告",
    announcementsUnread: "公告，有未读",
    noAnnouncements: "还没有公告",
    /** 一次都还没拉到公告时，弹窗里写的。 */
    announcementsLoading: "正在载入公告",
    announcementsLoadFailed: "公告没能载入，稍后再试",
    /** 没读过的那条公告，日期后面的标记。 */
    unreadAnnouncement: "新",
    /** 置顶的那条公告，日期后面的标记。 */
    pinnedAnnouncement: "置顶",
    markAnnouncementsRead: "已读",
    /** 铃铛旁边的服务状态和它打开的小窗口（GLOSSARY.md「服务状态」）；有服务不正常时按钮念后一句。 */
    serviceStatus: "服务状态",
    serviceStatusFailing: "服务状态，有服务不正常",
    serviceStatusNames: {
      chat_llm: "对话",
      memory_llm: "记忆",
      tts: "语音合成",
      stt: "语音识别",
      judge: "判断",
      embedding: "检索",
      rerank: "重排",
      image: "照片",
    },
    serviceStatuses: { ok: "正常", unsteady: "不稳定", down: "故障", idle: "最近没有调用" },
    serviceStatusWindow: (minutes: number) => `最近 ${minutes} 分钟`,
  },
  conversation: {
    back: "返回对话列表",
    menu: "更多操作",
    /** 她有没看过的成就解锁时，更多菜单键的读屏名字。 */
    menuUnseen: "更多操作，有新解锁的成就",
    newConversation: "新对话",
    /** 更多菜单里去日历子页、只看她的那一项（日程开着时才有）。 */
    herSchedule: "她的日程",
    call: (name: string) => `和${name}通话`,
    callTooltip: "语音通话",
    placeholder: "用中文或日语说点什么",
    send: "发送",
    /** 消息区里跨天处的日期条；昨天、更早的写法和列表一样（conversationList）。 */
    today: "今天",
    emptyTitle: (name: string) => `和${name}打个招呼吧`,
    emptyDescription: "打字，或者点右上角的电话和她通话。",
    replying: (name: string) => `${name}正在回复`,
    /** 对话事件（GLOSSARY.md「对话事件」）给用户看的一句话：消息区的分隔线和列表的「最后一句」都用它。 */
    events: {
      hung_up: (name: string) => `${name}挂断了电话`,
      gift: (name: string, gift: string) => `你送给${name}一份${gift}`,
      ended: (name: string) => `${name}结束了对话`,
      /** 她经期里用户第一次来时记下的（只给用户看）：`since` 是 `unwellSince` 拼出的那几个字。 */
      unwell: (name: string, since: string) => `${name}好像从${since}起就不太舒服`,
    },
    /** 她不太舒服从哪天起：早 0、1、2 天写词，再早写日期（两边留空格，「从 10月21日 起」）。 */
    unwellSince: {
      days: ["今天", "昨天", "前天"],
      date: (month: number, day: number) => ` ${month}月${day}日 `,
    },
    /** 她结束了对话（GLOSSARY.md「已结束的对话」）时换掉输入栏的结束卡：那句话同对话事件（`events.ended`），不写原因；
     * 她在冷却中时换成 `cooling`，写上解除时刻。 */
    ended: {
      cooling: (name: string, until: string) => `${name}结束了对话。${until} 以后可以再找她`,
      newConversation: "开个新对话",
    },
    /** 更多菜单里的「历史对话」、它打开的面板和历史对话的只读页（GLOSSARY.md「当前对话」「历史对话」）。 */
    past: {
      open: "历史对话",
      title: "历史对话",
      description: (name: string) => `和${name}的所有对话，最新的在上面。`,
      /** 面板里只有当前对话这一行时，下面那句说明。 */
      onlyCurrent: "开了新对话以后，之前的对话会留在这里。",
      current: "当前",
      ended: "她结束了",
      loading: "正在读取历史对话",
      loadFailed: "历史对话没能读取",
      retry: "再试一次",
      /** 行里和页首的日期：北京时间，今年的写月日（同 conversationList.monthDay），不是今年的带上年份。 */
      yearMonthDay: (year: string, month: string, day: string) => `${year}年${month}月${day}日`,
      /** 历史对话页首名字下面那一行。 */
      heading: (day: string) => `${day}的对话`,
      opening: "正在打开这段对话",
      openFailed: "这段对话没能打开",
      /** 换掉输入栏的只读卡。 */
      readOnly: "这是你们的历史对话",
      readOnlyEnded: "这是你们的历史对话，她结束了它",
      backToCurrent: "回到当前对话",
      /** 历史对话里禁用的电话键的提示。 */
      callTooltip: "回到当前对话才能打电话",
      /** 面板里历史对话那几行右端的删除键和它的确认框；`label` 是对话标题，没有标题时是日期。 */
      remove: "删除",
      removeLabel: (label: string) => `删除对话：${label}`,
      removeTitle: (label: string) => `删除「${label}」？`,
      removeDescription:
        "这段对话里的消息、通话记录和送礼记录都会彻底删除，无法恢复。她在这段对话里记下的事不受影响，可以在设置的「记忆」里删除。",
    },
    /** 她发来的照片（GLOSSARY.md「照片」）：对话记录里的照片块、点开放大，和没发出来时的说明。 */
    photo: {
      pending: "照片正在生成",
      sent: "她发来的照片",
      open: "放大照片",
      viewer: "照片",
      failed: "照片没发出来",
      /** 没发出来的原因，按后端的 `store.PhotoFailure`；不认识的原因按生图服务出错说。 */
      reasons: {
        timeout: "等太久了",
        service_error: "生图服务出错了",
        bad_image: "生成的图不对",
        own_key_failed: "你的生图密钥没能用",
        used_up: "这一小时的照片用完了",
      },
      toOwnKeys: "去设置自带密钥",
      /** 照片用完时她那条回复后面的胶囊；`time` 是 HH:MM。 */
      usedUp: (time: string) => `这一小时的照片用完了，${time} 以后可以再要`,
    },
    /** 她的一条话的菜单和下面的语音条（GLOSSARY.md「朗读」）。没合成出来时那一行写后端给的原因。 */
    readAloud: {
      menu: "朗读",
      voicing: "正在合成语音",
      play: "播放",
      pause: "暂停",
      retry: "再试一次",
      toOwnKeys: "去设置自带密钥",
      /** 这一小时的朗读次数用完了；`time` 是 HH:MM，按制作人的时区。 */
      usedUp: (time: string) => `这一小时的朗读次数用完了，${time} 以后可以再听`,
    },
    hearing: "正在听你说",
    loading: "正在打开对话",
    loadFailed: "对话没能打开",
    notFound: "没有这位角色",
    backToList: "回到对话列表",
    /** 失败时说明这次算不算进限额（GLOSSARY.md「限额」「回合」）。 */
    notCounted: "这次没有计入限额。",
    /** 文字回合撞上限额：带上自己的 LLM 就不计入，不论这个部署的免限额密钥是哪几项（GLOSSARY.md「免限额密钥」）。 */
    ownLLMExempts: "带上自己的 LLM，文字对话就不受限额。",
    /** 页首的好感度标识和它点开的说明（GLOSSARY.md「好感度」「冷却」）。只说档位，不说数值。 */
    affinity: {
      tiers: { cold: "冷淡", distant: "疏远", trust: "信任", close: "亲近", intimate: "亲密" },
      /** 每一档的大意，写在说明里档名下面。 */
      notes: {
        cold: "她对你明显冷淡，话很少。",
        distant: "她有点生气或失望，比平时冷一些。",
        trust: "你们一直以来的关系。",
        close: "她比平时更放松，更愿意和你说心里话。",
        intimate: "她非常信赖你，会说平时不轻易说的心事。",
      },
      label: (tier: string) => `你们的关系：${tier}`,
      title: (tier: string) => `你们现在的关系：${tier}`,
      cooling: (name: string) => `${name}现在不想说话`,
      coolingNote: (until: string) => `${until} 以后可以再找她。送她一件礼物，她会消气得快一些。`,
      /** 冷却中换掉输入栏的那一行。 */
      coolingComposer: (name: string, until: string) => `${name}现在不想说话。${until} 以后可以再找她`,
      tiersLabel: "五个档位",
      rule: "她对你的态度会随你说的话变化。低于「信任」时，不联系也会慢慢回到「信任」。",
      /** 解除时刻：按制作人的时区写成今天或明天加时刻。 */
      today: "今天",
      tomorrow: "明天",
      /** 回合改变了好感度时，她那条回复后面的胶囊、通话层的状态行。 */
      cues: {
        cooldown: (name: string) => `${name}现在不想说话了`,
        closer: (name: string, tier: string) => `和${name}更近了一步：${tier}`,
        further: (name: string, tier: string) => `${name}和你疏远了一些：${tier}`,
        happier: (name: string) => `${name}有点开心`,
        unhappier: (name: string) => `${name}有点不高兴`,
        /** 送礼让她解除了冷却。 */
        thawed: (name: string) => `${name}愿意和你说话了`,
      },
    },
    /** 页首的「换衣装」和它打开的面板（spec「衣装与换衣装」）。 */
    outfits: {
      open: "换衣装",
      title: "换衣装",
      hint: "打电话时她会穿这一套；只存在这台设备上。",
      loading: "正在读取衣装",
      loadFailed: "衣装没能读取",
      retry: "再试一次",
      /** 卡片下面的切换：私服 / 演出。 */
      lookLabel: (card: string) => `${card}的私服或演出服`,
      looks: { everyday: "私服", stage: "演出" },
      only: "只有一套",
      /** 大预览下面：卡名，「私服/演出服 · 稀有度 · 正在穿」。 */
      cardName: (card: string) => `【${card}】`,
      lookNames: { everyday: "私服", stage: "演出服" },
      wearing: "正在穿",
      separator: " · ",
      notLoaded: "这套没能载入",
      wear: "穿这套",
      preview: (card: string) => `预览${card}`,
    },
  },
  /** 通话层、收起后的通话条、列表里的通话状态（spec「通话层」「通话状态」）；换一位角色、离开导航外壳前的确认框。 */
  call: {
    leaveTitle: (name: string) => `会挂断和${name}的通话`,
    leaveDescription: "离开这里，正在进行的通话就会挂断。",
    leaveConfirm: "挂断并离开",
    stay: "留在这里",
    layer: (name: string) => `和${name}的通话`,
    collapse: "收起通话",
    collapseTooltip: "收起（Esc）",
    /** 通话中，页首的电话键变成这个。 */
    expand: "回到通话",
    textOnly: "只看文字",
    dialing: "正在呼叫…",
    /** 通话层的状态行：后面跟着三个依次闪的小点，所以不带省略号。 */
    calling: "正在呼叫",
    remaining: (clock: string) => `还剩 ${clock}`,
    speakFreely: "直接说话就好",
    repliesInText: "她会用文字回复",
    hearing: (text: string) => `你：${text}…`,
    /** 通话里打出去的话，她开口前留在台词卡底部。 */
    typed: (text: string) => `你：${text}`,
    /** 底栏的打字键；点了底栏换成输入栏。 */
    type: "打字",
    closeTyping: "收起输入栏",
    micMute: "麦克风静音",
    micUnmute: "取消麦克风静音",
    hangUp: "挂断",
    switchMic: "切换麦克风",
    micSheet: {
      title: "切换麦克风",
      systemDefault: "系统默认",
      numbered: (n: number) => `麦克风 ${n}`,
      hint: "选中的麦克风当场换上，也会成为以后通话的默认麦克风。",
      inUse: "正在使用",
    },
    /** 麦克风出了状况：选定的不在，或者刚选的打不开。 */
    micNotices: {
      fell_back: "没有找到选定的麦克风，已改用系统默认",
      unavailable: "没能打开这个麦克风，仍在用原来的",
      lost: "麦克风断开了，也没有别的麦克风可用",
    },
    /** 通话里她发来的照片（spec「通话层」）：电脑上台词卡上方的小卡，手机上的一颗胶囊；收起时外壳顶上通话条的提示。 */
    photo: {
      taking: "正在拍照…",
      sent: "发来一张照片 · 点开看",
      open: "放大她发来的照片",
      /** `reason` 是 `photoFailureNote(reason).reason`。 */
      failed: (reason: string) => `照片没发出来 · ${reason}`,
      newPhoto: "新照片",
    },
    /** 消息列表里她那一行，也是收起后页首下面那条通话条上的字（呼叫中用 dialing）。 */
    listConnected: (clock: string) => `通话中 ${clock}`,
    ended: "通话已结束",
    /** 接通过的通话结束后，状态行带上通话时长。 */
    endedAfter: (clock: string) => `通话已结束 · ${clock}`,
    /** 是否计入限额（GLOSSARY.md「限额」「接通」）。 */
    counted: "这次通话计入每小时的限额。",
    notCounted: "这次通话不计入每小时的限额。",
    backToConversation: "回到对话",
    redial: "重拨",
    /** 她挂断了（不该说的话说多了，或者跌进冷却）：结束卡的标题；冷却的多一行解除时刻。 */
    hungUp: (name: string) => `${name}挂断了电话。`,
    hungUpCooling: (until: string) => `她现在不想说话，${until} 以后可以再找她。`,
    toOwnKeys: "去设置自带密钥",
    endings: {
      not_connected: {
        title: "没能接通",
        body: "通话没有连上，可能是网络或语音服务出了问题。可以稍后重拨。",
      },
      dropped: {
        title: "通话中断了",
        body: "网络或语音服务出了问题，通话在中途断开。已经说完的回合都记在对话里。",
      },
      duration_limit: {
        title: "这次通话到时长上限了",
        body: "单次通话的时长上限对所有人都一样。想接着聊，可以马上重拨。",
      },
      turn_limit: {
        title: "这次通话说到回合数上限了",
        body: "单次通话的回合数上限对所有人都一样。想接着聊，可以马上重拨。",
      },
      over_limit: {
        /** 撞上每小时的次数，或者单独限额设成了零：哪一种由后端的原话（detail）说。 */
        title: "通话次数超出了限额",
        /** 点名这个部署的免限额密钥（GLOSSARY.md「免限额密钥」），经 `sayServices` 拼上服务名。 */
        body: (services: string) => `这个部署上，带上自己的${services}的通话不计入限额。`,
      },
      busy: {
        title: "现在打电话的人太多",
        body: "稍后再拨一次试试。",
      },
      own_key: {
        title: "你的自带密钥出错了",
        body: "自带密钥调用失败时，不会悄悄改用部署者的密钥。检查一下设置页里的密钥再重拨。",
      },
      mic_denied: {
        title: "用不了麦克风",
        body: "浏览器没有允许本页使用麦克风，或者找不到麦克风。在地址栏旁的权限设置里允许麦克风，然后重拨。",
      },
    },
  },

  /** 信（GLOSSARY.md「信」，lib/letter）。 */
  letter: {
    /** 对话列表页首的信封键，读屏名字；有没读过的信时换一句。 */
    box: "信",
    boxUnread: "信，有没读过的",
    /** 信封键点开的列表的标题，和没有信时的一行。 */
    listTitle: "信",
    none: "还没有信",
    /** 所有的信里，没读过的那一组的标题；其余按月分组，组名是月份。 */
    unread: "没读过",
    /** 她的对话页页首、电话键旁的信封键：读屏名字，有没读过的信时换一句；点开的标题是 `title`。 */
    hers: (name: string) => `${name}的信`,
    hersUnread: (name: string) => `${name}的信，有没读过的`,
    /** 对话列表上她那一行名字后面的小信封，读屏读这一句。 */
    unreadMark: "有没读过的信",
    /** 列表里一封信的右键（长按）菜单，和确认框。 */
    remove: "删除这封信",
    removeTitle: (name: string) => `删除${name}的这封信？`,
    removeDescription: "信和她念信的声音都会彻底删除，无法恢复。",
    removeConfirm: "删除",
    loadFailed: "信没能载入",
    /** 信封上写的场合，越短越好；几个场合合在一封时用「、」连起来。 */
    occasions: {
      close: "更近了一步",
      intimate: "亲密",
      complete: "集齐",
      her_birthday: "她的生日",
      producer_birthday: "你的生日",
      anniversary: "相识纪念",
    } satisfies Record<Occasion, string>,
    /** 列表里一枚信封的读屏名字。 */
    row: (name: string, occasion: string, day: string, isUnread: boolean) =>
      `${name}的信，${occasion}，${day}${isUnread ? "，没读过" : ""}`,
    /** 整封信的读屏名字。 */
    title: (name: string) => `${name}的信`,
    /** 信封本身是个按钮：读屏名字，和信封下面那行小字。 */
    open: (name: string) => `拆开${name}的信`,
    openHint: "拆开",
    /** 读信时右上角的静音键，读屏名字（按下去是静音）。 */
    mute: "静音",
    skip: "跳过",
    done: "收好",
  },

  // —— 以下是登录、同意、设置、记忆和静态页（ticket 06）——
  // 句中带链接的文案用 {名字} 占位，经 interpolate() 换成链接。

  /** 全站都要说清的声明（PRODUCT.md「Brand Commitments」）。 */
  legal: {
    disclaimer: "非官方的粉丝作品，与版权方无关。角色由 AI 扮演。",
    privacy: "隐私政策",
    terms: "使用条款",
    pageTitle: (page: string) => `${page} · Eidolon-SC`,
  },
  failure: {
    signIn: "去登录",
    /** 填上自带密钥就能解决时，和通话结束卡上的同一句。 */
    toOwnKeys: "去设置自带密钥",
  },
  login: {
    lede: "和《偶像大师 闪耀色彩》283 事务所的偶像们打电话、说话。她们会用自己的声音回答你，记得原作里和制作人一起走过的事，也会记住你告诉她们的事。",
    signInRegion: "登录",
    signInWith: (provider: string) => `用 ${provider} 登录`,
    noProviders: "部署者还没有配置登录方式。",
    agreement: "登录即表示你已阅读{privacy}和{terms}。第一次登录时会请你确认一次。",
    refusedTitle: "没能登录",
    devTitle: "开发登录",
    devHint: "后端打开了 EIDOLON_DEV_LOGIN，可以直接以这个名字的用户登录。",
    devName: "用户名",
    devSubmit: "登录",
    castTitle: "可以说话的偶像",
  },
  /** 落地页（ADR-0016）。各幕的文案由后续的 ticket 补上，都要交用户审。 */
  landing: {
    disclaimer: "非官方粉丝作品，角色由 AI 扮演。",
    signIn: "登录",
    continue: "继续",
    panelTitle: "登录",
    devSignIn: "开发登录",
    /**
     * 第 1 幕「プリズム」：白光射进棱镜，散成她们的颜色（画面上仍是分光，文字只说这是什么）。name 是竖排的
     * 日文幕名，纯装饰，和幕名轨那一格同步改。title 的人数按名单算。
     */
    act1: {
      name: "プリズム",
      title: (count: string) => `一个电话，${count} 个角色。`,
      body: "每个偶像有自己的人设，用各自的语气和你聊天。",
    },
    /** 左侧竖排的日文幕名轨，按幕的编号；还没做的幕不显示。纯装饰，读屏读 label 和各幕自己的标题。 */
    rail: {
      label: "进度",
      acts: ["序", "プリズム", "光譜", "ことば", "着信", "記憶", "ことわり", "はじまり"],
    },
    /** 第 2 幕「光谱」：按组合排开的名牌。组合名用原作的写法，不翻译。 */
    act2: {
      label: "光谱：按组合排开的偶像",
      jump: "按组合跳转",
      jumpTo: (unit: string) => `跳到 ${unit}`,
      /** 没有组合的那一段（事务员はづき），排在最后。 */
      others: "283プロ",
      /** 声音开关：第一次点偶像、听到招呼以后出现在右上角，关掉以后点偶像只显示字幕。 */
      sound: "声音",
      soundOn: "开",
      soundOff: "关",
    },
    /**
     * 第 3 幕「她说日语」：她说几句日语，竖排的原文一列列出来，中文字幕一句句被光扫出来。台词是演示用的，
     * 照她的人设写，不引用剧情原文和歌词。`speaker` 是说话的那一位（角色标识），第 4 幕打来电话的也是她；
     * 她不在名单里时换成光谱里的第一位，台词就和人对不上了，换人要连台词一起换。句数是落地页模型的 TALK_LINES。
     */
    act3: {
      title: "日语语音，中文字幕。",
      body: "小偶像说的是日语语音，口癖和语气词都原样保留；对应的中文字幕会附在下面。",
      speaker: "mano",
      lines: [
        { ja: "えっと……プロデューサーさん。", zh: "那个……制作人。" },
        { ja: "今日の空、すっごく青いですっ", zh: "今天的天空，好蓝好蓝呀。" },
        { ja: "ほわっ……一緒にお散歩、しませんか？", zh: "呼哇……要不要一起去散散步？" },
      ],
    },
    /** 第 4 幕「来电」：模拟一次她打来的电话。只有访客接听时才响起铃声和接通音。 */
    act4: {
      title: "也可以和她通电话。",
      body: "和她实时语音通话：你开口说话，她用日语回答。",
      ringing: "来电",
      connected: "通话中",
      ended: "通话结束",
      answer: "接听",
      /** 来电画面底部滑块上的字；读屏器念的是 answer。 */
      slide: "滑动接听",
      hangUp: "挂断",
    },
    /**
     * 第 5 幕「记忆」：一件事被一位偶像收进记忆、传给另一位，再从她那里传开。不出现任何剧情原文、台词或歌词。
     * `cast` 是演员（角色标识），按顺序：发送的人、接收并传开的人、再传到的两位，各站在一座浮岛上；
     * 某位不在名单里时她的岛上没有人、她的话不出现。几句话是气泡里的字，不出声；照 cast 的这几位写，换人要连这几句话一起换。
     */
    act5: {
      cast: ["mano", "kaho", "fuyuko", "kiriko"],
      title: "你对她说的事，她们都会记得。",
      body: "告诉一位偶像的近况，别的偶像之后也会知道，提起时会说是听谁讲的。她们也记得原作里和你一起走过的那些日子。",
      /** 制作人发给发送的那一位的一句（深蓝气泡）；`name` 是读屏器念的说话的人。 */
      producer: { name: "制作人", line: "下周要考试了，有点紧张。" },
      /** 发送的那一位收进记忆以前，头上冒出的气泡。 */
      thinking: "思考中…",
      /** 演员说的话，和 cast 一一对应：日语原文在上，中文字幕在下。 */
      lines: [
        { ja: "うん、覚えておきますね", zh: "我记住了。" },
        { ja: "真乃さんから聞きました！ファイトです！", zh: "听真乃说你要考试了，加油！" },
        { ja: "テストでしょ？真乃から聞いたわよ", zh: "考试？真乃跟我说了。" },
        { ja: "真乃ちゃんから……聞きました……", zh: "听真乃说了……别太勉强……" },
      ],
      /** 收到的几位的记忆柱上冒出的标签：她想起了谁告诉她的事（来源角色）。`from` 是发送那一位的称呼，和台词里一样。 */
      recalled: (from: string) => `想起 1 条记忆 · 来自${from}`,
      from: "真乃",
      /** 最后的全景下面的一句。 */
      closing: "她们会记住你的事情，然后在所有人之间传开。",
    },
    /** 第 6 幕「诚实事项」：安静、居中的短文。限额不写具体数字；登录方式从后端读取。 */
    act6: {
      title: "使用须知",
      unofficial: "非官方粉丝作品，和原作版权方无关。角色完全由 AI 驱动。",
      // 下面两句不论免限额密钥是哪几项都要对（落地页静态渲染，不随开关变化），不点名哪几项。
      limits: "部署服务不向你收费，但每人可能存在使用限额。",
      ownKey: "支持 BYOK（自带密钥），密钥只保存于本地",
      memories: "记忆可查看&删除，管理者无法查看",
      affinity: "你的话语会影响她们对你的态度，切勿过于冒犯……",
      signIn: (providers: string) => `现支持 ${providers} 登录`,
      noSignIn: "暂时还不能登录。",
      /** 几种登录方式之间的连接词。 */
      or: "/",
    },
    /** 第 7 幕「开始」：每位角色一道光，收拢成一块手机屏幕的白光，出现行动按钮。 */
    act7: {
      title: "她们在屏幕的另一边。",
      body: "登录以后，挑一位偶像，和她说说话。",
    },
  },
  consent: {
    title: "开始之前",
    intro: "你和角色的对话、角色记下的关于你的事，会保存在这台服务器上，并交给第三方服务处理（语言模型、语音合成与识别等）。详情请看{privacy}和{terms}。",
    agreeTerms: "我已阅读并同意隐私政策和使用条款",
    agreeAge: "我已年满 13 岁",
    submit: "同意并开始",
    signOut: "退出登录",
    declineHint: "不同意的话，退出登录即可；在你同意之前，不会保存任何对话。",
  },
  settings: {
    title: "设置",
    loading: "正在读取…",
    /** 设置一级的各类，也是各自二级页首的名字。「登录与数据」不叫「账号」：GLOSSARY 把它列为避免的说法。 */
    categories: {
      profile: "档案",
      memories: "记忆",
      stats: "统计",
      call: "通话",
      "reach-outs": "搭话",
      moments: "朋友圈",
      cycles: "周期",
      appearance: "外观",
      "own-keys": "自带密钥",
      "sign-in": "登录与数据",
      "data-package": "数据包",
      about: "关于",
    },
    /** 一级每行名字下面的当前值摘要（「关于」没有）。 */
    summaries: {
      addressDefault: "按各自的习惯",
      profileUnsaved: "有修改未保存",
      memories: (count: number) => `${count} 条`,
      noMemories: "还没有记忆",
      daysKnown: (days: number) => `已认识 ${days} 天`,
      phoneTextureOn: "电话质感开",
      phoneTextureOff: "电话质感关",
      scspAvatarsOn: "SCSP 头像开",
      scspAvatarsOff: "SCSP 头像关",
      /** 搭话、周期这类只有一个开关的。 */
      switchOn: "开",
      switchOff: "关",
      ownKeysNone: "全部用部署者的服务",
      ownKeys: (services: string) => `已填 ${services}`,
    },
    /** 统计（GLOSSARY.md「统计」）。 */
    stats: {
      empty: "还没有和她们说过话",
      toConversations: "去对话列表",
      daysKnown: "已认识",
      currentVisits: "连续来访",
      longestVisits: "最长连续",
      days: "天",
      portrait: {
        parts: { night: "深夜", morning: "上午", afternoon: "下午", evening: "晚上" },
        and: "和",
        comesAt: (parts: string) => `常在${parts}来`,
        anyTime: "什么时段都会来",
      },
      heatmap: "过去一年",
      heatmapLabel: "过去一年每天来的次数",
      cameOn: (days: number) => `来过 ${days} 天`,
      dayCount: (month: number, day: number, count: number) =>
        count === 0 ? `${month}月${day}日 没来` : `${month}月${day}日 ${count} 次`,
      month: (month: number) => `${month}月`,
      affinity: "好感度",
      tierMore: (count: number) => `+${count}`,
      tierMoreLabel: (count: number) => `还有 ${count} 位`,
      tierLess: "收起",
      achievements: "成就",
      stagesUnlocked: "解锁的阶段",
      stagesUnit: "个",
      charactersComplete: "集齐的角色",
      charactersUnit: "位",
      rangeLabel: "时间跨度",
      ranges: { "30d": "近 30 天", "1y": "近一年", all: "全部" },
      turns: "回合",
      calls: "通话",
      callTime: "通话时长",
      hoursUnit: "小时",
      minutesUnit: "分",
      giftsGiven: "送出的礼物",
      mostTalked: "聊得最多",
      talked: (turns: number, days: number) => `${turns} 个回合 · 认识 ${days} 天`,
      mostCalled: "通话最久",
      calledHours: (hours: number, minutes: number) => `${hours} 小时 ${minutes} 分`,
      calledMinutes: (minutes: number) => `${minutes} 分`,
      hours: "分时段",
      hoursLabel: "每个钟点来的次数",
      hoursTotal: (count: number) => `共 ${count} 次`,
      hour: (hour: number) => `${hour}点`,
      hourCount: (hour: number, count: number) => `${hour}点 ${count} 次`,
      gifts: "礼物",
      mostGiven: "送得最多",
      likedGiven: "她喜欢的",
      times: (count: number) => `${count} 次`,
      timesUnit: "次",
      /** 分享图（GLOSSARY.md「分享图」）。 */
      share: {
        button: "分享",
        failed: "分享图没能生成，请再试一次",
        producer: "制作人",
        turnsUnit: "回合",
      },
    },
    /** 一级里「关于」上面的「赞赏」（GLOSSARY.md「赞赏」）：名字，点开放大的收款码给读屏的标题和替代文字。 */
    sponsor: {
      label: "赞赏",
      code: "赞赏收款码",
    },
    /** 「关于」的四行和最下面的免责声明（应用里只留这一处）。 */
    about: {
      site: "关于 Eidolon-SC",
      repository: "GitHub 仓库",
      privacy: "隐私政策",
      terms: "使用条款",
      disclaimer: "非官方粉丝作品，与版权方无关；角色由 AI 扮演。",
    },
    profile: {
      formOfAddress: "称呼",
      formOfAddressHint: "角色对你的叫法，只改变叫法，你仍然是她们的制作人。留空时，角色按各自的习惯称呼你。",
      formOfAddressPlaceholder: "例如：小林さん",
      gender: "性别",
      genderHint: "只影响角色现在怎么对待你，不会改写她们回忆中的原作剧情。",
      genderDefault: "沿用原作设定（男性）",
      male: "男性",
      female: "女性",
      timezone: "时区",
      timezoneHint: "角色口中的「今天」「今晚」按这个时区计算。自动时使用当前设备检测到的时区。",
      timezoneAuto: (zone: string) => `自动（${zone}）`,
      timezoneUnknown: "当前设备的时区",
      timezoneSearch: "搜索时区",
      birthday: "生日",
      birthdayHint: "生日当天，角色会为你送上祝福。只记月和日。",
      birthMonth: "月",
      birthDay: "日",
      birthdayUnset: "不填",
      monthOption: (month: string) => `${month} 月`,
      dayOption: (day: string) => `${day} 日`,
      birthDayMissing: "请补上日期；不想填生日的话，把月份也改成「不填」。",
      city: "所在城市",
      cityUnset: "未设置",
      citySearch: "搜索城市",
      citySearching: "正在搜索…",
      cityNone: "没有找到",
      cityHere: "用当前位置",
      cityClear: "清除",
      cityNoPosition: "没能取得位置",
      save: "保存档案",
      saving: "正在保存…",
      unsaved: "尚未保存",
      saved: "已保存，所有设备共用这份档案",
    },
    reachOuts: {
      on: "她们会主动搭话",
    },
    moments: {
      on: "她们会发朋友圈",
    },
    cycles: {
      on: "她们的周期",
      hint: "关掉后她不受周期影响，玩法里不显示周期；记录会留着。",
    },
    appearance: {
      scspAvatars: "SCSP 头像",
    },
    call: {
      mic: "默认麦克风",
      micHint: "语音通话默认使用的麦克风。通话中可以在通话层上切换，切换后的会成为新的默认。",
      micMissing: "已选的麦克风（现在没有连接）",
      micDefault: "系统默认",
      micNumbered: (n: number) => `麦克风 ${n}`,
      micUnnamed: "浏览器还没有允许本页使用麦克风，因此看不到名称。",
      micDenied: "没有获得麦克风权限，请在浏览器设置中允许后重试",
      micAllow: "允许使用麦克风",
      quality: "通话音质",
      qualityHint: "角色说话声音的合成音质，越高越清晰，不影响流量。下次接通时生效。",
      qualities: { low: "普通", standard: "清晰", high: "高保真" },
      phoneTexture: "电话质感",
      phoneTextureHint: "让角色的声音像隔着电话听筒。下次接通时生效；开启后，不同通话音质之间的差别会变小。",
    },
    ownKeys: {
      // 外面两句和 ⓘ 里的详细说明，措辞跟隐私说明逐句对齐过（PR #62），改措辞要同步隐私说明。
      summary:
        "填了自己的 API key，这一项服务就改用你的额度，费用由你承担。密钥只保存在这台设备的这个浏览器里，换设备、换浏览器或清除浏览器数据后要重新填写。",
      detailsLabel: "详细说明",
      details: [
        "密钥不存到服务器。",
        "以前填过的也需要重新填一次。",
        "每次聊天或通话时，密钥随请求发给服务器，只在处理期间使用。",
        "自带的密钥调用失败时，这一轮会失败并提示是哪一项出了问题，不会改用部署者的密钥；自带的生图失败时这一轮照常，只是照片没发出来。",
        "界面上只显示密钥的末 4 位。",
      ],
      /** 这个部署的免限额密钥（GLOSSARY.md「免限额密钥」）。带 `services` 的句子经 `sayServices` 拼上服务名，
       * `${services}` 两边不留空格，拉丁字母和汉字之间的空格由它补。 */
      exempting: (services: string) =>
        `这个部署上，带上自己的${services}的通话不计入每小时限额；文字对话带上自己的 LLM 就不计入。`,
      /** 按这个浏览器里存的 key，服务器答的现在计不计入。 */
      exemptAll: "文字对话和语音通话都不计入每小时限额。",
      exemptTurns: (services: string) =>
        `文字对话用的是你自己的 LLM，不计入每小时限额；语音通话要带上${services}才不计入。`,
      exemptCalls: "语音通话不计入每小时限额；文字对话要用你自己的 LLM 才不计入。",
      exemptNone: "现在文字对话和语音通话都计入每小时限额。",
      perCallLimits: "单次通话的时长和轮数上限对所有人都一样。",
      cannotKeep:
        "这个浏览器无法保存自带密钥，可能开着隐私模式，或者禁止了网站保存数据。换一个浏览器，或者允许本站保存数据后再填写。",
      llmTitle: "LLM（扮演角色、记住你说的事）",
      llmHint: "小模型会降低角色扮演和记忆的质量。模型需要支持流式输出和工具调用，保存前会先试调一次。",
      ttsTitle: "语音合成（Fish Audio）",
      ttsModel: "模型",
      /** Fish Audio 的模型（`FISH_AUDIO_MODELS`），后台配置页的选项也用这份名字。 */
      ttsModels: {
        "s2.1-pro-free": "S2.1 Pro Free（免费）",
        "s2.1-pro": "S2.1 Pro",
        "drama-3": "Drama 3",
        "s2-pro": "S2 Pro",
        s1: "S1",
      },
      sttTitle: "语音识别",
      sttProvider: "服务商",
      /** 自带的生图：接口形式和模型的选项名用后台配置页那份（`copy.admin.config`）。 */
      imageTitle: "生图（她发来的照片）",
      imageHint: "填了，她发来的照片用你的额度生成，不计入每小时的照片数。保存前会真生成一张试调。",
      imageNotSet: "未填写",
      imageFormat: "接口形式",
      sttProviders: { soniox: "Soniox", bailian: "阿里云百炼" },
      last4: (last4: string) => `密钥末 4 位 ${last4}`,
      llmCurrent: (model: string, baseUrl: string) => `${model} · ${baseUrl}`,
      notSet: "未填写，使用部署者的服务",
      protocol: "接口类型",
      protocols: {
        "chat-completions": "OpenAI 兼容（Chat Completions）",
        responses: "OpenAI Responses",
        anthropic: "Anthropic Messages",
      },
      baseUrl: "接口地址（base_url）",
      model: "模型名",
      apiKey: "API key",
      /** 修改已存的 LLM 时，key 一栏留空就沿用存着的那把。 */
      keepApiKey: "留空则沿用现在的密钥。",
      textEffort: "文字的思考强度",
      textEffortHint: "文字对话用这一档；没另配后台模型时，记住你说的事、给对话起标题也用这一档。",
      callEffort: "通话的思考强度",
      extraBody: "额外请求参数",
      /** 已存的 LLM 设了思考强度或额外请求参数时，摘要多一行。 */
      llmThinking: (text: string, call: string) => `思考强度：文字 ${text}，通话 ${call}`,
      llmExtraBody: "带额外请求参数",
      /** 另配的后台模型：只在填了上面的 LLM 时显示，删掉上面的 LLM 时一起删掉。 */
      memoryLlmTitle: "后台模型（可选）",
      memoryLlmHint:
        "想让记住你说的事、给对话起标题换一个模型（比如便宜一些的）时填写。填了，上面的 LLM 就只管扮演角色。同样需要支持流式输出和工具调用，保存前会先试调一次。删掉上面的 LLM 时它也一起删掉。",
      memoryLlmNotSet: "未填写，用上面的 LLM 记住你说的事、给对话起标题",
      memoryEffort: "思考强度",
      memoryEffortHint: "记住你说的事、给对话起标题用这一档，不跟上面 LLM 的档位走。",
      /** 已存的后台模型设了思考强度时，摘要多一行。 */
      memoryLlmThinking: (effort: string) => `思考强度：${effort}`,
      fill: "填写",
      edit: "修改",
      remove: "删除",
      removeLabel: (service: string) => `删除${service}的密钥`,
      save: "试调并保存",
      saving: "正在试调…",
    },
    signIn: {
      title: "登录方式",
      hint: "绑定另一种登录方式后，用哪一种登录都是你，看到的是同一份记忆。邮箱相同的两个身份也不会自动合并。",
      linked: (provider: string) => `已绑定 ${provider}。`,
      unlink: "解绑",
      unlinkLabel: (provider: string) => `解绑 ${provider}`,
      onlyMethod: "这是你唯一的登录方式，不能解绑",
      link: (provider: string) => `绑定 ${provider}`,
    },
    signOut: {
      title: "退出登录",
      button: "退出登录",
      everywhere: "退出所有设备",
      everywhereTitle: "退出所有设备？",
      everywhereHint:
        "你在所有设备上都会退出登录。这个浏览器里的自带密钥会一并清除；其他设备上的自带密钥不会被清除，需要在那几台设备上自己删除。",
    },
    admin: {
      title: "后台",
      hint: "你是这套部署的管理者，可以在后台查看看板、修改配置和管理用户。",
      enter: "进入后台",
    },
    /** 数据包（GLOSSARY.md「数据包」）：导出带走、导入接着用。 */
    dataPackage: {
      exportTitle: "导出",
      exportHint: "把你的数据下载成一个文件，带到这里或别的部署导入。",
      categories: {
        conversations: "对话",
        photos: "照片",
        memories: "记忆",
        profile: "制作人档案",
        cycles: "周期记录",
      },
      export: "导出",
      importTitle: "导入",
      importHint: "导入的内容并进你现有的数据。",
      chooseFile: "选择数据包",
      import: "导入",
      importing: "正在导入…",
      reading: "正在读取…",
      nothingToChoose: "这个数据包里没有能导入的内容。",
      /** 「导入了 3 段对话、2 张照片。」 */
      imported: (counts: string) => `导入了 ${counts}。`,
      importedWithProfile: (counts: string) => `导入了 ${counts}和制作人档案。`,
      importedProfile: "导入了制作人档案。",
      count: {
        conversations: (n: number) => `${n} 段对话`,
        photos: (n: number) => `${n} 张照片`,
        memories: (n: number) => `${n} 条记忆`,
        cycles: (n: number) => `${n} 条周期记录`,
      },
      separator: "、",
      nothingNew: "没有新的内容要导入。",
      /** 「跳过了和月岡恋鐘的 2 段、櫻木真乃的 1 段对话，这里没有她们。」 */
      skipped: (parts: string, many: boolean) => `跳过了和${parts}对话，这里没有${many ? "她们" : "她"}。`,
      skippedPart: (name: string, n: number) => `${name}的 ${n} 段`,
      /** 「跳过了 2 条周期记录。」：角色不在、天数不对、在未来，或和已有的重叠。 */
      skippedCycles: (n: number) => `跳过了 ${n} 条周期记录。`,
      failures: {
        broken: "这不是一个能用的数据包",
        too_new: "这个数据包来自更新的版本，请部署者升级后再导入",
        too_large: "数据包太大了（最大 200 MB），可以不带照片重新导出",
        busy: "已经有一个数据包在导入或导出",
      },
      usedUp: (time: string) => `今天的导入次数用完了，${time} 以后可以再导入`,
    },
    deleteAccount: {
      title: "删除我的全部数据",
      hint: "彻底删除你在这里的所有数据，无法恢复。",
      start: "删除我的全部数据",
      confirmTitle: "删除全部数据？",
      // 完整后果只在按下确认前看到，措辞跟以前一模一样。
      confirmHint:
        "彻底删除你的记忆、对话、制作人档案、登录方式、登录状态和限额的计数，无法恢复，这个浏览器里的自带密钥也一并清除；每天的加密备份里的副本最多 30 天后清除。运行记录会保留到期满 90 天，但不再关联到你。所有设备都会退出登录；之后再用同一种登录方式登录，会是一位全新的用户。",
      confirm: "确认删除，无法恢复",
      exportFirst: "先导出数据包",
    },
  },
  admin: {
    /** 一排同名按钮（每行一个「修改」「封禁」）的读屏名：动作加对象，看得见的字仍只是动作。 */
    actionOn: (action: string, target: string) => `${action}：${target}`,
    title: "后台",
    nav: "后台导航",
    pages: {
      dashboard: "看板",
      config: "配置",
      users: "用户",
      announcements: "公告",
    },
    signedInAs: (name: string) => `管理者：${name}`,
    backToSettings: "返回设置",
    toggleNav: "展开或收起后台导航",
    breadcrumb: "当前位置",
    comingSoon: "这一页还在做。",
    usage: {
      units: { tokens: "tokens", bytes: "字节", characters: "字符", seconds: "秒", images: "张" } as Record<
        string,
        string
      >,
      per: {
        tokens: "每百万 tokens",
        bytes: "每百万字节",
        characters: "每百万字符",
        seconds: "每小时",
        images: "每张",
      } as Record<string, string>,
      perCount: (count: string, unit: string) => `每 ${count} ${unit}`,
      amount: (count: string, unit: string) => `${count} ${unit}`,
      inOut: (input: string, output: string, unit: string) => `输入 ${input} · 输出 ${output} ${unit}`,
      unknown: (n: string) => `${n} 次未知`,
    },
    dashboard: {
      intro: "服务是否正常、用量和花费。",
      rangeLabel: "时间范围",
      ranges: { "24h": "24 小时", "7d": "7 天", "30d": "30 天", "90d": "90 天" },
      tabsLabel: "看板分组",
      tabs: { overview: "概览", usage: "用量", affinity: "好感度", cost: "花费" },
      failed: (reason: string) => `看板加载失败：${reason}`,
      freshness: {
        at: (time: string) => `数据截至 ${time}`,
        loading: "正在读取…",
        refresh: "刷新",
        refreshLabel: "刷新看板",
        shownFrom: (time: string) => `下面仍是 ${time} 的数据，每分钟会再试一次。`,
        shownFromRange: (time: string, range: string) => `下面仍是 ${time} 取到的 ${range}数据，每分钟会再试一次。`,
      },
      groups: {
        usage: { title: "用量" },
      },
      /** 长列表默认收起，底下一个展开键。 */
      fold: {
        more: (n: string) => `展开全部 ${n} 位`,
        less: "收起",
      },
      zeroRows: {
        rest: (n: string) => `其余 ${n} 项为 0`,
        all: (n: string) => `${n} 项都为 0`,
      },
      tiles: {
        turns: "回合",
        turnsInCalls: (n: string) => `其中 ${n} 个在通话里`,
        calls: "通话",
        /** 带齐了免限额密钥、不计入限额的通话（运行记录里通话的「用了自带密钥」，GLOSSARY.md「运行记录」）。 */
        callsExempt: (n: string) => `其中 ${n} 次不计入限额`,
        activeUsers: "活跃用户",
        /** 数字卡分两组的小标题：此刻的，和按时间范围统计的（「30 天内」）。 */
        now: "此刻",
        inRange: (range: string) => `${range}内`,
        callsInProgress: "进行中的通话",
        ownKeys: "用自带密钥的回合",
        ownKeysShare: (share: string) => `占 ${share}`,
        timeToSpeak: "到开口（中位数）",
        timeToSpeakP90: (p90: string) => `九成在 ${p90} 内`,
      },
      trend: {
        turns: {
          title: "回合趋势",
          hint: { hour: "每小时的回合数", "6h": "每 6 小时的回合数", day: "每天的回合数" },
          tooltip: (span: string, turns: string, users: string) =>
            `${span}：${turns} 个回合，${users} 位活跃用户`,
          total: (range: string, turns: string, users: string) => `${range}合计：${turns} 个回合，${users} 位活跃用户`,
          empty: "这段时间没有回合。",
        },
        calls: {
          title: "通话趋势",
          hint: { hour: "每小时的通话数", "6h": "每 6 小时的通话数", day: "每天的通话数" },
          tooltip: (span: string, calls: string, users: string) =>
            `${span}：${calls} 次通话，${users} 位活跃用户`,
          total: (range: string, calls: string, users: string) => `${range}合计：${calls} 次通话，${users} 位活跃用户`,
          empty: "这段时间没有通话。",
        },
      },
      results: {
        title: "回合结果",
        result: "结果",
        turns: "回合数",
        share: "占比",
        names: { success: "成功", failed: "失败", rejected: "被拒绝", left: "用户离开" },
      },
      callResults: {
        title: "通话结果",
        result: "结果",
        calls: "通话数",
        share: "占比",
        names: { success: "成功", failed: "因故障中断", rejected: "被拒绝", not_connected: "没能接通" },
      },
      durations: {
        title: "通话时长",
        hint: (p50: string, p90: string) => `中位数 ${p50}，九成在 ${p90} 内`,
        range: "时长",
        calls: "通话数",
      },
      endReasons: {
        title: "结束原因",
        reason: "原因",
        calls: "通话数",
        share: "占比",
        names: {
          hung_up: "用户挂断",
          left: "离开对话页",
          duration_limit: "撞上时长上限",
          turn_limit: "撞上回合上限",
          character_hung_up: "角色挂断",
          banned: "被封禁",
          deleted: "用户被删除",
          failed: "故障",
          shutdown: "服务重启或关闭",
        },
      },
      health: {
        title: "服务健康",
        service: "服务",
        status: "状态",
        calls: "调用",
        errorRate: "出错率",
        errors: "出错类别",
        latency: "延迟 p50 / p95",
        firstToken: "首字 p50 / p95",
        cacheHitRate: "缓存命中率",
        usage: "计费用量",
        own: "自带密钥",
        empty: "这段时间没有服务调用。",
        summary: {
          ok: "这段时间各项服务正常",
          idle: "这段时间没有服务调用",
          problem: (service: string, status: string, rate: string) => `${service}${status}（${rate}）`,
          more: (n: string) => `等 ${n} 项`,
          link: "看服务健康",
        },
        statuses: { ok: "正常", degraded: "出错偏多", failing: "大量出错", idle: "没有调用" },
        services: {
          chat_llm: "扮演角色的 LLM",
          memory_llm: "后台模型",
          tts: "语音合成",
          stt: "语音识别",
          judge: "判断模型",
          embedding: "向量化",
          rerank: "重排",
          image: "生图",
        },
        errorKinds: {
          timeout: "超时",
          connection: "连不上",
          rate_limited: "限流",
          unauthorized: "密钥或余额",
          refused: "请求被拒",
          server_error: "服务端出错",
          unreadable: "返回无法解析",
          other: "其他",
        },
        stripped: (photos: string, kinds: string) => `${photos} 张剥掉了 tag：${kinds}`,
        crossings: {
          nudity: "裸露",
          underwear: "内衣",
          exposure: "透视走光",
          bathing: "洗澡",
          pose: "姿势镜头",
          expression: "表情",
          appearance: "外貌",
          style: "画风画师",
          people: "别人入镜",
        },
      },
      backups: {
        title: "备份",
        hint: "每天加密备份一次整个数据库。",
        /** 「备份」这一块的结论：正常只写 muted 字，异常带红点（DESIGN.md「Admin status & charts」）。 */
        states: {
          ok: "正常",
          busy: "备份中…",
          unconfigured: "未配置：这个部署没有设置备份",
          misconfigured: "配置有误，备份不会运行",
          never_succeeded: "还没有成功过一次备份",
          overdue: "超过 26 小时没有成功的备份",
        },
        busySince: (by: string, time: string) => `${by}，${time} 开始`,
        unconfiguredHelp: "照 docs/deploy.md「备份」在 .env 里设好存储桶和 age 公钥，再重启后端。",
        backUpNow: "立即备份",
        backingUp: "备份中…",
        backUpFailed: (reason: string) => `没能开始备份：${reason}`,
        loadFailed: (reason: string) => `备份状态读取失败：${reason}`,
        lastSuccess: "上一次成功",
        lastSuccessValue: (size: string, by: string) => `${size}，${by}`,
        never: "还没有",
        bucket: "存储桶里",
        bucketValue: (kept: string, total: string) => `${kept} 份，共 ${total}`,
        bucketNoSize: (kept: string) => `${kept} 份（存储桶没有给出大小）`,
        overWarning: "超过了空间提醒",
        notListed: "还没有列出过",
        keepDays: "保留期",
        keepDaysValue: (days: string) => `${days} 天`,
        warnGb: "空间提醒",
        warnGbValue: (gb: string) => `超过 ${gb} GB 时提醒`,
        warnGbUnset: "未设置",
        lastFailure: "最近一次失败",
        lastFailureAt: (by: string) => `，${by}`,
        /** 每次备份是谁发起的，接在时间后面：「5小时前，77.3 MB，每天的 cron 发起」。 */
        sources: { cron: "每天的 cron 发起", manual: "在服务器上手动发起", admin: "从后台按钮发起" },
        stages: {
          config: "配置不全",
          export: "导出失败",
          upload: "上传失败",
          prune: "清理过期备份失败",
          abandoned: "没有完成（进程中途退出，或服务重启）",
        },
      },
      /** 「用量」里的「搭话」一小节：范围内搭了几次、失败几次、被回的占比（被回的 ÷ 成功的）。 */
      reachOuts: {
        title: "搭话",
        tiles: { succeeded: "成功", failed: "失败", answered: "被回了" },
      },
      /** 「用量」里的「酒吧」一小节：范围内光顾了几次（不算被拒的）、玩完几次、失败几次。 */
      bar: {
        title: "酒吧",
        tiles: { visits: "光顾", done: "玩完", failed: "失败" },
      },
      /** 「用量」里的「朋友圈」一小节：范围内发了几条、失败几次、回评论几次、失败几次（写下时评论已删的不算失败）；
       * 近 30 天露出的动态里制作人赞过或评论过的占比，不跟时间范围走。 */
      moments: {
        title: "朋友圈",
        tiles: {
          posted: "发了",
          posts_failed: "发失败",
          replied: "回评论",
          replies_failed: "回失败",
          liked_or_commented: "近 30 天制作人赞或评论过",
        },
      },
      /** 「好感度」里的「日程」一小节：本周（北京时间）排了日程的人数，不跟时间范围走。 */
      schedule: {
        title: "日程",
        tiles: { scheduled: "本周排了日程的人数" },
      },
      /** 「好感度」里的「周期」一小节：现在库里记过周期的用户数，不跟时间范围走。 */
      cycles: {
        title: "周期",
        tiles: { recorded: "记过周期的用户数" },
      },
      /** 「好感度」里的「成就」一小节：范围内解锁了几个成就阶段、发出几次抽奖、几张重置卡。 */
      achievements: {
        title: "成就",
        tiles: {
          stages: "解锁的阶段",
          draws: "发出的抽奖次数",
          reset_cards: "重置卡",
        },
      },
      affinity: {
        title: "好感度",
        tiles: {
          cooldowns: "进入冷却",
          cooledUsers: (n: string) => `涉及 ${n} 位用户`,
          outOfLine: "不该说的话",
          manipulation: "操纵",
        },
        levels: {
          title: "打分分布",
          level: "打分",
          turns: "回合数",
          share: "占比",
          names: ["0 · 伤害了她", "1 · 让她不舒服", "2 · 没有影响", "3 · 让她有点开心", "4 · 让她很开心"],
        },
        characters: {
          title: "按角色",
          character: "角色",
          judged: "判断过的回合",
          raised: "加分占比",
          lowered: "减分占比",
          cooldowns: "进入冷却",
          sheEnded: "挂断或结束对话",
          empty: "这段时间没有判断过的回合。",
          end: (raised: string, lowered: string) => `加分 ${raised} · 减分 ${lowered}`,
          details: (judged: string, cooldowns: string, sheEnded: string) =>
            `判断过 ${judged} 个回合 · 冷却 ${cooldowns} · 挂断或结束对话 ${sheEnded}`,
        },
      },
      characters: {
        title: "按角色",
        character: "角色",
        turns: "回合数",
        calls: "通话数",
        removed: "已下线的角色",
        empty: "这段时间没有回合或通话。",
      },
      cost: {
        title: "花费",
        notes: "备注",
        hint: (catalogAsOf: string | null, presetAsOf: string | null) =>
          `部署者的 key 按单价估算。${catalogAsOf ? `目录价格更新于 ${catalogAsOf}。` : ""}${
            presetAsOf ? `部分单价是 ${presetAsOf} 整理的预设。` : ""
          }`,
        total: "合计（估算）",
        totalNote: (unknown: string) => `另有 ${unknown} 次调用没说用量，没有算进去`,
        empty: "这段时间部署者的 key 没有花钱。",
        trendTitle: (currency: string) => `花费趋势（${currency}）`,
        trendHint: { hour: "每小时的花费", "6h": "每 6 小时的花费", day: "每天的花费" },
        trendReadout: (span: string, amount: string) => `${span}：约 ${amount}`,
        trendTotal: (range: string, amount: string) => `${range}合计：约 ${amount}`,
        trendEmpty: "这段时间没有花费。",
        byService: "按服务",
        byModel: "按模型",
        service: "服务",
        model: "提供方 / 模型",
        usage: "计费用量",
        price: "单价",
        amount: "花费",
        unpriced: "未设单价",
        usageUnknown: "用量未知",
        unknownCalls: (n: string) => `${n} 次没说用量`,
        unpricedModels: (n: string) => `${n} 个模型未设单价`,
        own: {
          title: "自带密钥的用量",
          hint: "用户自己付费，只列用量。",
          calls: "调用",
        },
        sources: {
          preset: "预设",
          catalog: "目录",
          catalog_upstream: "按原厂价格估算",
          override: "后台设定",
        } as Record<string, string>,
      },
    },
    users: {
      intro: "这里只有用户是谁、怎样使用这套部署；看不到任何人的对话、记忆和制作人档案。",
      search: "搜索用户",
      searchPlaceholder: "名字、邮箱或用户 ID",
      total: (n: number) => `共 ${n} 位用户`,
      empty: "没有找到用户。",
      emptyHint: "试试换个名字、邮箱，或者完整的用户 ID。",
      pagination: "用户列表分页",
      previousPage: "上一页",
      nextPage: "下一页",
      pageOf: (page: number, pages: number) => `第 ${page} / ${pages} 页`,
      clearSearch: "清空搜索",
      columns: {
        user: "用户",
        signInMethods: "登录方式",
        createdAt: "注册时间",
        lastActive: "最后活跃",
        status: "状态",
        limits: "单独限额",
        turns24h: "24 小时回合",
        calls24h: "24 小时通话",
        actions: "操作",
      },
      usage: {
        title: "近期用量",
        hint: "来自运行记录。回合包括通话里的回合；被拒绝的回合和通话（多是撞上了限额）只计入「被拒绝」。",
        ranges: { "24h": "最近 24 小时", "7d": "最近 7 天", "30d": "最近 30 天" },
        rows: { turns: "回合", calls: "通话", rejected: "被拒绝" },
        split: (deployer: string, ownKeys: string) => `部署者 ${deployer} · 自带密钥 ${ownKeys}`,
        /** 通话那一行：运行记录里通话的「用了自带密钥」是带齐了免限额密钥、不计入限额（GLOSSARY.md「运行记录」）。 */
        splitCalls: (counted: string, exempt: string) => `计入限额 ${counted} · 不计入 ${exempt}`,
      },
      usage24h: (turns: string, calls: string) => `24 小时：回合 ${turns} · 通话 ${calls}`,
      limitsToken: (summary: string) => `单独限额：${summary}`,
      sort: { label: "排序", newest: "最近注册", turns: "24 小时回合最多", calls: "24 小时通话最多" },
      never: "—",
      noSignInMethods: "没有登录方式",
      active: "正常",
      banned: "已封禁",
      admin: "管理者",
      adminCannotBeBanned: "管理者不能在后台封禁或删除",
      ban: "封禁",
      unban: "解除封禁",
      backToList: "返回用户列表",
      loading: "正在加载这位用户",
      details: {
        title: "资料",
        signInMethods: "登录方式",
        identifier: "标识",
        email: "邮箱",
        noEmail: "没有邮箱",
        id: "用户 ID",
        createdAt: "注册时间",
        /** 经邀请链接注册的用户多一项，值是那条链接的备注。 */
        invite: "经邀请链接注册",
        lastActive: "最后活跃",
        bannedAt: "封禁于",
        banNote: "封禁备注",
        noNote: "没有备注",
      },
      banDialog: {
        title: (name: string) => `封禁 ${name}`,
        hint: "封禁后，这位用户会在所有设备上退出登录，进行中的通话随即挂断，之后不能再登录；他的数据保持原样，随时可以解除封禁。",
        note: "备注",
        noteHint: "只有管理者看得到，被封禁的用户看不到。",
        confirm: "确认封禁",
      },
      limits: {
        title: "单独限额",
        default: "跟随全站",
        unlimited: "不限",
        ownKeysOnly: "只能用自带密钥",
        perHour: (n: number) => `每小时 ${n} 次`,
        photosPerHour: (n: number) => `每小时 ${n} 张`,
        turns: "回合",
        calls: "通话",
        summary: (turns: string, calls: string) => `回合 ${turns} · 通话 ${calls}`,
        /** 单独设了照片数时接在后面。 */
        withPhotos: (summary: string, photos: string) => `${summary} · 照片 ${photos}`,
        /** 单独设了光顾次数时接在后面（在照片之后）。 */
        withVisits: (summary: string, visits: string) => `${summary} · 光顾 ${visits}`,
        /** 单独设了朗读次数时接在后面（在光顾之后）。 */
        withReadAlouds: (summary: string, readAlouds: string) => `${summary} · 朗读 ${readAlouds}`,
        updatedAt: "设定于",
        set: "设定单独限额",
        edit: "修改单独限额",
        takeOff: "取消单独限额",
      },
      limitsDialog: {
        title: (name: string) => `${name} 的单独限额`,
        hint: "只对这位用户生效，保存后从他的下一个回合、下一次通话、光顾或朗读起按这里的数字计算；没有单独设定的一项跟随全站。不计入限额的回合、通话、光顾和朗读照常放行。单次通话的时长和回合上限对所有人都一样，不能单独设。",
        turns: "每小时的回合数",
        calls: "每小时的通话次数",
        photos: "每小时的照片数",
        visits: "每小时的光顾次数",
        readAlouds: "每小时的朗读次数",
        choices: { default: "跟随全站", number: "设定次数", unlimited: "不限", ownKeys: "只能用自带密钥" },
        /** 「只能用自带密钥」是什么意思：只放行不计入限额的（GLOSSARY.md「免限额密钥」）。通话的按配置页「限额」
         * 里现在的免限额密钥点名，经 `sayServices` 拼上服务名；读不到配置时用 `callsOwnKeysHintUnknown`。 */
        turnsOwnKeysHint: "只放行用自带 LLM 的文字回合。",
        callsOwnKeysHint: (services: string) => `只放行带上自己的${services}的通话；全站的免限额密钥改了，这里跟着变。`,
        callsOwnKeysHintUnknown: "只放行不计入限额的通话。",
        photosOwnKeysHint: "只发用自带生图生成的照片。",
        visitsOwnKeysHint: "只放行用自带 LLM 的光顾。",
        readAloudsOwnKeysHint: "只用自带语音合成的 key 朗读。",
        /** 「跟随全站」带上全站现在的数字，不用去配置页查：「跟随全站（60 次）」。 */
        defaultIs: (site: string) => `跟随全站（${site}）`,
        siteCount: (n: number) => (n === 0 ? "不限" : `${n} 次`),
        sitePhotos: (n: number) => (n === 0 ? "不限" : `${n} 张`),
        count: (what: string) => `${what}（次数）`,
        units: "次 / 小时",
        photoUnits: "张 / 小时",
        note: "备注",
        noteHint: "只有管理者看得到。",
        confirm: "保存",
        needsOne: "至少要单独设定一项；都跟随全站的话，用「取消单独限额」。",
        needsCount: "填 1 以上的次数。",
      },
      delete: "删除这位用户",
      deleteSection: { hint: "彻底删除他的全部数据，无法恢复。确认之前会再列出要删掉什么。" },
      deleteDialog: {
        title: (name: string) => `删除 ${name} 的全部数据？`,
        hint: "和他自己删除完全一样：彻底删除他的记忆、对话、制作人档案、登录方式、登录状态和限额的计数，无法恢复，进行中的通话随即挂断；每天的加密备份里的副本最多再留 30 天。",
        banned: "他已被封禁：删除后，他用过的登录方式仍然不能再登录，也不能被绑定，删除不等于解封。",
        notBanned: "他没有被封禁：之后再用同一种登录方式登录，会是一位全新的用户。",
        confirm: "确认删除，无法恢复",
      },
    },
    config: {
      intro:
        "这里改的配置存进数据库，优先于 .env。LLM、语音、生图和判断模型保存前会先试调一次，试不通不保存；保存后新的回合和新的通话立刻用上，进行中的通话不受影响，不用重启。没有标注状态的项用的是 .env 的值。",
      loading: "正在读取…",
      /** 页首的分类标签（TabsList 的读屏名）和各个标签。 */
      nav: "配置分类",
      tabs: {
        models: "模型",
        voice: "语音",
        image: "生图",
        weather: "天气",
        network: "网络",
        status: "服务状态",
        limits: "限额与玩法",
        registration: "注册",
        sponsor: "赞赏",
        prices: "单价",
        read_only: "只读",
      },
      /** 标签里有覆盖没生效的项时，标签旁的琥珀色点念这一句。 */
      tabFailed: "有覆盖没有生效",
      /** 窄屏代替标签的下拉收起时，有任何一类有覆盖没生效，框里的琥珀色点念这一句。 */
      someTabFailed: "有分类里有覆盖没有生效",
      items: {
        chat_llm: {
          title: "扮演角色的 LLM",
          hint: "模型需要支持流式输出和工具调用，保存前会先用同样的检查试调一次。",
        },
        memory_llm: {
          title: "后台模型",
          hint: "每个回合结束后用它从对话里记下关于制作人的事，第 3 个回合后也用它给对话起标题。保存前和扮演角色的 LLM 一样先试调一次。",
        },
        tts: {
          title: "语音合成（Fish Audio）",
          hint: "保存前查一下 key 的余额（不花钱）。新配置只影响之后接通的通话，进行中的通话不变。",
        },
        stt: {
          title: "语音识别",
          hint: "选用哪一家，以及它的 key。保存前做一次不花钱的检查，选阿里云百炼时顺带探测 key 所在的地域。新配置只影响之后接通的通话；自带语音识别密钥的用户不受影响。",
        },
        image: {
          title: "生图",
          hint: "她发的照片由它生成。保存前用固定的提示词带上画风真生成一张来检查，这一张不计用量。",
        },
        judge: {
          title: "判断模型",
          hint: "决定每个回合要不要检索、要不要回忆剧情，好感度开着时还判断制作人的话让好感度怎样变化，也判断通话中角色的情绪。保存前 Cloudflare 和阿里云百炼做启动时的检查，Jev 问一个最小的问题。换模型时，判断阈值的覆盖都会被清掉。进行中的通话继续用接通时的模型判断情绪。",
        },
        judge_thresholds: {
          title: "判断模型的阈值",
          hint: "判断模型给出的概率达到阈值才算「是」。回忆阈值越高越少去回忆剧情；情绪阈值以下当作平静、不点头；「不该说的话」「操纵」是好感度的两道是非题，阈值越高越少判成「是」。",
        },
        rerank: {
          title: "重排的阈值",
          hint: "重排打分低于阈值的剧情、角色资料和记忆不放进提示词。阈值越高带上的越少。",
        },
        limits: {
          title: "限额、单次通话上限和历史回合数",
          hint: "每小时的回合数、通话次数和照片数对每位用户分别计算。用了自带 LLM 的文字回合不计入，照片照样计入；通话把下面打开的几项免限额密钥都自带了才不计入，没打开的由部署者承担。保存后下一个回合、下一次通话就按新的设置执行；进行中的通话仍按接通时的规则、时长和回合上限。",
        },
        affinity: {
          title: "好感度和礼物",
          hint: "需要判断模型：每个回合由它判断制作人的话让好感度怎样变化。关掉时不判断、不显示，冷却也不拦人，成就不出现也不记进度；已有的好感度原样留着，再打开接着用。保存后从下一个回合起生效，进行中的通话也是。",
        },
        reach_outs: {
          title: "搭话",
          hint: "打开后，用户一阵子没来，角色会在当前对话里先说几句。用的是部署者的对话模型，花费由部署者出，自带 LLM 的用户也一样。保存后下一分钟起生效。",
        },
        letters: {
          title: "信",
          hint: "打开后，角色和用户的好感度第一次升到亲近、亲密，或者集齐这位角色时，她会给用户写一封信。用的是部署者的对话模型，花费由部署者出，自带 LLM 的用户也一样。关掉后不再写，已经写好的信用户照样能看。保存后下一分钟起生效。",
        },
        moments: {
          title: "朋友圈",
          hint: "打开后，和用户聊过的角色会在他的朋友圈里发动态。用的是部署者的对话模型，花费由部署者出，自带 LLM 的用户也一样。保存后下一分钟起生效。",
        },
        qweather: {
          title: "和风天气",
          hint: "配好后，用户可以在制作人档案里设所在城市，角色在对话里知道那边的天气和预警；没配时只知道东京的天气。用 JWT 认证，五项都要填。保存前按坐标找一次北京来检查。",
        },
        schedule: {
          title: "日程",
          hint: "打开后，日历里每周发布一批工作，用户排进角色的一周，角色知道并说起；排给她的工作做完了，好感度上升（好感度关着时不加）。关掉时日历只有月视图，角色不再说起日程，已排的原样留着，再打开接着用。保存后从下一次读取起生效。",
        },
        cycles: {
          title: "周期",
          hint: "打开后，每位用户的每位角色各有一个周期，经前、经期她的言行、好感度、挂断、暖的礼物和对话事件跟着变；用户可以在设置里自己关。关掉时周期照走，再打开她还在本来的位置。保存后从下一个回合、下一次搭话起生效。",
        },
        bar: {
          title: "酒吧",
          hint: "打开后，角色来 VA-283 光顾，制作人照她的点单调饮品。用的是对话模型，自带 LLM 的用户用他们自己的。关掉时进不了门，进行中的光顾照常走完。保存后从下一次进门起生效。",
        },
        proxy: {
          title: "网络代理",
          hint: "打开的服务经过这个代理连服务商，其余的直连；用户自带的密钥和部署者的分开选。保存前把换了路线的部署者服务按新路线各连一次，有一项不通就不保存。保存后从下一次请求起生效，进行中的回合和通话也是；已经连上的语音连接不断。",
        },
        service_status: {
          title: "服务状态",
          hint: "对话列表铃铛旁边给用户看各项服务正不正常：按统计时段里用部署者 key 的调用算出错率，时段里没有调用的，后台用最小的真实请求试一下（生图不试）。一项都不显示时用户那边没有按钮。保存后立刻生效。",
        },
        registration: {
          title: "注册方式",
          hint: "只让受邀的人注册时，新用户要从下面的邀请链接登录；已经注册的用户和管理者照常登录。保存后立刻生效。",
        },
      },
      status: {
        env: "使用 .env 的值",
        overridden: "已被后台覆盖",
        failed: "覆盖没有生效，回退到 .env",
      },
      /** 卡片标题旁的 Badge：用 .env 的值是常态，不标（DESIGN.md「Admin status & charts」）。 */
      badges: { overridden: "已被后台覆盖", failed: "覆盖没有生效" },
      failed: (reason: string) => `后台覆盖的配置没有生效，现在用的是 .env 的值。原因：${reason}`,
      columns: { field: "项", env: ".env 的值", effective: "当前生效", override: "后台覆盖" },
      fields: {
        protocol: "接口类型",
        base_url: "接口地址（base_url）",
        model: "模型名",
        max_tokens: "max_tokens",
        reasoning_effort: "思考强度",
        call_reasoning_effort: "通话的思考强度",
        extra_body: "额外请求参数",
        api_key: "API key",
        provider: "服务",
        soniox_api_key: "Soniox 的 key",
        dashscope_api_key: "阿里云百炼的 key",
        region: "百炼的地域",
        account_id: "Cloudflare 账号 ID",
        workspace_id: "百炼的业务空间 ID",
        emotion_timeout: "情绪判断的超时（秒）",
        recall: "回忆阈值",
        emotion: "情绪的最低概率",
        out_of_line: "「不该说的话」的阈值",
        manipulation: "「操纵」的阈值",
        photo: "「要照片」的阈值",
        references: "剧情和角色资料的最低相关度",
        memories: "记忆的最低相关度",
        turns_per_hour: "每小时回合数",
        calls_per_hour: "每小时通话次数",
        photos_per_hour: "每小时照片数",
        visits_per_hour: "每小时光顾次数",
        read_alouds_per_hour: "每小时朗读次数",
        call_minutes: "单次通话的时长上限（分钟）",
        turns_per_call: "单次通话的回合上限",
        concurrent_calls: "同时进行的通话数上限",
        history_turns: "带上的历史回合数",
        /** 免限额密钥（GLOSSARY.md「免限额密钥」）的三个开关。 */
        exempting_llm: "免限额密钥：LLM",
        exempting_tts: "免限额密钥：语音合成",
        exempting_stt: "免限额密钥：语音识别",
        enabled: "好感度和礼物",
        api_format: "接口形式",
        concurrency: "同时生成几张",
        style: "画风",
      } as Record<string, string>,
      /** 只在某一项里换个叫法的字段：对话模型的思考强度只管文字对话。 */
      itemFields: {
        chat_llm: { reasoning_effort: "文字的思考强度" },
        reach_outs: { enabled: "搭话", per_day: "每位用户每天最多几次" },
        letters: { enabled: "信" },
        moments: {
          enabled: "朋友圈",
          per_day: "每位用户每天最多几条",
          map: "地图",
          replies_per_day: "每位用户每天她最多回几条评论",
        },
        qweather: {
          host: "API Host",
          developer_id: "开发者 ID",
          project_id: "项目 ID",
          key_id: "凭据 ID",
          private_key: "私钥（Ed25519）",
        },
        schedule: { enabled: "日程" },
        cycles: { enabled: "周期" },
        bar: { enabled: "酒吧" },
        proxy: {
          enabled: "代理",
          url: "代理地址",
          password: "代理密码",
          chat_llm: "扮演角色的 LLM 走代理",
          memory_llm: "后台模型走代理",
          judge: "判断模型走代理",
          embedding: "向量化走代理",
          rerank: "重排走代理",
          tts: "语音合成走代理",
          stt: "语音识别走代理",
          image: "生图走代理",
          own_llm: "自带的 LLM 走代理",
          own_tts: "自带的语音合成走代理",
          own_stt: "自带的语音识别走代理",
          own_image: "自带的生图走代理",
        },
        service_status: {
          window_minutes: "统计时段",
          chat_llm: "显示「对话」（扮演角色的 LLM）",
          memory_llm: "显示「记忆」（后台模型）",
          tts: "显示「语音合成」",
          stt: "显示「语音识别」",
          judge: "显示「判断」（判断模型）",
          embedding: "显示「检索」（向量化）",
          rerank: "显示「重排」",
          image: "显示「照片」（生图）",
        },
        registration: { mode: "谁能注册" },
      } as Partial<Record<string, Record<string, string>>>,
      formHints: {
        reasoning_effort: `${reasoningEffortHints.effort}选「高」及以上时，max_tokens 留空或设宽裕一些，思考也算在上限里。`,
        call_reasoning_effort: reasoningEffortHints.callEffort,
        extra_body: reasoningEffortHints.extraBody,
        account_id: "只有 Cloudflare 需要；换成 Cloudflare 时必填。",
        workspace_id: "只有阿里云百炼需要；换成百炼时必填。地域不选就是北京。",
        emotion_timeout: "大于 0、不超过 30 秒；超时的那一段不判断情绪。",
        stt_api_key: "填写所选服务的 key，留空则沿用这家已有的 key。",
        proxy_enabled: "关闭时所有服务都直连，地址、密码和下面的选择照样留着。",
        proxy_url:
          "http://、https://、socks5:// 或 socks5h:// 开头，写明主机和端口，比如 http://127.0.0.1:7890（生产环境的后端和宿主机共用网络，宿主机上的代理直接写 127.0.0.1）。地址里带的密码会单独加密保存。留空表示没有代理。",
        proxy_password: "代理要求认证时填写，地址里要写用户名（http://用户名@主机:端口）。留空则不改。",
        proxy_unconfigured: "这个部署没有配置这项服务，开关暂时不起作用。",
        service_status_unconfigured: "这个部署没有配置这项服务，打开了也不显示。",
        service_status_window_minutes: "按最近这么久里的调用算；也是空闲的服务多久试一次。",
        service_status_image: "生图每张都要花钱，不会去试，没有调用时显示「最近没有调用」。",
        proxy_own_llm: "只有服务地址属于已知服务商（价格目录里有的）时才走代理，其余的照旧直连。",
        proxy_own_image: "只有 NovelAI 官方地址（https://image.novelai.net）走代理，中转一律直连。",
        judge_api_key: "Jev 填 OpenRouter 等的 key，Cloudflare 填 API token，阿里云百炼填这个业务空间的 key；换服务时必填，留空则不改。",
        judge_model: "Cloudflare 只能是 clef 或 clef-flash；阿里云百炼填 decision-model-preview。",
        image_base_url: "官方格式填到域名根，OpenAI 图像格式填到 /v1。",
        probability: "0 到 1 之间。",
        exempting_llm: "打开：通话要自带 LLM 才可能不计入限额。关闭：通话的 LLM 由部署者承担，带不带都不影响计数。文字回合不看这里，用了自带 LLM 就不计入。",
        exempting_tts: "打开：通话要自带语音合成（Fish Audio）才可能不计入限额。关闭：语音合成由部署者承担，带不带都不影响计数。",
        exempting_stt: "打开：通话要自带语音识别才可能不计入限额。关闭：语音识别由部署者承担，带不带都不影响计数。",
      } as Record<string, string>,
      /** 免限额密钥只剩这一项开着时，开关关不掉，下面写这一句。 */
      lastExemptingKey: "至少要开一项；想取消限额，把每小时的回合数和通话次数设成不限。",
      problems: {
        required: (field: string) => `${field}不能为空。`,
        maxTokens: (field: string) => `${field}需要是正整数，留空用默认值。`,
        ...reasoningEffortProblems,
        probability: (field: string) => `${field}需要是 0 到 1 之间的数。`,
        seconds: (field: string) => `${field}需要大于 0、不超过 30。`,
        limit: (field: string) => `${field}需要是 1 以上的整数；不想限制就选「不限」。`,
        count: (field: string) => `${field}需要是 1 到 10 之间的整数。`,
        positive: (field: string) => `${field}需要是正整数。`,
      },
      unlimited: "不限",
      minutes: (n: string) => `${n} 分钟`,
      /** 开关类的值（免限额密钥、好感度和礼物、搭话）。 */
      switchOn: "打开",
      switchOff: "关闭",
      /** 限额一项先选种类：设定上限，或者不限。不用 0 表示不限（单独限额里另有「只能用自带密钥」）。 */
      limitChoices: { number: "设定上限", unlimited: "不限" },
      providers: {
        soniox: "Soniox",
        bailian: "阿里云百炼",
        jev: "Jev",
        cloudflare: "Cloudflare Workers AI",
      } as Record<string, string>,
      regions: { beijing: "北京", singapore: "新加坡" } as Record<string, string>,
      /** 注册方式（GLOSSARY.md「注册方式」）的两种。 */
      registrations: { open: "谁都能注册", invite: "只让受邀的人注册" } as Record<string, string>,
      mapSites: { osm: "OpenStreetMap", google: "Google Maps", amap: "高德地图" } as Record<string, string>,
      imageFormats: { novelai: "NovelAI 官方格式", openai: "OpenAI 图像格式" } as Record<string, string>,
      imageModels: {
        "nai-diffusion-5-curated": "V5 Curated",
        "nai-diffusion-5-full": "V5 Full",
        "nai-diffusion-4-5-curated": "V4.5 Curated",
        "nai-diffusion-4-5-full": "V4.5 Full",
        "nai-diffusion-4-curated-preview": "V4 Curated",
        "nai-diffusion-4-full": "V4 Full",
      } as Record<string, string>,
      /** 模型下拉里的最后一项：选了它，下面出一个框手填模型名。 */
      customModel: "其他（手填）",
      followsChat:
        "当前跟随扮演角色的 LLM：.env 里没有给它单独设置服务和模型，后台也没有覆盖，所以接口类型、地址、key 和模型名用的是扮演角色的 LLM 当前生效的值；max_tokens、思考强度和额外请求参数仍是它自己的（.env 的 BACKGROUND_LLM_*）。在这里保存后就单独设置。",
      forModel: (model: string) =>
        `这里的阈值只对当前的模型 ${model} 生效；换了模型（包括改了 .env 后重启）以后，这里的覆盖不再生效。`,
      unavailable: (reason: string) => `${reason}。`,
      readOnly: {
        title: "只能查看的项",
        hint: "这些项只能在服务器上的 .env 里改，后台只显示。任何密钥都只显示设没设。",
        columns: { name: "项", value: "当前的值", why: "为什么不能在后台改" },
        names: {
          admins: "管理者名单",
          secret_key: "EIDOLON_SECRET_KEY",
          oauth: "OAuth 登录",
          domain: "域名",
          webrtc: "WebRTC / TURN",
          backup: "备份",
          paths: "路径",
          embedding: "向量化的服务和模型",
        } as Record<string, string>,
        set: "已设置",
        unset: "未设置",
        /** 开发登录打开、没设管理者名单时，人人都是管理者。 */
        everyone: "所有人（开发登录）",
      },
      protocols: {
        "chat-completions": "OpenAI 兼容（Chat Completions）",
        responses: "OpenAI Responses",
        anthropic: "Anthropic Messages",
      },
      defaultMaxTokens: "默认",
      last4: (last4: string) => `末 4 位 ${last4}`,
      none: "—",
      inEffect: "生效中",
      notInEffect: "已失效",
      edit: "修改",
      /** 服务类的项保存前先试调；阈值和限额只查范围，直接保存。 */
      save: { tried: "试调并保存", plain: "保存" },
      saving: { tried: "正在试调…", plain: "正在保存…" },
      saved: "已保存，新的回合和通话会用上新的配置。",
      restore: "恢复成 .env 的值",
      restored: "已恢复成 .env 的值。",
      apiKeyHint: "留空则不改。",
      keysReadOnly: "这个部署没有设置 EIDOLON_SECRET_KEY，key 不能以明文存进数据库，只能在 .env 里修改；其他项照常可以改。",
      maxTokensHint: "留空用接口类型的默认值。",
      /** 「好感度和礼物」卡里开关下面那一块：一次给所有现有用户各发一张重置卡。 */
      resetCardGrants: {
        title: "给所有现有用户各发一张重置卡",
        hint: "判断模型误判了一阵子时，用它给大家补偿。不能单独给某一位发；好感度和礼物开着时才能发。",
        /** 「上次发放：」后面是时间，再跟「，共 n 张」。 */
        last: "上次发放：",
        lastCount: (n: number) => `，共 ${n} 张`,
        never: "还没有发过",
        grant: "发放",
        dialog: {
          title: "给所有现有用户各发一张重置卡？",
          description: (n: number) => `现有的 ${n} 位用户每人多一张，之后注册的用户拿不到。发出后不能收回。`,
          confirm: (n: number) => `发出 ${n} 张`,
        },
        granted: (n: number) => `已发出 ${n} 张重置卡。`,
        /** 发完的提示下面一句，「去写一条公告」链到公告页。 */
        announce: { before: "需要的话，", link: "去写一条公告", after: "告诉大家。" },
      },
      /** 「赞赏」标签里的那张卡（GLOSSARY.md「赞赏」）。不是 .env 里的配置，没有「恢复成 .env 的值」，只有「清除」。 */
      sponsor: {
        title: "赞赏",
        hint: "用户在设置里「关于」上面看到「赞赏」，点开是这张收款码。",
        loading: "正在读取…",
        switch: "在设置里显示",
        noImage: "还没上传收款码，用户暂时看不到「赞赏」。",
        preview: "收款码",
        upload: "上传收款码",
        replace: "换一张",
        uploading: "正在上传…",
        formats: (mb: number) => `PNG、JPEG 或 WebP，不超过 ${mb} MB。`,
        notAPicture: "只能上传 PNG、JPEG 或 WebP 图片。",
        tooLarge: (mb: number) => `图片不能超过 ${mb} MB。`,
        clear: "清除",
        dialog: {
          title: "清除赞赏？",
          description: "开关会关掉，收款码会删除，用户不再看到「赞赏」。",
          confirm: "清除",
        },
      },
      /** 「注册」标签里注册方式下面的那张卡（GLOSSARY.md「邀请链接」）。不是 .env 里的配置。 */
      invites: {
        title: "邀请链接",
        hint: "把链接发给想邀请的人，对方打开后登录就注册好了。",
        loading: "正在读取…",
        create: "生成邀请链接",
        empty: "还没有邀请链接。",
        noNote: "没有备注",
        used: (used: number, max: number) => `已用 ${used} / ${max} 次`,
        expiresAt: "到期",
        neverExpires: "不过期",
        states: { used_up: "已用完", expired: "已过期" } as Record<string, string>,
        invited: "经它注册：",
        nameSeparator: "、",
        copy: "复制链接",
        copied: "已复制",
        copyFailed: (link: string) => `没能复制，请手动复制：${link}`,
        created: "已生成邀请链接。",
        delete: "删除",
        form: {
          note: "备注",
          noteHint: "比如发给谁，只有管理者看得到。",
          maxUses: "可用次数",
          lifetime: "有效期",
          lifetimes: { "1": "1 天", "7": "7 天", "30": "30 天", never: "不过期" } as Record<string, string>,
          submit: "生成",
          submitting: "正在生成…",
          maxUsesProblem: (max: number) => `可用次数要在 1 到 ${max} 之间。`,
        },
        dialog: {
          title: "删除这条邀请链接？",
          description: "链接会立刻失效；经它注册的用户照常使用。",
          confirm: "删除",
        },
      },
    },
    prices: {
      title: "单价",
      hint: (asOf: string | null) =>
        `看板按这些单价估算部署者的花费。以「提供方 + 模型 + 计费单位」为准，提供方是服务地址的主机名。生效顺序：后台设定 > 在线目录（models.dev 和 OpenRouter，每天更新，只有按 tokens 计费的模型）> 预设${
          asOf ? `（整理于 ${asOf}）` : ""
        }。服务地址不在目录里（例如中转）时，按模型名用原厂价格估算。改了单价，之前的花费也按新单价重新估算。这里列出预设、后台设定过的和最近 90 天用过的模型。`,
      loading: "正在读取…",
      columns: {
        model: "提供方 / 模型",
        unit: "单位",
        preset: "预设",
        catalog: "目录",
        override: "后台设定",
        effective: "生效单价",
        actions: "操作",
      },
      none: "—",
      /** 一个单价里的各项：输入、命中缓存的输入、输出。 */
      priceParts: {
        input: (price: string) => `输入 ${price}`,
        cacheRead: (price: string) => `命中缓存 ${price}`,
        output: (price: string) => `输出 ${price}`,
      },
      inEffect: "生效",
      setOn: (date: string) => `设于 ${date}`,
      asOf: (date: string) => `整理于 ${date}`,
      fetchedOn: (date: string) => `拉取于 ${date}`,
      upstream: (match: string) => `按原厂价格估算：${match}`,
      listedAs: (match: string) => `目录里是 ${match}`,
      catalog: {
        fetching: "正在从目录拉取单价…",
        never: "还没有拉取过目录，暂时按预设估算。",
        unreachable: (error: string) => `拉取目录失败，暂时按预设估算：${error}`,
        fresh: "目录更新于",
        kept: (error: string) => `最近一次拉取失败，继续使用之前拉取的目录：${error}`,
        failedAt: "失败于",
        refresh: "立即从目录刷新",
        refreshed: "已从目录刷新。",
      },
      edit: "修改",
      restoreTo: { catalog: "恢复成目录价格", preset: "恢复成预设" },
      remove: "删除",
      add: "新增单价",
      priceIt: "设单价",
      filter: "按模型或提供方筛选",
      clearFilter: "清空筛选",
      noMatch: "没有匹配的模型。",
      showAll: (n: number) => `显示全部 ${n} 个`,
      fold: "收起",
      save: "保存",
      saved: "已保存，看板按新单价估算。",
      restored: "已恢复。",
      formTitle: {
        add: "新增单价",
        edit: (model: string) => `修改单价：${model}`,
        price: (model: string) => `设单价：${model}`,
      },
      /** 修改、设单价时标题下的一行：这条单价的键，表单里不能改。 */
      formKey: (provider: string, unit: string) => `${provider} · ${unit}`,
      unpriced: {
        title: "用过但未设单价的模型",
        hint: "最近 90 天部署者的 key 用过、目录和预设里却都找不到单价的模型。看板上它们只显示用量和「未设单价」。",
      },
      fields: {
        provider: "提供方（主机名）",
        model: "模型名",
        unit: "计费单位",
        input: "输入单价",
        output: "输出单价",
        cacheRead: "缓存命中单价",
        currency: "币种",
      },
      formHints: {
        provider: "和运行记录里的一致，例如 api.deepseek.com。",
        model: "和运行记录里的一致。",
        input: "每个计价口径的价格，非负数。",
        output: "只有 LLM 的输出单独计价；留空表示按输入单价算。",
        cacheRead: "只有 LLM 有：输入里命中服务商缓存的部分按这个价算；留空表示按输入单价算。",
      } as Record<string, string>,
      units: {
        tokens: "tokens（每百万）",
        bytes: "字节（每百万，UTF-8）",
        characters: "字符（每百万）",
        seconds: "秒（每小时）",
        images: "张（每张）",
      } as Record<string, string>,
      currencies: { USD: "美元（USD）", CNY: "人民币（CNY）" } as Record<string, string>,
      problems: {
        required: (field: string) => `${field}不能为空。`,
        amount: (field: string) => `${field}需要是非负数。`,
      },
    },
    announcements: {
      intro: "写给所有用户的公告，发布后出现在对话列表的铃铛里。修改已发布的公告不会再提醒用户一次；撤回后再发布，算一条新公告。",
      write: "写公告",
      columns: { body: "正文", status: "状态", publishedAt: "发布时间", updatedAt: "最后修改" },
      status: { draft: "草稿", published: "已发布" },
      notPublished: "未发布",
      pinned: "置顶",
      empty: "还没有公告",
      emptyHint: "点「写公告」写第一条。",
      loading: "正在读取…",
      backToList: "返回公告列表",
      editor: {
        newTitle: "写公告",
        title: "编辑公告",
        body: "正文",
        bodyHint: "支持 Markdown 的加粗、斜体、链接、列表和行内代码，换行照原样换行；不支持标题、图片和 HTML。",
        count: (n: number, max: number) => `${n} / ${max} 字`,
        tooLong: (max: number) => `最多 ${max} 字。`,
        modes: "编辑或预览",
        edit: "编辑",
        preview: "预览",
        emptyPreview: "还没有内容。",
        publishedHint: "已发布：保存修改不会让用户再看到一次未读。想让用户重新看到，先撤回再发布。",
        createdAt: "创建于",
        publishedAt: "发布于",
        updatedAt: "最后修改于",
      },
      actions: {
        saveDraft: "保存草稿",
        publish: "发布",
        save: "保存",
        withdraw: "撤回",
        pin: "置顶",
        unpin: "取消置顶",
      },
      notices: {
        saved: "已保存。",
        published: "已发布，用户现在能看到它。",
        withdrawn: "已撤回成草稿，用户看不到它了。",
        pinned: "已置顶。",
        unpinned: "已取消置顶。",
      },
      deleteSection: {
        title: "删除这条公告",
        hint: "删除后不能恢复；已发布的会从所有用户的公告里消失。",
        action: "删除",
      },
      deleteDialog: {
        title: "删除这条公告？",
        hint: "删除后不能恢复。",
        published: "它已经发布，会从所有用户的公告里消失。",
        confirm: "删除",
      },
    },
  },
  /** 玩法页（GLOSSARY.md「玩法」）：导航里的第一级，每张卡进一个子页（礼物、成就、日历）。 */
  play: {
    title: "玩法",
    /** 子页读到状态之前。 */
    loading: "正在读取",
    /** 卡片状态那一行里各段之间。 */
    separator: " · ",
    /** 好感度和礼物没开放时：礼物、成就两个子页页首下面是这一句（第一级只剩「日历」卡）。 */
    closed: {
      title: "玩法暂时没有开放",
      description: "这里还没有开放好感度和礼物。已经有的礼物会留着，开放后照常能送。",
    },
    cards: {
      gifts: {
        name: "礼物",
        draws: (n: number) => `还有 ${n} 次抽奖`,
        backpack: (items: number) => `背包 ${items} 件`,
        resetCards: (n: number) => `重置卡 ${n} 张`,
        /** 名字旁的点，读屏读的名字：有新到的抽奖次数。 */
        dot: "有新到的抽奖次数",
      },
      achievements: {
        name: "成就",
        /** 平时：合起来的成就一共解锁了几个阶段。 */
        unlocked: (n: number) => `已解锁 ${n} 个阶段`,
        /** 有这台设备上还没看过的解锁时，换成这一句。 */
        unseen: (n: number) => `${n} 个新解锁`,
        /** 名字旁的点，读屏读的名字：有新解锁的成就。 */
        dot: "有新解锁的成就",
      },
      calendar: {
        name: "日历",
        /** 今天及以后最近的一件：「下一个：10月27日 樋口円香的生日」；今天就有时「今天：…」。 */
        next: (date: string, what: string) => `下一个：${date} ${what}`,
        today: (what: string) => `今天：${what}`,
        birthday: (name: string) => `${name}的生日`,
        /** 本周还有工作待排时，状态最前面一段。 */
        pending: (n: number) => `本周还有 ${n} 项工作待排`,
      },
      cycles: {
        name: "周期",
        /** 一位都没记过时。 */
        empty: "凭她的言行记下她的经期，这里替你推算。",
        /** 「记过 3 位 · 最近 円香 10月31日」：推算的下一次经期离今天最近的那位。 */
        status: (n: number, name: string, date: string) => `记过 ${n} 位 · 最近 ${name} ${date}`,
      },
      bar: {
        name: "VA-283",
        /** 今天还没玩完过光顾，玩完有奖励。 */
        rewardToday: "今天第一次光顾有奖励",
        /** 好感度和礼物开着，今天已经玩完过。 */
        rewarded: "今天的奖励领过了",
        /** 好感度和礼物关着：光顾什么都不给。 */
        unrewarded: "调一杯给来店的她",
      },
    },
    /** 周期子页（`/play/cycles`，GLOSSARY.md「周期」「推算」）。 */
    cycles: {
      lead: "凭她的言行记下她的经期，这里替你推算。",
      /** 搜索框右边的筛选：电脑上弹出框、手机上抽屉，单选。 */
      filter: {
        label: "筛选",
        only: (what: string) => `筛选，只看${what}`,
        title: "头像条里显示谁",
        all: "全部",
        recorded: "记过的",
        now: "推算在经前、经期的",
        unrecorded: "还没记过的",
        count: (n: number) => `${n} 位`,
      },
      /** 她那一块顶上的一句话。 */
      line: {
        none: "还没记过。记下一次，这里就开始推算。",
        recorded: (day: number) => `经期第 ${day} 天`,
        estimated: "推算在经期",
        premenstrual: (date: string) => `推算在经前 · ${date} 来`,
        late: (date: string) => `推算 ${date} 来，还没记下`,
        next: (date: string, days: number, from: string) => `下次经期推算在 ${date}（还有 ${days} 天），经前从 ${from} 起。`,
      },
      /** 月历上的三种记号，也是图例和点中那一天的说明。 */
      kinds: { recorded: "记下的经期", estimated: "推算的经期", premenstrual: "推算的经前" },
      /** 电脑上每段经前第一天的格子底部。 */
      premenstrualMark: "经前",
      /** 点中那一天的一条。 */
      day: {
        prompt: "点一天来记下她这次经期的第一天。",
        first: "这天是第一天",
        future: "不能记未来",
        edit: "改这次",
      },
      /** 右栏的三行。 */
      stats: {
        cycle: "周期",
        period: "经期",
        offBy: "过去的估算平均差",
        days: (n: string | number) => `${n} 天`,
        rough: "粗略估计",
        compareLater: "再记一次就能比较",
      },
      /** 推算变淡的原因，每种一句。 */
      reasons: {
        once: "再记一次就能按她自己的周期推算。",
        irregular: "她的周期长短不一，估算只作参考。",
        /** 「长短不一」那句末尾的链接，展开讲解的「青春期」。 */
        irregularLink: "见「青春期」",
        missed: "中间可能漏记了一次。",
        late: "这次可能还没记下。",
      },
      /** 右栏的「记过的经期」，新的在上。 */
      records: {
        title: "记过的经期",
        row: (days: number, gap: number | null) => (gap === null ? `${days} 天` : `${days} 天 · 隔 ${gap} 天`),
        edit: (date: string) => `改${date}这次`,
        all: (n: number) => `展开全部 ${n} 次`,
        less: "收起",
      },
      /** 最下面通栏的讲解七块（正文在 `lib/cycleGuide`）。 */
      guide: {
        title: "讲解",
        diagram: {
          label: "以 28 天为例：经期第 1–5 天，易孕期第 10–16 天，排卵日第 15 天",
          period: "经期 第 1–5 天",
          fertile: "易孕期 第 10–16 天",
          ovulation: "排卵日 第 15 天",
          caption: "以 28 天为例",
        },
      },
      /** 页面最后一行。 */
      disclaimer: "推算只是估计，不是医疗建议，不能用来避孕；身体不适请看医生。",
      /** 记一次、改一次的弹窗。 */
      dialog: {
        title: (name: string) => `记${name}的一次经期`,
        firstDay: "第一天",
        days: "天数",
        fewer: "少一天",
        more: "多一天",
        cancel: "取消",
        add: "记下",
        save: "保存",
        delete: "删除这次",
        /** 「2026年10月25日 周日」。 */
        fullDate: (year: number, month: number, day: number, weekday: string) => `${year}年${month}月${day}日 ${weekday}`,
      },
    },
    /** 日历子页（`/play/calendar`）。 */
    calendar: {
      /** 「10月27日」。 */
      date: (month: number, day: number) => `${month}月${day}日`,
      /** 星期几，0 是周日。 */
      weekdays: ["周日", "周一", "周二", "周三", "周四", "周五", "周六"],
      /** 这一天的清单里角色生日那一行名字后面的类别。 */
      birthday: "生日",
      /** 制作人自己的生日。 */
      mine: "我的生日",
      noEvents: "这一天没有事",
      /** 三类全筛掉时月视图下面那一句。 */
      nothingShown: "没有要显示的",
      /** 月视图上方的筛选：一排按钮，按下的是开着的。 */
      filters: {
        label: "筛选",
        character: "角色生日",
        producer: "我的生日",
        holiday: "节假日",
        schedule: "日程",
      },
      /** 月视图的标题「2026年10月」和两边的键。 */
      month: (year: number, month: number) => `${year}年${month}月`,
      previousMonth: "上个月",
      nextMonth: "下个月",
      /** 不在当月时出现，回到当月并选中今天。 */
      today: "今天",
      /** 表头一行周几，周一起。 */
      weekHeads: ["一", "二", "三", "四", "五", "六", "日"],
      /** 电脑上一格超过三件时的第三行。 */
      more: (n: number) => `还有 ${n} 项`,
      /** 格子的读屏名字：「10月27日 周二，2 项」。 */
      cell: (date: string, events: number) => (events > 0 ? `${date}，${events} 项` : date),
      /** 「只看她」时页首下面那一条，和看全部的 ✕。 */
      onlyHer: (name: string) => `只看${name}的日程`,
      showAll: "看全部",
      /** 页首末端的月 / 周切换（日程开着时才有）。 */
      views: { label: "视图", month: "月", week: "周" },
    },
    /** 日历子页的日程（GLOSSARY.md「日程」「工作」「时间段」）：周视图、待排、保存条、确认框和几个抽屉。 */
    schedule: {
      /** 周几，0 是周一。 */
      weekdays: ["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
      /** 四类工作，图标的读屏名字。 */
      categories: { practice: "练习", appearance: "出镜", business: "事务", private: "私人" },
      /** 三个时间段的名字，和周视图的表头。 */
      slots: ["上午", "下午", "晚上"],
      slotHeads: ["上午 6–12", "下午 12–18", "晚上 18–24"],
      /** 一项占的时间：「周三 下午」「周三 上午到下午」「周三 一整天」。 */
      when: (day: string, slots: string) => `${day} ${slots}`,
      span: (from: string, to: string) => `${from}到${to}`,
      wholeDay: "一整天",
      /** 周视图的标题和两边的翻页键。 */
      thisWeek: "本周",
      nextWeek: "下周",
      range: (from: string, to: string) => `${from} – ${to}`,
      previous: "上周",
      next: "下周",
      unpublished: "本周的工作北京时间周一 0:00 发布",
      /** 没有工作的已过、进行中的格子。 */
      past: "已过",
      underWay: "进行中",
      /** 工作块的读屏名字和状态（已经开始了的草稿块上也写 `states.started`）。 */
      block: (who: string, job: string, state: string) => `${who} ${job}，${state}`,
      states: { saved: "已保存", draft: "草稿", now: "进行中", done: "做完了", started: "开始了，存不了" },
      /** 排不了的原因，和后端 `schedule.py` 顶上的常量一样。 */
      reasons: {
        wholeDayFromMorning: "一整天的工作只能从上午排",
        noRoomThatDay: "当天排不下",
        past: "已经过了",
        underWay: "正在进行",
        onlyIn: (slots: string) => `只能排在${slots}`,
        taken: "格子里有别的工作",
      },
      /** 几个时间段连成一句：「晚上」「下午和晚上」。 */
      slotList: { separator: "、", last: "和" },
      /** 待排。 */
      pending: {
        title: (n: number) => `待排 ${n} 项`,
        left: (n: number) => `还能排 ${n} 格`,
        expires: "周日 24 点后作废",
        tonight: "今晚 24 点后作废",
        /** 一项的说明：「2 段 · 只能下午、晚上」。 */
        length: (n: number) => `${n} 段`,
        only: (slots: string) => `只能${slots}`,
        allPlaced: "本周的工作都排好了",
      },
      /** 手机上点了草稿块的抽屉。 */
      takeBack: "拿回待排",
      /** 手机上点了待排一项的抽屉，列出放得下的时间段。 */
      placeAt: (job: string) => `${job} 排到…`,
      nowhere: "没有放得下的时间段",
      /** 页底的保存条。 */
      drafts: (n: number) => `草稿 ${n} 项`,
      draftsNote: "保存后她才知道",
      save: "保存",
      /** 保存前的确认框。 */
      confirm: {
        title: (n: number) => `保存这 ${n} 项？`,
        description: "保存后不能更改，也不能撤掉。",
        cancel: "再看看",
        save: "保存",
      },
      /** 保存时没存下的几项：「真乃的拍摄广告：已经开始了，不保存，退回待排。」 */
      whose: (name: string, job: string) => `${name}的${job}`,
      startedBack: (jobs: string) => `${jobs}：已经开始了，不保存，退回待排。`,
      returnedBack: (jobs: string, reason: string) => `${jobs}：${reason}，不保存，退回待排。`,
    },
  },
  /** 酒吧（`/play/bar`，GLOSSARY.md「酒吧」）：画面里的字都是像素字，这里是它们写什么。 */
  bar: {
    /** 电视，读屏读的名字。 */
    tv: "换台",
    /** 侧边菜单下排，原版「退出」的位置：回玩法页。 */
    leave: "离开",
    /** 店门口和侧边菜单上排原版「读取」的位置：没全屏时进全屏，全屏时退出。 */
    screen: { full: "全屏", window: "窗口" },
    /** 侧边菜单上排原版的「设置」，和它弹出的设置框（「声音」「图像」两个标题和字图是原版的图，这里是读屏读的）。 */
    settings: {
      name: "设置",
      close: "关上设置",
      music: "背景音乐",
      sfx: "音效",
      quieter: (what: string) => `${what}调小`,
      louder: (what: string) => `${what}调大`,
      volume: (what: string, percent: number) => `${what}音量，${percent}%`,
      scanlines: "扫描线",
    },
    /** 点唱机：侧边菜单下排原版的位置那一格、选曲界面、店里的小播放器。曲名用原版的英文名，不在这里。 */
    jukebox: {
      name: "点唱机",
      title: "请选择一首曲子",
      add: "点击左侧的曲名来添加曲目。",
      /** 选曲界面左下的说明：电脑（细指针）和手机各一句。 */
      howTo: {
        fine: "悬停在曲名上试听，右键点击右侧曲目移除，点两首曲目可替换顺序。",
        coarse: "长按左侧曲名试听，长按右侧曲目移除，点两首曲目可替换顺序。",
      },
      /** 右边的槽，读屏读的。 */
      slot: (n: number, title: string | null) => (title === null ? `第 ${n} 首，空` : `第 ${n} 首，${title}`),
      prevPage: "上一页",
      nextPage: "下一页",
      ready: "Ready!",
      player: { previous: "上一首", pause: "暂停", play: "播放", next: "下一首", shuffle: "随机", loop: "单曲循环" },
    },
    /** 手机竖着时盖住整层的提醒。 */
    portrait: "请横过来",
    /** 安卓上提醒下面的按钮：进全屏、锁成横屏。 */
    fullscreen: "全屏横过来",
    /** 店门口：点一下进门；进不了时写为什么。 */
    door: {
      enter: "点一下进门",
      /** 店门口的小按钮：从头再看一遍教程。 */
      tutorial: "教程",
      overLimit: (time: string) => `这一小时的光顾次数用完了，${time} 以后再来`,
      failed: "没能进门，再点一下试试",
    },
    /** 文本框，读屏读的名字：点了打完这句或翻页。 */
    next: "继续",
    /** 文本框里制作人的名字。 */
    producer: "制作人",
    /** 教程期间侧边菜单「点唱机」那一格换成它：跳过教程，直接去选曲界面。 */
    skip: "跳过",
    /** 调酒台：开关、按钮上的字，和读屏读的材料份数。 */
    counter: {
      ice: "加冰",
      aged: "陈化",
      on: "，开着",
      off: "，关着",
      reset: "重做",
      mix: "调制",
      stop: "停止",
      serve: "上酒",
      parts: (name: string, n: number) => `${name}，${n} 份`,
    },
    /** 配方书：四个标签、每栏的标题、口味和种类的菜单分类名，翻页的读屏。饮品名用英文原名，不在这里。 */
    book: {
      tabs: { name: "按名称", flavor: "按口味", kind: "按种类", bottle: "瓶装饮品" },
      search: { name: "按名称搜索", flavor: "按口味搜索", kind: "按种类搜索", bottle: "瓶装饮品" },
      flavors: { sweet: "甜味", bitter: "苦味", sour: "酸味", spicy: "辛辣", bubbly: "发泡" },
      kinds: { girly: "女性化", manly: "男性化", classic: "经典", classy: "时尚", promo: "宣传" },
      /** 口味、种类的分类和它列出饮品时的标题，如「甜味饮品」。 */
      category: (name: string) => `${name}饮品`,
      prev: "上一页",
      next: "下一页",
      /** 瓶装的图，读屏读的：拖进摇酒器。 */
      bottle: (name: string) => `${name}，拖进摇酒器`,
    },
    /** 光顾没了（请求得 410、调用中途断了）时店门口写的。 */
    visitGone: "这次光顾已经结束了",
    /** 模型出错时文本框里的按钮。 */
    retry: "再试一次",
    /** 她告别以后的结束卡：当天第一次写得到了什么，之后只写她走了。 */
    end: {
      draws: "抽奖 +1",
      heart: "♥ ",
      affinityUp: "好感度上升",
      /** 什么都没给时；没读到她是谁时写「她」。 */
      left: (name: string | null) => `${name ?? "她"}走了`,
      again: "再营业",
    },
  },
  /** 礼物子页（`/play/gifts`，GLOSSARY.md「礼物」「抽奖」，DESIGN.md「玩法页」）：抽奖台、重置卡条、我的礼物，和送礼面板、抽奖弹窗里的字。 */
  gifts: {
    /** 对话页上的送礼入口（冷却时输入栏右边、页首好感度标识的说明末尾、冷却版结束卡的主按钮），都跳到礼物子页。 */
    giveHer: "送她一件礼物",
    /** 从对话页跳来时页首下面那一条，和取消预选的 ✕。 */
    pickFor: (name: string) => `给${name}挑一件礼物`,
    cancelPick: (name: string) => `不预选${name}`,
    /** 抽奖台。 */
    draw: {
      title: "抽奖",
      left: (n: number) => `还有 ${n} 次`,
      /** 小点的读屏；`over` 是成就给的让次数超过上限时，不再说「最多攒几次」。 */
      label: (n: number, max: number) => `抽奖还有 ${n} 次，最多攒 ${max} 次`,
      over: (n: number) => `抽奖还有 ${n} 次`,
      /** 超过上限（成就给的）时 7 个点后面写超出几次。 */
      more: (n: number) => `+${n}`,
      /** 下面那句说明：平时、攒满、用完。`next` 是下次到账的「今天 / 明天 HH:MM」（每天北京时间 0 点发，按制作人的时区写）。 */
      notes: {
        usual: (next: string, max: number) => `${next} 再发 2 次，最多攒 ${max} 次`,
        /** 每天发的那份攒到上限了；成就给的可以超过上限，所以不写「攒满几次」。 */
        full: "每天发的已攒满，抽掉之前不会再发",
        none: (next: string) => `已经抽完了，${next} 再发 2 次`,
      },
      once: "抽一次",
      all: "全部抽完",
    },
    /** 抽奖弹窗：礼物盒跳一会儿，然后揭晓。 */
    drawing: {
      opening: "正在打开礼物盒",
      /** 单抽的读屏标题；全部抽完的是「抽到 n 样东西」。 */
      one: "抽到了",
      all: (n: number) => `抽到 ${n} 样东西`,
      again: (n: number) => `再抽一次（还有 ${n} 次）`,
      give: "送给谁…",
      keep: "收下",
      resetCard: {
        name: "重置卡",
        rarity: "很少见",
        note: "不是礼物，自己用：把所有低于信任的角色拉回信任，冷却中的马上可以说话。能攒，不过期。",
      },
    },
    /** 重置卡条（有重置卡时才出现）和用之前的确认框。 */
    resetCards: {
      title: "重置卡",
      count: (n: number) => `×${n}`,
      /** 「×n」的读屏。 */
      label: (n: number) => `${n} 张`,
      notes: {
        some: (n: number) => `现在用会把 ${n} 位拉回信任`,
        none: "现在没有低于信任的角色，留着以后用。",
      },
      use: "使用",
      confirm: {
        title: "使用一张重置卡？",
        description: "下面几位会回到信任，冷却中的马上可以说话。她们不会知道发生过什么。",
        /** 列表里一位名字后面的读屏：现在的档位会回到信任。 */
        becomes: (now: string) => `，${now}，会回到信任`,
      },
    },
    rarity: { common: "普通", uncommon: "少见", rare: "稀有" },
    mine: "我的礼物",
    filters: {
      label: "按类别筛选",
      all: "全部",
      food: "吃的",
      drink: "饮品",
      flower: "花草",
      trinket: "小物件",
    },
    /** 网格里一格的读屏：名字、件数、稀有度。 */
    held: (name: string, count: number, rarity: string) => `${name}，${count} 件，${rarity}`,
    count: (n: number) => `×${n}`,
    noneOfKind: "这一类还没有礼物",
    empty: {
      title: "还没有礼物",
      withDraws: "抽一次，抽到的礼物会放在这里。",
      withoutDraws: (next: string) => `${next} 会发 2 次抽奖，抽到的礼物会放在这里。`,
    },
    /** 送礼面板：点一件礼物拉出来，选一位送出。 */
    give: {
      left: (n: number) => `还有 ${n} 件`,
      to: "送给谁",
      cooling: "冷却中",
      send: (name: string) => `送给${name}`,
      choose: "选一位",
    },
    /** 送出后页面底部的提示；有变化时用变化胶囊的话（copy.conversation.affinity.cues）。 */
    given: {
      stillCooling: (name: string, until: string) => `${name}还没消气，${until} 就会愿意说话了`,
      given: (name: string) => `已经送给${name}`,
      toConversation: "去对话",
    },
  },
  /** 成就（GLOSSARY.md「成就」）：她的对话页面板和「成就」子页那一小节里每一行的字。 */
  achievements: {
    names: {
      turns: "和她的回合",
      call_time: "和她通话",
      gifts: "送她的礼物",
      tier: "她的好感度到过",
      characters: "往来过的角色",
      intimate_characters: "到过亲密的角色",
      days: "来过的天数",
      draws: "抽过的奖",
    } as Record<string, string>,
    /** 进度和门槛的写法（通话时长另见 `duration`）；不认识的成就只写数字。 */
    units: {
      turns: (n: number) => `${n} 个回合`,
      gifts: (n: number) => `${n} 件`,
      characters: (n: number) => `${n} 位`,
      intimate_characters: (n: number) => `${n} 位`,
      days: (n: number) => `${n} 天`,
      draws: (n: number) => `${n} 次`,
    } as Record<string, (n: number) => string>,
    duration: {
      minutes: (m: number) => `${m} 分钟`,
      hours: (h: number) => `${h} 小时`,
      hoursMinutes: (h: number, m: number) => `${h} 小时 ${m} 分`,
    },
    /** 档位那一行只写下一个档位，不写好感度的数值。 */
    nextTier: (tier: string) => `下一个：${tier}`,
    allUnlocked: "全部解锁",
    draws: (n: number) => `抽奖 ×${n}`,
    complete: "集齐",
    completed: "集齐了",
    resetCards: (n: number) => `重置卡 ×${n}`,
    /** 她的对话页更多菜单里的那一项和它打开的面板。 */
    open: "成就",
    title: "成就",
    /** 阶段点的读屏名字。 */
    stagesLabel: (unlocked: number, count: number) => `解锁了 ${unlocked}/${count} 个阶段`,
    /** 新解锁那一行名字旁的点的读屏文字。 */
    unseen: "新解锁",
    /** 页首的奖杯：解锁她的阶段时跳出来，「+n」是这次到账的抽奖次数。 */
    trophy: (draws: number) => `成就，抽奖 +${draws}`,
  },
  memories: {
    intro: "角色们在对话中记下的、关于你的事。所有角色共用这些记忆，对一位角色说过的事，其他角色会以转述的口吻知道。删除后，角色不会再想起这件事。标为「已被取代」的记忆，已经被你后来说的话更新，角色不会再想起；删掉取代它的那条，它就恢复。",
    loading: "正在读取…",
    empty: "角色们还没有记下关于你的事。",
    toldTo: (name: string) => `对${name}说的`,
    goneCharacter: "已不在的角色",
    superseded: "已被取代",
    date: (year: number, month: number, day: number) => `${year}年${month}月${day}日`,
    remove: "删除",
    removeLabel: (text: string) => `删除记忆：${text}`,
    removeTitle: "删除这条记忆？",
    removeDescription: (text: string) => `「${text}」删除后，所有角色都不会再想起这件事，无法恢复。`,
    clear: "清空全部记忆",
    clearTitle: "清空全部记忆？",
    clearDescription: (count: number) => `确定清空全部 ${count} 条记忆吗？所有角色都会忘记这些事，无法恢复。`,
    clearConfirm: "确定清空",
  },
  privacy: {
    title: "隐私政策",
    sections: [
      {
        title: "我们保存哪些数据",
        items: [
          { term: "登录方式", text: "你用来登录的 Google 或 GitHub 账号的编号、显示名和邮箱。我们拿不到你的密码。" },
          { term: "对话", text: "你对角色说的话（打字的，以及通话时语音识别出的文字）和角色的回复，你送她礼物后留在对话里的送礼记录，以及「她挂断了电话」这样的记录（送礼记录和这类记录都不会被提炼成记忆）。她发给你的照片也存在对话里，只有你能看，随那段对话一起删除，也会进备份。她的搭话也存在对话里，随那段对话一起删除，也会进备份和你导出的数据包。每通接通了的通话，会在所在的对话下记下开始时间和时长，用于统计，不含通话内容，随那段对话一起删除。通话的录音不保存。开了新对话以后，之前的对话可以在对话页的「历史对话」里逐段删除，删除后立即从线上彻底删除（当前对话不能删除，开了新对话后它就能删了）；她在那段对话里记下的记忆不受影响，可以在设置的「记忆」里另外删除；已经做好的备份里的副本，最多 30 天后随备份过期清除。" },
          { term: "记忆", text: "角色从对话中记下的关于你的事，所有角色共用，你可以在设置的「记忆」里查看和删除。" },
          { term: "制作人档案", text: "你设置的称呼、性别、时区、生日（只有月和日）和所在城市（城市名和它的大致坐标）。" },
          { term: "好感度", text: "每位角色对你各有一份好感度，以及有没有在冷却、什么时候解除。你只看得到档位，看不到数值。它不能单独删除，删除记忆也不影响它；删除全部数据时一起删除。" },
          { term: "礼物", text: "你背包里的礼物、重置卡，还有抽奖次数。删除全部数据时一起删除。" },
          { term: "成就", text: "每个成就的累计进度和解锁了哪些阶段，以及它们给的抽奖次数和重置卡的到账记录。删除历史对话不影响它们，也不进数据包；删除全部数据时一起删除。" },
          { term: "日程", text: "你把哪一周的哪些工作排在了哪几个时间段，以及它们有没有算过好感度。删除历史对话不影响它，也不进数据包；删除全部数据时一起删除。" },
          { term: "周期记录", text: "你在周期页给各位角色记下的经期（第一天和天数），按你和角色分开存在服务器上。删除历史对话不影响它，会进备份，导出数据包时可以带上；删除全部数据时一起删除。" },
          { term: "酒吧", text: "每次在酒吧玩完的光顾：来的是哪位角色、什么时候、她的来意和聊的话题、每一单她要的和你上的饮品、上得怎么样，以及她醉没醉。不存你们说的话；点唱机的曲目选择和酒吧的设置只存在这台设备上。删除历史对话不影响它，会进备份，不进数据包；删除全部数据时一起删除。" },
          { term: "朋友圈", text: "角色在你的朋友圈里发的动态（文字、配图、地名和当时的天气），其他角色的赞和评论，你的赞、评论和她的回复，以及你在设置里的「朋友圈」开关和上次打开朋友圈的时间。只有你能看。每条动态满 30 天后，连同配图、赞和评论一起自动删除；你或部署者关掉朋友圈时不删，照常到期删除。删除历史对话不影响它，会进备份，不进数据包；删除全部数据时一起删除。" },
          { term: "搭话", text: "你在设置里的「搭话」开关，以及你看过哪些搭话。" },
          { term: "自带密钥", text: "如果你填了自己的 API key，它只保存在你的浏览器里，我们不保存；每次回合、通话、朗读或光顾酒吧时随请求发给服务器，只在处理期间（光顾是到这次光顾结束）留在内存里，不写入数据库、日志或备份。" },
          { term: "登录状态和限额的计数", text: "让你在各台设备上保持登录的状态，以及最近 24 小时内你发起回合、通话、朗读和光顾酒吧的次数、收到照片的张数（用于限额）。" },
          { term: "运行记录", text: "每个回合、每次通话、每次搭话、每次光顾、每条动态和她每次回你的评论是和哪位角色、什么时候、结果如何（成功、失败、被拒绝等）、通话的时长和结束原因（包括角色挂断），判断模型对每个回合的判断结果（这句话让角色开心、不舒服还是没有影响，有没有判为不该说的话或操纵，有没有因此进入冷却），以及其中用了哪些服务和模型、是否用了自带密钥、用量（例如 token 数）、有没有出错和花了多久；角色发照片或配图时，还记下描述画面的 tag 里有几个因为越界被剥掉、各属于哪一类（不记 tag 本身）；搭话还记下你有没有回；解锁一个成就阶段或集齐一位角色时，记下是哪个阶段、哪位角色。不含你说的话和角色的回复，不记密钥，也不记自带 LLM 的服务地址和模型名。满 90 天自动删除。" },
          { term: "备份", text: "以上数据每天加密备份一次，存放在部署者的私有云存储里，每份保留 30 天，用于服务器出故障时恢复。" },
        ],
        notes: [],
      },
      {
        title: "这些数据会交给哪些第三方处理",
        items: [
          // 不论免限额密钥是哪几项都要对，不点名哪几项。
          { term: "语言模型服务", text: "扮演角色、提炼记忆和给对话起标题时，对话内容和相关记忆会发给语言模型服务：你填了自己的 LLM，就发给你选择的服务（另配了后台模型的，提炼记忆和起标题时发给它）；没填，就发给部署者配置的服务。开着搭话时，即使你不在线，服务器也会把这段对话和相关记忆发给部署者配置的服务，生成她先说的话；填了自己的 LLM 也一样。开着朋友圈时，即使你不在线，服务器也会用部署者配置的服务写她的动态和评论区：发动态时带上她记下的相关记忆和你今天给她排的工作，回你的评论时带上你的评论、相关记忆和你们最近几个回合的对话；填了自己的 LLM 也一样。" },
          { term: "判断模型", text: "每个回合，你说的话连同最近几个回合的对话会发给部署者配置的判断模型（TypeSafe 的 Jev，经 OpenRouter 等转发；或 Cloudflare 的 Clef），用来判断要不要回忆剧情或查资料、你是不是在要照片，以及这句话让角色对你的好感度怎样变化；通话中角色的回复也会一段段发过去，判断她的情绪。判断模型始终由部署者提供，填了自带密钥也不改变这一点。" },
          { term: "语音服务", text: "通话时，你的声音会发给部署者选择的语音识别服务（Soniox 或阿里云百炼）识别成文字，角色的回复会发给 Fish Audio 合成语音。阿里云百炼不会用你的声音训练模型，但会保存一段时间，存放在中国内地或新加坡，取决于部署者的账号。" },
          { term: "向量化和重排服务", text: "为了在对话中找到相关的剧情和记忆，你说的话和记忆会发给部署者选择的向量化服务（硅基流动或 Google Gemini）和重排服务（硅基流动）。" },
          { term: "生图服务", text: "角色给你发照片时，描述这张照片的英文 tag（地点、服装、动作，由角色根据对话写出）会发给部署者配置的生图服务（NovelAI，或者转发它的中转）；不发你说的原话。你填了自己的生图密钥，就发给你自己选择的服务。她在朋友圈发配图时也只发描述配图的英文 tag，始终发给部署者配置的服务，填了自己的生图密钥也一样。" },
          {
            term: "天气服务",
            text: "打字、通话和搭话时，服务器会向 Open-Meteo 查东京的天气。你在制作人档案里设了所在城市时，还会把这个城市的大致坐标发给{qweather}（天气服务由和风天气驱动）和 Open-Meteo，查当地的天气和预警。搜索城市时，你输入的城市名会发给和风天气；用「用当前位置」时，浏览器给出的坐标会发给和风天气，找出离你最近的城市，坐标本身不保存。",
            links: { qweather: { label: "和风天气", href: "https://www.qweather.com" } },
          },
          { term: "登录服务", text: "登录时，Google 或 GitHub 会知道你登录了这个网站。" },
        ],
        notes: ["如果你填了自带密钥，对应的内容会发到你自己选择的服务商，由你和该服务商之间的约定管辖。"],
      },
      {
        title: "管理者能看到什么",
        items: [
          { term: "能看到", text: "你的登录方式（Google 或 GitHub、显示名和邮箱）、注册和最后活跃的时间、你是经哪条邀请链接注册的（如果是）、最近 24 小时到 30 天的回合和通话次数（包括被限额拒绝的）、你的用量里有多少用的是自带密钥、是否被封禁（以及封禁时管理者写的备注），以及有没有单独的限额。" },
          { term: "看不到", text: "你和角色的对话、她发给你的照片和描述照片的 tag、角色记下的记忆、你的制作人档案，各位角色对你的好感度和冷却，以及你的礼物、重置卡、抽奖次数、成就、日程、周期记录、光顾记录和朋友圈（动态、配图、赞和评论）；好感度和朋友圈只能看到所有用户合起来的统计，管理者也不能调整某一位用户的好感度。" },
        ],
        notes: [
          "管理者是部署者指定的少数几位用户，在只有他们能进入的后台里管理这个网站。运行记录还会汇总成全站的统计，用来查看各项服务是否正常、有多少人在用、大约花了多少钱。",
          "管理者可以封禁用户，或单独调整某位用户的限额；被封禁的用户不能再登录，进行中的通话会挂断，数据保持原样。",
        ],
      },
      {
        title: "怎样删除你的全部数据",
        items: [],
        notes: [
          "在设置页点「删除我的全部数据」，再确认一次，你的记忆、对话、制作人档案、登录方式、登录状态和限额的计数都会立刻从线上彻底删除（不是标记删除），所有设备都会退出登录；已经做好的备份里的副本，最多 30 天后随备份过期清除。这个浏览器里的自带密钥会在你登出或删除账号时一并清除，其他设备上的需要你在那几台设备上自己删除。之后再用同一个 Google 或 GitHub 身份登录，会是一位全新的用户。",
          "导出的数据包在你自己手里，删除数据不会删到它。",
          "你的运行记录不会随之删除，但不再关联到你，也无法再对应回你，满 90 天后照常删除；这样全站的统计数字不会因为有人离开而变化。管理者也可以应你的要求代你删除，效果完全一样。",
          "被封禁的用户被删除后，我们会保留他用过的登录方式的编号经过加密哈希后的结果（不含名字和邮箱），用来阻止他用同一身份再次登录；这份名单不会过期。",
          "已经发给第三方服务的内容，按各服务自己的政策保存和删除。",
        ],
      },
    ],
    contact: {
      title: "联系部署者",
      text: (contact: string) => `对你的数据有疑问，或者想请管理者代你删除，请联系：${contact}`,
    },
    lastUpdated: "最后更新：2026 年 10 月 31 日",
  },
  terms: {
    title: "使用条款",
    items: [
      { term: "非官方的粉丝作品", text: "与《偶像大师 闪耀色彩》的版权方和官方没有任何关系。" },
      { term: "角色由 AI 扮演", text: "和你说话、在朋友圈发动态和评论的角色不是真人，也不代表官方设定。她们说的话可能出错，请不要当真，也不要依赖她们做重要的决定。" },
      { term: "不保证一直可用", text: "服务由个人部署和负担费用，可能随时调整限额、暂停或关闭，数据也可能因故丢失。" },
      { term: "年满 13 岁", text: "你需要年满 13 岁才能使用。" },
      { term: "不要滥用", text: "请不要用它做违法的事，或刻意刷用量；管理者可以封禁这样的用户，或单独收紧他的限额。" },
      { term: "玩法：好感度、冷却和礼物", text: "角色对你的好感度会随你说的话升降：好好对她，她会更亲近你；冒犯她，她会疏远你，好感度跌到底时她会暂时不和你说话，这段时间叫冷却，通话中她也会挂断电话；一次通话里说了两次不该说的话（性骚扰、辱骂、威胁等），她同样会挂断。这些都是玩法的一部分，由 AI 根据你说的话判断，可能误判。冷却最长 24 小时，到时自动解除，不是封禁，也不是限额；管理者不会人工调整任何人的好感度或冷却。你在朋友圈的赞和评论不影响好感度。礼物、重置卡和抽奖次数只是应用里的玩法物品，没有现金价值，不能转让或交易；服务调整或关闭时，它们可能随之消失。成就给的抽奖次数和重置卡也一样；成就的内容、门槛和奖励可能调整，已经得到的不收回。每周发布的工作和你排的日程只影响她怎么说话和她对你的好感度，没有别的奖励；没排的工作每周作废，工作的内容和每周的规模可能调整。周期页的推算只供参考，不作医疗或避孕的依据。" },
      { term: "自带密钥", text: "你填进来的自己的 API key（LLM、语音合成、语音识别、生图都算），由你自己遵守那项服务的条款，包括它对年龄和用途的要求。" },
    ],
    seePrivacy: "数据怎样保存和处理，见{privacy}。",
    lastUpdated: "最后更新：2026 年 10 月 31 日",
  },
};
