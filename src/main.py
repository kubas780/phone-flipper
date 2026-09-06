"""
Główny skrypt: dla każdego modelu telefonu z config.yaml, przeszukuje wszystkie
włączone źródła, wykrywa uszkodzenia, szacuje wartość rynkową, dolicza koszt
ewentualnej naprawy, liczy zysk i wysyła powiadomienia Telegram dla okazji
spełniających próg min_profit_pln.

Uruchomienie lokalne:
    python src/main.py

Wymagane zmienne środowiskowe (patrz README.md):
    ALLEGRO_CLIENT_ID, ALLEGRO_CLIENT_SECRET
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
"""
import os
import sys
import time
import traceback

import yaml

sys.path.insert(0, os.path.dirname(__file__))

from models import Listing  # noqa: E402
from allegro_client import AllegroClient  # noqa: E402
import allegro_lokalnie_client  # noqa: E402
import olx_client  # noqa: E402
import vinted_client  # noqa: E402
import pricing  # noqa: E402
import state  # noqa: E402
from notifier import notify_opportunities  # noqa: E402

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def collect_listings_for_phone(cfg: dict, phone: dict, allegro: AllegroClient) -> list[Listing]:
    """Zbiera ogłoszenia dla jednego modelu telefonu ze wszystkich włączonych źródeł."""
    listings: list[Listing] = []
    queries = [phone["query"]] + phone.get("search_variants", [])
    sources = cfg.get("sources", {})

    for query in queries:
        if sources.get("allegro", True):
            try:
                raw = allegro.search_offers(query)
                listings += [AllegroClient.parse_offer(o, phone["name"]) for o in raw]
            except Exception as e:
                print(f"[allegro] Błąd dla '{query}': {e}")

        if sources.get("allegro_lokalnie", True):
            try:
                listings += allegro_lokalnie_client.search(query, phone["name"])
            except Exception as e:
                print(f"[allegro_lokalnie] Błąd dla '{query}': {e}")

        if sources.get("olx", True):
            try:
                listings += olx_client.search(query, phone["name"])
            except Exception as e:
                print(f"[olx] Błąd dla '{query}': {e}")

        if sources.get("vinted", True):
            try:
                listings += vinted_client.search(query, phone["name"])
            except Exception as e:
                print(f"[vinted] Błąd dla '{query}': {e}")

    return listings


def analyze_phone_listings(cfg: dict, listings: list[Listing], allegro: AllegroClient) -> list:
    """Wykrywa uszkodzenia, szacuje wartość rynkową i liczy zysk dla ogłoszeń JEDNEGO modelu."""
    damage_keywords = cfg["damage_keywords"]
    damage_to_part = cfg["damage_to_part_query"]
    min_profit = cfg["min_profit_pln"]
    safety_margin = cfg["safety_margin_pln"]
    min_comparables = cfg["comparables_min_count"]
    exclude_keywords = cfg["exclude_keywords"]
    min_listing_price = cfg["min_listing_price_pln"]

    # Usuwamy akcesoria/atrapy/nierealnie tanie ogłoszenia PRZED czymkolwiek innym,
    # żeby nie zaniżały mediany ceny rynkowej dla całego modelu.
    before = len(listings)
    listings = [
        l for l in listings
        if not pricing.is_excluded_listing(l, exclude_keywords, min_listing_price)
    ]
    removed = before - len(listings)
    if removed:
        print(f"  odfiltrowano {removed} ogłoszeń (akcesoria/atrapy/zbyt niska cena)")

    for listing in listings:
        listing.is_damaged, listing.detected_damage = pricing.detect_damage(listing, damage_keywords)

    opportunities = []
    for listing in listings:
        market_value, n_comparables = pricing.estimate_market_value(
            listings, exclude=listing, min_comparables=min_comparables
        )
        if market_value is None:
            continue

        repair_query = None
        repair_cost = 0.0
        if listing.is_damaged:
            repair_query = pricing.find_repair_part_query(listing, damage_to_part)
            if repair_query:
                try:
                    price = allegro.get_cheapest_part_price(repair_query)
                    repair_cost = price if price is not None else 0.0
                except Exception as e:
                    print(f"[allegro parts] Błąd dla '{repair_query}': {e}")
            else:
                # Uszkodzenie wykryte, ale nie wiadomo jakiej części szukać -
                # pomijamy tę ofertę, żeby nie zaniżyć kosztu naprawy.
                continue

        opp = pricing.build_opportunity_if_profitable(
            listing, market_value, n_comparables, repair_query, repair_cost,
            min_profit, safety_margin,
        )
        if opp:
            opportunities.append(opp)

    return opportunities


def main():
    cfg = load_config()

    allegro = AllegroClient(
        client_id=os.environ["ALLEGRO_CLIENT_ID"],
        client_secret=os.environ["ALLEGRO_CLIENT_SECRET"],
    )
    telegram_token = os.environ["TELEGRAM_BOT_TOKEN"]
    telegram_chat_id = os.environ["TELEGRAM_CHAT_ID"]

    seen = state.load_seen()
    all_new_opportunities = []

    for phone in cfg["phones"]:
        print(f"Skanuję: {phone['name']}...")
        try:
            listings = collect_listings_for_phone(cfg, phone, allegro)
            opportunities = analyze_phone_listings(cfg, listings, allegro)
        except Exception:
            print(f"Błąd przy przetwarzaniu {phone['name']}:")
            traceback.print_exc()
            continue

        new_keys = state.filter_new(seen, [o.listing.unique_key for o in opportunities])
        new_opps = [o for o in opportunities if o.listing.unique_key in new_keys]
        all_new_opportunities += new_opps

        state.mark_seen(seen, [o.listing.unique_key for o in opportunities])
        time.sleep(1)  # uprzejmość wobec API/serwisów

    if all_new_opportunities:
        print(f"Znaleziono {len(all_new_opportunities)} nowych okazji - wysyłam powiadomienia.")
        notify_opportunities(telegram_token, telegram_chat_id, all_new_opportunities)
    else:
        print("Brak nowych okazji w tym przebiegu.")

    state.save_seen(seen)


if __name__ == "__main__":
    main()
