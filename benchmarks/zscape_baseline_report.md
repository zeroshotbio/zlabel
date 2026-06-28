# ZSCAPE 2nd-atlas baseline report (anchor-rooted descent engine)

- clusters: 97  ·  scored: 96  ·  not_scored: 1

## Broad agreement (named + fallback, scored against the gold tissue)
- agreement: 88.9% (16/18)

## Coverage / split (over scored clusters)
- coverage (non-abstain): 21.9% (21/96)
- named: 17.7% (17/96)
- fallback: 1.0% (1/96)
- rollup: 3.1% (3/96)
- abstain: 78.1% (75/96)

## Agreement by prediction class
- named: 88.2% (15/17)
- fallback: 100.0% (1/1)

## Confidence by correctness (named + fallback)
- high: 100.0% (2/2)
- medium: 75.0% (3/4)
- low: 91.7% (11/12)

## Parent-child overcall audit (named calls)
- named calls audited: 17
- won with exactly CONVERGENCE_MIN=3 genes: 0.0% (0/17)
- thin-support overcalls (won at min, broader parent had more support): 0.0% (0/17)

Lowest support-fraction named calls (child support / best-parent support), top 15:
- hair_cell: neuromast (6) vs nervous system (18)  -> fraction 0.33
- unknown_dcn_col6: mesenchyme (7) vs portion of tissue (20)  -> fraction 0.35
- fin_bud_mesoderm_pectoral: pectoral fin (7) vs organism subdivision (17)  -> fraction 0.41
- xanthophore: xanthophore (7) vs organism subdivision (17)  -> fraction 0.41
- primordial_germ_cell: primordial germ cell (5) vs cell (12)  -> fraction 0.42
- endothelium_f8_clic2: posterior cardinal vein (8) vs multi-tissue structure (18)  -> fraction 0.44
- fin_fold: pectoral fin (10) vs surface structure (17)  -> fraction 0.59
- retinal_pigmented_epithelium_late: retinal pigmented epithelium (9) vs portion of tissue (15)  -> fraction 0.60
- pronephric_podocyte: pronephros (11) vs cavitated compound organ (17)  -> fraction 0.65
- cardiomyocyte: cardiac ventricle (16) vs cavitated compound organ (24)  -> fraction 0.67
- hatching_gland: epidermis (10) vs surface structure (15)  -> fraction 0.67
- basal_cell: epidermis (16) vs organism subdivision (22)  -> fraction 0.73
- periderm: epidermis (11) vs surface structure (15)  -> fraction 0.73
- endothelium_dorsal_aorta: blood vasculature (13) vs cardiovascular system (16)  -> fraction 0.81
- red_blood_cell: intermediate cell mass of mesoderm (13) vs portion of tissue (16)  -> fraction 0.81

## Failure gallery (scored disagreements)
- hatching_gland: gold Hatching Gland, predicted 'epidermis' (named)
- unknown_dcn_col6: gold Cranial Muscle (Late), predicted 'mesenchyme' (named)

## Marker visibility (vocab-hit-rate)
- median fraction of a cluster's markers in the panel vocabulary (scored): 4.0%

## Attractor over-attribution (named scored disagreements grounding under each attractor)
- epidermis: 1
- endothelium: 0
- mesenchyme: 1
- neural: 0
