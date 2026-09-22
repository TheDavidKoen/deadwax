import re
import urllib.parse
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass

MAX_ARTICLE_CHARS = 8000
SKIPPED_SECTIONS = frozenset(
    {
        "see also",
        "references",
        "notes",
        "citations",
        "footnotes",
        "sources",
        "bibliography",
        "further reading",
        "external links",
    }
)
HEADING = re.compile(r"^(=+)\s*(.*?)\s*\1\s*$")
MUSICBRAINZ_ARTIST = "https://musicbrainz.org/artist/"
WIKIPEDIA_PAGE = "https://en.wikipedia.org/wiki/"
MUSICBRAINZ_LICENCE = "CC0 1.0"
WIKIPEDIA_LICENCE = "CC BY-SA 4.0"


@dataclass(frozen=True)
class Section:
    heading: str
    text: str


def wikidata_id(relations: Sequence[Mapping]) -> str | None:
    for relation in relations:
        if relation.get("type") == "wikidata":
            return relation["url"]["resource"].rstrip("/").rsplit("/", 1)[-1]
    return None


def linked_wikipedia_title(relations: Sequence[Mapping]) -> str | None:
    for relation in relations:
        resource = relation.get("url", {}).get("resource", "")
        if relation.get("type") == "wikipedia" and "en.wikipedia.org/wiki/" in resource:
            return urllib.parse.unquote(resource.rsplit("/wiki/", 1)[-1]).replace("_", " ")
    return None


def facts(artist: Mapping) -> dict:
    span = artist.get("life-span") or {}
    return {
        "type": artist.get("type"),
        "country": artist.get("country"),
        "area": (artist.get("area") or {}).get("name"),
        "begin_area": (artist.get("begin-area") or {}).get("name"),
        "begin": span.get("begin"),
        "end": span.get("end"),
    }


def sections(extract: str) -> list[Section]:
    parsed: list[Section] = []
    heading, lines = "", []
    for line in extract.splitlines():
        match = HEADING.match(line)
        if match:
            parsed.append(Section(heading, "\n".join(lines).strip()))
            heading, lines = match.group(2), []
        else:
            lines.append(line)
    parsed.append(Section(heading, "\n".join(lines).strip()))

    kept: list[Section] = []
    total = 0
    for section in parsed:
        if not section.text or section.heading.casefold() in SKIPPED_SECTIONS:
            continue
        if kept and total + len(section.text) > MAX_ARTICLE_CHARS:
            break
        kept.append(section)
        total += len(section.text)
    return kept


def page_url(title: str) -> str:
    return WIKIPEDIA_PAGE + urllib.parse.quote(title.replace(" ", "_"))


def document(
    name: str,
    mbid: str,
    artist: Mapping,
    article: tuple[str, str] | None,
    retrieved: str,
) -> dict:
    wikipedia = None
    if article is not None:
        title, extract = article
        wikipedia = {
            "title": title,
            "url": page_url(title),
            "licence": WIKIPEDIA_LICENCE,
            "sections": [asdict(section) for section in sections(extract)],
        }
    return {
        "artist": name,
        "retrieved": retrieved,
        "musicbrainz": {
            "mbid": mbid,
            "url": MUSICBRAINZ_ARTIST + mbid,
            "licence": MUSICBRAINZ_LICENCE,
            "facts": facts(artist),
        },
        "wikipedia": wikipedia,
    }
