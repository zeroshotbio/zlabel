# Daniocell baseline report (anchor-rooted descent engine)

- clusters: 522  ·  scored: 511  ·  not_scored: 11

## Broad agreement (named + fallback, scored against the gold tissue)
- agreement: 56.4% (22/39)

## Coverage / split (over scored clusters)
- coverage (non-abstain): 7.6% (39/511)
- named: 7.6% (39/511)
- fallback: 0.0% (0/511)
- rollup: 0.0% (0/511)
- abstain: 92.4% (472/511)

## Agreement by prediction class
- named: 56.4% (22/39)
- fallback: n/a (0)

## Confidence by correctness (named + fallback)
- high: 100.0% (2/2)
- medium: 55.2% (16/29)
- low: 50.0% (4/8)

## Parent-child overcall audit (named calls)
- named calls audited: 39
- won with exactly CONVERGENCE_MIN=3 genes: 2.6% (1/39)
- thin-support overcalls (won at min, broader parent had more support): 2.6% (1/39)

Lowest support-fraction named calls (child support / best-parent support), top 15:
- musc.19: segmental plate (3) vs portion of tissue (19)  -> fraction 0.16
- fin.7: mesenchyme (4) vs portion of tissue (14)  -> fraction 0.29
- mese.20: head mesenchyme (6) vs portion of tissue (21)  -> fraction 0.29
- mese.19: mesenchyme (7) vs portion of tissue (21)  -> fraction 0.33
- mese.2: head mesenchyme (6) vs portion of tissue (18)  -> fraction 0.33
- mura.3: mesenchyme (7) vs portion of tissue (20)  -> fraction 0.35
- mese.5: head mesenchyme (8) vs portion of tissue (22)  -> fraction 0.36
- mese.23: head mesenchyme (8) vs portion of tissue (21)  -> fraction 0.38
- eye.30: retinal ganglion cell layer (7) vs compound organ (18)  -> fraction 0.39
- mese.24: head mesenchyme (10) vs portion of tissue (23)  -> fraction 0.43
- neur.12: diencephalon (9) vs cavitated compound organ (19)  -> fraction 0.47
- hema.35: nucleate erythrocyte (5) vs cell (10)  -> fraction 0.50
- neur.33: diencephalon (10) vs cavitated compound organ (20)  -> fraction 0.50
- peri.3: epidermis (8) vs portion of tissue (16)  -> fraction 0.50
- pigm.14: melanocyte (10) vs portion of tissue (20)  -> fraction 0.50

## Failure gallery (scored disagreements)
- eye.22: gold eye, predicted 'pigment cell' (named)
- fin.7: gold fin, predicted 'mesenchyme' (named)
- glia.11: gold glia, predicted 'diencephalon' (named)
- mura.3: gold mura, predicted 'mesenchyme' (named)
- musc.19: gold musc, predicted 'segmental plate' (named)
- peri.15: gold peri, predicted 'integument' (named)
- peri.16: gold peri, predicted 'epidermis' (named)
- peri.18: gold peri, predicted 'integument' (named)
- peri.20: gold peri, predicted 'epidermis' (named)
- peri.21: gold peri, predicted 'epidermis' (named)
- peri.24: gold peri, predicted 'epidermis' (named)
- peri.29: gold peri, predicted 'integument' (named)
- peri.3: gold peri, predicted 'epidermis' (named)
- peri.30: gold peri, predicted 'epidermis' (named)
- peri.5: gold peri, predicted 'epidermis' (named)
- ... and 2 more
