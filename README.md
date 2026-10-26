# Alaïa Bay sessions (unofficial)

An unofficial, easier-to-read view of the [Alaïa Bay](https://booking.alaiabay.ch/activity-agenda) surf session calendar. It is not made, run or endorsed by Alaïa Bay. Always confirm and book on the official booking site.

Live page: https://sofianbettayeb.github.io/alaia-sessions/

## Before and after

**Before: the official agenda.** A colour-coded grid per wave, 1 week at a time. Each colour is a level (the legend is under the grid), an X means full. Places left and prices only appear when you click a slot.

![The official Alaïa Bay agenda on desktop](docs/screenshots/alaia-agenda-desktop.jpg)

**After: this view.** Your levels only, ranked by what matters to you, with places left, price and the weather for every session.

![This view on desktop](docs/screenshots/desktop.png)

**On a phone**

| Official agenda | This view |
|---|---|
| ![Official agenda on a phone](docs/screenshots/alaia-agenda-phone.jpg) | ![This view on a phone](docs/screenshots/phone.png) |

Both captured on 26 October 2026 with the same sessions. On a phone the official grid cuts off Sunday.

## What changes when you look for a session

### 1. Set your levels once

The official agenda shows every level by default: you match colours against the legend, or set its level filter. Here you pick your levels on the first visit (and Adult or Kid), and the page remembers them in your browser. Every other level is hidden from then on.

![First visit on a phone](docs/screenshots/first-visit-phone.png)

### 2. Sessions are ordered by what matters to you

The official agenda is a time grid: finding the quietest or cheapest session means opening slots one by one. Here "Sort by" ranks every session:

- **Fewest people:** least booked first, then cheapest.
- **Lowest price:** cheapest first, then least booked. On 26 October, for Advanced Cruiser and Advanced Turn, that put the 4 CHF 89 deal sessions of Sunday 1 November at the top.
- **Best weather:** lowest chance of rain, then warmest.

The top 3 are shown as cards, 1 per start time, and the full list below follows the same order. Preferred days (in Settings) always come first. Filters narrow it down by days, time of day and wave.

### 3. The weather is next to every session

An outdoor wave in October depends on the weather, and the official agenda has none. Without this page you check MeteoSwiss in another tab and match the hours yourself. Here each session shows the MeteoSwiss forecast for its hour: icon and temperature, plus a warning when rain is 30% likely or more, or the wind reaches 20 km/h. "Best weather" turns that into a ranking.

### 4. You see what the agenda keeps behind a click

The booking site's data holds more than the grid shows. For every session at once, this page shows:

- **Places left**, which the official site keeps in a hidden field of each slot's booking popup (its "Entries left" filter only hides slots below a number), and a crowd estimate built from it (Quiet, Moderate, Busy).
- **The price and session type** (Guided, Coached, Deal), which the official site only shows after a click, slot by slot. When a slot lists no price at all (its popup says "No products are available for this time slot!"), this page shows the usual price for that level, marked `~CHF`.
- **2 weeks at once**, instead of 1 week per page.

### 5. Booking still happens on Alaïa Bay

The booking site has no link to a single session: it picks the agenda week from a server-side session. So "Book" opens a panel that sums up the session, says which week of the agenda to open, and offers "Copy details" and "Open booking site".

![The booking panel](docs/screenshots/book-panel.png)

## How it works

- `scrape_agenda.py` replays the agenda's own requests and opens each slot's booking popup to read places left and prices. It writes `agenda.json`.
- `fetch_forecast.py` reads the [MeteoSwiss open data](https://opendatadocs.meteoswiss.ch/e-forecast-data/e4-local-forecast-data) local forecast for Sion (postal code 1950), the same forecast the MeteoSwiss app shows, and writes `forecast.json`.
- `build_view.py` turns `agenda.json`, `forecast.json` and `view_template.html` into `index.html`, a single static page.
- A GitHub Actions workflow (`.github/workflows/refresh.yml`) reruns all 3 around 07:00, 12:00 and 17:00 Swiss time and commits the result. GitHub Pages serves `index.html`. If MeteoSwiss is unavailable, the last forecast is kept and the sessions still update.

## Methodology

### Crowd

The booking popup gives the places left for each slot, but not the capacity. Capacity is estimated as the most places ever seen free for that level, with a minimum of 12. "Booked" is capacity minus places left:

| Booked | Label |
|---|---|
| Under 40% | Quiet |
| 40% to 75% | Moderate |
| Over 75% | Busy |
| 0 places left | Full |

### Price

The price is the slot's adult product, or its kid product when the surfer is set to Kid and the slot has one. Kid mode tags slots with no kid rate as "Adult rate". When a slot lists no products, the page shows the most common listed price for that level, marked `~CHF`.

### Weather

MeteoSwiss publishes 1 CSV per parameter for every Swiss postal code, updated hourly and covering 8 days. Only the Sion rows are kept, and UTC times are converted to Swiss time. Each session reads the hourly values stamped at the end of its hour: a 16:00 to 17:00 session uses the 17:00 values. Sessions past the forecast, about 7 days out, show "No forecast yet" and go last under "Best weather". The rain ranking uses steps of 10%. When every session is dry, the page says it is ranking by warmth.

## Design review, 26 October 2026

The page went through the Impeccable `critique` command (a design review and an automated detector, run separately, then combined). It scored **26/40** on Nielsen's 10 usability heuristics. The 5 priority issues were fixed in commits `7b4efcb` and `f3ff6c4`:

| Severity | Issue | Fix |
|---|---|---|
| P0 | On a phone the session table scrolled sideways (861px of content on a 375px screen). | Below 920px each session becomes a compact card. |
| P1 | "Book" opened the generic agenda, so the slot details had to be remembered across sites. | "Book" opens a panel with the details, the week to open and a copy button. |
| P1 | The first visit was a form with 8 controls that opened with a red error. | The first visit asks only for levels and Adult or Kid. Sort and filters moved onto the page. |
| P1 | White text on the green "Advanced Cruiser" pill was 3.2:1, below the 4.5:1 minimum. | Each pill uses whichever text colour contrasts more (5.3:1 on that green). |
| P2 | 2 of the 3 best sessions were often the Left and Right wave of the same hour. | 1 card per start time, naming the other wave. |

## Run it locally

```bash
python3 serve.py
```

Then open http://localhost:4322/. Locally the page has a "Refresh data" button that reruns the scraper and the forecast (about 1 minute).
