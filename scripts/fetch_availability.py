#!/usr/bin/env python3
"""
Busca a disponibilidade pública de anúncios do Airbnb e calcula a ocupação
(dias reservados/bloqueados) das próximas 12 semanas.

Fonte dos dados: o próprio HTML da página do anúncio (o Airbnb embute o
calendário de disponibilidade em um bloco <script> na renderização inicial
da página). Isso não é uma API oficial — é o mesmo dado que qualquer
visitante vê ao abrir o anúncio no navegador. O layout pode mudar sem aviso;
o script foi escrito para falhar de forma clara (status "error") quando isso
acontecer, em vez de travar o job inteiro.

Uso:
    python scripts/fetch_availability.py
Lê:   listings.json  (lista de anúncios a monitorar)
Gera: data/occupancy.json
"""

import json
import os
import re
import sys
import time
import datetime

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

WEEKS = 12
DAYS = WEEKS * 7
REQUEST_TIMEOUT = 25
DELAY_BETWEEN_REQUESTS_SEC = 4  # evita bater rápido demais no servidor do Airbnb

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LISTINGS_PATH = os.path.join(BASE_DIR, "listings.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "occupancy.json")
DEBUG_DIR = os.path.join(BASE_DIR, "debug")

BOT_BLOCK_SIGNS = [
    "just a moment",
    "cf-browser-verification",
    "captcha",
    "px-captcha",
    "datadome",
    "attention required",
    "unusual traffic from your computer",
    "access to this page has been denied",
    "please verify you are a human",
    "verifique que você é humano",
]


def looks_blocked(html_text: str) -> bool:
    lowered = html_text.lower()
    return any(sign in lowered for sign in BOT_BLOCK_SIGNS)


def save_debug_html(listing_id: str, html_text: str):
    """Salva o HTML bruto recebido para permitir depuração manual depois."""
    try:
        os.makedirs(DEBUG_DIR, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        path = os.path.join(DEBUG_DIR, f"{listing_id or 'unknown'}_{ts}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html_text)
        print(f"  HTML de depuração salvo em: {path}")
    except OSError as e:
        print(f"  não consegui salvar HTML de depuração: {e}")


def extract_listing_id(url: str):
    m = re.search(r"/rooms/(\d+)", url)
    return m.group(1) if m else None


def find_calendar_days(obj, found):
    """Busca recursiva por objetos de dia de calendário dentro do JSON embutido na página."""
    if isinstance(obj, dict):
        if "calendarDate" in obj and (
            "available" in obj or "availableForCheckin" in obj
        ):
            found.append(obj)
        for v in obj.values():
            find_calendar_days(v, found)
    elif isinstance(obj, list):
        for v in obj:
            find_calendar_days(v, found)


def fetch_listing_availability(url: str):
    listing_id = extract_listing_id(url)
    if not listing_id:
        return {
            "status": "error",
            "error": "URL inválida: não encontrei o padrão /rooms/{id} no link.",
        }

    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as e:
        return {"status": "error", "error": f"Falha na requisição: {e}"}

    if resp.status_code != 200:
        save_debug_html(listing_id, resp.text)
        return {
            "status": "error",
            "error": (
                f"HTTP {resp.status_code} ao acessar o anúncio (pode ser bloqueio "
                "anti-bot). HTML salvo em debug/ para conferência."
            ),
        }

    soup = BeautifulSoup(resp.text, "html.parser")
    days_found = []
    for script in soup.find_all("script"):
        text = script.string
        if not text or "calendarDate" not in text:
            continue
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            continue
        find_calendar_days(data, days_found)

    if not days_found:
        save_debug_html(listing_id, resp.text)
        if looks_blocked(resp.text):
            error_msg = (
                "O acesso parece ter sido bloqueado por um sistema anti-bot "
                "(captcha/verificação). HTML salvo em debug/ para conferência."
            )
        else:
            error_msg = (
                "Não encontrei dados de calendário na página. O layout do "
                "Airbnb pode ter mudado, ou os dados agora só carregam via "
                "JavaScript no navegador (não vêm no HTML inicial). HTML salvo "
                "em debug/ para conferência."
            )
        return {"status": "error", "error": error_msg}

    by_date = {}
    for d in days_found:
        date_str = d.get("calendarDate")
        if not date_str or date_str in by_date:
            continue
        available = d.get("available")
        if available is None:
            available = d.get("availableForCheckin")
        by_date[date_str] = bool(available)

    today = datetime.date.today()
    daily = []
    booked_days = 0
    known_days = 0
    for i in range(DAYS):
        day = today + datetime.timedelta(days=i)
        key = day.isoformat()
        available = by_date.get(key)  # None = sem dado disponível
        if available is not None:
            known_days += 1
            if not available:
                booked_days += 1
        daily.append({"date": key, "available": available})

    weeks = []
    for w in range(WEEKS):
        week_days = daily[w * 7:(w + 1) * 7]
        w_known = sum(1 for d in week_days if d["available"] is not None)
        w_booked = sum(1 for d in week_days if d["available"] is False)
        weeks.append(
            {
                "week": w + 1,
                "start": week_days[0]["date"],
                "booked_days": w_booked,
                "known_days": w_known,
            }
        )

    return {
        "status": "ok",
        "listing_id": listing_id,
        "daily": daily,
        "weeks": weeks,
        "total_booked_days": booked_days,
        "total_known_days": known_days,
        "occupancy_rate": round(booked_days / known_days, 3) if known_days else None,
    }


def main():
    if not os.path.exists(LISTINGS_PATH):
        print(f"Arquivo {LISTINGS_PATH} não encontrado. Nada a fazer.")
        listings = []
    else:
        with open(LISTINGS_PATH, "r", encoding="utf-8") as f:
            listings = json.load(f)

    results = []
    for item in listings:
        url = item.get("url", "")
        nickname = item.get("nickname") or url
        print(f"Buscando: {nickname} -> {url}")
        info = fetch_listing_availability(url)
        info["id"] = item.get("id")
        info["url"] = url
        info["nickname"] = nickname
        info["updated_at"] = datetime.datetime.utcnow().isoformat() + "Z"
        results.append(info)
        if info["status"] != "ok":
            print(f"  aviso: {info.get('error')}")
        time.sleep(DELAY_BETWEEN_REQUESTS_SEC)

    output = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "weeks": WEEKS,
        "listings": results,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Concluído. {len(results)} anúncio(s) processado(s).")


if __name__ == "__main__":
    sys.exit(main())
