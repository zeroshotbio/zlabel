# zlabel

A small, readable library that **labels one scRNA-seq cluster from its marker
genes**, for whole-organism zebrafish (*Danio rerio*). You hand it a cluster's
marker genes (+ developmental stage); it returns a cell-identity label at the
deepest tier the evidence supports, with an evidence packet — or an honest
abstention. It does **not** cluster cells; that's the caller's job (scanpy, in a
notebook). This is "layer 1 only".

## The loop

1. **Normalize** each marker to its official ZFIN symbol (aliases + `a`/`b` paralogs).
2. **Score** markers against curated tissue/lineage panels → a ranked bucket table.
3. **Ground** the top markers in vivo (ZFIN expression → ZFA anatomy; plausible for the stage via ZFS?).
4. **Decide**: coherent markers + one dominant, corroborated bucket → assign with confidence; else abstain or roll up to a coarser tier.
5. **Emit** a `Label` evidence packet.

A label rests on **converging evidence, not one gene**. See
[`docs/design.md`](docs/design.md) for the full design.

## Status

Built in [7 phases, one PR each](.claude/docs/workflow.md). **Phase 1 ships the
data layer** — `zlabel.data`, the pure loaders for the three ontology authorities
zlabel grounds against (ZFA anatomy, ZFIN wildtype expression, ZFIN GAF gene
synonyms). The `label()` API arrives in a later phase.

## Quickstart

```bash
make setup                  # uv sync (Python 3.13)
bash scripts/setup_data.sh  # download ZFA + ZFIN GAF + ZFIN expression -> data/ontologies/
make verify                 # lint + types + tests
```

`data/` is gitignored; the test suite runs on small fixtures under `tests/fixtures/`
and needs no downloads.

## Develop

```bash
make format   # ruff format + safe fixes
make lint     # ruff check
make type     # pyright (basic)
make test     # pytest
```

Conventions: [`AGENTS.md`](AGENTS.md) (rules + architecture),
[`.claude/docs/`](.claude/docs/) (domain primer, workflow, git conventions).
