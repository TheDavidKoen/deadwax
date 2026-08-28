# 0003 — Python for the agent, JavaScript only for the site

Status: Accepted
Date: 2026-08-27
Amends: [0001](0001-the-model-never-computes.md), [0002](0002-no-vector-database.md)

## Context

Deadwax was specified in Node.js with vanilla JavaScript and the Vercel AI SDK, and the
first stage was built that way. That choice had a coherent argument behind it: the site is
Astro, so one language spans the whole repository; the retrieval layer is hand-written, so
there is no Python numerical library to miss; and the free-tier constraint favours a
runtime with no build step.

The argument is coherent and still wrong, for a reason that has nothing to do with
JavaScript being a worse language.

The agentic-AI ecosystem is Python, and not marginally. Google's Agent Development Kit has
no JavaScript SDK. AutoGen is Python and .NET only. LangChain's JavaScript port exists but
its documentation, integrations and examples trail the Python library. There is no
JavaScript equivalent of numpy, pandas or scikit-learn, so any claim to machine-learning
foundations is unsupportable in JavaScript. Tracing and evaluation tooling — Langfuse,
pytest-based eval harnesses, the MCP SDK — are all more mature on the Python side.

Deadwax is a demonstration piece as well as a working system, and the ecosystem it will be
read against is Python. Building it in JavaScript means every framework worth naming is out
of reach, and the parts that are reachable are the second-class ports.

The cost of changing was measured before deciding: one 120-line script and a package
manifest. Nothing else had been written. At Stage 9, with retrieval and tracing in place,
the same change would have meant rewriting the project.

## Decision

Python for the agent, domain, retrieval, evaluation harness and MCP server. Astro and
JavaScript remain for the website, which was always a separate concern.

Consequences for the staged build:

- Stages 0 through 2 use the standard library and pure functions with no framework and no
  SDK. The raw HTTP call, the fixtures and the validator are written directly, so the
  mechanics are understood before any abstraction is introduced.
- LangChain arrives at Stage 3, where the tool loop begins — the first point at which a
  framework earns its place rather than merely being present.
- The site consumes the evaluation results as static JSON produced by the Python build. The
  two languages meet at a file, not at an API.
- The live demo runs Python on a Hugging Face Space. Cloudflare Pages serves static files
  and has no Python runtime, so the JavaScript side renders and links but never executes
  anything. Everything that runs is Python.

Both prior records stand. [0001](0001-the-model-never-computes.md) said the model never
computes; the deterministic half is now Python rather than JavaScript, and the decision is
untouched. [0002](0002-no-vector-database.md) said no vector database; exhaustive cosine
similarity over a few thousand chunks remains correct, and Python makes it easier to write
clearly rather than harder.

## Consequences

**Good.** Every framework named in the wider ecosystem becomes reachable. The evaluation
harness gains pytest and its parametrisation, which suits running each case repeatedly and
reporting a pass rate. SQLite is in the standard library, removing a dependency the
JavaScript version needed. Tracing and MCP both move to their better-supported SDKs.

**Costly.** The repository is now two languages, which is a real complexity increase even
though the boundary is clean. The Stage 0 work is rewritten. The author is rusty at Python
and is learning it alongside the agent concepts, which will make the early stages slower —
accepted deliberately, because the alternative is fluency in the wrong language.

**Accepted risk.** A two-language repository can rot at the seam. The mitigation is that
the seam is a JSON file written at build time, not a running service: if the Python side
stops producing it, the site fails loudly at build rather than silently at runtime.

**What this record does not claim.** Python is not a better language than JavaScript. This
is a decision about which ecosystem the work has to live in, and it would resolve the other
way for a project whose centre of gravity was the browser.
