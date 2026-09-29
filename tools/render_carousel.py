import json, sys, asyncio
from playwright.async_api import async_playwright

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1350px;background:#0d0f14;color:#f2efe9;
 font-family:'Noto Sans CJK JP','Noto Sans CJK SC',sans-serif;position:relative;overflow:hidden}
.glow{position:absolute;right:-220px;top:-220px;width:640px;height:640px;border-radius:50%;
 background:radial-gradient(circle,rgba(214,160,74,.22),rgba(214,160,74,0) 65%)}
.wrap{position:absolute;inset:0;padding:110px 96px 120px;display:flex;flex-direction:column}
.tag{font-size:30px;letter-spacing:.08em;color:#d6a04a;font-weight:700;margin-bottom:44px}
.num{font-size:34px;color:#d6a04a;font-weight:900;margin-bottom:28px;letter-spacing:.06em}
h1{font-size:96px;line-height:1.28;font-weight:900;letter-spacing:.01em}
h2{font-size:74px;line-height:1.3;font-weight:900;margin-bottom:48px}
p{font-size:44px;line-height:1.75;line-break:strict;color:#d9d4cb;font-weight:500}
.em{color:#f2c46d}
.box{margin-top:auto;border:2px solid rgba(214,160,74,.55);border-radius:18px;padding:34px 40px;
 font-size:38px;line-height:1.6;color:#f2efe9;background:rgba(214,160,74,.07)}
.foot{position:absolute;left:96px;right:96px;bottom:56px;display:flex;justify-content:space-between;
 font-size:26px;color:#8d877c;letter-spacing:.05em}
.cta{font-size:64px;font-weight:900;line-height:1.35;margin-bottom:40px}
.line{display:inline-block;background:#06c755;color:#fff;font-weight:900;font-size:50px;
 padding:26px 44px;border-radius:999px;margin-top:20px}
"""

def page(inner, i, n):
    return f"""<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<div class='glow'></div><div class='wrap'>{inner}</div>
<div class='foot'><span>クロ｜バー店長のAI参謀</span><span>{i}/{n}</span></div></body></html>"""

async def main(spec_path, outdir):
    slides = json.load(open(spec_path))
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width':1080,'height':1350})
        for i, s in enumerate(slides, 1):
            await pg.set_content(page(s, i, len(slides)))
            await pg.wait_for_timeout(200)
            await pg.screenshot(path=f"{outdir}/slide{i:02d}.jpg", type='jpeg', quality=92)
        await b.close()

asyncio.run(main(sys.argv[1], sys.argv[2]))
