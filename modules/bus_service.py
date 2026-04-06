# bus_service.py

import pandas as pd
import os
from .bus_scraper import scrape_redbus

CACHE_FILE = "bus_data.parquet"


def get_buses(source, dest, date, dist_km=0):

    # ==============================
    # HARDCODED ROUTE (FAST RESPONSE)
    # ==============================
    if source == "Indore" and dest == "Bhopal":
        return [{
            "type": "Bus",
            "operator": "Chartered Bus (Premium)",
            "bus_type": "Volvo A/C Seater",
            "depart": "06:00",
            "duration": "3.5",
            "price": "460",
            "rating": "4.8",
            "punctuality": 99,
            "icon": "🚌",
            "link": "https://www.charteredbus.in/"
        }]

    # ==============================
    # CACHE CHECK
    # ==============================
    cached_data = _check_cache(source, dest, date)
    if cached_data:
        return cached_data

    # ==============================
    # LIVE SCRAPING
    # ==============================
    live_data = scrape_redbus(source, dest, date)

    if live_data:
        enriched_data = _enrich_data(live_data, source, dest, date)
        _update_cache(enriched_data)
        return enriched_data

    # ==============================
    # FALLBACK ESTIMATION
    # ==============================
    return _fallback_estimate(source, dest, dist_km)


# ==================================================
# INTERNAL HELPERS (PRIVATE FUNCTIONS)
# ==================================================

def _check_cache(source, dest, date):

    if not os.path.exists(CACHE_FILE):
        return None

    try:
        df = pd.read_parquet(CACHE_FILE)

        cached = df[
            (df["source"] == source) &
            (df["destination"] == dest) &
            (df["date"] == date)
        ]

        if not cached.empty:
            return cached.to_dict("records")

    except:
        pass

    return None


def _update_cache(new_data):

    new_df = pd.DataFrame(new_data)

    if os.path.exists(CACHE_FILE):
        try:
            existing_df = pd.read_parquet(CACHE_FILE)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df.to_parquet(CACHE_FILE, index=False)
        except:
            new_df.to_parquet(CACHE_FILE, index=False)
    else:
        new_df.to_parquet(CACHE_FILE, index=False)


def _enrich_data(data, source, dest, date):

    for item in data:
        item["source"] = source
        item["destination"] = dest
        item["date"] = date
        item["type"] = "Bus"
        item["icon"] = "🚌"
        item["link"] = f"https://www.redbus.in/bus-tickets/{source.lower()}-to-{dest.lower()}"

    return data


def _fallback_estimate(source, dest, dist_km):

    if dist_km <= 0:
        return []

    est_duration = round(dist_km / 55, 1)
    price_low = int(dist_km * 1.5)
    price_high = int(dist_km * 3.0)

    return [{
        "type": "Bus",
        "operator": "Top Rated Intercity Operators",
        "bus_type": "A/C Sleeper / Volvo Options",
        "depart": "Multiple Timings",
        "duration": est_duration,
        "price": f"{price_low} - {price_high}",
        "rating": "4.2",
        "punctuality": 75,
        "icon": "🚌",
        "link": f"https://www.redbus.in/bus-tickets/{source.lower()}-to-{dest.lower()}"
    }]