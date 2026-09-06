"""
Vinted nie udostępnia oficjalnego API dla zewnętrznych aplikacji, ale ich
własna strona internetowa korzysta wewnętrznie z endpointu
/api/v2/catalog/items, którego tu używamy.

RYZYKO: Vinted potrafi blokować ruch z adresów IP chmur (w tym GitHub Actions).
Jeśli ten moduł zacznie zwracać błędy 401/403, najprościej jest:
  1) zwiększyć odstępy między zapytaniami (sources w config.yaml),
  2) lub uruchamiać skrypt lokalnie / na własnym serwerze zamiast GitHub Actions
     (patrz README.md -> "Alternatywny hosting").
Telefony (kategoria elektronika) na Vinted pojawiają się rzadziej niż na
pozostałych portalach - to źródło jest tu traktowane jako dodatkowe.
"""
import requests

BASE_URL = "https://www.vinted.pl"
SEARCH_ENDPOINT = f"{BASE_URL}/api/v2/catalog/items"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pl-PL,pl;q=0.9",
}


def _get_session_cookies() -> requests.cookies.RequestsCookieJar:
    """Vinted wymaga wcześniejszej wizyty na stronie głównej, żeby dostać
    cookie sesyjne / anty-bot, zanim zapyta się API."""
    session = requests.Session()
    session.headers.update(HEADERS)
    session.get(BASE_URL, timeout=20)
    return session


def search(query: str, phone_model: str, limit: int = 30) -> list["Listing"]:
    from models import Listing

    session = _get_session_cookies()
    params = {
        "search_text": query,
        "per_page": limit,
        "order": "price_low_to_high",
    }
    resp = session.get(SEARCH_ENDPOINT, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    results: list[Listing] = []
    for item in data.get("items", []):
        try:
            price_field = item.get("price", item.get("total_item_price"))
            if isinstance(price_field, dict):
                price = float(price_field.get("amount"))
            else:
                price = float(price_field)

            results.append(Listing(
                source="vinted",
                listing_id=str(item["id"]),
                title=item.get("title", ""),
                price_pln=price,
                url=item.get("url", f"{BASE_URL}/items/{item['id']}"),
                phone_model=phone_model,
                description=item.get("title", ""),
            ))
        except (KeyError, ValueError, TypeError):
            continue

    return results
