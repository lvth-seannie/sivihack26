"""Small fixed lookup of German city coordinates + haversine distance.

Companies are headquartered in different regions (Augsburg, Plauen,
Hamburg), so "distance" has to be computed per company/tender pair rather
than baked into the tender row. This is a bounded, deterministic lookup
table for the cities used in this dataset - not a geocoding service.
"""

from math import asin, cos, radians, sin, sqrt
from typing import Optional

EARTH_RADIUS_KM = 6371

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


def distance_km(city_a: str, city_b: str) -> Optional[float]:
    """Great-circle distance between two known cities, or None if either
    city isn't in the lookup table (callers should treat that as "unknown",
    not "zero" - rule 1 is skipped rather than wrongly passing/failing)."""

    a = CITY_COORDS.get(city_a)
    b = CITY_COORDS.get(city_b)
    if a is None or b is None:
        return None

    lat1, lon1, lat2, lon2 = map(radians, [a[0], a[1], b[0], b[1]])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return round(2 * EARTH_RADIUS_KM * asin(sqrt(h)), 1)
