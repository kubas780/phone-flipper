"""
Trwałe przechowywanie ID ogłoszeń, o których użytkownik już został powiadomiony,
żeby przy każdym kolejnym uruchomieniu nie wysyłać tych samych okazji ponownie.

Plik seen_listings.json jest commitowany z powrotem do repozytorium przez
workflow GitHub Actions (patrz .github/workflows/scan.yml) - dzięki temu stan
przechowuje się między uruchomieniami mimo że każde uruchomienie startuje
w świeżym, tymczasowym środowisku.
"""
import json
import os
from datetime import datetime, timedelta

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "seen_listings.json")
# Ile dni trzymać wpis w historii, zanim zostanie wyczyszczony (żeby plik nie rósł w nieskończoność)
RETENTION_DAYS = 30


def load_seen() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_seen(seen: dict) -> None:
    cutoff = datetime.utcnow() - timedelta(days=RETENTION_DAYS)
    pruned = {
        key: ts for key, ts in seen.items()
        if datetime.fromisoformat(ts) > cutoff
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(pruned, f, ensure_ascii=False, indent=2)


def filter_new(seen: dict, unique_keys: list[str]) -> list[str]:
    return [k for k in unique_keys if k not in seen]


def mark_seen(seen: dict, unique_keys: list[str]) -> None:
    now = datetime.utcnow().isoformat()
    for k in unique_keys:
        seen[k] = now
