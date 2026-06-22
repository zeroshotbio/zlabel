# Daniocell baseline report (anchor-rooted descent engine)

- clusters: 522  ·  scored: 511  ·  not_scored: 11

## Broad agreement (named + fallback, scored against the gold tissue)
- agreement: 71.1% (27/38)

## Coverage / split (over scored clusters)
- coverage (non-abstain): 13.1% (67/511)
- named: 7.2% (37/511)
- fallback: 0.2% (1/511)
- rollup: 5.7% (29/511)
- abstain: 86.9% (444/511)

## Agreement by prediction class
- named: 70.3% (26/37)
- fallback: 100.0% (1/1)

## Confidence by correctness (named + fallback)
- high: 100.0% (12/12)
- medium: 62.5% (15/24)
- low: 0.0% (0/2)

## Parent-child overcall audit (named calls)
- named calls audited: 37
- won with exactly CONVERGENCE_MIN=3 genes: 2.7% (1/37)
- thin-support overcalls (won at min, broader parent had more support): 2.7% (1/37)

Lowest support-fraction named calls (child support / best-parent support), top 15:
- musc.19: segmental plate (3) vs portion of tissue (19)  -> fraction 0.16
- mura.3: mesenchyme (7) vs portion of tissue (20)  -> fraction 0.35
- mese.5: head mesenchyme (8) vs portion of tissue (22)  -> fraction 0.36
- eye.30: retinal ganglion cell layer (7) vs compound organ (18)  -> fraction 0.39
- hema.27: nucleate erythrocyte (8) vs hematopoietic system (17)  -> fraction 0.47
- neur.12: diencephalon (9) vs cavitated compound organ (19)  -> fraction 0.47
- endo.23: exocrine pancreas (7) vs compound organ (14)  -> fraction 0.50
- neur.33: diencephalon (10) vs cavitated compound organ (20)  -> fraction 0.50
- peri.3: epidermis (8) vs portion of tissue (16)  -> fraction 0.50
- pigm.14: melanocyte (10) vs portion of tissue (20)  -> fraction 0.50
- pigm.9: melanocyte (11) vs portion of tissue (21)  -> fraction 0.52
- neur.8: diencephalon (10) vs cavitated compound organ (19)  -> fraction 0.53
- hema.3: nucleate erythrocyte (7) vs blood (13)  -> fraction 0.54
- hema.22: nucleate erythrocyte (8) vs blood (14)  -> fraction 0.57
- hema.1: nucleate erythrocyte (7) vs blood (12)  -> fraction 0.58

## Failure gallery (scored disagreements)
- eye.22: gold eye, predicted 'pigment cell' (named)
- glia.11: gold glia, predicted 'diencephalon' (named)
- mura.3: gold mura, predicted 'mesenchyme' (named)
- musc.19: gold musc, predicted 'segmental plate' (named)
- peri.16: gold peri, predicted 'epidermis' (named)
- peri.20: gold peri, predicted 'epidermis' (named)
- peri.29: gold peri, predicted 'integument' (named)
- peri.3: gold peri, predicted 'epidermis' (named)
- peri.5: gold peri, predicted 'epidermis' (named)
- peri.6: gold peri, predicted 'epidermis' (named)
- peri.7: gold peri, predicted 'epidermis' (named)
