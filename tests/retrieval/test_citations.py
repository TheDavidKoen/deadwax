from deadwax.retrieval.citations import cited, source_lines, unretrieved

PASSAGES = {
    "can-03": {
        "artist": "Can",
        "section": "1960s",
        "source": "https://en.wikipedia.org/wiki/Can_(band)",
        "licence": "CC BY-SA 4.0",
    },
}


def test_a_citation_is_a_chunk_id_in_square_brackets():
    assert cited("Formed in 1968 [can-facts], with Mooney singing [can-04].") == [
        "can-facts",
        "can-04",
    ]


def test_several_ids_can_share_one_pair_of_brackets():
    assert cited("They split up [can-facts, can-10].") == ["can-facts", "can-10"]


def test_a_repeated_citation_is_counted_once_in_order_of_first_use():
    assert cited("[can-04] then [can-01] then [can-04]") == ["can-04", "can-01"]


def test_brackets_that_are_not_chunk_ids_are_ignored():
    assert cited("track [1] from [Kid A] at [t041]") == []


def test_ids_are_matched_regardless_of_case():
    assert cited("[Can-03]") == ["can-03"]


def test_a_citation_the_agent_was_never_given_is_reported():
    assert unretrieved(["can-03", "can-99"], ["can-03"]) == ["can-99"]


def test_a_source_line_names_the_page_and_its_licence():
    assert source_lines(["can-03"], PASSAGES) == [
        "[can-03] Can, 1960s. https://en.wikipedia.org/wiki/Can_(band) (CC BY-SA 4.0)"
    ]


def test_an_unretrieved_citation_has_no_source_line():
    assert source_lines(["can-99"], PASSAGES) == []
