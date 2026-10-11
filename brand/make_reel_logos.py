"""Generator rolek 1080x1920 w stylu „logotypy platform” dla synctech.pl.

Użycie:
    python3 brand/make_reel_logos.py spec.json posts/RRRR-MM-DD-reel.mp4

spec.json:
{
  "scenes": [
    {"type": "text", "dur": 3.0, "kicker": "SellAsist", "lines": ["Zamówienie", "z Allegro."], "accent": "I co dalej?"},
    {"type": "hub",  "dur": 4.5, "lines": ["Wszystko"], "accent": "w jednym panelu", "logos": ["allegro", "kaufland", "ebay", "dhl", "dpd"]},
    {"type": "logo", "dur": 3.0, "logo": "dhl", "lines": ["Etykieta"], "accent": "jednym klikiem", "sub": ["bez przepisywania adresu"]},
    {"type": "text", "dur": 3.5, "lines": ["Ty pakujesz."], "accent": "Reszta dzieje się sama.", "cta": "synctech.pl"}
  ]
}
Typy plansz: "text" (sam tekst), "hub" (SyncTech w środku, logotypy wskakują po kolei i łączą się liniami),
"logo" (duża karta z jednym logotypem + tekst). Bez emoji. Treść w środku kadru (górne ~250 px i dolne ~400 px
zasłania interfejs Instagrama). Zawsze jasne tło.
"""
import json
import math
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_post import T_MID, T_BRIGHT, font, fit  # noqa: E402
from make_post_logos import BG, INK, MUTED, logo_card, shadow_card  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS, M = 1080, 1920, 30, 90


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def back_ease(t):
    t = max(0.0, min(1.0, t))
    c = 1.7
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


def make_bg():
    img = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(img)
    for y in range(40, H, 48):
        for x in range(40, W, 48):
            d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(222, 234, 231))
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((560, -300, 1400, 520), fill=T_BRIGHT + (70,))
    ImageDraw.Draw(glow).ellipse((-400, 1500, 400, 2300), fill=T_BRIGHT + (50,))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(100)))
    logo = Image.open(os.path.join(HERE, "logo.png")).convert("RGBA")
    logo = logo.resize((360, int(logo.height * 360 / logo.width)), Image.LANCZOS)
    img.alpha_composite(logo, (M, 150))
    return img


def text_block(d, sc, y, a, lt):
    """Rysuje kicker/nagłówek/akcent/sub/cta od wysokości y z animacją wejścia. Zwraca y końca."""
    k = 0

    def alpha(i):
        return int(255 * ease((lt - 0.1 * i) / 0.4) * a)

    def dy(i):
        return int((1 - ease((lt - 0.1 * i) / 0.4)) * 50)

    if sc.get("kicker"):
        kf = font("Bold", 32)
        t = sc["kicker"].upper()
        tw = d.textlength(t, font=kf)
        al = alpha(k)
        d.rounded_rectangle((M, y + dy(k), M + tw + 44, y + dy(k) + 58), radius=29, fill=T_MID + (al,))
        d.text((M + 22, y + dy(k) + 11), t, font=kf, fill=(255, 255, 255, al))
        y += 90
        k += 1
    heads = list(sc.get("lines", [])) + ([sc["accent"]] if sc.get("accent") else [])
    if heads:
        size = min(fit(d, h, "ExtraBold", sc.get("size", 108), W - 2 * M) for h in heads)
        hf = font("ExtraBold", size)
        for i, h in enumerate(heads):
            acc = sc.get("accent") and i == len(heads) - 1
            d.text((M, y + dy(k)), h, font=hf, fill=(T_MID if acc else INK) + (alpha(k),))
            y += int(size * 1.15)
            k += 1
    if sc.get("sub"):
        y += 24
        sf = font("Medium", min(fit(d, s, "Medium", 46, W - 2 * M) for s in sc["sub"]))
        for s in sc["sub"]:
            d.text((M, y + dy(k)), s, font=sf, fill=MUTED + (alpha(k),))
            y += 62
        k += 1
    if sc.get("cta"):
        y += 50
        f = font("Bold", 54)
        tw = d.textlength(sc["cta"], font=f)
        al = alpha(k)
        d.rounded_rectangle((M, y + dy(k), M + tw + 84, y + dy(k) + 96), radius=48, fill=T_MID + (al,))
        d.text((M + 42, y + dy(k) + 16), sc["cta"], font=f, fill=(255, 255, 255, al))
        y += 96
    return y


def fade(lt, dur, last):
    if last:
        return 1.0
    return 1.0 - ease((lt - (dur - 0.3)) / 0.3) if lt > dur - 0.3 else 1.0


def scene_text(base, sc, lt, dur, last):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    heads = len(sc.get("lines", [])) + (1 if sc.get("accent") else 0)
    est = heads * 125 + (90 if sc.get("kicker") else 0) + len(sc.get("sub", [])) * 62 + (150 if sc.get("cta") else 0)
    text_block(d, sc, max(420, (H - est) // 2 - 80), fade(lt, dur, last), lt)
    return Image.alpha_composite(base, layer)


def scene_hub(base, sc, lt, dur, last):
    a = fade(lt, dur, last)
    img = base.copy()
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    text_block(d, sc, 400, a, lt)
    img = Image.alpha_composite(img, layer)
    logos = sc.get("logos", [])[:6]
    n = len(logos)
    cx, cy, rx, ry = W // 2, 1080, 330, 300
    pts = [(cx + rx * math.cos(-math.pi / 2 + i * 2 * math.pi / n), cy + ry * math.sin(-math.pi / 2 + i * 2 * math.pi / n)) for i in range(n)]
    hub_p = back_ease(lt / 0.5)
    stage = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stage)
    for i, (x, y) in enumerate(pts):
        t0 = 0.5 + i * 0.35
        p = ease((lt - t0 - 0.25) / 0.4)  # linia rysuje się po wejściu karty
        if p > 0:
            ex, ey = cx + (x - cx) * p, cy + (y - cy) * p
            sd.line((cx, cy, ex, ey), fill=T_MID, width=6)
            if p >= 1:
                pulse = (lt * 0.9 + i * 0.2) % 1.0
                mx, my = cx + (x - cx) * pulse, cy + (y - cy) * pulse
                sd.ellipse((mx - 11, my - 11, mx + 11, my + 11), fill=T_BRIGHT)
    r = int(150 * hub_p)
    if r > 4:
        shadow_card(stage, (cx - r, cy - r, cx + r, cy + r), radius=r, blur=30, alpha=55)
        ImageDraw.Draw(stage).ellipse((cx - r, cy - r, cx + r, cy + r), outline=T_BRIGHT, width=6)
        mark = Image.open(os.path.join(HERE, "logo.png")).convert("RGBA")
        mark = mark.crop((0, 0, mark.height, mark.height)).resize((max(1, r), max(1, r)), Image.LANCZOS)
        stage.alpha_composite(mark, (cx - r // 2, cy - r // 2))
    for i, (name, (x, y)) in enumerate(zip(logos, pts)):
        p = back_ease((lt - 0.5 - i * 0.35) / 0.45)
        if p <= 0.02:
            continue
        card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        logo_card(card, name, x, y, int(260 * p), int(150 * p))
        stage.alpha_composite(card)
    if a < 1:
        stage.putalpha(stage.getchannel("A").point(lambda v: int(v * a)))
    return Image.alpha_composite(img, stage)


def scene_logo(base, sc, lt, dur, last):
    a = fade(lt, dur, last)
    img = base.copy()
    stage = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    p = back_ease(lt / 0.55)
    if p > 0.02:
        logo_card(stage, sc["logo"], W // 2, 640, int(560 * p), int(320 * p), radius=48)
    d = ImageDraw.Draw(stage)
    text_block(d, sc, 900, 1.0, lt - 0.25)
    if a < 1:
        stage.putalpha(stage.getchannel("A").point(lambda v: int(v * a)))
    return Image.alpha_composite(img, stage)


def render(spec, out):
    scenes = spec["scenes"]
    total = sum(s["dur"] for s in scenes)
    base = make_bg()
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
           "-shortest", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-profile:v", "high", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "128k", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    fn = {"text": scene_text, "hub": scene_hub, "logo": scene_logo}
    for fi in range(int(total * FPS)):
        t = fi / FPS
        acc, idx = 0.0, 0
        while idx < len(scenes) - 1 and t >= acc + scenes[idx]["dur"]:
            acc += scenes[idx]["dur"]
            idx += 1
        sc = scenes[idx]
        frame = fn[sc.get("type", "text")](base, sc, t - acc, sc["dur"], idx == len(scenes) - 1)
        d = ImageDraw.Draw(frame)
        d.rounded_rectangle((M, 1480, W - M, 1486), radius=3, fill=(214, 228, 225))
        d.rounded_rectangle((M, 1480, M + int((W - 2 * M) * t / total), 1486), radius=3, fill=T_MID)
        proc.stdin.write(frame.convert("RGB").tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit("ffmpeg failed")


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        render(json.load(f), sys.argv[2])
    print("ok", sys.argv[2])
