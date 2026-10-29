# 0012 — The live demo runs on Render

Status: Accepted. Amends [0003](0003-python-for-the-agent.md).
Date: 2026-10-29

## Context

[ADR 0003](0003-python-for-the-agent.md) put the live demo on a Hugging Face Space, because
Cloudflare Pages has no Python runtime and the agent is Python. The demo was built for that:
a Gradio app with a CI job that uploaded it to the Space after the tests passed.

On the day it was first deployed, the Space could not be created. By October 2026 Hugging Face
requires a paid plan to create a Gradio or Docker Space. Static Spaces are still free, and a
free personal account can host up to two Gradio Spaces on ZeroGPU, but only once the account
is more than 30 days old, and ZeroGPU supports Python 3.12 and 3.10, not the 3.13 this project
pins. Every component must run on a free tier, so the host had to change.

The options considered:

- **Hugging Face PRO.** It works unchanged, and breaks the free-tier rule.
- **Hugging Face ZeroGPU.** It is free, but it means waiting a month, downgrading the whole
  project to Python 3.12, and occupying a GPU allocation with an app that never uses a GPU.
- **Vercel.** It runs Python 3.13 ASGI apps free, with fast cold starts. But it runs them as
  serverless functions, and a Gradio app is stateful across requests: a question joins a queue
  on one request and its answer streams back on another, and each visitor's conversation lives
  in the server's memory. Requests landing on different instances would fail intermittently.
  Doing it properly means replacing Gradio with a stateless endpoint and a static page.
- **Render.** A free web service runs one long-lived process, which is what Gradio expects,
  on Python 3.13, and deploys straight from the repository. It sleeps after 15 minutes without
  traffic and takes about a minute to wake.

## Decision

**The demo runs as a free Render web service, unchanged.** `render.yaml` declares it. Render
builds it with `uv sync --frozen`, so the demo installs exactly the versions in `uv.lock`, and
deploys only after the linked branch's CI checks pass. The Hugging Face deploy job and the
Space configuration are removed.

**The public link is a static waking page, also on Render.** While the demo sleeps nothing of
it is running, so it cannot explain its own absence. A static site never sleeps. Its page says
the demo is waking and why, loads the demo's favicon every few seconds, and goes to the demo the
first time it loads. A favicon only loads from the running app, never from Render's own
loading page, so the check cannot mistake one for the other.

## Consequences

**The first visitor after a quiet spell waits about a minute.** The waking page makes that
wait explained rather than broken.

**The daily question cap resets whenever the demo sleeps.** It lives in the process's memory,
and sleeping ends the process. The cap now limits a burst, not a day. The quota that matters
is protected elsewhere: the demo uses its own Google project, so however much it is used it
cannot spend the evaluation suite's allowance.

**The demo has a tighter machine.** Render does not publish the free instance's resources;
it is understood to be 512 MB. The demo measured about 234 MB with everything loaded, before
serving a request.

**The static site stays static.** ADR 0003's division holds: the JavaScript side renders and
links, and everything that runs is Python. Only the host of the Python changed.
