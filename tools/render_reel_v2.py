"""クロのリール v2（伸びているリールの型に寄せた版）1080x1920

v1 との違い
- 1フレーム目から大きなタイトルが見えている（黒い画面・フェードインで始めない）
- 冒頭2秒で2カット（フック → 切り返し）、以降も2〜3秒ごとに場面が変わる
- 画面上部にタイトルを固定表示＋進行バー（最後まで見たくなる）
- 項目は「番号・見出し・具体例（入力→変換のタイピング演出など）」の大きなカード
- クロは右下から顔を出し、吹き出しでひとこと
- 文字はすべてインスタのUIに隠れない範囲（上250px〜下1500px）に収める

使い方:
  python3 tools/render_reel_v2.py posts/YYYY-MM-DD/reel_v2.json posts/YYYY-MM-DD/

JSON:
{
 "title": ["上に固定する", "タイトル2行"],
 "scenes": [
   {"type":"hook", "dur":1.0, "big":["ハッシュタグ", "毎回打ってない？"], "kuro":"surprised"},
   {"type":"hook", "dur":1.2, "big":["2文字で", "全部出せます"], "em":1, "kuro":"point", "bubble":"ほんとに"},
   {"type":"item", "dur":2.8, "n":"1", "head":"いつものハッシュタグ", "from":"はっ", "to":"#飲食店経営 #個人店経営…", "note":"5つ打つのが2文字に", "kuro":"phone_think"},
   {"type":"end", "dur":3.0, "big":["保存して", "今夜1つだけ登録"], "sub":"同じことしてる人に送ってあげて", "kuro":"ok", "bubble":"またね"}
 ]
}
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
KURO = os.path.join(ROOT, "assets", "kuro")
W, H, FPS = 1080, 1920, 30
BLACK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
BG = (13, 15, 20); CARD = (28, 31, 40); GOLD = (214, 160, 74); EM = (242, 196, 109)
WHITE = (246, 243, 236); GRAY = (176, 170, 160); INK = (20, 22, 30)

_f = {}
def font(p, s):
    if (p, s) not in _f:
        _f[(p, s)] = ImageFont.truetype(p, s, index=0)
    return _f[(p, s)]

def ease(t): t = max(0., min(1., t)); return 1 - (1 - t) ** 3
def back(t):
    t = max(0., min(1., t)); c = 1.7
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2

def fit(d, text, path, size, maxw):
    while size > 30 and d.textlength(text, font=font(path, size)) > maxw:
        size -= 2
    return font(path, size)

def background():
    yy, xx = np.mgrid[0:H, 0:W]
    g1 = np.clip(1 - np.sqrt((xx - W * .85) ** 2 + (yy - H * .15) ** 2) / 820, 0, 1) ** 2
    g2 = np.clip(1 - np.sqrt((xx - W * .2) ** 2 + (yy - H * .9) ** 2) / 900, 0, 1) ** 2
    arr = np.zeros((H, W, 3))
    for c in range(3):
        arr[..., c] = BG[c] + (GOLD[c] - BG[c]) * (0.20 * g1 + 0.12 * g2)
    return Image.fromarray(arr.astype("uint8")).convert("RGBA")

_k = {}
def kuro(name, h):
    if (name, h) not in _k:
        im = Image.open(os.path.join(KURO, name + ".png")).convert("RGBA")
        _k[(name, h)] = im.resize((int(im.width * h / im.height), h), Image.LANCZOS)
    return _k[(name, h)]

def ctext(d, y, s, f, fill, a=255, x0=0, x1=W):
    w = d.textlength(s, font=f); d.text((x0 + (x1 - x0 - w) / 2, y), s, font=f, fill=fill + (a,))

def header(L, title, prog):
    d = ImageDraw.Draw(L)
    d.text((70, 150), "クロ｜バー店長のAI参謀", font=font(BOLD, 32), fill=GOLD + (255,))
    y = 205
    d.rounded_rectangle((50, y, W - 50, y + 64 * len(title) + 44), radius=28, fill=GOLD + (255,))
    for i, s in enumerate(title):
        ctext(d, y + 18 + i * 64, s, fit(d, s, BLACK, 54, W - 160), INK)
    by = y + 64 * len(title) + 66
    d.rounded_rectangle((50, by, W - 50, by + 12), radius=6, fill=(60, 62, 72, 255))
    d.rounded_rectangle((50, by, 50 + int((W - 100) * prog), by + 12), radius=6, fill=EM + (255,))
    return by + 60

def bubble(L, text, lt, x, y):
    a = back((lt - 0.25) / 0.3)
    if a <= 0 or not text: return
    f = font(BLACK, 44); tw = ImageDraw.Draw(L).textlength(text, font=f)
    bw, bh = int(tw + 70), 100
    B = Image.new("RGBA", (bw + 10, bh + 50), (0, 0, 0, 0)); d = ImageDraw.Draw(B)
    d.rounded_rectangle((0, 0, bw, bh), radius=50, fill=(252, 250, 244, 255))
    d.polygon([(bw * .62, bh - 4), (bw * .8, bh + 44), (bw * .45, bh - 4)], fill=(252, 250, 244, 255))
    d.text((35, 22), text, font=f, fill=INK + (255,))
    s = max(.01, a)
    B = B.resize((max(1, int(B.width * s)), max(1, int(B.height * s))), Image.LANCZOS)
    L.alpha_composite(B, (int(x - B.width * .8), int(y - B.height)))

def draw_kuro(im, L, sc, lt, t, small):
    h = 900 if small else 1050
    ci = kuro(sc["kuro"], h)
    pop = back(lt / 0.35)
    bob = math.sin(t * 2.4) * 7
    x = W - ci.width + 150 if small else W - ci.width + 60
    y = int(H - h * 0.62 + (1 - pop) * 260 + bob) if small else int(H - h * 0.70 + (1 - pop) * 260 + bob)
    im.alpha_composite(ci, (x, y))
    bubble(L, sc.get("bubble", ""), lt, x + ci.width * 0.30, y + 60)

def big_lines(d, lines, y, em_idx, lt, size=118, punch=False):
    for i, s in enumerate(lines):
        f = fit(d, s, BLACK, size, W - 120)
        col = EM if i == em_idx else WHITE
        if punch:
            a = 255
        else:
            a = 255
        # 太いフチで読みやすく
        w = d.textlength(s, font=f); x = (W - w) / 2
        d.text((x, y), s, font=f, fill=col + (a,), stroke_width=8, stroke_fill=BG + (255,))
        if i == em_idx:
            d.rectangle((x, y + f.size + 14, x + w, y + f.size + 26), fill=GOLD + (200,))
        y += f.size + 46
    return y

def scene_layer(sc, lt, top):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    typ = sc["type"]
    if typ == "hook":
        big_lines(d, sc["big"], top + 120, sc.get("em", -1), lt)
    elif typ == "item":
        y = top + 40
        # 番号バッジ
        d.ellipse((70, y, 210, y + 140), fill=GOLD + (255,))
        ctext(d, y + 18, sc["n"], font(BLACK, 92), INK, x0=70, x1=210)
        f = fit(d, sc["head"], BLACK, 84, W - 320)
        d.text((240, y + 22), sc["head"], font=f, fill=WHITE + (255,))
        y += 200
        # 入力→変換カード
        d.rounded_rectangle((60, y, W - 60, y + 360), radius=36, fill=CARD + (245,), outline=(70, 72, 84, 255), width=3)
        d.text((100, y + 34), sc.get("from_label", "打つのは"), font=font(BOLD, 36), fill=GRAY + (255,))
        src = sc["from"]; n = max(1, min(len(src), int(len(src) * ease(lt / 0.5)) + (1 if lt > 0.05 else 0)))
        typed = src[:n]
        d.rounded_rectangle((100, y + 90, 100 + max(160, d.textlength(src, font=font(BLACK, 78)) + 60), y + 200), radius=20, fill=(48, 51, 62, 255))
        d.text((130, y + 100), typed, font=font(BLACK, 78), fill=WHITE + (255,))
        if int(lt * 3) % 2 == 0 and lt < 0.8:
            cx = 130 + d.textlength(typed, font=font(BLACK, 78)) + 6
            d.rectangle((cx, y + 112, cx + 6, y + 186), fill=EM + (255,))
        a = ease((lt - 0.65) / 0.3)
        if a > 0:
            d.text((100, y + 222), "→", font=font(BLACK, 64), fill=GOLD + (int(255 * a),))
            f2 = fit(d, sc["to"], BLACK, 62, W - 300)
            d.text((180, y + 226 + int(20 * (1 - a))), sc["to"], font=f2, fill=EM + (int(255 * a),))
        y += 400
        a = ease((lt - 1.0) / 0.3)
        if a > 0 and sc.get("note"):
            f3 = fit(d, sc["note"], BOLD, 50, W - 140)
            d.text((80, y + int(16 * (1 - a))), "✓ " + sc["note"], font=f3, fill=WHITE + (int(255 * a),))
    elif typ == "end":
        y = big_lines(d, sc["big"], top + 100, len(sc["big"]) - 1, lt, size=104)
        a = ease((lt - 0.5) / 0.3)
        if sc.get("sub") and a > 0:
            f = fit(d, sc["sub"], BOLD, 48, W - 200)
            w = d.textlength(sc["sub"], font=f)
            d.rounded_rectangle(((W - w) / 2 - 40, y + 20, (W + w) / 2 + 40, y + 120), radius=50, outline=GOLD + (int(255 * a),), width=4)
            ctext(d, y + 42, sc["sub"], f, EM, int(255 * a))
    return L

def frame(bg, spec, sc, lt, t, total):
    im = bg.copy()
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    top = header(L, spec["title"], t / total)
    draw_kuro(im, L, sc, lt, t, small=(sc["type"] == "item"))
    S = scene_layer(sc, lt, top)
    # 切り替えのパンチズーム（カット感）
    if lt < 0.12:
        s = 1.06 - 0.5 * lt
        S2 = S.resize((int(W * s), int(H * s)), Image.BILINEAR)
        S = S2.crop(((S2.width - W) // 2, (S2.height - H) // 2, (S2.width - W) // 2 + W, (S2.height - H) // 2 + H))
    im.alpha_composite(S); im.alpha_composite(L)
    return im

def main(spec_path, outdir, name="reel_v2"):
    spec = json.load(open(spec_path, encoding="utf-8"))
    sc_list = spec["scenes"]; os.makedirs(outdir, exist_ok=True)
    starts, t0 = [], 0.
    for s in sc_list: starts.append(t0); t0 += float(s["dur"])
    total = t0; bg = background()
    silent = os.path.join(outdir, "_s.mp4"); out = os.path.join(outdir, name + ".mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium",
                          "-crf", "20", "-movflags", "+faststart", silent], stdin=subprocess.PIPE)
    for fr in range(int(total * FPS)):
        t = fr / FPS
        i = max(k for k, s0 in enumerate(starts) if s0 <= t)
        p.stdin.write(frame(bg, spec, sc_list[i], t - starts[i], t, total).convert("RGB").tobytes())
    p.stdin.close(); p.wait()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                    "-shortest", "-c:v", "copy", "-c:a", "aac", out], check=True)
    os.remove(silent)
    frame(bg, spec, sc_list[0], 0.5, 0.5, total).convert("RGB").save(os.path.join(outdir, name + "_cover.jpg"), quality=90)
    print(out, f"{total:.1f}s")

if __name__ == "__main__":
    main(*sys.argv[1:])
