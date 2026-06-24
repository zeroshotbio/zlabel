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

**For AI assistants and agents:** [`AGENTS.md`](AGENTS.md) is the self-contained
entry point — rules, architecture, commands, and build context in one file.
[`CLAUDE.md`](CLAUDE.md) adds harness wiring for Claude Code. The build is PR-gated
(one PR per phase; do not merge without human review).

## The loop

1. **Normalize** each marker to its official ZFIN symbol (aliases + `a`/`b` paralogs).
2. **Score** markers against curated tissue/lineage panels → a ranked bucket table (a coarse prior, not the namer).
3. **Descend** from the winning panel's ZFA anchor — each marker's in-vivo ZFIN expression votes for the anatomy terms it covers; the namer rolls down into the best-supported child while the markers keep converging on one subtype, stopping at the deepest term they still agree on.
4. **Guardrail (intrinsic) + stage** — the name is descended from the anchor, so it always sits at or under it; an anchor the markers don't support falls back to the coarse panel bucket. Check stage plausibility (ZFS).
5. **Decide** — assign with confidence, or abstain / roll up to a coarser tier when nothing dominates; a single sharply lineage-specific marker (e.g. `myod1` → muscle) rescues an otherwise-weak signal, named from that marker's panel.
6. **Emit** a `Label` evidence packet (named term, depth, the `panel_bucket` prior, convergent genes, confidence, evidence) — plus, on an abstention, the **forcing evidence** the *caller* decides on: the `candidates` set, the runner-up `margin`, and an `ood` flag (`in_set` = force-able; `structural` / `doublet` / `no_signal` = genuinely unassigned). `structural` / `doublet` are trustworthy when they fire; `in_set` is a soft signal — a broad attractor can mask a blind-spot (see [§Resolution](docs/design.md)).

A label rests on **converging evidence, not one gene**. The full design is in
[`docs/design.md`](docs/design.md).

## Status & Roadmap

Built in [7 phases, one PR each](.claude/docs/workflow.md):

- [x] **Phase 1** — Skeleton + data (`zlabel.data` loaders for ZFA, ZFIN expression, GAF synonyms; fixture tests)
- [x] **Phase 2** — Genes + panels (`normalize_symbol`, `panels.yaml` with curated buckets, `score_markers`)
- [x] **Phase 3** — Ground + label (`ground.py` lookups → converging-evidence decision → `Label`)
- [x] **Phase 4a** — Resolution engine (`resolve.py` support-weighted, anchor-rooted ZFA convergence namer; panels supply the coarse prior + anchor, and the guardrail is intrinsic to the descent)
- [x] **Phase 4b** — Eval (`build_daniocell_eval.py` + `evaluate.py` + the Daniocell crosswalk; broad agreement, coverage, named/fallback/abstain split, parent-child overcall audit)
- [ ] **Phase 5** — CLI + notebook 01 (`zlabel label/eval`; the one-cluster walkthrough)
- [ ] **Phase 6** — Notebooks 02/03 (scanpy clustering → markers → zlabel; end-to-end 48 hpf)
- [ ] **Phase 7** — LLM (optional) (`explain.py` narrator behind the `[llm]` extra)

## Usage

Phases 1–4a ship, plus the Phase 4b Daniocell evaluation harness. All loaders run offline (no network after `setup_data.sh`).

```python
# --- Phase 3: label a cluster end-to-end ---
from zlabel import Labeler

lab = Labeler(stage_hpf=48)   # loads ZFA + ZFIN-expr + GAF + panels once
label = lab.label(["mylpfa", "acta1b", "tnnt3a", "myod1", "myog"])
print(label.to_yaml())        # bucket, confidence, evidence packet, or abstention

# Introspect the same decision (advanced surface): the panel ladder, the full ZFA
# convergence descent with per-term gate pass/fail (near-misses included), and the
# branch taken. trace.label is identical to lab.label([...]).
trace = lab.trace(["mylpfa", "acta1b", "tnnt3a", "myod1", "myog"])
print(trace.to_yaml())
```

```python
import zlabel

# --- Phase 1: load the data authorities ---
synonyms = zlabel.load_gene_synonym_map("data/ontologies/zfin.gaf")
synonyms["flk1"]   # -> {'kdrl'}    alias resolved to current ZFIN symbol
synonyms["kdrl"]   # -> {'kdrl'}    current symbol is its own identity

zfa_ontology = zlabel.load_zfa("data/ontologies/zfa.obo")
zlabel.term_name(zfa_ontology, "ZFA:0005307")   # -> 'endothelial cell'

# --- Phase 2: normalize markers and score panels ---
result = zlabel.normalize_symbol("flk1", synonyms)
# NormalizedSymbol(input='flk1', status='resolved', symbols=frozenset({'kdrl'}), note=None)

panels = zlabel.load_panels("src/zlabel/panels.yaml")
# 33 panels (31 identity lineages + 2 state programs) spanning every germ layer;
# see docs/reference/panels_and_markers_reference.md for the full bucket list.

markers = ["mylpfa", "acta1b", "tnnt3a", "myod1", "myog", "hbae1.1", "kdrl"]
normalized = zlabel.normalize_markers(markers, synonyms)   # normalize once, then score
scores = zlabel.score_markers(normalized, panels)
scores[0]   # BucketScore(bucket='muscle', score=0.8105, kind='identity', ...)
scores[1]   # BucketScore(bucket='blood_erythroid', score=0.0979, ...)
```

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
- [`docs/reference/panels_and_markers_reference.md`](docs/reference/panels_and_markers_reference.md) — every panel bucket, its markers, ZFA anchor, and evidence (the companion to `panels.yaml`).
- [`AGENTS.md`](AGENTS.md) — rules + architecture for contributors (human or AI).
- [`.claude/docs/`](.claude/docs/) — domain primer, build workflow, git conventions.
- [`notebooks/build-demos/`](notebooks/build-demos/) — executable build walkthroughs (one per completed phase).
