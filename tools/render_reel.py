"""クロのリール動画（1080x1920）を JSON から作る。

使い方:
  python3 tools/render_reel.py posts/YYYY-MM-DD/reel.json posts/YYYY-MM-DD/

reel.json の例:
{
  "scenes": [
    {"dur": 3.0, "kuro": "surprised", "lines": ["売上が止まった夜、", "最初に見直した3つ"], "bubble": "え、そこから？"},
    {"dur": 4.0, "kuro": "point", "kicker": "01", "lines": ["見つけてもらう場所"], "sub": "地図・写真・営業時間、止まってない？", "bubble": "まず“見える化”"},
    {"dur": 4.5, "kuro": "offer_hand", "lines": ["どこが詰まってるか", "無料チェックでわかる"], "sub": "プロフィールのリンクから", "cta": true, "bubble": "一緒に見ようか"}
  ]
}
kuro は assets/kuro/ のファイル名（拡張子なし）。bubble は省略可。
出力: reel.mp4（無音の音声トラック付き）と cover.jpg（1枚目の場面）。
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
KURO = os.path.join(ROOT, "assets", "kuro")
W, H, FPS = 1080, 1920, 30
BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
BG = (13, 15, 20); GOLD = (214, 160, 74); EM = (242, 196, 109)
WHITE = (242, 239, 233); GRAY = (170, 165, 156)

_fonts = {}
def font(path, size):
    if (path, size) not in _fonts:
        _fonts[(path, size)] = ImageFont.truetype(path, size, index=0)
    return _fonts[(path, size)]

def ease(t):
    t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3

def back(t):
    t = max(0.0, min(1.0, t)); c = 1.7
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2

def background():
    yy, xx = np.mgrid[0:H, 0:W]
    g = np.clip(1 - np.sqrt((xx - W * 0.5) ** 2 + (yy - H * 0.72) ** 2) / 900, 0, 1) ** 2
    arr = np.zeros((H, W, 3))
    for c, (b, t) in enumerate(zip(BG, (72, 54, 34))):
        arr[..., c] = b + (t - b) * g
    return Image.fromarray(arr.astype("uint8")).convert("RGBA")

_kuro = {}
def kuro(name, height):
    key = (name, height)
    if key not in _kuro:
        im = Image.open(os.path.join(KURO, name + ".png")).convert("RGBA")
        w = int(im.width * height / im.height)
        _kuro[key] = im.resize((w, height), Image.LANCZOS)
    return _kuro[key]

def center_text(d, y, text, f, fill, alpha=255):
    w = d.textlength(text, font=f)
    d.text(((W - w) / 2, y), text, font=f, fill=fill + (alpha,))

def fit(d, text, path, size, maxw=960):
    while size > 40 and d.textlength(text, font=font(path, size)) > maxw:
        size -= 4
    return font(path, size)

def text_layer(sc, lt):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    d.text((80, 230), "クロ｜バー店長のAI参謀", font=font(REG, 34), fill=GOLD + (255,))
    y = 330
    kick = sc.get("kicker", "")
    if kick:
        a = ease(lt / 0.3)
        center_text(d, y + int(20 * (1 - a)), kick, font(BOLD, 110), GOLD, int(255 * a)); y += 150
    lines = sc.get("lines", [])
    for i, ln in enumerate(lines):
        a = ease((lt - 0.15 - i * 0.15) / 0.35)
        f = fit(d, ln, BOLD, 92 if kick else 84)
        col = EM if (i == len(lines) - 1 and not kick) else WHITE
        center_text(d, y + int(40 * (1 - a)), ln, f, col, int(255 * a)); y += f.size + 30
    sub = sc.get("sub", "")
    if sub:
        a = ease((lt - 0.7) / 0.4)
        if sc.get("cta"):
            d.rounded_rectangle((150, y + 30, 930, y + 150), radius=60, outline=GOLD + (int(255 * a),), width=5)
            center_text(d, y + 55, sub, fit(d, sub, BOLD, 52, 740), EM, int(255 * a))
        else:
            center_text(d, y + 30, sub, fit(d, sub, REG, 44), GRAY, int(255 * a))
    return L

def bubble(L, text, lt, anchor):
    a = back((lt - 0.9) / 0.35)
    if a <= 0 or not text:
        return
    f = font(BOLD, 46); tw = ImageDraw.Draw(L).textlength(text, font=f)
    bw, bh = int(tw + 80), 110
    B = Image.new("RGBA", (bw + 40, bh + 60), (0, 0, 0, 0)); d = ImageDraw.Draw(B)
    d.rounded_rectangle((0, 0, bw, bh), radius=55, fill=(250, 248, 242, 255))
    d.polygon([(bw * 0.7, bh - 5), (bw * 0.85, bh + 50), (bw * 0.55, bh - 5)], fill=(250, 248, 242, 255))
    d.text((40, 24), text, font=f, fill=(20, 22, 32, 255))
    s = max(0.01, a)
    B = B.resize((max(1, int(B.width * s)), max(1, int(B.height * s))), Image.LANCZOS)
    x, y = anchor
    L.alpha_composite(B, (max(10, int(x - B.width * 0.85)), int(y - B.height)))

def frame(bg, sc, lt, t):
    im = bg.copy()
    e = ease(lt / 0.45); bob = math.sin(t * 2.2) * 8
    h = int(1120 * (0.94 + 0.06 * back(lt / 0.5)))
    ci = kuro(sc["kuro"], 1120)
    if h != 1120:
        ci = ci.resize((int(ci.width * h / 1120), h), Image.BILINEAR)
    if e < 1:
        ci = ci.copy(); ci.putalpha(ci.getchannel("A").point(lambda v: int(v * min(1, e * 1.4))))
    top = int(800 + (1 - e) * 260 + bob)
    im.alpha_composite(ci, (W // 2 - ci.width // 2, top + (1120 - h)))
    L = text_layer(sc, lt)
    bubble(L, sc.get("bubble", ""), lt, (500, top + 150))
    im.alpha_composite(L)
    return im

def main(spec_path, outdir):
    spec = json.load(open(spec_path, encoding="utf-8"))
    scenes = spec["scenes"]; os.makedirs(outdir, exist_ok=True)
    starts, t0 = [], 0.0
    for s in scenes:
        starts.append(t0); t0 += float(s["dur"])
    total = t0; bg = background()
    silent = os.path.join(outdir, "_silent.mp4"); out = os.path.join(outdir, "reel.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                          "-preset", "medium", "-crf", "20", "-movflags", "+faststart", silent], stdin=subprocess.PIPE)
    for fr in range(int(total * FPS)):
        t = fr / FPS
        i = max(k for k, s0 in enumerate(starts) if s0 <= t)
        sc = scenes[i]; lt = t - starts[i]
        im = frame(bg, sc, lt, t)
        rem = starts[i] + float(sc["dur"]) - t
        if rem < 0.15:
            im = Image.blend(Image.new("RGBA", (W, H), BG + (255,)), im, rem / 0.15)
        p.stdin.write(im.convert("RGB").tobytes())
    p.stdin.close(); p.wait()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-f", "lavfi", "-i",
                    "anullsrc=r=44100:cl=stereo", "-shortest", "-c:v", "copy", "-c:a", "aac", out], check=True)
    os.remove(silent)
    frame(bg, scenes[0], 1.6, 1.6).convert("RGB").save(os.path.join(outdir, "cover.jpg"), quality=90)
    print(out, f"{total:.1f}s")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
