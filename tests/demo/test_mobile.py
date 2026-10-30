import re
from pathlib import Path

import mobile


def test_the_script_cannot_close_its_own_tag_early():
    body = mobile.script("placeholder").split("<script>", 1)[1].rsplit("</script>", 1)[0]
    assert "</" not in body


def test_the_placeholder_is_never_shown_as_an_answer():
    assert 'const PLACEHOLDER = "Ask a question.";' in mobile.script("  Ask a question.  ")


def test_desktop_keeps_the_section_open_and_headed():
    assert ".dw-behind .label-wrap { display: none !important; }" in mobile.CSS


def test_the_alert_reply_targets_ids_the_app_declares():
    app_source = (Path(__file__).parents[2] / "demo" / "app.py").read_text(encoding="utf-8")
    script = mobile.script("placeholder")
    for element_id in ("dw-question", "dw-ask"):
        assert f'elem_id="{element_id}"' in app_source
        assert f"#{element_id}" in script


def brand_colour(name: str) -> str:
    source = (Path(__file__).parents[2] / "demo" / "brand.py").read_text(encoding="utf-8")
    return re.search(rf'^{name} = "(#[0-9a-f]{{6}})"$', source, re.M).group(1)


def test_the_send_button_uses_the_themes_primary_colours():
    assert f"--dw-button: {brand_colour('INK')}" in mobile.CSS
    assert f"--dw-button: {brand_colour('GOLD_DARK')}" in mobile.CSS
