# SyncTech Studio (styl „pro”)

Grafiki i rolki renderowane jako HTML/CSS w Chromium (Playwright): warstwowe cienie, gradienty, typografia Inter Display, wektorowe logotypy platform, płynne animacje.

```
python3 brand/pro/render.py spec.json posts/RRRR-MM-DD.jpg        # post 1080x1350
python3 brand/pro/render.py spec.json posts/RRRR-MM-DD-reel.mp4   # rolka 1080x1920, 30 fps (~1 min renderu)
```

## Post — pola wspólne
- `layout`: `integrations` | `product` | `checklist` | `compare` | `myth`
- `eyebrow`: etykieta w prawym górnym rogu (np. „SellAsist · Wysyłki”)
- `lines`: linie nagłówka (każda linia = jedna linia na grafice, max ~18 znaków), `accent`: ostatnia linia w gradiencie marki
- `lead`: opcjonalny akapit pod nagłówkiem (`**pogrubienie**`)
- `logos`: slugi z `brand/logos/svg/*.svg` lub `brand/logos/*.png`; brak pliku = karta z nazwą (bez podrabiania logo)
- `note`: tekst w stopce (domyślnie „Wdrożenia i integracje e-commerce”)

## Układy
- `integrations`: SyncTech w środku, do 8 logotypów połączonych liniami.
- `product`: makieta panelu zamówień: `product.rows[] {logo,title,meta,status,tone: ok|wait|info|done, hl}`, `product.toast {logo,title,text}`. Numery zamówień to przykłady w makiecie, nie dane klientów.
- `checklist`: `items[]` jako tekst lub `[tytuł, dopisek]` (3–6), logotypy nad listą.
- `compare`: `left/right {title, items[]}` (ręcznie vs z integracją).
- `myth`: `myth`, `fact`, `factSub`.
- `email`: makieta newslettera: `email {from, subject, time, kicker, hero, heroSub, button, tiles[3], badges[0-2]}`.

## Rolka
`{"eyebrow": "...", "platform": "tiktok" (opcjonalnie: większy prawy margines pod pasek ikon TikToka), "scenes": [ {dur, lines, accent, size, top, kicker, lead, viz, cta, ...pola układu} ]}`. 4–5 scen, 14–18 s. `viz` = nazwa układu (`integrations`, `product`, `checklist`, `compare`, `myth`). Ostatnia scena: `cta: "synctech.pl"`.

Przykłady: `brand/pro/examples/`, gotowe próbki: `brand/samples/pro-*`.

## Okładka rolki
Ten sam spec rolki + wyjście `.jpg` = okładka 1080x1920 z treścią w strefie siatki profilu 3:4 (y 240–1680). Opcjonalne pole `cover {lines, accent, sub, logos, series, eyebrow}`; domyślnie hak z 1. sceny i logotypy z rolki.
