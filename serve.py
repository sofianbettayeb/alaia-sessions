"""Serve the booking view locally, with a refresh endpoint.

A static page can't call booking.alaiabay.ch itself (the browser blocks
cross-site requests), so the Refresh button posts to /refresh here, which
reruns the scraper and rebuilds index.html.

Usage:
    python3 serve.py            # http://localhost:4322/
"""

import json
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).parent
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 4322
lock = threading.Lock()


def refresh():
    """Scrape into a temp file first, so a failed run keeps the last good data."""
    tmp = HERE / "agenda.json.tmp"
    with tmp.open("w") as out:
        scrape = subprocess.run(
            [sys.executable, "-I", str(HERE / "scrape_agenda.py"), "--weeks", "2", "--details"],
            stdout=out, stderr=subprocess.PIPE, text=True, timeout=300,
        )
    if scrape.returncode != 0:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(scrape.stderr.strip().splitlines()[-1] if scrape.stderr.strip() else "scraper failed")
    tmp.replace(HERE / "agenda.json")
    subprocess.run([sys.executable, "-I", str(HERE / "build_view.py")], check=True, capture_output=True, timeout=60)
    return len(json.loads((HERE / "agenda.json").read_text()))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(HERE), **kwargs)

    def do_POST(self):
        if self.path != "/refresh":
            self.send_error(404)
            return
        if not lock.acquire(blocking=False):
            return self.reply(409, {"ok": False, "error": "A refresh is already running."})
        try:
            self.reply(200, {"ok": True, "slots": refresh()})
        except Exception as e:  # report any failure to the page instead of a bare 500
            self.reply(500, {"ok": False, "error": str(e)})
        finally:
            lock.release()

    def reply(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    print(f"Serving http://localhost:{PORT}/")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
