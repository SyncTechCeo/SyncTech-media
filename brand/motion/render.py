"""SyncTech Motion: rolki TikTok w stylu „product film” (3D telefon, kinetyczna typografia, sound design).

Użycie:
    python3 brand/motion/render.py spec.json posts/RRRR-MM-DD-tiktok.mp4        # wideo 1080x1920, 30 fps, motion blur
    python3 brand/motion/render.py spec.json posts/RRRR-MM-DD-tiktok-cover.jpg  # okładka
    python3 brand/motion/render.py spec.json frame.jpg --t 7.5                  # pojedyncza klatka (podgląd)

Opis spec: brand/motion/README.md, wzór: brand/motion/examples/email.json
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
BRAND = os.path.dirname(HERE)
RENDER_FPS = 60   # renderujemy 60 kl/s i łączymy pary klatek -> naturalny motion blur przy 30 kl/s
SR = 44100


def data_uri(path):
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def open_page(p, spec):
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1080, "height": 1920}, device_scale_factor=1)
    pg.add_init_script("window.SPEC=%s;window.BRAND=%s;" % (
        json.dumps(spec, ensure_ascii=False),
        json.dumps({"logo": data_uri(os.path.join(BRAND, "logo.png")), "mark": data_uri(os.path.join(BRAND, "pro", "mark.png"))})))
    pg.goto("file://" + os.path.join(HERE, "motion.html"))
    pg.evaluate("document.fonts.ready")
    pg.evaluate("window.build()")
    pg.wait_for_timeout(200)
    return b, pg


# ---------------- sound design (syntetyczny, bez cudzych nagrań) ----------------
def _lp(x, a):
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc += a * (x[i] - acc); y[i] = acc
    return y


def soundtrack(spec, total):
    n = int(total * SR) + SR
    t = np.arange(n) / SR
    out = np.zeros(n)
    rng = np.random.default_rng(7)
    # ciepły pad (Fmaj9) z wolnym wejściem i lekkim chorusem
    for f, g in ((87.31, .5), (174.61, .35), (220.0, .28), (261.63, .22), (329.63, .16), (392.0, .12)):
        out += g * (np.sin(2 * np.pi * f * t) + .5 * np.sin(2 * np.pi * f * 1.003 * t + 1.3))
    env = np.clip(t / 1.8, 0, 1) * np.clip((total + .4 - t) / 1.2, 0, 1)
    out *= .045 * env * (1 + .15 * np.sin(2 * np.pi * .25 * t))
    # puls (miękki kick co 0.5 s od 2. sceny)
    starts, acc = [], 0
    for b in spec["beats"]:
        starts.append(acc); acc += b["dur"]
    kick_t = np.arange(starts[1] if len(starts) > 1 else 0, total - 1.0, .5)
    for k in kick_t:
        i = int(k * SR); m = min(n - i, int(.35 * SR)); tt = np.arange(m) / SR
        out[i:i + m] += .22 * np.sin(2 * np.pi * (55 + 70 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 9)
    # whoosh na przejściach
    noise = rng.standard_normal(int(1.2 * SR))
    for s in starts[1:]:
        i0 = int((s - .55) * SR); m = len(noise); tt = np.arange(m) / SR
        sweep = _lp(noise * (np.sin(np.pi * np.clip(tt / .9, 0, 1)) ** 2), .08)
        hp = sweep - _lp(sweep, .01)
        seg = .5 * hp
        a, bnd = max(i0, 0), min(i0 + m, n)
        out[a:bnd] += seg[a - i0:bnd - i0]
    # „tick” przy pojawianiu się słów / kart i „tap” przy kliknięciu
    def tick(at, f=2400, g=.12, d=.05):
        i = int(at * SR); m = int(d * SR); tt = np.arange(m) / SR
        if 0 <= i < n - m:
            out[i:i + m] += g * np.sin(2 * np.pi * f * tt) * np.exp(-tt * 80)
    for k, b in enumerate(spec["beats"]):
        words = sum(len(l.split()) for l in b.get("lines", [])) + len(b.get("accent", "").split())
        for w in range(words):
            tick(starts[k] + .12 + w * .075 + .15, 1800 + 120 * w, .05)
        if b["type"] == "stack":
            for c in range(len(b.get("cards", []))):
                tick(starts[k] + .55 + c * .38 + .2, 1200, .14, .09)
        if b["type"] == "explode":
            tick(starts[k] + b["dur"] - .55, 900, .25, .12)
        if b["type"] == "device":
            tick(starts[k] + 1.0, 1567, .16, .25); tick(starts[k] + 1.08, 2093, .12, .3)
        if b["type"] == "cta":
            for f, d in ((523.25, 0), (659.25, .09), (783.99, .18), (1046.5, .27)):
                i = int((starts[k] + .9 + d) * SR); m = int(1.6 * SR); tt = np.arange(m) / SR
                if i + m < n:
                    out[i:i + m] += .07 * (np.sin(2 * np.pi * f * tt) + .3 * np.sin(4 * np.pi * f * tt)) * np.exp(-tt * 2.5)
    out = out[:int(total * SR)]
    out = np.tanh(out * 1.4) * .8
    st = np.stack([out, np.roll(out, 90)], 1)
    return (st * 32767).astype(np.int16)


def write_wav(path, data):
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(data.tobytes())


def render(spec, out, at=None):
    with sync_playwright() as p:
        b, pg = open_page(p, spec)
        if out.lower().endswith(".mp4"):
            total = pg.evaluate("window.TOTAL")
            wav = tempfile.mktemp(suffix=".wav")
            write_wav(wav, soundtrack(spec, total))
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(RENDER_FPS), "-c:v", "mjpeg", "-i", "-",
                   "-i", wav, "-filter:v", "tmix=frames=2:weights='1 1',fps=30",
                   "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-profile:v", "high",
                   "-movflags", "+faststart", "-c:a", "aac", "-b:a", "160k", "-shortest", out]
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            for i in range(int(round(total * RENDER_FPS))):
                pg.evaluate(f"window.seek({i / RENDER_FPS})")
                proc.stdin.write(pg.screenshot(type="jpeg", quality=95))
            proc.stdin.close()
            if proc.wait() != 0:
                raise SystemExit("ffmpeg failed")
            os.remove(wav)
        elif at is not None:
            pg.evaluate(f"window.seek({at})")
            pg.screenshot(path=out, type="jpeg", quality=92)
        else:
            pg.evaluate("window.cover()")
            pg.screenshot(path=out, type="jpeg", quality=95)
        b.close()
    print("ok", out)


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        spec = json.load(f)
    at = float(sys.argv[sys.argv.index("--t") + 1]) if "--t" in sys.argv else None
    render(spec, sys.argv[2], at)
