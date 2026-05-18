import os
import re
import httpx
from datetime import datetime, date, timedelta
from typing import List, Optional
from pathlib import Path
from icalendar import Calendar
import json

ICAL_URLS = {
    "farol_barra_flat_214": os.getenv(
        "ICAL_FAROL_BARRA",
        "https://www.airbnb.com.br/calendar/ical/41662018.ics",
    ),
    "ondina_apt_hotel_441": os.getenv(
        "ICAL_ONDINA",
        "https://www.airbnb.com.br/calendar/ical/986288391373272410.ics",
    ),
    "the_plaza_407": os.getenv(
        "ICAL_THE_PLAZA",
        "https://www.airbnb.com.br/calendar/ical/1544328946353777106.ics",
    ),
    "smart_convencoes_509": os.getenv(
        "ICAL_SMART",
        "https://www.airbnb.com.br/calendar/ical/1320242268460204756.ics",
    ),
}

CACHE_DIR = Path(__file__).parent.parent / "data" / "ical"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class ICalSync:
    @staticmethod
    async def fetch_ical(url: str) -> Optional[str]:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.get(url)
                if r.status_code == 200:
                    return r.text
                print(f"[iCal] Erro HTTP {r.status_code} ao buscar {url}")
                return None
        except Exception as e:
            print(f"[iCal] Erro ao buscar {url}: {e}")
            return None

    @staticmethod
    def parse_ical(ical_text: str) -> List[date]:
        blocked_dates = []
        try:
            cal = Calendar.from_ical(ical_text)
            for component in cal.walk():
                if component.name == "VEVENT":
                    dtstart = component.get("DTSTART").dt
                    dtend = component.get("DTEND").dt
                    if isinstance(dtstart, date) and isinstance(dtend, date):
                        current = dtstart
                        while current < dtend:
                            blocked_dates.append(current)
                            current += timedelta(days=1)
        except Exception as e:
            print(f"[iCal] Erro ao processar ICS: {e}")
        return blocked_dates

    @staticmethod
    def cache_file(prop_key: str) -> Path:
        return CACHE_DIR / f"{prop_key}.json"

    @staticmethod
    def load_cache(prop_key: str) -> List[str]:
        path = ICalSync.cache_file(prop_key)
        if path.exists():
            with open(path, "r") as f:
                return json.load(f)
        return []

    @staticmethod
    def save_cache(prop_key: str, dates_iso: List[str]):
        path = ICalSync.cache_file(prop_key)
        with open(path, "w") as f:
            json.dump(dates_iso, f)

    @staticmethod
    def is_blocked(prop_key: str, check_date: date) -> bool:
        cached = ICalSync.load_cache(prop_key)
        return check_date.isoformat() in cached

    @staticmethod
    async def sync_all():
        results = {}
        for prop_key, url in ICAL_URLS.items():
            if url:
                ical_text = await ICalSync.fetch_ical(url)
                if ical_text:
                    blocked = ICalSync.parse_ical(ical_text)
                    blocked_iso = [d.isoformat() for d in blocked]
                    ICalSync.save_cache(prop_key, blocked_iso)
                    results[prop_key] = {
                        "status": "ok",
                        "blocked_dates": len(blocked_iso),
                    }
                else:
                    results[prop_key] = {"status": "erro", "blocked_dates": 0}
            else:
                results[prop_key] = {"status": "sem_url", "blocked_dates": 0}
        return results

    @staticmethod
    def get_blocked_dates(prop_key: str, start: date, end: date) -> List[date]:
        cached = ICalSync.load_cache(prop_key)
        blocked = []
        for d_iso in cached:
            d = date.fromisoformat(d_iso)
            if start <= d < end:
                blocked.append(d)
        return blocked
