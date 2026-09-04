import os

from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_google_genai import ChatGoogleGenerativeAI

FREE_TIER_MODELS = (
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
)

DEFAULT_REQUESTS_PER_MINUTE = 12

_limiter: InMemoryRateLimiter | None = None


def shared_rate_limiter() -> InMemoryRateLimiter:
    global _limiter
    if _limiter is None:
        rpm = int(os.environ.get("DEADWAX_RPM", str(DEFAULT_REQUESTS_PER_MINUTE)))
        _limiter = InMemoryRateLimiter(
            requests_per_second=rpm / 60,
            check_every_n_seconds=0.5,
            max_bucket_size=1,
        )
    return _limiter


def _api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set. See .env.example.")
    return key


def model_order() -> tuple[str, ...]:
    preferred = os.environ.get("GEMINI_MODEL")
    if preferred is None:
        return FREE_TIER_MODELS
    return (preferred, *(name for name in FREE_TIER_MODELS if name != preferred))


def build_model(name: str) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=name,
        google_api_key=_api_key(),
        temperature=0.0,
        max_output_tokens=2048,
        max_retries=0,
        rate_limiter=shared_rate_limiter(),
    )
