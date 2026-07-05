# ZFA usefulness analysis

Read-only analysis of zlabel's ZFA label space. **No engine code or behavior changed** (descent and
panel changes were prototyped across phases, measured against the gate, and reverted). Regenerate
everything with:

```
uv run python analysis/zfa_usefulness/score_terms.py       # rubric -> term/edge CSVs + summary + sensitivity
uv run python analysis/zfa_usefulness/coverage.py          # reachability triage
uv run python analysis/zfa_usefulness/backlog.py           # ranked curation queue (corpus capacity)
uv run python analysis/zfa_usefulness/coverage_headroom.py # realizable headroom over the eval atlases
```

## Read in this order

1. **`REPORT.md`** — the consolidated findings + recommendation. Start here.
2. **`RELATIONSHIPS.md`** — ZFA relationship axes (is_a / part_of / develops_from) and which zlabel
   uses; retina + mesoderm worked examples. (Answers "what are these categories?")
3. **`coverage.md`** — what the descent can/can't reach; the develops_from coverage gap.
4. **`develops_from_experiment.md`** — the gated test of following develops_from. Verdict: NO-GO.
5. **`backlog.md`** — the 350 T4 cell types ranked by grounding capacity (with the Phase-3 correction:
   capacity is not eval-realizability).
6. **`grounding_augmentation.md`** — how to convert the backlog (targeted curation; bulk xpat ruled out).
7. **`grounding_pilot.md`** — **Phase-3 entry point.** End-to-end test of the coverage levers (backlog
   grounding + panel addition). Verdict: both NO-GO; coverage is selection-wall-bound.
8. **`coverage_headroom.md`** — the realizable-headroom scan output (per-cluster cause attribution).

## Data tables

- `zfa_term_usefulness.csv` — every ZFA term: tier, sub-signals, flags.
- `zfa_edges.csv` — every is_a/part_of step: sufficiency-gated discernibility, dead-step flag.
- `sensitivity.csv` — tier counts across the threshold grid (stability evidence).
- `coverage_unreached.csv` — useful terms the descent can't reach.
- `backlog.csv` — ranked curation queue (corpus capacity).
- `coverage_headroom.csv` — per-eval-cluster headroom classification (covered / panel-addable / selection- / resolution-bound).
- `summary.json` — all headline numbers.

## One-paragraph conclusion

The engine already never emits a useless label (0/176 named Daniocell calls are junk-tier — structural,
via the curated anchors + `CONVERGENCE_MIN`). The rubric's value is therefore as a **standing audit**,
not a driver of descent changes. **Every coverage lever tested is a NO-GO:** following `develops_from`
(0 new labels, otolith regression); targeted backlog grounding (the near-bar terms' markers never
co-occur in any of the 629 eval clusters — capacity is not realizability); and adding panels for
well-grounded unanchored terms (the best candidate, periderm, regresses the hard gate two ways).
**Coverage is bound by the selection/attractor wall, not by reachability or grounding** —
`grounding_pilot.md` is the Phase-3 entry point. See `validation/disagreement_sweep.md` for an
independent adjudication of the Daniocell "failures" (≈58% are gold-label artifacts, not engine errors).
