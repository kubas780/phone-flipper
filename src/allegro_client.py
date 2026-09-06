"""
Klient oficjalnego REST API Allegro.

Wymaga zarejestrowanej aplikacji na https://apps.developer.allegro.pl/
(typ: "Aplikacja bez udziału użytkownika" / Client Credentials).
Instrukcja zakładania konta jest w README.md.

Dokumentacja: https://developer.allegro.pl/about
"""
import time
import requests

TOKEN_URL = "https://allegro.pl/auth/oauth/token"
API_BASE = "https://api.allegro.pl"


class AllegroClient:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self._token = None
        self._token_expires_at = 0

    def _get_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 30:
            return self._token

        resp = requests.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(self.client_id, self.client_secret),
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        self._token_expires_at = time.time() + data.get("expires_in", 3600)
        return self._token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Accept": "application/vnd.allegro.public.v1+json",
        }

    def search_offers(self, phrase: str, limit: int = 40) -> list[dict]:
        """Zwraca listę ofert (surowy JSON) pasujących do frazy, posortowane po cenie rosnąco."""
        params = {
            "phrase": phrase,
            "limit": limit,
            "sort": "+price",
        }
        resp = requests.get(
            f"{API_BASE}/offers/listing",
            headers=self._headers(),
            params=params,
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json().get("items", {}).get("promoted", []) + \
            resp.json().get("items", {}).get("regular", [])

    def get_cheapest_part_price(self, part_query: str) -> float | None:
        """Szuka na Allegro najtańszej pasującej części zamiennej i zwraca jej cenę."""
        offers = self.search_offers(part_query, limit=10)
        prices = []
        for o in offers:
            try:
                price = float(o["sellingMode"]["price"]["amount"])
                prices.append(price)
            except (KeyError, TypeError, ValueError):
                continue
        return min(prices) if prices else None

    @staticmethod
    def parse_offer(offer: dict, phone_model: str) -> "Listing":
        from models import Listing  # import lokalny, unikamy cyklu
        price = float(offer["sellingMode"]["price"]["amount"])
        return Listing(
            source="allegro",
            listing_id=offer["id"],
            title=offer.get("name", ""),
            price_pln=price,
            url=f"https://allegro.pl/oferta/{offer['id']}",
            phone_model=phone_model,
            description=offer.get("name", ""),
        )
