"""Wykrywanie uszkodzeń w ogłoszeniu, szacowanie wartości rynkowej i zysku."""
import re
import statistics
from typing import Optional

from models import Listing, Opportunity

# Warianty, które ROZRÓŻNIAJĄ modele (np. S24 to nie to samo co S24 Ultra,
# iPhone 14 Pro to nie to samo co 14 Pro Max). Używane do weryfikacji, czy
# znalezione ogłoszenie faktycznie dotyczy dokładnie szukanego modelu.
_KNOWN_VARIANT_TOKENS = {"ultra", "plus", "pro", "max", "fe", "edge", "air"}
_TOKEN_RE = re.compile(r"[a-ząćęłńóśźż]+|\d+", re.IGNORECASE)


def _tokenize(text: str) -> set[str]:
    text = text.lower().replace("+", " plus ")
    return set(_TOKEN_RE.findall(text))


def listing_matches_model(listing: Listing, model_name: str) -> bool:
    """
    Sprawdza, czy ogłoszenie NA PEWNO dotyczy dokładnie szukanego modelu, a nie
    podobnie nazwanego innego telefonu (np. S21 FE zwrócone przy szukaniu S26 FE,
    albo "14 Pro Max" zwrócone przy szukaniu "14 Pro"). Wyszukiwarki portali robią
    "luźne" dopasowanie i potrafią zwrócić niepowiązane, podobne modele.
    """
    name_tokens = _tokenize(model_name)
    title_tokens = _tokenize(f"{listing.title} {listing.description}")

    # Wszystkie słowa/cyfry z nazwy modelu (np. "samsung","galaxy","s","24","ultra")
    # muszą pojawić się w tytule/opisie ogłoszenia.
    if not name_tokens.issubset(title_tokens):
        return False

    # Warianty NIE należące do szukanego modelu nie mogą występować w ogłoszeniu
    # (np. szukając "S24" odrzucamy ogłoszenia zawierające "ultra"/"plus"/"fe").
    forbidden = _KNOWN_VARIANT_TOKENS - name_tokens
    if forbidden & title_tokens:
        return False

    return True


def is_excluded_listing(listing: Listing, exclude_keywords: list[str], min_price_pln: float) -> bool:
    """
    Zwraca True, jeśli ogłoszenie należy całkowicie pominąć (nie jest prawdziwym
    telefonem - to akcesorium, atrapa, część, albo cena jest nierealnie niska).
    Wywoływać PRZED wykrywaniem uszkodzeń i PRZED liczeniem wartości rynkowej,
    żeby takie ogłoszenia nie zaniżały mediany cen dla danego modelu.
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
