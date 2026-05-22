"""
Ticketmaster Discovery API → SQLite pipeline.

Fetches upcoming Chicago events, cleans them with pandas,
and upserts into the events table. Falls back gracefully
if TICKETMASTER_API_KEY is not set.
"""
import json
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict

import requests
import pandas as pd

logger = logging.getLogger(__name__)

API_KEY = os.getenv("TICKETMASTER_API_KEY", "")
BASE_URL = "https://app.ticketmaster.com/discovery/v2/events.json"
DAYS_AHEAD = 30

# Chicago zip code → neighborhood mapping
_ZIP_TO_HOOD: Dict[str, str] = {
    "60601": "The Loop",    "60602": "The Loop",    "60603": "The Loop",
    "60604": "The Loop",    "60605": "South Loop",  "60606": "The Loop",
    "60607": "West Loop",   "60608": "Pilsen",      "60609": "Bridgeport",
    "60610": "Old Town",    "60611": "Streeterville","60612": "East Garfield Park",
    "60613": "Lakeview",    "60614": "Lincoln Park","60615": "Hyde Park",
    "60616": "Chinatown",   "60617": "South Chicago","60618": "Irving Park",
    "60619": "Chatham",     "60620": "Auburn Gresham","60621": "Englewood",
    "60622": "Wicker Park", "60623": "Little Village","60624": "Garfield Park",
    "60625": "Albany Park", "60626": "Rogers Park", "60628": "Roseland",
    "60630": "Jefferson Park","60631": "Norwood Park","60634": "Belmont Cragin",
    "60636": "West Englewood","60637": "Woodlawn",  "60638": "Garfield Ridge",
    "60640": "Uptown",      "60641": "Hermosa",     "60642": "River North",
    "60643": "Morgan Park", "60644": "Austin",      "60645": "West Ridge",
    "60647": "Logan Square","60649": "South Shore", "60651": "Humboldt Park",
    "60653": "Bronzeville",  "60654": "River North","60657": "Lakeview",
    "60660": "Edgewater",   "60661": "West Loop",
}

# Ticketmaster segment names → our categories
_CATEGORY_MAP = {
    "Music": "live_music",
    "Sports": "sports",
    "Arts & Theatre": "arts",
    "Film": "arts",
    "Miscellaneous": "other",
    "Undefined": "other",
}


def _infer_neighborhood(venue: dict) -> str:
    zip_code = (venue.get("postalCode") or "")[:5]
    if zip_code in _ZIP_TO_HOOD:
        return _ZIP_TO_HOOD[zip_code]
    name = (venue.get("name") or "").lower()
    if "wrigley" in name:
        return "Lakeview"
    if "united center" in name:
        return "West Loop"
    if "soldier field" in name or "grant park" in name or "millennium" in name:
        return "The Loop"
    if "navy pier" in name:
        return "Streeterville"
    if "thalia hall" in name:
        return "Pilsen"
    if "empty bottle" in name:
        return "Wicker Park"
    return "Chicago"


def _parse_raw_events(raw: list) -> pd.DataFrame:
    rows = []
    for e in raw:
        try:
            venue = (e.get("_embedded") or {}).get("venues", [{}])[0]
            prices = e.get("priceRanges") or [{}]
            classifications = (e.get("classifications") or [{}])[0]
            segment = (classifications.get("segment") or {}).get("name", "")
            genre = (classifications.get("genre") or {}).get("name", "")
            images = e.get("images") or []
            image_url = next(
                (img["url"] for img in images if img.get("ratio") == "16_9"), ""
            )

            rows.append({
                "id":            e.get("id", ""),
                "name":          (e.get("name") or "").strip(),
                "category":      _CATEGORY_MAP.get(segment, "other"),
                "subcategory":   genre.lower(),
                "venue_name":    (venue.get("name") or "").strip(),
                "venue_address": (venue.get("address") or {}).get("line1", ""),
                "neighborhood":  _infer_neighborhood(venue),
                "latitude":      float((venue.get("location") or {}).get("latitude") or 0),
                "longitude":     float((venue.get("location") or {}).get("longitude") or 0),
                "event_date":    (e.get("dates") or {}).get("start", {}).get("localDate", ""),
                "event_time":    (e.get("dates") or {}).get("start", {}).get("localTime", ""),
                "price_min":     float((prices[0] if prices else {}).get("min") or 0),
                "price_max":     float((prices[0] if prices else {}).get("max") or 0),
                "url":           e.get("url", ""),
                "image_url":     image_url,
                "tags":          json.dumps(
                    [t for t in [segment.lower(), genre.lower()] if t]
                ),
            })
        except Exception as exc:
            logger.warning("Skipping malformed event %s: %s", e.get("id"), exc)
    return pd.DataFrame(rows)


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    # Drop rows missing required fields
    df = df.dropna(subset=["id", "name"])
    df = df[df["id"].str.len() > 0]
    df = df[df["name"].str.len() > 0]

    # Parse and validate dates
    df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df = df[df["event_date"].notna()]

    # Remove past events
    today = datetime.utcnow().strftime("%Y-%m-%d")
    df = df[df["event_date"] >= today]

    # Numeric clean
    df["price_min"] = pd.to_numeric(df["price_min"], errors="coerce").fillna(0).clip(lower=0)
    df["price_max"] = pd.to_numeric(df["price_max"], errors="coerce").fillna(0).clip(lower=0)

    # Deduplicate by id (keep most recent fetch if dupes somehow appear)
    df = df.drop_duplicates(subset=["id"])

    now = datetime.utcnow().isoformat()
    df["fetched_at"] = now
    df["source"] = "ticketmaster"

    return df.reset_index(drop=True)


def fetch_and_clean(days_ahead: int = DAYS_AHEAD) -> List[Dict]:
    """
    Fetch Chicago events from Ticketmaster, clean with pandas,
    return list of dicts ready for upsert_events().
    Returns empty list if API key not set.
    """
    if not API_KEY:
        logger.info("TICKETMASTER_API_KEY not set — skipping fetch")
        return []

    start = datetime.utcnow().strftime("%Y-%m-%dT00:00:00Z")
    end   = (datetime.utcnow() + timedelta(days=days_ahead)).strftime("%Y-%m-%dT23:59:59Z")

    raw_events: list = []
    page = 0
    while True:
        try:
            resp = requests.get(BASE_URL, params={
                "apikey":        API_KEY,
                "city":          "Chicago",
                "stateCode":     "IL",
                "startDateTime": start,
                "endDateTime":   end,
                "size":          200,
                "page":          page,
                "sort":          "date,asc",
            }, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.error("Ticketmaster API error page %d: %s", page, exc)
            break

        embedded = (data.get("_embedded") or {})
        events = embedded.get("events") or []
        raw_events.extend(events)

        page_info = data.get("page", {})
        total_pages = page_info.get("totalPages", 1)
        if page >= min(total_pages - 1, 4):   # cap at 5 pages / 1000 events
            break
        page += 1

    logger.info("Ticketmaster: fetched %d raw events", len(raw_events))

    df = _parse_raw_events(raw_events)
    df = _clean(df)

    logger.info("Ticketmaster: %d clean events after pipeline", len(df))
    return df.to_dict("records")
