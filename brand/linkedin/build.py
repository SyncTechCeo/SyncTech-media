import base64, pathlib, sys
from playwright.sync_api import sync_playwright
here = pathlib.Path(__file__).resolve().parent
root = here.parent
mark = base64.b64encode((root/'pro/mark.png').read_bytes()).decode()
logo = base64.b64encode((root/'logo.png').read_bytes()).decode()
CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter Display','Inter',sans-serif;color:#0E1F1C;-webkit-font-smoothing:antialiased}
"""
LOGO = f"""<html><head><style>{CSS}
body{{width:400px;height:400px;background:#fff;display:flex;align-items:center;justify-content:center}}
img{{width:280px;height:280px}}</style></head><body><img src="data:image/png;base64,{mark}"></body></html>"""
COVER = f"""<html><head><style>{CSS}
body{{width:1128px;height:191px;position:relative;overflow:hidden;
background:
 radial-gradient(38% 120% at 92% 0%, rgba(106,211,192,.55) 0%, rgba(106,211,192,0) 100%),
 radial-gradient(30% 140% at 0% 100%, rgba(106,211,192,.35) 0%, rgba(106,211,192,0) 100%),
 radial-gradient(30% 90% at 70% 120%, rgba(173,226,255,.30) 0%, rgba(173,226,255,0) 100%),
 #F5F8F7}}
.grid{{position:absolute;inset:0;background-image:linear-gradient(to right,rgba(14,31,28,.05) 1px,transparent 1px),linear-gradient(to bottom,rgba(14,31,28,.05) 1px,transparent 1px);background-size:24px 24px;
 -webkit-mask-image:radial-gradient(60% 120% at 60% 50%,#000 0%,rgba(0,0,0,.3) 60%,transparent 90%)}}
.wrap{{position:absolute;left:300px;right:56px;top:0;bottom:0;display:flex;align-items:center;justify-content:space-between;gap:28px}}
h1{{font-weight:700;font-size:34px;line-height:1.08;letter-spacing:-.02em}}
h1 span{{background:linear-gradient(100deg,#1E4A43 0%,#2F7A6C 45%,#45B3A0 100%);-webkit-background-clip:text;color:transparent}}
p{{margin-top:8px;font-size:15px;color:#55625F;font-weight:500}}
.chips{{display:flex;flex-wrap:wrap;gap:7px;max-width:330px;justify-content:flex-end}}
.chip{{background:#fff;border:1px solid #DDF3EE;border-radius:999px;padding:6px 12px;font-size:13px;font-weight:600;color:#24715F;box-shadow:0 1px 2px rgba(14,31,28,.06),0 4px 12px rgba(14,31,28,.05)}}
</style></head><body><div class="grid"></div>
<div class="wrap"><div><h1>Wdrożenia i integracje<br><span>e-commerce</span></h1>
<p>SellAsist · ShopGold · marketplace'y · ERP · kurierzy</p></div>
<div class="chips"><div class="chip">Allegro</div><div class="chip">Amazon</div><div class="chip">Kaufland</div><div class="chip">BaseLinker</div><div class="chip">InPost</div><div class="chip">Subiekt</div><div class="chip">Automatyzacje</div><div class="chip">synctech.pl</div></div>
</div></body></html>"""
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, html, w, h in [('linkedin-logo.png', LOGO, 400, 400), ('linkedin-cover.png', COVER, 1128, 191)]:
        pg = b.new_page(viewport={'width': w, 'height': h}, device_scale_factor=2 if 'cover' in name else 1)
        pg.set_content(html); pg.wait_for_timeout(300)
        pg.screenshot(path=str(here/name))
    b.close()
