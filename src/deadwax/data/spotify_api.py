import json
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass, field

API = "https://api.spotify.com/v1"
PAGE_SIZE = 50
MIN_INTERVAL_SECONDS = 0.25
MAX_ATTEMPTS = 5


@dataclass
class Spotify:
    token: str
    last_request: float = field(default=0.0, init=False)

    def get(self, url: str) -> dict:
        if not url.startswith("https://"):
            url = f"{API}{url}"
        request = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
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
                if error.code != 429 or attempt >= MAX_ATTEMPTS:
                    raise
                retry_after = error.headers.get("Retry-After")
                time.sleep(int(retry_after) if retry_after else 2**attempt)
            attempt += 1

    def pages(self, url: str) -> Iterator[dict]:
        next_url: str | None = url
        while next_url:
            page = self.get(next_url)
            yield from page.get("items", [])
            next_url = page.get("next")


def saved_tracks(spotify: Spotify) -> list[dict]:
    return list(spotify.pages(f"/me/tracks?limit={PAGE_SIZE}"))


def recently_played(spotify: Spotify) -> list[dict]:
    return spotify.get(f"/me/player/recently-played?limit={PAGE_SIZE}").get("items", [])
