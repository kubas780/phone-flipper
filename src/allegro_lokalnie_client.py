"""
Allegro Lokalnie NIE udostępnia publicznego, oficjalnego API do wyszukiwania ofert
przez zewnętrzne aplikacje. Ten moduł pobiera i parsuje stronę wyników wyszukiwania.

UWAGA: to rozwiązanie jest z natury kruche - jeśli Allegro Lokalnie zmieni układ
strony (HTML), parsowanie może przestać działać i trzeba będzie zaktualizować
selektory w funkcji `_parse_listing_cards`. Instrukcja jak to zrobić samodzielnie
(bez programowania) jest w README.md w sekcji "Jak naprawić scraper".
"""
import re
import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://allegrolokalnie.pl/oferty/{query}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "pl-PL,pl;q=0.9",
}


def _clean_price(text: str) -> float | None:
    match = re.search(r"([\d\s]+[,.]?\d*)\s*z[łl]", text.replace("\xa0", " "))
    if not match:
        return None
    raw = match.group(1).replace(" ", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def search(query: str, phone_model: str, limit: int = 30) -> list["Listing"]:
    from models import Listing

    url = SEARCH_URL.format(query=requests.utils.quote(query))
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    results: list[Listing] = []
    # Karty ofert - selektor może wymagać dopasowania jeśli strona się zmieni.
    cards = soup.select("a[href*='/oferta/']")
    seen_ids = set()

    for card in cards[:limit]:
        href = card.get("href", "")
        m = re.search(r"/oferta/[^/]*-(\w+)$", href) or re.search(r"/oferta/(\w+)", href)
        if not m:
            continue
        listing_id = m.group(1)
        if listing_id in seen_ids:
            continue
        seen_ids.add(listing_id)

        title = card.get_text(strip=True)
        price = _clean_price(card.parent.get_text(" ", strip=True)) if card.parent else None
        if not title or price is None:
            continue

        full_url = href if href.startswith("http") else f"https://allegrolokalnie.pl{href}"
        results.append(Listing(
            source="allegro_lokalnie",
            listing_id=listing_id,
            title=title,
            price_pln=price,
            url=full_url,
            phone_model=phone_model,
            description=title,
        ))
    return results
