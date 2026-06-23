# Daniocell baseline report (anchor-rooted descent engine)

- clusters: 522  ·  scored: 511  ·  not_scored: 11

## Broad agreement (named + fallback, scored against the gold tissue)
- agreement: 71.3% (107/150)

## Coverage / split (over scored clusters)
- coverage (non-abstain): 35.0% (179/511)
- named: 28.6% (146/511)
- fallback: 0.8% (4/511)
- rollup: 5.7% (29/511)
- abstain: 65.0% (332/511)

## Agreement by prediction class
- named: 71.2% (104/146)
- fallback: 75.0% (3/4)

## Confidence by correctness (named + fallback)
- high: 100.0% (12/12)
- medium: 62.1% (18/29)
- low: 70.6% (77/109)

## Parent-child overcall audit (named calls)
- named calls audited: 146
- won with exactly CONVERGENCE_MIN=3 genes: 4.8% (7/146)
- thin-support overcalls (won at min, broader parent had more support): 4.8% (7/146)

Lowest support-fraction named calls (child support / best-parent support), top 15:
- fin.9: fin fold pectoral fin bud (3) vs multi-tissue structure (19)  -> fraction 0.16
- musc.19: segmental plate (3) vs portion of tissue (19)  -> fraction 0.16
- iono.12: NaK ionocyte (3) vs portion of tissue (16)  -> fraction 0.19
- iono.5: NaK ionocyte (3) vs portion of tissue (14)  -> fraction 0.21
- iono.6: NaK ionocyte (3) vs portion of tissue (14)  -> fraction 0.21
- pigm.3: xanthophore (3) vs organism subdivision (13)  -> fraction 0.23
- glia.23: oligodendrocyte (4) vs nervous system (17)  -> fraction 0.24
- pigm.23: pigment cell (3) vs cell (12)  -> fraction 0.25
- axia.4: notochord (4) vs portion of tissue (14)  -> fraction 0.29
- eye.20: epiphysis (5) vs cavitated compound organ (17)  -> fraction 0.29
- pigm.2: xanthophore (5) vs organism subdivision (16)  -> fraction 0.31
- axia.9: epidermis (7) vs portion of tissue (21)  -> fraction 0.33
- endo.17: intestine (6) vs cavitated compound organ (18)  -> fraction 0.33
- eye.14: epiphysis (6) vs cavitated compound organ (18)  -> fraction 0.33
- mura.3: mesenchyme (7) vs portion of tissue (20)  -> fraction 0.35

## Failure gallery (scored disagreements)
- axia.16: gold axia, predicted 'epidermis' (named)
- axia.2: gold axia, predicted 'epidermis' (named)
- axia.6: gold axia, predicted 'epidermis' (named)
- axia.9: gold axia, predicted 'epidermis' (named)
- eye.14: gold eye, predicted 'epiphysis' (named)
- eye.15: gold eye, predicted 'forebrain' (named)
- eye.20: gold eye, predicted 'epiphysis' (named)
- eye.22: gold eye, predicted 'pigment cell' (named)
- fin.11: gold fin, predicted 'epidermis' (named)
- fin.19: gold fin, predicted 'epidermis' (named)
- fin.3: gold fin, predicted 'epidermis' (named)
- fin.5: gold fin, predicted 'epidermis' (named)
- fin.9: gold fin, predicted 'fin fold pectoral fin bud' (named)
- glia.11: gold glia, predicted 'diencephalon' (named)
- hema.24: gold hema, predicted 'artery' (named)
- ... and 28 more
