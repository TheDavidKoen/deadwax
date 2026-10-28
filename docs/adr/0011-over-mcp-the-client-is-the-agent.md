# 0011 — Over MCP, the client is the agent

Status: Accepted
Date: 2026-10-28

## Context

Stage 11 exposes Deadwax's tools over the Model Context Protocol, so any MCP client — Claude
Code in the first instance — can query the library. The tools already exist. The question is
what else has to travel with them, and what cannot.

Inside Deadwax, a question passes through four layers of control:

1. **The tools**, which compute every number and adjudicate every constraint.
2. **The tool descriptions**, which tell the model when and how to call them.
3. **The system prompt**, which sets the rules that span tools: no arithmetic, check
   feasibility first, cite passages, disclose estimates.
4. **The loop around the model**: the repair-loop supervisor that stops the agent once a
   playlist validates ([ADR 0005](0005-the-agent-does-not-decide-when-it-is-finished.md)),
   the step limit, model fallback, tracing, and the citation check that flags an id the
   model was never given.

Over MCP the client runs its own model in its own loop. Deadwax is no longer the agent. It is
a set of tools someone else's agent calls.

## Decision

**The server registers the agent's own tools, by reference.** Each MCP tool is the same
Python function the LangChain tool wraps, with the same name and the same description, read
from the LangChain tool object. There is no second copy of any description to drift, and a
test fails if the two ever differ. Tool descriptions are behaviour control
([architecture rule 2](../../README.md#architecture-rules)), so a fork would be two
behaviours with one name.

**The system prompt travels as the server's instructions.** MCP lets a server send
instructions to the client when it connects. Deadwax sends its system prompt verbatim. Whether
the client honours it is the client's decision.

**Every tool is declared read-only and closed-world.** None of them writes anything, and the
annotations say so, so a client can call them without asking for confirmation.

**The server loads LangChain without ever calling a model.** Registering the functions by
reference means importing them from `deadwax.agent`, which imports LangChain. The alternative
was to move the plain functions out of the agent package, and their descriptions with them. That is
a larger change to the files that hold behaviour, made for start-up time alone.

## Consequences

**Layers 1 and 2 hold over MCP. Layers 3 and 4 become requests.** The arithmetic still happens in
Python, the validator still adjudicates, and feasibility is still a tool that returns
`feasible: false`. Nothing the tools return depends on who called them. But the stop condition,
the step limit and the citation check live in Deadwax's loop, and an MCP client never runs that
loop. Over MCP, the descriptions and instructions are the only means the server has to steer
behaviour, and the client's model is free to ignore both.

**Rule 1 is enforced in what the tools return, not in what the client does.** A client model can still add
numbers up itself instead of quoting `total_duration_display`. Deadwax cannot prevent that. It
can only make sure the exact figure is always in the result, so that a client following its
descriptions never needs to calculate.

**Rule 7 is not affected.** It covers model calls, and the server makes none. The single
exception is the query embedding behind `enrich_artist`, which goes through the same traced
wrapper as before.

**The eval suite does not measure MCP clients.** It grades Deadwax's own loop on its pinned
model. How well another client follows the descriptions is unmeasured, and would need a
harness for each client.
