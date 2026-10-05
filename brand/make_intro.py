"""Animowane intro logo synctech (MP4 z dźwiękiem).

Użycie:
    python3 brand/make_intro.py 9x16 intro_9x16.mp4
    python3 brand/make_intro.py 16x9 intro_16x9.mp4
    python3 brand/make_intro.py 1x1  intro_1x1.mp4

Kafelki i napis są wycinane z oryginalnego logo (brand/logo.png),
więc ostatnia klatka to dokładnie Twoje logo, bez zniekształceń.
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
DUR = 4.6
BG = (246, 250, 249)
MUTED = (88, 108, 104)
MINT = (106, 211, 192)

SIZES = {"9x16": (1080, 1920, 0.78), "16x9": (1920, 1080, 1.0), "1x1": (1080, 1080, 0.78)}

# geometria logo.png (1150x365): kafelki 3x3 i napis
TILE_X = [4, 125, 246]
TILE_Y = [4, 125, 246]
TILE = 114
WORD_X0, WORD_X1 = 410, 1150

# kolejność wlatywania: rogi -> krawędzie -> środek
ORDER = [(0, 0), (2, 2), (0, 2), (2, 0), (0, 1), (1, 2), (2, 1), (1, 0), (1, 1)]


def ease_out_back(t, s=1.4):
    t = max(0.0, min(1.0, t)) - 1
    return t * t * ((s + 1) * t + s) + 1


def ease_out_cubic(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def tone(sr, freq, dur, vol, decay):
    n = int(sr * dur)
    t = np.arange(n) / sr
    env = np.exp(-t * decay) * np.minimum(1, t * 400)
    return vol * env * (np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * freq * 2 * t))


def make_audio(path, tile_times, pulse_t, word_t):
    sr = 44100
    out = np.zeros(int(sr * DUR))

    def add(sig, at):
        i = int(at * sr)
        j = min(len(out), i + len(sig))
        out[i:j] += sig[: j - i]

    for k, at in enumerate(tile_times):
        add(tone(sr, 900 + 60 * k, 0.09, 0.10, 45), at)  # cichy „klik” przy zatrzaśnięciu
    add(tone(sr, 1318.5, 0.9, 0.12, 5), pulse_t)  # E6
    add(tone(sr, 1975.5, 0.9, 0.08, 5), pulse_t + 0.06)  # B6
    # miękki „whoosh” przy napisie
    n = int(sr * 0.5)
    noise = np.random.default_rng(1).standard_normal(n)
    noise = np.convolve(noise, np.ones(40) / 40, mode="same")
    env = np.sin(np.linspace(0, math.pi, n)) ** 2
    add(0.05 * noise * env, word_t - 0.1)
    out = np.clip(out, -1, 1)
    pcm = (out * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def render(fmt, out):
    W, H, sc = SIZES[fmt]
    logo = Image.open(os.path.join(HERE, "logo.png")).convert("RGBA")
    big = logo.resize((int(logo.width * sc), int(logo.height * sc)), Image.LANCZOS)
    lw, lh = big.size
    ox, oy = (W - lw) // 2, (H - lh) // 2 - int(40 * sc)

    tiles = {}
    for r in range(3):
        for c in range(3):
            x0, y0 = int(TILE_X[c] * sc), int(TILE_Y[r] * sc)
            tiles[(r, c)] = big.crop((x0, y0, x0 + int(TILE * sc) + 1, y0 + int(TILE * sc) + 1))
    wx0 = int(WORD_X0 * sc)
    word = big.crop((wx0, 0, lw, lh))
    grid_right = ox + int((TILE_X[2] + TILE) * sc)

    tagline = "Integracje  ·  Automatyzacja  ·  E-commerce"
    tf = font("Medium", 40 if fmt != "16x9" else 38)

    t_start, t_step, t_fly = 0.25, 0.11, 0.55
    tile_land = [t_start + i * t_step + t_fly * 0.72 for i in range(9)]
    pulse_t = t_start + 8 * t_step + t_fly + 0.05
    word_t = pulse_t + 0.25
    tag_t = word_t + 0.55

    rng = np.random.default_rng(7)
    starts = {}
    for i, (r, c) in enumerate(ORDER):
        ang = math.atan2(r - 1, c - 1) if (r, c) != (1, 1) else -math.pi / 2
        dist = (W + H) * 0.35
        jitter = rng.uniform(-0.35, 0.35)
        starts[(r, c)] = (math.cos(ang + jitter) * dist, math.sin(ang + jitter) * dist, rng.uniform(-80, 80))

    wav = out + ".wav"
    make_audio(wav, tile_land, pulse_t, word_t)

    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav, "-shortest",
           "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p",
           "-profile:v", "high", "-movflags", "+faststart", "-c:a", "aac", "-b:a", "160k", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    for fi in range(int(DUR * FPS)):
        t = fi / FPS
        frame = Image.new("RGBA", (W, H), BG + (255,))

        # miękka poświata za środkiem siatki po zatrzaśnięciu
        g = ease_out_cubic((t - pulse_t) / 0.4) * (1 - 0.6 * ease_in_out((t - pulse_t - 0.4) / 0.8))
        if g > 0:
            glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow)
            cx = ox + int((TILE_X[1] + TILE / 2) * sc)
            cy = oy + int((TILE_Y[1] + TILE / 2) * sc)
            rad = int(260 * sc)
            gd.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), fill=MINT + (int(45 * g),))
            glow = glow.filter(ImageFilter.GaussianBlur(int(90 * sc)))
            frame = Image.alpha_composite(frame, glow)

        # napis „synctech” wysuwa się zza siatki
        pw = ease_out_cubic((t - word_t) / 0.7)
        if pw > 0:
            shift = int((1 - pw) * (lw - wx0) * 0.55)
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            wl = word.copy()
            a = np.array(wl.split()[3]).astype(float) * min(1.0, pw * 1.6)
            wl.putalpha(Image.fromarray(a.astype(np.uint8)))
            layer.alpha_composite(wl, (ox + wx0 - shift, oy))
            la = np.array(layer)
            la[:, : grid_right + int(8 * sc), 3] = 0  # napis widoczny dopiero na prawo od siatki
            frame = Image.alpha_composite(frame, Image.fromarray(la, "RGBA"))

        # kafelki
        for i, key in enumerate(ORDER):
            lt = (t - (t_start + i * t_step)) / t_fly
            if lt <= 0:
                continue
            p = ease_out_back(lt)
            sx, sy, rot = starts[key]
            r, c = key
            tx = ox + int(TILE_X[c] * sc) + int((1 - p) * sx)
            ty = oy + int(TILE_Y[r] * sc) + int((1 - p) * sy)
            spr = tiles[key]
            scale = 1.0
            if key == (1, 1):
                q = (t - pulse_t) / 0.35
                if 0 < q < 1:
                    scale = 1 + 0.14 * math.sin(math.pi * q)
            ang = (1 - ease_out_cubic(lt)) * rot
            alpha = min(1.0, lt * 3)
            if abs(ang) > 0.3 or scale != 1.0 or alpha < 1:
                s2 = spr
                if scale != 1.0:
                    nw = int(spr.width * scale)
                    s2 = spr.resize((nw, nw), Image.BICUBIC)
                    tx -= (nw - spr.width) // 2
                    ty -= (nw - spr.width) // 2
                if abs(ang) > 0.3:
                    before = s2.size
                    s2 = s2.rotate(ang, resample=Image.BICUBIC, expand=True)
                    tx -= (s2.width - before[0]) // 2
                    ty -= (s2.height - before[1]) // 2
                if alpha < 1:
                    s2 = s2.copy()
                    a = np.array(s2.split()[3]).astype(float) * alpha
                    s2.putalpha(Image.fromarray(a.astype(np.uint8)))
                spr = s2
            if -spr.width < tx < W and -spr.height < ty < H:
                frame.alpha_composite(spr, (max(tx, 0), max(ty, 0)),
                                      (max(-tx, 0), max(-ty, 0)))

        # podpis
        pt = ease_out_cubic((t - tag_t) / 0.6)
        if pt > 0:
            d = ImageDraw.Draw(frame)
            tw = d.textlength(tagline, font=tf)
            y = oy + lh + int(70 * sc) + int((1 - pt) * 20)
            d.text(((W - tw) / 2, y), tagline, font=tf, fill=MUTED + (int(255 * pt),))

        proc.stdin.write(frame.convert("RGB").tobytes())

    proc.stdin.close()
    rc = proc.wait()
    os.remove(wav)
    if rc != 0:
        raise SystemExit("ffmpeg failed")


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2])
    print("ok", sys.argv[2])
