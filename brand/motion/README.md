# SyncTech Motion (styl TikTok „product film”)

Rolki TikTok w stylu premierowych filmów produktowych: jeden ciągły świat 3D zamiast cięć, telefon z prawdziwą głębią (krawędź, szkło, cień na podłodze), widok rozłożony ekranu (exploded view), kinetyczna typografia (słowo po słowie z rozmyciem), szklane karty, motion blur (render 60 kl/s → 30 kl/s) i własny sound design (pad, whoosh na przejściach, ticki, akord na końcu). Zawsze jasny motyw.

```
python3 brand/motion/render.py spec.json posts/RRRR-MM-DD-tiktok.mp4        # ok. 5–8 min renderu
python3 brand/motion/render.py spec.json posts/RRRR-MM-DD-tiktok-cover.jpg  # okładka
python3 brand/motion/render.py spec.json podglad.jpg --t 7.5                # jedna klatka
```

## Spec
- `screen`: treść ekranu telefonu (mail): `from, subject, kicker, hero, heroSub, button, tiles[3], callouts[3]` (opisy przy rozłożonych warstwach).
- `notif`: powiadomienie wpadające na ekran w scenie `device` (`title`, `text`).
- `oldmail`: rekwizyt „stary mail” w haku (`title, rows[[produkt, ilość, status]], text, links[]`), opcjonalnie.
- `beats[]`: sceny po kolei, każda `{type, dur, lines, accent, size}`:
  - `hook` – hak, telefon jeszcze poza kadrem (+ ewentualnie stary mail, który na końcu odlatuje obrotem),
  - `device` – telefon wjeżdża w 3D, wpada powiadomienie,
  - `explode` – warstwy ekranu rozchodzą się w głąb z opisami, na końcu „tap” w przycisk,
  - `stack` – telefon cofa się w nieostrość, wjeżdżają 3 szklane karty `cards[[tytuł, dopisek]]`,
  - `cta` – telefon z ekranem marki, `url: "synctech.pl"` z połyskiem.
- `cover`: `{lines, accent, sub, size}` dla okładki.

Wzór: `examples/email.json`. Nagłówki: max ~17 znaków w linii przy `size` 108–116.
