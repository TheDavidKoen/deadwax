from deadwax.retrieval.chunking import TARGET_CHARS, chunk_documents, facts_text, pieces, slug

DOCUMENTS = {
    "Can": {
        "musicbrainz": {
            "url": "https://musicbrainz.org/artist/can",
            "licence": "CC0 1.0",
            "facts": {
                "type": "Group",
                "area": "Germany",
                "begin_area": "Köln",
                "begin": "1968",
                "end": "1991",
            },
        },
        "wikipedia": {
            "url": "https://en.wikipedia.org/wiki/Can_(band)",
            "licence": "CC BY-SA 4.0",
            "sections": [
                {"heading": "", "text": "Can were a German rock band."},
                {"heading": "History", "text": "They recorded Tago Mago."},
            ],
        },
    },
    "Loscil": {
        "musicbrainz": {
            "url": "https://musicbrainz.org/artist/loscil",
            "licence": "CC0 1.0",
            "facts": {"type": "Person", "area": "Canada", "begin_area": None, "begin": None},
        },
        "wikipedia": None,
    },
}


def test_slugs_are_lowercase_and_punctuation_free():
    assert slug("Godspeed You! Black Emperor") == "godspeed-you-black-emperor"
    assert slug("Neu!") == "neu"


def test_a_group_reads_as_formed_and_dissolved():
    facts = DOCUMENTS["Can"]["musicbrainz"]["facts"]
    assert facts_text("Can", facts) == (
        "According to MusicBrainz, Can is a group from Germany. "
        "Formed in Köln in 1968. Dissolved in 1991."
    )


def test_missing_facts_are_left_out_rather_than_invented():
    facts = DOCUMENTS["Loscil"]["musicbrainz"]["facts"]
    assert (
        facts_text("Loscil", facts) == "According to MusicBrainz, Loscil is a person from Canada."
    )


def test_an_unknown_type_reads_naturally():
    assert facts_text("X", {"type": None}).startswith("According to MusicBrainz, X is an artist")


def test_every_artist_gets_a_facts_chunk_even_without_an_article():
    ids = [chunk.id for chunk in chunk_documents(DOCUMENTS)]
    assert ids == ["can-facts", "can-01", "can-02", "loscil-facts"]


def test_a_chunk_names_its_artist_and_section_so_it_stands_alone():
    chunk = chunk_documents(DOCUMENTS)[2]
    assert chunk.text == "Can — History\nThey recorded Tago Mago."
    assert chunk.section == "History"


def test_the_intro_is_labelled_rather_than_left_blank():
    assert chunk_documents(DOCUMENTS)[1].section == "Introduction"


def test_a_chunk_carries_the_source_and_licence_it_must_be_cited_with():
    facts, article = chunk_documents(DOCUMENTS)[:2]
    assert (facts.source, facts.licence) == ("https://musicbrainz.org/artist/can", "CC0 1.0")
    assert article.licence == "CC BY-SA 4.0"


def test_short_paragraphs_are_packed_together():
    assert pieces("One.\nTwo.\nThree.") == ["One.\nTwo.\nThree."]


def test_long_text_is_split_without_exceeding_the_target():
    text = "\n".join(f"Paragraph {i} " + "word " * 60 for i in range(10))
    parts = pieces(text)
    assert len(parts) > 1
    assert all(len(part) <= TARGET_CHARS for part in parts)


def test_a_paragraph_longer_than_the_target_splits_at_sentences():
    paragraph = " ".join(f"Sentence number {i} is here." for i in range(80))
    parts = pieces(paragraph)
    assert len(parts) > 1
    assert all(part.endswith(".") for part in parts)
