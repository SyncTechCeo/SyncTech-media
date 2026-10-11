"""SyncTech Studio: profesjonalne grafiki i rolki (HTML/CSS renderowane w Chromium).

Użycie:
    python3 brand/pro/render.py spec.json posts/RRRR-MM-DD.jpg        # post 1080x1350
    python3 brand/pro/render.py spec.json posts/RRRR-MM-DD-reel.mp4   # rolka 1080x1920, 30 fps

Format spec: patrz brand/pro/README.md (oraz przykłady w brand/pro/examples/).
"""
import base64
import json
import mimetypes
import os
import subprocess
import sys

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
BRAND = os.path.dirname(HERE)
FPS = 30

NAMES = {
    "sellasist": "SellAsist", "shopgold": "ShopGold", "inpost": "InPost", "empik": "Empik",
    "amazon": "Amazon", "baselinker": "BaseLinker", "shoper": "Shoper", "apilo": "Apilo",
    "subiekt": "Subiekt", "comarch": "Comarch", "fakturownia": "Fakturownia", "allegro": "Allegro",
    "kaufland": "Kaufland", "ebay": "eBay", "dhl": "DHL", "dpd": "DPD", "shopify": "Shopify",
    "prestashop": "PrestaShop", "woocommerce": "WooCommerce", "googleanalytics": "Google Analytics",
    "googleads": "Google Ads", "meta": "Meta", "facebook": "Facebook", "instagram": "Instagram",
}


def data_uri(path):
    mt = mimetypes.guess_type(path)[0] or "application/octet-stream"
    with open(path, "rb") as f:
        return f"data:{mt};base64," + base64.b64encode(f.read()).decode()


def logos():
    """Logotypy: najpierw SVG z brand/logos/svg, potem PNG z brand/logos (np. dodane ręcznie)."""
    out = {}
    pdir = os.path.join(BRAND, "logos")
    for fn in os.listdir(pdir):
        if fn.endswith(".png"):
            out[fn[:-4]] = data_uri(os.path.join(pdir, fn))
    sdir = os.path.join(pdir, "svg")
    for fn in os.listdir(sdir):
        if fn.endswith(".svg"):
            out[fn[:-4]] = data_uri(os.path.join(sdir, fn))
    return out


def page_for(p, spec):
    reel = spec.get("format") == "reel"
    w, h = 1080, 1920 if reel else 1350
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
    init = "window.SPEC=%s;window.LOGOS=%s;window.NAMES=%s;window.BRAND=%s;" % (
        json.dumps(spec, ensure_ascii=False), json.dumps(logos()), json.dumps(NAMES),
        json.dumps({"logo": data_uri(os.path.join(BRAND, "logo.png")), "mark": data_uri(os.path.join(HERE, "mark.png"))}))
    pg.add_init_script(init)
    pg.goto("file://" + os.path.join(HERE, "studio.html"))
    pg.evaluate("document.fonts.ready")
    pg.evaluate("window.build()")
    pg.wait_for_timeout(150)
    return b, pg, w, h


def render(spec, out):
    with sync_playwright() as p:
        if out.lower().endswith(".mp4"):
            spec["format"] = "reel"
            b, pg, w, h = page_for(p, spec)
            total = pg.evaluate("window.TOTAL")
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
                   "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100", "-shortest",
                   "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-profile:v", "high",
                   "-movflags", "+faststart", "-c:a", "aac", "-b:a", "128k", out]
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            for i in range(int(round(total * FPS))):
                pg.evaluate(f"window.seek({i / FPS})")
                proc.stdin.write(pg.screenshot(type="jpeg", quality=96, clip={"x": 0, "y": 0, "width": w, "height": h}))
            proc.stdin.close()
            if proc.wait() != 0:
                raise SystemExit("ffmpeg failed")
        else:
            spec["format"] = "post"
            b, pg, w, h = page_for(p, spec)
            pg.screenshot(path=out, type="jpeg", quality=95, clip={"x": 0, "y": 0, "width": w, "height": h})
        b.close()
    print("ok", out)


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        render(json.load(f), sys.argv[2])
