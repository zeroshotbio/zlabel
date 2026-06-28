# Agent instructions — zlabel

Canonical entry point for any AI assistant. Self-contained: reading this gives a
fresh agent enough to work here. Claude-Code harness specifics are in
[`CLAUDE.md`](CLAUDE.md).

## What zlabel is

A small, readable library that **labels a single scRNA-seq cluster from its marker
genes**, for whole-organism zebrafish (*Danio rerio*). You hand it a cluster's
marker genes (+ developmental stage); it returns a cell-identity label at the
deepest tier the evidence supports, with an evidence packet — or an honest
abstention. It does **not** cluster cells: that is the caller's job (scanpy, in a
notebook). This is "layer 1 only".

zlabel is the clean, layer-1 distillation of a much larger predecessor,
`daniotype` (at `../daniotype`), whose critical review motivated this rebuild.
Reuse daniotype's *pure* code (ontology loaders) verbatim; rewrite anything coupled
to its agent/schema machinery. **zlabel imports zero daniotype code.**

## Architecture (one line)

Normalize gene symbols → score markers against curated tissue panels (a coarse prior + anchor) →
name the cluster by descending from the winning panel's ZFA ontology anchor along well-supported
child paths (`resolve.py`, support-weighted: the markers must keep converging on a single subtype),
checked against ZFS stage → emit a `(label, depth, confidence, evidence)` packet, abstaining when
evidence does not converge.

## The annotation loop (what `label()` does)

1. **Normalize** every marker to its official ZFIN symbol (aliases + `a`/`b` paralogs).
2. **Score** markers against curated tissue/lineage panels → a ranked bucket table (a coarse prior, not the namer).
3. **Descend** on ZFA anatomy: each marker's in-vivo ZFIN expression votes for the terms it (and its ancestors) cover; seed at the panel's ontology anchor and roll down into the best-supported child while the markers converge on a single subtype — the deepest such term names the cluster (`resolve.py`).
4. **Guardrail (intrinsic) + stage**: the name is descended from the anchor, so it always sits under it (no separate contradiction check); an unsupported anchor falls back to the coarse panel bucket. Plausible for the stage (ZFS)?
5. **Decide**: assign with confidence, else abstain (`mixed/unresolved`) or roll up; a single sharply lineage-specific marker rescues an otherwise-weak signal (named from that marker's panel).
6. **Emit** a `Label` evidence packet — plus, on an abstention, the forcing evidence (`candidates`, `ood`, `margin`) so a caller can decide whether to force the top candidate itself.

Broad buckets are the honest call on a *low-resolution* cluster — **not a ceiling**.
The same `label()` resolves finer on subclusters (specific ZFA grounding + nested
panels). See [`docs/design.md`](docs/design.md) §Resolution.

## Commands

```bash
make setup    # uv sync (all groups + extras)
make format   # ruff format + safe fixes
make type     # pyright (basic)
make test     # pytest
make verify   # lint + docstrings + types + tests
make eval     # regenerate the Daniocell baseline report (needs data/ontologies)
make gate     # regression wall: regenerate baseline, fail on drift / overcall regression
make eval-zscape    # regenerate the held-out ZSCAPE 2nd-atlas report (needs data/ontologies)
make gate-zscape    # held-out wall: ZSCAPE report drift, with a directional (generalization) read
make eval-zebrahub  # regenerate the held-out Zebrahub 3rd-atlas report (needs data/ontologies)
make gate-zebrahub  # held-out wall: Zebrahub report drift, with a directional (generalization) read
make gate-all       # all regression walls: Daniocell (hard) + ZSCAPE + Zebrahub (held-out)
make hooks    # install the pre-commit hook that runs `make gate-all` on engine/panel/benchmark changes
```

## Tech stack

- Python 3.13 · uv · ruff (120 cols) · pyright (basic) · pytest.
- **Core deps (keep tiny, added per phase):** Phase 1 obonet + networkx; Phase 2 adds pyyaml; Phase 3 adds pydantic; Phase 4b keeps the core unchanged (the evaluator is stdlib + core deps).
- **Not in core:** scanpy / anndata (optional `[eval]` extra — the benchmark builder; also notebooks); pydantic-ai (optional `[llm]` extra, added later).

## Rules

- **uv only.** Never pip. `uv add` / `uv sync` / `uv run python` (never bare `python`).
- **Simplicity is the spec.** Readable top-to-bottom (the nanoGPT bar). If a piece is
  hard to explain, it is wrong. No abstraction the task does not need.
- **The "model" is data.** Domain knowledge lives in `panels.yaml`, not buried in code.
- **Deterministic core.** v1 has no LLM in the labeling decision; the LLM is a
  designed-in fast-follow (see design §LLM).
- **Small public surface.** `Labeler` and `Label` (plus the Phase 1/2 primitives) are the
  public API; `resolve.py` and the other `src/zlabel/` modules are the internal/advanced
  surface — import them directly (`import zlabel.resolve`), do not re-export them at top level.
- **Google-style docstrings, written as plain text.** `name (type): desc` for Args;
  a type-first `Returns:` (`type: desc`). **No backticks**, no reST (`:roles:`), and
  no block markdown (bullet lists, fences, headers) inside Python docstrings or
  comments — they don't render reliably there, so keep code prose plain. (Backticks
  belong in Markdown files like this one.) `make lint-docstrings` enforces it.
- **Verify library docs against the pinned version online**, not from memory.
- **One PR per build phase** ([`.claude/docs/workflow.md`](.claude/docs/workflow.md)).

## Where to look

- [`docs/design.md`](docs/design.md) — authoritative design + rationale.
- [`.claude/docs/domain.md`](.claude/docs/domain.md) — zebrafish + ontology primer.
- [`.claude/docs/workflow.md`](.claude/docs/workflow.md) — the 7-phase PR-gated build.
- [`.claude/docs/git-conventions.md`](.claude/docs/git-conventions.md) — commits + PRs.
