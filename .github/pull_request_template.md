## What this changes

<!-- One paragraph. What is different after this merges. -->

## Stage

<!-- e.g. Stage 3 - First tool loop. Link the PLAN.md acceptance criteria. -->

## Acceptance criteria

- [ ] The stage's "Done when" condition in PLAN.md is met

## Behavioural change

Does this touch a prompt, a tool description, or a model?

- [ ] No
- [ ] Yes — eval scores before and after are recorded below and in the commit message

| | Tool selection | Parameters | Answer |
| --- | --- | --- | --- |
| Before | | | |
| After | | | |

## Architecture rules

- [ ] No arithmetic, threshold or constraint check moved into a prompt (rule 1)
- [ ] Any new violation returns a code, the offending ids and a remedy (rule 3)
- [ ] Any inferred value carries `provenance`, and messages about it say so (rule 6)
- [ ] Every model call goes through the traced wrapper (rule 7)
- [ ] No new dependency, or the dependency was agreed first
