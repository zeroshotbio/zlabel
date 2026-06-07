# zlabel — design

## What it is

A small, readable library that **labels one scRNA-seq cluster from its marker
genes**, for whole-organism zebrafish (*Danio rerio*). Input: a cluster's marker
genes (+ developmental stage). Output: a cell-identity label **at the deepest tier
the evidence supports**, with an evidence packet — or an honest abstention. It does
not cluster cells (the caller does, with scanpy). This is **layer 1 only**.

### Rationale

zlabel is the clean distillation of `daniotype` (`../daniotype`), a ~11k-LOC
predecessor (descent + spine + gate + walk + audit + log). A critical review of
daniotype found it ran but could not *demonstrate* it worked (no validation leg),
its LLM de-novo naming was unmeasured and likely sparse at 48 hpf, and it could
confidently name QC artifacts. The conclusion was to rebuild the one valuable thing
— grounded cluster naming — as something a person can read top-to-bottom (the
nanoGPT / smolagents bar), with a validation leg from day one.

## What it does (the loop)

Whole-organism, low-resolution atlases are labeled **broad-first**: assign each
cluster to a high-level bucket (neural, epidermis, muscle, blood, immune,
endothelium, endoderm/gut, mesenchyme/cartilage, notochord, pigment, germline,
cycling, or mixed/unresolved), then subcluster later. A label rests on **converging
evidence, not one gene**:

1. **Normalize gene symbols** → official ZFIN symbol (resolve aliases + `a`/`b` paralogs) before anything else.
2. **Score markers against curated tissue panels** → a ranked bucket table (negative evidence falls out for free).
3. **Ground / corroborate** → where do the top markers express in vivo (ZFIN → ZFA anatomy)? Is the bucket plausible for the sample's stage (ZFS)?
4. **Decide** → coherent markers + one dominant, corroborated bucket → assign with confidence; otherwise `mixed/unresolved` (honest abstention) or a coarser tier.
5. **Emit a `Label` evidence packet** → bucket, levels, confidence, positive markers, panel scores, expression evidence, ZFA/ZFS/optional CL ids, rationale, `next_step: subcluster`.

The LLM is **not** in this loop for v1 (see §LLM).

### Resolution: broad-first is a default, not a ceiling

`label(markers)` is **resolution-agnostic** — it returns the *deepest tier the
evidence supports* and rolls up rather than overcalling. Broad buckets are what an
*honest* call looks like on a *low-resolution* cluster, not a cap. The same function
on a finer subcluster yields a finer label via three mechanisms, none needing code
changes:

1. **Ontology grounding already resolves fine** — `expression_lookup` → ZFIN
   in-vivo expression → ZFA (~2,860 classes down to specific anatomy). Specific
   markers ground to a specific ZFA term, finer than any broad panel.
2. **Hierarchical panels** — `panels.yaml` is nested (`muscle → {fast, slow,
   cardiac, myoblast …}`). Re-scoring a subcluster against sub-panels resolves
   finer; adding resolution = adding YAML, not code.
3. **The recursive loop** (notebooks) — cluster → label broad → subcluster each
   bucket → re-label. `Label.levels` grows deeper (`germ_layer → tissue → lineage →
   cell_type → subtype`); a `granularity` field reports how deep it got.

What v1 deterministic *won't* do: **open-ended fine de-novo naming of types with no
curated panel.** That is the LLM's job (§LLM).

## Public surface (the whole API)

```python
from zlabel import Labeler

labeler = Labeler(stage_hpf=48)                  # loads ZFA + ZFIN-expr + GAF + panels once
label = labeler.label(["mylz2", "acta1b", "tnnt3a", "myod1", "myog"])
# Label(bucket="muscle", levels=("mesoderm", "muscle", "skeletal muscle lineage"),
#       confidence="high", zfa_id="ZFA:0001056", panel_scores={...},
#       expression_evidence=[...], abstained=False, next_step="subcluster")
print(label.to_yaml())                           # the evidence packet
```

One entry point. Everything below it is short and inspectable.

## Repo structure (~7 core files, ≤~700 LOC core)

```text
zlabel/
  pyproject.toml          # uv · ruff (120) · pyright basic · py3.13 · minimal deps
  README.md               # what it is + the loop + quickstart
  Makefile                # setup / format / type / test
  scripts/
    setup_data.sh         # curl zfa.obo, zfin.gaf, zfin_wildtype_expression.txt -> data/ontologies/
    build_daniocell_eval.py  # one-off: Daniocell 19 broad tissues + cluster markers -> benchmarks/ csv
  src/zlabel/
    data.py     # LIFT (pure): load ZFA via obonet; parse ZFIN-expr TSV; load GAF synonym map
    genes.py    # REWRITE-minimal: normalize_symbol() via GAF alias/paralog resolution
    panels.yaml # THE MODEL: curated buckets -> {germ_layer, tissue, lineage, markers[], cite}
    panels.py   # load panels + rank-weighted overlap score (readable, no heavy dep)
    ground.py   # REWRITE-minimal (pure fns): expression_lookup / anatomy_search / anatomy_lineage / stage_ok
    label.py    # the converging-evidence decision -> Label  (the heart)
    models.py   # Label evidence packet (pydantic) + to_yaml()
    evaluate.py # run on labeled clusters -> agreement + coverage + calibration
    explain.py  # OPTIONAL [llm] extra: thin narrator over a finished Label (never picks the label)
    cli.py      # typer: `zlabel label --markers ... --stage 48` ; `zlabel eval <csv>`
  benchmarks/   # committed: curated eval substrate (data/ is gitignored, so eval data lives here)
  data/         # gitignored: downloaded ontologies
  tests/        # genes, panel scoring, ground lookups, label decision, eval — real unit tests, no LLM
  notebooks/
    01_label_one_cluster.py    # the muscle-cluster walkthrough
    02_cluster_with_scanpy.py  # layer-2 demo: adata -> leiden -> rank_genes -> zlabel
    03_end_to_end.py           # layer-3 demo: a real 48 hpf subset, start to finish
```

**Core deps:** pandas, numpy, obonet, networkx, pyyaml, pydantic. **No scanpy,
anndata, decoupler, or pydantic-ai in the core** — those live only in the optional
`[llm]` extra (pydantic-ai) and the notebooks (scanpy/anndata). The labeler takes
strings in, hands an evidence packet out.

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
4. **Eval** — `build_daniocell_eval.py` + `evaluate.py`; first numbers. *The proof it works.*
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

Starting without it costs nothing later: it slots into the labeler's output, not around it.
