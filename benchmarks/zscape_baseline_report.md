# ZSCAPE 2nd-atlas baseline report (anchor-rooted descent engine)

- clusters: 97  ·  scored: 96  ·  not_scored: 1

## Broad agreement (named + fallback, scored against the gold tissue)
- agreement: 86.8% (33/38)

## Coverage / split (over scored clusters)
- coverage (non-abstain): 42.7% (41/96)
- named: 38.5% (37/96)
- fallback: 1.0% (1/96)
- rollup: 3.1% (3/96)
- abstain: 57.3% (55/96)

## Agreement by prediction class
- named: 86.5% (32/37)
- fallback: 100.0% (1/1)

## Confidence by correctness (named + fallback)
- high: 100.0% (4/4)
- medium: 66.7% (6/9)
- low: 92.0% (23/25)

## Parent-child overcall audit (named calls)
- named calls audited: 37
- won with exactly CONVERGENCE_MIN=3 genes: 0.0% (0/37)
- thin-support overcalls (won at min, broader parent had more support): 0.0% (0/37)

Lowest support-fraction named calls (child support / best-parent support), top 15:
- hair_cell: neuromast (6) vs nervous system (18)  -> fraction 0.33
- primordial_germ_cell: primordial germ cell (5) vs cell (15)  -> fraction 0.33
- unknown_dcn_col6: mesenchyme (8) vs portion of tissue (21)  -> fraction 0.38
- fin_bud_mesoderm_pectoral: pectoral fin (7) vs organism subdivision (18)  -> fraction 0.39
- xanthophore: xanthophore (8) vs organism subdivision (19)  -> fraction 0.42
- endothelium_f8_clic2: posterior cardinal vein (9) vs multi-tissue structure (19)  -> fraction 0.47
- dorsal_spinal_cord_neuron: telencephalon (12) vs central nervous system (22)  -> fraction 0.55
- neuron_spinal_cord: telencephalon (11) vs cavitated compound organ (20)  -> fraction 0.55
- retinal_pigmented_epithelium_late: retinal pigmented epithelium (9) vs portion of tissue (16)  -> fraction 0.56
- neuron_dopaminergic: telencephalon (12) vs cavitated compound organ (21)  -> fraction 0.57
- neurons_differentiating_contains_peripheral: telencephalon (12) vs nervous system (21)  -> fraction 0.57
- neurons_gabaergic_glutamatergic_contains_purkinje: telencephalon (12) vs nervous system (21)  -> fraction 0.57
- posterior_spinal_cord_progenitors: diencephalon (12) vs cavitated compound organ (21)  -> fraction 0.57
- differentiating_neuron_2: telencephalon (13) vs cavitated compound organ (22)  -> fraction 0.59
- periderm: epidermis (12) vs organism subdivision (20)  -> fraction 0.60

## Failure gallery (scored disagreements)
- hatching_gland: gold Hatching Gland, predicted 'epidermis' (named)
- neuron_cranial_ganglia_sensory_rohon_beard: gold Peripheral Nervous System, predicted 'forebrain' (named)
- neuron_cranial_ganglion: gold Peripheral Nervous System, predicted 'diencephalon' (named)
- retinal_neuron: gold Eye, predicted 'telencephalon' (named)
- unknown_dcn_col6: gold Cranial Muscle (Late), predicted 'mesenchyme' (named)

## Marker visibility (vocab-hit-rate)
- median fraction of a cluster's markers in the panel vocabulary (scored): 8.0%

## Attractor over-attribution (named scored disagreements grounding under each attractor)
- epidermis: 1
- endothelium: 0
- mesenchyme: 1
- neural: 3
