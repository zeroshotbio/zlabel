<h1 align="center">zlabel</h1>

<p align="center">
  <em>Label one zebrafish scRNA-seq cluster from its marker genes — with its evidence, or an honest abstention.</em>
</p>

<p align="center">
  <code>Python 3.13</code> · <code>uv</code> · <code>ruff</code> · <code>pyright</code> · <code>pytest</code>
</p>

---

zlabel is a small, readable library for whole-organism zebrafish (*Danio rerio*).
You hand it a cluster's marker genes (plus the developmental stage); it returns a
cell-identity label **at the deepest tier the evidence supports**, packaged with the
evidence behind it — or `mixed/unresolved` when the evidence doesn't converge. It
does **not** cluster cells; that's the caller's job (scanpy, in a notebook). This is
"layer 1 only".

New to the domain? See the [glossary & concepts](docs/glossary.md) (ELI5).

## The loop

1. **Normalize** each marker to its official ZFIN symbol (aliases + `a`/`b` paralogs).
2. **Score** markers against curated tissue/lineage panels → a ranked bucket table.
3. **Ground** the top markers in vivo (ZFIN expression → ZFA anatomy; plausible for the stage via ZFS?).
4. **Decide** — coherent markers + one dominant, corroborated bucket → assign with confidence; else abstain or roll up to a coarser tier.
5. **Emit** a `Label` evidence packet.

A label rests on **converging evidence, not one gene**. The full design is in
[`docs/design.md`](docs/design.md).

## Status

Built in [7 phases, one PR each](.claude/docs/workflow.md). **Phase 1 ships the data
layer** — `zlabel.data`, the pure loaders for the three authorities zlabel grounds
against (ZFA anatomy, ZFIN wildtype expression, ZFIN GAF gene synonyms). The
`label()` API arrives in a later phase.

## Quickstart

```bash
make setup                  # uv sync (Python 3.13)
bash scripts/setup_data.sh  # download ZFA + ZFIN GAF + ZFIN expression -> data/ontologies/
make verify                 # lint + docstrings + types + tests
```

`data/` is gitignored; the test suite runs on small fixtures under `tests/fixtures/`
and needs no downloads.

## Commands

Run `make` (or `make help`) to see everything. The essentials:

| Command | What it does |
| --- | --- |
| `make setup` | Sync the full dev environment (all groups + extras) |
| `make format` | ruff format + safe autofixes |
| `make verify` | The PR gate: lint + docstrings + types + tests |

## Where to look

- [`docs/glossary.md`](docs/glossary.md) — terms, data authorities, and data flow (ELI5).
- [`docs/design.md`](docs/design.md) — authoritative design + rationale.
- [`AGENTS.md`](AGENTS.md) — rules + architecture for contributors (human or AI).
- [`.claude/docs/`](.claude/docs/) — domain primer, build workflow, git conventions.
