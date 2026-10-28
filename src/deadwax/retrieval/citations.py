import re
from collections.abc import Iterable, Mapping

CHUNK_ID = r"[a-z0-9]+(?:-[a-z0-9]+)+"
CITATION = re.compile(rf"\[({CHUNK_ID}(?:\s*,\s*{CHUNK_ID})*)\]", re.IGNORECASE)


def cited(text: str) -> list[str]:
    ids = (part.strip().casefold() for group in CITATION.findall(text) for part in group.split(","))
    return list(dict.fromkeys(ids))


def unretrieved(ids: Iterable[str], retrieved: Iterable[str]) -> list[str]:
    known = set(retrieved)
    return [chunk_id for chunk_id in ids if chunk_id not in known]


def source_lines(ids: Iterable[str], passages: Mapping[str, Mapping]) -> list[str]:
    return [
        f"[{chunk_id}] {p['artist']}, {p['section']}. {p['source']} ({p['licence']})"
        for chunk_id in ids
        if (p := passages.get(chunk_id)) is not None
    ]
