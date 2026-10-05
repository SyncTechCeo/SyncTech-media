"""Animowane intro logo synctech v2: nowoczesna sekwencja + dźwięk transformacji.

Użycie:
    python3 brand/make_intro.py 9x16 intro_9x16.mp4
    python3 brand/make_intro.py 16x9 intro_16x9.mp4
    python3 brand/make_intro.py 1x1  intro_1x1.mp4

Sekwencja:
  0.00  punkt + impuls (riser)
  0.75  rozbłysk w 9 punktów, które lecą na pozycje siatki (whoosh)
  1.15  punkty morfują w zaokrąglone kafelki (arpeggio „popów”)
  2.00  fala synchronizacji po przekątnej (shimmer)
  2.45  uderzenie: siatka przesuwa się w lewo, litery napisu wjeżdżają (impact + akord)
  3.35  połysk przez całe logo (glass sweep)
  3.70  podpis, potem trzymanie kadru
"""
import math
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_post import font  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
DUR = 5.4
SR = 44100
BG = np.array([247, 251, 250], dtype=np.float32)
MUTED = (88, 108, 104)
MINT = np.array([106, 211, 192], dtype=np.float32)
MINT_HI = np.array([190, 245, 232], dtype=np.float32)

SIZES = {"9x16": (1080, 1920, 0.80), "16x9": (1920, 1080, 1.05), "1x1": (1080, 1080, 0.80)}

# geometria logo.png (1150x365)
TILE_X = [4, 125, 246]
TILE_Y = [4, 125, 246]
TILE = 114
RADIUS = 18
TILE_RGB = [[(36, 77, 71), (61, 131, 121), (77, 161, 148)],
            [(61, 131, 121), (103, 208, 191), (77, 161, 148)],
            [(77, 161, 148), (61, 131, 121), (36, 77, 71)]]
LETTER_CUTS = [418, 505, 601, 699, 793, 866, 959, 1056, 1150]  # s y n c t e c h

T_BURST, T_MORPH, T_WAVE, T_IMPACT, T_SWEEP, T_TAG = 0.75, 1.15, 2.0, 2.45, 3.35, 3.7


# ---------- easing ----------
def clamp(t):
    return max(0.0, min(1.0, t))


def out_expo(t):
    t = clamp(t)
    return 1.0 if t >= 1 else 1 - 2 ** (-10 * t)


def out_back(t, s=1.7):
    t = clamp(t) - 1
    return t * t * ((s + 1) * t + s) + 1


def in_out_expo(t):
    t = clamp(t)
    if t in (0.0, 1.0):
        return t
    return 2 ** (20 * t - 10) / 2 if t < 0.5 else (2 - 2 ** (-20 * t + 10)) / 2


def out_cubic(t):
    return 1 - (1 - clamp(t)) ** 3


def lerp(a, b, t):
    return a + (b - a) * t


# ---------- grafika ----------
_tile_cache = {}


def tile_sprite(size, radius, rgb):
    """Antyaliasowany zaokrąglony kwadrat (supersampling x4)."""
    size = max(2, int(round(size)))
    radius = max(0, min(size / 2, radius))
    key = (size, int(radius * 4), tuple(int(v) for v in rgb))
    if key in _tile_cache:
        return _tile_cache[key]
    ss = 4
    im = Image.new("RGBA", (size * ss, size * ss), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, size * ss - 1, size * ss - 1), radius=int(radius * ss),
                                         fill=tuple(int(v) for v in rgb) + (255,))
    im = im.resize((size, size), Image.LANCZOS)
    if len(_tile_cache) > 4000:
        _tile_cache.clear()
    _tile_cache[key] = im
    return im


def paste_center(layer, spr, cx, cy, alpha=1.0):
    if alpha <= 0:
        return
    if alpha < 1:
        spr = spr.copy()
        a = np.asarray(spr.split()[3], dtype=np.float32) * alpha
        spr.putalpha(Image.fromarray(a.astype(np.uint8)))
    x, y = int(round(cx - spr.width / 2)), int(round(cy - spr.height / 2))
    W, H = layer.size
    if x >= W or y >= H or x + spr.width <= 0 or y + spr.height <= 0:
        return
    sx, sy = max(0, -x), max(0, -y)
    layer.alpha_composite(spr, (max(0, x), max(0, y)), (sx, sy))


def make_background(W, H):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    bg = np.ones((H, W, 3), np.float32) * BG
    # bardzo delikatne miętowe plamy
    for (cx, cy, r, s) in [(0.85, 0.15, 0.55, 0.06), (0.1, 0.9, 0.6, 0.05)]:
        d = ((xx - cx * W) ** 2 + (yy - cy * H) ** 2) / (r * max(W, H)) ** 2
        bg = bg + (MINT - BG) * (s * np.exp(-d * 3))[..., None]
    # subtelna siatka kropek
    step = 48
    dots = ((xx % step < 2.2) & (yy % step < 2.2)).astype(np.float32)
    bg = bg - dots[..., None] * 9
    return bg


def radial(W, H, cx, cy):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    return np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)


# ---------- dźwięk ----------
def env_ad(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / max(d, 1e-4))


def onepole_lp(x, cut):
    """Filtr dolnoprzepustowy o zmiennej częstotliwości (cut: tablica Hz)."""
    y = np.zeros_like(x)
    k = 1 - np.exp(-2 * np.pi * np.asarray(cut) / SR)
    acc = 0.0
    k = np.broadcast_to(k, x.shape)
    for i in range(len(x)):
        acc += k[i] * (x[i] - acc)
        y[i] = acc
    return y


def bandnoise(n, f0, f1, rng):
    noise = rng.standard_normal(n)
    cut_hi = np.geomspace(f0 * 1.8, f1 * 1.8, n)
    cut_lo = np.geomspace(f0 * 0.5, f1 * 0.5, n)
    return onepole_lp(noise, cut_hi) - onepole_lp(noise, cut_lo)


def sine_sweep(n, f0, f1):
    f = np.geomspace(f0, f1, n)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def build_audio(path, tile_order_times, letter_times):
    rng = np.random.default_rng(3)
    N = int(SR * DUR)
    L = np.zeros(N)
    R = np.zeros(N)

    def add(sig, at, gain=1.0, pan=0.0):
        i = int(at * SR)
        if i < 0:
            sig, i = sig[-i:], 0
        j = min(N, i + len(sig))
        if i >= N or j <= i:
            return
        gl = gain * math.cos((pan + 1) * math.pi / 4)
        gr = gain * math.sin((pan + 1) * math.pi / 4)
        L[i:j] += sig[: j - i] * gl
        R[i:j] += sig[: j - i] * gr

    # 1) riser: szum + sweep sinusa, narasta do rozbłysku
    n = int(SR * T_BURST)
    e = np.linspace(0, 1, n) ** 2.2
    riser = bandnoise(n, 300, 5000, rng) * 2.2 * e + 0.25 * sine_sweep(n, 180, 1400) * e
    add(riser, 0.0, 0.5)

    # 2) rozbłysk: „zip” + szybki whoosh w stereo
    n = int(SR * 0.45)
    zip_ = sine_sweep(n, 2400, 300) * env_ad(n, 0.002, 0.08)
    add(zip_, T_BURST, 0.25)
    n = int(SR * 0.6)
    wh = bandnoise(n, 3000, 400, rng) * np.sin(np.linspace(0, np.pi, n)) ** 1.5 * 3
    add(wh, T_BURST, 0.45, -0.6)
    add(wh[::-1] * 0.6, T_BURST + 0.05, 0.35, 0.6)

    # 3) popy przy morfowaniu: wznoszące się arpeggio (pentatonika)
    notes = [523.25, 587.33, 659.25, 783.99, 880.0, 1046.5, 1174.7, 1318.5, 1568.0]
    for k, at in enumerate(tile_order_times):
        n = int(SR * 0.22)
        f = notes[k] * (1 + 0.5 * np.exp(-np.arange(n) / (SR * 0.012)))  # pitch drop = „bloop”
        sig = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(n, 0.002, 0.07)
        add(sig, at, 0.42, -0.7 + 1.4 * (k % 3) / 2)

    # 4) shimmer fali synchronizacji
    n = int(SR * 0.7)
    sh = sum(np.sin(2 * np.pi * f * np.arange(n) / SR) for f in (2093, 2637, 3136, 3951))
    sh *= env_ad(n, 0.05, 0.25) * (0.6 + 0.4 * np.sin(2 * np.pi * 18 * np.arange(n) / SR))
    add(sh, T_WAVE, 0.08, -0.3)
    add(sh, T_WAVE + 0.04, 0.08, 0.3)

    # 5) przed uderzeniem: krótki reverse-whoosh
    n = int(SR * 0.35)
    rv = bandnoise(n, 500, 6000, rng) * np.linspace(0, 1, n) ** 3 * 3
    add(rv, T_IMPACT - 0.35, 0.45)

    # 6) IMPACT: sub z opadającą wysokością + ciało + transient
    n = int(SR * 1.6)
    t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t / 0.06)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.55)
    body = np.sin(2 * np.pi * np.cumsum(140 + 260 * np.exp(-t / 0.03)) / SR) * np.exp(-t / 0.12)
    click = rng.standard_normal(n) * np.exp(-t / 0.006)
    impact = np.tanh(1.6 * (0.9 * sub + 0.5 * body + 0.35 * click))
    add(impact, T_IMPACT, 0.9)

    # 7) akord (pad) po uderzeniu: Amaj9 z lekkim rozstrojeniem
    n = int(SR * (DUR - T_IMPACT))
    t = np.arange(n) / SR
    pad = np.zeros(n)
    for fr in (220.0, 277.18, 329.63, 415.30, 493.88):
        for det in (-0.6, 0.6):
            ph = 2 * np.pi * (fr + det) * t
            pad += np.sin(ph) + 0.25 * np.sin(2 * ph)
    pad *= np.minimum(1, t / 0.08) * np.exp(-t / 1.8)
    add(pad / 10, T_IMPACT, 0.32, -0.15)
    add(pad / 10, T_IMPACT + 0.012, 0.32, 0.15)

    # 8) tyknięcia liter
    for k, at in enumerate(letter_times):
        n = int(SR * 0.05)
        tk = rng.standard_normal(n) * np.exp(-np.arange(n) / (SR * 0.004))
        add(onepole_lp(tk, np.full(n, 6000.0)), at, 0.12, -0.5 + k / 7)

    # 9) glass sweep przy połysku
    n = int(SR * 0.9)
    gs = sine_sweep(n, 1800, 5200) * env_ad(n, 0.12, 0.25)
    gs += 0.6 * bandnoise(n, 4000, 9000, rng) * np.sin(np.linspace(0, np.pi, n)) ** 2
    add(gs, T_SWEEP, 0.07, -0.8)
    add(gs, T_SWEEP + 0.03, 0.07, 0.8)

    # pogłos: splot ze zanikającym szumem (osobno L/R)
    ir_n = int(SR * 1.3)
    ir_t = np.arange(ir_n) / SR
    out = []
    for ch, seed in ((L, 11), (R, 12)):
        ir = np.random.default_rng(seed).standard_normal(ir_n) * np.exp(-ir_t / 0.35)
        ir = onepole_lp(ir, np.full(ir_n, 5000.0))
        ir /= np.sqrt(np.sum(ir ** 2))
        size = 1 << int(np.ceil(np.log2(N + ir_n)))
        wet = np.fft.irfft(np.fft.rfft(ch, size) * np.fft.rfft(ir, size), size)[:N]
        out.append(ch + 0.28 * wet)
    st = np.stack(out, axis=1)
    fade = np.ones(N)
    fl = int(SR * 0.6)
    fade[-fl:] = np.linspace(1, 0, fl) ** 2
    st *= fade[:, None]
    st = st / (np.max(np.abs(st)) + 1e-9) * 0.89  # ok. -1 dBFS
    pcm = (st * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ---------- render ----------
def render(fmt, out):
    W, H, sc = SIZES[fmt]
    logo = Image.open(os.path.join(HERE, "logo.png")).convert("RGBA")
    big = logo.resize((int(logo.width * sc), int(logo.height * sc)), Image.LANCZOS)
    big = big.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
    lw, lh = big.size
    ox, oy = (W - lw) // 2, (H - lh) // 2 - int(30 * sc)

    letters = []
    for i in range(8):
        x0, x1 = int(LETTER_CUTS[i] * sc), int(LETTER_CUTS[i + 1] * sc)
        letters.append((x0, big.crop((x0, 0, x1, lh))))

    # środki kafelków (w końcowym układzie)
    centers = {(r, c): (ox + (TILE_X[c] + TILE / 2) * sc, oy + (TILE_Y[r] + TILE / 2) * sc)
               for r in range(3) for c in range(3)}
    gcx, gcy = centers[(1, 1)]
    shift0 = W / 2 - gcx  # na starcie siatka jest na środku ekranu
    grid_right = ox + (TILE_X[2] + TILE) * sc

    tile_px = TILE * sc
    dot_px = 26 * sc
    order = sorted(centers, key=lambda k: (k[0] + k[1], k[1]))  # fala po przekątnej
    morph_start = {k: T_MORPH + i * 0.075 for i, k in enumerate(order)}
    rng = np.random.default_rng(5)
    burst_delay = {k: rng.uniform(0, 0.12) for k in centers}

    letter_t0 = T_IMPACT + 0.12
    letter_times = [letter_t0 + i * 0.045 for i in range(8)]

    tagline = "INTEGRACJE  ·  AUTOMATYZACJA  ·  E-COMMERCE"
    tf = font("SemiBold", 34 if W > 1500 else 28)

    wav = out + ".wav"
    build_audio(wav, [morph_start[k] + 0.05 for k in order], letter_times)

    bg = make_background(W, H)
    rad_center = radial(W, H, W / 2, gcy)
    rad_grid = radial(W, H, gcx, gcy)
    YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)

    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav, "-shortest",
           "-c:v", "libx264", "-preset", "medium", "-crf", "15", "-pix_fmt", "yuv420p",
           "-profile:v", "high", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "192k", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    for fi in range(int(DUR * FPS)):
        t = fi / FPS
        frame = bg.copy()

        # impulsy (fale) – na starcie i przy uderzeniu
        for (t0, dur, maxr, strength, width) in [(0.15, 0.9, 0.45, 0.55, 3.0),
                                                  (0.45, 0.9, 0.45, 0.35, 2.5),
                                                  (T_IMPACT, 1.1, 0.75, 0.45, 5.0)]:
            p = (t - t0) / dur
            if 0 < p < 1:
                Rr = out_expo(p) * maxr * max(W, H)
                wpx = width * sc * (1 + 4 * p)
                ring = np.clip(1 - np.abs(rad_center - Rr) / wpx, 0, 1) * strength * (1 - p) ** 1.5
                if t0 == T_IMPACT:
                    ring = np.clip(1 - np.abs(rad_grid - Rr) / wpx, 0, 1) * strength * (1 - p) ** 1.5
                frame = frame + (MINT - frame) * ring[..., None]

        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))

        # przesunięcie siatki: środek ekranu -> pozycja końcowa
        gs = in_out_expo((t - T_IMPACT + 0.05) / 0.75)
        dx = shift0 * (1 - gs)

        # faza 1: pojedynczy punkt
        if t < T_BURST:
            p = out_back(t / 0.35)
            breathe = 1 + 0.12 * math.sin(t * 14) * clamp((t - 0.35) / 0.2)
            size = dot_px * 1.3 * p * breathe
            paste_center(layer, tile_sprite(size, size / 2, MINT), W / 2, gcy)

        # faza 2–4: punkty lecą, morfują, fala
        if t >= T_BURST:
            for key, (cx, cy) in centers.items():
                r, c = key
                p = out_expo((t - T_BURST - burst_delay[key]) / 0.55)
                sx, sy = W / 2, gcy
                px, py = lerp(sx, cx + dx, p), lerp(sy, cy, p)
                m = (t - morph_start[key]) / 0.42
                mp = out_back(m, 2.2) if m > 0 else 0.0
                size = lerp(dot_px, tile_px, mp)
                radius = lerp(dot_px / 2, RADIUS * sc, clamp(m * 1.3))
                col = MINT + (np.array(TILE_RGB[r][c], np.float32) - MINT) * clamp(m * 1.2)
                # fala synchronizacji
                wv = (t - (T_WAVE + (r + c) * 0.06)) / 0.32
                if 0 < wv < 1:
                    k = math.sin(math.pi * wv)
                    col = col + (MINT_HI - col) * 0.75 * k
                    size *= 1 + 0.07 * k
                # smuga ruchu w locie
                if 0 < p < 0.97:
                    for g in range(1, 6):
                        pg = out_expo((t - g / FPS * 0.6 - T_BURST - burst_delay[key]) / 0.55)
                        gx, gy = lerp(sx, cx + dx, pg), lerp(sy, cy, pg)
                        paste_center(layer, tile_sprite(size * (1 - g * 0.1), size / 2, col), gx, gy,
                                     0.22 * (1 - g / 6))
                paste_center(layer, tile_sprite(size, radius, col), px, py)

        # faza 5: litery wjeżdżają od dołu z maską, kaskadowo
        word_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        any_letter = False
        for i, (lx, im) in enumerate(letters):
            p = out_expo((t - letter_times[i]) / 0.6)
            if p <= 0:
                continue
            any_letter = True
            off = int((1 - p) * lh * 0.9)
            crop_h = lh - off
            if crop_h <= 0:
                continue
            part = im.crop((0, 0, im.width, crop_h))
            word_layer.alpha_composite(part, (int(ox + lx + dx * 0.0), oy + off))
        if any_letter:
            wa = np.array(word_layer)
            wa[:, : int(grid_right + dx + 6 * sc), 3] = 0
            layer = Image.alpha_composite(layer, Image.fromarray(wa, "RGBA"))

        # faza 6: połysk (glass sweep) po całym logo
        sp = (t - T_SWEEP) / 0.7
        if 0 < sp < 1:
            la = np.array(layer).astype(np.float32)
            yy, xx = YY, XX
            pos = lerp(ox - 300 * sc, ox + lw + 300 * sc, in_out_expo(sp))
            band = np.exp(-(((xx + (yy - gcy) * 0.45) - pos) / (55 * sc)) ** 2)
            k = band * (la[..., 3] / 255.0) * 0.55
            la[..., :3] = la[..., :3] + (255 - la[..., :3]) * k[..., None]
            layer = Image.fromarray(la.clip(0, 255).astype(np.uint8), "RGBA")

        # podpis z animacją rozstrzelenia liter
        pt = out_expo((t - T_TAG) / 0.9)
        if pt > 0:
            d = ImageDraw.Draw(layer)
            track = lerp(18, 4, pt) * (1 if fmt != "16x9" else 1)
            widths = [d.textlength(ch, font=tf) for ch in tagline]
            total = sum(widths) + track * (len(tagline) - 1)
            x = (W - total) / 2
            y = oy + lh + 80 * sc
            for ch, wch in zip(tagline, widths):
                d.text((x, y), ch, font=tf, fill=MUTED + (int(255 * pt),))
                x += wch + track

        # złożenie + lekki „punch” kamery przy uderzeniu
        base = Image.fromarray(frame.clip(0, 255).astype(np.uint8), "RGB").convert("RGBA")
        img = Image.alpha_composite(base, layer).convert("RGB")
        pz = (t - T_IMPACT) / 0.45
        if 0 < pz < 1:
            z = 1 + 0.035 * (1 - out_cubic(pz))
            nw, nh = int(W * z), int(H * z)
            img = img.resize((nw, nh), Image.BICUBIC).crop(((nw - W) // 2, (nh - H) // 2,
                                                             (nw - W) // 2 + W, (nh - H) // 2 + H))
        proc.stdin.write(img.tobytes())

    proc.stdin.close()
    rc = proc.wait()
    os.remove(wav)
    if rc != 0:
        raise SystemExit("ffmpeg failed")


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2])
    print("ok", sys.argv[2])
