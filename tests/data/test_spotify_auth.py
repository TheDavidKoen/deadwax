import string
import time
import urllib.parse

from deadwax.data.spotify_auth import (
    EXPIRY_MARGIN_SECONDS,
    SCOPES,
    Token,
    authorize_url,
    code_challenge,
    code_verifier,
    to_token,
)

URL_SAFE = set(string.ascii_letters + string.digits + "-_")


def test_the_challenge_matches_the_worked_example_in_rfc_7636():
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    assert code_challenge(verifier) == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


def test_a_verifier_is_url_safe_and_within_the_permitted_length():
    verifier = code_verifier()
    assert 43 <= len(verifier) <= 128
    assert set(verifier) <= URL_SAFE


def test_every_verifier_is_different():
    assert code_verifier() != code_verifier()


def test_the_sign_in_url_asks_only_for_read_access():
    url = authorize_url("client", "http://127.0.0.1:8888/callback", "challenge", "state")
    query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
    assert query["code_challenge_method"] == "S256"
    assert query["scope"].split() == list(SCOPES)
    assert all("read" in scope and "modify" not in scope for scope in SCOPES)
    assert query["redirect_uri"] == "http://127.0.0.1:8888/callback"


def test_a_refresh_that_returns_no_new_refresh_token_keeps_the_old_one():
    token = to_token({"access_token": "new", "expires_in": 3600}, "kept")
    assert token.refresh_token == "kept"


def test_a_token_counts_as_expired_shortly_before_it_actually_expires():
    soon = Token("a", "r", time.time() + EXPIRY_MARGIN_SECONDS / 2)
    later = Token("a", "r", time.time() + EXPIRY_MARGIN_SECONDS * 10)
    assert soon.expired
    assert not later.expired
