import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

TARGET_CHARS = 900
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
BEGIN_VERBS = {"Person": "Born", "Group": "Formed"}
END_VERBS = {"Person": "Died", "Group": "Dissolved"}


@dataclass(frozen=True)
class Chunk:
    id: str
    artist: str
    section: str
    text: str
    source: str
    licence: str


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")


def pack(units: Iterable[str], limit: int, separator: str) -> list[str]:
    groups: list[str] = []
    current = ""
    for unit in units:
        if current and len(current) + len(separator) + len(unit) > limit:
            groups.append(current)
            current = unit
        else:
            current = f"{current}{separator}{unit}" if current else unit
    if current:
        groups.append(current)
    return groups


def pieces(text: str, limit: int = TARGET_CHARS) -> list[str]:
    units: list[str] = []
    for paragraph in filter(None, (line.strip() for line in text.splitlines())):
        if len(paragraph) <= limit:
            units.append(paragraph)
        else:
            units.extend(pack(SENTENCE_END.split(paragraph), limit, " "))
    return pack(units, limit, "\n")


def facts_text(artist: str, facts: Mapping) -> str:
    kind = (facts.get("type") or "artist").casefold()
    article = "an" if kind[0] in "aeiou" else "a"
    origin = f" from {facts['area']}" if facts.get("area") else ""
    sentences = [f"According to MusicBrainz, {artist} is {article} {kind}{origin}."]

    place = f" in {facts['begin_area']}" if facts.get("begin_area") else ""
    when = f" in {facts['begin']}" if facts.get("begin") else ""
    if place or when:
        sentences.append(f"{BEGIN_VERBS.get(facts.get('type'), 'Began')}{place}{when}.")
    if facts.get("end"):
        sentences.append(f"{END_VERBS.get(facts.get('type'), 'Ended')} in {facts['end']}.")
    return " ".join(sentences)


def chunk_documents(documents: Mapping[str, Mapping]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for artist, document in documents.items():
        key = slug(artist)
        musicbrainz = document["musicbrainz"]
        chunks.append(
            Chunk(
                id=f"{key}-facts",
                artist=artist,
                section="MusicBrainz",
                text=facts_text(artist, musicbrainz["facts"]),
                source=musicbrainz["url"],
                licence=musicbrainz["licence"],
            )
        )

        wikipedia = document["wikipedia"]
        if wikipedia is None:
            continue
        numbered = (
            (section["heading"] or "Introduction", piece)
            for section in wikipedia["sections"]
            for piece in pieces(section["text"])
        )
        for number, (heading, piece) in enumerate(numbered, start=1):
            chunks.append(
                Chunk(
                    id=f"{key}-{number:02d}",
                    artist=artist,
                    section=heading,
                    text=f"{artist} — {heading}\n{piece}",
                    source=wikipedia["url"],
                    licence=wikipedia["licence"],
                )
            )
    return chunks
