"""Generator grafik 1080x1350 w stylu „logotypy platform” dla synctech.pl.

Użycie:
    python3 brand/make_post_logos.py spec.json posts/RRRR-MM-DD.jpg

spec.json:
{
  "layout": "hub",                      # "hub" (SyncTech w środku + połączone logotypy)
                                        # "checklist" (karta z listą + logotypy nad nią)
                                        # "vs" (dwie kolumny: lewa vs prawa, logotypy u góry)
  "kicker": "INTEGRACJE",               # mała etykieta nad nagłówkiem (opcjonalnie)
  "headline": ["Jeden panel,"],         # 1-2 linie, max ~16 znaków
  "accent": "wszystkie kanały.",        # linia w kolorze marki (opcjonalnie)
  "logos": ["allegro", "kaufland", "ebay"],   # nazwy plików z brand/logos/ (bez .png); brak pliku = karta z nazwą
  "items": ["...", "..."],              # checklist: 3-5 punktów (max ~34 znaki); vs: patrz niżej
  "left":  {"title": "Ręcznie", "items": ["..."]},    # tylko layout "vs"
  "right": {"title": "Z integracją", "items": ["..."]},
  "sub": "Krótki dopisek pod grafiką"   # opcjonalnie, 1 linia
}
Zawsze jasne tło. Logotypy pokazujemy w oryginalnych kolorach, bez zmian proporcji.
"""
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_post import T_DARK, T_MID, T_BRIGHT, font, fit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1350
BG = (247, 250, 249)
INK = (16, 32, 29)
MUTED = (88, 108, 104)
LINE = (190, 222, 215)
M = 80

NAMES = {
    "sellasist": "SellAsist", "shopgold": "ShopGold", "inpost": "InPost", "empik": "Empik",
    "amazon": "Amazon", "baselinker": "BaseLinker", "shoper": "Shoper", "apilo": "Apilo",
    "subiekt": "Subiekt", "comarch": "Comarch", "fakturownia": "Fakturownia", "allegro": "Allegro",
    "kaufland": "Kaufland", "ebay": "eBay", "dhl": "DHL", "dpd": "DPD", "shopify": "Shopify",
    "prestashop": "PrestaShop", "woocommerce": "WooCommerce", "googleanalytics": "Google Analytics",
    "googleads": "Google Ads", "meta": "Meta",
}


def logo_img(name, max_w, max_h):
    p = os.path.join(HERE, "logos", f"{name}.png")
    if not os.path.exists(p):
        return None
    im = Image.open(p).convert("RGBA")
    k = min(max_w / im.width, max_h / im.height)
    return im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)


def shadow_card(img, box, radius=36, fill=(255, 255, 255), blur=22, offset=10, alpha=38):
    x0, y0, x1, y1 = box
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((x0, y0 + offset, x1, y1 + offset), radius=radius, fill=(20, 60, 54, alpha))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    img.alpha_composite(sh)
    ImageDraw.Draw(img).rounded_rectangle(box, radius=radius, fill=fill + (255,))


def logo_card(img, name, cx, cy, w, h, radius=32):
    box = (int(cx - w / 2), int(cy - h / 2), int(cx + w / 2), int(cy + h / 2))
    shadow_card(img, box, radius=radius)
    lg = logo_img(name, w * 0.66, h * 0.6)
    d = ImageDraw.Draw(img)
    if lg:
        img.alpha_composite(lg, (int(cx - lg.width / 2), int(cy - lg.height / 2)))
    else:
        label = NAMES.get(name, name)
        size = fit(d, label, "ExtraBold", 46, w * 0.8)
        f = font("ExtraBold", size)
        tw = d.textlength(label, font=f)
        d.text((cx - tw / 2, cy - size * 0.62), label, font=f, fill=T_DARK)


def background(img):
    d = ImageDraw.Draw(img)
    for y in range(40, H, 44):
        for x in range(40, W, 44):
            d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(222, 234, 231))
    # miękka miętowa poświata w prawym górnym rogu
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((620, -260, 1340, 460), fill=T_BRIGHT + (70,))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(90)))


def header(img, spec):
    logo = Image.open(os.path.join(HERE, "logo.png")).convert("RGBA")
    lw = 300
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    img.alpha_composite(logo, (M, 70))
    d = ImageDraw.Draw(img)
    y = 210
    if spec.get("kicker"):
        kf = font("Bold", 28)
        t = spec["kicker"].upper()
        tw = d.textlength(t, font=kf)
        d.rounded_rectangle((M, y, M + tw + 40, y + 52), radius=26, fill=T_MID)
        d.text((M + 20, y + 10), t, font=kf, fill=(255, 255, 255))
        y += 80
    lines = list(spec.get("headline", []))
    acc = spec.get("accent")
    allp = lines + ([acc] if acc else [])
    size = min(fit(d, ln, "ExtraBold", 96, W - 2 * M) for ln in allp)
    hf = font("ExtraBold", size)
    for i, ln in enumerate(allp):
        d.text((M, y), ln, font=hf, fill=T_MID if (acc and i == len(allp) - 1) else INK)
        y += int(size * 1.12)
    return y


def footer(img, spec):
    d = ImageDraw.Draw(img)
    if spec.get("sub"):
        f = font("Medium", fit(d, spec["sub"], "Medium", 36, W - 2 * M))
        d.text((M, 1200), spec["sub"], font=f, fill=MUTED)
    t = "synctech.pl"
    f = font("Bold", 34)
    tw = d.textlength(t, font=f)
    d.rounded_rectangle((W - M - tw - 60, 1250, W - M, 1310), radius=30, fill=T_MID)
    d.text((W - M - tw - 30, 1259), t, font=f, fill=(255, 255, 255))


def layout_hub(img, spec, top):
    logos = spec.get("logos", [])[:6]
    cx, cy = W // 2, max(top + 360, 780)
    rx, ry = 360, 250
    d = ImageDraw.Draw(img)
    n = len(logos)
    pts = []
    for i in range(n):
        a = math.pi + (i + 0.5) * (2 * math.pi / n) if n > 2 else math.pi * (1 if i == 0 else 0)
        pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    for (x, y) in pts:  # linie połączeń (przerywane) + kropki
        steps = 26
        for s in range(0, steps, 2):
            t0, t1 = s / steps, (s + 1) / steps
            d.line((cx + (x - cx) * t0, cy + (y - cy) * t0, cx + (x - cx) * t1, cy + (y - cy) * t1), fill=T_MID, width=5)
        mx, my = cx + (x - cx) * 0.55, cy + (y - cy) * 0.55
        d.ellipse((mx - 9, my - 9, mx + 9, my + 9), fill=T_BRIGHT)
    # hub
    shadow_card(img, (cx - 150, cy - 150, cx + 150, cy + 150), radius=150, fill=(255, 255, 255), blur=30, alpha=55)
    ImageDraw.Draw(img).ellipse((cx - 150, cy - 150, cx + 150, cy + 150), outline=T_BRIGHT, width=6)
    mark = Image.open(os.path.join(HERE, "logo.png")).convert("RGBA")
    mark = mark.crop((0, 0, mark.height, mark.height))  # sygnet (kwadrat z kafelkami)
    mark = mark.resize((150, 150), Image.LANCZOS)
    img.alpha_composite(mark, (cx - 75, cy - 75))
    for name, (x, y) in zip(logos, pts):
        logo_card(img, name, x, y, 250, 140)


def layout_checklist(img, spec, top):
    items = spec.get("items", [])[:5]
    logos = spec.get("logos", [])[:3]
    y0 = top + (110 if logos else 40)
    pad_top = 110 if logos else 45
    bottom = 1160 if spec.get("sub") else 1220
    rows = min(112, (bottom - y0 - pad_top - 25) // max(1, len(items)))
    box = (M, y0, W - M, y0 + pad_top + 25 + rows * len(items))
    shadow_card(img, box, radius=40)
    d = ImageDraw.Draw(img)
    f = font("SemiBold", min(fit(d, it, "SemiBold", 42, W - 2 * M - 190) for it in items) if items else 42)
    y = y0 + pad_top
    for i, it in enumerate(items):
        cx, cyy = M + 80, y + 30
        d.ellipse((cx - 30, cyy - 30, cx + 30, cyy + 30), fill=T_MID)
        d.line((cx - 13, cyy + 1, cx - 3, cyy + 12, cx + 15, cyy - 11), fill=(255, 255, 255), width=8, joint="curve")
        d.text((M + 140, y + 4), it, font=f, fill=INK)
        if i < len(items) - 1:
            d.line((M + 140, y + rows - 22, W - M - 50, y + rows - 22), fill=(230, 238, 236), width=2)
        y += rows
    # logotypy „wiszące” nad kartą
    for i, name in enumerate(logos):
        logo_card(img, name, W - M - 130 - i * 270, y0 - 10, 240, 120, radius=28)


def layout_vs(img, spec, top):
    logos = spec.get("logos", [])[:4]
    y = top + 30
    if logos:
        cw = 200
        gap = 30
        x = M + cw / 2
        for name in logos:
            logo_card(img, name, x, y + 60, cw, 110, radius=26)
            x += cw + gap
        y += 170
    colw = (W - 2 * M - 30) // 2
    d = ImageDraw.Draw(img)
    for k, side in enumerate(("left", "right")):
        s = spec.get(side, {})
        x0 = M + k * (colw + 30)
        good = k == 1
        box = (x0, y, x0 + colw, 1160)
        shadow_card(img, box, radius=36, fill=(255, 255, 255) if good else (238, 243, 242), alpha=38 if good else 0)
        if good:
            ImageDraw.Draw(img).rounded_rectangle(box, radius=36, outline=T_MID, width=4)
        d = ImageDraw.Draw(img)
        tf = font("ExtraBold", fit(d, s.get("title", ""), "ExtraBold", 50, colw - 60))
        d.text((x0 + 34, y + 34), s.get("title", ""), font=tf, fill=T_MID if good else MUTED)
        f = font("SemiBold", 34)
        yy = y + 130
        for it in s.get("items", [])[:5]:
            sym = "✓" if good else "×"
            d.text((x0 + 34, yy - 4), sym, font=font("ExtraBold", 40), fill=T_MID if good else (180, 90, 80))
            # zawijanie do szerokości kolumny
            words, line, lines = it.split(), "", []
            # sierotki: jednoliterowe słowa (z, i, w, a, o, u) łączymy z następnym
            merged = []
            for w_ in words:
                if merged and len(merged[-1]) == 1 and merged[-1].isalpha():
                    merged[-1] = merged[-1] + "\u00a0" + w_
                else:
                    merged.append(w_)
            words = merged
            for w_ in words:
                if d.textlength((line + " " + w_).strip(), font=f) > colw - 120:
                    lines.append(line)
                    line = w_
                else:
                    line = (line + " " + w_).strip()
            lines.append(line)
            for ln in lines:
                d.text((x0 + 84, yy), ln, font=f, fill=INK if good else MUTED)
                yy += 44
            yy += 30


def render(spec, out):
    img = Image.new("RGBA", (W, H), BG + (255,))
    background(img)
    top = header(img, spec)
    {"hub": layout_hub, "checklist": layout_checklist, "vs": layout_vs}[spec.get("layout", "hub")](img, spec, top)
    footer(img, spec)
    img.convert("RGB").save(out, quality=93)


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        render(json.load(f), sys.argv[2])
    print("ok", sys.argv[2])
