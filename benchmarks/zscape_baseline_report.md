# ZSCAPE 2nd-atlas baseline report (anchor-rooted descent engine)

- clusters: 97  ·  scored: 96  ·  not_scored: 1

## Broad agreement (named + fallback, scored against the gold tissue)
- agreement: 86.1% (31/36)

## Coverage / split (over scored clusters)
- coverage (non-abstain): 42.7% (41/96)
- named: 36.5% (35/96)
- fallback: 1.0% (1/96)
- rollup: 5.2% (5/96)
- abstain: 57.3% (55/96)

## Agreement by prediction class
- named: 85.7% (30/35)
- fallback: 100.0% (1/1)

## Confidence by correctness (named + fallback)
- high: 100.0% (4/4)
- medium: 50.0% (3/6)
- low: 92.3% (24/26)

## Parent-child overcall audit (named calls)
- named calls audited: 35
- won with exactly CONVERGENCE_MIN=3 genes: 0.0% (0/35)
- thin-support overcalls (won at min, broader parent had more support): 0.0% (0/35)

Lowest support-fraction named calls (child support / best-parent support), top 15:
- pronephric_podocyte: pronephric podocyte (5) vs compound organ (17)  -> fraction 0.29
- hair_cell: neuromast (6) vs nervous system (18)  -> fraction 0.33
- unknown_dcn_col6: mesenchyme (7) vs portion of tissue (20)  -> fraction 0.35
- xanthophore: xanthophore (7) vs organism subdivision (19)  -> fraction 0.37
- primordial_germ_cell: primordial germ cell (5) vs cell (13)  -> fraction 0.38
- endothelium_f8_clic2: axial blood vessel (7) vs multi-tissue structure (16)  -> fraction 0.44
- endothelium_vein_early_artery: posterior cardinal vein (9) vs compound organ (19)  -> fraction 0.47
- retinal_pigmented_epithelium_late: retinal pigmented epithelium (8) vs portion of tissue (16)  -> fraction 0.50
- neurons_differentiating_contains_peripheral: telencephalon (11) vs nervous system (21)  -> fraction 0.52
- neuron_spinal_cord: telencephalon (12) vs cavitated compound organ (22)  -> fraction 0.55
- fin_bud_mesoderm_pectoral: fin (9) vs organism subdivision (16)  -> fraction 0.56
- neuron_dopaminergic: telencephalon (13) vs nervous system (22)  -> fraction 0.59
- retinal_neuron: telencephalon (13) vs nervous system (22)  -> fraction 0.59
- hatching_gland: epidermis (12) vs surface structure (20)  -> fraction 0.60
- neuron_cranial_ganglion: diencephalon (12) vs cavitated compound organ (20)  -> fraction 0.60

## Failure gallery (scored disagreements)
- hatching_gland: gold Hatching Gland, predicted 'epidermis' (named)
- neuron_cranial_ganglia_sensory_rohon_beard: gold Peripheral Nervous System, predicted 'brain' (named)
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
