import base64
import hashlib
import json
import secrets
import time
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
SCOPES = ("user-library-read", "user-read-recently-played")
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8888/callback"
TOKEN_FILE = Path(".cache") / "spotify-token.json"
EXPIRY_MARGIN_SECONDS = 60
SIGNED_IN_PAGE = b"<p>Signed in to Deadwax. You can close this tab.</p>"


@dataclass(frozen=True)
class Token:
    access_token: str
    refresh_token: str
    expires_at: float

    @property
    def expired(self) -> bool:
        return time.time() > self.expires_at - EXPIRY_MARGIN_SECONDS


def code_verifier() -> str:
    return secrets.token_urlsafe(96)


def code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def authorize_url(client_id: str, redirect_uri: str, challenge: str, state: str) -> str:
    query = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "code_challenge_method": "S256",
            "code_challenge": challenge,
            "scope": " ".join(SCOPES),
            "state": state,
        }
    )
    return f"{AUTHORIZE_URL}?{query}"


def to_token(payload: dict, previous_refresh_token: str = "") -> Token:
    return Token(
        access_token=payload["access_token"],
        refresh_token=payload.get("refresh_token") or previous_refresh_token,
        expires_at=time.time() + payload["expires_in"],
    )


def _post(form: dict) -> dict:
    request = urllib.request.Request(
        TOKEN_URL,
        data=urllib.parse.urlencode(form).encode("ascii"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_code(redirect_uri: str, state: str) -> str:
    target = urllib.parse.urlsplit(redirect_uri)
    received: dict[str, str] = {}

    class Callback(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            url = urllib.parse.urlsplit(self.path)
            if url.path == target.path:
                received.update(urllib.parse.parse_qsl(url.query))
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(SIGNED_IN_PAGE)

        def log_message(self, *args: object) -> None:
            pass

    with HTTPServer((target.hostname or "127.0.0.1", target.port or 80), Callback) as server:
        while not received:
            server.handle_request()

    if "error" in received:
        raise PermissionError(f"Spotify sign-in was refused: {received['error']}")
    if received.get("state") != state:
        raise PermissionError("the sign-in response did not match this request; try again")
    return received["code"]


def sign_in(client_id: str, redirect_uri: str) -> Token:
    verifier = code_verifier()
    state = secrets.token_urlsafe(16)
    url = authorize_url(client_id, redirect_uri, code_challenge(verifier), state)
    print(f"Opening Spotify in your browser. If nothing opens, visit:\n{url}")
    webbrowser.open(url)
    code = wait_for_code(redirect_uri, state)
    payload = _post(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "code_verifier": verifier,
        }
    )
    return to_token(payload)


def refresh(client_id: str, token: Token) -> Token:
    payload = _post(
        {
            "grant_type": "refresh_token",
            "refresh_token": token.refresh_token,
            "client_id": client_id,
        }
    )
    return to_token(payload, token.refresh_token)


def load_token(path: Path = TOKEN_FILE) -> Token | None:
    if not path.exists():
        return None
    return Token(**json.loads(path.read_text(encoding="utf-8")))


def save_token(token: Token, path: Path = TOKEN_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(token)), encoding="utf-8")


def access_token(client_id: str, redirect_uri: str) -> str:
    token = load_token()
    if token is None:
        token = sign_in(client_id, redirect_uri)
    elif token.expired:
        token = refresh(client_id, token)
    save_token(token)
    return token.access_token
