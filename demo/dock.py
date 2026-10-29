import json
from dataclasses import dataclass
from html import escape
from pathlib import Path

ICONS = Path(__file__).parent / "assets" / "stack"
REPOSITORY = "https://github.com/TheDavidKoen/deadwax/blob/main"
SITE = "https://davidkoen.is-a.dev"


@dataclass(frozen=True)
class Layer:
    layer: str
    choice: str
    logo: str | None
    why: str
    reference: str | None


STACK = (
    Layer(
        "Language",
        "Python 3.13",
        "python",
        "The agent ecosystem is Python-first, so the whole system is too: the agent, the "
        "validator, the evaluation harness and this demo. The deterministic core was written "
        "with the standard library alone before any framework arrived.",
        "docs/adr/0003-python-for-the-agent.md",
    ),
    Layer(
        "Agent",
        "LangChain",
        "langchain",
        "Runs the tool-calling loop. It arrived only once a hand-written loop had shown what a "
        "framework should take off my hands, and a supervisor in plain Python, not the model, "
        "decides when the agent has finished.",
        "docs/adr/0005-the-agent-does-not-decide-when-it-is-finished.md",
    ),
    Layer(
        "Model",
        "Google Gemini",
        "googlegemini",
        "Reads the question, chooses the tools and writes the reply. It never computes: every "
        "count, total and constraint check is plain Python, and every number it quotes comes "
        "from a tool result.",
        "docs/adr/0001-the-model-never-computes.md",
    ),
    Layer(
        "Evaluation",
        "Eval harness",
        None,
        "25 cases, each run three times and scored separately on tool choice, parameters, "
        "answer and convergence, because one pass on a non-deterministic system is an "
        "anecdote. A change to a prompt or tool description is measured before it merges.",
        "README.md#evaluation",
    ),
    Layer(
        "Retrieval",
        "Plain-Python search",
        None,
        "Artist background comes from a reviewed snapshot of MusicBrainz and Wikipedia, "
        "embedded once at build time. Searching 627 passages needs a loop, not a vector "
        "database, and answers must cite the passages they used.",
        "docs/adr/0002-no-vector-database.md",
    ),
    Layer(
        "Tracing",
        "Langfuse",
        None,
        "Every model call is traced, including the closing turn that writes the answer, and "
        "every eval run attaches its scores to its trace, so a failing case is one filter "
        "away.",
        "README.md#tracing",
    ),
    Layer(
        "Store",
        "SQLite",
        "sqlite",
        "A Spotify library is pulled once into the standard library's SQLite. Genres come "
        "from MusicBrainz, matched by each track's ISRC rather than by name.",
        "docs/adr/0010-real-data-comes-from-spotify-and-musicbrainz-by-isrc.md",
    ),
    Layer(
        "Interop",
        "Model Context Protocol",
        "modelcontextprotocol",
        "The same four tools, served to any MCP client such as Claude Code. Their "
        "descriptions are registered by reference, so they cannot drift from the agent's.",
        "docs/adr/0011-over-mcp-the-client-is-the-agent.md",
    ),
    Layer(
        "Hosting",
        "Gradio on Render",
        "gradio",
        "This page. A free Render service that sleeps when idle, behind a static page that "
        "explains the wait, and deployed only once CI passes.",
        "docs/adr/0012-the-live-demo-runs-on-render.md",
    ),
    Layer(
        "Toolchain",
        "uv, ruff and pytest",
        "uv",
        "uv pins Python and every dependency in a lockfile. Every pull request runs lint, "
        "formatting, the unit tests and a check of every eval case.",
        None,
    ),
)

PLUS = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" '
    'stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>'
)
D_MARK = (
    '<svg viewBox="0 0 32 32"><path fill="currentColor" fill-rule="evenodd" '
    'd="M8 6h7.4c6.1 0 10.2 4 10.2 10s-4.1 10-10.2 10H8V6zm5 4.6v10.8h2.2c3.5 0 5.6-2 '
    '5.6-5.4s-2.1-5.4-5.6-5.4H13z"/><circle cx="27" cy="6" r="4" fill="#ff0000"/></svg>'
)


def icon(name: str) -> str:
    return (ICONS / f"{name}.svg").read_text(encoding="utf-8").strip()


def reference_label(reference: str) -> str:
    return f"ADR {Path(reference).name[:4]}" if reference.startswith("docs/adr/") else "README"


def row(layer: Layer) -> str:
    logo = f'<span class="dw-stack__logo">{icon(layer.logo)}</span>' if layer.logo else ""
    link = (
        f' <a href="{REPOSITORY}/{layer.reference}" target="_blank" rel="noopener">'
        f"{reference_label(layer.reference)}</a>"
        if layer.reference
        else ""
    )
    return (
        '<div class="dw-stack__row">'
        f'<dt><span class="dw-stack__layer">{escape(layer.layer)}</span>'
        f'<span class="dw-stack__choice">{escape(layer.choice)}</span>{logo}</dt>'
        f"<dd>{escape(layer.why)}{link}</dd>"
        "</div>"
    )


def html() -> str:
    rows = "".join(row(layer) for layer in STACK)
    return f"""
<button type="button" class="dw-launcher dw-launcher--toggle" style="--dw-order: 0"
  aria-expanded="false" aria-label="Explore more" aria-describedby="dw-tip-toggle">
  <span class="dw-launcher__mark" aria-hidden="true">{PLUS}</span>
  <span class="dw-launcher__tip" id="dw-tip-toggle" role="tooltip">Explore more.</span>
</button>
<button type="button" class="dw-launcher dw-launcher--stowable" style="--dw-order: 1"
  aria-label="Open the tech stack" aria-haspopup="dialog" aria-describedby="dw-tip-stack"
  data-dw-open inert>
  <span class="dw-launcher__mark" aria-hidden="true">{icon("langchain")}</span>
  <span class="dw-launcher__tip" id="dw-tip-stack" role="tooltip">Program's tech stack.</span>
</button>
<a class="dw-launcher dw-launcher--stowable" style="--dw-order: 2" href="{SITE}"
  target="_blank" rel="noopener" aria-label="David Koen's portfolio"
  aria-describedby="dw-tip-site" inert>
  <span class="dw-launcher__mark dw-launcher__mark--site" aria-hidden="true">{D_MARK}</span>
  <span class="dw-launcher__tip" id="dw-tip-site" role="tooltip">Back to my site.</span>
</a>
<dialog class="dw-sheet" aria-labelledby="dw-stack-heading">
  <header class="dw-sheet__bar">
    <div>
      <p class="dw-sheet__eyebrow">Decisions, not defaults</p>
      <h2 id="dw-stack-heading">What Deadwax runs on</h2>
    </div>
    <button type="button" class="dw-sheet__close" aria-label="Close" data-dw-close>&times;</button>
  </header>
  <div class="dw-sheet__body"><dl class="dw-stack">{rows}</dl></div>
</dialog>
"""


SCRIPT_TEMPLATE = """
<script>
(() => {
  const DOCK = %s;

  function mount() {
    if (document.getElementById("dw-dock")) return;
    const dock = document.createElement("div");
    dock.id = "dw-dock";
    dock.innerHTML = DOCK;
    document.body.appendChild(dock);

    const toggle = dock.querySelector(".dw-launcher--toggle");
    const stowable = dock.querySelectorAll(".dw-launcher--stowable");
    const sheet = dock.querySelector(".dw-sheet");
    const isOpen = () => toggle.getAttribute("aria-expanded") === "true";
    const setOpen = (open) => {
      document.documentElement.dataset.dwDock = open ? "open" : "closed";
      toggle.setAttribute("aria-expanded", String(open));
      stowable.forEach((bubble) => { bubble.inert = !open; });
    };

    setOpen(false);
    toggle.addEventListener("click", () => setOpen(!isOpen()));
    dock.querySelector("[data-dw-open]").addEventListener("click", () => sheet.showModal());
    dock.querySelector("[data-dw-close]").addEventListener("click", () => sheet.close());
    sheet.addEventListener("click", (event) => { if (event.target === sheet) sheet.close(); });
    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape" || sheet.open || !isOpen()) return;
      setOpen(false);
      toggle.focus();
    });
    document.addEventListener("pointerdown", (event) => {
      if (sheet.open || event.target.closest(".dw-launcher")) return;
      setOpen(false);
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
  else mount();
})();
</script>
"""


def script() -> str:
    return SCRIPT_TEMPLATE % json.dumps(html()).replace("</", "<\\/")


CSS = """
:root {
  --dw-raised: #fffdf9; --dw-raised-hover: #f0ebe2; --dw-line: #e4dfd6;
  --dw-dock-size: 3.25rem; --dw-dock-gap: 0.65rem; --dw-dock-top: 1.25rem; --dw-dock-right: 1.25rem;
  --dw-ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
  --dw-ease-out-quint: cubic-bezier(0.22, 1, 0.36, 1);
  --dw-ease-in-expo: cubic-bezier(0.7, 0, 0.84, 0);
}
.dark { --dw-raised: #232120; --dw-raised-hover: #2e2b28; --dw-line: #3a3631; }

.dw-launcher {
  position: fixed; z-index: 55; right: var(--dw-dock-right);
  top: calc(var(--dw-dock-top) + var(--dw-order) * (var(--dw-dock-size) + var(--dw-dock-gap)));
  display: grid; place-items: center; width: var(--dw-dock-size); height: var(--dw-dock-size);
  padding: 0; color: var(--dw-ink); background: var(--dw-raised);
  border: 1px solid var(--dw-line); border-radius: 50%; cursor: pointer; text-decoration: none;
  transition: transform 0.28s var(--dw-ease-out-quint), border-color 0.28s var(--dw-ease-out-quint),
    box-shadow 0.28s var(--dw-ease-out-quint);
}
.dw-launcher:hover, .dw-launcher:focus-visible {
  transform: translateY(-3px); border-color: var(--dw-gold);
  box-shadow: 0 10px 24px rgb(0 0 0 / 0.35);
}
.dw-launcher--toggle[aria-expanded="true"] { border-color: var(--dw-gold); }
.dw-launcher--stowable {
  transition:
    transform 0.46s var(--dw-ease-spring) calc((var(--dw-order) - 1) * 0.07s),
    opacity 0.24s linear calc((var(--dw-order) - 1) * 0.07s),
    border-color 0.28s var(--dw-ease-out-quint), box-shadow 0.28s var(--dw-ease-out-quint);
}
html[data-dw-dock="closed"] .dw-launcher--stowable {
  transform: translateY(calc(var(--dw-order) * (var(--dw-dock-size) + var(--dw-dock-gap)) * -1))
    scale(0.2);
  opacity: 0;
  transition:
    transform 0.3s var(--dw-ease-in-expo) calc((2 - var(--dw-order)) * 0.05s),
    opacity 0.2s linear calc((2 - var(--dw-order)) * 0.05s);
}
.dw-launcher__mark { display: grid; width: 1.5rem; height: 1.5rem; }
.dw-launcher__mark svg { width: 100%; height: 100%; }
.dw-launcher__mark--site { width: 1.7rem; height: 1.7rem; }
.dw-launcher--toggle .dw-launcher__mark { transition: transform 0.4s var(--dw-ease-spring); }
.dw-launcher--toggle[aria-expanded="true"] .dw-launcher__mark { transform: rotate(135deg); }

.dw-launcher__tip {
  position: absolute; top: 50%; right: calc(100% + 0.85rem);
  padding: 0.45rem 0.75rem; font: 700 0.75rem/1.2 system-ui, -apple-system, "Segoe UI", sans-serif;
  white-space: nowrap; color: var(--dw-ink); background: var(--dw-raised-hover);
  border-radius: 0.4rem; opacity: 0; pointer-events: none;
  transform: translateY(-50%) translateX(0.4rem);
  transition: opacity 0.2s linear, transform 0.26s var(--dw-ease-out-quint);
}
.dw-launcher__tip::after {
  content: ""; position: absolute; top: 50%; left: 100%;
  border: 5px solid transparent; border-left-color: var(--dw-raised-hover);
  transform: translateY(-50%);
}
.dw-launcher:hover .dw-launcher__tip, .dw-launcher:focus-visible .dw-launcher__tip {
  opacity: 1; transform: translateY(-50%) translateX(0);
}

.dw-sheet {
  inset: 0; margin: auto; width: min(46rem, 92vw); max-height: 84vh; padding: 0;
  overflow: hidden; color: var(--dw-ink); background: var(--dw-raised);
  border: 1px solid var(--dw-line); border-radius: 1rem;
  font: 15px/1.6 system-ui, -apple-system, "Segoe UI", sans-serif;
  opacity: 0; transform: scale(0.92);
  transition: opacity 0.16s ease-in, transform 0.18s ease-in,
    display 0.18s allow-discrete, overlay 0.18s allow-discrete;
}
.dw-sheet[open] {
  display: flex; flex-direction: column; opacity: 1; transform: scale(1);
  transition: opacity 0.2s linear, transform 0.36s var(--dw-ease-spring),
    display 0.36s allow-discrete, overlay 0.36s allow-discrete;
}
@starting-style { .dw-sheet[open] { opacity: 0; transform: translateY(1.25rem) scale(0.985); } }
.dw-sheet::backdrop {
  background: rgb(0 0 0 / 0.65); backdrop-filter: blur(3px); opacity: 0;
  transition: opacity 0.3s linear, display 0.3s allow-discrete, overlay 0.3s allow-discrete;
}
.dw-sheet[open]::backdrop { opacity: 1; }
@starting-style { .dw-sheet[open]::backdrop { opacity: 0; } }
.dw-sheet__bar {
  flex-shrink: 0; display: flex; align-items: flex-start; justify-content: space-between;
  gap: 1rem; padding: 1.5rem 1.75rem 1.1rem; border-bottom: 1px solid var(--dw-line);
}
.dw-sheet__eyebrow {
  margin: 0; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.16em;
  text-transform: uppercase; color: var(--dw-gold);
}
.dw-sheet__bar h2 {
  margin: 0.4rem 0 0; font-family: "Cormorant Garamond", Georgia, serif; font-weight: 500;
  font-size: 1.75rem; letter-spacing: 0.04em; color: var(--dw-ink);
}
.dw-sheet__close {
  flex-shrink: 0; padding: 0; font-size: 1.6rem; line-height: 1; color: var(--dw-muted);
  background: none; border: 0; cursor: pointer;
}
.dw-sheet__close:hover { color: var(--dw-ink); }
.dw-sheet__body { flex: 1; min-height: 0; padding: 1.4rem 1.75rem 1.75rem; overflow-y: auto; }

.dw-stack { display: grid; gap: 1.4rem; margin: 0; }
.dw-stack__row {
  display: grid; gap: 0.35rem; padding-top: 1.4rem; border-top: 1px solid var(--dw-line);
}
.dw-stack__row:first-child { padding-top: 0; border-top: 0; }
.dw-stack__row dt { display: grid; align-content: start; gap: 0.2rem; }
.dw-stack__row dd { margin: 0; font-size: 0.875rem; color: var(--dw-muted); }
.dw-stack__row dd a {
  margin-left: 0.4rem; white-space: nowrap; font-size: 0.75rem; font-weight: 700;
  color: var(--dw-gold); text-underline-offset: 4px;
}
.dw-stack__layer {
  font-size: 0.75rem; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase;
  color: var(--dw-muted);
}
.dw-stack__choice { font-size: 1.05rem; font-weight: 800; color: var(--dw-ink); }
.dw-stack__logo {
  display: block; width: 1.5rem; height: 1.5rem; margin-top: 0.4rem; color: var(--dw-ink);
}
.dw-stack__logo svg { width: 100%; height: 100%; }
@media (min-width: 44rem) {
  .dw-stack__row { grid-template-columns: 13rem 1fr; gap: 0.35rem 1.75rem; }
}

@media (max-width: 640px) {
  :root { --dw-dock-size: 2.75rem; --dw-dock-top: 0.75rem; --dw-dock-right: 0.75rem; }
  .dw-launcher__mark { width: 1.25rem; height: 1.25rem; }
  .dw-sheet__bar { padding: 1.1rem 1.1rem 0.9rem; }
  .dw-sheet__body { padding: 1.1rem; }
  .dw-sheet__bar h2 { font-size: 1.4rem; }
}

@media (prefers-reduced-motion: reduce) {
  .dw-launcher, .dw-launcher__tip, .dw-launcher__mark, .dw-sheet, .dw-sheet[open],
  .dw-sheet::backdrop, .dw-sheet[open]::backdrop { transition: none; }
  .dw-launcher:hover, .dw-launcher:focus-visible { transform: none; }
}
"""
