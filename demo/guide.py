from dataclasses import dataclass
from html import escape

CYCLE_SECONDS = 26
FIRST_LINE_SECONDS = 1.0
SECONDS_PER_LINE = 1.5
VISIBLE_UNTIL = 92
GONE_BY = 97


@dataclass(frozen=True)
class Line:
    text: str
    kind: str


TERMINAL = (
    Line("git clone https://github.com/TheDavidKoen/deadwax", "command"),
    Line("cd deadwax", "command"),
    Line("uv sync", "command"),
    Line('uv run deadwax "how many jazz tracks are in the library?"', "command"),
    Line("There are 9 jazz tracks, 1:41:25 in total.", "output"),
    Line("uv run deadwax-spotify login", "command"),
    Line("uv run deadwax-spotify pull", "command"),
    Line("294 tracks written to data/library.sqlite", "output"),
    Line("claude", "command"),
    Line("> how many Tame Impala songs do I have?", "prompt"),
    Line("You have 7 Tame Impala tracks, 30:03 in total.", "output"),
)


def _appears_at(position: int) -> float:
    seconds = FIRST_LINE_SECONDS + position * SECONDS_PER_LINE
    return round(seconds / CYCLE_SECONDS * 100, 2)


def terminal_css() -> str:
    rules = [
        ".dw-term { background: #1b1a18; color: #e8e4dd; border-radius: 6px; "
        "padding: 18px 20px; font-family: ui-monospace, Consolas, monospace; font-size: 13px; "
        "line-height: 1.7; min-height: 320px; border: 1px solid #3a3631; }",
        ".dw-term .dw-bar { display: flex; gap: 6px; margin-bottom: 12px; }",
        ".dw-term .dw-bar span { width: 10px; height: 10px; border-radius: 50%; "
        "background: #3a3631; }",
        ".dw-term .command::before { content: '$ '; color: #e1ad66; }",
        ".dw-term .output { color: #a39d94; }",
        ".dw-term .prompt { color: #e1ad66; }",
        ".dw-term div[class^='dw-l'] { opacity: 0; white-space: pre-wrap; "
        "word-break: break-word; }",
    ]
    for position in range(len(TERMINAL)):
        start = _appears_at(position)
        rules.append(
            f"@keyframes dw-l{position} {{ 0%, {round(start - 0.01, 2)}% {{ opacity: 0; }} "
            f"{start}%, {VISIBLE_UNTIL}% {{ opacity: 1; }} {GONE_BY}%, 100% {{ opacity: 0; }} }}"
        )
        rules.append(
            f".dw-term .dw-l{position} {{ animation: dw-l{position} {CYCLE_SECONDS}s infinite; }}"
        )
    rules.append(
        "@media (prefers-reduced-motion: reduce) { .dw-term div[class^='dw-l'] "
        "{ animation: none; opacity: 1; } }"
    )
    return "\n".join(rules)


def terminal_html() -> str:
    lines = "".join(
        f'<div class="dw-l{position} {line.kind}">{escape(line.text)}</div>'
        for position, line in enumerate(TERMINAL)
    )
    bar = '<div class="dw-bar"><span></span><span></span><span></span></div>'
    return f'<div class="dw-term" aria-label="Setting up Deadwax">{bar}{lines}</div>'


GET_THE_CODE = """
You need [git](https://git-scm.com/downloads) and [uv](https://docs.astral.sh/uv/). uv installs
the right version of Python by itself.

```
git clone https://github.com/TheDavidKoen/deadwax
cd deadwax
uv sync
```

Copy `.env.example` to `.env` (`copy` on Windows, `cp` elsewhere) and paste a free Gemini key
from [Google AI Studio](https://aistudio.google.com/apikey) after `GEMINI_API_KEY=`.
"""

ASK_IT = """
Ask from the terminal. It answers from the same 100-track library as this page until you
connect Spotify.

```
uv run deadwax "build me a 30 minute ambient playlist, nothing over 8 minutes"
```

The tool calls and the model that answered are printed alongside the answer.
"""

CONNECT_YOUR_AI = """
Deadwax is also a [Model Context Protocol](https://modelcontextprotocol.io) server, so an AI
assistant can call its tools directly. Your assistant becomes the agent; Deadwax still does
every count and check.

**Claude Code** — the repository ships a `.mcp.json`. Start Claude Code in the `deadwax`
folder and approve the `deadwax` server when asked.

**Any other MCP client** — add this to its MCP settings, with your own path:

```
{
  "mcpServers": {
    "deadwax": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/deadwax", "deadwax-mcp"]
    }
  }
}
```
"""

CONNECT_SPOTIFY = """
Point Deadwax at your own saved tracks. Spotify requires the app owner to have Premium.

1. Create an app at [developer.spotify.com](https://developer.spotify.com/dashboard) with the
   redirect URI `http://127.0.0.1:8888/callback`.
2. Put its client ID in `.env` after `SPOTIFY_CLIENT_ID=`.
3. Sign in and pull your library:

```
uv run deadwax-spotify login
uv run deadwax-spotify pull
```

4. Set `DEADWAX_LIBRARY=data/library.sqlite` in `.env`.

Sign-in is read-only and needs no client secret. Your library stays on your machine; genres
come from MusicBrainz, matched by each track's ISRC.
"""

STEPS = (
    ("1 · Get the code", GET_THE_CODE),
    ("2 · Ask it", ASK_IT),
    ("3 · Connect your AI", CONNECT_YOUR_AI),
    ("4 · Connect Spotify", CONNECT_SPOTIFY),
)
