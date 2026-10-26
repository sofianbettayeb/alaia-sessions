"""Fetch the MeteoSwiss local forecast for Sion (Alaïa Bay) into JSON.

MeteoSwiss open data publishes the forecast behind its app as one CSV per
parameter per hourly run, covering every Swiss postal code for 8 days:
https://opendatadocs.meteoswiss.ch/e-forecast-data/e4-local-forecast-data

Hourly files are about 30 MB and sorted by time, so each one is streamed and
only the Sion rows are kept.

Usage:
    python3 fetch_forecast.py > forecast.json
"""

import csv
import io
import json
import sys
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

STAC = "https://data.geo.admin.ch/api/stac/v1/collections/ch.meteoschweiz.ogd-local-forecasting"
TZ = ZoneInfo("Europe/Zurich")
# Postal code 1950 Sion, the point the MeteoSwiss app uses for that code.
POINT_ID, POINT_TYPE = "195000", "2"
POINT_NAME = "Sion (1950)"

# Daily values for the local day (00:00 to 24:00 Swiss time).
DAILY = {"jp2000d0": "icon", "tre200px": "tmax", "tre200pn": "tmin", "rka150p0": "rain_mm"}
# Hourly values; the timestamp marks the end of the hour (or 3 hours) it covers.
HOURLY = {"tre200h0": "temp", "jww003i0": "icon", "rp0003i0": "rain_pct", "fu3010h0": "wind"}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "alaia-sessions (forecast)"})
    return urllib.request.urlopen(req, timeout=120)


def latest_run():
    """Newest run whose files for every parameter we need are published."""
    with get(f"{STAC}/items?limit=100") as r:
        items = json.load(r)["features"]
    for item in sorted(items, key=lambda f: f["id"], reverse=True):
        runs = {}
        for name, asset in item["assets"].items():
            _, _, run, param, _ = name.split(".")
            runs.setdefault(run, {})[param] = asset["href"]
        for run in sorted(runs, reverse=True):
            if all(p in runs[run] for p in (*DAILY, *HOURLY)):
                return run, runs[run]
    raise RuntimeError("no complete forecast run found")


def rows(url, param):
    """Yield (UTC datetime, value) for Sion from one parameter file."""
    with get(url) as r:
        for row in csv.DictReader(io.TextIOWrapper(r, encoding="latin-1"), delimiter=";"):
            if row["point_id"] == POINT_ID and row["point_type_id"] == POINT_TYPE and row[param] != "":
                yield datetime.strptime(row["Date"], "%Y%m%d%H%M").replace(tzinfo=timezone.utc), float(row[param])


def main():
    run, hrefs = latest_run()

    days = {}
    for param, key in DAILY.items():
        for when, value in rows(hrefs[param], param):
            # Daily "local day" values are stamped at 00:00 of that day.
            days.setdefault(when.strftime("%Y-%m-%d"), {})[key] = value

    hours = {}
    for param, key in HOURLY.items():
        for when, value in rows(hrefs[param], param):
            hours.setdefault(when.astimezone(TZ).strftime("%Y-%m-%dT%H"), {})[key] = value

    for d in (*days.values(), *hours.values()):
        for k in ("icon", "rain_pct", "wind"):
            if k in d:
                d[k] = int(d[k])

    issued = datetime.strptime(run, "%Y%m%d%H%M").replace(tzinfo=timezone.utc).astimezone(TZ)
    out = {
        "source": "MeteoSwiss",
        "point": POINT_NAME,
        "issued": issued.isoformat(timespec="minutes"),
        "days": [{"date": d, **v} for d, v in sorted(days.items())],
        "hours": dict(sorted(hours.items())),
    }
    json.dump(out, sys.stdout, indent=1, ensure_ascii=False)
    print(f"\nforecast run {run}: {len(days)} days, {len(hours)} hours", file=sys.stderr)


if __name__ == "__main__":
    main()
