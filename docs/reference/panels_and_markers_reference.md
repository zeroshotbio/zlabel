# Panel & marker reference

Companion to [`src/zlabel/panels.yaml`](../../src/zlabel/panels.yaml): what each panel
is, the markers that define it, the ZFA anchor it descends from, and how the panels
sit on the zebrafish structural hierarchy.

## Overview

zlabel's panels are the curated domain knowledge in `src/zlabel/panels.yaml`: 31
identity buckets plus 2 state buckets, each a broad zebrafish cell-type family. A
panel pairs a marker-gene signature with a ZFA anatomy anchor. The engine reads two
fields — `markers` decide which bucket a cluster scores into, and `ontology_anchor`
seeds the ZFA descent that names it at the depth the evidence supports. Panels are a
coarse prior, not the namer: biological resolution comes from the ontology walk in
`resolve.py`.

## How a panel works

Three fields drive the engine:

- **`markers`** — current ZFIN gene symbols (the grounding spine). The scorer ranks buckets by how a
  cluster's genes overlap each panel's markers; the best overlap wins. This is the
  only field that selects a bucket.
- **`ontology_anchor`** — one or more ZFA terms. The winning panel's anchor seeds the
  support-weighted descent in `resolve.py`: each gene's in-vivo ZFIN expression votes
  for ZFA terms, and the walk steps down from the anchor to the deepest term the genes
  converge on. This is the only field that sets where naming starts.
- **`kind`** — `identity` or `state`.

An optional **`scoring_markers`** list holds markers kept for overlap scoring only — they aid
bucket selection but are not required to express under the anchor in ZFIN. `Panel.markers` is the
union of the spine and `scoring_markers` (what the scorer sees); the grounding audit
(`scripts/audit_panels.py`) requires only the spine to ground, and fails if a spine marker does not.

`germ_layer` / `tissue` / `lineage` supply a fallback label when the evidence does not
converge; `cite` records provenance. A panel proposes a neighbourhood; the ZFA
evidence picks the exact address, so `Label.depth` is earned from the data, not
declared by the panel.

## The structural ladder

A zebrafish cell type sits on a four-rung ladder — **Organ System → Organ → Tissue →
Cell Type**. That ladder is the ZFA ontology itself, and zlabel produces it by
descent rather than encoding it in the panels:

- **Cardiovascular** — the `cardiac` panel (anchor: heart) descends heart → myocardium
  → cardiomyocyte as the markers converge.
- **Visual** — the `eye` panel (anchor: eye) descends eye → retina → photoreceptor.

`Label.levels` is the path taken; `Label.depth` is how far down the evidence reached.

Panels deliberately anchor at **different rungs** — the coarsest rung where the marker
set is still discriminative. `neural` anchors at an organ system (nervous system);
`cardiac` at an organ (heart); `glia` at a cell type (glial cell), because glial
markers would otherwise be swamped by neurons at the system level. Across the 31
identity panels the anchors fall at 7 organ-system, 9 organ, 4 tissue, and 10
cell-type rungs, with `fin` off the ladder (a regional appendage). Eight panels anchor
across more than one rung (marked † below).

Each anchor's rung is **derived from ZFA**, not hand-assigned — a term's placement
under *anatomical system* (ZFA:0001439), *compound organ* (ZFA:0000496), *portion of
tissue* (ZFA:0001477), or *cell* (ZFA:0009000). `make audit` prints the rung for every
panel, so the tables below cannot drift from the ontology.

## The panels

Grouped by germ layer. Anchor = the ZFA seed term(s); rung = the anchor's structural
tier; † = anchors span more than one rung.

### Ectoderm — neural, sensory, surface

| panel | anchor · rung | markers |
|---|---|---|
| neural | nervous system `ZFA:0000396` · organ_system | elavl3, neurod1, tubb5, sox3, sox2, her4.1, ascl1a, gfap |
| glia | glial cell `ZFA:0009073` · cell_type | sox10, olig2, mbpa, gfap, plp1b, slc1a3b |
| neural_crest † | neural crest `ZFA:0000045` + neural crest cell `ZFA:0009165` · cell_type | sox10, foxd3, tfap2a, snai1b, dlx2a, sox9b |
| eye | eye `ZFA:0000107` · organ | cryaa, crybb1, mipa, rho, opn1mw1, gnat2, crx, rpe65a |
| otic † | otic vesicle `ZFA:0000051` + inner ear `ZFA:0000217` · organ_system | otomp, oc90, otol1a, dlx3b, eya1, atoh1a |
| lateral_line | lateral line system `ZFA:0000034` + taste bud `ZFA:0001074` · organ_system | atoh1a, myo6b, cldnb, six1b, eya1 |
| olfactory † | olfactory system `ZFA:0001149` + olfactory epithelium `ZFA:0000554` · tissue | ompb, s100z, calb2b, gng8, neurod1 |
| epidermis † | epidermis `ZFA:0000105` + integument `ZFA:0000368` · tissue | krt4, krt5, tp63, cldne, krt8, cldnb |
| ionocyte | ionocyte `ZFA:0005323` · cell_type | foxi3a, foxi3b, ca2, slc12a10.2, trpv6, atp1b1b |
| pigment | pigment cell `ZFA:0009090` · cell_type | mitfa, dct, tyrp1b, gch2, slc45a2, xdh |

### Mesoderm

| panel | anchor · rung | markers |
|---|---|---|
| muscle | musculature system `ZFA:0000548` · organ_system | myod1, myog, myf5, mylpfa, acta1b, tnnt3a, tnnc2.2, ckma |
| cardiac | heart `ZFA:0000114` · organ | myl7, myh6, myh7, nppa, tnnt2a, ttn.2 |
| mural | mural cell `ZFA:0005944` · cell_type | pdgfrb, notch3, tagln, acta2, desma, cspg4 |
| endothelium † | vasculature `ZFA:0005249` + endothelial cell `ZFA:0009065` · cell_type | kdrl, fli1, etsrp, cdh5, pecam1a, flt1 |
| blood_erythroid | blood `ZFA:0000007` + hematopoietic system `ZFA:0005023` · organ_system | gata1a, hbae1.1, hbbe2, alas2, klf1, slc4a1a, cahz |
| immune_myeloid | immune system `ZFA:0001159` + hematopoietic system `ZFA:0005023` · organ_system | lcp1, mpeg1.1, coro1a, spi1b, mfap4.1, lyz, csf1ra |
| blood_lymphoid | lymphocyte `ZFA:0009250` · cell_type | lck, rag1, rag2, il7r, cd8a |
| pronephros | pronephros `ZFA:0000151` · organ | pax2a, wt1a, wt1b, slc20a1a, cdh17, slc12a1, pax8 |
| mesenchyme | mesenchyme `ZFA:0000393` · tissue | dcn, twist1a, prrx1a, osr2, fn1a, col1a1a, col1a2 |
| cartilage † | cartilage element `ZFA:0001501` + chondrocyte `ZFA:0009084` · cell_type | sox9a, sox9b, col2a1a, acana, matn1, runx2b |
| osteoblast † | osteoblast `ZFA:0009031` + bone tissue `ZFA:0005621` · cell_type | sp7, spp1, bglap, col10a1a, runx2a, runx2b |
| notochord | notochord `ZFA:0000135` · tissue | tbxta, shha, col2a1a, col8a1a, noto |
| fin | fin `ZFA:0000108` + fin bud `ZFA:0001383` · off-ladder | tbx5a, fgf24, hoxd13a, hoxa13a, msx1b, and1 |

### Endoderm

| panel | anchor · rung | markers |
|---|---|---|
| endoderm_gut † | digestive system `ZFA:0000339` + presumptive endoderm `ZFA:0000416` · organ_system | sox32, sox17, foxa2, gata5, gata6, hhex |
| liver | liver `ZFA:0000123` · organ | fabp10a, cp, tfa, gc, f2, serpina1l |
| pancreas | pancreas `ZFA:0000140` · organ | ins, gcga, sst2, pdx1, prss1, cpa5 |
| intestine | intestine `ZFA:0001338` · organ | fabp2, fabp6, cdx1b, slc15a1b, vil1 |

### Germline & endocrine

| panel | anchor · rung | markers |
|---|---|---|
| germline | germ line cell `ZFA:0009016` · cell_type | ddx4, nanos3, dazl, piwil1 |
| pituitary | adenohypophysis `ZFA:0001282` · organ | pou1f1, prl, gh1, pomca, tshba, cga |
| interrenal | interrenal gland `ZFA:0001345` · organ | nr5a1a, cyp11a1.1, star, mc2r |
| pineal | epiphysis `ZFA:0000019` · organ | aanat2, exorh, otx5, asip2b |

### State (orthogonal to identity)

State panels carry no anatomy anchor — a cycling muscle cell is still muscle; the
state is recorded separately.

| panel | markers |
|---|---|
| cycling | mki67, pcna, top2a, hmgb2a, stmn1a |
| stress_response | hsp70l, hspa5, dnajb1b, fosab, atf3 |

## Notes on specific panels

- **glia** is anchored below the nervous system so glial clusters resolve to glia
  rather than rolling up to the CNS.
- **lateral_line** covers both the lateral line and taste buds — `taste bud`
  (`ZFA:0001074`) is one of its anchors — which share hair-cell and placodal markers
  (`atoh1a`, `eya1`, `six1b`) with `otic`. A cluster grounds under whichever anchor
  its expression supports; there is no separate taste-bud bucket at this broad altitude.
- **mural** sits on a sparsely curated ZFA term; `desma` and `cspg4` do not ground under it and are
  kept in `scoring_markers` (`tagln` and `acta2` do ground and stay in the spine).
- **mesenchyme** keeps the type-I collagens (`col1a1a`, `col1a2`) in `scoring_markers`: pan-ECM
  genes that aid overlap but ground in mature connective tissue, not the embryonic mesenchyme term.
- **pigment** keeps `xdh` (xanthophore) in `scoring_markers` — its ZFIN expression is too sparse to ground.
- **cardiac** descends toward cardiac muscle (`ZFA:0005280`); Daniocell has no heart
  tissue, so this panel is exercised by other atlases rather than that benchmark.

## Curation & validation

- **Current ZFIN symbols only**, enforced by `scripts/audit_panels.py`: every marker
  resolves through the ZFIN GAF synonym map, and each identity panel has at least
  `CONVERGENCE_MIN` (3) markers whose ZFIN wildtype expression grounds under its
  anchor. `scripts/verify_anchors.py` checks every anchor id exists in `zfa.obo`.
- **Nomenclature**: teleost duplicates use `a`/`b` (`fli1` / `fli1b`); tandem
  duplicates use `.1`/`.2` (`tnnc2.2`, `mfap4.1`).
- **Anchors are zebrafish-native (ZFA)** and chosen coarse, so a marker expressing
  anywhere in the tissue still grounds; where a Daniocell tissue exists, the anchor
  matches the eval crosswalk so predictions are credited.
- **Markers come from ZFIN wildtype expression and primary literature** — never
  Daniocell cluster markers, which would make the eval circular.

## Completeness

[`benchmarks/cell_population_coverage.yaml`](../../benchmarks/cell_population_coverage.yaml)
records every major atlas cell population, the bucket it maps to, and the expected
anchor; `tests/test_coverage.py` keeps it consistent with `panels.yaml`. Regional
labels (pharyngeal arch, paraxial mesoderm, sclerotome) resolve to their lineage
buckets. Two populations are not yet panels because their ZFA terms are too sparsely
curated to reach the grounding bar — **hatching gland** and **thyroid**; clusters of
those types abstain.

## References

- **ZFIN** — gene nomenclature, GAF synonyms, wildtype expression. https://zfin.org/downloads
- **ZFA** — Zebrafish Anatomy Ontology. https://github.com/obophenotype/zebrafish-anatomical-ontology
- **Daniocell** — Sur, Wang, Farrell et al., *Developmental Cell* 2023. https://daniocell.nichd.nih.gov
- **Zebrahub** — Lange et al., *Cell* 2024. https://zebrahub.org
- **ZSCAPE** — Saunders, Srivatsan et al., *Nature* 2023. https://cole-trapnell-lab.github.io/zscape
- [`docs/reference/cell_labelling_playbook.md`](cell_labelling_playbook.md) — marker and ontology background.
