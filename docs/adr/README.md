# Architecture decision records

One file per significant decision, in the format described by Michael Nygard:
context, decision, consequences — including the consequences we did not want.

A decision belongs here if reversing it later would be expensive, or if a reasonable
engineer would ask "why did you do it that way?". Library choices that could be swapped in
an afternoon do not need a record.

Records are immutable once merged. If a decision is later reversed, add a new record that
supersedes the old one and update the old one's status. Do not edit history — the fact
that we changed our mind, and why, is the useful part.

| # | Decision | Status |
| --- | --- | --- |
| [0001](0001-the-model-never-computes.md) | The model never computes | Accepted, amended by 0003 and 0007 |
| [0002](0002-no-vector-database.md) | No vector database | Accepted, amended by 0003 |
| [0003](0003-python-for-the-agent.md) | Python for the agent, JavaScript only for the site | Accepted |
| [0004](0004-agent-convergence-is-enforced-in-code.md) | Agent convergence is enforced in code, not requested in a prompt | Accepted, extended by 0005 |
| [0005](0005-the-agent-does-not-decide-when-it-is-finished.md) | The agent does not decide when it is finished | Accepted, amended by 0006 |
| [0006](0006-an-empty-brief-is-a-question-not-a-playlist.md) | An empty brief is a question, not a playlist | Accepted |
| [0007](0007-where-the-model-never-computes-line-falls.md) | Where the "model never computes" line falls | Accepted |
