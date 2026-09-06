"""Wykrywanie uszkodzeń w ogłoszeniu, szacowanie wartości rynkowej i zysku."""
import statistics
import re

from typing import Optional

from models import Listing, Opportunity

_KNOWN_VARIANT_TOKENS = {"ultra", "plus", "pro", "max", "fe", "edge", "air"}
_TOKEN_RE = re.compile(r"[a-ząćęłńóśźż]+|\d+", re.IGNORECASE)


def _tokenize(text: str) -> set[str]:
    text = text.lower().replace("+", " plus ")
    return set(_TOKEN_RE.findall(text))


def listing_matches_model(listing: "Listing", model_name: str) -> bool:
    name_tokens = _tokenize(model_name)
    title_tokens = _tokenize(f"{listing.title} {listing.description}")

    if not name_tokens.issubset(title_tokens):
        return False

    forbidden = _KNOWN_VARIANT_TOKENS - name_tokens
    if forbidden & title_tokens:
        return False

    return True
def is_excluded_listing(listing: Listing, exclude_keywords: list[str], min_price_pln: float) -> bool:
    """
    Zwraca True, jeśli ogłoszenie należy całkowicie pominąć (nie jest prawdziwym
    telefonem - to akcesorium, atrapa, część, albo cena jest nierealnie niska).
    """
    if listing.price_pln < min_price_pln:
        return True
    text = f"{listing.title} {listing.description}".lower()
    for kw in exclude_keywords:
        if kw.lower() in text:
            return True
    return False
def detect_damage(listing: Listing, damage_keywords: list[str]) -> tuple[bool, Optional[str]]:
    text = f"{listing.title} {listing.description}".lower()
    for kw in damage_keywords:
        if kw.lower() in text:
            return True, kw
    return False, None


def estimate_market_value(
    all_listings_same_model: list[Listing],
    exclude: Listing,
    min_comparables: int,
) -> tuple[Optional[float], int]:
    """
    Szacuje wartość rynkową sprawnego egzemplarza jako medianę cen SPRAWNYCH
    ogłoszeń tego samego modelu (z pominięciem badanego ogłoszenia).
    Zwraca (wartość_rynkowa, liczba_ofert_użytych_do_wyliczenia).
    """
    comparable_prices = [
        l.price_pln
        for l in all_listings_same_model
        if l.unique_key != exclude.unique_key and not l.is_damaged
    ]
    if len(comparable_prices) < min_comparables:
        return None, len(comparable_prices)
    return statistics.median(comparable_prices), len(comparable_prices)


def find_repair_part_query(listing: Listing, damage_to_part_query: dict) -> Optional[str]:
    if not listing.detected_damage:
        return None
    text = f"{listing.title} {listing.description}".lower()
    for damage_fragment, part_query_template in damage_to_part_query.items():
        if damage_fragment.lower() in text:
            return part_query_template.format(model=listing.phone_model)
    return None


def calculate_profit(
    listing: Listing,
    market_value_pln: float,
    repair_part_cost_pln: float,
    safety_margin_pln: float,
) -> float:
    """
    zysk = wartość_rynkowa - cena_zakupu - koszt_części - margines_bezpieczeństwa
    (Praca własna przy naprawie nie jest wyceniana pieniężnie - użytkownik naprawia sam.)
    """
    return market_value_pln - listing.price_pln - repair_part_cost_pln - safety_margin_pln


def build_opportunity_if_profitable(
    listing: Listing,
    market_value_pln: Optional[float],
    comparables_count: int,
    repair_part_query: Optional[str],
    repair_part_cost_pln: float,
    min_profit_pln: float,
    safety_margin_pln: float,
) -> Optional[Opportunity]:
    if market_value_pln is None:
        return None

    profit = calculate_profit(listing, market_value_pln, repair_part_cost_pln, safety_margin_pln)
    if profit < min_profit_pln:
        return None

    return Opportunity(
        listing=listing,
        market_value_pln=market_value_pln,
        repair_part_query=repair_part_query,
        repair_part_cost_pln=repair_part_cost_pln,
        estimated_profit_pln=profit,
        comparables_count=comparables_count,
    )
