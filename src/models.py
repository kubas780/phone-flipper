"""Wspólne struktury danych używane w całym projekcie."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Listing:
    """Pojedyncze ogłoszenie znalezione na jednym z portali."""
    source: str            # "allegro" | "allegro_lokalnie" | "olx" | "vinted"
    listing_id: str        # unikalne ID w ramach źródła (do deduplikacji)
    title: str
    price_pln: float
    url: str
    phone_model: str       # nazwa modelu z config.yaml, do którego dopasowano
    description: str = ""
    is_damaged: bool = False
    detected_damage: Optional[str] = None  # np. "wyświetlacz", "bateria"

    @property
    def unique_key(self) -> str:
        return f"{self.source}:{self.listing_id}"


@dataclass
class Opportunity:
    """Wynik analizy - okazja spełniająca próg zysku."""
    listing: Listing
    market_value_pln: float
    repair_part_query: Optional[str]
    repair_part_cost_pln: float
    estimated_profit_pln: float
    comparables_count: int
