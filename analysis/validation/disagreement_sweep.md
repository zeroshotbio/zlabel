# Disagreement sweep — literature + ZFIN adjudication of every scored named miss

**Read-only validation. No engine code or behavior changed.** The Daniocell baseline reports 74.0%
broad agreement and lists a "failure gallery." This sweep takes **all 45 scored named/fallback calls
that disagree with the Daniocell gold** and adjudicates each one the way a referee would — zlabel's
own trace + ZFIN curated expression + published literature — into three buckets: the gold is
wrong/coarse (zlabel is right), the promiscuity wall (right class, wrong fine region), or a genuine
engine error.

- **Source:** `benchmarks/daniocell_eval.csv`, engine on `main` (anchor-rooted descent), ZFA
  `releases/2026-06-02`, ZFIN wildtype-expression corpus.
- **Reproduce the set:** `cluster_outcomes(...)` filtered to `kind in {named,fallback} & scored &
  agrees is False` → 45 clusters. Per-cluster descent terminal and marker identity-signal were read
  from `Labeler.trace`; raw markers from the eval CSV.

---

## Headline

**Of the 45 "failures," almost none are zlabel being biologically wrong about a cluster's dominant
signal.** They split:

| Bucket | Count | What it is |
|--------|------:|------------|
| **A — Gold wrong / coarser; zlabel correct or correct superclass** | **~26 (58%)** | The disagreement is a gold-label or crosswalk-granularity artifact, not an engine error. Fixing the crosswalk would *raise* reported agreement. |
| **B — Promiscuity wall: right germ-layer/class, wrong fine region or organ** | **~12 (27%)** | The documented "Known limit." Pan-neuronal/sensory markers pull the descent to a wrong fine region (the `glia.11 → diencephalon` mechanism). |
| **C — Genuine engine error: a minority attractor beat the dominant identity** | **~3–5 (7–11%)** | A real bug: stray keratins routed cartilage/notochord clusters into the epidermis attractor. |

The reported 74% broad agreement **understates** the engine: a large share of the 26% "disagreement"
is the gold being noisy or coarser than zlabel, not zlabel being wrong.

---

## Bucket A — gold wrong / coarser (zlabel is right or names the correct superclass)

| Cluster | gold | zlabel | Marker evidence (dominant signal) | Adjudication |
|---|---|---|---|---|
| hema.2 | hema | blood vessel | `cdh5 tie1 etv2 egfl7 clec14a mrc1a lyve1b` — pure endothelium, **zero blood markers** | zlabel right; "hema" bundles endothelium |
| hema.24 | hema | dorsal aorta | `cdh5 kdrl pecam1 cldn5 sox7 podxl` — arterial endothelium | zlabel right |
| hema.28 | hema | dorsal aorta | `kdrl pecam1 cdh5 cldn5 clec14a` | zlabel right |
| hema.30 | hema | posterior cardinal vein | `ramp2 ecscr egfl7 etv2 lyve1b mrc1a` — venous/lymphatic endothelium | zlabel right |
| hema.37 | hema | blood vasculature | `flt4 lyve1b mrc1a stab2 etv2` — lymphatic/venous endothelium | zlabel right |
| pgc.1 | pgc | germline | `ddx4` (**vasa**) — the canonical germ-cell marker | zlabel **exactly right**; crosswalk artifact |
| eye.22 | eye | pigment cell | `pmela dct tyrp1b oca2 slc45a2` + `presumptive RPE` signal — retinal pigment epithelium | correct cell-type; gold = organ |
| fin.9 | fin | fin fold pectoral fin bud | `and1 and2` (**actinodin**, fin-fold specific) | names a fin structure; miss is a crosswalk-anchor technicality |
| fin.3/5/11/19 | fin | epidermis | `krt4 krt5 cyt1 cldn epcam aqp3a` — fin **epidermis** | correct cell-class; gold = organ |
| peri.2/3/4/5/6/7/11/13/20/22/23/26/29 (13) | peri | epidermis / integument | `krt4 cyt1 krt5` + `EVL`, `epidermal superficial stratum` signal | **periderm = EVL = superficial epidermis** — correct superclass |
| mura.3 | mura | mesenchyme | `foxf2a col4a col6a dcn col1a2 barx1` — perivascular mesenchyme | correct superclass (mural ⊂ mesenchyme) |

Two biological bridges, both literature-confirmed: **periderm is the enveloping layer (EVL), the
superficial keratin layer of the epidermis** (Krt4/Cyt1/Krt8); **hematopoietic stem cells bud from the
hemogenic endothelium of the dorsal aorta** — blood and endothelium are sister lineages, so a "hema"
supercluster of endothelial cells naming as dorsal aorta / vessel is correct, not a miss.

## Bucket B — promiscuity wall (right class, wrong fine region) — the `glia.11` pattern

| Cluster | gold | zlabel | What the markers really are | Why the miss |
|---|---|---|---|---|
| eye.14, eye.20 | eye | epiphysis | retinal photoreceptors (`crx`-type, rod/cone signal) | pineal & retina are **serially homologous photoreceptive organs** (shared `otx5`/`crx`) — descent can't separate them |
| eye.15, eye.36 | eye | forebrain / nervous system | retinal/neural; lateral-line & statoacoustic ganglion signal | over-coarse neural; eye derives from forebrain |
| otic.7 | otic | neuromast | otic **hair cells** (`otofb myo6b six1b gipc3`) | otic & lateral-line hair cells share the program; wrong organ, right cell-type |
| tast.1, tast.9 | tast | peripheral olfactory organ | chemosensory; lateral-line/olfactory signal | sensory cross-talk |
| tast.19 | tast | retina | neuroendocrine/sensory (`chga scg2a insm1a`) | sensory/neural overlap |
| pigm.6 | pigm | forebrain | **pan-neuronal** (`elavl3 stmn1b gpm6a sncb`), no pigment markers | gold-noise + neural-region overcall |
| pron.15 | pron | epiphysis | **pan-neuronal**, no kidney markers | gold-noise + neural-region overcall |
| mese.6 | mese | nervous system | neural + collagen (cranial neural crest?) | promiscuous neural attractor |
| musc.19 | musc | segmental plate | paraxial mesoderm (`tcf15 twist1a`) + connective | defensible lineage, thin support |

Same root cause as `glia.11 → diencephalon`: promiscuous pan-neuronal / sensory-ganglion markers
out-vote the few identity-specific markers, and the descent rides the **region axis** instead of the
**cell-type axis**, overcalling a wrong fine region.

## Bucket C — genuine engine error (attractor beat the dominant identity)

| Cluster | gold | zlabel | Dominant signal it missed | Bug |
|---|---|---|---|---|
| axia.6, axia.9, axia.16 | axia | epidermis | `col2a1a col9 col11 chad cnmd` (cartilage) + `tbxta` (**notochord**) | a handful of keratins (`krt5 krt8 krt15`) routed an axial cartilage/notochord cluster into the **epidermis attractor** |

(Borderline: `otic.18`, `otic.11`, `iono.1`, `iono.18` predict epidermis, but their markers genuinely
*are* epidermal keratins — so they read as "epidermal cells within that organ," i.e. closer to Bucket A
than a clean error.)

---

## Actionable findings

1. **Crosswalk/gold fixes are free accuracy.** periderm ⊂ epidermis, hema ⊃ endothelium, pgc = germline,
   mural ⊂ mesenchyme, RPE = pigment cell, fin actinodin. ~20 of the 45 "disagreements" are the
   crosswalk scoring a correct (or correct-superclass) call as a miss. Reconciling these would lift the
   reported 74% materially without touching the engine.

2. **The promiscuity wall is the real, known limit** — and it is the *same* mechanism in every neural
   miss: region-axis descent + promiscuous markers → wrong fine region (epiphysis, forebrain,
   diencephalon). A depth governor that refuses to descend the region axis on promiscuous pan-neuronal
   clusters (or that prefers the grounded cell-type term, e.g. `branchiomotor neuron`) would convert
   over-calls into honest coarser calls.

3. **One concrete bug to fix now:** the **epidermis attractor** wins on stray keratins even when the
   dominant signal is cartilage/notochord (`axia.*`: `col2a1a`/`tbxta` present, yet predicted
   epidermis). A guard — when a cluster carries strong cartilage/notochord collagen support, the
   epidermis bucket should not win on minority keratins — fixes the only clear-cut biological errors in
   the set.

## Caveats

- "Gold-noise" calls (e.g. `pigm.6`/`pron.15` are pan-neuronal, `hema.*` are endothelial) are read
  from the cluster's own markers, not an external re-clustering; they are high-confidence where a
  canonical marker is decisive (`ddx4`, `cdh5`/`kdrl`, `elavl3`) and weaker where the cluster is mixed.
- Bucket boundaries are judgement calls on a few borderline rows (`otic.18`, `iono.*`, `musc.19`); the
  counts are robust to those (±2), the headline is not.

## Sources

- Periderm/EVL: [Analysis of zebrafish periderm enhancers (eLife 2020)](https://elifesciences.org/articles/51325) ·
  [Basal keratinocytes contribute to all strata of adult zebrafish epidermis (PLoS One 2014)](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0084858)
- Hemogenic endothelium: [Blood stem cell-forming haemogenic endothelium derives from arterial endothelium (Nat Commun 2019)](https://www.nature.com/articles/s41467-019-11423-2) ·
  [Live imaging of Runx1 in the dorsal aorta (Blood 2010)](https://ashpublications.org/blood/article/116/6/909/27637)
- Pineal/retina serial homology: [Otx5 regulates circadian genes in the zebrafish pineal (Nat Genet 2002)](https://www.nature.com/articles/ng793) ·
  [Bsx specifies pineal identity among photoreceptive organs (Commun Biol 2019)](https://www.nature.com/articles/s42003-019-0613-1)
- Branchiomotor anchor (the `glia.11` worked case): [Ahn 2000 tbx20 (PMID 10906473)](https://pubmed.ncbi.nlm.nih.gov/10906473/) ·
  [Tbx20 cranial motor neuron migration (Development 2006)](https://journals.biologists.com/dev/article/133/24/4945/52935)
