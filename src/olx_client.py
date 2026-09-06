"""
OLX nie ma publicznego API dla stron trzecich. Strona wyników wyszukiwania
osadza jednak dane ofert w formacie JSON wewnątrz znacznika <script id="olx-init-config">
lub podobnego - to znacznie stabilniejsze źródło niż parsowanie samego HTML-a,
ale format tego JSON-a też może się zmienić w przyszłości.

Jeśli funkcja `search` zacznie zwracać puste listy mimo że oferty na OLX
istnieją, patrz README.md -> "Jak naprawić scraper".
"""
import json
import re
import requests

SEARCH_URL = "https://www.olx.pl/oferty/q-{query}/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "pl-PL,pl;q=0.9",
}


def _extract_next_data(html: str) -> dict | None:
    """OLX (Next.js) zwykle osadza dane w <script id="__NEXT_DATA__">...</script>."""
    match = re.search(
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL
    )
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _walk_for_listings(node, out: list):
    """Rekurencyjnie szuka w drzewie JSON obiektów wyglądających jak ogłoszenie."""
    if isinstance(node, dict):
        if "id" in node and "title" in node and "url" in node and "price" in node:
            out.append(node)
        for v in node.values():
            _walk_for_listings(v, out)
    elif isinstance(node, list):
        for item in node:
            _walk_for_listings(item, out)


def search(query: str, phone_model: str, limit: int = 30) -> list["Listing"]:
    from models import Listing

    url = SEARCH_URL.format(query=requests.utils.quote(query))
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    data = _extract_next_data(resp.text)
    raw_listings: list = []
    if data:
        _walk_for_listings(data, raw_listings)

    results: list[Listing] = []
    for item in raw_listings[:limit]:
        try:
            price_obj = item.get("price", {})
            # struktura ceny bywa zagnieżdżona, np. {"regularPrice": {"value": 100}}
            price = None
            if isinstance(price_obj, dict):
                for key in ("value", "amount"):
                    if key in price_obj:
                        price = float(price_obj[key])
                        break
                    inner = price_obj.get("regularPrice") or price_obj.get("displayValue")
                    if isinstance(inner, dict) and "value" in inner:
                        price = float(inner["value"])
                        break
            elif isinstance(price_obj, (int, float, str)):
                price = float(str(price_obj).replace(" ", "").replace(",", "."))

            if price is None:
                continue

            listing_url = item["url"]
            if not listing_url.startswith("http"):
                listing_url = f"https://www.olx.pl{listing_url}"

            results.append(Listing(
                source="olx",
                listing_id=str(item["id"]),
                title=item.get("title", ""),
                price_pln=price,
                url=listing_url,
                phone_model=phone_model,
                description=item.get("description", item.get("title", "")),
            ))
        except (KeyError, ValueError, TypeError):
            continue

    return results
