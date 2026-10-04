"""Generator rolek 1080x1920 (MP4, 30 fps) dla synctech.pl.

Użycie:
    python3 brand/make_reel.py spec.json posts/RRRR-MM-DD-reel.mp4

spec.json:
{
  "variant": "dark",                 # "dark" (domyślnie) lub "light"
  "scenes": [
    {"dur": 3.0, "lines": ["3 rzeczy,", "które Twój sklep"], "accent": "powinien robić sam"},
    {"dur": 3.0, "num": "1", "lines": ["Przenoszenie", "zamówień"], "sub": ["z wielu kanałów do", "jednego panelu"]},
    {"dur": 3.0, "lines": ["Ty sprzedajesz."], "accent": "Reszta dzieje się sama.", "cta": "synctech.pl"}
  ]
}
Bez emoji w tekście (font ich nie renderuje). Linie krótkie: max ~14 znaków nagłówka.
Treść trzymaj w środku kadru: górne ~250 px i dolne ~400 px zasłania interfejs Instagrama.
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_post import THEMES, T_DARK, T_MID, T_LIGHT, T_BRIGHT, font  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
MARGIN = 90


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def background(th, t, dark):
    img = Image.new("RGBA", (W, H), th["bg"] + (255,))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    grid = [[T_DARK, T_MID, T_LIGHT], [T_MID, T_BRIGHT, T_LIGHT], [T_LIGHT, T_MID, T_DARK]]
    s, gap = 200, 22
    drift = int(t * 6)  # wolny dryf kafelków
    ox, oy = 560 - drift, -40 + drift // 2
    for r in range(3):
        for c in range(3):
            x, y = ox + c * (s + gap), oy + r * (s + gap)
            ld.rounded_rectangle((x, y, x + s, y + s), radius=34, fill=grid[r][c] + (th["tile_alpha"],))
    ox2, oy2 = -260 + drift, 1500 - drift // 2
    for r in range(2):
        for c in range(2):
            x, y = ox2 + c * (s + gap), oy2 + r * (s + gap)
            ld.rounded_rectangle((x, y, x + s, y + s), radius=34, fill=grid[r + 1][c] + (th["tile_alpha"] // 2,))
    return Image.alpha_composite(img, layer)


def load_logo(dark):
    logo = Image.open(os.path.join(HERE, "logo.png")).convert("RGBA")
    if dark:
        px = logo.load()
        for yy in range(logo.height):
            for xx in range(logo.width):
                r, g, b, a = px[xx, yy]
                if a and max(r, g, b) < 60:
                    px[xx, yy] = (240, 246, 244, a)
    lw = 360
    return logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)


def fit_size(d, lines, style, size, max_w):
    while size > 48 and any(d.textlength(l, font=font(style, size)) > max_w for l in lines):
        size -= 4
    return size


def scene_items(d, sc, th):
    """Zwraca listę elementów (typ, tekst, font, kolor, y) z wyśrodkowanym blokiem."""
    items = []
    if sc.get("num"):
        items.append(("text", sc["num"], font("ExtraBold", 220), th["accent"], 230))
    heads = list(sc.get("lines", [])) + ([sc["accent"]] if sc.get("accent") else [])
    if heads:
        size = fit_size(d, heads, "ExtraBold", 112, W - 2 * MARGIN)
        hf = font("ExtraBold", size)
        for i, ln in enumerate(heads):
            is_acc = sc.get("accent") and i == len(heads) - 1
            items.append(("text", ln, hf, th["accent"] if is_acc else th["ink"], int(size * 1.18)))
    if sc.get("sub"):
        items.append(("gap", None, None, None, 30))
        sf = font("Medium", 46)
        for ln in sc["sub"]:
            items.append(("text", ln, sf, th["muted"], 62))
    if sc.get("cta"):
        items.append(("gap", None, None, None, 50))
        items.append(("cta", sc["cta"], font("Bold", 52), th["accent"], 110))
    total = sum(it[4] for it in items)
    y = max(330, (H - total) // 2 - 60)
    out = []
    for it in items:
        out.append(it[:4] + (y,))
        y += it[4]
    return out


def draw_scene(base, sc, th, lt, dur):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    items = scene_items(d, sc, th)
    fade_out = ease((lt - (dur - 0.35)) / 0.35) if lt > dur - 0.35 else 0.0
    k = 0
    for typ, txt, f, col, y in items:
        if typ == "gap":
            continue
        p = ease((lt - 0.12 * k) / 0.45)
        k += 1
        a = int(255 * p * (1 - fade_out))
        if a <= 0:
            continue
        dy = int((1 - p) * 60 - fade_out * 40)
        if typ == "cta":
            tw = d.textlength(txt, font=f)
            x0 = MARGIN
            d.rounded_rectangle((x0, y + dy, x0 + tw + 80, y + dy + 92), radius=46, fill=col + (a,))
            d.text((x0 + 40, y + dy + 16), txt, font=f, fill=th["bg"] + (a,))
        else:
            d.text((MARGIN, y + dy), txt, font=f, fill=col + (a,))
    return Image.alpha_composite(base, layer)


def render(spec, out):
    variant = spec.get("variant", "dark")
    th = THEMES[variant]
    logo = load_logo(variant == "dark")
    scenes = spec["scenes"]
    total = sum(s["dur"] for s in scenes)
    nframes = int(total * FPS)

    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
           "-shortest", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-profile:v", "high", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "128k", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    for fi in range(nframes):
        t = fi / FPS
        acc, idx = 0.0, 0
        while idx < len(scenes) - 1 and t >= acc + scenes[idx]["dur"]:
            acc += scenes[idx]["dur"]
            idx += 1
        sc, lt = scenes[idx], t - acc
        frame = background(th, t, variant == "dark")
        frame.alpha_composite(logo, (MARGIN, 150))
        # pasek postępu
        d = ImageDraw.Draw(frame)
        d.rounded_rectangle((MARGIN, 1440, W - MARGIN, 1446), radius=3, fill=th["muted"] + (60,))
        d.rounded_rectangle((MARGIN, 1440, MARGIN + int((W - 2 * MARGIN) * t / total), 1446), radius=3, fill=th["accent"])
        frame = draw_scene(frame, sc, th, lt, sc["dur"] if idx < len(scenes) - 1 else sc["dur"] + 1)
        proc.stdin.write(frame.convert("RGB").tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit("ffmpeg failed")


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        render(json.load(f), sys.argv[2])
    print("ok", sys.argv[2])
