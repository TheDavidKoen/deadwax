from pathlib import Path

import dock

ROOT = Path(__file__).parents[2]


def test_every_reference_points_at_a_file_in_the_repository():
    for layer in dock.STACK:
        if layer.reference:
            path, _, anchor = layer.reference.partition("#")
            assert (ROOT / path).is_file(), layer.reference
            if anchor:
                text = (ROOT / path).read_text(encoding="utf-8").lower()
                assert f"## {anchor}" in text, layer.reference


def test_every_logo_has_a_clean_icon_file():
    for layer in dock.STACK:
        if layer.logo:
            svg = dock.icon(layer.logo)
            assert svg.startswith("<svg") and 'fill="currentColor"' in svg
            assert "<script" not in svg.lower()


def test_adr_links_are_labelled_with_their_number():
    assert dock.reference_label("docs/adr/0012-the-live-demo-runs-on-render.md") == "ADR 0012"
    assert dock.reference_label("README.md#tracing") == "README"


def test_the_script_cannot_close_its_own_tag_early():
    body = dock.script().split("<script>", 1)[1].rsplit("</script>", 1)[0]
    assert "</" not in body


def test_hidden_bubbles_start_out_of_keyboard_reach():
    stowable = dock.html().count("dw-launcher--stowable")
    assert stowable == 2
    assert dock.html().count(" inert>") == stowable
