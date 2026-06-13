# Build-Demos Notebook Guidance

This file defines expectations for notebooks in `notebooks/build-demos/`.

## Purpose

- Build-demos are phase walkthroughs for library internals.
- They are not the final user workflow notebooks under `notebooks/demo/`.
- Each notebook should make Phase N understandable in one pass.

## Keep Notebooks Aligned To The Core Loop

Use the canonical loop language from `docs/design.md`:

1. Normalize symbols
2. Score against panels
3. Ground in vivo evidence
4. Decide
5. Emit a `Label` packet

State clearly which steps are implemented in the current phase and which are future phases.

## Required Notebook Shape

Each build-demo notebook should include:

1. Title + phase scope
2. Prerequisites (repo-root commands)
3. A bootstrap/setup code cell
4. Section rhythm: markdown context -> code -> short interpretation
5. A synthesis section that names the phase handoff artifact
6. A final "What's next" section linking to the next phase notebook

## Execution Flow Requirements

- The core path must run top-to-bottom in a fresh kernel.
- Minimize hidden cross-cell state. If optional cells depend on prior variables, guard or reconstruct them.
- Keep optional sections explicitly labeled as optional.
- Avoid empty trailing cells.

## Visuals And Output Hygiene

- Add a one-line "What to look for" caption before each major visual/output block.
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
