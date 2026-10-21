"""Scrape the Alaia Bay surf agenda (booking.alaiabay.ch) into JSON.

The booking site (Wave7) has no JSON API. The agenda page fills itself with a
POST to index.php?do=displayActivityAgenda, which returns an HTML fragment.
This script replays that call with a session cookie and parses the fragment.

Usage:
    python3 scrape_agenda.py              # current week
    python3 scrape_agenda.py --weeks 3    # current week + next 2
"""

import argparse
import html
import http.cookiejar
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

BASE = "https://booking.alaiabay.ch"
TZ = ZoneInfo("Europe/Zurich")
WAVES = {"1": "Left", "2": "Right"}

# One timeslot cell: class carries "<unix start>_<wave>", the onclick carries
# the timeslot id, the tooltip carries time range / price category / level,
# and the inner span shows "X" when the slot is full.
CELL_RE = re.compile(
    r'class="[^"]*booking-agenda-clickable_(\d+)_(\d+)([^"]*)"'
    r'.*?background\s*:\s*(#[0-9A-Fa-f]{3,6})'
    r".*?modalBookingVoucherActivity\('(\d+)'"
    r'.*?data-original-title="([^"]*)"'
    r'.*?<span class="default_display">(.*?)</span>',
    re.S,
)
TOOLTIP_RE = re.compile(r"<b>([^<]+?)\s*:</b>\s*([^<]*)")

# Booking popup for one slot: a hidden input with the places left, then one
# "row-catalog" block per bookable product (name in <strong>, price in .cart-title).
ENTRIES_LEFT_RE = re.compile(r'nb_entries_left"\s+value="(\d+)"')
PRODUCT_RE = re.compile(
    r'id="row-catalog-\d+".*?<strong[^>]*>\s*([^<]+?)\s*</strong>'
    r'.*?class="cart-title">\s*CHF\s*([\d\',.]+)',
    re.S,
)


def make_opener():
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    opener.addheaders = [("User-Agent", "Mozilla/5.0 (agenda-scraper)")]
    # Opening the page creates the session; setLang makes tooltips English.
    opener.open(f"{BASE}/index.php?ctrl=do&do=setLang&lang=en&goto=activity-agenda").read()
    return opener


def post(opener, **data):
    body = urllib.parse.urlencode({"ctrl": "do", **data}).encode()
    with opener.open(f"{BASE}/index.php", body) as r:
        return r.read().decode("utf-8", "replace")


def monday_ts(dt):
    monday = (dt - timedelta(days=dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return int(monday.timestamp())


def to_24h(value):
    value = value.strip()
    for fmt in ("%I:%M %p", "%H:%M"):
        try:
            return datetime.strptime(value, fmt).strftime("%H:%M")
        except ValueError:
            pass
    return value


def parse_tooltip(raw):
    fields = dict(TOOLTIP_RE.findall(html.unescape(raw)))
    # Keys differ by language ("From"/"De", "Session level"/"Niveau de la session"),
    # so match by position-independent keywords.
    out = {}
    for key, value in fields.items():
        k = key.lower()
        if "price" in k or "prix" in k:
            out["price_category"] = value.strip()
        elif "level" in k or "niveau" in k:
            out["level"] = value.strip()
        elif k in ("to", "a", "à"):
            out["end"] = to_24h(value)
        elif k in ("from", "de"):
            out["start"] = value.strip().rstrip("-").strip()
    return out


def parse_agenda(fragment):
    slots = []
    for ts, wave, extra_cls, color, slot_id, tooltip, display in CELL_RE.findall(fragment):
        start = datetime.fromtimestamp(int(ts), TZ)
        info = parse_tooltip(tooltip)
        slots.append({
            "timeslot_id": int(slot_id),
            "date": start.date().isoformat(),
            "start": start.strftime("%H:%M"),
            "end": info.get("end"),
            "wave": WAVES.get(wave, wave),
            "level": info.get("level"),
            "price_category": info.get("price_category"),
            "level_color": color,
            "sold_out": "X" in display,
            "past": "expired_timeslot" in extra_cls,
        })
    return slots


def add_details(opener, slot):
    """Open the slot's booking popup to read places left and product prices."""
    fragment = post(opener, do="modalBookingVoucherActivity", init_cart=0,
                    timeslot_id=slot["timeslot_id"], nb_levels=15)
    left = ENTRIES_LEFT_RE.search(fragment)
    slot["places_left"] = int(left.group(1)) if left else 0
    slot["products"] = [
        {"name": html.unescape(name), "price_chf": float(price.replace("'", "").replace(",", "."))}
        for name, price in PRODUCT_RE.findall(fragment)
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weeks", type=int, default=1)
    ap.add_argument("--activity", default="surf_wave")
    ap.add_argument("--details", action="store_true",
                    help="also open each upcoming slot for places left and prices (1 request per slot)")
    args = ap.parse_args()

    opener = make_opener()
    week_start = datetime.now(TZ)
    slots = []
    for i in range(args.weeks):
        start = monday_ts(week_start + timedelta(weeks=i))
        post(opener, do="setAgendaDates", activity_type=args.activity, start=start)
        slots += parse_agenda(post(opener, do="displayActivityAgenda", activity_type=args.activity))
        time.sleep(1)  # be polite

    if args.details:
        for slot in slots:
            if slot["past"] or slot["sold_out"]:
                slot["places_left"], slot["products"] = 0, []
                continue
            add_details(opener, slot)
            time.sleep(0.4)

    slots.sort(key=lambda s: (s["date"], s["start"], s["wave"]))
    json.dump(slots, sys.stdout, indent=2, ensure_ascii=False)
    print(f"\n{len(slots)} slots", file=sys.stderr)


if __name__ == "__main__":
    main()
