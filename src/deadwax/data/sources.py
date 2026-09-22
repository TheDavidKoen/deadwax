import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from deadwax import __version__

USER_AGENT = f"Deadwax/{__version__} ( https://github.com/TheDavidKoen/deadwax )"
MUSICBRAINZ = "https://musicbrainz.org/ws/2"
MIN_INTERVAL_SECONDS = 1.1
RETRY_STATUSES = (429, 503)
MAX_ATTEMPTS = 4


@dataclass
class Http:
    cache_dir: Path
    last_request: float = field(default=0.0, init=False)

    def get_json(self, url: str) -> dict:
        path = self.cache_dir / f"{hashlib.sha256(url.encode()).hexdigest()}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))

        payload = self._fetch(url)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
        return payload

    def _fetch(self, url: str) -> dict:
        request = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
        )
        attempt = 1
        while True:
            wait = self.last_request + MIN_INTERVAL_SECONDS - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self.last_request = time.monotonic()
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as error:
                if error.code not in RETRY_STATUSES or attempt >= MAX_ATTEMPTS:
                    raise
            time.sleep(2**attempt)
            attempt += 1


def search_artists(http: Http, name: str, limit: int = 10) -> list[dict]:
    phrase = name.replace("\\", "\\\\").replace('"', '\\"')
    query = urllib.parse.urlencode({"query": f'artist:"{phrase}"', "fmt": "json", "limit": limit})
    return http.get_json(f"{MUSICBRAINZ}/artist/?{query}").get("artists", [])
