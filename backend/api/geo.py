"""Geocoding + distance helpers.

`haversine_km()` is pure math over coordinates already stored on the
Company/Tender rows - this is what runs at evaluation time (see
services.py), never a network call.

`geocode()` is for the one-time `backfill_coordinates` management command
only - never called from the request path. It checks a small fast-path
dict for cities we already know precisely, then falls back to Nominatim
(OpenStreetMap's free geocoder, no API key) for everything else, one
request at a time, respecting Nominatim's usage policy (max 1 req/sec,
a descriptive User-Agent). Results are meant to be cached to the DB
immediately by the caller.
"""

import time
from math import asin, cos, radians, sin, sqrt
from typing import Optional, Tuple

import requests

EARTH_RADIUS_KM = 6371

# Fast path: cities we've already verified precisely, so the backfill
# command doesn't spend a Nominatim call (or its 1-req/sec budget) on them.
CITY_COORDS = {
    "Augsburg": (48.3705, 10.8978),
    "Königsbrunn": (48.2739, 10.8956),
    "Gersthofen": (48.4231, 10.8683),
    "Neusäß": (48.4147, 10.8393),
    "Friedberg": (48.3653, 10.9866),
    "Rosenheim": (47.8564, 12.1289),
    "Kempten": (47.7267, 10.3172),
    "Plauen": (50.4948, 12.1382),
    "Zwickau": (50.7213, 12.4939),
    "Gera": (50.8802, 12.0813),
    "Chemnitz": (50.8278, 12.9214),
    "Hof": (50.3125, 11.9192),
    "Hamburg": (53.5511, 9.9937),
    "Bremen": (53.0793, 8.8017),
    "Hannover": (52.3759, 9.7320),
    "Lübeck": (53.8655, 10.6866),
}

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_USER_AGENT = "SiviHack26-TenderScreening/1.0 (hackathon project; contact via GitHub repo)"
NOMINATIM_DELAY_SECONDS = 1.1


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
    return round(2 * EARTH_RADIUS_KM * asin(sqrt(h)), 1)


def geocode(place: str) -> Optional[Tuple[float, float]]:
    """One-time lookup for backfill_coordinates - do not call at request
    time. Returns (lat, lng), or None if the place couldn't be resolved."""

    if not place:
        return None
    if place in CITY_COORDS:
        return CITY_COORDS[place]

    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": place, "countrycodes": "de", "format": "json", "limit": 1},
            headers={"User-Agent": NOMINATIM_USER_AGENT},
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json()
    except (requests.RequestException, ValueError):
        results = None
    finally:
        time.sleep(NOMINATIM_DELAY_SECONDS)

    if not results:
        return None
    try:
        return (float(results[0]["lat"]), float(results[0]["lon"]))
    except (KeyError, IndexError, ValueError, TypeError):
        return None
