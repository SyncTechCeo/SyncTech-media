# Zasady postów synctech.pl

## Kanały i harmonogram
- Jedna publikacja dziennie o **10:00 (Europe/Warsaw)**.
- Układ tygodnia: **post (grafika)** w poniedziałek, środę, piątek i sobotę; **rolka (wideo)** we wtorek, czwartek i niedzielę.
- Publikacja jednocześnie na **Instagram** i **Facebook**, przez Metricool, marka „SyncTech.pl” (brandId `7240380`).
- Facebook: **wyłącznie firmowa strona SyncTech.pl** (facebookData `1012521311954593`). Nigdy profil prywatny. Jeśli w Metricool pojawi się inne konto Facebook, nie publikuj tam.

## O firmie
synctech.pl to usługi IT i e-commerce: integracje BaseLinker, ShopGold, Shopify, Subiekt GT, automatyzacja sklepów internetowych (zamówienia, stany magazynowe, faktury, etykiety, synchronizacja produktów). Klienci to właściciele małych i średnich sklepów internetowych w Polsce.

## Ton
- Po polsku, na „Ty”, konkretnie, bez korpomowy.
- Każdy post daje coś wartościowego: poradę, problem z rozwiązaniem albo konkretną wiedzę. Maks. 1 na 5 postów może być wprost ofertą.
- **Nie wymyślaj** klientów, case studies, liczb, opinii ani wyników („oszczędziliśmy klientowi 40 h”). Można pisać ogólnie („w wielu sklepach…”) albo używać pytań i przykładów hipotetycznych, wyraźnie jako przykład.
- Opis: 600–1200 znaków, mocny pierwszy wiersz, krótkie akapity, 2–5 emoji, zakończenie z wezwaniem do działania (np. „Napisz do nas: synctech.pl”).
- Instagram: 8–12 hashtagów na końcu. Facebook: ten sam tekst, ale 2–3 hashtagi i link `https://synctech.pl`.

## Rotacja tematów (po kolei, potem od nowa)
1. Porada BaseLinker (np. automatyczne akcje, statusy, szablony)
2. Problem → rozwiązanie (ręczna praca w sklepie, którą da się zautomatyzować)
3. Shopify / ShopGold: funkcja lub integracja, o której mało kto wie
4. Mit lub błąd w e-commerce (np. „automatyzacja jest tylko dla dużych”)
5. Checklista lub lista kroków (np. 5 rzeczy do sprawdzenia przed integracją)
6. Subiekt GT i magazyn: stany, faktury, synchronizacja
7. Oferta / jak pracujemy (konsultacja, wdrożenie, wsparcie)

## Styl wizualny
Zawsze **jasny motyw** (`"variant": "light"`), właściciel nie chce ciemnych grafik. Logo musi być wyraźne.

## Grafika (post)
Generator: `python3 brand/make_post.py spec.json posts/RRRR-MM-DD.jpg` (opis formatu w pliku). Zawsze `light`. Nagłówek krótki (max ~13 znaków w linii, 2–3 linie + akcent). Zawsze obejrzyj gotowy obraz przed publikacją.

## Rolka (reel)
Generator: `python3 brand/make_reel.py spec.json posts/RRRR-MM-DD-reel.mp4` (opis formatu w pliku). 4–6 plansz, łącznie 12–20 s, pierwsza plansza to mocny hak (pytanie lub obietnica), ostatnia ma CTA `synctech.pl`. Bez emoji w tekście plansz. Sprawdź 3 klatki (ffmpeg -ss … -frames:v 1) przed publikacją.
Publikacja: Instagram `instagramData {type: REEL, showReelOnFeed: true}`, Facebook `facebookData {type: REEL}`.

## Dziennik
Każdy opublikowany post dopisz do `log.md` (data, numer tematu z rotacji, nagłówek). Przed pisaniem nowego posta przeczytaj ostatnie 14 wpisów, żeby nie powtarzać tematów ani nagłówków.
