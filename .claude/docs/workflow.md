# Build workflow — 7 phases, one PR each

zlabel is built in **seven phases**. Every phase follows the same loop:

1. **Implement** the phase — and nothing beyond it.
2. **Self-review** the diff comprehensively: correctness, simplicity, naming,
   docstrings, dead code.
3. **Meet the bar** (below). Simplify until it does.
4. **Update the docs** to match the code (`README`, `docs/design.md`, these
   `.claude/docs/` files, docstrings).
5. **Open a PR** — branch `feat/phaseN-<slug>`, Conventional-Commit title, body with
   *what + why* and a *test plan*.
6. **Stop and wait** for human review. Do not start the next phase until the PR is
   reviewed.

## The bar (a PR fails if it misses any)

- **Understandable.** A reader new to the file gets it in one pass.
- **Not overcomplicated.** No abstraction the phase does not need; no speculative
  generality.
- **Well-documented — the right words, not verbose prose.** Every public function
  has a tight Google-style docstring; non-obvious choices get a one-line *why*. Cut
  anything that just restates the code.
- **Docs current.** No stale claims anywhere in the repo.
- **No baseline regression.** `make gate` passes: the parent-child overcall audit did not
  rise and `benchmarks/daniocell_baseline_report.md` did not drift. An intentional behavior
  change regenerated the baseline (`make eval`) and committed it for review. (Mechanized as a
  pre-commit hook via `make hooks`.)

## The phases

1. **Skeleton + data** — repo, `pyproject`, `setup_data.sh`, `data.py` loaders (ZFA / ZFIN-expr / GAF synonyms) + tests on small fixtures.
2. **Genes + panels** — `genes.normalize_symbol`, `panels.yaml` (curated buckets, each cited), the overlap scorer + tests.
3. **Ground + label** — pure grounding lookups, then the converging-evidence decision in `label.py` → `Label`; unit-test the worked examples.
4. Split into two PRs:
   - **4a (engine)** — `resolve.py` support-weighted, anchor-rooted ZFA convergence namer (descends from the winning panel's anchor; the guardrail is intrinsic); panels supply the coarse prior + anchor; `Label` gains depth, panel_bucket, convergent_genes.
   - **4b (eval, shipped)** — `build_daniocell_eval.py` + `evaluate.py` + the Daniocell crosswalk; broad agreement, coverage, the named/fallback/abstain split, and the parent-child overcall audit (the proof it works).
5. **CLI + notebook 01** — `zlabel label` / `zlabel eval`; the one-cluster walkthrough.
6. **Notebooks 02/03** — scanpy clustering → markers → zlabel, then a real 48 hpf end-to-end (one-off demos).
7. **LLM (optional)** — `explain.py` narrator behind the `[llm]` extra; later, the fine de-novo namer.

Full per-phase detail: [`docs/design.md`](../../docs/design.md).
