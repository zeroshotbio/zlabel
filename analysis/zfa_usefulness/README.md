# ZFA usefulness analysis

Read-only analysis of zlabel's ZFA label space. **No engine code or behavior changed** (one descent
change was prototyped in Phase 3, measured, and reverted). Regenerate everything with:

```
uv run python analysis/zfa_usefulness/score_terms.py   # rubric -> term/edge CSVs + summary + sensitivity
uv run python analysis/zfa_usefulness/coverage.py      # reachability triage
uv run python analysis/zfa_usefulness/backlog.py        # ranked curation queue
```

## Read in this order

1. **`REPORT.md`** — the consolidated findings + recommendation. Start here.
2. **`RELATIONSHIPS.md`** — ZFA relationship axes (is_a / part_of / develops_from) and which zlabel
   uses; retina + mesoderm worked examples. (Answers "what are these categories?")
3. **`coverage.md`** — what the descent can/can't reach; the develops_from coverage gap.
4. **`develops_from_experiment.md`** — the gated test of following develops_from. Verdict: NO-GO.
5. **`backlog.md`** — the 255 reachable ungroundable cell types, ranked (the real coverage lever).
6. **`grounding_augmentation.md`** — how to convert the backlog (targeted curation; bulk xpat ruled out).

## Data tables

- `zfa_term_usefulness.csv` — every ZFA term: tier, sub-signals, flags.
- `zfa_edges.csv` — every is_a/part_of step: sufficiency-gated discernibility, dead-step flag.
- `sensitivity.csv` — tier counts across the threshold grid (stability evidence).
- `coverage_unreached.csv` — useful terms the descent can't reach.
- `backlog.csv` — ranked curation queue.
- `summary.json` — all headline numbers.

## One-paragraph conclusion

The engine already never emits a useless label (0/173 named Daniocell calls are junk-tier — structural,
via the curated anchors + `CONVERGENCE_MIN`). The rubric's value is therefore as a **standing audit**
and a **curation backlog generator**, not a driver of descent changes. The most plausible coverage
lever — following the ignored `develops_from` axis — was tested and is a NO-GO (0 new labels, otolith-
type regressions). Coverage grows only by **targeted grounding** of the 50 near-bar cell types in
`backlog.csv`. See `validation/disagreement_sweep.md` for an independent adjudication of the Daniocell
"failures" (≈58% are gold-label artifacts, not engine errors).
