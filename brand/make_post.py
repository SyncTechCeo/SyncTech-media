"""Generator grafik 1080x1350 do postów synctech.pl.

Użycie:
    python3 brand/make_post.py spec.json posts/RRRR-MM-DD.jpg

spec.json:
{
  "headline": ["Twój sklep", "może działać"],   # 1-3 linie, krótkie (max ~13 znaków na linię)
  "accent": "sam.",                              # ostatnia linia w kolorze marki (opcjonalnie)
  "sub": ["Zamówienia, stany i faktury", "synchronizują się automatycznie."],  # 0-3 linie
  "chips": ["BaseLinker", "ShopGold", "Shopify"],  # 0-4 krótkie tagi
  "variant": "light"                             # "light" lub "dark"
}
"""
import glob
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1350

T_DARK = (37, 77, 72)
T_MID = (64, 130, 118)
T_LIGHT = (81, 160, 147)
T_BRIGHT = (106, 211, 192)

THEMES = {
    "light": dict(bg=(246, 250, 249), ink=(16, 32, 29), muted=(88, 108, 104),
                  accent=T_MID, tile_alpha=60, chip_fill=(255, 255, 255), chip_text=T_DARK),
    "dark": dict(bg=(14, 28, 26), ink=(240, 246, 244), muted=(160, 185, 180),
                 accent=T_BRIGHT, tile_alpha=70, chip_fill=(20, 40, 37), chip_text=(230, 240, 238)),
}


def font(style, size):
    c = glob.glob(f"/usr/share/fonts/**/Inter*{style}*.[to]tf", recursive=True)
    c = [x for x in c if "Italic" not in x and "Display" not in x]
    if not c:
        c = glob.glob("/usr/share/fonts/**/DejaVuSans-Bold.ttf", recursive=True)
    return ImageFont.truetype(sorted(c, key=len)[0], size)


def fit(d, text, style, size, max_w):
    while size > 40 and d.textlength(text, font=font(style, size)) > max_w:
        size -= 4
    return size


def render(spec, out):
    th = THEMES[spec.get("variant", "light")]
    img = Image.new("RGBA", (W, H), th["bg"] + (255,))

    grid = [[T_DARK, T_MID, T_LIGHT], [T_MID, T_BRIGHT, T_LIGHT], [T_LIGHT, T_MID, T_DARK]]
    s, gap, ox, oy = 170, 20, 620, -60
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for r in range(3):
        for c in range(3):
            x, y = ox + c * (s + gap), oy + r * (s + gap)
            ld.rounded_rectangle((x, y, x + s, y + s), radius=30, fill=grid[r][c] + (th["tile_alpha"],))
    img = Image.alpha_composite(img, layer)

    logo = Image.open(os.path.join(HERE, "logo.png")).convert("RGBA")
    if spec.get("variant") == "dark":
        # rozjaśnij ciemne litery "sync" na ciemnym tle
        px = logo.load()
        for yy in range(logo.height):
            for xx in range(logo.width):
                r, g, b, a = px[xx, yy]
                if a and max(r, g, b) < 60:
                    px[xx, yy] = (240, 246, 244, a)
    lw = 380
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    img.alpha_composite(logo, (80, 88))
    d = ImageDraw.Draw(img)

    lines = list(spec.get("headline", []))
    accent = spec.get("accent")
    all_lines = lines + ([accent] if accent else [])
    size = min(fit(d, ln, "ExtraBold", 108, W - 160) for ln in all_lines)
    hf = font("ExtraBold", size)
    step = int(size * 1.15)
    y = 1100 - 170 - step * len(all_lines) - (50 * len(spec.get("sub", [])))
    y = max(y, 470)
    for ln in lines:
        d.text((80, y), ln, font=hf, fill=th["ink"])
        y += step
    if accent:
        d.text((80, y), accent, font=hf, fill=th["accent"])
        y += step

    sf = font("Medium", 38)
    y += 30
    for ln in spec.get("sub", []):
        d.text((80, y), ln, font=sf, fill=th["muted"])
        y += 50

    chips = spec.get("chips", [])[:4]
    if chips:
        cf = font("SemiBold", 30)
        x, cy = 80, 1150
        for t in chips:
            tw = d.textlength(t, font=cf)
            if x + tw + 48 > W - 60:
                break
            d.rounded_rectangle((x, cy, x + tw + 48, cy + 62), radius=31, outline=T_MID, width=2, fill=th["chip_fill"])
            d.text((x + 24, cy + 13), t, font=cf, fill=th["chip_text"])
            x += tw + 48 + 16

    d.text((80, 1250), "synctech.pl", font=font("SemiBold", 30), fill=th["accent"])
    img.convert("RGB").save(out, quality=93)


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        render(json.load(f), sys.argv[2])
    print("ok", sys.argv[2])
