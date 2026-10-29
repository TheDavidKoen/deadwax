import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[2]


def card() -> dict[str, str]:
    text = (ROOT / "demo" / "README.md").read_text(encoding="utf-8")
    _, front_matter, _ = text.split("---", 2)
    pairs = (line.split(":", 1) for line in front_matter.strip().splitlines())
    return {key.strip(): value.strip().strip('"') for key, value in pairs}


def locked_version(package: str) -> str:
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    return next(p["version"] for p in lock["package"] if p["name"] == package)


def test_the_space_runs_the_gradio_version_the_lockfile_tested():
    assert card()["sdk_version"] == locked_version("gradio")


def test_the_space_runs_the_projects_python():
    pinned = (ROOT / ".python-version").read_text(encoding="utf-8").strip()
    assert card()["python_version"] == pinned


def test_the_space_starts_the_demo_app():
    assert (ROOT / "demo" / card()["app_file"]).is_file()
