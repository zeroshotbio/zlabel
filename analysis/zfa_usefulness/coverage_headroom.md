# Realizable coverage headroom — what a missing panel/anchor blocks

Read-only. Runs the current engine over all committed eval clusters and asks, per cluster, whether
a NEW panel/anchor could turn it into a correct (or deeper-correct) named call. Useful = T1/T2.
Correctness is overlay-extended where an overlay exists (matches the eval's overlay-corrected
agreement), so headroom is conservative. Firing is predicted by support >= 3; a confirming
panel + make gate-all is the proof. The 0.6-floor flag estimates whether the call would also clear
DESCENT_SUPPORT_FRACTION=0.6 when descended from a higher anchor (anchoring
directly at the term avoids that floor).

Scored clusters classified: **616** (plus 0 skipped as unmapped/out-of-scope).

## Categories

| category | count | meaning |
|---|---|---|
| covered | 187 | clean correct call — no headroom |
| **panel_addable_new_correct** | **63** | not correctly covered, but markers converge on an unreachable useful correct term — a NEW panel would add a correct call |
| panel_addable_deeper_correct | 5 | already correct, but an unreachable finer useful term is supported — a panel would deepen it |
| selection_bound | 334 | a useful correct term IS reachable but the engine did not emit it (support-floor / panel-score) — not a panel fix |
| resolution_bound | 27 | no useful term reaches support >= 3 — a genuinely low-resolution cluster |

**Headline (upper bound): 63 new-correct + 5 deeper-correct = 68 panel-addable clusters** (22 also clear the 0.6 floor).
**Of the 63 new-correct, 31 have a candidate that matches the cluster's FINE label** (likely right subtype); the rest only ground under an over-broad gold (e.g. ovary for a thyroid follicle cluster) and are probably not real panels.

## Panel-addable by candidate term (the actionable curation list)

`fine` = clusters whose candidate matches the fine label (the trustworthy subset).

| candidate term | clusters | fine | atlases |
|---|---|---|---|
| periderm (ZFA:0001185) | 19 | 19 | daniocell |
| polster (ZFA:0000058) | 14 | 0 | daniocell |
| prechordal plate (ZFA:0000060) | 7 | 0 | daniocell |
| endoderm (ZFA:0000017) | 7 | 7 | daniocell |
| mandibular arch skeleton (ZFA:0001227) | 4 | 2 | zscape |
| pharyngeal arch (ZFA:0001306) | 3 | 0 | zscape |
| palatoquadrate arch (ZFA:0001272) | 3 | 1 | zscape |
| hypochord (ZFA:0000031) | 2 | 1 | daniocell, zscape |
| axial mesoderm (ZFA:0001204) | 1 | 1 | daniocell |
| ovarian follicle (ZFA:0001110) | 1 | 0 | zscape |
| skeletal tissue (ZFA:0005619) | 1 | 0 | zscape |
| pharyngeal arch 2 (ZFA:0001611) | 1 | 0 | zscape |
| pharyngeal arch 1 (ZFA:0001612) | 1 | 0 | zscape |
| portion of connective tissue (ZFA:0001632) | 1 | 1 | zscape |
| opercle (ZFA:0000250) | 1 | 0 | zscape |
| ovary (ZFA:0000403) | 1 | 0 | zscape |
| intermediate mesoderm (ZFA:0001206) | 1 | 1 | zebrahub |

## Panel-addable clusters (detail)

| atlas | cluster | broad gold | fine gold | current | candidate | sup | floor |
|---|---|---|---|---|---|---|---|
| daniocell | axia.4 | axia | axial | named* | axial mesoderm | 3 | risk |
| daniocell | endo.18 | endo | endoderm | abstain | endoderm | 4 | risk |
| daniocell | endo.20 | endo | endoderm | abstain | endoderm | 3 | risk |
| daniocell | endo.28 | endo | endoderm | abstain | endoderm | 5 | risk |
| daniocell | endo.29 | endo | endoderm | abstain | endoderm | 3 | risk |
| daniocell | endo.30 | endo | endoderm | abstain | endoderm | 3 | risk |
| daniocell | endo.32 | endo | endoderm | abstain | endoderm | 5 | risk |
| daniocell | endo.33 | endo | endoderm | abstain | endoderm | 4 | risk |
| daniocell | endo.8 | endo | endoderm | abstain | hypochord | 3 | risk |
| zscape | hypochord | Hypochord | hypochord | abstain | hypochord | 14 | ok |
| zebrahub | intermediate_mesoderm | intermediate_mesoderm | intermediate_mesoderm | abstain | intermediate mesoderm | 5 | risk |
| zscape | head_mesenchyme_maybe_ventral_hand2 | Pharyngeal Arch | head mesenchyme (maybe ventral, hand2+) | abstain | mandibular arch skeleton | 3 | risk |
| zscape | pharyngeal_arch_early | Pharyngeal Arch | pharyngeal arch (early) | abstain | mandibular arch skeleton | 4 | risk |
| zscape | pharyngeal_arch_nc_derived | Pharyngeal Arch | pharyngeal arch (NC-derived) | abstain | mandibular arch skeleton | 4 | risk |
| zscape | vascular_smooth_muscle | Pharyngeal Arch | vascular smooth muscle | abstain | mandibular arch skeleton | 3 | risk |
| zscape | osteoblast | Bone | osteoblast | rollup | opercle | 3 | risk |
| zscape | adrenal_gland | Endocrine | adrenal gland | fallback* | ovarian follicle | 3 | risk |
| zscape | thyroid_follicle_cell | Endocrine | thyroid follicle cell | abstain | ovary | 3 | risk |
| zscape | head_mesenchyme | Pharyngeal Arch | head mesenchyme | abstain | palatoquadrate arch | 4 | risk |
| zscape | jaw_chondrocyte | Pharyngeal Arch | jaw chondrocyte | abstain | palatoquadrate arch | 8 | risk |
| zscape | pharyngeal_arch_contains_muscle_early_cartilage | Pharyngeal Arch | pharyngeal arch (contains muscle, early cartilage) | abstain | palatoquadrate arch | 4 | risk |
| daniocell | peri.1 | peri | periderm | rollup | periderm | 14 | ok |
| daniocell | peri.10 | peri | periderm | rollup | periderm | 12 | ok |
| daniocell | peri.12 | peri | periderm | rollup | periderm | 16 | ok |
| daniocell | peri.14 | peri | periderm | rollup | periderm | 15 | ok |
| daniocell | peri.15 | peri | periderm | rollup | periderm | 11 | ok |
| daniocell | peri.16 | peri | periderm | rollup | periderm | 16 | ok |
| daniocell | peri.17 | peri | periderm | rollup | periderm | 14 | ok |
| daniocell | peri.18 | peri | periderm | rollup | periderm | 10 | risk |
| daniocell | peri.19 | peri | periderm | abstain | periderm | 16 | ok |
| daniocell | peri.21 | peri | periderm | rollup | periderm | 15 | ok |
| daniocell | peri.24 | peri | periderm | rollup | periderm | 16 | ok |
| daniocell | peri.25 | peri | periderm | rollup | periderm | 16 | ok |
| daniocell | peri.27 | peri | periderm | abstain | periderm | 11 | ok |
| daniocell | peri.28 | peri | periderm | rollup | periderm | 13 | ok |
| daniocell | peri.29 | peri | periderm | named* | periderm | 12 | ok |
| daniocell | peri.30 | peri | periderm | rollup | periderm | 13 | ok |
| daniocell | peri.31 | peri | periderm | rollup | periderm | 18 | ok |
| daniocell | peri.8 | peri | periderm | rollup | periderm | 14 | ok |
| daniocell | peri.9 | peri | periderm | abstain | periderm | 11 | ok |
| zscape | chondrocranium | Pharyngeal Arch | chondrocranium | abstain | pharyngeal arch | 3 | risk |
| zscape | cranial_muscle_progenitor | Pharyngeal Arch | cranial muscle (progenitor) | abstain | pharyngeal arch | 8 | risk |
| zscape | head_mesenchyme_pa_cartilage | Pharyngeal Arch | head mesenchyme/PA cartilage | abstain | pharyngeal arch | 6 | risk |
| zscape | cranial_muscle_mid | Pharyngeal Arch | cranial muscle (mid) | abstain | pharyngeal arch 1 | 6 | risk |
| zscape | cranial_muscle_early | Pharyngeal Arch | cranial muscle (early) | abstain | pharyngeal arch 2 | 3 | risk |
| daniocell | axia.11 | axia | axial | abstain | polster | 3 | risk |
| daniocell | axia.12 | axia | axial | abstain | polster | 7 | risk |
| daniocell | axia.13 | axia | axial | named* | polster | 6 | risk |
| daniocell | axia.14 | axia | axial | abstain | polster | 17 | ok |
| daniocell | axia.15 | axia | axial | abstain | polster | 15 | ok |
| daniocell | axia.17 | axia | axial | abstain | polster | 4 | risk |
| daniocell | axia.18 | axia | axial | rollup | polster | 6 | risk |
| daniocell | axia.20 | axia | axial | abstain | polster | 13 | ok |
| daniocell | axia.21 | axia | axial | abstain | polster | 6 | risk |
| daniocell | axia.22 | axia | axial | abstain | polster | 3 | risk |
| daniocell | axia.23 | axia | axial | abstain | polster | 4 | risk |
| daniocell | axia.3 | axia | axial | abstain | polster | 6 | risk |
| daniocell | axia.5 | axia | axial | named* | polster | 6 | risk |
| daniocell | axia.8 | axia | axial | abstain | polster | 3 | risk |
| zscape | head_eye_connective_tissue | Connective Tissue | head/eye connective tissue | abstain | portion of connective tissue | 4 | risk |
| daniocell | axia.1 | axia | axial | abstain | prechordal plate | 5 | risk |
| daniocell | axia.16 | axia | axial | abstain | prechordal plate | 3 | risk |
| daniocell | axia.19 | axia | axial | abstain | prechordal plate | 5 | risk |
| daniocell | axia.2 | axia | axial | abstain | prechordal plate | 3 | risk |
| daniocell | axia.6 | axia | axial | abstain | prechordal plate | 3 | risk |
| daniocell | axia.7 | axia | axial | abstain | prechordal plate | 4 | risk |
| daniocell | axia.9 | axia | axial | abstain | prechordal plate | 4 | risk |
| zscape | connective_tissue_meninges_dermal_fb | Connective Tissue | connective tissue-meninges-dermal FB | abstain | skeletal tissue | 4 | risk |

(* current call already correct at a coarser term; the candidate would deepen it.)

## By atlas

| atlas | covered | panel_addable_new_correct | panel_addable_deeper_correct | selection_bound | resolution_bound |
|---|---|---|---|---|---|
| daniocell | 150 | 45 | 4 | 288 | 24 |
| zscape | 34 | 17 | 1 | 41 | 3 |
| zebrahub | 3 | 1 | 0 | 5 | 0 |

## Reading this

panel_addable_new_correct is the realizable coverage gain from adding panels. If it is small, the
two earlier coverage levers (develops_from, backlog grounding) plus this one are all exhausted and
coverage is anchor/resolution-bound — document and close. If it is material, each candidate term is
a curation target: add a panel anchored at (or just above) it, then confirm with make gate-all that
it yields real new/deeper correct calls with the thin-overcall line unchanged.

Full per-cluster classification: coverage_headroom.csv.
