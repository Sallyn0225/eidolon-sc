// 界面上的图标统一用 Lucide，以语义别名导出，不手绘 SVG（DESIGN.md「The Library Icon Rule」；品牌标志是例外，见文件末尾）。
export {
  ArrowRightLeft as MicSwitchIcon,
  ChevronDown as CollapseIcon,
  ChevronLeft as BackIcon,
  Mic as MicIcon,
  MicOff as MicOffIcon,
  Phone as PhoneIcon,
  PhoneOff as HangUpIcon,
  Shirt as OutfitIcon,
} from "lucide-react";

// 她结束了对话（GLOSSARY.md「已结束的对话」）：对话事件的分隔线和换掉输入栏的结束卡。
export { MessageCircleOff as EndedIcon } from "lucide-react";

// 她好像不太舒服（对话事件 `unwell`）：中性，不用她的颜色、不用心形。
export { CloudDrizzle as UnwellIcon } from "lucide-react";

// 记忆页、设置页用的图标（ticket 06）。
export { Trash2 as TrashIcon } from "lucide-react";

// 看板长列表底下的「展开全部」「收起」。
export { ChevronDown as ShowMoreIcon, ChevronUp as ShowLessIcon } from "lucide-react";

// 后台导航用的图标。
export {
  LayoutDashboard as DashboardIcon,
  Megaphone as AnnouncementsIcon,
  SlidersHorizontal as ConfigIcon,
  Users as UsersIcon,
} from "lucide-react";

// 发送键和更多菜单。
export { ArrowUp as SendIcon, Ellipsis as MoreIcon } from "lucide-react";

// 失败提示（components/app/FailureNotice）。
export { CircleAlert as FailureIcon } from "lucide-react";

// 设置页「已绑定」的提示和它的关闭键（shadcn-redesign 18）。
export { CircleCheck as SuccessIcon, X as CloseIcon } from "lucide-react";

// 成就面板里没集齐的「集齐」一行。
export { Circle as TaskOpenIcon } from "lucide-react";

// 对话页更多菜单的「成就」，和解锁她的阶段时页首好感度标识左边跳出的奖杯（GLOSSARY.md「成就」）。
export { Trophy as AchievementsIcon } from "lucide-react";

// 对话列表页首的公告铃铛（GLOSSARY.md「公告」）；后台导航的公告用 Megaphone。
export { Bell as AnnouncementsBellIcon } from "lucide-react";
// 对话列表页首的信封键（GLOSSARY.md「信」）；读信时右上角的静音键。
export { Mail as LetterIcon, Volume2 as LetterSoundIcon, VolumeX as LetterMutedIcon } from "lucide-react";

// 对话列表页首铃铛旁边的服务状态（GLOSSARY.md「服务状态」）。
export { Activity as ServiceStatusIcon } from "lucide-react";

// 对话列表的搜索框；通话条右端「回到通话 ›」的箭头。
export { ChevronRight as ForwardIcon, Search as SearchIcon } from "lucide-react";

// 对话列表搜索框右边的筛选按钮；置顶那一行的图钉，也是行菜单里「置顶」的图标。
export { ListFilter as FilterIcon, Pin as PinIcon } from "lucide-react";

// 对话列表行菜单里的「取消置顶」「在列表中隐藏」「在列表中显示」。
export { Eye as ShowIcon, EyeOff as HideIcon, PinOff as UnpinIcon } from "lucide-react";

// 对话页更多菜单里的「新对话」「历史对话」（换衣装用 OutfitIcon）；历史对话底部只读卡的图标（GLOSSARY.md「历史对话」）。
export { History as PastConversationsIcon, SquarePen as NewConversationIcon } from "lucide-react";

// 后台用户列表可以排序的表头：按它从多到少排着的，和还没按它排的（shadcn-redesign 22）。
export { ArrowDown as SortedIcon, ArrowUpDown as SortableIcon } from "lucide-react";

// 她的气泡菜单里的「朗读」，和下面语音条的播放、暂停（GLOSSARY.md「朗读」）。
export { Pause as PauseVoiceIcon, Play as PlayVoiceIcon, Volume2 as ReadAloudIcon } from "lucide-react";

// 通话层右上角的「只看文字」胶囊。
export { Captions as TextOnlyIcon } from "lucide-react";

// 通话层底栏的打字键：点了底栏换成输入栏。
export { Keyboard as TypingIcon } from "lucide-react";

// 导航栏（电脑）和 dock（手机）的四项（朋友圈开着时）；玩法页第一级「礼物」卡的图标也是 GiftIcon（「成就」卡用 AchievementsIcon）。
export {
  Aperture as MomentsIcon,
  MessageCircle as ConversationsIcon,
  Settings as SettingsIcon,
  Shapes as PlayIcon,
} from "lucide-react";
export { Gift as GiftIcon } from "lucide-react";

// 朋友圈页一条动态下面那一块里，赞的人那一行打头的心形；也是行尾「⋯」弹出的「赞」。
export { Heart as LikesIcon } from "lucide-react";
// 朋友圈页行尾「⋯」弹出的「评论」。
export { MessageCircle as CommentIcon } from "lucide-react";

// 日历：玩法页第一级「日历」卡；筛选、月视图和这一天的清单里我的生日（蛋糕，角色生日的蛋糕是她的颜色）和节假日（旗子）。
export { CalendarDays as CalendarIcon } from "lucide-react";
export { Cake as BirthdayIcon, Flag as HolidayIcon } from "lucide-react";
// 日历子页月视图标题两边的上个月、下个月。
export { ChevronLeft as PreviousMonthIcon, ChevronRight as NextMonthIcon } from "lucide-react";
// 日历子页页首末端的月 / 周切换。
export { CalendarDays as MonthViewIcon, Rows3 as WeekViewIcon } from "lucide-react";
// 日程：四类工作（练习、出镜、事务、私人）的图标，都不上色；保存过的工作块末尾的锁。周视图的翻页键沿用上个月、下个月那两枚。
export {
  Briefcase as BusinessJobIcon,
  Camera as AppearanceJobIcon,
  Coffee as PrivateJobIcon,
  Lock as LockedIcon,
  Music as PracticeJobIcon,
} from "lucide-react";
// 日历子页筛选里的「日程」。对话页更多菜单的「她的日程」用 CalendarIcon。
export { CalendarCheck as ScheduleIcon } from "lucide-react";

// 周期：玩法页第一级「周期」卡（中性）；周期子页记录行的铅笔、点中那一天的「改这次」，弹窗里天数的 −/+。
export { CalendarHeart as CyclesCardIcon } from "lucide-react";
export { Minus as FewerDaysIcon, Pencil as EditRecordIcon, Plus as MoreDaysIcon } from "lucide-react";
// 酒吧：玩法页第一级「VA-283」卡（中性）。
export { Martini as BarCardIcon } from "lucide-react";

// 礼物子页：抽奖台的「抽一次」和抽到稀有礼物时插画角上的闪光；我的礼物的四个类别筛选；
// 重置卡确认框里「现在的档位 → 信任」的箭头。
export { Sparkles as DrawIcon, Sparkles as RareIcon } from "lucide-react";
export { ArrowRight as BecomesIcon } from "lucide-react";
export { Cookie as FoodIcon, CupSoda as DrinkIcon, Flower2 as FlowerIcon, Gem as TrinketIcon } from "lucide-react";

// 设置一级的各类（档案、记忆、统计、通话用 PhoneIcon、搭话、周期、外观、自带密钥、登录与数据、数据包、关于）和「关于」上面的「赞赏」；「关于」里新标签页打开的链接行尾的外链图标。
export {
  BookHeart as MemoriesIcon,
  CalendarSync as CyclesIcon,
  HandHeart as SponsorIcon,
  ChartColumn as StatsIcon,
  CircleUser as ProfileIcon,
  ExternalLink as ExternalLinkIcon,
  Info as AboutIcon,
  KeyRound as OwnKeysIcon,
  Palette as AppearanceIcon,
  LogIn as SignInIcon,
  MessageCircleHeart as ReachOutsIcon,
  Package as DataPackageIcon,
} from "lucide-react";

// 对话页首的好感度标识（GLOSSARY.md「好感度」「冷却」）：五档心形和冷却中的沙漏；
// 回合改变了好感度时，心形上、变化胶囊里和通话层状态行里的升降小箭头。
export {
  ArrowDown as AffinityDownIcon,
  ArrowUp as AffinityUpIcon,
  Heart as AffinityHeartIcon,
  HeartCrack as AffinityDistantIcon,
  HeartOff as AffinityColdIcon,
  Hourglass as CooldownIcon,
} from "lucide-react";

// 她发来的照片（GLOSSARY.md「照片」）：对话记录里照片生成中的占位、对话列表和历史对话面板里最后一句前的相机，
// 没发出来时的说明，和这一小时的照片用完时她那条回复后面的胶囊。
export { Camera as PhotoIcon, CameraOff as PhotosUsedUpIcon, ImageOff as PhotoFailedIcon } from "lucide-react";

// 导航栏底部（电脑）的 GitHub 仓库链接；品牌标志 Lucide 不收，是 The Library Icon Rule 的例外。
export { GitHubIcon } from "./GitHubIcon";
