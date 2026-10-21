"""Build index.html from agenda.json (output of scrape_agenda.py --details).

Usage:
    python3 scrape_agenda.py --weeks 2 --details > agenda.json
    python3 build_view.py            # writes index.html next to this script
"""

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).parent

data = json.loads((HERE / "agenda.json").read_text())
# Show Swiss time even when built on a UTC machine (GitHub Actions).
mtime = datetime.fromtimestamp((HERE / "agenda.json").stat().st_mtime, ZoneInfo("Europe/Zurich"))
generated = mtime.strftime("%d %b %Y, %H:%M")
page = (HERE / "view_template.html").read_text()
page = page.replace("/*DATA*/[]", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
page = page.replace("/*GENERATED*/", generated)
page = page.replace("/*GENERATED_ISO*/", mtime.isoformat(timespec="seconds"))
(HERE / "index.html").write_text(page)
print(f"wrote {HERE / 'index.html'} ({len(data)} slots)")
