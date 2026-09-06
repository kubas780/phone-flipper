"""Wysyłanie powiadomień push na telefon przez Telegram Bota."""
import requests

from models import Opportunity


def send_telegram_message(bot_token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    resp = requests.post(
        url,
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=20,
    )
    resp.raise_for_status()


def format_opportunity_message(opp: Opportunity) -> str:
    l = opp.listing
    lines = [
        f"💰 <b>OKAZJA: {l.phone_model}</b>",
        f"Źródło: {l.source}",
        f"Cena ogłoszenia: {l.price_pln:.0f} zł",
        f"Szacowana wartość rynkowa (sprawny): {opp.market_value_pln:.0f} zł "
        f"(na podstawie {opp.comparables_count} ofert)",
    ]
    if opp.repair_part_query:
        lines.append(
            f"Uszkodzenie: {l.detected_damage} → część: \"{opp.repair_part_query}\" "
            f"(~{opp.repair_part_cost_pln:.0f} zł)"
        )
    lines.append(f"<b>Szacowany zysk: {opp.estimated_profit_pln:.0f} zł</b>")
    lines.append(f"🔗 {l.url}")
    return "\n".join(lines)


def notify_opportunities(bot_token: str, chat_id: str, opportunities: list[Opportunity]) -> None:
    for opp in opportunities:
        try:
            send_telegram_message(bot_token, chat_id, format_opportunity_message(opp))
        except requests.RequestException as e:
            print(f"[notifier] Błąd wysyłki powiadomienia dla {opp.listing.url}: {e}")
