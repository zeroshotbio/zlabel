# Build-Demos Notebook Guidance

This file defines expectations for notebooks in `notebooks/build-demos/`.

## Purpose

- Build-demos are phase walkthroughs for library internals.
- They are not the final user workflow notebooks under `notebooks/demo/`.
- Each notebook should make Phase N understandable in one pass.

## Keep Notebooks Aligned To The Core Loop

Use the canonical loop language from `docs/design.md`:

1. Normalize symbols
2. Score against panels (a coarse prior)
3. Converge on ZFA anatomy (the namer)
4. Guardrail against the panel's ontology anchor
5. Decide
6. Emit a `Label` packet

State clearly which steps are implemented in the current phase and which are future phases.

## Required Notebook Shape

Each build-demo notebook should include:

1. Title + phase scope
2. Prerequisites (repo-root commands)
3. A bootstrap/setup code cell
4. Section rhythm: markdown context -> code -> short interpretation
5. A synthesis section that names the phase handoff artifact
6. A final "What's next" section linking to the next phase notebook
7. An "Explore it yourself" section — a documented helper the reader re-runs with their
   own inputs (e.g. `label_and_explain`, `explore_gene`, `score_panels`) plus a "now try
   your own" cell. Build-demos are exploration tools, not just linear demonstrations.
8. A deep-unfold of the phase's keystone function(s): a markdown cell that walks the
   algorithm step by step, then inline code that reproduces those steps on the real
   example and asserts the result matches the library call.

## Execution Flow Requirements

- The core path must run top-to-bottom in a fresh kernel.
- Minimize hidden cross-cell state. If optional cells depend on prior variables, guard or reconstruct them.
- Keep optional sections explicitly labeled as optional.
- Avoid empty trailing cells.

## Visuals And Output Hygiene

- Add a one-line "What to look for" caption before each major visual/output block.
- Use `rich` (Table / Panel / Tree) for structured text output, with a consistent colour
  key (green = resolved/agree/identity, yellow = ambiguous/state/warning, red =
  unresolved/disagree, dim = zero/abstain). rich augments the interactive viz (pyvis /
  plotly / matplotlib); it does not replace it.
- Write heavy, stepwise comments in code cells so a reader follows the logic line by line.
- Prefer lightweight visuals that explain the current phase; avoid adding heavy tooling unless needed.
- Keep notebook diffs reviewable: clear noisy or bulky outputs (especially embedded interactive HTML) before committing.

## Terminology And Consistency

- Stay consistent with `AGENTS.md`, `docs/design.md`, and `docs/glossary.md`.
- Use "broad-first" framing where relevant.
- Distinguish clearly between:
  - input symbols vs resolved symbols
  - ranked bucket table vs final label decision

## Pre-PR Checklist

- Notebook runs cleanly from top to bottom.
- Narrative and code outputs agree (no stale comments).
- Optional sections are clearly marked.
- Links to adjacent phase notebooks are present.
- `make verify` passes after notebook/doc updates.
