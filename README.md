# Phone Flipper — szukacz okazji na telefony

Apka co 15 minut sprawdza Allegro, Allegro Lokalnie, OLX i Vinted, szuka
telefonów, na których sprzedaży zarobisz co najmniej 200 zł (uwzględniając
koszt oryginalnych części, jeśli telefon jest uszkodzony), i wysyła Ci
powiadomienie na Telegramie.

**Nie musisz nic programować.** Poniżej masz wszystko krok po kroku.
Całość zajmuje ok. 20-30 minut, robisz to raz.

---

## Ważne zastrzeżenia zanim zaczniesz

1. **Allegro** ma oficjalne API — to źródło jest stabilne i zgodne z regulaminem.
2. **Allegro Lokalnie, OLX i Vinted nie mają oficjalnego API do tego celu.**
   Apka "czyta" ich strony wyszukiwania w sposób automatyczny (tzw. scraping).
   To działa, ale:
   - narusza regulaminy tych serwisów (dozwolony użytek osobisty, ale formalnie
     to szara strefa — traktuj to świadomie, nie jako coś w 100% "legalnego"),
   - może się czasem "zepsuć", gdy serwis zmieni swoją stronę — wtedy trzeba
     poprosić o poprawkę kodu (patrz sekcja "Jak naprawić scraper" niżej),
   - Vinted bywa bardziej restrykcyjny i może blokować ruch z serwerów w chmurze.
3. Wycena "wartości rynkowej" telefonu to **mediana cen podobnych, aktywnych
   ofert** znalezionych w tym samym przebiegu skanowania. To dobre przybliżenie,
   ale nie 100% pewna wycena — zawsze rzuć okiem samodzielnie przed zakupem.
4. To narzędzie **tylko namierza i powiadamia** — decyzję o zakupie i całą
   transakcję zawsze robisz Ty ręcznie.

---

## Krok 1: Załóż konto GitHub (jeśli nie masz)

1. Wejdź na https://github.com/signup i załóż darmowe konto.
2. Utwórz nowe, **prywatne** repozytorium (przycisk "New repository"),
   np. o nazwie `phone-flipper`.
3. Wgraj do niego wszystkie pliki z tej paczki, którą Ci przygotowałem
   (przez przycisk "Add file" → "Upload files" na stronie repozytorium —
   przeciągnij cały folder).

## Krok 2: Załóż aplikację na Allegro (żeby korzystać z ich API)

1. Wejdź na https://apps.developer.allegro.pl/ i zaloguj się swoim kontem Allegro.
2. Kliknij "Zarejestruj aplikację".
3. Wybierz typ **"Allegro REST API"**, autoryzacja: **"Aplikacja bez logowania
   użytkownika (Client Credentials)"**.
4. Po zarejestrowaniu zobaczysz **Client ID** i **Client Secret** — zapisz je,
   będą potrzebne w Kroku 4.

## Krok 3: Załóż bota Telegram (do powiadomień)

1. W aplikacji Telegram wyszukaj **@BotFather** i wpisz `/newbot`.
2. Podaj nazwę bota (dowolną) i unikalny login kończący się na "bot"
   (np. `moj_flipper_bot`).
3. BotFather poda Ci **token** (długi ciąg znaków) — zapisz go.
4. Napisz do swojego nowo utworzonego bota cokolwiek (np. "cześć") — to
   konieczne, żeby mógł Ci pisać jako pierwszy.
5. Żeby poznać swój **chat_id**, wejdź w przeglądarce na:
   `https://api.telegram.org/bot<TWÓJ_TOKEN>/getUpdates`
   (podmień `<TWÓJ_TOKEN>` na token z punktu 3) i znajdź w odpowiedzi
   liczbę przy `"chat":{"id": ...}` — to jest Twój chat_id.

## Krok 4: Dodaj sekrety do repozytorium GitHub

W swoim repozytorium na GitHubie: **Settings → Secrets and variables →
Actions → New repository secret**. Dodaj po kolei 4 sekrety:

| Nazwa sekretu           | Wartość                                   |
|--------------------------|--------------------------------------------|
| `ALLEGRO_CLIENT_ID`      | Client ID z Kroku 2                        |
| `ALLEGRO_CLIENT_SECRET`  | Client Secret z Kroku 2                    |
| `TELEGRAM_BOT_TOKEN`     | Token bota z Kroku 3                       |
| `TELEGRAM_CHAT_ID`       | Twój chat_id z Kroku 3                     |

## Krok 5: Włącz harmonogram

1. Wejdź w zakładkę **Actions** w swoim repozytorium.
2. Jeśli GitHub pyta, potwierdź włączenie workflowów.
3. Znajdź workflow **"Skanowanie okazji na telefony"**, kliknij **"Run workflow"**,
   żeby przetestować ręcznie od razu (nie czekając na harmonogram co 15 min).
4. Sprawdź zakładkę z logami uruchomienia — jeśli wszystko zielone, powinieneś
   dostać wiadomość na Telegramie przy pierwszej znalezionej okazji (albo
   informację w logach "Brak nowych okazji", jeśli akurat nic nie znaleziono).

Od tej pory apka będzie się uruchamiać sama co 15 minut, całkowicie za darmo
(GitHub Actions ma darmowy limit, którego to zużycie nie przekroczy przy tej
częstotliwości).

---

## Dostosowanie do siebie

Otwórz plik **`config.yaml`** w repozytorium (można edytować wprost na stronie
GitHub, klikając ikonę ołówka) i zmień:

- `phones` — listę modeli telefonów, które Cię interesują,
- `min_profit_pln` — próg zysku (domyślnie 200 zł),
- `damage_keywords` / `damage_to_part_query` — słowa wskazujące uszkodzenie
  i jakiej części wtedy szukać.

Zmiany zapisują się od razu przy następnym uruchomieniu.

---

## Jak naprawić scraper (gdy OLX / Allegro Lokalnie / Vinted "się zepsują")

Te trzy źródła nie mają oficjalnego API, więc apka czyta bezpośrednio ich
strony internetowe. Jeśli te serwisy zmienią wygląd/strukturę strony, dany
moduł może przestać zwracać wyniki. Objawy: w logach GitHub Actions zobaczysz
`0 wyników` dla danego źródła, mimo że oferty na stronie istnieją.

W takiej sytuacji najprościej jest wrócić do mnie (Claude) z informacją
"scraper dla X przestał działać" — mogę zaktualizować kod. Jeśli chcesz spróbować
sam znaleźć nowy fragment strony do sczytania, mogę Cię przez to przeprowadzić
na bieżąco.

---

## Struktura plików

```
phone-flipper/
├── config.yaml              # ustawienia - edytujesz Ty
├── seen_listings.json       # pamięć apki (nie ruszaj ręcznie)
├── requirements.txt         # lista bibliotek Pythona
├── .github/workflows/scan.yml   # harmonogram uruchamiania w chmurze
└── src/
    ├── main.py                    # główny skrypt
    ├── models.py                  # struktury danych
    ├── allegro_client.py          # oficjalne API Allegro
    ├── allegro_lokalnie_client.py # scraper Allegro Lokalnie
    ├── olx_client.py               # scraper OLX
    ├── vinted_client.py            # scraper Vinted
    ├── pricing.py                  # wykrywanie uszkodzeń + kalkulacja zysku
    ├── notifier.py                  # wysyłka na Telegram
    └── state.py                     # zapamiętywanie już wysłanych okazji
```
