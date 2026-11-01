"""Builds index.html: the GPT Image prototype beside the old NovelAI pictures."""

import html
from pathlib import Path

HERE = Path(__file__).parent

COMMON_PHOTO = (
    "A casual smartphone snapshot that a young woman living in Tokyo just posted to her "
    "social media feed. …… Shot handheld at eye level, natural unposed framing, realistic "
    "phone-camera look. No added text, captions or watermarks."
)
COMMON_ANIME = (
    "A Japanese anime-style illustration of a casual snapshot …, drawn like the background "
    "art of a modern slice-of-life anime: clean lines, soft painterly colors, gentle light. "
    "…… Seen at eye level, as if she took it herself. No added text, captions or watermarks."
)

SCENES = [
    {
        "id": "S1", "title": "风景 · 商店街傍晚", "ask": "横 1536×1024",
        "body": "Place: 下北沢南口商店街（世田谷区）— 下北沢站南口延伸出去、挂着拱门招牌的商店街，旧衣店、拉面店、杂货店。<br>"
                "What: 傍晚回家路上经过的商店街。<br>Details: street, dusk, sidewalk, power lines, vending machine, storefronts.<br>"
                "When: November, around 5 pm, clear.",
        "nai": [("K1-1", "旧图 K1-1：no humans, scenery, japan, outdoors, street, dusk, sidewalk, power lines, vending machine（现行写法）"),
                ("A1-1", "旧图 A1-1：street, dusk, city lights（没加 japan，画成俯瞰）")],
        "notes": "实拍风：拱门上的字写对了，有古着店、ラーメン招牌、Asahi 自动售货机、电线，像手机随手拍。"
                 "二次元风：基本还是照片，只是调色更浓，没画成动画。",
    },
    {
        "id": "S2", "title": "风景 · 神社", "ask": "横 1536×1024",
        "body": "Place: 日枝神社（千代田区）— 赤坂的神社，有朱红的鸟居隧道和电动扶梯。<br>What: 日枝神社的千本鸟居。<br>"
                "Details: torii, stone steps, trees.<br>When: November, around 10 am, clear.",
        "nai": [("J1-1", "旧图 J1-1：scenery, japan, street, dusk（NovelAI 没有神社的无人旧图，这里放街景作画风参照）")],
        "notes": "两张都认得出是日枝神社山王稲荷那段鸟居石阶，带红叶（11 月）。二次元风偏插画写实，远处有高楼。",
    },
    {
        "id": "S3", "title": "风景 · 圣地（乞田川樱花）", "ask": "横 1536×1024",
        "body": "Place: 乞田川（多摩市）— 流经多摩市的小河，两岸约 3 公里种了 500 多棵樱花，春天沿河是一条花廊。<br>"
                "What: 乞田川边的樱花开了。<br>Details: river, cherry blossoms, bridge, path.<br>When: early April, around 11 am, clear.",
        "nai": [("J2-1", "旧图 J2-1：scenery, japan, park, autumn leaves, bench, tree")],
        "notes": "实拍风：郊外小河、护岸、低层公寓，很像多摩一带。二次元风：这张是六组里最像动画背景的。",
    },
    {
        "id": "S4", "title": "风景 · 雨天喫茶店", "ask": "横 1536×1024",
        "body": "Place: 七つ森（杉並区）— 高圆寺的老喫茶店，昏暗的木头和旧物，招牌是蛋包饭和甜点。<br>"
                "What: 下雨天躲进老喫茶店，窗外一直在下雨。<br>Details: window, rain, coffee cup, wooden table.<br>When: June, around 3 pm, rain.",
        "nai": [],
        "notes": "实拍风返回了竖图（要的是横图）。二次元风：把地点介绍里的「蛋包饭和甜点」也画上了桌，看着像写实 CG。"
                 "地点介绍会被当成画面内容，拼提示词时要标明它只是背景信息。",
    },
    {
        "id": "S5", "title": "食物 · 奶油苏打", "ask": "竖 1024×1536",
        "body": "Place: さぼうる（千代田区）— 神保町的山小屋风喫茶店，门口立着图腾柱，招牌是奶油苏打。<br>"
                "What: さぼうる的奶油苏打。<br>Details: cream soda, on table.<br>When: August, around 2 pm, clear.",
        "nai": [("B1", "旧图 B1：food focus, parfait, cafe, on table, depth of field")],
        "notes": "两张都画出了图腾柱和山小屋风内装，真去过的人能认出来。二次元风返回接近方图（1312×1199）。",
    },
    {
        "id": "S6", "title": "物品 · 窗边的花（没有地点）", "ask": "竖 1024×1536",
        "body": "Place: none given (at home).<br>What: 收到的花插在宿舍窗边。<br>"
                "Details: flowers, vase, windowsill, sunlight.<br>When: November, around 9 am, clear.",
        "nai": [("B2", "旧图 B2：object focus, flower, vase, window, sunlight, depth of field")],
        "notes": "实拍风很像手机照片。二次元风是柔光插画，六组里第二像动画；也返回接近方图。",
    },
]


def img(src: str, cap: str) -> str:
    return (f'<figure><a href="{src}" target="_blank"><img src="{src}" loading="lazy"></a>'
            f"<figcaption>{cap}</figcaption></figure>")


def main() -> None:
    rows = []
    for s in SCENES:
        cells = [img(f"{s['id']}-photo.webp", "GPT · 实拍风"), img(f"{s['id']}-anime.webp", "GPT · 二次元风")]
        cells += [img(f"nai/{n}.webp", html.escape(c)) for n, c in s["nai"]]
        rows.append(
            f"<section><h2>{s['id']} {s['title']} <small>请求 {s['ask']}</small></h2>"
            f"<p class=prompt>{s['body']}</p><p class=notes>{s['notes']}</p>"
            f"<div class=grid>{''.join(cells)}</div></section>"
        )
    page = f"""<!doctype html><html lang=zh-CN><meta charset=utf-8>
<title>配图原型：GPT Image vs NovelAI</title>
<style>
body{{font:15px/1.6 system-ui,'Microsoft YaHei',sans-serif;max-width:1400px;margin:2rem auto;padding:0 1rem;background:#fafafa;color:#222}}
h1{{font-size:1.4rem}} h2{{font-size:1.1rem;margin:2.5rem 0 .3rem}} small{{color:#888;font-weight:normal}}
.prompt{{font:13px/1.5 ui-monospace,Consolas,monospace;background:#f0f0f0;padding:.6rem .8rem;border-radius:6px}}
.notes{{background:#fff8e1;padding:.5rem .8rem;border-radius:6px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px;align-items:start}}
figure{{margin:0}} img{{width:100%;border-radius:6px;display:block}} figcaption{{font-size:13px;color:#555;margin-top:4px}}
.intro{{background:#fff;padding:1rem;border-radius:8px;border:1px solid #ddd}}
</style>
<h1>朋友圈无人配图：GPT Image（gpt-image-2，medium）vs NovelAI 旧图</h1>
<div class=intro>
<p>每个场景用同样的内容出两张：实拍风和二次元风。提示词照服务器以后会拼的写法：地点原名和所在区、地点介绍、她写的 note、景物 tag、季节、时段、天气。两种风格只差开头和结尾的风格句：</p>
<p class=prompt>实拍风：{html.escape(COMMON_PHOTO)}<br><br>二次元风：{html.escape(COMMON_ANIME)}</p>
<p>NovelAI 旧图来自 <code>prototype/moments-images</code>（V5 Curated，画风插槽 <code>0.7::artist:rella::</code>），场景不完全一样，只用来对比画风。点图看原图。</p>
</div>
{''.join(rows)}
</html>"""
    (HERE / "index.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    main()
