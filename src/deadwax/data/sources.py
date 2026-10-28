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
WIKIDATA_ENTITY = "https://www.wikidata.org/wiki/Special:EntityData"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
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


def lookup_artist(http: Http, mbid: str) -> dict:
    return http.get_json(f"{MUSICBRAINZ}/artist/{mbid}?inc=url-rels+tags&fmt=json")


def english_wikipedia_title(http: Http, wikidata_id: str) -> str | None:
    payload = http.get_json(f"{WIKIDATA_ENTITY}/{wikidata_id}.json")
    entity = next(iter(payload.get("entities", {}).values()), {})
    return entity.get("sitelinks", {}).get("enwiki", {}).get("title")


def wikipedia_article(http: Http, title: str) -> tuple[str, str] | None:
    query = urllib.parse.urlencode(
        {
            "action": "query",
            "prop": "extracts",
            "explaintext": 1,
            "exsectionformat": "wiki",
            "redirects": 1,
            "format": "json",
            "formatversion": 2,
            "titles": title,
        }
    )
    pages = http.get_json(f"{WIKIPEDIA_API}?{query}").get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing") or not pages[0].get("extract"):
        return None
    return pages[0]["title"], pages[0]["extract"]
