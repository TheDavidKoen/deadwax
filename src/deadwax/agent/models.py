import os

from langchain_google_genai import ChatGoogleGenerativeAI

FREE_TIER_MODELS = (
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
)


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
    )
