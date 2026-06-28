# Daniocell baseline report (anchor-rooted descent engine)

- clusters: 522  ·  scored: 511  ·  not_scored: 11

## Broad agreement (named + fallback, scored against the gold tissue)
- agreement: 74.0% (128/173)

## Coverage / split (over scored clusters)
- coverage (non-abstain): 42.1% (215/511)
- named: 33.1% (169/511)
- fallback: 0.8% (4/511)
- rollup: 8.2% (42/511)
- abstain: 57.9% (296/511)

## Agreement by prediction class
- named: 74.0% (125/169)
- fallback: 75.0% (3/4)

## Confidence by correctness (named + fallback)
- high: 100.0% (20/20)
- medium: 70.3% (26/37)
- low: 70.7% (82/116)

## Parent-child overcall audit (named calls)
- named calls audited: 169
- won with exactly CONVERGENCE_MIN=3 genes: 3.0% (5/169)
- thin-support overcalls (won at min, broader parent had more support): 3.0% (5/169)

Lowest support-fraction named calls (child support / best-parent support), top 15:
- musc.19: segmental plate (3) vs portion of tissue (22)  -> fraction 0.14
- fin.9: fin fold pectoral fin bud (3) vs multi-tissue structure (20)  -> fraction 0.15
- iono.17: NaK ionocyte (3) vs portion of tissue (18)  -> fraction 0.17
- pigm.18: pigment cell (3) vs cell (15)  -> fraction 0.20
- pigm.23: pigment cell (3) vs cell (13)  -> fraction 0.23
- glia.23: oligodendrocyte (5) vs nervous system (19)  -> fraction 0.26
- axia.4: notochord (4) vs portion of tissue (15)  -> fraction 0.27
- pron.15: epiphysis (6) vs cavitated compound organ (22)  -> fraction 0.27
- eye.20: epiphysis (5) vs cavitated compound organ (18)  -> fraction 0.28
- endo.17: intestine (6) vs cavitated compound organ (21)  -> fraction 0.29
- axia.6: epidermis (7) vs portion of tissue (23)  -> fraction 0.30
- pigm.3: xanthophore (4) vs organism subdivision (13)  -> fraction 0.31
- axia.9: epidermis (8) vs portion of tissue (23)  -> fraction 0.35
- mese.5: head mesenchyme (8) vs portion of tissue (23)  -> fraction 0.35
- eye.14: epiphysis (7) vs cavitated compound organ (19)  -> fraction 0.37

## Failure gallery (scored disagreements)
- axia.16: gold axia, predicted 'epidermis' (named)
- axia.6: gold axia, predicted 'epidermis' (named)
- axia.9: gold axia, predicted 'epidermis' (named)
- eye.14: gold eye, predicted 'epiphysis' (named)
- eye.15: gold eye, predicted 'forebrain' (named)
- eye.20: gold eye, predicted 'epiphysis' (named)
- eye.22: gold eye, predicted 'pigment cell' (named)
- eye.36: gold eye, predicted 'nervous system' (named)
- fin.11: gold fin, predicted 'epidermis' (named)
- fin.19: gold fin, predicted 'epidermis' (named)
- fin.3: gold fin, predicted 'epidermis' (named)
- fin.5: gold fin, predicted 'epidermis' (named)
- fin.9: gold fin, predicted 'fin fold pectoral fin bud' (named)
- hema.2: gold hema, predicted 'blood vessel' (named)
- hema.24: gold hema, predicted 'dorsal aorta' (named)
- ... and 30 more

## Marker visibility (vocab-hit-rate)
- median fraction of a cluster's markers in the panel vocabulary (scored): 12.0%

## Attractor over-attribution (named scored disagreements grounding under each attractor)
- epidermis: 24
- endothelium: 5
- mesenchyme: 2
- neural: 11
