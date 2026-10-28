from deadwax.data.documents import (
    MAX_ARTICLE_CHARS,
    document,
    facts,
    linked_wikipedia_title,
    page_url,
    sections,
    wikidata_id,
)

RELATIONS = [
    {"type": "discogs", "url": {"resource": "https://www.discogs.com/artist/1"}},
    {"type": "wikidata", "url": {"resource": "https://www.wikidata.org/wiki/Q208012"}},
]

ARTICLE = """Can were a German rock band formed in Cologne in 1968.

== History ==
They recorded Tago Mago in 1971.

=== Later years ===
The band split in 1979.

== References ==
Some citation.

== External links ==
A link."""


def test_the_wikidata_id_is_read_from_the_url_relation():
    assert wikidata_id(RELATIONS) == "Q208012"


def test_a_missing_wikidata_relation_gives_none():
    assert wikidata_id(RELATIONS[:1]) is None


def test_a_direct_wikipedia_link_is_used_when_there_is_no_wikidata():
    relations = [
        {"type": "wikipedia", "url": {"resource": "https://en.wikipedia.org/wiki/Can_(band)"}}
    ]
    assert linked_wikipedia_title(relations) == "Can (band)"


def test_facts_are_read_from_a_musicbrainz_artist():
    artist = {
        "type": "Group",
        "country": "DE",
        "area": {"name": "Germany"},
        "begin-area": {"name": "Cologne"},
        "life-span": {"begin": "1968", "end": "1979"},
    }
    assert facts(artist) == {
        "type": "Group",
        "country": "DE",
        "area": "Germany",
        "begin_area": "Cologne",
        "begin": "1968",
        "end": "1979",
    }


def test_missing_facts_are_none_rather_than_errors():
    assert facts({})["begin_area"] is None


def test_an_article_splits_into_its_sections_with_headings_kept():
    parsed = sections(ARTICLE)
    assert [s.heading for s in parsed] == ["", "History", "Later years"]
    assert parsed[0].text == "Can were a German rock band formed in Cologne in 1968."


def test_reference_sections_are_dropped():
    assert all(s.heading not in ("References", "External links") for s in sections(ARTICLE))


def test_a_long_article_is_cut_at_a_section_boundary():
    long_article = "Intro.\n" + "".join(f"== Part {i} ==\n{'x' * 3000}\n" for i in range(10))
    parsed = sections(long_article)
    assert sum(len(s.text) for s in parsed) <= MAX_ARTICLE_CHARS
    assert all(len(s.text) in (6, 3000) for s in parsed)


def test_an_intro_longer_than_the_limit_is_still_kept():
    parsed = sections("y" * (MAX_ARTICLE_CHARS + 1))
    assert len(parsed) == 1


def test_a_page_url_escapes_the_title():
    assert page_url("Can (band)") == "https://en.wikipedia.org/wiki/Can_%28band%29"


def test_an_artist_without_an_article_still_gets_a_document():
    doc = document("Loscil", "abc", {}, None, "2026-09-22")
    assert doc["wikipedia"] is None
    assert doc["musicbrainz"]["url"].endswith("/abc")
    assert doc["musicbrainz"]["licence"] == "CC0 1.0"


def test_an_article_carries_its_url_and_licence():
    doc = document("Can", "abc", {}, ("Can (band)", ARTICLE), "2026-09-22")
    assert doc["wikipedia"]["licence"] == "CC BY-SA 4.0"
    assert doc["wikipedia"]["url"] == page_url("Can (band)")
