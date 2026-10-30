"""PROTOTYPE (票 04：原型：配图实测), throwaway.

Generates the must-test matrix of research/moments-novelai-composition §7 through the
image service in the repo's .env, prompts built per §6.2, and writes a gallery.

    uv run python -I run_matrix.py <repo>/.env <out dir> [case id ...]
"""

import asyncio
import html
import io
import json
import os
import sys
import time
import zipfile
from pathlib import Path

import httpx
from PIL import Image

from eidolon.photo_prompt import NEGATIVE_PROMPT, QUALITY_TAGS, WORK_TAG

Q = ", ".join(QUALITY_TAGS)
NEG = NEGATIVE_PROMPT
NEG_NO_HUMANS = NEG + ", 1girl, 1boy, people"
NEG_CANDID = NEG + ", looking at viewer"

CHARS = {
    "mano": ("sakuragi mano", "brown hair, medium hair, brown eyes"),
    "hiori": ("kazano hiori", "black hair, long hair, ponytail, blue eyes"),
    "amana": ("osaki amana", "brown hair, long hair, swept bangs, yellow eyes"),
    "tenka": ("osaki tenka", "brown hair, long hair, hair between eyes, yellow eyes"),
    "meguru": ("hachimiya meguru", "blonde hair, long hair, ahoge, low twintails, blue eyes"),
}

SEED_A, SEED_B, SEED_C, SEED_D = 1234567, 7654321, 2468013, 1357911


def join(*parts: str) -> str:
    return ", ".join(p for p in parts if p)


def single(who: str, style: str, framing: str, place: str, outfit: str, action: str) -> str:
    tag, look = CHARS[who]
    return join("1girl, solo", tag, WORK_TAG, style, look, framing, place, outfit, action)


def cases(style: str) -> list[dict]:
    group_e1 = join(
        "2girls", WORK_TAG, style, "side-by-side, upper body, cafe, indoors, casual, smile",
        "looking at viewer", Q,
    )
    group_3 = join(
        "3girls", WORK_TAG, style, "group picture, upper body, cafe, indoors, casual, smile",
        "looking at viewer", Q,
    )
    return [
        dict(id="A1-1", kind="scenery 风景", look="rella 下有没有把人画回来；像不像随手拍的风景",
             pos=join("no humans, scenery", style, "street, dusk", "city lights", Q),
             neg=NEG_NO_HUMANS, seed=SEED_A),
        dict(id="A1-2", kind="scenery 风景", look="同上（海边）",
             pos=join("no humans, scenery", style, "beach, blue sky", "ocean", Q),
             neg=NEG_NO_HUMANS, seed=SEED_A),
        dict(id="A2", kind="scenery 实拍风", look="实拍风能不能当朋友圈风景；和 A1-1 比哪个好（同种子）",
             pos=join("background dataset, no humans, scenery", "street, dusk", "city lights", Q),
             neg=NEG_NO_HUMANS, seed=SEED_A),
        dict(id="B1", kind="food 食物", look="会不会变成白底写实食物图；有没有场景",
             pos=join("no humans, food focus", style, "parfait", "cafe, on table", "depth of field", Q),
             neg=NEG_NO_HUMANS, seed=SEED_A),
        dict(id="B2", kind="object 物品", look="同上（桌上的花）",
             pos=join("no humans, object focus", style, "flower, vase", "window, sunlight", "depth of field", Q),
             neg=NEG_NO_HUMANS, seed=SEED_A),
        dict(id="C1", kind="candid 抓拍", look="像不像抓拍；看不看镜头（真乃，咖啡店，在吃东西往下看）",
             pos=join(single("mano", style, "upper body", "cafe, indoors", "casual", "eating, looking down"),
                      "depth of field", Q),
             neg=NEG_CANDID, seed=SEED_B),
        dict(id="C2", kind="candid 抓拍", look="只靠服务器默认补的 looking away 够不够（走路，没写视线）",
             pos=join(single("mano", style, "cowboy shot", "street, outdoors", "casual", "walking, looking away"),
                      "depth of field", Q),
             neg=NEG_CANDID, seed=SEED_C),
        dict(id="C3", kind="posed 摆拍", look="和 C2 同种子同场景，抓拍和摆拍拉开差别没有",
             pos=join(single("mano", style, "cowboy shot", "street, outdoors", "casual", "walking, looking at viewer"), Q),
             neg=NEG, seed=SEED_C),
        dict(id="E1-1", kind="group 合照他拍", look="人数对不对；真乃和灯织认不认得出；串没串色（AI's Choice）",
             pos=group_e1, neg=NEG, seed=SEED_A, chars=["mano", "hiori"]),
        dict(id="E1-2", kind="group 合照他拍", look="同上，第二个种子",
             pos=group_e1, neg=NEG, seed=SEED_D, chars=["mano", "hiori"]),
        dict(id="E2", kind="group 合照他拍 + 坐标", look="和 E1-1 同种子，加坐标 (0.3,0.5)/(0.7,0.5) 有没有好处",
             pos=group_e1, neg=NEG, seed=SEED_A, chars=["mano", "hiori"], coords=[(0.3, 0.5), (0.7, 0.5)]),
        dict(id="E3", kind="group 合照自拍", look="两人自拍会不会多出手或手机",
             pos=join("2girls", WORK_TAG, style, "selfie, upper body, park, outdoors, casual, heads together, smile",
                      "looking at viewer", Q),
             neg=NEG, seed=SEED_B, chars=["mano", "hiori"]),
        dict(id="E4-1", kind="group 双胞胎", look="最难：甘奈和甜花会不会长成一个人、认混（AI's Choice）",
             pos=group_e1, neg=NEG, seed=SEED_A, chars=["amana", "tenka"]),
        dict(id="E4-2", kind="group 双胞胎", look="同上，第二个种子",
             pos=group_e1, neg=NEG, seed=SEED_D, chars=["amana", "tenka"]),
        # 选测
        dict(id="C1b", kind="candid 抓拍重试", look="C1 原样换种子：看镜头是偶发还是稳定",
             pos=join(single("mano", style, "upper body", "cafe, indoors", "casual", "eating, looking down"),
                      "depth of field", Q),
             neg=NEG_CANDID, seed=SEED_D),
        dict(id="C1c", kind="candid 抓拍重试", look="C1 同种子，eating 换 drinking：是不是动作的问题",
             pos=join(single("mano", style, "upper body", "cafe, indoors", "casual", "drinking, looking down"),
                      "depth of field", Q),
             neg=NEG_CANDID, seed=SEED_B),
        dict(id="F1", kind="group 三人他拍", look="真乃+灯织+めぐる：人数和认人（AI's Choice）",
             pos=group_3, neg=NEG, seed=SEED_A, chars=["mano", "hiori", "meguru"]),
        dict(id="F2", kind="group 三人 + 坐标", look="F1 加坐标 0.2/0.5/0.8",
             pos=group_3, neg=NEG, seed=SEED_A, chars=["mano", "hiori", "meguru"],
             coords=[(0.2, 0.5), (0.5, 0.5), (0.8, 0.5)]),
        dict(id="H1", kind="group 横图", look="E1-1 改 1216×832：合照横图是不是更好",
             pos=group_e1, neg=NEG, seed=SEED_A, chars=["mano", "hiori"], size=(1216, 832)),
        dict(id="H1s", kind="group 方图", look="E1-1 改 1024×1024",
             pos=group_e1, neg=NEG, seed=SEED_A, chars=["mano", "hiori"], size=(1024, 1024)),
        dict(id="H2", kind="scenery 横图", look="A1-1 改 1216×832：风景横图是不是更好",
             pos=join("no humans, scenery", style, "street, dusk", "city lights", Q),
             neg=NEG_NO_HUMANS, seed=SEED_A, size=(1216, 832)),
        dict(id="H2s", kind="scenery 方图", look="A1-1 改 1024×1024",
             pos=join("no humans, scenery", style, "street, dusk", "city lights", Q),
             neg=NEG_NO_HUMANS, seed=SEED_A, size=(1024, 1024)),
    ]


def body(model: str, case: dict) -> dict:
    width, height = case.get("size", (832, 1216))
    coords = case.get("coords")
    names = case.get("chars", [])
    centers = coords or [(0, 0)] * len(names)
    char_pos = [
        {"char_caption": join("girl", *CHARS[n]), "centers": [{"x": x, "y": y}]}
        for n, (x, y) in zip(names, centers)
    ]
    char_neg = [{"char_caption": "", "centers": c["centers"]} for c in char_pos]
    return {
        "input": case["pos"],
        "model": model,
        "action": "generate",
        "parameters": {
            "params_version": 3, "width": width, "height": height, "scale": 7,
            "sampler": "k_euler_ancestral", "steps": 23, "n_samples": 1, "ucPreset": 3,
            "qualityToggle": False, "seed": case["seed"], "noise_schedule": "karras",
            "cfg_rescale": 0, "negative_prompt": case["neg"],
            "v4_prompt": {
                "caption": {"base_caption": case["pos"], "char_captions": char_pos},
                "use_coords": bool(coords), "use_order": True,
            },
            "v4_negative_prompt": {
                "caption": {"base_caption": case["neg"], "char_captions": char_neg},
                "legacy_uc": False,
            },
        },
    }


def env(path: Path) -> dict[str, str]:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("NOVELAI_") and "=" in line:
            k, _, v = line.partition("=")
            out[k] = v.strip()
    return out


def metadata_chars(png: bytes) -> str:
    """What the returned PNG says about the character boxes it was made with."""
    with Image.open(io.BytesIO(png)) as im:
        comment = im.info.get("Comment")
    if not comment:
        return "PNG 里没有 Comment 元数据"
    try:
        meta = json.loads(comment)
    except ValueError:
        return "Comment 不是 JSON"
    caps = (meta.get("v4_prompt") or {}).get("caption", {}).get("char_captions")
    if caps is None:
        return "元数据里没有 v4_prompt"
    return f"元数据 char_captions {len(caps)} 个；use_coords={meta.get('v4_prompt', {}).get('use_coords')}"


async def run(case: dict, settings: dict, client: httpx.AsyncClient, out: Path) -> dict:
    started = time.monotonic()
    res = await client.post(
        f"{settings['NOVELAI_BASE_URL']}/ai/generate-image",
        json=body(settings.get("NOVELAI_MODEL") or "nai-diffusion-5-curated", case),
        headers={"Authorization": f"Bearer {settings['NOVELAI_API_KEY']}"},
    )
    took = time.monotonic() - started
    if res.status_code >= 400:
        return {**case, "error": f"{res.status_code}: {res.text[:300]}", "took": took}
    with zipfile.ZipFile(io.BytesIO(res.content)) as z:
        png = z.read(z.namelist()[0])
    (out / "png" / f"{case['id']}.png").write_bytes(png)
    with Image.open(io.BytesIO(png)) as im:
        size = im.size
        im.convert("RGB").save(out / f"{case['id']}.webp", "WEBP", quality=85)
    return {**case, "size": size, "meta": metadata_chars(png), "took": took}


def gallery(results: list[dict], out: Path) -> None:
    cards = []
    for r in results:
        chars = "、".join(r.get("chars", [])) or "—"
        status = (f"<p class=err>失败：{html.escape(r['error'])}</p>" if "error" in r
                  else f"<img src='{r['id']}.webp' loading=lazy>")
        cards.append(f"""<figure>
<h2>{r['id']} · {html.escape(r['kind'])}</h2>
<p class=look>{html.escape(r['look'])}</p>
{status}
<details><summary>提示词</summary>
<p><b>正面</b> {html.escape(r['pos'])}</p>
<p><b>角色框</b> {html.escape(chars)}；<b>种子</b> {r['seed']}；{html.escape(str(r.get('meta', '')))}；{r.get('size')}；{r.get('took', 0):.0f} 秒</p>
<p><b>负面</b> {html.escape(r['neg'])}</p>
</details></figure>""")
    (out / "index.html").write_text(f"""<!doctype html><meta charset=utf-8>
<title>原型：配图实测（PROTOTYPE）</title>
<style>
body{{font:14px/1.5 system-ui,sans-serif;margin:24px;background:#f6f5f2;color:#222}}
main{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px}}
figure{{margin:0;background:#fff;border-radius:10px;padding:12px;box-shadow:0 1px 3px #0002}}
h2{{font-size:15px;margin:0 0 4px}} .look{{color:#555;margin:0 0 8px}}
img{{width:100%;border-radius:6px;display:block}} details{{font-size:12px;color:#444}}
.err{{color:#b00}}
</style>
<h1>原型：配图实测 · {len(results)} 张</h1>
<p>PROTOTYPE，用完即弃。V5 Curated，除 H 组外 832×1216，画风插槽见提示词。</p>
<main>{''.join(cards)}</main>""", encoding="utf-8")


async def main() -> None:
    settings = env(Path(sys.argv[1]))
    out = Path(sys.argv[2])
    (out / "png").mkdir(parents=True, exist_ok=True)
    only = set(sys.argv[3:])
    todo = [c for c in cases(settings.get("NOVELAI_STYLE", "")) if not only or c["id"] in only]
    done_file = out / "results.json"
    done = {r["id"]: r for r in json.loads(done_file.read_text(encoding="utf-8"))} if done_file.exists() else {}
    async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=10)) as client:
        for case in todo:
            r = await run(case, settings, client, out)
            done[case["id"]] = r
            print(case["id"], r.get("error") or f"{r['size']} {r['meta']} {r['took']:.0f}s", flush=True)
            done_file.write_text(json.dumps(list(done.values()), ensure_ascii=False, indent=1), encoding="utf-8")
    order = [c["id"] for c in cases(settings.get("NOVELAI_STYLE", ""))]
    gallery(sorted(done.values(), key=lambda r: order.index(r["id"])), out)


asyncio.run(main())
