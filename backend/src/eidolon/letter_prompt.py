"""What she writes a letter with (GLOSSARY.md「信」), and what comes of it: the prompt put
together from what is read beforehand (`LetterMaterial`), as the content prototype's second
version had it (`prototype/letters-content`), and the letter read back out of what the model
wrote (`parse_letter`).

The prompt opens with her character sheet, her birthday and her character facts in full; then
the producer, as turns tell of them; then how she speaks to the producer in the tier the
letter is written in (nothing in trust, nor where affinity is off), what there is between
them (the day they first talked, how many turns they have had, told as background alone,
and her own memories of the producer), their latest messages across every conversation, the
letters she wrote them before, not to be repeated, and how to write this one, on its
occasions, that day. Last, as the user's words, that she is to write it.

The model writes one JSON object: a salutation, three to five paragraphs, each in Japanese
with its Chinese, and where each thing between them came from. The sources only hold the
model to what happened; they are not kept. Delivery cues in the Chinese are taken out here;
those in the Japanese are kept, for reading it aloud, and taken out wherever it is shown
(`shown`)."""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Literal

from eidolon.affinity import Tier, affinity_prompt
from eidolon.characters import Character
from eidolon.delivery_cues import without_written_cues
from eidolon.llm import ChatMessage
from eidolon.producer import ProducerProfile, producer_prompt
from eidolon.today import always_known

Occasion = Literal[
    "close", "intimate", "complete", "her_birthday", "producer_birthday", "anniversary"
]
"""What she writes a letter on: her affinity first reaching close, first reaching intimate,
and her being complete (GLOSSARY.md「成就」); her birthday, the producer's, and the day they
first talked come round, 100 days on and every year after."""

OCCASIONS: tuple[Occasion, ...] = (
    "intimate", "close", "complete", "her_birthday", "producer_birthday", "anniversary"
)
"""Every occasion, in the order a letter of several names them."""

_OCCASIONS: dict[Occasion, str] = {
    "close": "你对制作人的感情，第一次比平时更近了一步：更信赖他，更想把心里话告诉他。"
    "你自己察觉到了这份变化，想借这封信告诉他。",
    "intimate": "你对制作人的感情，第一次到了这样的程度：他对你来说已经是非常特别、可以依靠的人。"
    "你想把平时说不出口的心意写下来。",
    "complete": "你和制作人之间的往来已经很多很多了：聊过很多、打过很多电话、收到过他的礼物、"
    "一起完成过工作。你想回头看看这一路，写信谢谢他。",
    "her_birthday": "今天是你的生日。制作人一直陪在你身边，你想在自己生日这天写信，谢谢他的陪伴。",
    "producer_birthday": "今天是制作人的生日。你想在这一天给他写一封信，祝他生日快乐。",
    "anniversary": "今天是你们认识{since}的日子（从你们第一次说话那天算起）。"
    "你想回头看看你们是怎么开始的，写信纪念这一天。",
}

_RECALLED: dict[Occasion, str] = {
    "close": "第一次和他更近了一步",
    "intimate": "他第一次成了特别的人",
    "complete": "回头看这一路",
    "her_birthday": "你自己的生日",
    "producer_birthday": "他的生日",
    "anniversary": "认识的纪念日",
}
"""Each occasion as she recalls a letter written on it."""

ANNIVERSARY_DAYS = 100
"""How many days after they first talked their first anniversary is; then every year."""

WRITE = "（请写这封信。）"

SHORTER = "（正文太长了。请把正文缩短到日语合计 280 字以内，其余照同样的规矩，重新输出整个 JSON 对象。）"

_RULES = """# 写信
你要亲手给制作人写一封信。{occasion}
今天是 {date}。

- 用日语写，这是你亲笔写的信：用你平时的自称、口癖和对制作人的叫法，像你本人写的，不像客套的贺卡。每段附简体中文翻译。
- 抬头一行，按你平时对制作人的叫法写，例如「プロデューサーさんへ」。
- 正文 3 到 5 段，日语合计 200 到 280 字，最多不能超过 300 字；宁短勿长。不写署名，信末会附你的签名。
- 信里提到的、你和这位制作人之间的具体事情，只能来自上面「你们之间的事」和你们的对话记录；你在原作里和制作人的经历也可以写。没有出处的事不要编，宁可写得朴素一点。
- 不要报数字（聊了多少、通了多少次电话），不提好感度、档位、成就这类词。
- 正文里可以在句子前加英文的语气提示，用方括号括起来，例如 [softly]、[smiling]、[pause]，只用于朗读，少用；中文翻译里不要带语气提示。
只输出一个 JSON 对象，不要别的文字：
{{"salutation": "抬头", "paragraphs": [{{"ja": "日语正文", "zh": "中文翻译"}}], "sources": ["每一处具体事情的出处，中文，一条一句：出自哪条记忆/哪段对话/原作哪段"]}}"""


@dataclass(frozen=True)
class Said:
    """A message between them, as she reads it back: the day it was said where the producer
    is, whether she said it, and its words, without delivery cues."""

    day: date
    by_her: bool
    text: str


@dataclass(frozen=True)
class Paragraph:
    """A paragraph of a letter: in Japanese, delivery cues and all, and in Chinese."""

    ja: str
    zh: str


@dataclass(frozen=True)
class Written:
    """A letter as she wrote it: the salutation and the paragraphs, delivery cues and all
    in the Japanese."""

    salutation: str
    paragraphs: tuple[Paragraph, ...]

    @property
    def length(self) -> int:
        """How long the body is: the characters of its Japanese without delivery cues, but
        for spaces."""
        return sum(len("".join(shown(p.ja).split())) for p in self.paragraphs)


@dataclass(frozen=True)
class Earlier:
    """A letter she wrote the producer before: the day, on what, and what it says."""

    day: date
    occasions: tuple[Occasion, ...]
    written: Written


@dataclass(frozen=True)
class LetterMaterial:
    """What she writes a letter with, read beforehand."""

    character: Character
    profile: ProducerProfile
    tier: Tier | None
    """The tier she writes in; None where affinity is off."""
    first_day: date | None
    """The day they first talked, where the producer is; None if never."""
    turns: int
    memories: Sequence[str]
    """Her own memories of the producer, the earliest first."""
    said: Sequence[Said]
    """Their latest messages, across every conversation, the earliest first."""
    earlier: Sequence[Earlier]
    """The letters she wrote the producer before, the earliest first."""
    occasions: Sequence[Occasion]
    day: date
    """The day she writes it, where the producer is."""


def shown(text: str) -> str:
    """`text` of a letter as it is shown: without its delivery cues."""
    return without_written_cues(text)


def letter_prompt(material: LetterMaterial) -> list[ChatMessage]:
    """The prompt she writes the letter on."""
    character = material.character
    facts = "\n\n".join(f.text for f in character.facts)
    opening = [*always_known(character, None), *([f"# 你的经历\n{facts}"] if facts else [])]
    context = [
        *(affinity_prompt(material.tier, None) if material.tier is not None else []),
        _between(material),
        _said(material.said),
        *([_earlier(material.earlier)] if material.earlier else []),
        _RULES.format(occasion=_occasion(material), date=_date(material.day)),
    ]
    return [
        ChatMessage("system", "\n\n".join(opening)),
        ChatMessage("system", producer_prompt(material.profile)),
        ChatMessage("system", "\n\n".join(context)),
        ChatMessage("user", WRITE),
    ]


def shorter_prompt(prompt: Sequence[ChatMessage], written: str) -> list[ChatMessage]:
    """The prompt she rewrites a letter too long on: `prompt`, what she `written`, and that
    it is too long."""
    return [*prompt, ChatMessage("assistant", written), ChatMessage("user", SHORTER)]


def parse_letter(text: str) -> Written | None:
    """The letter the model wrote in `text`, without the delivery cues of its Chinese; None if
    there is none: no JSON object, or one without a salutation or a paragraph."""
    try:
        found = json.loads(text[text.index("{") : text.rindex("}") + 1])
    except ValueError:
        return None
    if not isinstance(found, dict):
        return None
    salutation, paragraphs = found.get("salutation"), found.get("paragraphs")
    if not isinstance(salutation, str) or not shown(salutation) or not isinstance(paragraphs, list):
        return None
    kept = []
    for p in paragraphs:
        if not isinstance(p, dict):
            return None
        ja, zh = p.get("ja"), p.get("zh")
        if not isinstance(ja, str) or not isinstance(zh, str) or not shown(ja) or not shown(zh):
            return None
        kept.append(Paragraph(ja.strip(), shown(zh)))
    if not kept:
        return None
    return Written(salutation.strip(), tuple(kept))


def _occasion(material: LetterMaterial) -> str:
    since = _since(material.first_day, material.day)
    told = [_OCCASIONS[o].format(since=since) for o in material.occasions]
    if len(told) == 1:
        return told[0]
    each = "\n".join(f"- {t}" for t in told)
    return f"这次有几件事在同一天：\n{each}\n把这几件事都写进这封信里。"


def _since(first_day: date | None, day: date) -> str:
    """How long they have known each other on `day`, as she counts it: 100 days within the
    first year, else the years, a letter put off to the next day counted as on its own."""
    years = 0 if first_day is None else (day - first_day).days // 365
    if years == 0:
        return f"满 {ANNIVERSARY_DAYS} 天"
    return "满一年" if years == 1 else f"满 {years} 年"


def _between(material: LetterMaterial) -> str:
    lines = []
    if material.first_day is not None:
        lines.append(
            f"- 你们第一次说话是 {_date(material.first_day)}；一共聊过 {material.turns} 个回合"
            "（只当背景，不要写进信里）。"
        )
    lines += [f"- 记忆：{m}" for m in material.memories]
    return "# 你们之间的事\n" + ("\n".join(lines) or "（没有）")


def _said(said: Sequence[Said]) -> str:
    lines = [f"[{_date(s.day)}] {'你' if s.by_her else '制作人'}：{s.text}" for s in said]
    return "# 你们最近的对话记录（按时间）\n" + ("\n".join(lines) or "（没有）")


def _earlier(earlier: Sequence[Earlier]) -> str:
    letters = []
    for each in earlier:
        on = "、".join(_RECALLED[o] for o in each.occasions)
        body = "\n".join(shown(p.ja) for p in each.written.paragraphs)
        letters.append(f"## {_date(each.day)}（{on}）\n{shown(each.written.salutation)}\n{body}")
    return (
        "# 你以前写给这位制作人的信\n"
        "这次不要重复以前写过的事，开头和结尾也不要和以前一样。\n\n" + "\n\n".join(letters)
    )


def _date(day: date) -> str:
    return f"{day.year}年{day.month}月{day.day}日"
