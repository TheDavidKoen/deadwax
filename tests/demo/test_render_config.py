import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
BLUEPRINT = (ROOT / "render.yaml").read_text(encoding="utf-8")
WAKE_PAGE = ROOT / "demo" / "wake" / "index.html"


def declared(key: str) -> list[str]:
    return [value.strip() for value in re.findall(rf"^\s*-?\s*{key}:\s*(.+)$", BLUEPRINT, re.M)]


def test_the_waking_page_points_at_the_demo_service():
    demo_service = declared("name")[0]
    assert f'"https://{demo_service}.onrender.com"' in WAKE_PAGE.read_text(encoding="utf-8")


def test_the_static_site_publishes_the_waking_page():
    publish_path = declared("staticPublishPath")[0]
    assert (ROOT / publish_path / "index.html") == WAKE_PAGE


def test_the_demo_service_starts_the_demo_app():
    start = declared("startCommand")[0]
    assert (ROOT / start.split()[-1]).is_file()


def test_the_demo_installs_exactly_the_locked_versions():
    assert "uv sync --frozen --group demo" in declared("buildCommand")[0]
