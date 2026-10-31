# PROTOTYPE, throwaway: 信的内容原型（.scratch/letters 拷问后，2026-10-31）。
# 在线上后端容器里跑：读一位用户的真实数据，按场合让部署者的对话模型写信，把信和用到的材料打成 JSON 印到 stdout。
#   timeout 600 ssh vps 'cd ~/eidolon-sc && docker compose exec -T backend python - <user_id> <variant>' \
#     < backend/scripts/prototype_letters.py > E:/tmp/letters-proto/<variant>.json
# 不写库、不记用量。不合进 dev/main。

import asyncio
import json
import os
import sqlite3
import sys
from pathlib import Path

from eidolon.affinity import affinity_prompt, tier_of
from eidolon.characters import load_characters
from eidolon.llm import ChatMessage
from eidolon.llm.openai_compat import OpenAICompatLLM
from eidolon.producer import producer_prompt
from eidolon.store import read_profile
from eidolon.today import always_known

USER = sys.argv[1]
VARIANT = sys.argv[2] if len(sys.argv) > 2 else "base"

# (角色, 场合, 写信那天, 用哪一档的口吻；None 照她现在的档位)
CASES = [
    ("kaho", "intimate", "2026-11-02", "intimate"),
    ("kaho", "her_birthday", "2027-07-29", None),
    ("hazuki", "close", "2026-11-02", "close"),
    ("hazuki", "producer_birthday", "2027-02-25", None),
    ("mano", "close", "2026-11-02", "close"),
    ("mano", "anniversary_100", "2027-01-05", None),
    ("madoka", "close", "2026-11-02", "close"),
    ("mano", "complete", "2026-11-02", None),
]

OCCASIONS = {
    "close": "你对制作人的感情，第一次比平时更近了一步：更信赖他，更想把心里话告诉他。你自己察觉到了这份变化，想借这封信告诉他。",
    "intimate": "你对制作人的感情，第一次到了这样的程度：他对你来说已经是非常特别、可以依靠的人。你想把平时说不出口的心意写下来。",
    "complete": "你和制作人之间的往来已经很多很多了：聊过很多、打过很多电话、收到过他的礼物、一起完成过工作。你想回头看看这一路，写信谢谢他。",
    "producer_birthday": "今天是制作人的生日（按他那边的日期）。你写信祝他生日快乐。",
    "her_birthday": "今天是你自己的生日。你写信给制作人，谢谢他这段时间的陪伴。",
    "anniversary_100": "今天是你和这位制作人第一次说话后满 100 天。你写信纪念这一天。",
}

RULES = """# 写信
你要亲手给制作人写一封信。{occasion}
今天是 {date}。

- 用日语写，这是你亲笔写的信：用你平时的自称、口癖和对制作人的叫法，像你本人写的，不像客套的贺卡。每段附简体中文翻译。
- 抬头一行，按你平时对制作人的叫法写，例如「プロデューサーさんへ」。
- 正文 3 到 5 段，日语合计 200 到 280 字，最多不能超过 300 字；宁短勿长。不写署名，信末会附你的签名。
- 信里提到的、你和这位制作人之间的具体事情，只能来自下面「你们之间的事」和你们的对话记录；你在原作里和制作人的经历也可以写。没有出处的事不要编，宁可写得朴素一点。
- 不要报数字（聊了多少、通了多少次电话），不提好感度、档位、成就这类词。
- 正文里可以在句子前加英文的语气提示，用方括号括起来，例如 [softly]、[smiling]、[pause]，只用于朗读，少用；中文翻译里不要带语气提示。
{extra}
只输出一个 JSON 对象，不要别的文字：
{{"salutation": "抬头", "paragraphs": [{{"ja": "日语正文", "zh": "中文翻译"}}], "sources": ["每一处具体事情的出处，中文，一条一句：出自哪条记忆/哪段对话/原作哪段"]}}"""

EXTRAS = {
    "base": "",
    "v2": "",
    "grounded": "- 至少有一段写你们俩之间真实发生过的一件小事（来自记忆或对话记录），写具体：当时说了什么、你怎么想的。这是别人收不到的部分。",
}


async def main() -> None:
    db = sqlite3.connect("file:/data/eidolon.db?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    path = Path(os.environ.get("EIDOLON_CHARACTERS_PATH", "/app/characters/characters.toml"))
    characters = load_characters(path)
    profile = read_profile(db, USER)
    llm = OpenAICompatLLM(
        os.environ["CHAT_LLM_BASE_URL"], os.environ["CHAT_LLM_API_KEY"], os.environ["CHAT_LLM_MODEL"],
    )
    out = []
    written: dict[str, list[dict]] = {}
    for cid, occasion, date, tone in CASES:
        c = characters[cid]
        facts_file = path.parent / "facts" / f"{cid}.md"
        facts = facts_file.read_text(encoding="utf-8") if facts_file.exists() else ""
        value = db.execute(
            "select value from affinities where user_id=? and character_id=?", (USER, cid)
        ).fetchone()
        tier = tone or tier_of(value[0] if value else 50)
        memories = [r[0] for r in db.execute(
            "select text from memories where user_id=? and source_character_id=? and superseded_by is null"
            " order by created_at", (USER, cid))]
        rows = db.execute(
            "select m.role, m.text, m.ja, m.zh, m.created_at from messages m join conversations c"
            " on c.id=m.conversation_id where c.user_id=? and c.character_id=? order by m.created_at",
            (USER, cid)).fetchall()
        turns = sum(1 for r in rows if r["role"] == "user")
        first = rows[0]["created_at"][:10] if rows else None
        recent = rows[-60:]
        log = "\n".join(
            f"[{r['created_at'][:10]}] {'制作人' if r['role'] == 'user' else '你'}：{r['text'] or r['ja'] or ''}"
            for r in recent
        )
        between = [
            f"- 你们第一次说话是 {first}；一共聊过 {turns} 个回合（只当背景，不要写进信里）。",
            *(f"- 记忆：{m}" for m in memories),
        ]
        context = "\n\n".join([
            *affinity_prompt(tier, None),
            "# 你们之间的事\n" + "\n".join(between),
            "# 你们最近的对话记录（按时间）\n" + (log or "（没有）"),
            RULES.format(occasion=OCCASIONS[occasion], date=date, extra=EXTRAS[VARIANT]),
        ])
        prompt = [
            ChatMessage("system", "\n\n".join([*always_known(c, None), "# 你的经历\n" + facts])),
            ChatMessage("system", producer_prompt(profile)),
            ChatMessage("system", context),
            ChatMessage("user", "（请写这封信。）"),
        ]

        raw = ""
        async for item in llm.stream(prompt):
            if isinstance(item, str):
                raw += item
        try:
            letter = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
        except ValueError:
            letter = {"error": raw}
        written.setdefault(cid, []).append({"date": date, "occasion": occasion, "letter": letter})
        out.append({
            "character": cid, "name": c.name, "occasion": occasion, "date": date, "tier": tier,
            "memories": memories, "turns": turns, "first": first, "recent_count": len(recent),
            "letter": letter,
        })
        print(f"done {cid} {occasion}", file=sys.stderr)
    print(json.dumps({"variant": VARIANT, "model": os.environ["CHAT_LLM_MODEL"], "letters": out},
                     ensure_ascii=False))


asyncio.run(main())
