# Alaïa Bay sessions (unofficial)

An unofficial, easier-to-read view of the [Alaïa Bay](https://booking.alaiabay.ch/activity-agenda) surf session calendar. It is not made, run or endorsed by Alaïa Bay. Always confirm and book on the official booking site.

It shows each session's level, how booked it is and its price, and ranks the best sessions for your levels. Your settings stay in your own browser.

## How it works

- `scrape_agenda.py` reads the public agenda and each slot's booking popup (places left, prices) and writes `agenda.json`.
- `fetch_forecast.py` reads the [MeteoSwiss open data](https://opendatadocs.meteoswiss.ch/e-forecast-data/e4-local-forecast-data) local forecast for Sion (postal code 1950), the same forecast the MeteoSwiss app shows, and writes `forecast.json`: 1 summary per day plus hourly temperature, rain chance and wind.
- `build_view.py` turns `agenda.json`, `forecast.json` and `view_template.html` into `index.html`. Each session shows the forecast for its hour, and "Best weather" ranks sessions by it.
- A GitHub Actions workflow (`.github/workflows/refresh.yml`) reruns all 3 around 07:00, 12:00 and 17:00 Swiss time and commits the result. GitHub Pages serves `index.html`.

"Booked" is an estimate: capacity is taken as the most places ever seen free for a level, with a minimum of 12.

## Run it locally

```bash
python3 serve.py
```

Then open http://localhost:4322/. Locally the page has a "Refresh data" button that reruns the scraper and the forecast (about 1 minute).
