# zlabel — design

## What it is

A small, readable library that **labels one scRNA-seq cluster from its marker
genes**, for whole-organism zebrafish (*Danio rerio*). 

**Input**: a cluster's marker genes (+ developmental stage).<br>
**Output**: a cell-identity label **at the deepest tier the evidence supports**, with an evidence packet — or an honest abstention. 

> [!CAUTION]
> It does not cluster cells (the caller does, with `scanpy` probably). 

This is **layer 1 only**.

### Rationale

zlabel is the clean distillation of `daniotype` (`../daniotype`), a ~11k-LOC
predecessor (descent + spine + gate + walk + audit + log). A critical review of
daniotype found it ran but could not *demonstrate* it worked (no validation leg),
its LLM de-novo naming was unmeasured and likely sparse at 48 hpf, and it could
confidently name QC artifacts. The conclusion was to rebuild the one valuable thing
— grounded cluster naming — as something a person can read top-to-bottom (the
nanoGPT / smolagents bar), with a validation leg from day one.

## What it does (the loop)

A label rests on **converging evidence, not one gene**:

1. **Normalize gene symbols** → official ZFIN symbol (resolve aliases + `a`/`b` paralogs) before anything else.
2. **Score markers against curated tissue panels** → a ranked bucket table; the winning panel is the coarse prior and ontology-anchor guardrail.
3. **Converge on ZFA anatomy** → for each marker, look up ZFIN in-vivo expression and walk the ZFA ancestor DAG; tally distinct genes per anatomy term; name the cluster the most specific term that clears the convergence and IC gates. Depth falls out of the evidence: a tight endothelial panel resolves to a cell type; a broad neural panel stays at CNS.
4. **Guardrail** → if the ZFA-voted term contradicts the panel's ontology anchor, discard the vote and fall back to the coarse panel bucket. Check stage plausibility (ZFS) as a confidence component.
5. **Decide** → one dominant, corroborated bucket with convergent anatomy → assign with confidence; otherwise `mixed/unresolved` (honest abstention) or a germ-layer rollup.
6. **Emit a `Label` evidence packet** → bucket (named ZFA term or coarse fallback), levels (ZFA ancestry chain), depth, panel_bucket (the prior), convergent_genes, confidence, expression_evidence, rationale.

> [!WARNING]
> The LLM is **not** in this loop for v1 (see §LLM).

### Resolution: the evidence names at whatever depth it supports

`label(markers)` is **resolution-agnostic** — it returns the *deepest ZFA anatomy term
the markers converge on in vivo* and rolls up rather than overcalling. The curated
panels are a **coarse prior and ontology-anchor guardrail**, not the naming authority.
`Label.depth` (`len(levels)`) is a real, evidence-dependent integer — not a hardcoded tier
ladder. The same function resolves finer on a tighter subcluster and shallower on a
heterogeneous one; that is the engine being honest, not a failure.

The panels themselves are a versioned **v1 starter set** (see `docs/reference/
cell_labelling_playbook.md §7`): *"These are starter panels for first-pass annotation.
They must be versioned and adapted to stage, genome build, sequencing chemistry, and
atlas source. Do not treat this table as a final marker authority."* They will be
replaced by a curated gold standard as the eval matures.

What v1 deterministic *won't* do: **open-ended de-novo naming of types with no
expression footprint.** That is the LLM's job (§LLM).

## Public surface (the whole API)

### Phase 2 primitives (lower-level API)

Gene normalization and panel scoring are live:

```python
import zlabel

synonyms = zlabel.load_gene_synonym_map("data/ontologies/zfin.gaf")
result = zlabel.normalize_symbol("flk1", synonyms)
# NormalizedSymbol(input='flk1', status='resolved', symbols=frozenset({'kdrl'}), note=None)

panels = zlabel.load_panels("src/zlabel/panels.yaml")   # 14 curated buckets
scores = zlabel.score_markers(["mylz2", "acta1b", "tnnt3a", "myod1", "myog"], panels, synonyms)
scores[0]   # BucketScore(bucket='muscle', score=0.8105, kind='identity', ...)
```

### Phase 4a (current — the resolution engine)

```python
from zlabel import Labeler

labeler = Labeler(stage_hpf=48)                  # loads ZFA + ZFIN-expr + GAF + panels once
label = labeler.label(["mylz2", "acta1b", "tnnt3a", "myod1", "myog"])
# Label(bucket="muscle cell",                     # named ZFA term, not the panel bucket
#       levels=("cell", "muscle cell"),            # ZFA ancestry chain
#       depth=2,                                   # len(levels)
#       panel_bucket="muscle",                     # coarse prior (kept visible)
#       convergent_genes=("acta1b", "myog", "mylpfa"),  # anatomy-vote evidence
#       confidence="high", zfa_id="ZFA:0009234",
#       expression_evidence=[...], abstained=False, next_step="subcluster")
print(label.to_yaml())                           # the evidence packet
```

One entry point. The public surface is small — `Labeler`, `Label`, and the Phase 1/2
primitives — while the decision code beneath it stays readable and unit-tested.

### Confidence rubric (provisional — calibrated in Phase 4b eval)

`Labeler` grades an assigned call on a weighted 0–1 score: **coherence** 0.40 (rank-weighted
strength of the winner's markers) + **margin** 0.30 (lead over the runner-up) + **grounding**
0.20 (fraction of the winning panel's matched markers whose ZFIN expression grounds under the
named ZFA term, or the panel anchor when the vote fails) + **stage** 0.10 (fraction on-stage for the
sample). Tiers: ≥ 0.80 `high`, ≥ 0.60 `medium`, else `low`. Two caps keep it honest — a
germ-layer rollup never exceeds `medium`, and `high` requires real anatomy convergence (the
guardrail blocking the named term drops grounding and prevents false `high`). The weights are a
first cut; Phase 4b eval calibrates them.

## Repo structure (~7 core files, ~1,800 LOC core)

Files marked [P1] / [P2] shipped; later phases show their planned target.

```text
zlabel/
  pyproject.toml          # uv · ruff (120) · pyright basic · py3.13 · minimal deps  [P1]
  README.md               # what it is + the loop + quickstart                         [P1]
  Makefile                # setup / format / lint / lint-docstrings / type / test / verify [P1]
  scripts/
    setup_data.sh         # curl zfa.obo, zfin.gaf, zfin_wildtype_expression.txt -> data/ontologies/  [P1]
    build_daniocell_eval.py  # Daniocell 19 broad tissues + cluster markers -> benchmarks/ csv  [P4]
  src/zlabel/
    data.py     # LIFT (pure): load ZFA via obonet; parse ZFIN-expr TSV; load GAF synonym map  [P1]
    genes.py    # normalize_symbol() via GAF alias/paralog resolution                           [P2]
    panels.yaml # THE MODEL: curated buckets -> {germ_layer, tissue, lineage, kind, markers[], cite, subpanels?}  [P2]
    panels.py   # load panels + rank-weighted overlap score (readable, no heavy dep)            [P2]
    ground.py   # pure fns: expression_lookup / grounds_under / stage_plausibility              [P3 shipped]
    label.py    # converging-evidence decision -> Label  (the heart)                           [P3+4a shipped]
    models.py   # Label evidence packet (pydantic) + to_yaml()                                 [P3+4a shipped]
    resolve.py  # IC-weighted ZFA convergence namer (build_ic + resolve_label)                 [P4a shipped]
    evaluate.py # run on labeled clusters -> agreement + coverage + calibration                [P4b]
    explain.py  # OPTIONAL [llm] extra: thin narrator over a finished Label                    [P7]
    cli.py      # typer: zlabel label --markers ... --stage 48 ; zlabel eval <csv>            [P5]
  benchmarks/   # committed eval substrate (data/ is gitignored, so eval data lives here)     [P4]
  data/         # gitignored: downloaded ontologies
  tests/        # genes, panel scoring, ground lookups, label decision, eval — real unit tests, no LLM
  notebooks/
    build-demos/
      phase_01.ipynb           # data-layer walkthrough (Phase 1)                   [P1 shipped]
      phase_02.ipynb           # genes + panels walkthrough (Phase 2)               [P2 shipped]
    demo/
      01_label_one_cluster.ipynb    # the muscle-cluster walkthrough                [P5]
      02_cluster_with_scanpy.ipynb  # layer-2: adata -> leiden -> rank_genes -> zlabel [P6]
      03_end_to_end.ipynb           # layer-3: a real 48 hpf subset, start to finish   [P6]
```

**Core deps (added per phase):** Phase 1 obonet + networkx; Phase 2 adds pyyaml;
Phase 3 adds pydantic; Phase 4 adds pandas + numpy. **No scanpy, anndata,
decoupler, or pydantic-ai in the core** — those live only in the optional `[llm]`
extra (pydantic-ai) and the notebooks (scanpy/anndata). The labeler takes strings
in, hands an evidence packet out.

## Lift vs. rewrite (zero daniotype dependency)

- **LIFT ~verbatim (pure, already clean):** the ZFA OBO loader + edge-type-aware
  ancestors; the ZFIN wildtype-expression TSV parser; the GAF synonym map; the ZFS
  stage→hpf table. Sources: daniotype `ontology/{zfa,zfin_expression,go,zfs_stages}.py`.
- **REWRITE as small pure functions:** the grounding lookups (strip the pydantic-ai
  `RunContext` / `DescentDeps` wrappers → `f(loaded_data, query) -> dict`) and the
  gene normalizer.
- **NEW (the value):** `panels.yaml`, the overlap scorer, the decision in `label.py`,
  the `Label` packet, the `evaluate` harness.
- **DROP entirely:** descent panel/orchestrator, gate, decision-log/replay, walk,
  audit notebooks, schema registry, marker DB — all of daniotype's machinery.

## Validation (built in from day one)

`build_daniocell_eval.py` produces a small CSV (`cluster_id, markers, broad_tissue`)
from **Daniocell's 19 broad tissue assignments** (ground truth) + its per-cluster
markers, committed under `benchmarks/`. `evaluate.py` runs zlabel on it and reports
three numbers: **broad-bucket agreement**, **coverage** (non-abstain rate), and
**abstention calibration** (accuracy on confident calls vs. abstain rate). Optional
comparison points: a bare-LLM baseline (GPTCellType-style) and a panels-only-no-
ontology score, to see what each layer earns. Daniocell's broad-tissue labels make
this a clean benchmark — no fine-naming ambiguity, no platform-gap confound.

## Build order (7 phases, one PR each)

See [`.claude/docs/workflow.md`](../.claude/docs/workflow.md) for the per-phase
discipline and the review bar.

1. **Skeleton + data** — repo, `pyproject`, `setup_data.sh`, `data.py` loaders + fixture tests.
2. **Genes + panels** — `normalize_symbol`, `panels.yaml`, the overlap scorer + tests.
3. **Ground + label** — grounding lookups, then the decision in `label.py` → `Label`; unit-test the worked examples.
4. **Resolution engine + eval** — split into two PRs:
   - **4a (engine)** — `resolve.py` IC-weighted ZFA convergence namer; `label.py`/`models.py` wired to name from ZFA; panels demote to coarse prior + guardrail.
   - **4b (eval)** — `build_daniocell_eval.py` + `evaluate.py`; first broad-agreement + depth numbers. *The proof it works.*
5. **CLI + notebook 01** — `zlabel label/eval`; the one-cluster walkthrough.
6. **Notebooks 02/03** — scanpy clustering → markers → zlabel, then end-to-end.
7. **LLM (optional)** — `explain.py`, behind the `[llm]` extra.

## LLM: deferred fast-follow

v1 ships deterministic, no pydantic-ai in core — **but the seam is designed in.**
`label.py` returns a structured `Label` packet specifically so an LLM step drops in
without reshaping the core. Two roles, in order:

1. **Narrator** (`explain.py`, trivial) — prose rationale over a finished, already-decided packet.
2. **Fine de-novo namer** (the real reason we want it) — on subclusters with no
   curated panel, coin a specific name from looked-up ZFA / expression evidence
   under cite-discipline. This is where "label lower-level clusters" becomes fully
   general.
