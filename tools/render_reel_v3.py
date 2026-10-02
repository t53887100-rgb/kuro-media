"""クロのリール v3（明るい背景・強調演出・効果音つき）1080x1920

v2 からの変更
- 背景を明るい生成り色に（黒背景は怪しく見えるという意見を反映）
- 強調シーン（hook / end）は「バーン」演出：文字が大きく叩きつけられる＋画面の揺れ＋フラッシュ＋集中線＋黄色マーカー
- 効果音を自動で付ける（すべてプログラムで合成した音なので著作権の心配なし）
    ・強調シーン：ドン（低音のインパクト）
    ・場面の切り替え：シュッ（風切り音）
    ・入力のタイピング：カチカチ
    ・答えが出る瞬間：チーン
    ・吹き出し：ポン
- narration.wav（同じフォルダ）があれば、効果音と一緒にミックスする

使い方:
  python3 tools/render_reel_v3.py posts/xxx/reel.json posts/xxx/ [出力名]
JSON は v2 と同じ形式（title / scenes[type=hook|item|end]）
"""
import json, math, os, random, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
KURO = os.path.join(ROOT, "assets", "kuro")
W, H, FPS, SR = 1080, 1920, 30, 44100
BLACK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
PAPER = (250, 246, 236); PAPER2 = (243, 234, 214)
NAVY = (26, 30, 52); YELLOW = (255, 210, 60); RED = (226, 64, 44)
CARD = (255, 255, 255); GRAY = (110, 108, 104); GOLD = (196, 140, 50)

_f = {}
def font(p, s):
    if (p, s) not in _f: _f[(p, s)] = ImageFont.truetype(p, s, index=0)
    return _f[(p, s)]
def ease(t): t = max(0., min(1., t)); return 1 - (1 - t) ** 3
def back(t):
    t = max(0., min(1., t)); c = 1.9
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2
def fit(d, s, p, size, maxw):
    while size > 30 and d.textlength(s, font=font(p, size)) > maxw: size -= 2
    return font(p, size)

def background():
    yy, xx = np.mgrid[0:H, 0:W]
    g = np.clip(1 - np.sqrt((xx - W * .5) ** 2 + (yy - H * .45) ** 2) / 1300, 0, 1)
    arr = np.zeros((H, W, 3))
    for c in range(3): arr[..., c] = PAPER2[c] + (PAPER[c] - PAPER2[c]) * g
    im = Image.fromarray(arr.astype("uint8")).convert("RGBA")
    d = ImageDraw.Draw(im)
    for x in range(0, W, 54):  # うすい方眼（ノートっぽさ）
        d.line((x, 0, x, H), fill=(232, 222, 200, 255), width=1)
    for y in range(0, H, 54):
        d.line((0, y, W, y), fill=(232, 222, 200, 255), width=1)
    return im

_k = {}
def kuro(name, h):
    if (name, h) not in _k:
        im = Image.open(os.path.join(KURO, name + ".png")).convert("RGBA")
        _k[(name, h)] = im.resize((int(im.width * h / im.height), h), Image.LANCZOS)
    return _k[(name, h)]

def ctext(d, y, s, f, fill, a=255, x0=0, x1=W, **kw):
    w = d.textlength(s, font=f); d.text((x0 + (x1 - x0 - w) / 2, y), s, font=f, fill=fill + (a,), **kw)

def header(L, title, prog):
    d = ImageDraw.Draw(L)
    d.text((70, 150), "クロ｜バー店長のAI参謀", font=font(BOLD, 32), fill=NAVY + (255,))
    y = 205; hh = 64 * len(title) + 44
    d.rounded_rectangle((50, y + 8, W - 42, y + hh + 8), radius=28, fill=(0, 0, 0, 40))
    d.rounded_rectangle((50, y, W - 50, y + hh), radius=28, fill=NAVY + (255,))
    for i, s in enumerate(title):
        ctext(d, y + 18 + i * 64, s, fit(d, s, BLACK, 54, W - 160), (255, 255, 255))
    by = y + hh + 22
    d.rounded_rectangle((50, by, W - 50, by + 12), radius=6, fill=(220, 210, 188, 255))
    d.rounded_rectangle((50, by, 50 + int((W - 100) * prog), by + 12), radius=6, fill=RED + (255,))
    return by + 60

def burst(L, lt, cy):
    a = 1 - ease(lt / 0.6)
    if a <= 0: return
    d = ImageDraw.Draw(L); rnd = random.Random(int(lt * 20))
    for i in range(46):
        ang = i / 46 * 2 * math.pi + rnd.uniform(-.04, .04)
        r0 = 380 + rnd.uniform(0, 120); r1 = 1300
        w = rnd.choice([3, 5, 8])
        d.line((W / 2 + r0 * math.cos(ang), cy + r0 * math.sin(ang), W / 2 + r1 * math.cos(ang), cy + r1 * math.sin(ang)),
               fill=NAVY + (int(70 * a),), width=w)

def bubble(L, text, lt, x, y):
    a = back((lt - 0.25) / 0.3)
    if a <= 0 or not text: return
    f = font(BLACK, 44); tw = ImageDraw.Draw(L).textlength(text, font=f)
    bw, bh = int(tw + 70), 100
    B = Image.new("RGBA", (bw + 10, bh + 50), (0, 0, 0, 0)); d = ImageDraw.Draw(B)
    d.rounded_rectangle((0, 0, bw, bh), radius=50, fill=(255, 255, 255, 255), outline=NAVY + (255,), width=5)
    d.polygon([(bw * .62, bh - 3), (bw * .8, bh + 44), (bw * .45, bh - 3)], fill=(255, 255, 255, 255), outline=NAVY + (255,))
    d.rectangle((bw * .46, bh - 6, bw * .61, bh - 1), fill=(255, 255, 255, 255))
    d.text((35, 22), text, font=f, fill=NAVY + (255,))
    s = max(.01, a)
    B = B.resize((max(1, int(B.width * s)), max(1, int(B.height * s))), Image.LANCZOS)
    L.alpha_composite(B, (int(x - B.width * .8), int(y - B.height)))

def draw_kuro(im, L, sc, lt, t, small):
    h = 900 if small else 1000
    ci = kuro(sc["kuro"], h); pop = back(lt / 0.35); bob = math.sin(t * 2.4) * 7
    x = W - ci.width + (150 if small else 70)
    y = int(H - h * (0.62 if small else 0.68) + (1 - pop) * 260 + bob)
    sh = Image.new("RGBA", ci.size, (0, 0, 0, 0)); sh.putalpha(ci.getchannel("A").point(lambda v: v // 5))
    im.alpha_composite(sh, (x + 14, y + 14)); im.alpha_composite(ci, (x, y))
    bubble(L, sc.get("bubble", ""), lt, x + ci.width * 0.30, y + 60)

def slam_lines(L, lines, y, em, lt, size=124):
    """文字を叩きつける：1行ずつ大きく→ドン"""
    d0 = ImageDraw.Draw(L)
    for i, s in enumerate(lines):
        st = lt - i * 0.16
        if st <= 0: y += size + 50; continue
        f = fit(d0, s, BLACK, size, W - 110)
        T = Image.new("RGBA", (W, f.size + 70), (0, 0, 0, 0)); d = ImageDraw.Draw(T)
        w = d.textlength(s, font=f); x = (W - w) / 2
        if i == em:
            mw = ease(st / 0.25)
            d.rectangle((x - 14, f.size * .55, x - 14 + (w + 28) * mw, f.size + 26), fill=YELLOW + (255,))
        col = RED if i == em else NAVY
        d.text((x, 8), s, font=f, fill=col + (255,), stroke_width=7, stroke_fill=(255, 255, 255, 255))
        sc = 1 + 0.9 * (1 - back(st / 0.2))
        if sc != 1:
            T = T.resize((max(1, int(T.width * sc)), max(1, int(T.height * sc))), Image.BILINEAR)
        a = min(1, st / 0.06)
        if a < 1: T.putalpha(T.getchannel("A").point(lambda v: int(v * a)))
        L.alpha_composite(T, (int((W - T.width) / 2), int(y - (T.height - f.size - 70) / 2)))
        y += f.size + 50
    return y

def scene_layer(sc, lt, top):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    typ = sc["type"]
    if typ == "hook":
        burst(L, lt, top + 330)
        slam_lines(L, sc["big"], top + 150, sc.get("em", len(sc["big"]) - 1), lt)
    elif typ == "item":
        y = top + 30
        p = back(lt / 0.25)
        d.ellipse((70, y, 210, y + 140), fill=NAVY + (255,))
        ctext(d, y + 18, sc["n"], font(BLACK, int(92 * max(.3, p))), YELLOW, x0=70, x1=210)
        f = fit(d, sc["head"], BLACK, 82, W - 320)
        d.text((240, y + 24), sc["head"], font=f, fill=NAVY + (255,))
        y += 200
        d.rounded_rectangle((68, y + 12, W - 52, y + 372), radius=36, fill=(0, 0, 0, 35))
        d.rounded_rectangle((60, y, W - 60, y + 360), radius=36, fill=CARD + (255,), outline=NAVY + (255,), width=4)
        d.text((100, y + 30), sc.get("from_label", "打つのは"), font=font(BOLD, 36), fill=GRAY + (255,))
        src = sc["from"]; n = max(1, min(len(src), int(len(src) * ease(lt / 0.5)) + 1))
        fb = font(BLACK, 78)
        d.rounded_rectangle((100, y + 86, 100 + max(160, d.textlength(src, font=fb) + 60), y + 196), radius=20, fill=(238, 236, 230, 255))
        d.text((130, y + 96), src[:n], font=fb, fill=NAVY + (255,))
        if int(lt * 3) % 2 == 0 and lt < 0.8:
            cx = 130 + d.textlength(src[:n], font=fb) + 6
            d.rectangle((cx, y + 108, cx + 6, y + 184), fill=RED + (255,))
        a = ease((lt - 0.65) / 0.2)
        if a > 0:
            f2 = fit(d, sc["to"], BLACK, 62, W - 300)
            tw = d.textlength(sc["to"], font=f2)
            d.rectangle((176, y + 262, 176 + (tw + 10) * a, y + 300), fill=YELLOW + (255,))
            d.text((100, y + 218), "→", font=font(BLACK, 64), fill=RED + (int(255 * a),))
            d.text((180, y + 222), sc["to"], font=f2, fill=NAVY + (int(255 * a),))
        y += 410
        a = ease((lt - 1.0) / 0.25)
        if a > 0 and sc.get("note"):
            f3 = fit(d, sc["note"], BLACK, 54, W - 160)
            d.text((80, y + int(16 * (1 - a))), "✓ " + sc["note"], font=f3, fill=RED + (int(255 * a),))
    elif typ == "end":
        burst(L, lt, top + 300)
        y = slam_lines(L, sc["big"], top + 110, len(sc["big"]) - 1, lt, size=110)
        a = ease((lt - 0.55) / 0.25)
        if sc.get("sub") and a > 0:
            f = fit(d, sc["sub"], BLACK, 48, W - 200); w = d.textlength(sc["sub"], font=f)
            d.rounded_rectangle(((W - w) / 2 - 40, y + 10, (W + w) / 2 + 40, y + 112), radius=52, fill=RED + (int(255 * a),))
            ctext(d, y + 32, sc["sub"], f, (255, 255, 255), int(255 * a))
    return L

def frame(bg, spec, sc, lt, t, total):
    im = bg.copy(); L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    top = header(L, spec["title"], t / total)
    draw_kuro(im, L, sc, lt, t, small=(sc["type"] == "item"))
    S = scene_layer(sc, lt, top)
    im.alpha_composite(S); im.alpha_composite(L)
    if sc["type"] in ("hook", "end"):
        # ドンの瞬間：画面の揺れとフラッシュ
        k = max(0., 1 - lt / 0.28)
        if k > 0:
            r = random.Random(int(t * FPS))
            dx, dy = int(r.uniform(-1, 1) * 22 * k), int(r.uniform(-1, 1) * 22 * k)
            im = Image.new("RGBA", (W, H), PAPER + (255,)).copy() if False else im.transform(im.size, Image.AFFINE, (1, 0, -dx, 0, 1, -dy), fillcolor=PAPER + (255,))
        fl = max(0., 1 - lt / 0.09)
        if fl > 0:
            im = Image.blend(im, Image.new("RGBA", (W, H), (255, 255, 255, 255)), 0.55 * fl)
    elif lt < 0.1:
        s = 1.05 - 0.5 * lt
        S2 = im.resize((int(W * s), int(H * s)), Image.BILINEAR)
        im = S2.crop(((S2.width - W) // 2, (S2.height - H) // 2, (S2.width - W) // 2 + W, (S2.height - H) // 2 + H))
    return im

# ---------- 効果音（合成） ----------
def env(n, a=0.002, r=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / r)
def sfx_don():
    n = int(SR * 0.7); t = np.arange(n) / SR
    f = 95 * np.exp(-t * 4) + 42
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .001, .22)
    s += np.random.randn(n) * env(n, .0005, .03) * 0.6
    return s * 0.95
def sfx_whoosh():
    n = int(SR * 0.28); x = np.random.randn(n)
    y = np.convolve(x, np.ones(18) / 18, "same")
    sh = np.sin(np.linspace(0, np.pi, n)) ** 2
    return y * sh * 0.9
def sfx_click():
    n = int(SR * 0.025); return np.random.randn(n) * env(n, .0003, .004) * 0.5
def sfx_ding():
    n = int(SR * 0.9); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 1318 * t) + .5 * np.sin(2 * np.pi * 2637 * t) + .25 * np.sin(2 * np.pi * 3951 * t)) * env(n, .002, .25) * 0.32
def sfx_pop():
    n = int(SR * 0.09); t = np.arange(n) / SR
    return np.sin(2 * np.pi * (500 + 2600 * t / 0.09) * t) * env(n, .001, .03) * 0.45

def build_audio(scenes, starts, total, path, narration=None):
    mix = np.zeros(int(SR * (total + 1)))
    def add(s, at, g=1.0):
        i = int(at * SR); e = min(len(mix), i + len(s)); mix[i:e] += s[:e - i] * g
    for k, (sc, s0) in enumerate(zip(scenes, starts)):
        if k > 0: add(sfx_whoosh(), max(0, s0 - 0.12), .5)
        if sc["type"] in ("hook", "end"):
            for i in range(len(sc["big"])): add(sfx_don(), s0 + 0.03 + i * 0.16, .9 if i == 0 else .6)
        if sc["type"] == "item":
            add(sfx_pop(), s0 + 0.02, .7)
            for j in range(len(sc["from"])): add(sfx_click(), s0 + 0.06 + j * 0.5 / max(1, len(sc["from"])))
            add(sfx_ding(), s0 + 0.66)
        if sc.get("bubble"): add(sfx_pop(), s0 + 0.3, .6)
    mix = mix[:int(SR * total)]
    if narration and os.path.exists(narration):
        with wave.open(narration) as w:
            nr = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float) / 32768
            if w.getnchannels() == 2: nr = nr[::2]
            if w.getframerate() != SR:
                nr = np.interp(np.arange(0, len(nr), w.getframerate() / SR), np.arange(len(nr)), nr)
        mix *= 0.55; m = min(len(mix), len(nr)); mix[:m] += nr[:m] * 0.95
    mix = np.clip(mix / max(1, np.abs(mix).max() / 0.95), -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())

def main(spec_path, outdir, name="reel_v3"):
    spec = json.load(open(spec_path, encoding="utf-8")); scs = spec["scenes"]; os.makedirs(outdir, exist_ok=True)
    starts, t0 = [], 0.
    for s in scs: starts.append(t0); t0 += float(s["dur"])
    total = t0; bg = background()
    silent = os.path.join(outdir, "_v.mp4"); aud = os.path.join(outdir, "_a.wav"); out = os.path.join(outdir, name + ".mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium",
                          "-crf", "20", silent], stdin=subprocess.PIPE)
    for fr in range(int(total * FPS)):
        t = fr / FPS; i = max(k for k, s0 in enumerate(starts) if s0 <= t)
        p.stdin.write(frame(bg, spec, scs[i], t - starts[i], t, total).convert("RGB").tobytes())
    p.stdin.close(); p.wait()
    build_audio(scs, starts, total, aud, os.path.join(outdir, "narration.wav"))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", aud, "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], check=True)
    os.remove(silent); os.remove(aud)
    frame(bg, spec, scs[0], 0.6, 0.6, total).convert("RGB").save(os.path.join(outdir, name + "_cover.jpg"), quality=90)
    print(out, f"{total:.1f}s")

if __name__ == "__main__":
    main(*sys.argv[1:])
