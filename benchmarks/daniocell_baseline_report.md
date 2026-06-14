# Daniocell baseline report (IC-first engine)

- clusters: 522  ·  scored: 511  ·  not_scored: 11

## Broad agreement (named + fallback, scored against the gold tissue)
- agreement: 53.8% (21/39)

## Coverage / split (over scored clusters)
- coverage (non-abstain): 7.6% (39/511)
- named: 1.4% (7/511)
- fallback: 6.3% (32/511)
- rollup: 0.0% (0/511)
- abstain: 92.4% (472/511)

## Agreement by prediction class
- named: 57.1% (4/7)
- fallback: 53.1% (17/32)

## Confidence by correctness (named + fallback)
- high: 80.0% (4/5)
- medium: 45.8% (11/24)
- low: 60.0% (6/10)

## Parent-child overcall audit (named calls)
- named calls audited: 7
- won with exactly CONVERGENCE_MIN=3 genes: 85.7% (6/7)
- thin-support overcalls (won at min, broader parent had more support): 85.7% (6/7)

Lowest support-fraction named calls (child support / best-parent support), top 15:
- glia.11: trochlear motor nucleus (3) vs brain (22)  -> fraction 0.14
- neur.30: posterior lateral line placode (3) vs nervous system (21)  -> fraction 0.14
- neur.12: anterior lateral line system (3) vs nervous system (19)  -> fraction 0.16
- neur.33: statoacoustic (VIII) ganglion (3) vs portion of tissue (19)  -> fraction 0.16
- eye.30: statoacoustic (VIII) ganglion (3) vs nervous system (18)  -> fraction 0.17
- peri.6: epidermal superficial stratum (3) vs portion of tissue (16)  -> fraction 0.19
- neur.8: statoacoustic (VIII) ganglion (4) vs portion of tissue (18)  -> fraction 0.22

## Failure gallery (scored disagreements)
- eye.22: gold eye, predicted 'pigment' (fallback)
- eye.30: gold eye, predicted 'statoacoustic (VIII) ganglion' (named)
- fin.7: gold fin, predicted 'mesenchyme' (fallback)
- glia.11: gold glia, predicted 'trochlear motor nucleus' (named)
- mura.3: gold mura, predicted 'mesenchyme' (fallback)
- musc.19: gold musc, predicted 'mesenchyme' (fallback)
- peri.15: gold peri, predicted 'epidermis' (fallback)
- peri.16: gold peri, predicted 'epidermis' (fallback)
- peri.18: gold peri, predicted 'epidermis' (fallback)
- peri.20: gold peri, predicted 'epidermis' (fallback)
- peri.21: gold peri, predicted 'epidermis' (fallback)
- peri.24: gold peri, predicted 'epidermis' (fallback)
- peri.29: gold peri, predicted 'epidermis' (fallback)
- peri.3: gold peri, predicted 'epidermis' (fallback)
- peri.30: gold peri, predicted 'epidermis' (fallback)
- ... and 3 more
