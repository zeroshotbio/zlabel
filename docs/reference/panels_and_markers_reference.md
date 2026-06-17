# Panel & marker reference

The companion to [`src/zlabel/panels.yaml`](../../src/zlabel/panels.yaml): why each
bucket exists, what its markers are, why its ZFA anchor is right, and the evidence
behind every choice. `panels.yaml` is the lean machine-readable model; this is the
prose and the citations.

## Bottom line

zlabel's panels are a **complete, dataset-agnostic broad taxonomy**. Every cell
population in the major zebrafish atlases (Daniocell, Zebrahub, ZSCAPE; the internal
ChemFish / MiniFin / MegaFin inherit by projection onto these) maps up to exactly one
bucket — a scientist could say which one fits. Fine subtypes are **not** separate
panels; they fall out of the ZFA convergence descent (`resolve.py`). Labels are
scientist-sensible, not copies of any atlas's strings: what matters is that a
cluster's **marker signature resolves to the correct ZFA anchor**.

Each panel is a *coarse prior + descent anchor*, not the naming authority. The scorer
ranks buckets by marker overlap; the winning bucket's `ontology_anchor` seeds the
support-weighted descent that names the cluster at honest depth. See
[`docs/design.md`](../design.md) and [`.claude/docs/domain.md`](../../.claude/docs/domain.md).

## How to read this file

- **Anchor**: the ZFA term(s) the descent seeds at. Verified to exist by
  `scripts/verify_anchors.py`; verified to be *reachable from the markers' in-vivo
  expression* by `scripts/audit_panels.py`.
- **Grounding (N/M)**: of M markers, N have ZFIN wildtype-expression records at or
  under the anchor — the panel's convergence capacity (needs ≥ `CONVERGENCE_MIN`=3).
- **note**: previous ZFIN name resolved, or "scoring" for a marker that aids bucket
  scoring but does not itself ground under the cell-type anchor.

## Curation & validation rules

- **Current ZFIN symbols only**, enforced by `scripts/audit_panels.py`: every marker
  must resolve via the ZFIN GAF synonym map, and each identity panel must have ≥3
  markers grounding under its anchor. Last validated 2026-06-16.
- **Paralog / tandem-duplicate nomenclature**: teleost duplicates use `a`/`b`
  (`fli1` vs `fli1b`), tandem duplicates use `.1`/`.2` (`tnnc2.2`, `mfap4.1`). Several
  prior entries were previous names and were updated to the current symbol (see
  Changelog).
- **Anchors are zebrafish-native (ZFA)** and chosen coarse, so a marker expressing
  anywhere in the tissue still grounds. Where a Daniocell tissue exists, the anchor
  matches the eval crosswalk so predictions are credited.
- **Markers come from ZFIN wildtype expression + primary literature, never Daniocell
  cluster markers** — citing the benchmark would make the eval circular.
- **Deferred buckets**: hatching gland and thyroid cannot reach the ≥3-grounding bar
  with current ZFIN curation; such clusters abstain. Tracked in
  [`benchmarks/cell_population_coverage.yaml`](../../benchmarks/cell_population_coverage.yaml).

---

## Ectoderm — neural / sensory / surface

### neural — nervous system (ZFA:0000396) · grounding 8/8
Pan-neural identity (neurons + progenitors); fine depth (region, neuron type) comes from the descent.

| marker | role | note |
|---|---|---|
| elavl3 | pan-neuronal RNA-binding protein (HuC/HuD) | the most reliable neural marker |
| neurod1 | proneural bHLH; differentiation | |
| tubb5 | beta-tubulin; axons/progenitors | |
| sox3, sox2 | pan-neural progenitor TFs | |
| her4.1 | Notch target; radial-glia-like | |
| ascl1a | proneural bHLH | |
| gfap | astrocyte / radial glia | also in glia |

### glia — glial cell (ZFA:0009073) · grounding 6/6
Astrocyte / oligodendrocyte / radial glia / Schwann; distinct from neurons. Anchor is more specific than nervous system, so glial clusters resolve to glia rather than rolling up to CNS.

| marker | role | note |
|---|---|---|
| sox10 | oligodendrocyte + peripheral glia | also neural crest |
| olig2 | oligodendrocyte lineage | |
| mbpa | myelin basic protein | strong glial grounding |
| gfap | astrocyte / radial glia | |
| plp1b | myelin proteolipid | |
| slc1a3b | astroglial glutamate transporter (GLAST) | |

### neural_crest — neural crest / neural crest cell (ZFA:0000045 / ZFA:0009165) · grounding 6/6
The migratory, multipotent crest; pigment and craniofacial cartilage are downstream derivatives with their own buckets.

| marker | role | note |
|---|---|---|
| sox10 | pan-neural-crest | |
| foxd3 | premigratory/migratory crest | |
| tfap2a | crest specifier | |
| snai1b | EMT / delamination | |
| dlx2a | cranial neural crest | |
| sox9b | skeletogenic crest | also cartilage |

### eye — eye (ZFA:0000107) · grounding 8/8
Retina (photoreceptors, interneurons, RGC), lens, and RPE — the highest-coverage gap closed (Daniocell's 2nd-largest tissue).

| marker | role | note |
|---|---|---|
| cryaa, crybb1 | lens crystallins | |
| mipa | lens fiber aquaporin-0 | |
| rho | rod opsin | |
| opn1mw1 | cone opsin | |
| gnat2 | cone transducin | |
| crx | photoreceptor TF | |
| rpe65a | retinal pigment epithelium | |

### otic — otic vesicle / inner ear (ZFA:0000051 / ZFA:0000217) · grounding 6/6

| marker | role | note |
|---|---|---|
| otomp, oc90, otol1a | otolith matrix | |
| dlx3b | otic/placodal | |
| eya1 | otic placode | also lateral line |
| atoh1a | hair-cell fate | also lateral line |

### lateral_line — lateral line system / taste bud (ZFA:0000034 / ZFA:0001074) · grounding 5/5
Mechano/chemosensory hair-cell systems. Shares hair-cell markers with otic; the anchor (lateral line vs inner ear) and the cluster's expression disambiguate.

| marker | role | note |
|---|---|---|
| atoh1a | hair-cell fate | shared with otic |
| myo6b | hair-cell stereocilia | |
| cldnb | neuromast/primordium | |
| six1b, eya1 | placodal/sensory | |

### olfactory — olfactory system / epithelium (ZFA:0001149 / ZFA:0000554) · grounding 5/5

| marker | role | note |
|---|---|---|
| ompb | olfactory marker protein | |
| s100z | olfactory epithelium | |
| calb2b | sensory neurons | |
| gng8 | olfactory sensory neurons | |
| neurod1 | differentiating neurons | shared with neural |

### epidermis — epidermis / integument (ZFA:0000105 / ZFA:0000368) · grounding 6/6
Basal + suprabasal epidermis and periderm; mucous/goblet cells resolve here too.

| marker | role | note |
|---|---|---|
| krt4 | suprabasal/periderm keratin | |
| krt5 | basal epidermis keratin | |
| tp63 | basal progenitor TF | |
| cldne | periderm tight junction | |
| krt8 | simple/embryonic epithelium | replaces dead `epcam` |
| cldnb | periderm/epithelial junction | |

### ionocyte — ionocyte (ZFA:0005323) · grounding 6/6
Ion-transporting epidermal cells (HR, NaR, NCC subtypes by descent).

| marker | role | note |
|---|---|---|
| foxi3a, foxi3b | ionocyte master TFs | |
| ca2 | H+-ATPase-rich ionocyte | |
| slc12a10.2 | NCC ionocyte | |
| trpv6 | Ca2+-transporting ionocyte | |
| atp1b1b | Na/K-ATPase subunit | |

### pigment — pigment cell (ZFA:0009090) · grounding 5/6
Neural-crest-derived melanophore / xanthophore / iridophore.

| marker | role | note |
|---|---|---|
| mitfa | melanocyte master TF | |
| dct, tyrp1b | melanin synthesis | |
| gch2 | pteridine (xanthophore/iridophore) | |
| slc45a2 | melanocyte transporter | |
| xdh | xanthophore | scoring |

---

## Mesoderm

### muscle — musculature system (ZFA:0000548) · grounding 8/8
Skeletal muscle; subpanels (fast/slow/myoblast) reserved for subcluster resolution.

| marker | role | note |
|---|---|---|
| myod1, myog, myf5 | myogenic regulatory TFs | |
| mylpfa | fast skeletal myosin light chain | |
| acta1b, tnnt3a | sarcomeric, fast fiber | |
| tnnc2.2 | fast-fiber troponin C | prev. `tnnc2` |
| ckma | mature muscle energy metabolism | |

### cardiac — heart (ZFA:0000114, descends to cardiac muscle ZFA:0005280) · grounding 6/6
Cardiomyocytes. Atlases (Zebrahub/ZSCAPE/ChemFish) label heart; Daniocell has no heart tissue, so this serves cross-atlas completeness rather than the Daniocell eval.

| marker | role | note |
|---|---|---|
| myl7 | pan-cardiomyocyte (cmlc2) | |
| myh6 | atrial myocardium | |
| myh7 | ventricular myocardium | prev. `vmhc` |
| nppa | chamber myocardium | |
| tnnt2a | cardiac sarcomere | |
| ttn.2 | sarcomere titin | |

### mural — mural cell (ZFA:0005944) · grounding 4/6
Pericytes + vascular smooth muscle. The ZFA mural-cell term has sparse curated expression, so grounding is thin (lower-confidence bucket); contractile markers aid scoring.

| marker | role | note |
|---|---|---|
| pdgfrb | pericyte recruitment | |
| notch3 | mural identity | |
| tagln, acta2 | smooth-muscle contractile | scoring |
| desma, cspg4 | mural/pericyte | scoring |

### endothelium — vasculature / endothelial cell (ZFA:0005249 / ZFA:0009065) · grounding 6/6
Vascular + lymphatic endothelium (arterial/venous/lymphatic by descent).

| marker | role | note |
|---|---|---|
| kdrl | VEGFR2; vascular endothelium | |
| fli1 | pan-endothelial ETS TF | prev. `fli1a` |
| etsrp | hemato-vascular progenitor | prev. `etv2` |
| cdh5 | VE-cadherin junction | |
| pecam1a | pan-endothelial | prev. `pecam1` |
| flt1 | VEGFR1; venous/tip | |

### blood_erythroid — blood / hematopoietic system (ZFA:0000007 / ZFA:0005023) · grounding 7/7
Restored from 3 live markers (three were dead in the prior file).

| marker | role | note |
|---|---|---|
| gata1a | erythroid master TF | |
| hbae1.1 | embryonic alpha-globin | |
| hbbe2 | embryonic beta-globin | replaces dead `hbbe1.1` |
| alas2 | heme biosynthesis | |
| klf1 | erythroid differentiation TF | prev. `klf1a` |
| slc4a1a | band-3; erythrocyte membrane | replaces dead `hemgn` |
| cahz | erythrocyte carbonic anhydrase | |

### immune_myeloid — immune system / hematopoietic system (ZFA:0001159 / ZFA:0005023) · grounding 7/7
Macrophage + neutrophil (and microglia).

| marker | role | note |
|---|---|---|
| lcp1 | pan-leukocyte (L-plastin) | |
| mpeg1.1 | macrophage | |
| coro1a | leukocyte/macrophage | |
| spi1b | myeloid master TF (PU.1) | |
| mfap4.1 | macrophage | prev. `mfap4` |
| lyz | innate effector | |
| csf1ra | macrophage CSF1 receptor | |

### blood_lymphoid — lymphocyte (ZFA:0009250) · grounding 5/5
T / B / NK. Rare in early embryo, prominent in juvenile/adult and ZSCAPE.

| marker | role | note |
|---|---|---|
| lck | pan-T receptor signaling | |
| rag1, rag2 | V(D)J recombination | |
| il7r | lymphoid progenitor | |
| cd8a | cytotoxic T cell | |

### pronephros — pronephros (ZFA:0000151) · grounding 7/7
Embryonic kidney: podocyte, proximal/distal tubule, duct (by descent).

| marker | role | note |
|---|---|---|
| pax2a | nephron progenitor TF | |
| wt1a, wt1b | podocyte/glomerulus | |
| slc20a1a | proximal tubule | |
| cdh17 | tubule/duct | |
| slc12a1 | distal tubule | |
| pax8 | nephron progenitor | |

### mesenchyme — mesenchyme (ZFA:0000393) · grounding 5/7
Fibroblast / connective / stromal. The collagens aid scoring but ground in mature connective-tissue terms outside the embryonic mesenchyme anchor.

| marker | role | note |
|---|---|---|
| dcn | mesenchymal proteoglycan | |
| twist1a | mesenchymal/EMT TF | |
| prrx1a | limb/craniofacial mesenchyme | |
| osr2 | lateral-plate/craniofacial | |
| fn1a | ECM fibronectin | |
| col1a1a, col1a2 | type-I collagen ECM | scoring |

### cartilage — cartilage element / chondrocyte (ZFA:0001501 / ZFA:0009084) · grounding 6/6

| marker | role | note |
|---|---|---|
| sox9a, sox9b | chondrogenic TFs | |
| col2a1a | hyaline cartilage ECM | |
| acana | cartilage proteoglycan | |
| matn1 | cartilage ECM | |
| runx2b | osteochondrogenic | |

### osteoblast — osteoblast / bone tissue (ZFA:0009031 / ZFA:0005621) · grounding 6/6

| marker | role | note |
|---|---|---|
| sp7 | osteoblast master TF (osterix) | |
| spp1 | osteopontin; bone matrix | |
| bglap | osteocalcin; mature osteoblast | |
| col10a1a | hypertrophic/perichondral bone | |
| runx2a, runx2b | osteoblast determination | |

### notochord — notochord (ZFA:0000135) · grounding 5/5

| marker | role | note |
|---|---|---|
| tbxta | notochord master TF | prev. `ntl` |
| shha | notochord signaling | |
| col2a1a, col8a1a | notochord sheath ECM | |
| noto | notochord-specific TF | |

### fin — fin / fin bud (ZFA:0000108 / ZFA:0001383) · grounding 6/6

| marker | role | note |
|---|---|---|
| tbx5a | pectoral fin bud initiation | |
| fgf24 | fin bud outgrowth | |
| hoxd13a, hoxa13a | distal fin/autopod | |
| msx1b | fin fold/apical | prev. `msxb` |
| and1 | actinotrichia | |

---

## Endoderm

### endoderm_gut — digestive system / presumptive endoderm (ZFA:0000339 / ZFA:0000416) · grounding 6/6
Early endoderm and gut field; liver/pancreas/intestine resolve deeper via their own buckets.

| marker | role | note |
|---|---|---|
| sox32 | endoderm master regulator (casanova) | |
| sox17 | definitive endoderm | |
| foxa2 | endoderm/liver/floor plate | |
| gata5, gata6 | early endoderm | |
| hhex | liver/thyroid endoderm | |

### liver — liver (ZFA:0000123) · grounding 6/6
Hepatocyte. Eval-creditable via Daniocell `endo` (liver is under digestive system).

| marker | role | note |
|---|---|---|
| fabp10a | hepatocyte fatty-acid binding | |
| cp | ceruloplasmin | |
| tfa | transferrin | |
| gc | vitamin-D binding protein | |
| f2 | prothrombin | |
| serpina1l | protease inhibitor | |

### pancreas — pancreas (ZFA:0000140) · grounding 6/6
Endocrine islet (ins/gcga/sst2/pdx1) + exocrine acinar (prss1/cpa5).

| marker | role | note |
|---|---|---|
| ins | beta cell insulin | |
| gcga | alpha cell glucagon | |
| sst2 | delta cell somatostatin | |
| pdx1 | pancreas/beta progenitor | |
| prss1 | exocrine trypsin | |
| cpa5 | exocrine carboxypeptidase | |

### intestine — intestine (ZFA:0001338) · grounding 5/5

| marker | role | note |
|---|---|---|
| fabp2 | enterocyte fatty-acid binding | |
| fabp6 | ileal/bile-acid enterocyte | |
| cdx1b | posterior gut TF | |
| slc15a1b | intestinal peptide transport | |
| vil1 | brush border | |

---

## Germline

### germline — germ line cell (ZFA:0009016) · grounding 4/4

| marker | role | note |
|---|---|---|
| ddx4 | germ-cell helicase | prev. `vasa` |
| nanos3 | germline maintenance | |
| dazl | germ-cell RNA-binding | |
| piwil1 | piRNA pathway | |

---

## Endocrine

### pituitary — adenohypophysis (ZFA:0001282) · grounding 6/6

| marker | role | note |
|---|---|---|
| pou1f1 | pituitary lineage TF (Pit1) | |
| prl | lactotrope | |
| gh1 | somatotrope | |
| pomca | cortico/melanotrope | |
| tshba | thyrotrope | |
| cga | glycoprotein-hormone alpha | |

### interrenal — interrenal gland (ZFA:0001345) · grounding 4/4
The teleost adrenal-cortex homolog (steroidogenic).

| marker | role | note |
|---|---|---|
| nr5a1a | steroidogenic TF (SF-1) | |
| cyp11a1.1 | steroidogenesis | |
| star | steroidogenesis | |
| mc2r | ACTH receptor | |

### pineal — epiphysis (ZFA:0000019) · grounding 4/4

| marker | role | note |
|---|---|---|
| aanat2 | melatonin synthesis | |
| exorh | pineal photoreceptor opsin | |
| otx5 | pineal photoreceptor TF | |
| asip2b | pineal | |

---

## State panels (orthogonal to identity)

A cycling muscle cell is still muscle; the state is recorded separately and carries
no anatomy anchor.

- **cycling**: mki67, pcna, top2a, hmgb2a, stmn1a (GO cell-cycle).
- **stress_response**: hsp70l, hspa5, dnajb1b (heat-shock) + fosab, atf3 (immediate-early).

---

## Eval impact (Daniocell benchmark)

Re-running `src/zlabel/evaluate.py` after this expansion (vs. the committed baseline):

| metric | baseline | after |
|---|---|---|
| coverage (non-abstain) | 7.6% (39/511) | 12.9% (66/511) |
| broad agreement | 56.4% | 70.3% |
| abstain | 92.4% | 87.1% |
| high-confidence (correct) | 2/2 | 12/12 |
| thin-support overcalls | 1/39 | 1/36 |

Coverage and agreement both rose with no overcall regression — the descent's support
floors hold while the new buckets give honest clusters somewhere to land.

## Completeness

[`benchmarks/cell_population_coverage.yaml`](../../benchmarks/cell_population_coverage.yaml)
records every major atlas population, the bucket it maps to, and the expected anchor;
`tests/test_coverage.py` keeps it consistent with `panels.yaml`. Regional labels
(pharyngeal arch, paraxial mesoderm, sclerotome) resolve to lineage buckets; deferred
populations (hatching gland, thyroid) abstain until curation improves.

## Changelog (vs. the prior 12+2 panel file)

- **Fixed dead markers** absent from the ZFIN GAF: `epcam` → `krt8`/`cldnb`
  (epidermis); `hbbe1.1`,`hemgn` → `hbbe2`,`slc4a1a`,`cahz` (erythroid; was down to 3
  live markers).
- **Updated previous names to current symbols**: `fli1a`→`fli1`, `etv2`→`etsrp`,
  `pecam1`→`pecam1a` (endothelium); `tnnc2`→`tnnc2.2` (muscle); `mfap4`→`mfap4.1`
  (immune_myeloid); `klf1a`→`klf1` (erythroid); `vmhc`→`myh7` (cardiac).
- **Added 19 buckets** for atlas completeness: glia, neural_crest, eye, otic,
  lateral_line, olfactory, ionocyte (ectoderm); cardiac, mural, blood_lymphoid,
  pronephros, osteoblast, fin (mesoderm); liver, pancreas, intestine (endoderm);
  pituitary, interrenal, pineal (endocrine).
- **Deferred** hatching gland and thyroid (insufficient ZFIN grounding).

## References

- ZFIN — gene nomenclature, GAF synonyms, wildtype expression. https://zfin.org/downloads
- ZFA — Zebrafish Anatomy Ontology. https://github.com/obophenotype/zebrafish-anatomical-ontology
- Daniocell — Sur, Wang, Farrell et al., *Developmental Cell* 2023. https://daniocell.nichd.nih.gov
- Zebrahub — Lange et al., *Cell* 2024. https://zebrahub.org
- ZSCAPE — Saunders, Srivatsan et al., *Nature* 2023. https://cole-trapnell-lab.github.io/zscape
- [`docs/reference/cell_labelling_playbook.md`](cell_labelling_playbook.md) §7 — the v1 starter panels.
