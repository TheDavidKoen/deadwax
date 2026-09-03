import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API_ROOT = "https://generativelanguage.googleapis.com/v1beta"

BOLD = "\033[1m"
RESET = "\033[0m"

DEFAULT_PROMPT = "In one sentence, what makes a good running order for an album?"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip("\"'"))


def read_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key

    print("GEMINI_API_KEY is not set.", file=sys.stderr)
    print("", file=sys.stderr)
    print("  1. Get a free key at https://aistudio.google.com/apikey", file=sys.stderr)
    print("  2. copy .env.example .env", file=sys.stderr)
    print("  3. Paste the key after GEMINI_API_KEY=", file=sys.stderr)
    raise SystemExit(1)


def read_model() -> str:
    model = os.environ.get("GEMINI_MODEL")
    if model:
        return model

    print("GEMINI_MODEL is not set.", file=sys.stderr)
    print("Run `uv run scripts/raw_call.py --list` to see what your key reaches.", file=sys.stderr)
    raise SystemExit(1)


def heading(text: str) -> None:
    print()
    print(f"{BOLD}{text}{RESET}")
    print("-" * len(text))


def show(value: object) -> None:
    print(value if isinstance(value, str) else json.dumps(value, indent=2))


def send(url: str, headers: dict[str, str], body: dict | None) -> tuple[int, dict]:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers=headers,
        method="GET" if payload is None else "POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, decode(response.read())
    except urllib.error.HTTPError as error:
        return error.code, decode(error.read())
    except urllib.error.URLError as error:
        print(f"Could not reach {url}: {error.reason}", file=sys.stderr)
        raise SystemExit(1) from error


def decode(payload: bytes) -> dict:
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return {"unparsedBody": payload.decode("utf-8", errors="replace")}


def list_models(api_key: str) -> None:
    status, body = send(f"{API_ROOT}/models", {"x-goog-api-key": api_key}, None)

    if status != 200:
        heading(f"Request failed with {status}")
        show(body)
        raise SystemExit(1)

    heading("Models that support generateContent")
    for model in body["models"]:
        if "generateContent" not in model.get("supportedGenerationMethods", []):
            continue
        name = model["name"].removeprefix("models/")
        print(f"{name:<42}{model['displayName']}")

    print()
    print("Put one of these in .env as GEMINI_MODEL.")


def generate(api_key: str, model: str, prompt: str) -> None:
    url = f"{API_ROOT}/models/{model}:generateContent"

    headers = {
        "content-type": "application/json",
        "x-goog-api-key": api_key,
    }

    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048},
    }

    heading("Request")
    show(f"POST {url}")
    show({**headers, "x-goog-api-key": f"{api_key[:6]}...redacted"})
    show(body)

    started_at = time.perf_counter()
    status, response = send(url, headers, body)
    elapsed_ms = round((time.perf_counter() - started_at) * 1000)

    heading(f"Response - {status} in {elapsed_ms}ms")
    show(response)

    if status != 200:
        heading("That failed")
        show("400 is usually a malformed body or an unknown model name.")
        show("403 means the key is wrong. 429 means you have hit the free-tier rate limit.")
        raise SystemExit(1)

    candidate = response["candidates"][0]

    heading("The part you actually wanted")
    show("".join(part["text"] for part in candidate["content"]["parts"]))

    heading("What it cost")
    show(
        {
            "finishReason": candidate.get("finishReason"),
            "modelVersion": response.get("modelVersion"),
            **response.get("usageMetadata", {}),
        }
    )


def main() -> None:
    load_env_file(Path(__file__).resolve().parent.parent / ".env")

    args = sys.argv[1:]
    api_key = read_api_key()

    if "--list" in args:
        list_models(api_key)
        return

    prompt = " ".join(arg for arg in args if not arg.startswith("--")) or DEFAULT_PROMPT
    generate(api_key, read_model(), prompt)


if __name__ == "__main__":
    main()
