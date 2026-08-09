# ZFA anatomical structural buckets

Ontology data-version: `releases/2026-06-02`.

## TL;DR

ZFA does not encode one linear five-rung is_a ladder. This export assigns each active term one exclusive structural bucket from configured ZFA roots (many with legacy CARO xrefs), then builds a generated part_of display tree under system anchors.

### Why six principal buckets (not five)?

The underlying ZFA/CARO structural categories are five: cell, tissue, multi-tissue structure, organ, anatomical system. We split the last one into two display buckets so transitive system subtypes (CNS is_a nervous system; cranium is_a skeletal system) are not collapsed into the same count as true top-level systems:

1. anatomical_system — ZFA:0001439 itself or a direct is_a child (19 terms)
2. anatomical_system_subtype — other is_a* descendants of anatomical system (40 terms)
3. organ
4. multi_tissue_structure
5. tissue
6. cell

Everything else lands in secondary named buckets (cluster, embryonic, space, substance, …) or other_unclassified_anatomical_entity. This is a structural classification export — not a cell-type labeling depth ladder.

### Counts at a glance

- Active terms: **3107**
- Obsolete (excluded): **53**
- Stranded (unattached in generated hierarchy): **1533**

| Bucket | Count |
| --- | ---: |
| `anatomical_system` | 19 |
| `anatomical_system_subtype` | 40 |
| `organ` | 419 |
| `multi_tissue_structure` | 645 |
| `tissue` | 866 |
| `cell` | 650 |
| **Principal subtotal** | **2639** |
| Secondary + unclassified | 468 |
| **Total active** | **3107** |

Legacy note: CARO is deprecated in favour of Uberon; CARO xrefs here are historical alignment metadata on ZFA roots, not a current authoritative upper ontology.

## Principal structural buckets

| Bucket | Rule | Notes |
| --- | --- | --- |
| `anatomical_system` | `ZFA:0001439` or direct is_a child | ZFA anatomical-system root and its immediate children |
| `anatomical_system_subtype` | Other is_a* descendants of anatomical system | Taxonomic subtypes (e.g. CNS is_a nervous system), not mereological subdivisions |
| `organ` | is_a* compound organ (`ZFA:0000496`) or simple organ (`ZFA:0001492`); cavitated/solid included under compound | Includes skeletal elements / fin rays as ZFA models them |
| `multi_tissue_structure` | is_a* `ZFA:0001488` | Multi-tissue bounded unit |
| `tissue` | is_a* portion of tissue | Tissue-level organization |
| `cell` | is_a* `ZFA:0009000` cell | cell_slim / CL xrefs are metadata only |

### Display-assignment precedence (principal)

```text
anatomical_system > anatomical_system_subtype > organ
> multi_tissue_structure > tissue > cell
```

Among equal-rank hits, source_class is the deepest configured classification root (e.g. cavitated compound organ over compound organ).

### Secondary buckets (exclusive; deepest configured root wins)

| Output bucket | Configured ZFA roots | Notes |
| --- | --- | --- |
| `anatomical_cluster` | `ZFA:0001478` | Deeper than anatomical group; exclusive count is not the group ancestry total |
| `anatomical_group` | `ZFA:0001512` | Broader group class |
| `organism_subdivision` | `ZFA:0001308`, `ZFA:0000292` (surface structure) | Deeper surface-structure root preferred when both match |
| `anatomical_space` | `ZFA:0001643` | |
| `organism_substance` | `ZFA:0001487` | e.g. blood |
| `acellular_structure` | `ZFA:0000382` | |
| `embryonic_structure` | `ZFA:0001105` | |
| `extraembryonic_structure` | `ZFA:0000020` | |
| `anatomical_line` / `anatomical_surface` / `whole_organism` | CARO-aligned ZFA roots | |
| `other_unclassified_anatomical_entity` | — | Not matched to a configured bucket (may still have unused CARO xrefs) |

Two lymphatic endothelial cluster terms (`ZFA:0005954`, `ZFA:0005955`) are forced to anatomical_group by explicit ID override (ZFA asserts is_a lymphatic system).

### explicit_germ_layer

Self or recursive develops_from path to ectoderm / endoderm / mesoderm only. Blank means no path under this inference profile — not “no known developmental origin.”

### Stranded / generated hierarchy

`stranded` = principal-bucket term not placed under an `anatomical_system` or `anatomical_system_subtype` anchor in the **generated** hierarchy.

part_of profile:

- asserted part_of edges only (no is_a-inherited restrictions)
- transitive walk; secondary-category nodes are traversable waypoints
- only principal-bucket terms appear as tree nodes
- first attach to nearest coarser principal parent (preserves organ nesting)
- if that chain never reaches a system/subtype anchor, reattach to the nearest reachable hierarchy-root ancestor
- single preferred parent (no multi-tree duplication)

Hierarchy column **Immediate children in generated hierarchy** counts those tree edges — not raw ZFA direct part_of children. Empty anchors are often is_a forests.

## Summary counts

- Active terms: **3107**
- Obsolete (excluded): **53**
- Stranded (unattached in generated hierarchy): **1533**

| Level | Count |
| --- | ---: |
| `anatomical_system` | 19 |
| `anatomical_system_subtype` | 40 |
| `organ` | 419 |
| `multi_tissue_structure` | 645 |
| `tissue` | 866 |
| `cell` | 650 |
| `anatomical_cluster` | 162 |
| `anatomical_group` | 6 |
| `organism_subdivision` | 67 |
| `anatomical_space` | 67 |
| `acellular_structure` | 19 |
| `organism_substance` | 19 |
| `embryonic_structure` | 86 |
| `extraembryonic_structure` | 3 |
| `anatomical_line` | 15 |
| `anatomical_surface` | 2 |
| `whole_organism` | 3 |
| `other_unclassified_anatomical_entity` | 19 |

## Artifacts

JSON/JSONL under the output directory from make zfa-scale (default `data/zfa/`). This markdown is emitted by the same command (`anatomical_levels.md` plus `docs/zfa-anatomical-levels.md` via the Makefile).

## Examples

| Structure | ZFA id | Bucket | Source class | explicit_germ_layer |
| --- | --- | --- | --- | --- |
| adaxial cell (stranded) | `ZFA:0000003` | `cell` | `ZFA:0009000` cell | — |
| ectoderm (stranded) | `ZFA:0000016` | `tissue` | `ZFA:0001477` portion of tissue | ectoderm |
| diencephalon | `ZFA:0000101` | `multi_tissue_structure` | `ZFA:0001488` multi-tissue structure | — |
| hindbrain | `ZFA:0000029` | `multi_tissue_structure` | `ZFA:0001488` multi-tissue structure | — |
| brain | `ZFA:0000008` | `organ` | `ZFA:0001490` cavitated compound organ | — |
| central nervous system | `ZFA:0000012` | `anatomical_system_subtype` | `ZFA:0001439` anatomical system | — |
| nervous system | `ZFA:0000396` | `anatomical_system` | `ZFA:0001439` anatomical system | — |
| blood | `ZFA:0000007` | `organism_substance` | `ZFA:0001487` portion of organism substance | — |
| Kupffer's vesicle | `ZFA:0000001` | `embryonic_structure` | `ZFA:0001105` embryonic structure | — |
| ventral wall of dorsal aorta | `ZFA:0005028` | `tissue` | `ZFA:0001477` portion of tissue | — |
| mandibular fat | `ZFA:0005764` | `tissue` | `ZFA:0001477` portion of tissue | — |
| cardiac lymphatic endothelial cluster | `ZFA:0005954` | `anatomical_group` | `ZFA:0001512` anatomical group | — |

## Hierarchy anchors (system + subtype)

| Id | Name | Bucket | Immediate children in generated hierarchy |
| --- | --- | --- | ---: |
| `ZFA:0001327` | abdominal musculature | `anatomical_system_subtype` | 0 |
| `ZFA:0001154` | anal fin musculature | `anatomical_system_subtype` | 5 |
| `ZFA:0000167` | anal fin skeleton | `anatomical_system_subtype` | 4 |
| `ZFA:0001439` | anatomical system | `anatomical_system` | 0 |
| `ZFA:0001468` | anterior lateral line system | `anatomical_system_subtype` | 11 |
| `ZFA:0001574` | autonomic nervous system | `anatomical_system_subtype` | 1 |
| `ZFA:0001123` | axial fin skeleton | `anatomical_system_subtype` | 0 |
| `ZFA:0005063` | cardiac conduction system | `anatomical_system` | 0 |
| `ZFA:0000010` | cardiovascular system | `anatomical_system` | 15 |
| `ZFA:0000628` | caudal fin musculature | `anatomical_system_subtype` | 3 |
| `ZFA:0000862` | caudal fin skeleton | `anatomical_system_subtype` | 15 |
| `ZFA:0005074` | central cardiac conduction system | `anatomical_system_subtype` | 0 |
| `ZFA:0000012` | central nervous system | `anatomical_system_subtype` | 25 |
| `ZFA:0000328` | cephalic musculature | `anatomical_system_subtype` | 1 |
| `ZFA:0000737` | cranium | `anatomical_system_subtype` | 123 |
| `ZFA:0005819` | deep caudal fin musculature | `anatomical_system_subtype` | 5 |
| `ZFA:0000339` | digestive system | `anatomical_system` | 15 |
| `ZFA:0000648` | dorsal fin musculature | `anatomical_system_subtype` | 5 |
| `ZFA:0001124` | dorsal fin skeleton | `anatomical_system_subtype` | 3 |
| `ZFA:0001158` | endocrine system | `anatomical_system` | 8 |
| `ZFA:0001324` | enteric musculature | `anatomical_system_subtype` | 2 |
| `ZFA:0001155` | enteric nervous system | `anatomical_system_subtype` | 1 |
| `ZFA:0000511` | extraocular musculature | `anatomical_system_subtype` | 6 |
| `ZFA:0000207` | fin musculature | `anatomical_system_subtype` | 0 |
| `ZFA:0001101` | gustatory system | `anatomical_system_subtype` | 11 |
| `ZFA:0005391` | head sensory canal system | `anatomical_system_subtype` | 7 |
| `ZFA:0005023` | hematopoietic system | `anatomical_system` | 7 |
| `ZFA:0001159` | immune system | `anatomical_system` | 7 |
| `ZFA:0005734` | lacunocanalicular system | `anatomical_system` | 1 |
| `ZFA:0000034` | lateral line system | `anatomical_system_subtype` | 10 |
| `ZFA:0000036` | liver and biliary system | `anatomical_system` | 6 |
| `ZFA:0000385` | lymphatic system | `anatomical_system` | 5 |
| `ZFA:0005114` | middle lateral line system | `anatomical_system_subtype` | 4 |
| `ZFA:0000548` | musculature system | `anatomical_system` | 1 |
| `ZFA:0000396` | nervous system | `anatomical_system` | 5 |
| `ZFA:0001149` | olfactory system | `anatomical_system_subtype` | 69 |
| `ZFA:0000027` | paired fin skeleton | `anatomical_system_subtype` | 1 |
| `ZFA:0001371` | pancreatic system | `anatomical_system` | 5 |
| `ZFA:0001575` | parasympathetic nervous system | `anatomical_system_subtype` | 1 |
| `ZFA:0000563` | pectoral fin musculature | `anatomical_system_subtype` | 8 |
| `ZFA:0000943` | pectoral fin skeleton | `anatomical_system_subtype` | 12 |
| `ZFA:0000258` | pelvic fin musculature | `anatomical_system_subtype` | 6 |
| `ZFA:0001387` | pelvic fin skeleton | `anatomical_system_subtype` | 5 |
| `ZFA:0005075` | peripheral cardiac conduction system | `anatomical_system_subtype` | 0 |
| `ZFA:0000142` | peripheral nervous system | `anatomical_system_subtype` | 5 |
| `ZFA:0001307` | pharyngeal musculature | `anatomical_system_subtype` | 3 |
| `ZFA:0000317` | postcranial axial skeleton | `anatomical_system_subtype` | 26 |
| `ZFA:0001471` | posterior lateral line system | `anatomical_system_subtype` | 4 |
| `ZFA:0000163` | renal system | `anatomical_system` | 5 |
| `ZFA:0000632` | reproductive system | `anatomical_system` | 5 |
| `ZFA:0000272` | respiratory system | `anatomical_system` | 1 |
| `ZFA:0000282` | sensory system | `anatomical_system` | 0 |
| `ZFA:0000434` | skeletal system | `anatomical_system` | 2 |
| `ZFA:0005818` | superficial caudal fin musculature | `anatomical_system_subtype` | 6 |
| `ZFA:0001576` | sympathetic nervous system | `anatomical_system_subtype` | 3 |
| `ZFA:0000473` | trunk musculature | `anatomical_system_subtype` | 9 |
| `ZFA:0001261` | ventricular system | `anatomical_system` | 7 |
| `ZFA:0001138` | vestibuloauditory system | `anatomical_system_subtype` | 13 |
| `ZFA:0001127` | visual system | `anatomical_system_subtype` | 3 |

## All terms by bucket

### `anatomical_system` (19)

| Id | Name | Source class | explicit_germ_layer | Stranded |
| --- | --- | --- | --- | --- |
| `ZFA:0001439` | anatomical system | `ZFA:0001439` | — |  |
| `ZFA:0005063` | cardiac conduction system | `ZFA:0001439` | — |  |
| `ZFA:0000010` | cardiovascular system | `ZFA:0001439` | — |  |
| `ZFA:0000339` | digestive system | `ZFA:0001439` | — |  |
| `ZFA:0001158` | endocrine system | `ZFA:0001439` | — |  |
| `ZFA:0005023` | hematopoietic system | `ZFA:0001439` | — |  |
| `ZFA:0001159` | immune system | `ZFA:0001439` | — |  |
| `ZFA:0005734` | lacunocanalicular system | `ZFA:0001439` | — |  |
| `ZFA:0000036` | liver and biliary system | `ZFA:0001439` | — |  |
| `ZFA:0000385` | lymphatic system | `ZFA:0001439` | — |  |
| `ZFA:0000548` | musculature system | `ZFA:0001439` | — |  |
| `ZFA:0000396` | nervous system | `ZFA:0001439` | — |  |
| `ZFA:0001371` | pancreatic system | `ZFA:0001439` | — |  |
| `ZFA:0000163` | renal system | `ZFA:0001439` | — |  |
| `ZFA:0000632` | reproductive system | `ZFA:0001439` | — |  |
| `ZFA:0000272` | respiratory system | `ZFA:0001439` | — |  |
| `ZFA:0000282` | sensory system | `ZFA:0001439` | — |  |
| `ZFA:0000434` | skeletal system | `ZFA:0001439` | — |  |
| `ZFA:0001261` | ventricular system | `ZFA:0001439` | — |  |

### `anatomical_system_subtype` (40)

| Id | Name | Source class | explicit_germ_layer | Stranded |
| --- | --- | --- | --- | --- |
| `ZFA:0001327` | abdominal musculature | `ZFA:0001439` | — |  |
| `ZFA:0001154` | anal fin musculature | `ZFA:0001439` | — |  |
| `ZFA:0000167` | anal fin skeleton | `ZFA:0001439` | — |  |
| `ZFA:0001468` | anterior lateral line system | `ZFA:0001439` | — |  |
| `ZFA:0001574` | autonomic nervous system | `ZFA:0001439` | — |  |
| `ZFA:0001123` | axial fin skeleton | `ZFA:0001439` | — |  |
| `ZFA:0000628` | caudal fin musculature | `ZFA:0001439` | — |  |
| `ZFA:0000862` | caudal fin skeleton | `ZFA:0001439` | — |  |
| `ZFA:0005074` | central cardiac conduction system | `ZFA:0001439` | — |  |
| `ZFA:0000012` | central nervous system | `ZFA:0001439` | — |  |
| `ZFA:0000328` | cephalic musculature | `ZFA:0001439` | — |  |
| `ZFA:0000737` | cranium | `ZFA:0001439` | — |  |
| `ZFA:0005819` | deep caudal fin musculature | `ZFA:0001439` | — |  |
| `ZFA:0000648` | dorsal fin musculature | `ZFA:0001439` | — |  |
| `ZFA:0001124` | dorsal fin skeleton | `ZFA:0001439` | — |  |
| `ZFA:0001324` | enteric musculature | `ZFA:0001439` | — |  |
| `ZFA:0001155` | enteric nervous system | `ZFA:0001439` | — |  |
| `ZFA:0000511` | extraocular musculature | `ZFA:0001439` | — |  |
| `ZFA:0000207` | fin musculature | `ZFA:0001439` | — |  |
| `ZFA:0001101` | gustatory system | `ZFA:0001439` | — |  |
| `ZFA:0005391` | head sensory canal system | `ZFA:0001439` | — |  |
| `ZFA:0000034` | lateral line system | `ZFA:0001439` | — |  |
| `ZFA:0005114` | middle lateral line system | `ZFA:0001439` | — |  |
| `ZFA:0001149` | olfactory system | `ZFA:0001439` | — |  |
| `ZFA:0000027` | paired fin skeleton | `ZFA:0001439` | — |  |
| `ZFA:0001575` | parasympathetic nervous system | `ZFA:0001439` | — |  |
| `ZFA:0000563` | pectoral fin musculature | `ZFA:0001439` | — |  |
| `ZFA:0000943` | pectoral fin skeleton | `ZFA:0001439` | — |  |
| `ZFA:0000258` | pelvic fin musculature | `ZFA:0001439` | — |  |
| `ZFA:0001387` | pelvic fin skeleton | `ZFA:0001439` | — |  |
| `ZFA:0005075` | peripheral cardiac conduction system | `ZFA:0001439` | — |  |
| `ZFA:0000142` | peripheral nervous system | `ZFA:0001439` | — |  |
| `ZFA:0001307` | pharyngeal musculature | `ZFA:0001439` | — |  |
| `ZFA:0000317` | postcranial axial skeleton | `ZFA:0001439` | — |  |
| `ZFA:0001471` | posterior lateral line system | `ZFA:0001439` | — |  |
| `ZFA:0005818` | superficial caudal fin musculature | `ZFA:0001439` | — |  |
| `ZFA:0001576` | sympathetic nervous system | `ZFA:0001439` | — |  |
| `ZFA:0000473` | trunk musculature | `ZFA:0001439` | — |  |
| `ZFA:0001138` | vestibuloauditory system | `ZFA:0001439` | — |  |
| `ZFA:0001127` | visual system | `ZFA:0001439` | — |  |

### `organ` (419)

| Id | Name | Source class | explicit_germ_layer | Stranded |
| --- | --- | --- | --- | --- |
| `ZFA:0005435` | actinotrichium | `ZFA:0000496` | — | yes |
| `ZFA:0005398` | anal fin actinotrichium | `ZFA:0000496` | — |  |
| `ZFA:0000646` | anal fin distal radial | `ZFA:0000496` | — |  |
| `ZFA:0001421` | anal fin lepidotrichium | `ZFA:0000496` | — |  |
| `ZFA:0005399` | anal fin lepidotrichium 1 | `ZFA:0000496` | — | yes |
| `ZFA:0005400` | anal fin lepidotrichium 2 | `ZFA:0000496` | — | yes |
| `ZFA:0005401` | anal fin lepidotrichium 3 | `ZFA:0000496` | — | yes |
| `ZFA:0005402` | anal fin lepidotrichium 4 | `ZFA:0000496` | — | yes |
| `ZFA:0005403` | anal fin lepidotrichium 5 | `ZFA:0000496` | — | yes |
| `ZFA:0005404` | anal fin lepidotrichium 6 | `ZFA:0000496` | — | yes |
| `ZFA:0005405` | anal fin lepidotrichium 7 | `ZFA:0000496` | — | yes |
| `ZFA:0000268` | anal fin proximal radial | `ZFA:0000496` | — |  |
| `ZFA:0001646` | anal fin radial | `ZFA:0000496` | — | yes |
| `ZFA:0001645` | angular bone | `ZFA:0000496` | — | yes |
| `ZFA:0000467` | anguloarticular | `ZFA:0000496` | — |  |
| `ZFA:0005886` | anterior basicapsular commissure | `ZFA:0000496` | — |  |
| `ZFA:0001432` | anterior sclerotic bone | `ZFA:0000496` | — | yes |
| `ZFA:0001644` | articular cartilage | `ZFA:0000496` | — | yes |
| `ZFA:0000471` | atrium | `ZFA:0001490` | — |  |
| `ZFA:0001500` | auditory capsule | `ZFA:0000496` | — |  |
| `ZFA:0000620` | autopalatine | `ZFA:0000496` | — |  |
| `ZFA:0001425` | basal plate cartilage | `ZFA:0000496` | — |  |
| `ZFA:0000170` | basibranchial | `ZFA:0000496` | — |  |
| `ZFA:0001223` | basibranchial 1 | `ZFA:0000496` | — | yes |
| `ZFA:0001224` | basibranchial 2 | `ZFA:0000496` | — | yes |
| `ZFA:0001225` | basibranchial 3 | `ZFA:0000496` | — | yes |
| `ZFA:0001226` | basibranchial 4 | `ZFA:0000496` | — | yes |
| `ZFA:0001060` | basidorsal | `ZFA:0000496` | — | yes |
| `ZFA:0000316` | basihyal bone | `ZFA:0000496` | — |  |
| `ZFA:0001510` | basihyal cartilage | `ZFA:0000496` | — |  |
| `ZFA:0000472` | basioccipital | `ZFA:0000496` | — |  |
| `ZFA:0001598` | basioccipital posterodorsal region | `ZFA:0000496` | — |  |
| `ZFA:0000623` | basipterygium | `ZFA:0000496` | — |  |
| `ZFA:0001539` | basipterygium cartilage | `ZFA:0000496` | — | yes |
| `ZFA:0001361` | basiventral | `ZFA:0000496` | — | yes |
| `ZFA:0001079` | blood vasculature | `ZFA:0001490` | — | yes |
| `ZFA:0001514` | bone element | `ZFA:0000496` | — | yes |
| `ZFA:0005532` | bony plate | `ZFA:0000496` | — | yes |
| `ZFA:0000008` | brain | `ZFA:0001490` | — |  |
| `ZFA:0005535` | branched anal fin ray | `ZFA:0000496` | — | yes |
| `ZFA:0005533` | branched caudal fin ray | `ZFA:0000496` | — | yes |
| `ZFA:0005534` | branched dorsal fin ray | `ZFA:0000496` | — | yes |
| `ZFA:0000476` | branchiostegal ray | `ZFA:0000496` | — |  |
| `ZFA:0001279` | branchiostegal ray 1 | `ZFA:0000496` | — | yes |
| `ZFA:0001281` | branchiostegal ray 2 | `ZFA:0000496` | — | yes |
| `ZFA:0001280` | branchiostegal ray 3 | `ZFA:0000496` | — | yes |
| `ZFA:0000009` | cardiac ventricle | `ZFA:0001490` | — |  |
| `ZFA:0000096` | cardinal system | `ZFA:0001490` | — | yes |
| `ZFA:0001501` | cartilage element | `ZFA:0000496` | — | yes |
| `ZFA:0005424` | caudal fin actinotrichium | `ZFA:0000496` | — |  |
| `ZFA:0005262` | caudal fin dorsal procurrent ray | `ZFA:0000496` | — | yes |
| `ZFA:0001550` | caudal fin lepidotrichium | `ZFA:0000496` | — |  |
| `ZFA:0001585` | caudal fin principal ray | `ZFA:0000496` | — | yes |
| `ZFA:0005512` | caudal fin principal ray 1 | `ZFA:0000496` | — | yes |
| `ZFA:0005521` | caudal fin principal ray 10 | `ZFA:0000496` | — | yes |
| `ZFA:0005522` | caudal fin principal ray 11 | `ZFA:0000496` | — | yes |
| `ZFA:0005523` | caudal fin principal ray 12 | `ZFA:0000496` | — | yes |
| `ZFA:0005595` | caudal fin principal ray 13 | `ZFA:0000496` | — | yes |
| `ZFA:0005524` | caudal fin principal ray 14 | `ZFA:0000496` | — | yes |
| `ZFA:0005525` | caudal fin principal ray 15 | `ZFA:0000496` | — | yes |
| `ZFA:0005526` | caudal fin principal ray 16 | `ZFA:0000496` | — | yes |
| `ZFA:0005527` | caudal fin principal ray 17 | `ZFA:0000496` | — | yes |
| `ZFA:0005528` | caudal fin principal ray 18 | `ZFA:0000496` | — | yes |
| `ZFA:0005529` | caudal fin principal ray 19 | `ZFA:0000496` | — | yes |
| `ZFA:0005514` | caudal fin principal ray 2 | `ZFA:0000496` | — | yes |
| `ZFA:0005513` | caudal fin principal ray 3 | `ZFA:0000496` | — | yes |
| `ZFA:0005515` | caudal fin principal ray 4 | `ZFA:0000496` | — | yes |
| `ZFA:0005516` | caudal fin principal ray 5 | `ZFA:0000496` | — | yes |
| `ZFA:0005517` | caudal fin principal ray 6 | `ZFA:0000496` | — | yes |
| `ZFA:0005518` | caudal fin principal ray 7 | `ZFA:0000496` | — | yes |
| `ZFA:0005519` | caudal fin principal ray 8 | `ZFA:0000496` | — | yes |
| `ZFA:0005520` | caudal fin principal ray 9 | `ZFA:0000496` | — | yes |
| `ZFA:0001584` | caudal fin procurrent ray | `ZFA:0000496` | — | yes |
| `ZFA:0005263` | caudal fin ventral procurrent ray | `ZFA:0000496` | — | yes |
| `ZFA:0000326` | caudal vertebra | `ZFA:0000496` | — | yes |
| `ZFA:0001490` | cavitated compound organ | `ZFA:0001490` | — | yes |
| `ZFA:0000126` | centrum | `ZFA:0000496` | — |  |
| `ZFA:0001237` | ceratobranchial 1 bone | `ZFA:0000496` | — |  |
| `ZFA:0001520` | ceratobranchial 1 cartilage | `ZFA:0000496` | — |  |
| `ZFA:0001242` | ceratobranchial 2 bone | `ZFA:0000496` | — |  |
| `ZFA:0001517` | ceratobranchial 2 cartilage | `ZFA:0000496` | — |  |
| `ZFA:0001241` | ceratobranchial 3 bone | `ZFA:0000496` | — |  |
| `ZFA:0001518` | ceratobranchial 3 cartilage | `ZFA:0000496` | — |  |
| `ZFA:0001240` | ceratobranchial 4 bone | `ZFA:0000496` | — |  |
| `ZFA:0001519` | ceratobranchial 4 cartilage | `ZFA:0000496` | — |  |
| `ZFA:0001239` | ceratobranchial 5 bone | `ZFA:0000496` | — |  |
| `ZFA:0001521` | ceratobranchial 5 cartilage | `ZFA:0000496` | — |  |
| `ZFA:0000488` | ceratobranchial bone | `ZFA:0000496` | — |  |
| `ZFA:0001516` | ceratobranchial cartilage | `ZFA:0000496` | — |  |
| `ZFA:0000578` | ceratohyal bone | `ZFA:0000496` | — |  |
| `ZFA:0001400` | ceratohyal cartilage | `ZFA:0000496` | — |  |
| `ZFA:0001693` | chondral bone | `ZFA:0000496` | — | yes |
| `ZFA:0001461` | chondrocranium cartilage | `ZFA:0000496` | — |  |
| `ZFA:0001592` | claustrum bone | `ZFA:0001491` | — | yes |
| `ZFA:0000637` | claustrum cartilage | `ZFA:0000496` | — |  |
| `ZFA:0000184` | cleithrum | `ZFA:0000496` | — |  |
| `ZFA:0000496` | compound organ | `ZFA:0000496` | — | yes |
| `ZFA:0001220` | copula | `ZFA:0000496` | — |  |
| `ZFA:0001221` | copula 1 | `ZFA:0000496` | — | yes |
| `ZFA:0001222` | copula 2 | `ZFA:0000496` | — | yes |
| `ZFA:0000332` | coracoid | `ZFA:0000496` | — |  |
| `ZFA:0001274` | coronomeckelian | `ZFA:0000496` | — |  |
| `ZFA:0001458` | cranial cartilage | `ZFA:0000496` | — |  |
| `ZFA:0000191` | dentary | `ZFA:0000496` | — |  |
| `ZFA:0001590` | dermal bone | `ZFA:0000496` | — | yes |
| `ZFA:0000052` | dorsal actinotrichium | `ZFA:0000496` | — | yes |
| `ZFA:0000936` | dorsal fin distal radial | `ZFA:0000496` | — |  |
| `ZFA:0005372` | dorsal fin distal radial 1 | `ZFA:0000496` | — | yes |
| `ZFA:0005373` | dorsal fin distal radial 2 | `ZFA:0000496` | — | yes |
| `ZFA:0005374` | dorsal fin distal radial 3 | `ZFA:0000496` | — | yes |
| `ZFA:0005375` | dorsal fin distal radial 4 | `ZFA:0000496` | — | yes |
| `ZFA:0005376` | dorsal fin distal radial 5 | `ZFA:0000496` | — | yes |
| `ZFA:0005377` | dorsal fin distal radial 6 | `ZFA:0000496` | — | yes |
| `ZFA:0005378` | dorsal fin distal radial 7 | `ZFA:0000496` | — | yes |
| `ZFA:0005379` | dorsal fin distal radial 8 | `ZFA:0000496` | — | yes |
| `ZFA:0001418` | dorsal fin lepidotrichium | `ZFA:0000496` | — |  |
| `ZFA:0005355` | dorsal fin lepidotrichium 1 | `ZFA:0000496` | — | yes |
| `ZFA:0005356` | dorsal fin lepidotrichium 2 | `ZFA:0000496` | — | yes |
| `ZFA:0005357` | dorsal fin lepidotrichium 3 | `ZFA:0000496` | — | yes |
| `ZFA:0005358` | dorsal fin lepidotrichium 4 | `ZFA:0000496` | — | yes |
| `ZFA:0005359` | dorsal fin lepidotrichium 5 | `ZFA:0000496` | — | yes |
| `ZFA:0005360` | dorsal fin lepidotrichium 6 | `ZFA:0000496` | — | yes |
| `ZFA:0005361` | dorsal fin lepidotrichium 7 | `ZFA:0000496` | — | yes |
| `ZFA:0000947` | dorsal fin proximal radial | `ZFA:0000496` | — |  |
| `ZFA:0005362` | dorsal fin proximal radial 1 | `ZFA:0000496` | — | yes |
| `ZFA:0005363` | dorsal fin proximal radial 2 | `ZFA:0000496` | — | yes |
| `ZFA:0005380` | dorsal fin proximal radial 3 | `ZFA:0000496` | — | yes |
| `ZFA:0005381` | dorsal fin proximal radial 4 | `ZFA:0000496` | — | yes |
| `ZFA:0005382` | dorsal fin proximal radial 5 | `ZFA:0000496` | — | yes |
| `ZFA:0005383` | dorsal fin proximal radial 6 | `ZFA:0000496` | — | yes |
| `ZFA:0005384` | dorsal fin proximal radial 7 | `ZFA:0000496` | — | yes |
| `ZFA:0005385` | dorsal fin proximal radial 8 | `ZFA:0000496` | — | yes |
| `ZFA:0001647` | dorsal fin radial | `ZFA:0000496` | — | yes |
| `ZFA:0000196` | dorsal hypohyal bone | `ZFA:0000496` | — | yes |
| `ZFA:0000656` | ectopterygoid | `ZFA:0000496` | — |  |
| `ZFA:0001591` | endochondral bone | `ZFA:0000496` | — | yes |
| `ZFA:0005620` | endochondral element | `ZFA:0000496` | — | yes |
| `ZFA:0000657` | entopterygoid | `ZFA:0000496` | — |  |
| `ZFA:0001243` | epibranchial 1 bone | `ZFA:0000496` | — |  |
| `ZFA:0001528` | epibranchial 1 cartilage | `ZFA:0000496` | — |  |
| `ZFA:0001246` | epibranchial 2 bone | `ZFA:0000496` | — |  |
| `ZFA:0001530` | epibranchial 2 cartilage | `ZFA:0000496` | — |  |
| `ZFA:0001247` | epibranchial 3 bone | `ZFA:0000496` | — |  |
| `ZFA:0001529` | epibranchial 3 cartilage | `ZFA:0000496` | — |  |
| `ZFA:0001245` | epibranchial 4 bone | `ZFA:0000496` | — |  |
| `ZFA:0001531` | epibranchial 4 cartilage | `ZFA:0000496` | — |  |
| `ZFA:0001244` | epibranchial 5 | `ZFA:0000496` | — |  |
| `ZFA:0000658` | epibranchial bone | `ZFA:0000496` | — |  |
| `ZFA:0001527` | epibranchial cartilage | `ZFA:0000496` | — |  |
| `ZFA:0001382` | epibranchial uncinate process | `ZFA:0000496` | — |  |
| `ZFA:0000627` | epihyal | `ZFA:0000496` | — |  |
| `ZFA:0000507` | epineural | `ZFA:0000496` | — | yes |
| `ZFA:0001412` | epiotic | `ZFA:0000496` | — |  |
| `ZFA:0001502` | epiphyseal bar | `ZFA:0000496` | — |  |
| `ZFA:0000350` | epipleural | `ZFA:0000496` | — | yes |
| `ZFA:0000660` | epural | `ZFA:0000496` | — |  |
| `ZFA:0001405` | ethmoid cartilage | `ZFA:0000496` | — |  |
| `ZFA:0000661` | exoccipital | `ZFA:0000496` | — |  |
| `ZFA:0001597` | exoccipital posteroventral region | `ZFA:0000496` | — |  |
| `ZFA:0000663` | extrascapula | `ZFA:0000496` | — |  |
| `ZFA:0000107` | eye | `ZFA:0001490` | — |  |
| `ZFA:0000089` | fin fold actinotrichium | `ZFA:0000496` | — | yes |
| `ZFA:0000514` | frontal bone | `ZFA:0000496` | — |  |
| `ZFA:0000208` | gall bladder | `ZFA:0000496` | — |  |
| `ZFA:0000354` | gill | `ZFA:0000496` | — |  |
| `ZFA:0000356` | gill raker | `ZFA:0000496` | — |  |
| `ZFA:0005390` | gill ray | `ZFA:0000496` | — |  |
| `ZFA:0000413` | gonad | `ZFA:0001490` | — |  |
| `ZFA:0000669` | head kidney | `ZFA:0000496` | — |  |
| `ZFA:0000114` | heart | `ZFA:0001490` | — |  |
| `ZFA:0000360` | heart tube | `ZFA:0001490` | — |  |
| `ZFA:0000519` | hemal arch | `ZFA:0000496` | — | yes |
| `ZFA:0000735` | hemal postzygapophysis | `ZFA:0000496` | — | yes |
| `ZFA:0007005` | hemal prezygapophysis | `ZFA:0000496` | — | yes |
| `ZFA:0001364` | hemal spine | `ZFA:0000496` | — | yes |
| `ZFA:0000672` | hyomandibula | `ZFA:0000496` | — |  |
| `ZFA:0001422` | hyosymplectic cartilage | `ZFA:0000496` | — |  |
| `ZFA:0001233` | hypobranchial 1 bone | `ZFA:0000496` | — |  |
| `ZFA:0001524` | hypobranchial 1 cartilage | `ZFA:0000496` | — |  |
| `ZFA:0001236` | hypobranchial 2 bone | `ZFA:0000496` | — |  |
| `ZFA:0001525` | hypobranchial 2 cartilage | `ZFA:0000496` | — |  |
| `ZFA:0001235` | hypobranchial 3 bone | `ZFA:0000496` | — |  |
| `ZFA:0001526` | hypobranchial 3 cartilage | `ZFA:0000496` | — |  |
| `ZFA:0001234` | hypobranchial 4 bone | `ZFA:0000496` | — |  |
| `ZFA:0001523` | hypobranchial 4 cartilage | `ZFA:0000496` | — |  |
| `ZFA:0000363` | hypobranchial bone | `ZFA:0000496` | — |  |
| `ZFA:0001522` | hypobranchial cartilage | `ZFA:0000496` | — |  |
| `ZFA:0001381` | hypohyal bone | `ZFA:0000496` | — |  |
| `ZFA:0000118` | hypophysis | `ZFA:0000496` | — |  |
| `ZFA:0000364` | hypural | `ZFA:0000496` | — |  |
| `ZFA:0001560` | hypural 1 | `ZFA:0000496` | — | yes |
| `ZFA:0001561` | hypural 2 | `ZFA:0000496` | — | yes |
| `ZFA:0001562` | hypural 3 | `ZFA:0000496` | — | yes |
| `ZFA:0001563` | hypural 4 | `ZFA:0000496` | — | yes |
| `ZFA:0001564` | hypural 5 | `ZFA:0000496` | — | yes |
| `ZFA:0001028` | hypurapophysis | `ZFA:0000496` | — | yes |
| `ZFA:0000376` | infraorbital | `ZFA:0000496` | — |  |
| `ZFA:0000223` | infraorbital 1 | `ZFA:0000496` | — | yes |
| `ZFA:0001407` | infraorbital 2 | `ZFA:0000496` | — | yes |
| `ZFA:0001408` | infraorbital 3 | `ZFA:0000496` | — | yes |
| `ZFA:0001409` | infraorbital 4 | `ZFA:0000496` | — | yes |
| `ZFA:0000495` | infraorbital 5 | `ZFA:0000496` | — | yes |
| `ZFA:0000474` | intercalar | `ZFA:0000496` | — |  |
| `ZFA:0000525` | intercalarium | `ZFA:0000496` | — |  |
| `ZFA:0001603` | intercalarium articulating process | `ZFA:0000496` | — |  |
| `ZFA:0001602` | intercalarium ascending process | `ZFA:0000496` | — |  |
| `ZFA:0001511` | interhyal cartilage | `ZFA:0000496` | — |  |
| `ZFA:0000526` | intermuscular bone | `ZFA:0000496` | — |  |
| `ZFA:0000674` | interopercle | `ZFA:0000496` | — |  |
| `ZFA:0001338` | intestine | `ZFA:0001490` | — |  |
| `ZFA:0001635` | intramembranous bone | `ZFA:0000496` | — | yes |
| `ZFA:0005568` | iris blood vessels | `ZFA:0001490` | — |  |
| `ZFA:0000529` | kidney | `ZFA:0001490` | — |  |
| `ZFA:0001406` | kinethmoid bone | `ZFA:0000496` | — |  |
| `ZFA:0000585` | kinethmoid cartilage | `ZFA:0000496` | — | yes |
| `ZFA:0001503` | lamina orbitonasalis | `ZFA:0000496` | — |  |
| `ZFA:0005888` | lateral basicapsular commissure | `ZFA:0000496` | — |  |
| `ZFA:0000226` | lateral ethmoid | `ZFA:0000496` | — |  |
| `ZFA:0001554` | lepidotrichium | `ZFA:0000496` | — | yes |
| `ZFA:0005633` | lepidotrichium segment | `ZFA:0000496` | — | yes |
| `ZFA:0000123` | liver | `ZFA:0001491` | endoderm |  |
| `ZFA:0001601` | manubrium | `ZFA:0000496` | — |  |
| `ZFA:0000270` | maxilla | `ZFA:0000496` | — |  |
| `ZFA:0001205` | Meckel's cartilage | `ZFA:0000496` | — |  |
| `ZFA:0001535` | median fin cartilage | `ZFA:0000496` | — | yes |
| `ZFA:0001636` | membrane bone | `ZFA:0000496` | — | yes |
| `ZFA:0000323` | mesethmoid bone | `ZFA:0000496` | — |  |
| `ZFA:0000239` | mesocoracoid bone | `ZFA:0000496` | — |  |
| `ZFA:0001537` | mesocoracoid cartilage | `ZFA:0000496` | — | yes |
| `ZFA:0000240` | metapterygoid | `ZFA:0000496` | — |  |
| `ZFA:0000365` | nasal bone | `ZFA:0000496` | — |  |
| `ZFA:0001066` | neural arch | `ZFA:0000496` | — |  |
| `ZFA:0001394` | neural arch 3 | `ZFA:0000496` | — | yes |
| `ZFA:0001395` | neural arch 4 | `ZFA:0000496` | — | yes |
| `ZFA:0000681` | neural postzygapophysis | `ZFA:0000496` | — |  |
| `ZFA:0001325` | neural prezygapophysis | `ZFA:0000496` | — |  |
| `ZFA:0001336` | neural spine | `ZFA:0000496` | — |  |
| `ZFA:0001600` | neural spine 4 | `ZFA:0000496` | — | yes |
| `ZFA:0001321` | neurocranial trabecula | `ZFA:0000496` | — |  |
| `ZFA:0001582` | non-Weberian precaudal vertebra | `ZFA:0000496` | — | yes |
| `ZFA:0001631` | notochordal ossification | `ZFA:0000496` | — | yes |
| `ZFA:0001504` | occipital arch cartilage | `ZFA:0000496` | — |  |
| `ZFA:0000250` | opercle | `ZFA:0000496` | — |  |
| `ZFA:0005961` | opisthural cartilage | `ZFA:0000496` | — |  |
| `ZFA:0000253` | orbitosphenoid | `ZFA:0000496` | — |  |
| `ZFA:0001171` | os suspensorium | `ZFA:0000496` | — |  |
| `ZFA:0001599` | os suspensorium medial flange | `ZFA:0000496` | — |  |
| `ZFA:0000559` | otolith organ | `ZFA:0001490` | — |  |
| `ZFA:0000403` | ovary | `ZFA:0001490` | — |  |
| `ZFA:0001543` | paired fin cartilage | `ZFA:0000496` | — |  |
| `ZFA:0001399` | palatoquadrate cartilage | `ZFA:0000496` | — |  |
| `ZFA:0000140` | pancreas | `ZFA:0000496` | — |  |
| `ZFA:0001423` | parachordal cartilage | `ZFA:0000496` | — |  |
| `ZFA:0001360` | parapineal organ | `ZFA:0000496` | — |  |
| `ZFA:0001362` | parapophysis | `ZFA:0000496` | — | yes |
| `ZFA:0001392` | parapophysis 1 | `ZFA:0000496` | — | yes |
| `ZFA:0001393` | parapophysis 2 | `ZFA:0000496` | — | yes |
| `ZFA:0001396` | parapophysis/rib | `ZFA:0000496` | — | yes |
| `ZFA:0000561` | parasphenoid | `ZFA:0000496` | — |  |
| `ZFA:0000438` | parhypural | `ZFA:0000496` | — | yes |
| `ZFA:0000486` | parietal bone | `ZFA:0000496` | — |  |
| `ZFA:0005545` | pectoral fin actinotrichium | `ZFA:0000496` | — |  |
| `ZFA:0000257` | pectoral fin cartilage | `ZFA:0000496` | — |  |
| `ZFA:0001588` | pectoral fin distal radial | `ZFA:0000496` | — | yes |
| `ZFA:0001456` | pectoral fin endoskeletal disc | `ZFA:0000496` | — | yes |
| `ZFA:0001551` | pectoral fin lepidotrichium | `ZFA:0000496` | — |  |
| `ZFA:0005547` | pectoral fin lepidotrichium 1 | `ZFA:0000496` | — | yes |
| `ZFA:0005548` | pectoral fin lepidotrichium 2 | `ZFA:0000496` | — | yes |
| `ZFA:0005549` | pectoral fin lepidotrichium 3 | `ZFA:0000496` | — | yes |
| `ZFA:0005553` | pectoral fin lepidotrichium 4 | `ZFA:0000496` | — | yes |
| `ZFA:0005552` | pectoral fin lepidotrichium 5 | `ZFA:0000496` | — | yes |
| `ZFA:0005550` | pectoral fin lepidotrichium 6 | `ZFA:0000496` | — | yes |
| `ZFA:0005551` | pectoral fin lepidotrichium 7 | `ZFA:0000496` | — | yes |
| `ZFA:0001587` | pectoral fin proximal radial | `ZFA:0000496` | — | yes |
| `ZFA:0001586` | pectoral fin radial | `ZFA:0000496` | — |  |
| `ZFA:0005546` | pelvic fin actinotrichium | `ZFA:0000496` | — |  |
| `ZFA:0001459` | pelvic fin cartilage | `ZFA:0000496` | — |  |
| `ZFA:0001552` | pelvic fin lepidotrichium | `ZFA:0000496` | — |  |
| `ZFA:0005554` | pelvic fin lepidotrichium 1 | `ZFA:0000496` | — | yes |
| `ZFA:0005555` | pelvic fin lepidotrichium 2 | `ZFA:0000496` | — | yes |
| `ZFA:0005557` | pelvic fin lepidotrichium 3 | `ZFA:0000496` | — | yes |
| `ZFA:0005556` | pelvic fin lepidotrichium 4 | `ZFA:0000496` | — | yes |
| `ZFA:0000508` | pelvic radial | `ZFA:0000496` | — |  |
| `ZFA:0001417` | pelvic radial 1 | `ZFA:0000496` | — | yes |
| `ZFA:0001542` | pelvic radial 1 cartilage | `ZFA:0000496` | — | yes |
| `ZFA:0001415` | pelvic radial 2 | `ZFA:0000496` | — | yes |
| `ZFA:0001541` | pelvic radial 2 cartilage | `ZFA:0000496` | — | yes |
| `ZFA:0001416` | pelvic radial 3 | `ZFA:0000496` | — | yes |
| `ZFA:0001540` | pelvic radial 3 cartilage | `ZFA:0000496` | — | yes |
| `ZFA:0001538` | pelvic radial cartilage | `ZFA:0000496` | — | yes |
| `ZFA:0001630` | perichondral bone | `ZFA:0000496` | — | yes |
| `ZFA:0001629` | perichordal bone | `ZFA:0000496` | — | yes |
| `ZFA:0000047` | peripheral olfactory organ | `ZFA:0001490` | — |  |
| `ZFA:0001460` | pharyngeal arch cartilage | `ZFA:0000496` | — |  |
| `ZFA:0001250` | pharyngobranchial 2 bone | `ZFA:0000496` | — |  |
| `ZFA:0001536` | pharyngobranchial 2 cartilage | `ZFA:0000496` | — |  |
| `ZFA:0001252` | pharyngobranchial 3 bone | `ZFA:0000496` | — |  |
| `ZFA:0001534` | pharyngobranchial 3 cartilage | `ZFA:0000496` | — |  |
| `ZFA:0001251` | pharyngobranchial 4 cartilage | `ZFA:0000496` | — |  |
| `ZFA:0000527` | pharyngobranchial bone | `ZFA:0000496` | — |  |
| `ZFA:0001533` | pharyngobranchial cartilage | `ZFA:0000496` | — | yes |
| `ZFA:0001397` | post-Weberian supraneural | `ZFA:0000496` | — | yes |
| `ZFA:0000410` | postcleithrum | `ZFA:0000496` | — |  |
| `ZFA:0001457` | postcranial axial cartilage | `ZFA:0000496` | — |  |
| `ZFA:0005887` | posterior basicapsular commissure | `ZFA:0000496` | — |  |
| `ZFA:0001293` | posterior kidney | `ZFA:0000496` | — |  |
| `ZFA:0001433` | posterior sclerotic bone | `ZFA:0000496` | — | yes |
| `ZFA:0000549` | posttemporal | `ZFA:0000496` | — |  |
| `ZFA:0000263` | precaudal vertebra | `ZFA:0000496` | — | yes |
| `ZFA:0001404` | preethmoid bone | `ZFA:0000496` | — |  |
| `ZFA:0000567` | premaxilla | `ZFA:0000496` | — |  |
| `ZFA:0001577` | premaxilla ascending process | `ZFA:0000496` | — |  |
| `ZFA:0000264` | preopercle | `ZFA:0000496` | — |  |
| `ZFA:0001594` | preopercle horizontal limb | `ZFA:0000496` | — |  |
| `ZFA:0001595` | preopercle vertical limb | `ZFA:0000496` | — |  |
| `ZFA:0000557` | preural 1 vertebra | `ZFA:0000496` | — | yes |
| `ZFA:0000586` | preural 2 vertebra | `ZFA:0000496` | — | yes |
| `ZFA:0001583` | preural centrum 1+ ural centrum 1 | `ZFA:0000496` | — |  |
| `ZFA:0000734` | preural vertebra | `ZFA:0000496` | — |  |
| `ZFA:0000308` | prevomer | `ZFA:0000496` | — |  |
| `ZFA:0000151` | pronephros | `ZFA:0001490` | — |  |
| `ZFA:0000575` | prootic | `ZFA:0000496` | — |  |
| `ZFA:0001589` | propterygium | `ZFA:0000496` | — | yes |
| `ZFA:0000419` | pterosphenoid | `ZFA:0000496` | — |  |
| `ZFA:0000576` | pterotic | `ZFA:0000496` | — |  |
| `ZFA:0000621` | quadrate | `ZFA:0000496` | — |  |
| `ZFA:0001593` | quadrate ventral process | `ZFA:0000496` | — |  |
| `ZFA:0000271` | radial | `ZFA:0000496` | — | yes |
| `ZFA:0001628` | replacement bone | `ZFA:0000496` | — | yes |
| `ZFA:0005624` | replacement element | `ZFA:0000496` | — | yes |
| `ZFA:0000422` | retroarticular | `ZFA:0000496` | — |  |
| `ZFA:0000538` | rib | `ZFA:0000496` | — | yes |
| `ZFA:0005538` | rib of vertebra 1 | `ZFA:0000496` | — | yes |
| `ZFA:0005539` | rib of vertebra 2 | `ZFA:0000496` | — | yes |
| `ZFA:0005540` | rib of vertebra 3 | `ZFA:0000496` | — | yes |
| `ZFA:0005541` | rib of vertebra 4 | `ZFA:0000496` | — | yes |
| `ZFA:0005542` | rib of vertebra 5 | `ZFA:0000496` | — | yes |
| `ZFA:0005543` | rib of vertebra 6 | `ZFA:0000496` | — | yes |
| `ZFA:0001172` | roofing cartilage | `ZFA:0000496` | — |  |
| `ZFA:0001641` | rudimentary neural arch | `ZFA:0000496` | — |  |
| `ZFA:0000429` | scaphium | `ZFA:0000496` | — |  |
| `ZFA:0000583` | scapula | `ZFA:0000496` | — |  |
| `ZFA:0001455` | scapulocoracoid | `ZFA:0000496` | — |  |
| `ZFA:0001411` | sclerotic bone | `ZFA:0000496` | — |  |
| `ZFA:0001509` | sclerotic cartilage | `ZFA:0000496` | — | yes |
| `ZFA:0005511` | sensory canal tubular ossicle | `ZFA:0000496` | — | yes |
| `ZFA:0001492` | simple organ | `ZFA:0001492` | — | yes |
| `ZFA:0005494` | skeletal element | `ZFA:0000496` | — |  |
| `ZFA:0001491` | solid compound organ | `ZFA:0001491` | — | yes |
| `ZFA:0000859` | specialized hemal arch and spine | `ZFA:0000496` | — |  |
| `ZFA:0000587` | sphenotic | `ZFA:0000496` | — |  |
| `ZFA:0000075` | spinal cord | `ZFA:0001490` | — |  |
| `ZFA:0000436` | spleen | `ZFA:0000496` | — |  |
| `ZFA:0000284` | subopercle | `ZFA:0000496` | — |  |
| `ZFA:0000594` | supracleithrum | `ZFA:0000496` | — |  |
| `ZFA:0001335` | supradorsal | `ZFA:0000496` | — |  |
| `ZFA:0001403` | supraethmoid | `ZFA:0000496` | — |  |
| `ZFA:0000442` | supraneural | `ZFA:0000496` | — |  |
| `ZFA:0005602` | supraneural 10 | `ZFA:0000496` | — | yes |
| `ZFA:0001191` | supraneural 2 | `ZFA:0000496` | — |  |
| `ZFA:0001192` | supraneural 3 | `ZFA:0000496` | — |  |
| `ZFA:0001165` | supraneural 5 | `ZFA:0000496` | — | yes |
| `ZFA:0001164` | supraneural 6 | `ZFA:0000496` | — | yes |
| `ZFA:0001163` | supraneural 7 | `ZFA:0000496` | — | yes |
| `ZFA:0001193` | supraneural 8 | `ZFA:0000496` | — | yes |
| `ZFA:0001166` | supraneural 9 | `ZFA:0000496` | — | yes |
| `ZFA:0000595` | supraoccipital | `ZFA:0000496` | — |  |
| `ZFA:0000691` | supraorbital bone | `ZFA:0000496` | — |  |
| `ZFA:0000076` | swim bladder | `ZFA:0001490` | endoderm | yes |
| `ZFA:0000692` | symplectic | `ZFA:0000496` | — |  |
| `ZFA:0001505` | taenia marginalis anterior | `ZFA:0000496` | — |  |
| `ZFA:0001515` | taenia marginalis posterior | `ZFA:0000496` | — |  |
| `ZFA:0001506` | tectum synoticum | `ZFA:0000496` | — |  |
| `ZFA:0000598` | testis | `ZFA:0001490` | — |  |
| `ZFA:0001078` | thymus | `ZFA:0000496` | — |  |
| `ZFA:0001508` | trabecula communis | `ZFA:0000496` | — |  |
| `ZFA:0001507` | trabecula cranii | `ZFA:0000496` | — |  |
| `ZFA:0000698` | tripus | `ZFA:0000496` | — |  |
| `ZFA:0001581` | ural centrum 2 | `ZFA:0000496` | — |  |
| `ZFA:0005959` | ural vertebra | `ZFA:0000496` | — |  |
| `ZFA:0001579` | ural vertebra 2 | `ZFA:0000496` | — |  |
| `ZFA:0000452` | urohyal | `ZFA:0000496` | — |  |
| `ZFA:0000602` | uroneural | `ZFA:0000496` | — |  |
| `ZFA:0000158` | urostyle | `ZFA:0000496` | — |  |
| `ZFA:0000078` | ventral actinotrichium | `ZFA:0000496` | — | yes |
| `ZFA:0000300` | ventral hypohyal bone | `ZFA:0000496` | — | yes |
| `ZFA:0001189` | vertebra | `ZFA:0000496` | — |  |
| `ZFA:0001167` | vertebra 1 | `ZFA:0000496` | — | yes |
| `ZFA:0005353` | vertebra 10 | `ZFA:0000496` | — | yes |
| `ZFA:0005354` | vertebra 11 | `ZFA:0000496` | — | yes |
| `ZFA:0005352` | vertebra 12 | `ZFA:0000496` | — | yes |
| `ZFA:0007096` | vertebra 13 | `ZFA:0000496` | — | yes |
| `ZFA:0007097` | vertebra 14 | `ZFA:0000496` | — | yes |
| `ZFA:0007098` | vertebra 15 | `ZFA:0000496` | — | yes |
| `ZFA:0007099` | vertebra 16 | `ZFA:0000496` | — | yes |
| `ZFA:0007100` | vertebra 17 | `ZFA:0000496` | — | yes |
| `ZFA:0007101` | vertebra 18 | `ZFA:0000496` | — | yes |
| `ZFA:0007102` | vertebra 19 | `ZFA:0000496` | — | yes |
| `ZFA:0001168` | vertebra 2 | `ZFA:0000496` | — | yes |
| `ZFA:0007103` | vertebra 20 | `ZFA:0000496` | — | yes |
| `ZFA:0007104` | vertebra 21 | `ZFA:0000496` | — | yes |
| `ZFA:0007105` | vertebra 22 | `ZFA:0000496` | — | yes |
| `ZFA:0007106` | vertebra 23 | `ZFA:0000496` | — | yes |
| `ZFA:0007107` | vertebra 24 | `ZFA:0000496` | — | yes |
| `ZFA:0007108` | vertebra 25 | `ZFA:0000496` | — | yes |
| `ZFA:0007109` | vertebra 26 | `ZFA:0000496` | — | yes |
| `ZFA:0007110` | vertebra 27 | `ZFA:0000496` | — | yes |
| `ZFA:0007111` | vertebra 28 | `ZFA:0000496` | — | yes |
| `ZFA:0007112` | vertebra 29 | `ZFA:0000496` | — | yes |
| `ZFA:0001169` | vertebra 3 | `ZFA:0000496` | — | yes |
| `ZFA:0007113` | vertebra 30 | `ZFA:0000496` | — | yes |
| `ZFA:0001170` | vertebra 4 | `ZFA:0000496` | — | yes |
| `ZFA:0005347` | vertebra 5 | `ZFA:0000496` | — | yes |
| `ZFA:0005348` | vertebra 6 | `ZFA:0000496` | — | yes |
| `ZFA:0005349` | vertebra 7 | `ZFA:0000496` | — | yes |
| `ZFA:0005350` | vertebra 8 | `ZFA:0000496` | — | yes |
| `ZFA:0005351` | vertebra 9 | `ZFA:0000496` | — | yes |
| `ZFA:0000461` | Weberian ossicle | `ZFA:0001491` | — |  |
| `ZFA:0001190` | Weberian vertebra | `ZFA:0000496` | — |  |

### `multi_tissue_structure` (645)

| Id | Name | Source class | explicit_germ_layer | Stranded |
| --- | --- | --- | --- | --- |
| `ZFA:0007077` | accessory chamber of the maxillary blood sinus | `ZFA:0001488` | — | yes |
| `ZFA:0000714` | accessory pretectal nucleus | `ZFA:0001488` | — |  |
| `ZFA:0001282` | adenohypophysis | `ZFA:0001488` | — |  |
| `ZFA:0000716` | afferent branchial artery | `ZFA:0001488` | — |  |
| `ZFA:0005012` | afferent filamental artery | `ZFA:0001488` | — |  |
| `ZFA:0005307` | afferent glomerular arteriole | `ZFA:0001488` | — |  |
| `ZFA:0005015` | afferent lamellar arteriole | `ZFA:0001488` | — |  |
| `ZFA:0000618` | ansulate commissure | `ZFA:0001488` | — | yes |
| `ZFA:0000423` | anterior cardinal vein | `ZFA:0001488` | — | yes |
| `ZFA:0005342` | anterior catecholaminergic tract | `ZFA:0001488` | — | yes |
| `ZFA:0001067` | anterior cerebral vein | `ZFA:0001488` | — | yes |
| `ZFA:0001277` | anterior chamber swim bladder | `ZFA:0001488` | endoderm | yes |
| `ZFA:0001108` | anterior commissure | `ZFA:0001488` | — | yes |
| `ZFA:0005052` | anterior mesencephalic central artery | `ZFA:0001488` | — | yes |
| `ZFA:0005080` | anterior mesenteric artery | `ZFA:0001488` | — | yes |
| `ZFA:0005683` | anteromedial  zone olfactory bulb | `ZFA:0001488` | — |  |
| `ZFA:0005004` | aortic arch | `ZFA:0001488` | — | yes |
| `ZFA:0005005` | aortic arch 1 | `ZFA:0001488` | — | yes |
| `ZFA:0005006` | aortic arch 2 | `ZFA:0001488` | — | yes |
| `ZFA:0005007` | aortic arch 3 | `ZFA:0001488` | — | yes |
| `ZFA:0005008` | aortic arch 4 | `ZFA:0001488` | — | yes |
| `ZFA:0005009` | aortic arch 5 | `ZFA:0001488` | — | yes |
| `ZFA:0005016` | aortic arch 6 | `ZFA:0001488` | — | yes |
| `ZFA:0005255` | arteriole | `ZFA:0001488` | — | yes |
| `ZFA:0000005` | artery | `ZFA:0001488` | — | yes |
| `ZFA:0001315` | atrioventricular canal | `ZFA:0001488` | — |  |
| `ZFA:0005064` | atrioventricular valve | `ZFA:0001488` | — |  |
| `ZFA:0005295` | axial blood vessel | `ZFA:0001488` | — | yes |
| `ZFA:0005296` | axial lymph vessel | `ZFA:0001488` | — |  |
| `ZFA:0001073` | axial vasculature | `ZFA:0001488` | — | yes |
| `ZFA:0005000` | basal communicating artery | `ZFA:0001488` | — | yes |
| `ZFA:0005002` | basilar artery | `ZFA:0001488` | — | yes |
| `ZFA:0005164` | bile ductule | `ZFA:0001488` | — |  |
| `ZFA:0007072` | blood sinus | `ZFA:0001488` | — |  |
| `ZFA:0005314` | blood vessel | `ZFA:0001488` | — | yes |
| `ZFA:0000099` | brain vasculature | `ZFA:0001488` | — |  |
| `ZFA:0001707` | brainstem | `ZFA:0001488` | — |  |
| `ZFA:0000318` | brainstem and spinal white matter | `ZFA:0001488` | — |  |
| `ZFA:0000626` | bulbo-spinal tract | `ZFA:0001488` | — | yes |
| `ZFA:0000173` | bulbus arteriosus | `ZFA:0001488` | — |  |
| `ZFA:0005068` | bulbus arteriosus inner layer | `ZFA:0001488` | — |  |
| `ZFA:0005950` | bulbus arteriosus lymph vessel | `ZFA:0001488` | — |  |
| `ZFA:0005067` | bulbus arteriosus middle layer | `ZFA:0001488` | — |  |
| `ZFA:0005951` | cardiac ventricle lymph vessel | `ZFA:0001488` | — |  |
| `ZFA:0000097` | carotid artery | `ZFA:0001488` | — | yes |
| `ZFA:0000011` | caudal artery | `ZFA:0001488` | — | yes |
| `ZFA:0000320` | caudal commissure | `ZFA:0001488` | — |  |
| `ZFA:0001051` | caudal division of the internal carotid artery | `ZFA:0001488` | — | yes |
| `ZFA:0005304` | caudal fin blood vessel | `ZFA:0001488` | — | yes |
| `ZFA:0005303` | caudal fin lymph vessel | `ZFA:0001488` | — |  |
| `ZFA:0005097` | caudal fin vasculature | `ZFA:0001488` | — | yes |
| `ZFA:0000634` | caudal hypothalamic zone | `ZFA:0001488` | — |  |
| `ZFA:0000479` | caudal mesencephalo-cerebellar tract | `ZFA:0001488` | — |  |
| `ZFA:0000630` | caudal parvocellular preoptic nucleus | `ZFA:0001488` | — |  |
| `ZFA:0000324` | caudal periventricular hypothalamus | `ZFA:0001488` | — |  |
| `ZFA:0000481` | caudal preglomerular nucleus | `ZFA:0001488` | — | yes |
| `ZFA:0000631` | caudal pretectal nucleus | `ZFA:0001488` | — |  |
| `ZFA:0000325` | caudal thalamic nucleus | `ZFA:0001488` | — |  |
| `ZFA:0000482` | caudal tuberal nucleus | `ZFA:0001488` | — |  |
| `ZFA:0000633` | caudal tuberculum | `ZFA:0001488` | — |  |
| `ZFA:0000180` | caudal vein | `ZFA:0001488` | — | yes |
| `ZFA:0001286` | caudal vein plexus | `ZFA:0001488` | — | yes |
| `ZFA:0000484` | celiacomesenteric artery | `ZFA:0001488` | — | yes |
| `ZFA:0005020` | central artery | `ZFA:0001488` | — |  |
| `ZFA:0000938` | central canal | `ZFA:0001488` | — |  |
| `ZFA:0000182` | central caudal thalamic nucleus | `ZFA:0001488` | — |  |
| `ZFA:0007076` | central chamber of the maxillary blood sinus | `ZFA:0001488` | — | yes |
| `ZFA:0000485` | central nucleus inferior lobe | `ZFA:0001488` | — |  |
| `ZFA:0000635` | central pretectal nucleus | `ZFA:0001488` | — |  |
| `ZFA:0000183` | central pretectum | `ZFA:0001488` | — |  |
| `ZFA:0005098` | central ray artery | `ZFA:0001488` | — | yes |
| `ZFA:0005168` | central vein | `ZFA:0001488` | — |  |
| `ZFA:0000327` | central zone of the optic tectum | `ZFA:0001488` | — |  |
| `ZFA:0005673` | central zone olfactory bulb | `ZFA:0001488` | — |  |
| `ZFA:0005670` | central zone protoglomerulus | `ZFA:0001488` | — |  |
| `ZFA:0005721` | central zone protoglomerulus 1 | `ZFA:0001488` | — |  |
| `ZFA:0005722` | central zone protoglomerulus 2 | `ZFA:0001488` | — |  |
| `ZFA:0005723` | central zone protoglomerulus 3 | `ZFA:0001488` | — |  |
| `ZFA:0005724` | central zone protoglomerulus 4 | `ZFA:0001488` | — |  |
| `ZFA:0005725` | central zone protoglomerulus 5 | `ZFA:0001488` | — |  |
| `ZFA:0005851` | ceratobranchial 5 primary tooth | `ZFA:0001488` | — | yes |
| `ZFA:0005849` | ceratobranchial 5 replacement  tooth | `ZFA:0001488` | — | yes |
| `ZFA:0000694` | ceratobranchial 5 tooth | `ZFA:0001488` | — |  |
| `ZFA:0005021` | cerebellar central artery | `ZFA:0001488` | — | yes |
| `ZFA:0005869` | cerebellar plate | `ZFA:0001488` | — |  |
| `ZFA:0001708` | cerebellar white matter | `ZFA:0001488` | — |  |
| `ZFA:0000174` | cerebellovestibular tract | `ZFA:0001488` | — |  |
| `ZFA:0000100` | cerebellum | `ZFA:0001488` | — |  |
| `ZFA:0001443` | choroid plexus | `ZFA:0001488` | — |  |
| `ZFA:0001446` | choroid plexus fourth ventricle | `ZFA:0001488` | — |  |
| `ZFA:0001445` | choroid plexus tectal ventricle | `ZFA:0001488` | — |  |
| `ZFA:0001447` | choroid plexus telencephalic ventricle | `ZFA:0001488` | — |  |
| `ZFA:0001444` | choroid plexus third ventricle | `ZFA:0001488` | — |  |
| `ZFA:0005219` | choroid plexus vascular circuit | `ZFA:0001488` | — |  |
| `ZFA:0001203` | ciliary zone | `ZFA:0001488` | — |  |
| `ZFA:0005781` | cloaca | `ZFA:0001488` | — |  |
| `ZFA:0001438` | coelom | `ZFA:0001488` | — | yes |
| `ZFA:0005294` | collecting duct | `ZFA:0001488` | — | yes |
| `ZFA:0000490` | commissura cerebelli | `ZFA:0001488` | — | yes |
| `ZFA:0000638` | commissura rostral, pars dorsalis | `ZFA:0001488` | — | yes |
| `ZFA:0000185` | commissura rostral, pars ventralis | `ZFA:0001488` | — | yes |
| `ZFA:0000331` | commissure infima of Haller | `ZFA:0001488` | — | yes |
| `ZFA:0000491` | commissure of the caudal tuberculum | `ZFA:0001488` | — | yes |
| `ZFA:0000639` | commissure of the secondary gustatory nucleus | `ZFA:0001488` | — |  |
| `ZFA:0005877` | commissure of the tract of the commissure of the caudal tuberculum | `ZFA:0001488` | — | yes |
| `ZFA:0005165` | common bile duct | `ZFA:0001488` | — |  |
| `ZFA:0000186` | common cardinal vein | `ZFA:0001488` | — | yes |
| `ZFA:0005411` | common crus | `ZFA:0001488` | — |  |
| `ZFA:0005051` | communicating vessel palatocerebral artery | `ZFA:0001488` | — | yes |
| `ZFA:0001489` | compound organ component | `ZFA:0001488` | — | yes |
| `ZFA:0005013` | concurrent branch afferent branchial artery | `ZFA:0001488` | — |  |
| `ZFA:0000640` | cornea | `ZFA:0001488` | — |  |
| `ZFA:0005812` | coronary artery | `ZFA:0001488` | — |  |
| `ZFA:0005953` | coronary capillary plexus | `ZFA:0001488` | — | yes |
| `ZFA:0005814` | coronary vein | `ZFA:0001488` | — |  |
| `ZFA:0000188` | corpus cerebelli | `ZFA:0001488` | — |  |
| `ZFA:0000334` | corpus mamillare | `ZFA:0001488` | — |  |
| `ZFA:0005297` | cranial blood vessel | `ZFA:0001488` | — | yes |
| `ZFA:0001059` | cranial division of the internal carotid artery | `ZFA:0001488` | — | yes |
| `ZFA:0005298` | cranial lymph vessel | `ZFA:0001488` | — | yes |
| `ZFA:0001267` | cranial vasculature | `ZFA:0001488` | — | yes |
| `ZFA:0000335` | crossed tecto-bulbar tract | `ZFA:0001488` | — | yes |
| `ZFA:0005166` | cystic duct | `ZFA:0001488` | — |  |
| `ZFA:0000493` | decussation of medial funicular nucleus | `ZFA:0001488` | — |  |
| `ZFA:0000642` | decussation of the medial octavolateralis nucleus | `ZFA:0001488` | — |  |
| `ZFA:0005936` | deep subintestinal venous plexus | `ZFA:0001488` | — | yes |
| `ZFA:0000494` | deep white zone | `ZFA:0001488` | — |  |
| `ZFA:0005138` | dental organ | `ZFA:0001488` | — | yes |
| `ZFA:0001183` | dermal superficial region | `ZFA:0001488` | — | yes |
| `ZFA:0001119` | dermis | `ZFA:0001488` | — | yes |
| `ZFA:0005591` | developing mesonephric distal tubule | `ZFA:0001488` | — |  |
| `ZFA:0005585` | developing mesonephric proximal tubule | `ZFA:0001488` | — |  |
| `ZFA:0005932` | developmental vascular plexus | `ZFA:0001488` | — | yes |
| `ZFA:0005685` | dG1 | `ZFA:0001488` | — |  |
| `ZFA:0001659` | diencephalic nucleus | `ZFA:0001488` | — |  |
| `ZFA:0000338` | diencephalic white matter | `ZFA:0001488` | — |  |
| `ZFA:0000101` | diencephalon | `ZFA:0001488` | — |  |
| `ZFA:0000193` | diffuse nucleus inferior lobe | `ZFA:0001488` | — |  |
| `ZFA:0005162` | digestive system duct | `ZFA:0001488` | — |  |
| `ZFA:0007075` | distal bulb of the maxillary blood sinus | `ZFA:0001488` | — | yes |
| `ZFA:0005293` | distal early tubule | `ZFA:0001488` | — |  |
| `ZFA:0005292` | distal late tubule | `ZFA:0001488` | — |  |
| `ZFA:0005686` | dlG1 | `ZFA:0001488` | — |  |
| `ZFA:0005687` | dlG2 | `ZFA:0001488` | — |  |
| `ZFA:0005688` | dlG3 | `ZFA:0001488` | — |  |
| `ZFA:0005689` | dlG4 | `ZFA:0001488` | — |  |
| `ZFA:0005690` | dlG5 | `ZFA:0001488` | — |  |
| `ZFA:0000194` | dorsal accessory optic nucleus | `ZFA:0001488` | — |  |
| `ZFA:0000014` | dorsal aorta | `ZFA:0001488` | — | yes |
| `ZFA:0005082` | dorsal branch nasal ciliary artery | `ZFA:0001488` | — | yes |
| `ZFA:0000647` | dorsal caudal thalamic nucleus | `ZFA:0001488` | — |  |
| `ZFA:0005030` | dorsal ciliary vein | `ZFA:0001488` | — | yes |
| `ZFA:0000102` | dorsal fin fold | `ZFA:0001488` | — | yes |
| `ZFA:0000501` | dorsal funiculus | `ZFA:0001488` | — |  |
| `ZFA:0000649` | dorsal horn spinal cord | `ZFA:0001488` | — |  |
| `ZFA:0000347` | dorsal hypothalamic zone | `ZFA:0001488` | — |  |
| `ZFA:0005025` | dorsal longitudinal anastomotic vessel | `ZFA:0001488` | — | yes |
| `ZFA:0005266` | dorsal longitudinal fasciculus | `ZFA:0001488` | — | yes |
| `ZFA:0005320` | dorsal longitudinal lymphatic vessel | `ZFA:0001488` | — | yes |
| `ZFA:0005031` | dorsal longitudinal vein | `ZFA:0001488` | — |  |
| `ZFA:0000199` | dorsal periventricular hypothalamus | `ZFA:0001488` | — |  |
| `ZFA:0000505` | dorsal telencephalon | `ZFA:0001488` | — |  |
| `ZFA:0000653` | dorsal thalamus | `ZFA:0001488` | — |  |
| `ZFA:0005674` | dorsal zone olfactory bulb | `ZFA:0001488` | — |  |
| `ZFA:0005678` | dorsolateral zone olfactory bulb | `ZFA:0001488` | — |  |
| `ZFA:0000655` | dorsomedial optic tract | `ZFA:0001488` | — | yes |
| `ZFA:0001322` | dorsoventral diencephalic tract | `ZFA:0001488` | — | yes |
| `ZFA:0005171` | duct | `ZFA:0001488` | — | yes |
| `ZFA:0001437` | ductus communicans | `ZFA:0001488` | — | yes |
| `ZFA:0000202` | efferent branchial artery | `ZFA:0001488` | — |  |
| `ZFA:0005018` | efferent filamental artery | `ZFA:0001488` | — |  |
| `ZFA:0005308` | efferent glomerular arteriole | `ZFA:0001488` | — |  |
| `ZFA:0005019` | efferent lamellar arteriole | `ZFA:0001488` | — |  |
| `ZFA:0001260` | endocrine pancreas | `ZFA:0001488` | — |  |
| `ZFA:0005343` | endohypothalamic tract | `ZFA:0001488` | — | yes |
| `ZFA:0001705` | endolymphatic duct | `ZFA:0001488` | — |  |
| `ZFA:0000019` | epiphysis | `ZFA:0001488` | — |  |
| `ZFA:0000509` | epithalamus | `ZFA:0001488` | — |  |
| `ZFA:0000204` | esophagus | `ZFA:0001488` | endoderm |  |
| `ZFA:0001249` | exocrine pancreas | `ZFA:0001488` | endoderm |  |
| `ZFA:0005170` | extrahepatic duct | `ZFA:0001488` | — |  |
| `ZFA:0005346` | extrapancreatic duct | `ZFA:0001488` | — |  |
| `ZFA:0005831` | facial lymphatic network | `ZFA:0001488` | — | yes |
| `ZFA:0005108` | facial lymphatic vessel | `ZFA:0001488` | — | yes |
| `ZFA:0000353` | fasciculus retroflexus | `ZFA:0001488` | — | yes |
| `ZFA:0000666` | filamental artery | `ZFA:0001488` | — |  |
| `ZFA:0005299` | fin blood vessel | `ZFA:0001488` | — | yes |
| `ZFA:0005316` | fin fold pectoral fin bud | `ZFA:0001488` | — | yes |
| `ZFA:0005300` | fin lymph vessel | `ZFA:0001488` | — | yes |
| `ZFA:0005095` | fin vasculature | `ZFA:0001488` | — | yes |
| `ZFA:0000022` | floor plate | `ZFA:0001488` | — |  |
| `ZFA:0000871` | floor plate diencephalic region | `ZFA:0001488` | — |  |
| `ZFA:0001677` | floor plate midbrain region | `ZFA:0001488` | — |  |
| `ZFA:0000887` | floor plate neural rod | `ZFA:0001488` | — |  |
| `ZFA:0001434` | floor plate neural tube | `ZFA:0001488` | — |  |
| `ZFA:0000882` | floor plate rhombomere 1 | `ZFA:0001488` | — |  |
| `ZFA:0000763` | floor plate rhombomere 2 | `ZFA:0001488` | — |  |
| `ZFA:0000888` | floor plate rhombomere 3 | `ZFA:0001488` | — |  |
| `ZFA:0000893` | floor plate rhombomere 4 | `ZFA:0001488` | — |  |
| `ZFA:0000764` | floor plate rhombomere 5 | `ZFA:0001488` | — |  |
| `ZFA:0000889` | floor plate rhombomere 6 | `ZFA:0001488` | — |  |
| `ZFA:0000904` | floor plate rhombomere 7 | `ZFA:0001488` | — |  |
| `ZFA:0000765` | floor plate rhombomere 8 | `ZFA:0001488` | — |  |
| `ZFA:0001258` | floor plate rhombomere region | `ZFA:0001488` | — |  |
| `ZFA:0000890` | floor plate spinal cord region | `ZFA:0001488` | — |  |
| `ZFA:0000914` | floor plate telencephalic region | `ZFA:0001488` | — |  |
| `ZFA:0000109` | forebrain | `ZFA:0001488` | — |  |
| `ZFA:0001259` | forebrain ventricle | `ZFA:0001488` | — |  |
| `ZFA:0000110` | fourth ventricle | `ZFA:0001488` | — |  |
| `ZFA:0000211` | gill lamella | `ZFA:0001488` | — |  |
| `ZFA:0000357` | glomerular layer | `ZFA:0001488` | — |  |
| `ZFA:0000517` | glossopharyngeal lobe | `ZFA:0001488` | — |  |
| `ZFA:0000212` | granular eminence | `ZFA:0001488` | — |  |
| `ZFA:0001681` | grey matter | `ZFA:0001488` | — |  |
| `ZFA:0000213` | habenula | `ZFA:0001488` | — |  |
| `ZFA:0000359` | habenular commissure | `ZFA:0001488` | — | yes |
| `ZFA:0005949` | heart lymph vessel | `ZFA:0001488` | — | yes |
| `ZFA:0005952` | heart lymphatic system | `ZFA:0001488` | — | yes |
| `ZFA:0005065` | heart valve | `ZFA:0001488` | — |  |
| `ZFA:0005811` | heart vasculature | `ZFA:0001488` | — |  |
| `ZFA:0005161` | hepatic artery | `ZFA:0001488` | — |  |
| `ZFA:0001100` | hepatic duct | `ZFA:0001488` | — |  |
| `ZFA:0005090` | hepatic portal vein | `ZFA:0001488` | — |  |
| `ZFA:0005091` | hepatic sinusoid | `ZFA:0001488` | — |  |
| `ZFA:0000670` | hepatic vein | `ZFA:0001488` | — |  |
| `ZFA:0005167` | hepatopancreatic ampulla | `ZFA:0001488` | — |  |
| `ZFA:0000029` | hindbrain | `ZFA:0001488` | — |  |
| `ZFA:0001692` | hindbrain commissure | `ZFA:0001488` | — |  |
| `ZFA:0000520` | horizontal commissure | `ZFA:0001488` | — | yes |
| `ZFA:0005045` | hyaloid artery | `ZFA:0001488` | — | yes |
| `ZFA:0005858` | hyaloid capillaries | `ZFA:0001488` | — | yes |
| `ZFA:0005047` | hyaloid vein | `ZFA:0001488` | — | yes |
| `ZFA:0005046` | hyaloid vessel | `ZFA:0001488` | — | yes |
| `ZFA:0000673` | hypobranchial artery | `ZFA:0001488` | — | yes |
| `ZFA:0005787` | hypophyseal artery | `ZFA:0001488` | — |  |
| `ZFA:0005788` | hypophyseal vein | `ZFA:0001488` | — |  |
| `ZFA:0000032` | hypothalamus | `ZFA:0001488` | — |  |
| `ZFA:0001678` | immature eye | `ZFA:0001488` | — | yes |
| `ZFA:0005272` | immature gonad | `ZFA:0001488` | — |  |
| `ZFA:0000165` | inferior lobe | `ZFA:0001488` | — |  |
| `ZFA:0005392` | infraorbital sensory canal | `ZFA:0001488` | — |  |
| `ZFA:0001199` | infundibulum | `ZFA:0001488` | — |  |
| `ZFA:0005054` | inner optic circle | `ZFA:0001488` | — | yes |
| `ZFA:0005938` | inter-organ blood vessel | `ZFA:0001488` | — | yes |
| `ZFA:0005749` | intercalated duct pancreas | `ZFA:0001488` | — | yes |
| `ZFA:0005937` | interconnecting vessels | `ZFA:0001488` | — | yes |
| `ZFA:0006000` | intermediate hypothalamus | `ZFA:0001488` | — |  |
| `ZFA:0001669` | intermediate nucleus | `ZFA:0001488` | — |  |
| `ZFA:0000370` | intermediate thalamic nucleus | `ZFA:0001488` | — |  |
| `ZFA:0005081` | internal carotid artery | `ZFA:0001488` | — | yes |
| `ZFA:0005101` | interray vessel | `ZFA:0001488` | — | yes |
| `ZFA:0001345` | interrenal gland | `ZFA:0001488` | — |  |
| `ZFA:0001346` | interrenal primordium | `ZFA:0001488` | — |  |
| `ZFA:0005801` | interrenal vessel | `ZFA:0001488` | — |  |
| `ZFA:0001061` | intersegmental artery | `ZFA:0001488` | — | yes |
| `ZFA:0005319` | intersegmental lymph vessel | `ZFA:0001488` | — | yes |
| `ZFA:0001057` | intersegmental vein | `ZFA:0001488` | — | yes |
| `ZFA:0001285` | intersegmental vessel | `ZFA:0001488` | — | yes |
| `ZFA:0000684` | intertectal commissure | `ZFA:0001488` | — |  |
| `ZFA:0005100` | intervessel commissure | `ZFA:0001488` | — | yes |
| `ZFA:0001076` | intestinal bulb | `ZFA:0001488` | endoderm |  |
| `ZFA:0005848` | intestinal interlymphatic vessel | `ZFA:0001488` | — | yes |
| `ZFA:0005659` | intestinal lamina propria mucosa | `ZFA:0001488` | — |  |
| `ZFA:0005840` | intestinal lymphatic network | `ZFA:0001488` | — | yes |
| `ZFA:0005660` | intestinal mucosa | `ZFA:0001488` | — |  |
| `ZFA:0005737` | intestinal rod | `ZFA:0001488` | endoderm | yes |
| `ZFA:0005169` | intrahepatic bile duct | `ZFA:0001488` | — |  |
| `ZFA:0005748` | intrapancreatic duct | `ZFA:0001488` | — |  |
| `ZFA:0001238` | iris | `ZFA:0001488` | — |  |
| `ZFA:0005109` | jugular lymphatic vessel | `ZFA:0001488` | — | yes |
| `ZFA:0005306` | kidney blood vessel | `ZFA:0001488` | — |  |
| `ZFA:0005305` | kidney vasculature | `ZFA:0001488` | — |  |
| `ZFA:0000374` | lagena | `ZFA:0001488` | — |  |
| `ZFA:0001054` | lateral dorsal aorta | `ZFA:0001488` | — | yes |
| `ZFA:0005837` | lateral facial lymph vessel | `ZFA:0001488` | — | yes |
| `ZFA:0007012` | lateral forebrain bundle | `ZFA:0001488` | — |  |
| `ZFA:0000379` | lateral forebrain bundle diencephalon | `ZFA:0001488` | — |  |
| `ZFA:0000779` | lateral forebrain bundle telencephalon | `ZFA:0001488` | — |  |
| `ZFA:0000533` | lateral funiculus | `ZFA:0001488` | — |  |
| `ZFA:0000227` | lateral hypothalamic nucleus | `ZFA:0001488` | — |  |
| `ZFA:0000534` | lateral longitudinal fasciculus | `ZFA:0001488` | — |  |
| `ZFA:0000229` | lateral olfactory tract | `ZFA:0001488` | — | yes |
| `ZFA:0000209` | lateral preglomerular nucleus | `ZFA:0001488` | — | yes |
| `ZFA:0005669` | lateral protoglomerulus | `ZFA:0001488` | — |  |
| `ZFA:0005717` | lateral protoglomerulus 1 | `ZFA:0001488` | — |  |
| `ZFA:0005718` | lateral protoglomerulus 2 | `ZFA:0001488` | — |  |
| `ZFA:0005719` | lateral protoglomerulus 3 | `ZFA:0001488` | — |  |
| `ZFA:0005720` | lateral protoglomerulus 4 | `ZFA:0001488` | — |  |
| `ZFA:0000532` | lateral valvula cerebelli | `ZFA:0001488` | — |  |
| `ZFA:0000780` | lateral wall diencephalic region | `ZFA:0001488` | — |  |
| `ZFA:0000906` | lateral wall midbrain region | `ZFA:0001488` | — |  |
| `ZFA:0000781` | lateral wall rhombomere 1 | `ZFA:0001488` | — | yes |
| `ZFA:0000907` | lateral wall rhombomere 2 | `ZFA:0001488` | — | yes |
| `ZFA:0000994` | lateral wall rhombomere 3 | `ZFA:0001488` | — | yes |
| `ZFA:0000782` | lateral wall rhombomere 4 | `ZFA:0001488` | — | yes |
| `ZFA:0000908` | lateral wall rhombomere 5 | `ZFA:0001488` | — | yes |
| `ZFA:0000995` | lateral wall rhombomere 6 | `ZFA:0001488` | — | yes |
| `ZFA:0000783` | lateral wall rhombomere 7 | `ZFA:0001488` | — | yes |
| `ZFA:0000909` | lateral wall rhombomere 8 | `ZFA:0001488` | — | yes |
| `ZFA:0000996` | lateral wall spinal cord | `ZFA:0001488` | — |  |
| `ZFA:0000785` | lateral wall telencephalic region | `ZFA:0001488` | — |  |
| `ZFA:0005675` | lateral zone olfactory bulb | `ZFA:0001488` | — |  |
| `ZFA:0005846` | left intestinal lymphatics | `ZFA:0001488` | — | yes |
| `ZFA:0005172` | left liver lobe | `ZFA:0001488` | — |  |
| `ZFA:0005702` | lg1 | `ZFA:0001488` | — |  |
| `ZFA:0005703` | lG2 | `ZFA:0001488` | — |  |
| `ZFA:0005704` | lG3 | `ZFA:0001488` | — |  |
| `ZFA:0005705` | lG4 | `ZFA:0001488` | — |  |
| `ZFA:0005706` | lg5 | `ZFA:0001488` | — |  |
| `ZFA:0005708` | lg6 | `ZFA:0001488` | — |  |
| `ZFA:0005707` | lGx | `ZFA:0001488` | — |  |
| `ZFA:0005939` | liver pancreas connecting vessel | `ZFA:0001488` | — | yes |
| `ZFA:0005106` | longitudinal lateral lymphatic vessel | `ZFA:0001488` | — | yes |
| `ZFA:0005845` | lower left intestinal lymph vessel | `ZFA:0001488` | — | yes |
| `ZFA:0001441` | lower rhombic lip | `ZFA:0001488` | — |  |
| `ZFA:0005842` | lower right intestinal lymph vessel | `ZFA:0001488` | — | yes |
| `ZFA:0005105` | lymph vasculature | `ZFA:0001488` | — |  |
| `ZFA:0005844` | lymph vessel | `ZFA:0001488` | — |  |
| `ZFA:0005832` | lymphatic branchial arch 1 | `ZFA:0001488` | — | yes |
| `ZFA:0005833` | lymphatic branchial arch 2 | `ZFA:0001488` | — | yes |
| `ZFA:0005834` | lymphatic branchial arch 3 | `ZFA:0001488` | — | yes |
| `ZFA:0005835` | lymphatic branchial arch 4 | `ZFA:0001488` | — | yes |
| `ZFA:0005715` | maG1 | `ZFA:0001488` | — |  |
| `ZFA:0000248` | magnocellular preoptic nucleus | `ZFA:0001488` | — |  |
| `ZFA:0000235` | magnocellular superficial pretectal nucleus | `ZFA:0001488` | — |  |
| `ZFA:0005716` | maGx | `ZFA:0001488` | — |  |
| `ZFA:0005752` | main intrapancreatic duct | `ZFA:0001488` | — | yes |
| `ZFA:0005451` | mandibular sensory canal | `ZFA:0001488` | — |  |
| `ZFA:0005933` | mature plexus | `ZFA:0001488` | — | yes |
| `ZFA:0005408` | maxillary barbel | `ZFA:0001488` | — | yes |
| `ZFA:0007074` | maxillary barbel blood sinus | `ZFA:0001488` | — | yes |
| `ZFA:0007079` | maxillary barbel blood vessel | `ZFA:0001488` | — | yes |
| `ZFA:0007078` | maxillary barbel lymph vessel | `ZFA:0001488` | — | yes |
| `ZFA:0007081` | maxillary barbel proximal plexus | `ZFA:0001488` | — | yes |
| `ZFA:0007080` | maxillary barbel vasculature | `ZFA:0001488` | — | yes |
| `ZFA:0005709` | mdG1 | `ZFA:0001488` | — |  |
| `ZFA:0005710` | mdG2 | `ZFA:0001488` | — |  |
| `ZFA:0005711` | mdG3 | `ZFA:0001488` | — |  |
| `ZFA:0005712` | mdG4 | `ZFA:0001488` | — |  |
| `ZFA:0005713` | mdG5 | `ZFA:0001488` | — |  |
| `ZFA:0005714` | mdG6 | `ZFA:0001488` | — |  |
| `ZFA:0000388` | medial caudal lobe | `ZFA:0001488` | — |  |
| `ZFA:0005839` | medial facial lymph vessel | `ZFA:0001488` | — | yes |
| `ZFA:0005111` | medial forebrain bundle | `ZFA:0001488` | — | yes |
| `ZFA:0000237` | medial forebrain bundle diencephalon | `ZFA:0001488` | — | yes |
| `ZFA:0000910` | medial forebrain bundle telencephalon | `ZFA:0001488` | — | yes |
| `ZFA:0005341` | medial longitudinal catecholaminergic tract | `ZFA:0001488` | — | yes |
| `ZFA:0000543` | medial longitudinal fasciculus | `ZFA:0001488` | — | yes |
| `ZFA:0000238` | medial olfactory tract | `ZFA:0001488` | — | yes |
| `ZFA:0000390` | medial preglomerular nucleus | `ZFA:0001488` | — | yes |
| `ZFA:0005671` | medial protoglomerulus | `ZFA:0001488` | — |  |
| `ZFA:0005726` | medial protoglomerulus 1 | `ZFA:0001488` | — |  |
| `ZFA:0005727` | medial protoglomerulus 2 | `ZFA:0001488` | — |  |
| `ZFA:0005728` | medial protoglomerulus 3 | `ZFA:0001488` | — |  |
| `ZFA:0005729` | medial protoglomerulus 4 | `ZFA:0001488` | — |  |
| `ZFA:0000280` | medial valvula cerebelli | `ZFA:0001488` | — |  |
| `ZFA:0005676` | medial zone olfactory bulb | `ZFA:0001488` | — |  |
| `ZFA:0000039` | median axial vein | `ZFA:0001488` | — | yes |
| `ZFA:0005055` | median palatocerebral vein | `ZFA:0001488` | — | yes |
| `ZFA:0000392` | median tuberal portion | `ZFA:0001488` | — |  |
| `ZFA:0005682` | mediodorsal zone of the olfactory bulb | `ZFA:0001488` | — |  |
| `ZFA:0000545` | medulla oblongata | `ZFA:0001488` | — |  |
| `ZFA:0001068` | mesencephalic artery | `ZFA:0001488` | — | yes |
| `ZFA:0005092` | mesencephalic vein | `ZFA:0001488` | — | yes |
| `ZFA:0000546` | mesonephric duct | `ZFA:0001488` | — |  |
| `ZFA:0000333` | mesovarium | `ZFA:0001488` | — |  |
| `ZFA:0005084` | metencephalic artery | `ZFA:0001488` | — | yes |
| `ZFA:0005010` | mid cerebral vein | `ZFA:0001488` | — | yes |
| `ZFA:0001323` | mid intestine | `ZFA:0001488` | endoderm |  |
| `ZFA:0000128` | midbrain | `ZFA:0001488` | — |  |
| `ZFA:0005078` | middle mesencephalic central artery | `ZFA:0001488` | — | yes |
| `ZFA:0001488` | multi-tissue structure | `ZFA:0001488` | — | yes |
| `ZFA:0005085` | nasal artery | `ZFA:0001488` | — | yes |
| `ZFA:0005507` | nasal capsule | `ZFA:0001488` | — | yes |
| `ZFA:0005053` | nasal ciliary artery | `ZFA:0001488` | — | yes |
| `ZFA:0005093` | nasal vein | `ZFA:0001488` | — | yes |
| `ZFA:0001271` | neurohypophysis | `ZFA:0001488` | — |  |
| `ZFA:0005850` | nucleus of the caudal commissure | `ZFA:0001488` | — | yes |
| `ZFA:0005339` | nucleus of the lateral recess | `ZFA:0001488` | — |  |
| `ZFA:0000941` | nucleus of the medial longitudinal fasciculus synencephalon | `ZFA:0001488` | — |  |
| `ZFA:0005340` | nucleus of the posterior recess | `ZFA:0001488` | — |  |
| `ZFA:0001340` | nucleus of the tract of the postoptic commissure | `ZFA:0001488` | — | yes |
| `ZFA:0000397` | nucleus subglomerulosis | `ZFA:0001488` | — |  |
| `ZFA:0007057` | ocular blood vessel | `ZFA:0001488` | — | yes |
| `ZFA:0000402` | olfactory bulb | `ZFA:0001488` | — |  |
| `ZFA:0005661` | olfactory bulb glomerulus | `ZFA:0001488` | — |  |
| `ZFA:0005668` | olfactory bulb protoglomerulus | `ZFA:0001488` | — |  |
| `ZFA:0005022` | opercular artery | `ZFA:0001488` | — | yes |
| `ZFA:0005044` | optic artery | `ZFA:0001488` | — | yes |
| `ZFA:0000556` | optic chiasm | `ZFA:0001488` | — | yes |
| `ZFA:0005094` | optic choroid vascular plexus | `ZFA:0001488` | — |  |
| `ZFA:0001202` | optic cup | `ZFA:0001488` | — | yes |
| `ZFA:0000445` | optic tectum | `ZFA:0001488` | — |  |
| `ZFA:0000252` | optic tract | `ZFA:0001488` | — | yes |
| `ZFA:0005032` | optic vein | `ZFA:0001488` | — | yes |
| `ZFA:0005462` | otic duct | `ZFA:0001488` | — | yes |
| `ZFA:0005393` | otic sensory canal | `ZFA:0001488` | — |  |
| `ZFA:0005838` | otolithic lymph vessel | `ZFA:0001488` | — | yes |
| `ZFA:0001110` | ovarian follicle | `ZFA:0001488` | — |  |
| `ZFA:0001263` | ovarian follicle stage I | `ZFA:0001488` | — | yes |
| `ZFA:0001265` | ovarian follicle stage II | `ZFA:0001488` | — | yes |
| `ZFA:0001266` | ovarian follicle stage III | `ZFA:0001488` | — | yes |
| `ZFA:0001264` | ovarian follicle stage IV | `ZFA:0001488` | — | yes |
| `ZFA:0005862` | ovarian lymph vessel | `ZFA:0001488` | — | yes |
| `ZFA:0000560` | oviduct | `ZFA:0001488` | — |  |
| `ZFA:0005050` | palatocerebral artery | `ZFA:0001488` | — | yes |
| `ZFA:0005056` | palatocerebral vein | `ZFA:0001488` | — | yes |
| `ZFA:0001372` | pancreatic duct | `ZFA:0001488` | endoderm |  |
| `ZFA:0005751` | pancreatic interlobular duct | `ZFA:0001488` | — | yes |
| `ZFA:0005750` | pancreatic intralobular duct | `ZFA:0001488` | — |  |
| `ZFA:0005034` | parachordal vessel | `ZFA:0001488` | — | yes |
| `ZFA:0000404` | paracommissural nucleus | `ZFA:0001488` | — |  |
| `ZFA:0000475` | paraventricular organ | `ZFA:0001488` | — |  |
| `ZFA:0005131` | parietal peritoneum | `ZFA:0001488` | — | yes |
| `ZFA:0001680` | parvocellular preoptic nucleus | `ZFA:0001488` | — | yes |
| `ZFA:0000406` | parvocellular superficial pretectal nucleus | `ZFA:0001488` | — |  |
| `ZFA:0005086` | pectoral artery | `ZFA:0001488` | — | yes |
| `ZFA:0005301` | pectoral fin blood vessel | `ZFA:0001488` | — | yes |
| `ZFA:0005317` | pectoral fin fold | `ZFA:0001488` | — | yes |
| `ZFA:0005302` | pectoral fin lymph vessel | `ZFA:0001488` | — | yes |
| `ZFA:0005096` | pectoral fin vasculature | `ZFA:0001488` | — | yes |
| `ZFA:0005107` | pectoral lymphatic vessel | `ZFA:0001488` | — | yes |
| `ZFA:0005087` | pectoral vein | `ZFA:0001488` | — | yes |
| `ZFA:0000054` | pericardium | `ZFA:0001488` | — | yes |
| `ZFA:0005461` | perilymphatic duct | `ZFA:0001488` | — | yes |
| `ZFA:0005120` | peritoneum | `ZFA:0001488` | — | yes |
| `ZFA:0000516` | periventricular grey zone | `ZFA:0001488` | — |  |
| `ZFA:0000260` | periventricular nucleus | `ZFA:0001488` | — |  |
| `ZFA:0000408` | periventricular nucleus of caudal tuberculum | `ZFA:0001488` | — |  |
| `ZFA:0001306` | pharyngeal arch | `ZFA:0001488` | — | yes |
| `ZFA:0001612` | pharyngeal arch 1 | `ZFA:0001488` | — | yes |
| `ZFA:0001611` | pharyngeal arch 2 | `ZFA:0001488` | — | yes |
| `ZFA:0001606` | pharyngeal arch 3 | `ZFA:0001488` | — | yes |
| `ZFA:0001613` | pharyngeal arch 3-7 | `ZFA:0001488` | — |  |
| `ZFA:0001607` | pharyngeal arch 4 | `ZFA:0001488` | — | yes |
| `ZFA:0001608` | pharyngeal arch 5 | `ZFA:0001488` | — | yes |
| `ZFA:0001609` | pharyngeal arch 6 | `ZFA:0001488` | — | yes |
| `ZFA:0001610` | pharyngeal arch 7 | `ZFA:0001488` | — | yes |
| `ZFA:0001106` | pharyngeal pouch | `ZFA:0001488` | — |  |
| `ZFA:0001128` | pharyngeal pouch 1 | `ZFA:0001488` | — | yes |
| `ZFA:0001130` | pharyngeal pouch 2 | `ZFA:0001488` | — | yes |
| `ZFA:0001131` | pharyngeal pouch 3 | `ZFA:0001488` | — | yes |
| `ZFA:0001134` | pharyngeal pouch 4 | `ZFA:0001488` | — | yes |
| `ZFA:0001133` | pharyngeal pouch 5 | `ZFA:0001488` | — | yes |
| `ZFA:0001132` | pharyngeal pouch 6 | `ZFA:0001488` | — | yes |
| `ZFA:0001129` | pharyngeal pouches 2-6 | `ZFA:0001488` | — | yes |
| `ZFA:0005003` | pharyngeal vasculature | `ZFA:0001488` | — | yes |
| `ZFA:0000056` | pharynx | `ZFA:0001488` | — |  |
| `ZFA:0001430` | pneumatic duct | `ZFA:0001488` | — | yes |
| `ZFA:0005394` | post-otic sensory canal | `ZFA:0001488` | — |  |
| `ZFA:0005037` | post-vent vasculature | `ZFA:0001488` | — | yes |
| `ZFA:0000477` | posterior cardinal vein | `ZFA:0001488` | — | yes |
| `ZFA:0001063` | posterior caudal vein | `ZFA:0001488` | — | yes |
| `ZFA:0005027` | posterior cerebral vein | `ZFA:0001488` | — |  |
| `ZFA:0001278` | posterior chamber swim bladder | `ZFA:0001488` | — | yes |
| `ZFA:0005001` | posterior communicating artery | `ZFA:0001488` | — | yes |
| `ZFA:0000706` | posterior intestine | `ZFA:0001488` | endoderm |  |
| `ZFA:0005079` | posterior mesencephalic central artery | `ZFA:0001488` | — | yes |
| `ZFA:0005088` | posterior mesenteric artery | `ZFA:0001488` | — | yes |
| `ZFA:0001623` | posterior pronephric duct | `ZFA:0001488` | — |  |
| `ZFA:0005684` | posteromedial glomerulus | `ZFA:0001488` | — |  |
| `ZFA:0000059` | postoptic commissure | `ZFA:0001488` | — | yes |
| `ZFA:0001571` | postovulatory follicle | `ZFA:0001488` | — | yes |
| `ZFA:0001662` | preglomerular nucleus | `ZFA:0001488` | — |  |
| `ZFA:0005448` | preopercular sensory canal | `ZFA:0001488` | — |  |
| `ZFA:0005395` | preoperculo-mandibular sensory canal | `ZFA:0001488` | — |  |
| `ZFA:0000470` | preoptic area | `ZFA:0001488` | — |  |
| `ZFA:0005789` | preopticohypophyseal tract | `ZFA:0001488` | — | yes |
| `ZFA:0005344` | preopticohypothalamic tract | `ZFA:0001488` | — | yes |
| `ZFA:0001718` | presumptive atrium heart tube | `ZFA:0001488` | — |  |
| `ZFA:0001721` | presumptive atrium primitive heart tube | `ZFA:0001488` | — |  |
| `ZFA:0001719` | presumptive cardiac ventricle heart tube | `ZFA:0001488` | — |  |
| `ZFA:0001720` | presumptive cardiac ventricle primitive heart tube | `ZFA:0001488` | — |  |
| `ZFA:0000601` | pretectal periventricular nucleus | `ZFA:0001488` | — |  |
| `ZFA:0000266` | pretecto-mammillary tract | `ZFA:0001488` | — | yes |
| `ZFA:0000418` | pretectum | `ZFA:0001488` | — |  |
| `ZFA:0005026` | primary head sinus | `ZFA:0001488` | — | yes |
| `ZFA:0000149` | primitive heart tube | `ZFA:0001488` | — |  |
| `ZFA:0001053` | primitive internal carotid artery | `ZFA:0001488` | — | yes |
| `ZFA:0001355` | primitive meninx | `ZFA:0001488` | — |  |
| `ZFA:0001062` | primitive mesencephalic artery | `ZFA:0001488` | — | yes |
| `ZFA:0005048` | primitive prosencephalic artery | `ZFA:0001488` | — | yes |
| `ZFA:0001052` | primordial hindbrain channel | `ZFA:0001488` | — | yes |
| `ZFA:0005017` | primordial midbrain channel | `ZFA:0001488` | — | yes |
| `ZFA:0001622` | pronephric distal early tubule | `ZFA:0001488` | — |  |
| `ZFA:0001624` | pronephric distal late tubule | `ZFA:0001488` | — |  |
| `ZFA:0000150` | pronephric duct | `ZFA:0001488` | — |  |
| `ZFA:0001557` | pronephric glomerulus | `ZFA:0001488` | — |  |
| `ZFA:0001620` | pronephric proximal convoluted tubule | `ZFA:0001488` | — |  |
| `ZFA:0001621` | pronephric proximal straight tubule | `ZFA:0001488` | — |  |
| `ZFA:0001558` | pronephric tubule | `ZFA:0001488` | — |  |
| `ZFA:0005500` | prootic bulla | `ZFA:0001488` | — | yes |
| `ZFA:0005049` | prosencephalic artery | `ZFA:0001488` | — | yes |
| `ZFA:0005290` | proximal convoluted tubule | `ZFA:0001488` | — |  |
| `ZFA:0005291` | proximal straight tubule | `ZFA:0001488` | — |  |
| `ZFA:0005967` | pseudobranch | `ZFA:0001488` | — | yes |
| `ZFA:0005011` | pseudobranchial artery | `ZFA:0001488` | — | yes |
| `ZFA:0005099` | ray vein | `ZFA:0001488` | — | yes |
| `ZFA:0005014` | recurrent branch afferent branchial artery | `ZFA:0001488` | — |  |
| `ZFA:0000420` | renal artery | `ZFA:0001488` | — | yes |
| `ZFA:0005281` | renal corpuscle | `ZFA:0001488` | — |  |
| `ZFA:0005289` | renal duct | `ZFA:0001488` | — |  |
| `ZFA:0001288` | renal glomerulus | `ZFA:0001488` | — |  |
| `ZFA:0000577` | renal portal vein | `ZFA:0001488` | — | yes |
| `ZFA:0001287` | renal tubule | `ZFA:0001488` | — |  |
| `ZFA:0005854` | replacement  tooth 3V | `ZFA:0001488` | — | yes |
| `ZFA:0005856` | replacement tooth 1V | `ZFA:0001488` | — | yes |
| `ZFA:0005855` | replacement tooth 2V | `ZFA:0001488` | — | yes |
| `ZFA:0005852` | replacement tooth 4V | `ZFA:0001488` | — | yes |
| `ZFA:0005853` | replacement tooth 5V | `ZFA:0001488` | — | yes |
| `ZFA:0000152` | retina | `ZFA:0001488` | — |  |
| `ZFA:0005864` | retinotectal tract | `ZFA:0001488` | — | yes |
| `ZFA:0001440` | rhombic lip | `ZFA:0001488` | — |  |
| `ZFA:0005843` | right intestinal lymphatics | `ZFA:0001488` | — | yes |
| `ZFA:0005173` | right liver lobe | `ZFA:0001488` | — |  |
| `ZFA:0007058` | roof plate | `ZFA:0001488` | — |  |
| `ZFA:0000643` | rostral cerebellar tract | `ZFA:0001488` | — |  |
| `ZFA:0000579` | rostral mesencephalo-cerebellar tract | `ZFA:0001488` | — |  |
| `ZFA:0000426` | rostral parvocellular preoptic nucleus | `ZFA:0001488` | — |  |
| `ZFA:0000580` | rostral preglomerular nucleus | `ZFA:0001488` | — | yes |
| `ZFA:0000427` | rostral thalamic nucleus | `ZFA:0001488` | — |  |
| `ZFA:0000581` | rostral tuberal nucleus | `ZFA:0001488` | — |  |
| `ZFA:0000276` | rostrolateral thalamic nucleus of Butler & Saidel | `ZFA:0001488` | — |  |
| `ZFA:0000428` | saccule | `ZFA:0001488` | — |  |
| `ZFA:0005829` | Schlemm's canal | `ZFA:0001488` | — |  |
| `ZFA:0005563` | sclera | `ZFA:0001488` | — |  |
| `ZFA:0000430` | secondary gustatory tract | `ZFA:0001488` | — |  |
| `ZFA:0000677` | segmental intercostal artery | `ZFA:0001488` | — | yes |
| `ZFA:0005879` | seminiferous tubule | `ZFA:0001488` | — |  |
| `ZFA:0005443` | sensory canal | `ZFA:0001488` | — |  |
| `ZFA:0005447` | sensory canal tubule | `ZFA:0001488` | — | yes |
| `ZFA:0005425` | serous membrane | `ZFA:0001488` | — | yes |
| `ZFA:0000680` | sinoatrial valve | `ZFA:0001488` | — |  |
| `ZFA:0000154` | sinus venosus | `ZFA:0001488` | — |  |
| `ZFA:0001268` | sperm duct | `ZFA:0001488` | — |  |
| `ZFA:0000682` | spinal artery | `ZFA:0001488` | — | yes |
| `ZFA:0005578` | spinal nerve root | `ZFA:0001488` | — |  |
| `ZFA:0001332` | spinal neuromere | `ZFA:0001488` | — |  |
| `ZFA:0000683` | subcommissural organ | `ZFA:0001488` | — |  |
| `ZFA:0005035` | subintestinal vein | `ZFA:0001488` | — | yes |
| `ZFA:0005934` | subintestinal venous plexus | `ZFA:0001488` | — | yes |
| `ZFA:0000686` | superficial grey and white zone | `ZFA:0001488` | — |  |
| `ZFA:0000687` | superficial pretectum | `ZFA:0001488` | — |  |
| `ZFA:0005935` | superficial subintestinal venous plexus | `ZFA:0001488` | — | yes |
| `ZFA:0000441` | suprachiasmatic nucleus | `ZFA:0001488` | — |  |
| `ZFA:0005036` | supraintestinal artery | `ZFA:0001488` | — | yes |
| `ZFA:0005747` | supraintestinal lymphatic vessel | `ZFA:0001488` | — | yes |
| `ZFA:0005038` | supraintestinal vein | `ZFA:0001488` | — | yes |
| `ZFA:0000690` | supraoptic commissure | `ZFA:0001488` | — | yes |
| `ZFA:0001657` | supraoptic tract | `ZFA:0001488` | — |  |
| `ZFA:0005396` | supraorbital sensory canal | `ZFA:0001488` | — |  |
| `ZFA:0005445` | supratemporal sensory canal | `ZFA:0001488` | — | yes |
| `ZFA:0005089` | swim bladder artery | `ZFA:0001488` | — | yes |
| `ZFA:0000293` | synencephalon | `ZFA:0001488` | — |  |
| `ZFA:0001074` | taste bud | `ZFA:0001488` | — |  |
| `ZFA:0005907` | tectal neuropile | `ZFA:0001488` | — |  |
| `ZFA:0000159` | tectal ventricle | `ZFA:0001488` | — |  |
| `ZFA:0000446` | tecto-bulbar tract | `ZFA:0001488` | — | yes |
| `ZFA:0000160` | tegmentum | `ZFA:0001488` | — |  |
| `ZFA:0000696` | telencephalic ventricle | `ZFA:0001488` | — |  |
| `ZFA:0000597` | telencephalic white matter | `ZFA:0001488` | — |  |
| `ZFA:0000079` | telencephalon | `ZFA:0001488` | — |  |
| `ZFA:0000448` | tertiary gustatory nucleus | `ZFA:0001488` | — |  |
| `ZFA:0007010` | thalamic eminence | `ZFA:0001488` | — |  |
| `ZFA:0001215` | thalamus | `ZFA:0001488` | — |  |
| `ZFA:0001113` | thecal cell layer | `ZFA:0001488` | — |  |
| `ZFA:0000161` | third ventricle | `ZFA:0001488` | — |  |
| `ZFA:0005110` | thoracic duct | `ZFA:0001488` | — | yes |
| `ZFA:0005333` | tongue | `ZFA:0001488` | — |  |
| `ZFA:0001148` | tooth 1D | `ZFA:0001488` | — | yes |
| `ZFA:0001146` | tooth 1MD | `ZFA:0001488` | — | yes |
| `ZFA:0001141` | tooth 1V | `ZFA:0001488` | — | yes |
| `ZFA:0001150` | tooth 2D | `ZFA:0001488` | — | yes |
| `ZFA:0001147` | tooth 2MD | `ZFA:0001488` | — | yes |
| `ZFA:0001144` | tooth 2V | `ZFA:0001488` | — | yes |
| `ZFA:0001152` | tooth 3MD | `ZFA:0001488` | — | yes |
| `ZFA:0001145` | tooth 3V | `ZFA:0001488` | — | yes |
| `ZFA:0001151` | tooth 4MD | `ZFA:0001488` | — | yes |
| `ZFA:0001143` | tooth 4V | `ZFA:0001488` | — | yes |
| `ZFA:0001142` | tooth 5V | `ZFA:0001488` | — | yes |
| `ZFA:0005141` | tooth pulp | `ZFA:0001488` | — |  |
| `ZFA:0000294` | torus lateralis | `ZFA:0001488` | — |  |
| `ZFA:0000449` | torus longitudinalis | `ZFA:0001488` | — |  |
| `ZFA:0000599` | torus semicircularis | `ZFA:0001488` | — |  |
| `ZFA:0005452` | tract of the caudal commissure | `ZFA:0001488` | — |  |
| `ZFA:0005875` | tract of the commissure of the caudal tuberculum | `ZFA:0001488` | — | yes |
| `ZFA:0001366` | tract of the postoptic commissure | `ZFA:0001488` | — | yes |
| `ZFA:0005248` | trans-choroid plexus branch | `ZFA:0001488` | — |  |
| `ZFA:0005412` | transverse canal | `ZFA:0001488` | — |  |
| `ZFA:0005444` | trunk sensory canal | `ZFA:0001488` | — | yes |
| `ZFA:0005024` | trunk vasculature | `ZFA:0001488` | — | yes |
| `ZFA:0001700` | tunica externa swim bladder | `ZFA:0001488` | — | yes |
| `ZFA:0001701` | tunica interna swim bladder | `ZFA:0001488` | — | yes |
| `ZFA:0001448` | ultimobranchial body | `ZFA:0001488` | — |  |
| `ZFA:0000296` | uncrossed tecto-bulbar tract | `ZFA:0001488` | — | yes |
| `ZFA:0005847` | upper left intestinal lymph vessel | `ZFA:0001488` | — | yes |
| `ZFA:0001442` | upper rhombic lip | `ZFA:0001488` | — |  |
| `ZFA:0005841` | upper right intestinal lymph vessel | `ZFA:0001488` | — | yes |
| `ZFA:0000700` | utricle | `ZFA:0001488` | — |  |
| `ZFA:0000297` | vagal lobe | `ZFA:0001488` | — |  |
| `ZFA:0005653` | vagal sensory zone | `ZFA:0001488` | — |  |
| `ZFA:0000603` | valvula cerebelli | `ZFA:0001488` | — |  |
| `ZFA:0005931` | vascular plexus | `ZFA:0001488` | — | yes |
| `ZFA:0005249` | vasculature | `ZFA:0001488` | — |  |
| `ZFA:0000082` | vein | `ZFA:0001488` | — | yes |
| `ZFA:0000454` | ventral accessory optic nucleus | `ZFA:0001488` | — |  |
| `ZFA:0000604` | ventral aorta | `ZFA:0001488` | — | yes |
| `ZFA:0005083` | ventral branch nasal ciliary artery | `ZFA:0001488` | — | yes |
| `ZFA:0005571` | ventral canal eye | `ZFA:0001488` | — |  |
| `ZFA:0001069` | ventral fin fold | `ZFA:0001488` | — | yes |
| `ZFA:0000605` | ventral funiculus | `ZFA:0001488` | — |  |
| `ZFA:0000702` | ventral horn spinal cord | `ZFA:0001488` | — |  |
| `ZFA:0000707` | ventral hypothalamic zone | `ZFA:0001488` | — |  |
| `ZFA:0005174` | ventral liver lobe | `ZFA:0001488` | — |  |
| `ZFA:0005672` | ventral posterior glomerulus | `ZFA:0001488` | — | yes |
| `ZFA:0000607` | ventral rhombencephalic commissure | `ZFA:0001488` | — | yes |
| `ZFA:0000985` | ventral rhombencephalic commissure medulla oblongata | `ZFA:0001488` | — |  |
| `ZFA:0000304` | ventral telencephalon | `ZFA:0001488` | — |  |
| `ZFA:0000458` | ventral thalamus | `ZFA:0001488` | — |  |
| `ZFA:0005576` | ventral thalamus nucleus | `ZFA:0001488` | — |  |
| `ZFA:0005677` | ventral zone olfactory bulb | `ZFA:0001488` | — |  |
| `ZFA:0001375` | ventriculo bulbo valve | `ZFA:0001488` | — |  |
| `ZFA:0005680` | ventroanterior zone of olfactory bulb | `ZFA:0001488` | — |  |
| `ZFA:0000708` | ventrolateral optic tract | `ZFA:0001488` | — | yes |
| `ZFA:0000306` | ventrolateral thalamic nucleus | `ZFA:0001488` | — |  |
| `ZFA:0000459` | ventromedial thalamic nucleus | `ZFA:0001488` | — |  |
| `ZFA:0005679` | ventromedial zone olfactory bulb | `ZFA:0001488` | — |  |
| `ZFA:0005681` | ventroposterior zone olfactory bulb | `ZFA:0001488` | — |  |
| `ZFA:0005315` | venule | `ZFA:0001488` | — | yes |
| `ZFA:0005033` | vertebral artery | `ZFA:0001488` | — | yes |
| `ZFA:0000709` | vestibulo-spinal tract | `ZFA:0001488` | — | yes |
| `ZFA:0000307` | vestibulolateralis lobe | `ZFA:0001488` | — |  |
| `ZFA:0005132` | visceral peritoneum | `ZFA:0001488` | — | yes |
| `ZFA:0005691` | vmG1 | `ZFA:0001488` | — |  |
| `ZFA:0005692` | vmG2 | `ZFA:0001488` | — |  |
| `ZFA:0005693` | vmG3 | `ZFA:0001488` | — |  |
| `ZFA:0005694` | vmG4 | `ZFA:0001488` | — |  |
| `ZFA:0005695` | vmG5 | `ZFA:0001488` | — |  |
| `ZFA:0005696` | vmG6 | `ZFA:0001488` | — |  |
| `ZFA:0005697` | vmG7 | `ZFA:0001488` | — |  |
| `ZFA:0005698` | vmGx | `ZFA:0001488` | — |  |
| `ZFA:0005699` | vmGy | `ZFA:0001488` | — |  |
| `ZFA:0005700` | vpG1 | `ZFA:0001488` | — |  |
| `ZFA:0005701` | vpG2 | `ZFA:0001488` | — |  |
| `ZFA:0001682` | white matter | `ZFA:0001488` | — |  |

### `tissue` (866)

| Id | Name | Source class | explicit_germ_layer | Stranded |
| --- | --- | --- | --- | --- |
| `ZFA:0000713` | abducens motor nucleus | `ZFA:0001477` | — |  |
| `ZFA:0000462` | abductor hyohyoid | `ZFA:0001477` | — | yes |
| `ZFA:0005269` | abductor muscle | `ZFA:0001477` | — | yes |
| `ZFA:0000614` | abductor profundus | `ZFA:0001477` | — |  |
| `ZFA:0000615` | adductor arcus palatini | `ZFA:0001477` | — | yes |
| `ZFA:0000715` | adductor hyohyoid | `ZFA:0001477` | — | yes |
| `ZFA:0007053` | adductor hyomandibulae | `ZFA:0001477` | — | yes |
| `ZFA:0007049` | adductor mandibulae | `ZFA:0001477` | — | yes |
| `ZFA:0000311` | adductor mandibulae complex | `ZFA:0001477` | — | yes |
| `ZFA:0005268` | adductor muscle | `ZFA:0001477` | — | yes |
| `ZFA:0000465` | adductor operculi | `ZFA:0001477` | — | yes |
| `ZFA:0000616` | adductor profundus | `ZFA:0001477` | — |  |
| `ZFA:0001198` | adenohypophyseal placode | `ZFA:0001477` | — | yes |
| `ZFA:0005345` | adipose tissue | `ZFA:0001477` | — | yes |
| `ZFA:0001357` | alar plate midbrain region | `ZFA:0001477` | — | yes |
| `ZFA:0005144` | ampullary nerve | `ZFA:0001477` | — | yes |
| `ZFA:0000466` | anal depressor | `ZFA:0001477` | — |  |
| `ZFA:0000617` | anal erector | `ZFA:0001477` | — |  |
| `ZFA:0000313` | anal inclinator | `ZFA:0001477` | — |  |
| `ZFA:0005897` | anal protractor | `ZFA:0001477` | — |  |
| `ZFA:0005896` | anal retractor | `ZFA:0001477` | — |  |
| `ZFA:0005604` | angiogenic sprout | `ZFA:0001477` | — | yes |
| `ZFA:0001676` | annular ligament | `ZFA:0001477` | — |  |
| `ZFA:0000004` | anterior axial hypoblast | `ZFA:0001477` | — | yes |
| `ZFA:0000619` | anterior crista | `ZFA:0001477` | — | yes |
| `ZFA:0000468` | anterior crista primordium | `ZFA:0001477` | — | yes |
| `ZFA:0001578` | anterior dorsomedial process of autopalatine | `ZFA:0001477` | — |  |
| `ZFA:0001470` | anterior lateral line | `ZFA:0001477` | — |  |
| `ZFA:0001391` | anterior lateral line ganglion | `ZFA:0001477` | — | yes |
| `ZFA:0000425` | anterior lateral line nerve | `ZFA:0001477` | — |  |
| `ZFA:0005117` | anterior lateral line primordium | `ZFA:0001477` | — |  |
| `ZFA:0005039` | anterior lateral mesoderm | `ZFA:0001477` | — | yes |
| `ZFA:0005041` | anterior lateral plate mesoderm | `ZFA:0001477` | — | yes |
| `ZFA:0005657` | anterior lateral process of autopalatine | `ZFA:0001477` | — |  |
| `ZFA:0000168` | anterior macula | `ZFA:0001477` | — |  |
| `ZFA:0005923` | anterior migratory muscle precursor stream | `ZFA:0001477` | — | yes |
| `ZFA:0007024` | anterior neural keel | `ZFA:0001477` | — | yes |
| `ZFA:0007016` | anterior neural plate | `ZFA:0001477` | — | yes |
| `ZFA:0007031` | anterior neural rod | `ZFA:0001477` | — | yes |
| `ZFA:0007038` | anterior neural tube | `ZFA:0001477` | — | yes |
| `ZFA:0007014` | anterior presumptive neural plate | `ZFA:0001477` | — | yes |
| `ZFA:0005337` | anterior swim bladder bud | `ZFA:0001477` | endoderm | yes |
| `ZFA:0005655` | anterior ventromedial process of autopalatine | `ZFA:0001477` | — |  |
| `ZFA:0005148` | apical epidermal cap | `ZFA:0001477` | — | yes |
| `ZFA:0005652` | aponeurosis | `ZFA:0001477` | — | yes |
| `ZFA:0005146` | area postrema | `ZFA:0001477` | — |  |
| `ZFA:0005914` | argentum | `ZFA:0001477` | — |  |
| `ZFA:0005275` | arrector muscle | `ZFA:0001477` | — | yes |
| `ZFA:0001614` | atrial endocardium | `ZFA:0001477` | — |  |
| `ZFA:0005774` | atrial epicardium | `ZFA:0001477` | — |  |
| `ZFA:0001374` | atrial myocardium | `ZFA:0001477` | — |  |
| `ZFA:0001616` | atrioventricular canal endocardium | `ZFA:0001477` | — |  |
| `ZFA:0005070` | atrioventricular node | `ZFA:0001477` | — |  |
| `ZFA:0005073` | atrioventricular ring | `ZFA:0001477` | — |  |
| `ZFA:0001493` | atypical epithelium | `ZFA:0001477` | — | yes |
| `ZFA:0001378` | axial hypoblast | `ZFA:0001477` | — | yes |
| `ZFA:0001204` | axial mesoderm | `ZFA:0001477` | — | yes |
| `ZFA:0005796` | basal layer breeding tubercle | `ZFA:0001477` | — | yes |
| `ZFA:0000761` | basal plate midbrain region | `ZFA:0001477` | — | yes |
| `ZFA:0005150` | basal regeneration epithelium | `ZFA:0001477` | — | yes |
| `ZFA:0001270` | blastema | `ZFA:0001477` | — | yes |
| `ZFA:0000094` | blood island | `ZFA:0001477` | — |  |
| `ZFA:0005257` | blood vessel endothelium | `ZFA:0001477` | — | yes |
| `ZFA:0005941` | bone callus | `ZFA:0001477` | — | yes |
| `ZFA:0005621` | bone tissue | `ZFA:0001477` | — | yes |
| `ZFA:0001637` | bony projection | `ZFA:0001477` | — | yes |
| `ZFA:0005575` | brain nucleus | `ZFA:0001477` | — |  |
| `ZFA:0000463` | branchial adductor | `ZFA:0001477` | — | yes |
| `ZFA:0001650` | branchial mesenchyme | `ZFA:0001477` | — | yes |
| `ZFA:0000172` | branchial muscle | `ZFA:0001477` | — |  |
| `ZFA:0000319` | branchiostegal membrane | `ZFA:0001477` | — |  |
| `ZFA:0005066` | bulbus arteriosus outer layer | `ZFA:0001477` | — |  |
| `ZFA:0005250` | capillary | `ZFA:0001477` | — | yes |
| `ZFA:0001318` | cardiac jelly | `ZFA:0001477` | — |  |
| `ZFA:0005280` | cardiac muscle | `ZFA:0001477` | — | yes |
| `ZFA:0001648` | cardiac neural crest | `ZFA:0001477` | — | yes |
| `ZFA:0005622` | cartilage tissue | `ZFA:0001477` | — | yes |
| `ZFA:0005903` | cartilaginous projection | `ZFA:0001477` | — | yes |
| `ZFA:0005767` | caudal fin fat | `ZFA:0001477` | — | yes |
| `ZFA:0005898` | caudal hematopoietic tissue | `ZFA:0001477` | — |  |
| `ZFA:0000321` | caudal levator | `ZFA:0001477` | — | yes |
| `ZFA:0000629` | caudal motor nucleus | `ZFA:0001477` | — | yes |
| `ZFA:0000177` | caudal oblique | `ZFA:0001477` | — | yes |
| `ZFA:0001699` | caudal octaval nerve motor nucleus | `ZFA:0001477` | — | yes |
| `ZFA:0000322` | caudal octaval nucleus | `ZFA:0001477` | — | yes |
| `ZFA:0000480` | caudal octavolateralis nucleus | `ZFA:0001477` | — | yes |
| `ZFA:0000179` | caudal root of abducens nerve | `ZFA:0001477` | — |  |
| `ZFA:0000181` | caudal zone of dorsal telencephalon | `ZFA:0001477` | — |  |
| `ZFA:0001668` | central nucleus of ventral telencephalon | `ZFA:0001477` | — | yes |
| `ZFA:0000826` | central nucleus torus semicircularis | `ZFA:0001477` | — |  |
| `ZFA:0000487` | central zone of dorsal telencephalon | `ZFA:0001477` | — |  |
| `ZFA:0005867` | cephalic mesoderm | `ZFA:0001477` | — | yes |
| `ZFA:0005644` | ceratobranchial 5 ligament | `ZFA:0001477` | — | yes |
| `ZFA:0000636` | cerebellar crest | `ZFA:0001477` | — |  |
| `ZFA:0001082` | chordo neural hinge | `ZFA:0001477` | — | yes |
| `ZFA:0005640` | cleithrum-vertebral ligament | `ZFA:0001477` | — | yes |
| `ZFA:0001711` | climbing fiber | `ZFA:0001477` | — |  |
| `ZFA:0005783` | cloacal epithelium | `ZFA:0001477` | — |  |
| `ZFA:0005062` | compact layer of ventricle | `ZFA:0001477` | — |  |
| `ZFA:0007050` | constrictor dorsalis | `ZFA:0001477` | — | yes |
| `ZFA:0005259` | continuous blood vessel endothelium | `ZFA:0001477` | — | yes |
| `ZFA:0000492` | coracoradialis | `ZFA:0001477` | — |  |
| `ZFA:0001687` | corneal endothelium | `ZFA:0001477` | — |  |
| `ZFA:0001683` | corneal epithelium | `ZFA:0001477` | — |  |
| `ZFA:0001688` | corneal primordium | `ZFA:0001477` | — |  |
| `ZFA:0001685` | corneal stroma | `ZFA:0001477` | — |  |
| `ZFA:0005813` | coronary capillary | `ZFA:0001477` | — |  |
| `ZFA:0005905` | coronoid process | `ZFA:0001477` | — |  |
| `ZFA:0001200` | corpuscles of Stannius | `ZFA:0001477` | — | yes |
| `ZFA:0005760` | cranial fat | `ZFA:0001477` | — | yes |
| `ZFA:0000013` | cranial ganglion | `ZFA:0001477` | — | yes |
| `ZFA:0000641` | cranial nerve | `ZFA:0001477` | — | yes |
| `ZFA:0000249` | cranial nerve I | `ZFA:0001477` | — |  |
| `ZFA:0000435` | cranial nerve II | `ZFA:0001477` | — |  |
| `ZFA:0000405` | cranial nerve III | `ZFA:0001477` | — |  |
| `ZFA:0000600` | cranial nerve IV | `ZFA:0001477` | — |  |
| `ZFA:0000668` | cranial nerve IX | `ZFA:0001477` | — |  |
| `ZFA:0001663` | cranial nerve root | `ZFA:0001477` | — | yes |
| `ZFA:0000697` | cranial nerve V | `ZFA:0001477` | — | yes |
| `ZFA:0000310` | cranial nerve VI | `ZFA:0001477` | — | yes |
| `ZFA:0000664` | cranial nerve VII | `ZFA:0001477` | — |  |
| `ZFA:0000247` | cranial nerve VIII | `ZFA:0001477` | — | yes |
| `ZFA:0000453` | cranial nerve X | `ZFA:0001477` | — |  |
| `ZFA:0001194` | cranial neural crest | `ZFA:0001477` | — | yes |
| `ZFA:0005825` | deep lateral dorsal muscle | `ZFA:0001477` | — |  |
| `ZFA:0005824` | deep lateral ventral muscle | `ZFA:0001477` | — |  |
| `ZFA:0005134` | dental epithelium | `ZFA:0001477` | — | yes |
| `ZFA:0005139` | dental mesenchyme | `ZFA:0001477` | — | yes |
| `ZFA:0005140` | dental papilla | `ZFA:0001477` | — | yes |
| `ZFA:0005143` | dentine | `ZFA:0001477` | — |  |
| `ZFA:0005270` | depressor muscle | `ZFA:0001477` | — | yes |
| `ZFA:0001182` | dermal deep region | `ZFA:0001477` | — | yes |
| `ZFA:0001513` | dermomyotome | `ZFA:0001477` | — | yes |
| `ZFA:0000645` | descending octaval nucleus | `ZFA:0001477` | — | yes |
| `ZFA:0000192` | descending trigeminal root | `ZFA:0001477` | — |  |
| `ZFA:0000498` | dilatator operculi | `ZFA:0001477` | — | yes |
| `ZFA:0005149` | distal epidermal cap | `ZFA:0001477` | — | yes |
| `ZFA:0001312` | dorsal anterior lateral line ganglion | `ZFA:0001477` | — | yes |
| `ZFA:0001480` | dorsal anterior lateral line nerve | `ZFA:0001477` | — |  |
| `ZFA:0000499` | dorsal arrector | `ZFA:0001477` | — | yes |
| `ZFA:0005122` | dorsal axial hypoblast | `ZFA:0001477` | — | yes |
| `ZFA:0000195` | dorsal depressor | `ZFA:0001477` | — |  |
| `ZFA:0000340` | dorsal entopeduncular nucleus of ventral telencephalon | `ZFA:0001477` | — | yes |
| `ZFA:0000500` | dorsal erector | `ZFA:0001477` | — |  |
| `ZFA:0005816` | dorsal fin protractor | `ZFA:0001477` | — |  |
| `ZFA:0005817` | dorsal fin retractor | `ZFA:0001477` | — |  |
| `ZFA:0000197` | dorsal habenular nucleus | `ZFA:0001477` | — |  |
| `ZFA:0000342` | dorsal inclinator | `ZFA:0001477` | — |  |
| `ZFA:0005822` | dorsal interfilamental caudal muscle | `ZFA:0001477` | — |  |
| `ZFA:0005112` | dorsal lateral line | `ZFA:0001477` | — |  |
| `ZFA:0005130` | dorsal mesentery | `ZFA:0001477` | — | yes |
| `ZFA:0000502` | dorsal motor nucleus trigeminal nerve | `ZFA:0001477` | — | yes |
| `ZFA:0000650` | dorsal motor root of V | `ZFA:0001477` | — |  |
| `ZFA:0000343` | dorsal nucleus of ventral telencephalon | `ZFA:0001477` | — | yes |
| `ZFA:0000503` | dorsal oblique branchial muscle | `ZFA:0001477` | — | yes |
| `ZFA:0000738` | dorsal oblique extraocular muscle | `ZFA:0001477` | — |  |
| `ZFA:0000651` | dorsal pelvic arrector | `ZFA:0001477` | — |  |
| `ZFA:0000345` | dorsal rectus | `ZFA:0001477` | — |  |
| `ZFA:0000504` | dorsal retractor | `ZFA:0001477` | — | yes |
| `ZFA:0000652` | dorsal root | `ZFA:0001477` | — |  |
| `ZFA:0000200` | dorsal root ganglion | `ZFA:0001477` | — | yes |
| `ZFA:0005663` | dorsal spinal nerve | `ZFA:0001477` | — | yes |
| `ZFA:0000346` | dorsal tegmental nucleus | `ZFA:0001477` | — |  |
| `ZFA:0000201` | dorsal transverse | `ZFA:0001477` | — | yes |
| `ZFA:0000506` | dorsal zone of dorsal telencephalon | `ZFA:0001477` | — |  |
| `ZFA:0007001` | dorso-rostral cluster | `ZFA:0001477` | — |  |
| `ZFA:0007060` | dorsolateral field | `ZFA:0001477` | — | yes |
| `ZFA:0001695` | dorsolateral motor nucleus of vagal nerve | `ZFA:0001477` | — | yes |
| `ZFA:0001672` | dorsolateral septum | `ZFA:0001477` | — | yes |
| `ZFA:0000016` | ectoderm | `ZFA:0001477` | ectoderm | yes |
| `ZFA:0005771` | ectomesenchyme | `ZFA:0001477` | — | yes |
| `ZFA:0005142` | enameloid | `ZFA:0001477` | — |  |
| `ZFA:0001317` | endocardial cushion | `ZFA:0001477` | — |  |
| `ZFA:0005489` | endocardial precursor | `ZFA:0001477` | — |  |
| `ZFA:0005072` | endocardial ring | `ZFA:0001477` | — |  |
| `ZFA:0001320` | endocardium | `ZFA:0001477` | — |  |
| `ZFA:0000017` | endoderm | `ZFA:0001477` | endoderm | yes |
| `ZFA:0005912` | endolymphatic sac | `ZFA:0001477` | — |  |
| `ZFA:0005927` | endothelial blood brain barrier | `ZFA:0001477` | — | yes |
| `ZFA:0005279` | enteric circular muscle | `ZFA:0001477` | — |  |
| `ZFA:0005278` | enteric longitudinal muscle | `ZFA:0001477` | — |  |
| `ZFA:0001084` | epaxial myotome region | `ZFA:0001477` | — |  |
| `ZFA:0000864` | epaxial region somite 1 | `ZFA:0001477` | — | yes |
| `ZFA:0000991` | epaxial region somite 10 | `ZFA:0001477` | — | yes |
| `ZFA:0000739` | epaxial region somite 11 | `ZFA:0001477` | — | yes |
| `ZFA:0000865` | epaxial region somite 12 | `ZFA:0001477` | — | yes |
| `ZFA:0001001` | epaxial region somite 13 | `ZFA:0001477` | — | yes |
| `ZFA:0000741` | epaxial region somite 14 | `ZFA:0001477` | — | yes |
| `ZFA:0000866` | epaxial region somite 15 | `ZFA:0001477` | — | yes |
| `ZFA:0001012` | epaxial region somite 16 | `ZFA:0001477` | — | yes |
| `ZFA:0000742` | epaxial region somite 17 | `ZFA:0001477` | — | yes |
| `ZFA:0000867` | epaxial region somite 18 | `ZFA:0001477` | — | yes |
| `ZFA:0001023` | epaxial region somite 19 | `ZFA:0001477` | — | yes |
| `ZFA:0000743` | epaxial region somite 2 | `ZFA:0001477` | — | yes |
| `ZFA:0000868` | epaxial region somite 20 | `ZFA:0001477` | — | yes |
| `ZFA:0001030` | epaxial region somite 21 | `ZFA:0001477` | — | yes |
| `ZFA:0000744` | epaxial region somite 22 | `ZFA:0001477` | — | yes |
| `ZFA:0000869` | epaxial region somite 23 | `ZFA:0001477` | — | yes |
| `ZFA:0001040` | epaxial region somite 24 | `ZFA:0001477` | — | yes |
| `ZFA:0000745` | epaxial region somite 25 | `ZFA:0001477` | — | yes |
| `ZFA:0000870` | epaxial region somite 26 | `ZFA:0001477` | — | yes |
| `ZFA:0000718` | epaxial region somite 27 | `ZFA:0001477` | — | yes |
| `ZFA:0000746` | epaxial region somite 28 | `ZFA:0001477` | — | yes |
| `ZFA:0000872` | epaxial region somite 29 | `ZFA:0001477` | — | yes |
| `ZFA:0000729` | epaxial region somite 3 | `ZFA:0001477` | — | yes |
| `ZFA:0000747` | epaxial region somite 30 | `ZFA:0001477` | — | yes |
| `ZFA:0000873` | epaxial region somite 4 | `ZFA:0001477` | — | yes |
| `ZFA:0000740` | epaxial region somite 5 | `ZFA:0001477` | — | yes |
| `ZFA:0000748` | epaxial region somite 6 | `ZFA:0001477` | — | yes |
| `ZFA:0000874` | epaxial region somite 7 | `ZFA:0001477` | — | yes |
| `ZFA:0000751` | epaxial region somite 8 | `ZFA:0001477` | — | yes |
| `ZFA:0000749` | epaxial region somite 9 | `ZFA:0001477` | — | yes |
| `ZFA:0000349` | epaxialis | `ZFA:0001477` | — |  |
| `ZFA:0007061` | epibranchial field | `ZFA:0001477` | — | yes |
| `ZFA:0001555` | epibranchial ganglion | `ZFA:0001477` | — | yes |
| `ZFA:0005057` | epicardium | `ZFA:0001477` | — |  |
| `ZFA:0001180` | epidermal basal stratum | `ZFA:0001477` | — | yes |
| `ZFA:0001181` | epidermal intermediate stratum | `ZFA:0001477` | — | yes |
| `ZFA:0001703` | epidermal placode | `ZFA:0001477` | — | yes |
| `ZFA:0001179` | epidermal superficial stratum | `ZFA:0001477` | — | yes |
| `ZFA:0000105` | epidermis | `ZFA:0001477` | ectoderm | yes |
| `ZFA:0007004` | epiphyseal cluster | `ZFA:0001477` | — |  |
| `ZFA:0001292` | epiphyseal stalk | `ZFA:0001477` | — |  |
| `ZFA:0001486` | epithelium | `ZFA:0001477` | — | yes |
| `ZFA:0005267` | erector muscle | `ZFA:0001477` | — | yes |
| `ZFA:0001499` | esophageal epithelium | `ZFA:0001477` | — |  |
| `ZFA:0005763` | esophageal fat | `ZFA:0001477` | — | yes |
| `ZFA:0000415` | esophageal sphincter | `ZFA:0001477` | — | yes |
| `ZFA:0005785` | esophageal striated muscle | `ZFA:0001477` | — |  |
| `ZFA:0000352` | external cellular layer | `ZFA:0001477` | — |  |
| `ZFA:0005823` | external lateral dorsal muscle | `ZFA:0001477` | — |  |
| `ZFA:0000205` | external lateral ventral muscle | `ZFA:0001477` | — |  |
| `ZFA:0000510` | external levatores | `ZFA:0001477` | — | yes |
| `ZFA:0000662` | external pharyngoclavicularis | `ZFA:0001477` | — | yes |
| `ZFA:0000309` | external yolk syncytial layer | `ZFA:0001477` | — | yes |
| `ZFA:0001291` | facial ganglion | `ZFA:0001477` | — | yes |
| `ZFA:0000512` | facial lobe | `ZFA:0001477` | — |  |
| `ZFA:0005836` | facial lymphatic sprout | `ZFA:0001477` | — | yes |
| `ZFA:0000206` | facial nerve motor nucleus | `ZFA:0001477` | — |  |
| `ZFA:0000762` | facio-acoustic neural crest | `ZFA:0001477` | — | yes |
| `ZFA:0005260` | fenestrated blood vessel endothelium | `ZFA:0001477` | — | yes |
| `ZFA:0005940` | fibrocartilaginous callus | `ZFA:0001477` | — | yes |
| `ZFA:0005271` | flexor muscle | `ZFA:0001477` | — | yes |
| `ZFA:0007071` | flexural organ | `ZFA:0001477` | — |  |
| `ZFA:0007026` | forebrain neural keel | `ZFA:0001477` | — | yes |
| `ZFA:0007018` | forebrain neural plate | `ZFA:0001477` | — | yes |
| `ZFA:0007034` | forebrain neural rod | `ZFA:0001477` | — | yes |
| `ZFA:0007041` | forebrain neural tube | `ZFA:0001477` | — | yes |
| `ZFA:0000190` | ganglion | `ZFA:0001477` | — |  |
| `ZFA:0000210` | gigantocellular part of magnocellular preoptic nucleus | `ZFA:0001477` | — |  |
| `ZFA:0000667` | gill filament | `ZFA:0001477` | — |  |
| `ZFA:0005284` | glomerular capillary | `ZFA:0001477` | — |  |
| `ZFA:0001301` | glossopharyngeal ganglion | `ZFA:0001477` | — | yes |
| `ZFA:0007066` | glossopharyngeal neural crest | `ZFA:0001477` | — | yes |
| `ZFA:0001262` | gonad primordium | `ZFA:0001477` | — |  |
| `ZFA:0000358` | granular layer corpus cerebelli | `ZFA:0001477` | — |  |
| `ZFA:0000766` | granular layer valvula cerebelli | `ZFA:0001477` | — |  |
| `ZFA:0001112` | granulosa cell layer | `ZFA:0001477` | — |  |
| `ZFA:0000518` | griseum centrale | `ZFA:0001477` | — |  |
| `ZFA:0005868` | griseum tectale | `ZFA:0001477` | — |  |
| `ZFA:0005123` | gut epithelium | `ZFA:0001477` | — |  |
| `ZFA:0000113` | head mesenchyme | `ZFA:0001477` | — | yes |
| `ZFA:0001652` | head muscle | `ZFA:0001477` | — |  |
| `ZFA:0000028` | heart primordium | `ZFA:0001477` | — |  |
| `ZFA:0000115` | heart rudiment | `ZFA:0001477` | — |  |
| `ZFA:0007029` | hindbrain neural keel | `ZFA:0001477` | — | yes |
| `ZFA:0007022` | hindbrain neural plate | `ZFA:0001477` | — | yes |
| `ZFA:0007036` | hindbrain neural rod | `ZFA:0001477` | — | yes |
| `ZFA:0007043` | hindbrain neural tube | `ZFA:0001477` | — | yes |
| `ZFA:0001658` | hindbrain nucleus | `ZFA:0001477` | — |  |
| `ZFA:0007052` | hyohyoideus | `ZFA:0001477` | — | yes |
| `ZFA:0000521` | hyoid muscle | `ZFA:0001477` | — |  |
| `ZFA:0007065` | hyoid neural crest | `ZFA:0001477` | — | yes |
| `ZFA:0005397` | hyoideomandibular nerve | `ZFA:0001477` | — |  |
| `ZFA:0001085` | hypaxial myotome region | `ZFA:0001477` | — |  |
| `ZFA:0000891` | hypaxial region somite 1 | `ZFA:0001477` | — | yes |
| `ZFA:0000925` | hypaxial region somite 10 | `ZFA:0001477` | — | yes |
| `ZFA:0000767` | hypaxial region somite 11 | `ZFA:0001477` | — | yes |
| `ZFA:0000892` | hypaxial region somite 12 | `ZFA:0001477` | — | yes |
| `ZFA:0000937` | hypaxial region somite 13 | `ZFA:0001477` | — | yes |
| `ZFA:0000768` | hypaxial region somite 14 | `ZFA:0001477` | — | yes |
| `ZFA:0000894` | hypaxial region somite 15 | `ZFA:0001477` | — | yes |
| `ZFA:0000946` | hypaxial region somite 16 | `ZFA:0001477` | — | yes |
| `ZFA:0000769` | hypaxial region somite 17 | `ZFA:0001477` | — | yes |
| `ZFA:0000895` | hypaxial region somite 18 | `ZFA:0001477` | — | yes |
| `ZFA:0000957` | hypaxial region somite 19 | `ZFA:0001477` | — | yes |
| `ZFA:0000770` | hypaxial region somite 2 | `ZFA:0001477` | — | yes |
| `ZFA:0000896` | hypaxial region somite 20 | `ZFA:0001477` | — | yes |
| `ZFA:0000968` | hypaxial region somite 21 | `ZFA:0001477` | — | yes |
| `ZFA:0000771` | hypaxial region somite 22 | `ZFA:0001477` | — | yes |
| `ZFA:0000897` | hypaxial region somite 23 | `ZFA:0001477` | — | yes |
| `ZFA:0000979` | hypaxial region somite 24 | `ZFA:0001477` | — | yes |
| `ZFA:0000772` | hypaxial region somite 25 | `ZFA:0001477` | — | yes |
| `ZFA:0000898` | hypaxial region somite 26 | `ZFA:0001477` | — | yes |
| `ZFA:0000986` | hypaxial region somite 27 | `ZFA:0001477` | — | yes |
| `ZFA:0000774` | hypaxial region somite 28 | `ZFA:0001477` | — | yes |
| `ZFA:0000899` | hypaxial region somite 29 | `ZFA:0001477` | — | yes |
| `ZFA:0000987` | hypaxial region somite 3 | `ZFA:0001477` | — | yes |
| `ZFA:0000775` | hypaxial region somite 30 | `ZFA:0001477` | — | yes |
| `ZFA:0000900` | hypaxial region somite 4 | `ZFA:0001477` | — | yes |
| `ZFA:0000988` | hypaxial region somite 5 | `ZFA:0001477` | — | yes |
| `ZFA:0000776` | hypaxial region somite 6 | `ZFA:0001477` | — | yes |
| `ZFA:0000901` | hypaxial region somite 7 | `ZFA:0001477` | — | yes |
| `ZFA:0000989` | hypaxial region somite 8 | `ZFA:0001477` | — | yes |
| `ZFA:0000777` | hypaxial region somite 9 | `ZFA:0001477` | — | yes |
| `ZFA:0000362` | hypaxialis | `ZFA:0001477` | — |  |
| `ZFA:0000031` | hypochord | `ZFA:0001477` | — | yes |
| `ZFA:0001136` | hypodermis | `ZFA:0001477` | — | yes |
| `ZFA:0005790` | hypophyseal capillary | `ZFA:0001477` | — |  |
| `ZFA:0000902` | hypural muscle | `ZFA:0001477` | — |  |
| `ZFA:0001096` | immature anterior macula | `ZFA:0001477` | — | yes |
| `ZFA:0001095` | immature macula | `ZFA:0001477` | — | yes |
| `ZFA:0001097` | immature posterior macula | `ZFA:0001477` | — | yes |
| `ZFA:0005780` | immature thymic epithelium | `ZFA:0001477` | — |  |
| `ZFA:0005276` | inclinator muscle | `ZFA:0001477` | — | yes |
| `ZFA:0000341` | inferior caudal dorsal flexor | `ZFA:0001477` | — |  |
| `ZFA:0000269` | inferior caudal ventral flexor | `ZFA:0001477` | — |  |
| `ZFA:0000522` | inferior hyohyoid | `ZFA:0001477` | — | yes |
| `ZFA:0000215` | inferior olive | `ZFA:0001477` | — |  |
| `ZFA:0000366` | inferior raphe nucleus | `ZFA:0001477` | — |  |
| `ZFA:0000523` | inferior reticular formation | `ZFA:0001477` | — |  |
| `ZFA:0000216` | infracarinalis | `ZFA:0001477` | — |  |
| `ZFA:0000524` | infraorbital lateral line | `ZFA:0001477` | — |  |
| `ZFA:0005136` | inner dental epithelium | `ZFA:0001477` | — | yes |
| `ZFA:0005637` | intercostal ligament | `ZFA:0001477` | — | yes |
| `ZFA:0007051` | interhyoideus | `ZFA:0001477` | — | yes |
| `ZFA:0000369` | intermandibularis | `ZFA:0001477` | — | yes |
| `ZFA:0000033` | intermediate cell mass of mesoderm | `ZFA:0001477` | — |  |
| `ZFA:0000990` | intermediate mesenchyme | `ZFA:0001477` | — | yes |
| `ZFA:0001206` | intermediate mesoderm | `ZFA:0001477` | — | yes |
| `ZFA:0000219` | intermediate reticular formation | `ZFA:0001477` | — |  |
| `ZFA:0000573` | internal cellular layer | `ZFA:0001477` | — |  |
| `ZFA:0001107` | internal gill bud | `ZFA:0001477` | — |  |
| `ZFA:0000221` | internal levator | `ZFA:0001477` | — | yes |
| `ZFA:0000371` | internal pharyngoclavicularis | `ZFA:0001477` | — | yes |
| `ZFA:0000712` | internal yolk syncytial layer | `ZFA:0001477` | — | yes |
| `ZFA:0005501` | interopercular-mandibular ligament | `ZFA:0001477` | — | yes |
| `ZFA:0005636` | interossicular ligament | `ZFA:0001477` | — |  |
| `ZFA:0000372` | interpeduncular nucleus medulla oblongata | `ZFA:0001477` | — |  |
| `ZFA:0000903` | interpeduncular nucleus tegmentum | `ZFA:0001477` | — |  |
| `ZFA:0000528` | interradialis caudalis | `ZFA:0001477` | — |  |
| `ZFA:0005802` | interrenal  angiogenic sprout | `ZFA:0001477` | — |  |
| `ZFA:0007119` | intervertebral ligament | `ZFA:0001477` | — |  |
| `ZFA:0005256` | intervillus pockets | `ZFA:0001477` | — |  |
| `ZFA:0005126` | intestinal bulb epithelium | `ZFA:0001477` | — |  |
| `ZFA:0005738` | intestinal bulb primordium | `ZFA:0001477` | endoderm | yes |
| `ZFA:0005124` | intestinal epithelium | `ZFA:0001477` | — |  |
| `ZFA:0005273` | intestinal mucosal muscle | `ZFA:0001477` | — |  |
| `ZFA:0005125` | intestinal villus | `ZFA:0001477` | — |  |
| `ZFA:0005915` | iris melanophore layer | `ZFA:0001477` | — |  |
| `ZFA:0005569` | iris stroma | `ZFA:0001477` | — |  |
| `ZFA:0005755` | islet | `ZFA:0001477` | — |  |
| `ZFA:0000222` | isthmic primary nucleus | `ZFA:0001477` | — | yes |
| `ZFA:0000166` | lateral crista | `ZFA:0001477` | — | yes |
| `ZFA:0000225` | lateral crista primordium | `ZFA:0001477` | — | yes |
| `ZFA:0005502` | lateral ethmoid-autopalatine ligament | `ZFA:0001477` | — | yes |
| `ZFA:0005503` | lateral ethmoid-ectopterygoid ligament | `ZFA:0001477` | — | yes |
| `ZFA:0001256` | lateral floor plate | `ZFA:0001477` | — |  |
| `ZFA:0000380` | lateral lemniscus nucleus | `ZFA:0001477` | — |  |
| `ZFA:0001469` | lateral line | `ZFA:0001477` | — |  |
| `ZFA:0000120` | lateral line ganglion | `ZFA:0001477` | — |  |
| `ZFA:0001479` | lateral line nerve | `ZFA:0001477` | — |  |
| `ZFA:0000228` | lateral line primordium | `ZFA:0001477` | — |  |
| `ZFA:0000381` | lateral line sensory nucleus | `ZFA:0001477` | — |  |
| `ZFA:0000905` | lateral mesenchyme derived from mesoderm | `ZFA:0001477` | — | yes |
| `ZFA:0001065` | lateral mesoderm | `ZFA:0001477` | — | yes |
| `ZFA:0000992` | lateral migration pathway mesenchyme | `ZFA:0001477` | — | yes |
| `ZFA:0000176` | lateral nucleus of ventral telencephalon | `ZFA:0001477` | — | yes |
| `ZFA:0000121` | lateral plate mesoderm | `ZFA:0001477` | — | yes |
| `ZFA:0000383` | lateral rectus | `ZFA:0001477` | — |  |
| `ZFA:0000535` | lateral reticular nucleus | `ZFA:0001477` | — |  |
| `ZFA:0005664` | lateral spinal nerve | `ZFA:0001477` | — | yes |
| `ZFA:0000993` | lateral wall neural rod | `ZFA:0001477` | — | yes |
| `ZFA:0001435` | lateral wall neural tube | `ZFA:0001477` | — | yes |
| `ZFA:0000536` | lateral zone of dorsal telencephalon | `ZFA:0001477` | — |  |
| `ZFA:0000035` | lens | `ZFA:0001477` | — |  |
| `ZFA:0001326` | lens epithelium | `ZFA:0001477` | — |  |
| `ZFA:0000122` | lens placode | `ZFA:0001477` | — | yes |
| `ZFA:0000384` | levator arcus palatini | `ZFA:0001477` | — | yes |
| `ZFA:0000537` | levator operculi | `ZFA:0001477` | — | yes |
| `ZFA:0001675` | ligament | `ZFA:0001477` | — | yes |
| `ZFA:0005334` | lip epithelium | `ZFA:0001477` | — |  |
| `ZFA:0000539` | locus coeruleus | `ZFA:0001477` | — |  |
| `ZFA:0000230` | longitudinal hypochordal | `ZFA:0001477` | — |  |
| `ZFA:0000233` | lower oral valve | `ZFA:0001477` | — | yes |
| `ZFA:0005258` | lymph vessel endothelium | `ZFA:0001477` | — |  |
| `ZFA:0005605` | lymphangioblast cord | `ZFA:0001477` | — | yes |
| `ZFA:0005603` | lymphangiogenic sprout | `ZFA:0001477` | — | yes |
| `ZFA:0005252` | lymphatic capillary | `ZFA:0001477` | — |  |
| `ZFA:0000386` | macula | `ZFA:0001477` | — |  |
| `ZFA:0001671` | macula communis | `ZFA:0001477` | — |  |
| `ZFA:0000116` | macula lagena | `ZFA:0001477` | — |  |
| `ZFA:0000234` | macula neglecta | `ZFA:0001477` | — |  |
| `ZFA:0007000` | macula saccule | `ZFA:0001477` | — |  |
| `ZFA:0000030` | macula utricle | `ZFA:0001477` | — |  |
| `ZFA:0000540` | magnocellular octaval nucleus | `ZFA:0001477` | — | yes |
| `ZFA:0005764` | mandibular fat | `ZFA:0001477` | — |  |
| `ZFA:0000259` | mandibular lateral line | `ZFA:0001477` | — |  |
| `ZFA:0000236` | mandibular muscle | `ZFA:0001477` | — |  |
| `ZFA:0007064` | mandibular neural crest | `ZFA:0001477` | — | yes |
| `ZFA:0005641` | maxillo-mandibular ligament | `ZFA:0001477` | — | yes |
| `ZFA:0005642` | maxillo-rostroid ligament | `ZFA:0001477` | — | yes |
| `ZFA:0001257` | medial floor plate | `ZFA:0001477` | — |  |
| `ZFA:0000389` | medial funicular nucleus medulla oblongata | `ZFA:0001477` | — |  |
| `ZFA:0000997` | medial funicular nucleus trigeminal nucleus | `ZFA:0001477` | — | yes |
| `ZFA:0000786` | medial migration pathway mesenchyme | `ZFA:0001477` | — | yes |
| `ZFA:0001696` | medial motor nucleus of vagal nerve | `ZFA:0001477` | — | yes |
| `ZFA:0000291` | medial octavolateralis nucleus | `ZFA:0001477` | — |  |
| `ZFA:0000301` | medial rectus | `ZFA:0001477` | — |  |
| `ZFA:0000391` | medial zone of dorsal telencephalon | `ZFA:0001477` | — |  |
| `ZFA:0000312` | mesencephalic nucleus of trigeminal nerve | `ZFA:0001477` | — | yes |
| `ZFA:0000393` | mesenchyme | `ZFA:0001477` | — | yes |
| `ZFA:0000998` | mesenchyme derived from head mesoderm | `ZFA:0001477` | — | yes |
| `ZFA:0000787` | mesenchyme derived from head neural crest | `ZFA:0001477` | — | yes |
| `ZFA:0000999` | mesenchyme derived from trunk neural crest | `ZFA:0001477` | — | yes |
| `ZFA:0000788` | mesenchyme dorsal fin | `ZFA:0001477` | — | yes |
| `ZFA:0000912` | mesenchyme median fin fold | `ZFA:0001477` | — | yes |
| `ZFA:0001000` | mesenchyme pectoral fin | `ZFA:0001477` | — | yes |
| `ZFA:0001449` | mesenchyme pelvic fin | `ZFA:0001477` | — | yes |
| `ZFA:0005129` | mesentery | `ZFA:0001477` | — | yes |
| `ZFA:0000041` | mesoderm | `ZFA:0001477` | mesoderm | yes |
| `ZFA:0000789` | mesoderm pectoral fin bud | `ZFA:0001477` | — | yes |
| `ZFA:0001386` | mesoderm pelvic fin bud | `ZFA:0001477` | — | yes |
| `ZFA:0005251` | microcirculatory vessel | `ZFA:0001477` | — |  |
| `ZFA:0005757` | mid diencephalic organizer | `ZFA:0001477` | — |  |
| `ZFA:0005127` | mid intestine epithelium | `ZFA:0001477` | — |  |
| `ZFA:0007125` | midbrain hindbrain boundary constriction | `ZFA:0001477` | — |  |
| `ZFA:0007025` | midbrain neural keel | `ZFA:0001477` | — | yes |
| `ZFA:0007019` | midbrain neural plate | `ZFA:0001477` | — | yes |
| `ZFA:0007032` | midbrain neural rod | `ZFA:0001477` | — | yes |
| `ZFA:0007039` | midbrain neural tube | `ZFA:0001477` | — | yes |
| `ZFA:0001665` | midbrain nucleus | `ZFA:0001477` | — |  |
| `ZFA:0000344` | middle lateral line | `ZFA:0001477` | — |  |
| `ZFA:0001483` | middle lateral line ganglion | `ZFA:0001477` | — |  |
| `ZFA:0001482` | middle lateral line nerve | `ZFA:0001477` | — |  |
| `ZFA:0005118` | middle lateral line primordium | `ZFA:0001477` | — |  |
| `ZFA:0005924` | middle migratory muscle precursor stream | `ZFA:0001477` | — | yes |
| `ZFA:0007087` | migratory cranial neural crest | `ZFA:0001477` | — | yes |
| `ZFA:0005922` | migratory muscle precursor stream | `ZFA:0001477` | — | yes |
| `ZFA:0007085` | migratory neural crest | `ZFA:0001477` | — | yes |
| `ZFA:0007093` | migratory trunk neural crest | `ZFA:0001477` | — | yes |
| `ZFA:0000394` | molecular layer corpus cerebelli | `ZFA:0001477` | — |  |
| `ZFA:0000913` | molecular layer valvula cerebelli | `ZFA:0001477` | — |  |
| `ZFA:0001710` | mossy fiber | `ZFA:0001477` | — |  |
| `ZFA:0000387` | motor nucleus of vagal nerve | `ZFA:0001477` | — |  |
| `ZFA:0001494` | multilaminar epithelium | `ZFA:0001477` | — | yes |
| `ZFA:0005145` | muscle | `ZFA:0001477` | — |  |
| `ZFA:0005490` | myocardial precursor | `ZFA:0001477` | — |  |
| `ZFA:0001319` | myocardium | `ZFA:0001477` | — |  |
| `ZFA:0001056` | myotome | `ZFA:0001477` | — |  |
| `ZFA:0000924` | myotome somite 1 | `ZFA:0001477` | — | yes |
| `ZFA:0001013` | myotome somite 10 | `ZFA:0001477` | — | yes |
| `ZFA:0000801` | myotome somite 11 | `ZFA:0001477` | — | yes |
| `ZFA:0000926` | myotome somite 12 | `ZFA:0001477` | — | yes |
| `ZFA:0001014` | myotome somite 13 | `ZFA:0001477` | — | yes |
| `ZFA:0000044` | myotome somite 14 | `ZFA:0001477` | — | yes |
| `ZFA:0000802` | myotome somite 15 | `ZFA:0001477` | — | yes |
| `ZFA:0000927` | myotome somite 16 | `ZFA:0001477` | — | yes |
| `ZFA:0001015` | myotome somite 17 | `ZFA:0001477` | — | yes |
| `ZFA:0000803` | myotome somite 18 | `ZFA:0001477` | — | yes |
| `ZFA:0000928` | myotome somite 19 | `ZFA:0001477` | — | yes |
| `ZFA:0001016` | myotome somite 2 | `ZFA:0001477` | — | yes |
| `ZFA:0000804` | myotome somite 20 | `ZFA:0001477` | — | yes |
| `ZFA:0000929` | myotome somite 21 | `ZFA:0001477` | — | yes |
| `ZFA:0001017` | myotome somite 22 | `ZFA:0001477` | — | yes |
| `ZFA:0000805` | myotome somite 23 | `ZFA:0001477` | — | yes |
| `ZFA:0000930` | myotome somite 24 | `ZFA:0001477` | — | yes |
| `ZFA:0001018` | myotome somite 25 | `ZFA:0001477` | — | yes |
| `ZFA:0000807` | myotome somite 26 | `ZFA:0001477` | — | yes |
| `ZFA:0000931` | myotome somite 27 | `ZFA:0001477` | — | yes |
| `ZFA:0001019` | myotome somite 28 | `ZFA:0001477` | — | yes |
| `ZFA:0000808` | myotome somite 29 | `ZFA:0001477` | — | yes |
| `ZFA:0000932` | myotome somite 3 | `ZFA:0001477` | — | yes |
| `ZFA:0001020` | myotome somite 30 | `ZFA:0001477` | — | yes |
| `ZFA:0000809` | myotome somite 4 | `ZFA:0001477` | — | yes |
| `ZFA:0000933` | myotome somite 5 | `ZFA:0001477` | — | yes |
| `ZFA:0001021` | myotome somite 6 | `ZFA:0001477` | — | yes |
| `ZFA:0000810` | myotome somite 7 | `ZFA:0001477` | — | yes |
| `ZFA:0000934` | myotome somite 8 | `ZFA:0001477` | — | yes |
| `ZFA:0001022` | myotome somite 9 | `ZFA:0001477` | — | yes |
| `ZFA:0005587` | nephron progenitor | `ZFA:0001477` | — |  |
| `ZFA:0007009` | nerve | `ZFA:0001477` | — |  |
| `ZFA:0000045` | neural crest | `ZFA:0001477` | — | yes |
| `ZFA:0000811` | neural crest diencephalon | `ZFA:0001477` | — | yes |
| `ZFA:0007063` | neural crest hindbrain | `ZFA:0001477` | — | yes |
| `ZFA:0000935` | neural crest midbrain | `ZFA:0001477` | — | yes |
| `ZFA:0000812` | neural crest telencephalon | `ZFA:0001477` | — | yes |
| `ZFA:0000131` | neural keel | `ZFA:0001477` | — | yes |
| `ZFA:0000132` | neural plate | `ZFA:0001477` | — | yes |
| `ZFA:0007082` | neural plate border | `ZFA:0001477` | — | yes |
| `ZFA:0000133` | neural rod | `ZFA:0001477` | — | yes |
| `ZFA:0001135` | neural tube | `ZFA:0001477` | — | yes |
| `ZFA:0001120` | neuroectoderm | `ZFA:0001477` | — | yes |
| `ZFA:0007059` | neurogenic field | `ZFA:0001477` | — | yes |
| `ZFA:0005043` | nevus | `ZFA:0001477` | — | yes |
| `ZFA:0001178` | non neural ectoderm | `ZFA:0001477` | — | yes |
| `ZFA:0001126` | noninvoluting endocytic marginal cell cluster | `ZFA:0001477` | — | yes |
| `ZFA:0000135` | notochord | `ZFA:0001477` | — | yes |
| `ZFA:0001670` | notochord posterior region | `ZFA:0001477` | — |  |
| `ZFA:0000244` | nucleus Edinger-Westphal | `ZFA:0001477` | — |  |
| `ZFA:0000398` | nucleus isthmi | `ZFA:0001477` | — |  |
| `ZFA:0000551` | nucleus lateralis valvulae | `ZFA:0001477` | — |  |
| `ZFA:0000245` | nucleus of the descending root | `ZFA:0001477` | — | yes |
| `ZFA:0000815` | nucleus of the medial longitudinal fasciculus medulla oblongata | `ZFA:0001477` | — |  |
| `ZFA:0001339` | nucleus of the tract of the anterior commissure | `ZFA:0001477` | — | yes |
| `ZFA:0000552` | nucleus ruber | `ZFA:0001477` | — |  |
| `ZFA:0000246` | nucleus taeniae | `ZFA:0001477` | — |  |
| `ZFA:0000400` | occipital lateral line | `ZFA:0001477` | — |  |
| `ZFA:0001697` | octaval nerve motor nucleus | `ZFA:0001477` | — |  |
| `ZFA:0000401` | octaval nerve sensory nucleus | `ZFA:0001477` | — |  |
| `ZFA:0000553` | oculomotor nucleus | `ZFA:0001477` | — |  |
| `ZFA:0005623` | odontoid tissue | `ZFA:0001477` | — | yes |
| `ZFA:0000554` | olfactory epithelium | `ZFA:0001477` | — |  |
| `ZFA:0007062` | olfactory field | `ZFA:0001477` | — | yes |
| `ZFA:0001428` | olfactory rosette | `ZFA:0001477` | — |  |
| `ZFA:0000424` | opercular lateral line | `ZFA:0001477` | — |  |
| `ZFA:0005885` | operculohyoid ligament | `ZFA:0001477` | — | yes |
| `ZFA:0005229` | optic choroid | `ZFA:0001477` | — |  |
| `ZFA:0001619` | optic fiber layer | `ZFA:0001477` | — |  |
| `ZFA:0001625` | optic nerve head | `ZFA:0001477` | — |  |
| `ZFA:0000570` | optic primordium | `ZFA:0001477` | — | yes |
| `ZFA:0000137` | optic stalk | `ZFA:0001477` | — |  |
| `ZFA:0000050` | optic vesicle | `ZFA:0001477` | — | yes |
| `ZFA:0005463` | oral ectoderm | `ZFA:0001477` | — | yes |
| `ZFA:0000816` | oral epithelium | `ZFA:0001477` | — | yes |
| `ZFA:0001125` | organizer inducing center | `ZFA:0001477` | — | yes |
| `ZFA:0007068` | otic epithelium | `ZFA:0001477` | — | yes |
| `ZFA:0000464` | otic lateral line | `ZFA:0001477` | — |  |
| `ZFA:0007070` | otic sensory epithelium | `ZFA:0001477` | — | yes |
| `ZFA:0007069` | otic squamous epithelium | `ZFA:0001477` | — | yes |
| `ZFA:0000469` | otic vesicle anterior protrusion | `ZFA:0001477` | — | yes |
| `ZFA:0000232` | otic vesicle lateral protrusion | `ZFA:0001477` | — | yes |
| `ZFA:0000412` | otic vesicle posterior protrusion | `ZFA:0001477` | — | yes |
| `ZFA:0001715` | otic vesicle protrusion | `ZFA:0001477` | — | yes |
| `ZFA:0001716` | otic vesicle ventral protrusion | `ZFA:0001477` | — | yes |
| `ZFA:0005137` | outer dental epithelium | `ZFA:0001477` | — | yes |
| `ZFA:0005741` | pancreatic acinar gland | `ZFA:0001477` | — |  |
| `ZFA:0005758` | pancreatic fat | `ZFA:0001477` | — |  |
| `ZFA:0001713` | parallel fiber | `ZFA:0001477` | — |  |
| `ZFA:0000255` | paraxial mesoderm | `ZFA:0001477` | — | yes |
| `ZFA:0001195` | pars anterior | `ZFA:0001477` | — |  |
| `ZFA:0001197` | pars intermedia | `ZFA:0001477` | — |  |
| `ZFA:0000256` | pars subcommissuralis of ventral telencephalon | `ZFA:0001477` | — |  |
| `ZFA:0005809` | pectinate muscle | `ZFA:0001477` | — |  |
| `ZFA:0005437` | pectoral fin motor nerve | `ZFA:0001477` | — | yes |
| `ZFA:0005439` | pectoral fin motor nerve 1 | `ZFA:0001477` | — | yes |
| `ZFA:0005440` | pectoral fin motor nerve 2 | `ZFA:0001477` | — | yes |
| `ZFA:0005441` | pectoral fin motor nerve 3 | `ZFA:0001477` | — | yes |
| `ZFA:0005450` | pectoral fin motor nerve 4 | `ZFA:0001477` | — | yes |
| `ZFA:0005436` | pectoral fin nerve | `ZFA:0001477` | — | yes |
| `ZFA:0005766` | pectoral fin plate fat | `ZFA:0001477` | — | yes |
| `ZFA:0005438` | pectoral fin sensory nerve | `ZFA:0001477` | — | yes |
| `ZFA:0005863` | pectoral protractor | `ZFA:0001477` | — |  |
| `ZFA:0000564` | pelvic abductor profundus | `ZFA:0001477` | — |  |
| `ZFA:0000497` | pelvic adductor profundus | `ZFA:0001477` | — |  |
| `ZFA:0001454` | pelvic fin field | `ZFA:0001477` | — | yes |
| `ZFA:0005765` | pericardial fat | `ZFA:0001477` | — | yes |
| `ZFA:0001653` | pericardial muscle | `ZFA:0001477` | — |  |
| `ZFA:0001634` | perichondrium | `ZFA:0001477` | — | yes |
| `ZFA:0001633` | perichordal connective tissue | `ZFA:0001477` | — | yes |
| `ZFA:0001185` | periderm | `ZFA:0001477` | — | yes |
| `ZFA:0005572` | periocular mesenchyme | `ZFA:0001477` | — | yes |
| `ZFA:0005761` | periorbital fat | `ZFA:0001477` | — |  |
| `ZFA:0001667` | peripheral nucleus of ventral telencephalon | `ZFA:0001477` | — |  |
| `ZFA:0001666` | periventricular nucleus of ventral telencephalon | `ZFA:0001477` | — |  |
| `ZFA:0001379` | pharyngeal ectoderm | `ZFA:0001477` | — |  |
| `ZFA:0001104` | pharyngeal endoderm | `ZFA:0001477` | — |  |
| `ZFA:0001174` | pharyngeal epithelium | `ZFA:0001477` | — |  |
| `ZFA:0001467` | pharyngeal mesoderm | `ZFA:0001477` | — |  |
| `ZFA:0000261` | pharyngohyoid | `ZFA:0001477` | — | yes |
| `ZFA:0001465` | photoreceptor inner segment layer | `ZFA:0001477` | — |  |
| `ZFA:0001466` | photoreceptor outer segment layer | `ZFA:0001477` | — |  |
| `ZFA:0007054` | pillar of the anterior semicircular canal | `ZFA:0001477` | — | yes |
| `ZFA:0007055` | pillar of the lateral semicircular canal | `ZFA:0001477` | — | yes |
| `ZFA:0007056` | pillar of the posterior semicircular canal | `ZFA:0001477` | — | yes |
| `ZFA:0001717` | pillar of the semicircular canal | `ZFA:0001477` | — |  |
| `ZFA:0001632` | portion of connective tissue | `ZFA:0001477` | — | yes |
| `ZFA:0001477` | portion of tissue | `ZFA:0001477` | — | yes |
| `ZFA:0000819` | postcommissural nucleus of ventral telencephalon | `ZFA:0001477` | — | yes |
| `ZFA:0000566` | posterior crista | `ZFA:0001477` | — | yes |
| `ZFA:0000411` | posterior crista primordium | `ZFA:0001477` | — | yes |
| `ZFA:0005926` | posterior hypaxial muscle | `ZFA:0001477` | — | yes |
| `ZFA:0005128` | posterior intestine epithelium | `ZFA:0001477` | — |  |
| `ZFA:0000944` | posterior lateral line | `ZFA:0001477` | — |  |
| `ZFA:0001314` | posterior lateral line ganglion | `ZFA:0001477` | — | yes |
| `ZFA:0000175` | posterior lateral line nerve | `ZFA:0001477` | — |  |
| `ZFA:0001157` | posterior lateral line primordium | `ZFA:0001477` | — |  |
| `ZFA:0005040` | posterior lateral mesoderm | `ZFA:0001477` | — | yes |
| `ZFA:0005042` | posterior lateral plate mesoderm | `ZFA:0001477` | — | yes |
| `ZFA:0000558` | posterior macula | `ZFA:0001477` | — |  |
| `ZFA:0005925` | posterior migratory muscle precursor stream | `ZFA:0001477` | — | yes |
| `ZFA:0007023` | posterior neural keel | `ZFA:0001477` | — | yes |
| `ZFA:0007017` | posterior neural plate | `ZFA:0001477` | — | yes |
| `ZFA:0007030` | posterior neural rod | `ZFA:0001477` | — | yes |
| `ZFA:0007037` | posterior neural tube | `ZFA:0001477` | — | yes |
| `ZFA:0007015` | posterior presumptive neural plate | `ZFA:0001477` | — | yes |
| `ZFA:0000060` | prechordal plate | `ZFA:0001477` | — | yes |
| `ZFA:0005635` | predentine | `ZFA:0001477` | — | yes |
| `ZFA:0005265` | premaxillary-maxillary ligament | `ZFA:0001477` | — | yes |
| `ZFA:0005643` | premaxillo-rostroid ligament | `ZFA:0001477` | — | yes |
| `ZFA:0007088` | premigratory cranial neural crest | `ZFA:0001477` | — | yes |
| `ZFA:0007083` | premigratory neural crest | `ZFA:0001477` | — | yes |
| `ZFA:0007092` | premigratory trunk neural crest | `ZFA:0001477` | — | yes |
| `ZFA:0005646` | preopercle-retroarticular ligament | `ZFA:0001477` | — | yes |
| `ZFA:0007013` | preplacodal ectoderm | `ZFA:0001477` | — | yes |
| `ZFA:0001723` | presumptive atrioventricular canal | `ZFA:0001477` | — |  |
| `ZFA:0001712` | presumptive bulbus arteriosus | `ZFA:0001477` | — |  |
| `ZFA:0001724` | presumptive endocardium | `ZFA:0001477` | — |  |
| `ZFA:0001071` | presumptive neural retina | `ZFA:0001477` | — | yes |
| `ZFA:0000064` | presumptive retinal pigmented epithelium | `ZFA:0001477` | — | yes |
| `ZFA:0001722` | presumptive sinus venosus | `ZFA:0001477` | — |  |
| `ZFA:0005135` | primary dental epithelium | `ZFA:0001477` | — | yes |
| `ZFA:0001122` | primary germ layer | `ZFA:0001477` | — | yes |
| `ZFA:0005754` | primary islet | `ZFA:0001477` | — | yes |
| `ZFA:0000267` | primary olfactory fiber layer | `ZFA:0001477` | — |  |
| `ZFA:0005115` | primary posterior lateral line primordium | `ZFA:0001477` | — | yes |
| `ZFA:0001431` | primitive olfactory epithelium | `ZFA:0001477` | — |  |
| `ZFA:0005651` | primitive pectoral fin abductor | `ZFA:0001477` | — | yes |
| `ZFA:0005650` | primitive pectoral fin adductor | `ZFA:0001477` | — |  |
| `ZFA:0005264` | primordial ligament | `ZFA:0001477` | — | yes |
| `ZFA:0005076` | primordial vasculature | `ZFA:0001477` | — |  |
| `ZFA:0005808` | proepicardial cluster | `ZFA:0001477` | — |  |
| `ZFA:0005309` | pronephric glomerular capillary | `ZFA:0001477` | — |  |
| `ZFA:0005310` | pronephric glomerular capsule | `ZFA:0001477` | — |  |
| `ZFA:0005311` | pronephric glomerular capsule epithelium | `ZFA:0001477` | — |  |
| `ZFA:0000067` | pronephric mesoderm | `ZFA:0001477` | — | yes |
| `ZFA:0000612` | protractor hyoidei | `ZFA:0001477` | — | yes |
| `ZFA:0005581` | proximal pars anterior | `ZFA:0001477` | — |  |
| `ZFA:0005902` | pterygoid process | `ZFA:0001477` | — |  |
| `ZFA:0001706` | Purkinje cell layer corpus cerebelli | `ZFA:0001477` | — |  |
| `ZFA:0001709` | Purkinje cell layer valvula cerebelli | `ZFA:0001477` | — |  |
| `ZFA:0001429` | raphe nucleus | `ZFA:0001477` | — |  |
| `ZFA:0005147` | regenerating tissue | `ZFA:0001477` | — | yes |
| `ZFA:0001389` | regeneration epithelium | `ZFA:0001477` | — | yes |
| `ZFA:0005871` | region of the nucleus of the medial longitudinal fascicle | `ZFA:0001477` | — |  |
| `ZFA:0005906` | Reissner's fiber | `ZFA:0001477` | — |  |
| `ZFA:0005254` | renal glomerular capsule | `ZFA:0001477` | — |  |
| `ZFA:0005253` | renal glomerular capsule epithelium | `ZFA:0001477` | — |  |
| `ZFA:0005586` | renal vesicle | `ZFA:0001477` | — | yes |
| `ZFA:0000024` | retinal ganglion cell layer | `ZFA:0001477` | — |  |
| `ZFA:0000119` | retinal inner nuclear layer | `ZFA:0001477` | — |  |
| `ZFA:0001329` | retinal inner plexiform layer | `ZFA:0001477` | — |  |
| `ZFA:0000046` | retinal neural layer | `ZFA:0001477` | — |  |
| `ZFA:0001464` | retinal outer nuclear layer | `ZFA:0001477` | — |  |
| `ZFA:0001330` | retinal outer plexiform layer | `ZFA:0001477` | — |  |
| `ZFA:0000143` | retinal photoreceptor layer | `ZFA:0001477` | — |  |
| `ZFA:0000144` | retinal pigmented epithelium | `ZFA:0001477` | — |  |
| `ZFA:0005904` | retroarticular  process | `ZFA:0001477` | — |  |
| `ZFA:0001358` | roof plate diencephalic region | `ZFA:0001477` | — |  |
| `ZFA:0000355` | roof plate midbrain region | `ZFA:0001477` | — |  |
| `ZFA:0001436` | roof plate neural tube region | `ZFA:0001477` | — |  |
| `ZFA:0001033` | roof plate rhombomere 1 | `ZFA:0001477` | — |  |
| `ZFA:0000824` | roof plate rhombomere 2 | `ZFA:0001477` | — |  |
| `ZFA:0000950` | roof plate rhombomere 3 | `ZFA:0001477` | — |  |
| `ZFA:0001034` | roof plate rhombomere 4 | `ZFA:0001477` | — |  |
| `ZFA:0000828` | roof plate rhombomere 5 | `ZFA:0001477` | — |  |
| `ZFA:0000825` | roof plate rhombomere 6 | `ZFA:0001477` | — |  |
| `ZFA:0000951` | roof plate rhombomere 7 | `ZFA:0001477` | — |  |
| `ZFA:0001035` | roof plate rhombomere 8 | `ZFA:0001477` | — |  |
| `ZFA:0001311` | roof plate rhombomere region | `ZFA:0001477` | — |  |
| `ZFA:0001177` | roof plate spinal cord region | `ZFA:0001477` | — |  |
| `ZFA:0005029` | rostral blood island | `ZFA:0001477` | — |  |
| `ZFA:0000654` | rostral motor nucleus | `ZFA:0001477` | — | yes |
| `ZFA:0001698` | rostral octaval nerve motor nucleus | `ZFA:0001477` | — | yes |
| `ZFA:0000274` | rostral octaval nucleus | `ZFA:0001477` | — | yes |
| `ZFA:0005580` | rostral pars anterior | `ZFA:0001477` | — |  |
| `ZFA:0000665` | rostral root of abducens nerve | `ZFA:0001477` | — |  |
| `ZFA:0000275` | rostral tegmental nucleus | `ZFA:0001477` | — |  |
| `ZFA:0000582` | saccus dorsalis | `ZFA:0001477` | — |  |
| `ZFA:0001704` | scale primordium | `ZFA:0001477` | — | yes |
| `ZFA:0005638` | scapulo-vertebral ligament | `ZFA:0001477` | — | yes |
| `ZFA:0001080` | sclerotome | `ZFA:0001477` | — | yes |
| `ZFA:0000952` | sclerotome somite 1 | `ZFA:0001477` | — | yes |
| `ZFA:0001036` | sclerotome somite 10 | `ZFA:0001477` | — | yes |
| `ZFA:0000829` | sclerotome somite 11 | `ZFA:0001477` | — | yes |
| `ZFA:0000953` | sclerotome somite 12 | `ZFA:0001477` | — | yes |
| `ZFA:0001037` | sclerotome somite 13 | `ZFA:0001477` | — | yes |
| `ZFA:0000830` | sclerotome somite 14 | `ZFA:0001477` | — | yes |
| `ZFA:0000954` | sclerotome somite 15 | `ZFA:0001477` | — | yes |
| `ZFA:0001038` | sclerotome somite 16 | `ZFA:0001477` | — | yes |
| `ZFA:0000831` | sclerotome somite 17 | `ZFA:0001477` | — | yes |
| `ZFA:0000955` | sclerotome somite 18 | `ZFA:0001477` | — | yes |
| `ZFA:0001039` | sclerotome somite 19 | `ZFA:0001477` | — | yes |
| `ZFA:0000832` | sclerotome somite 2 | `ZFA:0001477` | — | yes |
| `ZFA:0000956` | sclerotome somite 20 | `ZFA:0001477` | — | yes |
| `ZFA:0001041` | sclerotome somite 21 | `ZFA:0001477` | — | yes |
| `ZFA:0000833` | sclerotome somite 22 | `ZFA:0001477` | — | yes |
| `ZFA:0000958` | sclerotome somite 23 | `ZFA:0001477` | — | yes |
| `ZFA:0001042` | sclerotome somite 24 | `ZFA:0001477` | — | yes |
| `ZFA:0000834` | sclerotome somite 25 | `ZFA:0001477` | — | yes |
| `ZFA:0000959` | sclerotome somite 26 | `ZFA:0001477` | — | yes |
| `ZFA:0001043` | sclerotome somite 27 | `ZFA:0001477` | — | yes |
| `ZFA:0000835` | sclerotome somite 28 | `ZFA:0001477` | — | yes |
| `ZFA:0000960` | sclerotome somite 29 | `ZFA:0001477` | — | yes |
| `ZFA:0001044` | sclerotome somite 3 | `ZFA:0001477` | — | yes |
| `ZFA:0000836` | sclerotome somite 30 | `ZFA:0001477` | — | yes |
| `ZFA:0000961` | sclerotome somite 4 | `ZFA:0001477` | — | yes |
| `ZFA:0001045` | sclerotome somite 5 | `ZFA:0001477` | — | yes |
| `ZFA:0000837` | sclerotome somite 6 | `ZFA:0001477` | — | yes |
| `ZFA:0000962` | sclerotome somite 7 | `ZFA:0001477` | — | yes |
| `ZFA:0001046` | sclerotome somite 8 | `ZFA:0001477` | — | yes |
| `ZFA:0000839` | sclerotome somite 9 | `ZFA:0001477` | — | yes |
| `ZFA:0005794` | second tier layer of breeding tubercle | `ZFA:0001477` | — | yes |
| `ZFA:0000278` | secondary gustatory nucleus medulla oblongata | `ZFA:0001477` | — |  |
| `ZFA:0000399` | secondary gustatory nucleus trigeminal nucleus | `ZFA:0001477` | — |  |
| `ZFA:0005756` | secondary islet | `ZFA:0001477` | — | yes |
| `ZFA:0005116` | secondary posterior lateral line primordium | `ZFA:0001477` | — | yes |
| `ZFA:0000279` | segmental plate | `ZFA:0001477` | — | yes |
| `ZFA:0005880` | seminiferous epithelium | `ZFA:0001477` | — |  |
| `ZFA:0000679` | sensory root of facial nerve | `ZFA:0001477` | — |  |
| `ZFA:0000433` | sensory trigeminal nucleus | `ZFA:0001477` | — |  |
| `ZFA:0001496` | simple columnar epithelium | `ZFA:0001477` | — | yes |
| `ZFA:0001497` | simple cuboidal epithelium | `ZFA:0001477` | — | yes |
| `ZFA:0001498` | simple squamous epithelium | `ZFA:0001477` | — | yes |
| `ZFA:0005069` | sinoatrial node | `ZFA:0001477` | — |  |
| `ZFA:0005600` | sinoatrial region | `ZFA:0001477` | — |  |
| `ZFA:0005601` | sinoatrial ring | `ZFA:0001477` | — |  |
| `ZFA:0005261` | sinusoidal blood vessel endothelium | `ZFA:0001477` | — | yes |
| `ZFA:0005277` | skeletal muscle | `ZFA:0001477` | — | yes |
| `ZFA:0005619` | skeletal tissue | `ZFA:0001477` | — |  |
| `ZFA:0005274` | smooth muscle | `ZFA:0001477` | — | yes |
| `ZFA:0001679` | solid lens vesicle | `ZFA:0001477` | — | yes |
| `ZFA:0000155` | somite | `ZFA:0001477` | — | yes |
| `ZFA:0000072` | somite 1 | `ZFA:0001477` | — | yes |
| `ZFA:0000974` | somite 10 | `ZFA:0001477` | — | yes |
| `ZFA:0000725` | somite 11 | `ZFA:0001477` | — | yes |
| `ZFA:0000851` | somite 12 | `ZFA:0001477` | — | yes |
| `ZFA:0000975` | somite 13 | `ZFA:0001477` | — | yes |
| `ZFA:0000726` | somite 14 | `ZFA:0001477` | — | yes |
| `ZFA:0000852` | somite 15 | `ZFA:0001477` | — | yes |
| `ZFA:0000976` | somite 16 | `ZFA:0001477` | — | yes |
| `ZFA:0000727` | somite 17 | `ZFA:0001477` | — | yes |
| `ZFA:0000853` | somite 18 | `ZFA:0001477` | — | yes |
| `ZFA:0000977` | somite 19 | `ZFA:0001477` | — | yes |
| `ZFA:0000728` | somite 2 | `ZFA:0001477` | — | yes |
| `ZFA:0000156` | somite 20 | `ZFA:0001477` | — | yes |
| `ZFA:0000854` | somite 21 | `ZFA:0001477` | — | yes |
| `ZFA:0000978` | somite 22 | `ZFA:0001477` | — | yes |
| `ZFA:0000730` | somite 23 | `ZFA:0001477` | — | yes |
| `ZFA:0000855` | somite 24 | `ZFA:0001477` | — | yes |
| `ZFA:0000980` | somite 25 | `ZFA:0001477` | — | yes |
| `ZFA:0000074` | somite 26 | `ZFA:0001477` | — | yes |
| `ZFA:0000731` | somite 27 | `ZFA:0001477` | — | yes |
| `ZFA:0000856` | somite 28 | `ZFA:0001477` | — | yes |
| `ZFA:0000981` | somite 29 | `ZFA:0001477` | — | yes |
| `ZFA:0000732` | somite 3 | `ZFA:0001477` | — | yes |
| `ZFA:0000157` | somite 30 | `ZFA:0001477` | — | yes |
| `ZFA:0000857` | somite 4 | `ZFA:0001477` | — | yes |
| `ZFA:0000073` | somite 5 | `ZFA:0001477` | — | yes |
| `ZFA:0000982` | somite 6 | `ZFA:0001477` | — | yes |
| `ZFA:0000733` | somite 7 | `ZFA:0001477` | — | yes |
| `ZFA:0000858` | somite 8 | `ZFA:0001477` | — | yes |
| `ZFA:0000983` | somite 9 | `ZFA:0001477` | — | yes |
| `ZFA:0005882` | spermatogenic cyst | `ZFA:0001477` | — |  |
| `ZFA:0007028` | spinal cord neural keel | `ZFA:0001477` | — | yes |
| `ZFA:0007021` | spinal cord neural plate | `ZFA:0001477` | — | yes |
| `ZFA:0007035` | spinal cord neural rod | `ZFA:0001477` | — | yes |
| `ZFA:0007042` | spinal cord neural tube | `ZFA:0001477` | — | yes |
| `ZFA:0005662` | spinal nerve | `ZFA:0001477` | — |  |
| `ZFA:0005795` | spinous layer of breeding tubercle | `ZFA:0001477` | — | yes |
| `ZFA:0000588` | statoacoustic (VIII) ganglion | `ZFA:0001477` | — |  |
| `ZFA:0001638` | statoacoustic (VIII) nucleus | `ZFA:0001477` | — |  |
| `ZFA:0001651` | sternohyoid | `ZFA:0001477` | — | yes |
| `ZFA:0001351` | stratum album centrale | `ZFA:0001477` | — |  |
| `ZFA:0001347` | stratum fibrosum et griseum superficiale | `ZFA:0001477` | — |  |
| `ZFA:0001350` | stratum griseum centrale | `ZFA:0001477` | — |  |
| `ZFA:0001348` | stratum marginale | `ZFA:0001477` | — |  |
| `ZFA:0001349` | stratum opticum | `ZFA:0001477` | — |  |
| `ZFA:0005762` | subcutaneous fat | `ZFA:0001477` | — | yes |
| `ZFA:0000685` | superficial abductor | `ZFA:0001477` | — |  |
| `ZFA:0000285` | superficial adductor | `ZFA:0001477` | — |  |
| `ZFA:0000286` | superficial lateralis | `ZFA:0001477` | — |  |
| `ZFA:0005793` | superficial layer of breeding tubercle | `ZFA:0001477` | — | yes |
| `ZFA:0000439` | superficial pelvic abductor | `ZFA:0001477` | — |  |
| `ZFA:0000592` | superficial pelvic adductor | `ZFA:0001477` | — |  |
| `ZFA:0000287` | superior caudal dorsal flexor | `ZFA:0001477` | — |  |
| `ZFA:0000455` | superior caudal ventral flexor | `ZFA:0001477` | — |  |
| `ZFA:0001572` | superior cervical ganglion | `ZFA:0001477` | — |  |
| `ZFA:0000440` | superior raphe nucleus | `ZFA:0001477` | — |  |
| `ZFA:0000593` | superior reticular formation medial column | `ZFA:0001477` | — |  |
| `ZFA:0000984` | superior reticular formation tegmentum | `ZFA:0001477` | — |  |
| `ZFA:0000288` | supracarinalis | `ZFA:0001477` | — |  |
| `ZFA:0005645` | supracleithrum-intercalar ligament | `ZFA:0001477` | — | yes |
| `ZFA:0005639` | supracleithrum-vertebral ligament | `ZFA:0001477` | — | yes |
| `ZFA:0000689` | supracommissural nucleus of ventral telencephalon | `ZFA:0001477` | — | yes |
| `ZFA:0000443` | supraorbital lateral line | `ZFA:0001477` | — |  |
| `ZFA:0001556` | sympathetic chain ganglion | `ZFA:0001477` | — |  |
| `ZFA:0000693` | tangential nucleus | `ZFA:0001477` | — | yes |
| `ZFA:0005916` | tapetum lucidum | `ZFA:0001477` | — |  |
| `ZFA:0005577` | tegmental nucleus | `ZFA:0001477` | — |  |
| `ZFA:0000447` | tela chorioidea | `ZFA:0001477` | — |  |
| `ZFA:0005158` | tela chorioidea fourth ventricle | `ZFA:0001477` | — |  |
| `ZFA:0005157` | tela chorioidea tectal ventricle | `ZFA:0001477` | — |  |
| `ZFA:0005160` | tela chorioidea telencephalic ventricle | `ZFA:0001477` | — |  |
| `ZFA:0005159` | tela chorioidea third ventricle | `ZFA:0001477` | — |  |
| `ZFA:0001660` | telencephalic nucleus | `ZFA:0001477` | — |  |
| `ZFA:0005647` | tendon | `ZFA:0001477` | — | yes |
| `ZFA:0001356` | terminal nerve | `ZFA:0001477` | — | yes |
| `ZFA:0005779` | thymic epithelium | `ZFA:0001477` | — |  |
| `ZFA:0001077` | thymus primordium | `ZFA:0001477` | — |  |
| `ZFA:0001072` | thyroid follicle | `ZFA:0001477` | — |  |
| `ZFA:0001081` | thyroid primordium | `ZFA:0001477` | — |  |
| `ZFA:0001153` | tooth placode | `ZFA:0001477` | — |  |
| `ZFA:0005059` | trabecular layer | `ZFA:0001477` | — |  |
| `ZFA:0005810` | trabecular layer of the atrium | `ZFA:0001477` | — |  |
| `ZFA:0005060` | trabecular layer of ventricle | `ZFA:0001477` | — |  |
| `ZFA:0005827` | transverse band | `ZFA:0001477` | — |  |
| `ZFA:0005826` | tri-tipped trabecula | `ZFA:0001477` | — |  |
| `ZFA:0000295` | trigeminal ganglion | `ZFA:0001477` | — | yes |
| `ZFA:0001365` | trigeminal motor nucleus | `ZFA:0001477` | — |  |
| `ZFA:0000080` | trigeminal neural crest | `ZFA:0001477` | — | yes |
| `ZFA:0000450` | trochlear motor nucleus | `ZFA:0001477` | — |  |
| `ZFA:0001573` | trunk ganglion | `ZFA:0001477` | — | yes |
| `ZFA:0000081` | trunk mesenchyme | `ZFA:0001477` | — | yes |
| `ZFA:0001024` | trunk neural crest | `ZFA:0001477` | — | yes |
| `ZFA:0005883` | tunica albuginea testis | `ZFA:0001477` | — |  |
| `ZFA:0005881` | tunica propria of seminiferous tubule | `ZFA:0001477` | — |  |
| `ZFA:0001495` | unilaminar epithelium | `ZFA:0001477` | — | yes |
| `ZFA:0000451` | upper oral valve | `ZFA:0001477` | — | yes |
| `ZFA:0007067` | vagal ganglion | `ZFA:0001477` | — | yes |
| `ZFA:0001302` | vagal ganglion 1 | `ZFA:0001477` | — | yes |
| `ZFA:0001303` | vagal ganglion 2 | `ZFA:0001477` | — | yes |
| `ZFA:0001304` | vagal ganglion 3 | `ZFA:0001477` | — | yes |
| `ZFA:0001305` | vagal ganglion 4 | `ZFA:0001477` | — | yes |
| `ZFA:0000818` | vagal neural crest | `ZFA:0001477` | — | yes |
| `ZFA:0007011` | vagal root | `ZFA:0001477` | — |  |
| `ZFA:0005077` | vascular cord | `ZFA:0001477` | — | yes |
| `ZFA:0001639` | vascular endothelium | `ZFA:0001477` | — |  |
| `ZFA:0005321` | vascular smooth muscle | `ZFA:0001477` | — | yes |
| `ZFA:0005559` | vascular sprouts | `ZFA:0001477` | — |  |
| `ZFA:0001313` | ventral anterior lateral line ganglion | `ZFA:0001477` | — | yes |
| `ZFA:0001481` | ventral anterior lateral line nerve | `ZFA:0001477` | — |  |
| `ZFA:0000701` | ventral arrector | `ZFA:0001477` | — |  |
| `ZFA:0005820` | ventral caudal adductor | `ZFA:0001477` | — |  |
| `ZFA:0000299` | ventral entopeduncular nucleus of ventral telencephalon | `ZFA:0001477` | — | yes |
| `ZFA:0000302` | ventral habenular nucleus | `ZFA:0001477` | — |  |
| `ZFA:0005821` | ventral interfilamental caudal muscle | `ZFA:0001477` | — |  |
| `ZFA:0007008` | ventral intermandibularis anterior | `ZFA:0001477` | — | yes |
| `ZFA:0007048` | ventral intermandibularis posterior | `ZFA:0001477` | — | yes |
| `ZFA:0001201` | ventral lateral mesoderm | `ZFA:0001477` | — | yes |
| `ZFA:0000164` | ventral mesenchyme | `ZFA:0001477` | — | yes |
| `ZFA:0005133` | ventral mesentery | `ZFA:0001477` | — | yes |
| `ZFA:0000083` | ventral mesoderm | `ZFA:0001477` | — | yes |
| `ZFA:0000703` | ventral motor nucleus trigeminal nerve | `ZFA:0001477` | — | yes |
| `ZFA:0000456` | ventral nucleus of ventral telencephalon | `ZFA:0001477` | — | yes |
| `ZFA:0000606` | ventral oblique branchial muscle | `ZFA:0001477` | — | yes |
| `ZFA:0000861` | ventral oblique extraocular muscle | `ZFA:0001477` | — |  |
| `ZFA:0000704` | ventral pelvic arrector | `ZFA:0001477` | — |  |
| `ZFA:0000457` | ventral rectus | `ZFA:0001477` | — |  |
| `ZFA:0000705` | ventral root | `ZFA:0001477` | — |  |
| `ZFA:0005665` | ventral spinal nerve | `ZFA:0001477` | — | yes |
| `ZFA:0005667` | ventral spinal nerve median branch | `ZFA:0001477` | — | yes |
| `ZFA:0005666` | ventral spinal nerve septal branch | `ZFA:0001477` | — | yes |
| `ZFA:0000608` | ventral transverse | `ZFA:0001477` | — | yes |
| `ZFA:0005028` | ventral wall of dorsal aorta | `ZFA:0001477` | — |  |
| `ZFA:0001615` | ventricular endocardium | `ZFA:0001477` | — |  |
| `ZFA:0005058` | ventricular epicardium | `ZFA:0001477` | — |  |
| `ZFA:0005061` | ventricular myocardium | `ZFA:0001477` | — |  |
| `ZFA:0007003` | ventro-caudal cluster | `ZFA:0001477` | — |  |
| `ZFA:0007002` | ventro-rostral cluster | `ZFA:0001477` | — |  |
| `ZFA:0000609` | ventrolateral nucleus | `ZFA:0001477` | — |  |
| `ZFA:0007118` | vertebral body end plate | `ZFA:0001477` | — |  |
| `ZFA:0005759` | visceral fat | `ZFA:0001477` | — | yes |
| `ZFA:0000710` | viscerosensory commissural nucleus of Cajal | `ZFA:0001477` | — |  |
| `ZFA:0001451` | zone of polarizing activity pectoral fin bud | `ZFA:0001477` | — | yes |
| `ZFA:0001452` | zone of polarizing activity pelvic fin bud | `ZFA:0001477` | — | yes |

### `cell` (650)

| Id | Name | Source class | explicit_germ_layer | Stranded |
| --- | --- | --- | --- | --- |
| `ZFA:0009129` | absorptive cell | `ZFA:0009000` | — | yes |
| `ZFA:0009095` | acid secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0009277` | acinar cell | `ZFA:0009000` | — | yes |
| `ZFA:0000003` | adaxial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009167` | adrenal medulla cell | `ZFA:0009000` | — | yes |
| `ZFA:0009061` | adrenergic neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009216` | adrenocorticotropic hormone secreting cell | `ZFA:0009000` | — |  |
| `ZFA:0009238` | afferent neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009201` | alkali secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0009335` | alpha-beta T cell | `ZFA:0009000` | — | yes |
| `ZFA:0009255` | amacrine cell | `ZFA:0009000` | — |  |
| `ZFA:0009028` | ameloblast | `ZFA:0009000` | — | yes |
| `ZFA:0009085` | amelocyte | `ZFA:0009000` | — | yes |
| `ZFA:0009271` | androgen secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0009258` | angioblastic mesenchymal cell | `ZFA:0009000` | — | yes |
| `ZFA:0009075` | astrocyte | `ZFA:0009000` | — | yes |
| `ZFA:0005244` | auditory epithelial support cell | `ZFA:0009000` | — | yes |
| `ZFA:0009121` | auditory receptor cell | `ZFA:0009000` | — | yes |
| `ZFA:0009059` | autonomic neuron | `ZFA:0009000` | — |  |
| `ZFA:0009142` | B cell | `ZFA:0009000` | — | yes |
| `ZFA:0009254` | band form neutrophil | `ZFA:0009000` | — | yes |
| `ZFA:0009132` | barrier cell | `ZFA:0009000` | — | yes |
| `ZFA:0009037` | barrier epithelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009068` | basket cell | `ZFA:0009000` | — | yes |
| `ZFA:0005236` | basophilic erythroblast | `ZFA:0009000` | — | yes |
| `ZFA:0009282` | Bergmann glial cell | `ZFA:0009000` | — | yes |
| `ZFA:0005231` | bifurcate interneuron | `ZFA:0009000` | — | yes |
| `ZFA:0009212` | biogenic amine secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0009055` | bipolar neuron | `ZFA:0009000` | — |  |
| `ZFA:0009178` | blastemal cell | `ZFA:0009000` | — | yes |
| `ZFA:0009177` | blastoderm cell | `ZFA:0009000` | — | yes |
| `ZFA:0000093` | blastomere | `ZFA:0009000` | — | yes |
| `ZFA:0009044` | blood cell | `ZFA:0009000` | — |  |
| `ZFA:0009036` | blood vessel endothelial cell | `ZFA:0009000` | mesoderm | yes |
| `ZFA:0009222` | blue sensitive photoreceptor cell | `ZFA:0009000` | — | yes |
| `ZFA:0005970` | brain lymphatic endothelial cell | `ZFA:0009000` | — |  |
| `ZFA:0005731` | branchiomotor neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009143` | brush border epithelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0005218` | CaD | `ZFA:0009000` | — | yes |
| `ZFA:0009300` | Cajal-Retzius cell | `ZFA:0009000` | — | yes |
| `ZFA:0009206` | calcitonin secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0009243` | CaP motoneuron | `ZFA:0009000` | — | yes |
| `ZFA:0009259` | cardiac mesenchymal cell | `ZFA:0009000` | — | yes |
| `ZFA:0009316` | cardiac muscle cell | `ZFA:0009000` | — |  |
| `ZFA:0009234` | cardiac muscle myoblast | `ZFA:0009000` | — | yes |
| `ZFA:0005217` | CaV | `ZFA:0009000` | — | yes |
| `ZFA:0009000` | cell | `ZFA:0009000` | — | yes |
| `ZFA:0009030` | cementoblast | `ZFA:0009000` | — | yes |
| `ZFA:0009087` | cementocyte | `ZFA:0009000` | — |  |
| `ZFA:0001691` | cerebellar granule cell | `ZFA:0009000` | — |  |
| `ZFA:0007120` | cerebrospinal fluid contacting neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009295` | cerebrospinal fluid secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0009124` | chemoreceptor cell | `ZFA:0009000` | — | yes |
| `ZFA:0009397` | cholangiocyte | `ZFA:0009000` | endoderm | yes |
| `ZFA:0009060` | cholinergic neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009027` | chondroblast | `ZFA:0009000` | mesoderm | yes |
| `ZFA:0009084` | chondrocyte | `ZFA:0009000` | mesoderm | yes |
| `ZFA:0009304` | choroid plexus epithelial cell | `ZFA:0009000` | — |  |
| `ZFA:0009175` | choroidal cell of the eye | `ZFA:0009000` | — | yes |
| `ZFA:0009099` | chromaffin cell | `ZFA:0009000` | — | yes |
| `ZFA:0005247` | CiA | `ZFA:0009000` | — | yes |
| `ZFA:0005233` | CiD | `ZFA:0009000` | — | yes |
| `ZFA:0009032` | ciliated cell | `ZFA:0009000` | — | yes |
| `ZFA:0009035` | ciliated epithelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009358` | ciliated olfactory receptor neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009043` | circulating cell | `ZFA:0009000` | — | yes |
| `ZFA:0005786` | cleft cell | `ZFA:0009000` | — | yes |
| `ZFA:0009191` | CNS interneuron | `ZFA:0009000` | — | yes |
| `ZFA:0009195` | CNS long range interneuron | `ZFA:0009000` | — | yes |
| `ZFA:0009067` | CNS neuron (sensu Vertebrata) | `ZFA:0009000` | — | yes |
| `ZFA:0009194` | CNS short range interneuron | `ZFA:0009000` | — | yes |
| `ZFA:0005186` | CoB | `ZFA:0009000` | — | yes |
| `ZFA:0005230` | CoBL | `ZFA:0009000` | — | yes |
| `ZFA:0005234` | CoLA | `ZFA:0009000` | — | yes |
| `ZFA:0009287` | collagen secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0009314` | columnar chondrocyte | `ZFA:0009000` | — | yes |
| `ZFA:0009038` | columnar/cuboidal epithelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009023` | common lymphoid progenitor | `ZFA:0009000` | — | yes |
| `ZFA:0009021` | common myeloid progenitor | `ZFA:0009000` | — | yes |
| `ZFA:0009322` | cone retinal bipolar cell | `ZFA:0009000` | — | yes |
| `ZFA:0009392` | connective tissue cell | `ZFA:0009000` | — | yes |
| `ZFA:0005175` | CoPA | `ZFA:0009000` | — | yes |
| `ZFA:0009079` | corneal endothelial cell | `ZFA:0009000` | — |  |
| `ZFA:0009264` | corneal epithelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0005176` | CoSA | `ZFA:0009000` | — | yes |
| `ZFA:0005730` | cranial motor neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009003` | cranial neural crest cell | `ZFA:0009000` | — | yes |
| `ZFA:0005770` | crypt neuron olfactory support cell | `ZFA:0009000` | — | yes |
| `ZFA:0009360` | crypt olfactory receptor neuron | `ZFA:0009000` | — | yes |
| `ZFA:0005332` | cyanoblast | `ZFA:0009000` | — | yes |
| `ZFA:0009317` | cyanophore | `ZFA:0009000` | — | yes |
| `ZFA:0009228` | D cell | `ZFA:0009000` | — |  |
| `ZFA:0005963` | DC2 dopaminergic neuron | `ZFA:0009000` | — |  |
| `ZFA:0005964` | DC4 dopaminergic neuron | `ZFA:0009000` | — |  |
| `ZFA:0001473` | deep blastomere | `ZFA:0009000` | — | yes |
| `ZFA:0009209` | dendritic cell | `ZFA:0009000` | — | yes |
| `ZFA:0009173` | dental papilla cell | `ZFA:0009000` | — | yes |
| `ZFA:0005806` | diencephalic efferent neurons to the lateral line | `ZFA:0009000` | — |  |
| `ZFA:0009217` | digestive enzyme secreting cell | `ZFA:0009000` | — |  |
| `ZFA:0005178` | DoLA | `ZFA:0009000` | — | yes |
| `ZFA:0009301` | dopaminergic neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009372` | duct epithelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009002` | early embryonic cell | `ZFA:0009000` | — | yes |
| `ZFA:0009385` | ecto-epithelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009137` | ectodermal cell | `ZFA:0009000` | — | yes |
| `ZFA:0009239` | efferent neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009128` | electrically active cell | `ZFA:0009000` | — | yes |
| `ZFA:0009190` | electrically responsive cell | `ZFA:0009000` | — | yes |
| `ZFA:0009193` | electrically signaling cell | `ZFA:0009000` | — | yes |
| `ZFA:0005773` | embryonic blood vessel endothelial progenitor cell | `ZFA:0009000` | — | yes |
| `ZFA:0007089` | embryonic cell | `ZFA:0009000` | — | yes |
| `ZFA:0009383` | endo-epithelial cell | `ZFA:0009000` | endoderm | yes |
| `ZFA:0009096` | endocrine cell | `ZFA:0009000` | — |  |
| `ZFA:0009139` | endodermal cell | `ZFA:0009000` | — | yes |
| `ZFA:0009232` | endorphin secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0009065` | endothelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009303` | endothelial tip cell | `ZFA:0009000` | — | yes |
| `ZFA:0009231` | enkephalin secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0005775` | enteric neuron | `ZFA:0009000` | — |  |
| `ZFA:0009269` | enterocyte | `ZFA:0009000` | — |  |
| `ZFA:0009097` | enteroendocrine cell | `ZFA:0009000` | — | yes |
| `ZFA:0009033` | ependymal cell | `ZFA:0009000` | — |  |
| `ZFA:0009294` | ependymoglial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009183` | epidermal cell | `ZFA:0009000` | — | yes |
| `ZFA:0007122` | epidermal stem cell | `ZFA:0009000` | — | yes |
| `ZFA:0009211` | epinephrin secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0009034` | epithelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009400` | epithelial cell of esophagus | `ZFA:0009000` | — |  |
| `ZFA:0009045` | epithelial cell of pancreas | `ZFA:0009000` | — | yes |
| `ZFA:0005237` | erythroblast | `ZFA:0009000` | — | yes |
| `ZFA:0009325` | erythroid lineage cell | `ZFA:0009000` | — | yes |
| `ZFA:0009015` | erythroid progenitor cell | `ZFA:0009000` | — | yes |
| `ZFA:0009263` | erythrophore | `ZFA:0009000` | — | yes |
| `ZFA:0009110` | estradiol secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0009153` | eurydendroid cell | `ZFA:0009000` | — |  |
| `ZFA:0009092` | exocrine cell | `ZFA:0009000` | — | yes |
| `ZFA:0009162` | extracellular matrix secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0009176` | extraembryonic cell | `ZFA:0009000` | — | yes |
| `ZFA:0009152` | extramedullary cell | `ZFA:0009000` | — | yes |
| `ZFA:0005966` | extrastriolar hair cell | `ZFA:0009000` | — |  |
| `ZFA:0009154` | eye photoreceptor cell | `ZFA:0009000` | — |  |
| `ZFA:0009117` | fast muscle cell | `ZFA:0009000` | — | yes |
| `ZFA:0000513` | fast muscle cell somite 1 | `ZFA:0009000` | — | yes |
| `ZFA:0000750` | fast muscle cell somite 10 | `ZFA:0009000` | — | yes |
| `ZFA:0000876` | fast muscle cell somite 11 | `ZFA:0009000` | — | yes |
| `ZFA:0000773` | fast muscle cell somite 12 | `ZFA:0009000` | — | yes |
| `ZFA:0000752` | fast muscle cell somite 13 | `ZFA:0009000` | — | yes |
| `ZFA:0000877` | fast muscle cell somite 14 | `ZFA:0009000` | — | yes |
| `ZFA:0000784` | fast muscle cell somite 15 | `ZFA:0009000` | — | yes |
| `ZFA:0000753` | fast muscle cell somite 16 | `ZFA:0009000` | — | yes |
| `ZFA:0000878` | fast muscle cell somite 17 | `ZFA:0009000` | — | yes |
| `ZFA:0000795` | fast muscle cell somite 18 | `ZFA:0009000` | — | yes |
| `ZFA:0000754` | fast muscle cell somite 19 | `ZFA:0009000` | — | yes |
| `ZFA:0000879` | fast muscle cell somite 2 | `ZFA:0009000` | — | yes |
| `ZFA:0000806` | fast muscle cell somite 20 | `ZFA:0009000` | — | yes |
| `ZFA:0000755` | fast muscle cell somite 21 | `ZFA:0009000` | — | yes |
| `ZFA:0000880` | fast muscle cell somite 22 | `ZFA:0009000` | — | yes |
| `ZFA:0000817` | fast muscle cell somite 23 | `ZFA:0009000` | — | yes |
| `ZFA:0000756` | fast muscle cell somite 24 | `ZFA:0009000` | — | yes |
| `ZFA:0000881` | fast muscle cell somite 25 | `ZFA:0009000` | — | yes |
| `ZFA:0000827` | fast muscle cell somite 26 | `ZFA:0009000` | — | yes |
| `ZFA:0000757` | fast muscle cell somite 27 | `ZFA:0009000` | — | yes |
| `ZFA:0000883` | fast muscle cell somite 28 | `ZFA:0009000` | — | yes |
| `ZFA:0000838` | fast muscle cell somite 29 | `ZFA:0009000` | — | yes |
| `ZFA:0000758` | fast muscle cell somite 3 | `ZFA:0009000` | — | yes |
| `ZFA:0000884` | fast muscle cell somite 30 | `ZFA:0009000` | — | yes |
| `ZFA:0000849` | fast muscle cell somite 4 | `ZFA:0009000` | — | yes |
| `ZFA:0000759` | fast muscle cell somite 5 | `ZFA:0009000` | — | yes |
| `ZFA:0000885` | fast muscle cell somite 6 | `ZFA:0009000` | — | yes |
| `ZFA:0000860` | fast muscle cell somite 7 | `ZFA:0009000` | — | yes |
| `ZFA:0000760` | fast muscle cell somite 8 | `ZFA:0009000` | — | yes |
| `ZFA:0000886` | fast muscle cell somite 9 | `ZFA:0009000` | — | yes |
| `ZFA:0009369` | fast muscle myoblast | `ZFA:0009000` | — | yes |
| `ZFA:0009082` | fat cell | `ZFA:0009000` | — | yes |
| `ZFA:0009286` | fenestrated cell | `ZFA:0009000` | — | yes |
| `ZFA:0005772` | fertilized egg | `ZFA:0009000` | — | yes |
| `ZFA:0009026` | fibroblast | `ZFA:0009000` | — | yes |
| `ZFA:0009202` | follicle stimulating hormone secreting cell | `ZFA:0009000` | — |  |
| `ZFA:0009281` | folliculostellate cell | `ZFA:0009000` | — |  |
| `ZFA:0009276` | GABAergic neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009093` | GAG secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0009156` | gamete | `ZFA:0009000` | — |  |
| `ZFA:0009339` | gamma-delta intraepithelial T cell | `ZFA:0009000` | — | yes |
| `ZFA:0009336` | gamma-delta T cell | `ZFA:0009000` | — | yes |
| `ZFA:0009182` | gastrula cell | `ZFA:0009000` | — | yes |
| `ZFA:0009016` | germ line cell | `ZFA:0009000` | — | yes |
| `ZFA:0005956` | germline stem cell | `ZFA:0009000` | — | yes |
| `ZFA:0005599` | ghrelin secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0005324` | gill ionocyte | `ZFA:0009000` | — |  |
| `ZFA:0009073` | glial cell | `ZFA:0009000` | — |  |
| `ZFA:0009147` | glial cell (sensu Vertebrata) | `ZFA:0009000` | — | yes |
| `ZFA:0009010` | glioblast | `ZFA:0009000` | — | yes |
| `ZFA:0009169` | glioblast (sensu Vertebrata) | `ZFA:0009000` | — | yes |
| `ZFA:0009103` | glucagon secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0009215` | glucocorticoid secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0009290` | glutamatergic neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009396` | glycinergic neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009094` | goblet cell | `ZFA:0009000` | — | yes |
| `ZFA:0005151` | gold iridophore | `ZFA:0009000` | — | yes |
| `ZFA:0009069` | Golgi cell | `ZFA:0009000` | — | yes |
| `ZFA:0009070` | granule cell | `ZFA:0009000` | — |  |
| `ZFA:0009048` | granulocyte | `ZFA:0009000` | — | yes |
| `ZFA:0009251` | granulocyte monocyte progenitor cell | `ZFA:0009000` | — | yes |
| `ZFA:0009227` | granulosa cell | `ZFA:0009000` | — | yes |
| `ZFA:0009223` | green sensitive photoreceptor cell | `ZFA:0009000` | — | yes |
| `ZFA:0009289` | gut absorptive cell | `ZFA:0009000` | — |  |
| `ZFA:0009078` | gut endothelial cell | `ZFA:0009000` | — |  |
| `ZFA:0009366` | hair cell | `ZFA:0009000` | — | yes |
| `ZFA:0000678` | hair cell anterior macula | `ZFA:0009000` | — |  |
| `ZFA:0000281` | hair cell posterior macula | `ZFA:0009000` | — |  |
| `ZFA:0009151` | hatching gland cell | `ZFA:0009000` | — | yes |
| `ZFA:0009402` | heart valve cell | `ZFA:0009000` | — |  |
| `ZFA:0009404` | heart valve endothelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009403` | heart valve interstitial cell | `ZFA:0009000` | — | yes |
| `ZFA:0005830` | hematopoietic cell | `ZFA:0009000` | — | yes |
| `ZFA:0009354` | hematopoietic multipotent progenitor cell | `ZFA:0009000` | — | yes |
| `ZFA:0009014` | hematopoietic stem cell | `ZFA:0009000` | — |  |
| `ZFA:0009398` | hepatoblast | `ZFA:0009000` | endoderm | yes |
| `ZFA:0009111` | hepatocyte | `ZFA:0009000` | endoderm |  |
| `ZFA:0005209` | hindbrain interneuron | `ZFA:0009000` | — |  |
| `ZFA:0009315` | horizontal cell | `ZFA:0009000` | — |  |
| `ZFA:0009313` | hypertrophic chondrocyte | `ZFA:0009000` | — | yes |
| `ZFA:0005778` | hypocretin-secreting neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009196` | hypodermal cell | `ZFA:0009000` | — | yes |
| `ZFA:0009343` | immature B cell | `ZFA:0009000` | — | yes |
| `ZFA:0009337` | immature gamma-delta T cell | `ZFA:0009000` | — | yes |
| `ZFA:0001098` | immature hair cell anterior macula | `ZFA:0009000` | — | yes |
| `ZFA:0001099` | immature hair cell posterior macula | `ZFA:0009000` | — | yes |
| `ZFA:0009346` | immature natural killer cell | `ZFA:0009000` | — | yes |
| `ZFA:0009328` | immature neutrophil | `ZFA:0009000` | — | yes |
| `ZFA:0001725` | immature Schwann cell | `ZFA:0009000` | — |  |
| `ZFA:0009225` | inhibitory interneuron | `ZFA:0009000` | — | yes |
| `ZFA:0009134` | insulating cell | `ZFA:0009000` | — | yes |
| `ZFA:0009101` | insulin secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0005325` | integument ionocyte | `ZFA:0009000` | — | yes |
| `ZFA:0009365` | interneuromast cell | `ZFA:0009000` | — |  |
| `ZFA:0009051` | interneuron | `ZFA:0009000` | — | yes |
| `ZFA:0009399` | intestinal epithelial cell | `ZFA:0009000` | — |  |
| `ZFA:0009379` | intrahepatic bile duct epithelial cell | `ZFA:0009000` | — |  |
| `ZFA:0005323` | ionocyte | `ZFA:0009000` | — | yes |
| `ZFA:0007123` | ionocyte progenitor cell | `ZFA:0009000` | — | yes |
| `ZFA:0005328` | iridoblast | `ZFA:0009000` | — | yes |
| `ZFA:0009199` | iridophore | `ZFA:0009000` | — |  |
| `ZFA:0009279` | ito cell | `ZFA:0009000` | — | yes |
| `ZFA:0005238` | juxtaglomerular cell | `ZFA:0009000` | — |  |
| `ZFA:0005828` | kappe olfactory receptor neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009157` | keratin accumulating cell | `ZFA:0009000` | — | yes |
| `ZFA:0009158` | keratinocyte | `ZFA:0009000` | — | yes |
| `ZFA:0007124` | keratinocyte progenitor cell | `ZFA:0009000` | — | yes |
| `ZFA:0009389` | kidney cell | `ZFA:0009000` | — |  |
| `ZFA:0009374` | kidney epithelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009390` | kidney interstitial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009391` | kidney medulla cell | `ZFA:0009000` | — | yes |
| `ZFA:0005240` | Kolmer-Agduhr neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009401` | lens fiber cell | `ZFA:0009000` | — |  |
| `ZFA:0009305` | leptomeningeal cell | `ZFA:0009000` | — | yes |
| `ZFA:0005329` | leucoblast | `ZFA:0009000` | — | yes |
| `ZFA:0009261` | leucophore | `ZFA:0009000` | — | yes |
| `ZFA:0009309` | leukocyte | `ZFA:0009000` | — |  |
| `ZFA:0009108` | Leydig cell | `ZFA:0009000` | — | yes |
| `ZFA:0009188` | ligament cell | `ZFA:0009000` | — | yes |
| `ZFA:0009130` | lining cell | `ZFA:0009000` | — | yes |
| `ZFA:0005945` | long double cone cell | `ZFA:0009000` | — | yes |
| `ZFA:0005947` | long single cone cell | `ZFA:0009000` | — | yes |
| `ZFA:0009203` | luteinizing hormone secreting cell | `ZFA:0009000` | — |  |
| `ZFA:0009393` | lymphangioblast | `ZFA:0009000` | — | yes |
| `ZFA:0009250` | lymphocyte | `ZFA:0009000` | — | yes |
| `ZFA:0009355` | lymphoid progenitor cell | `ZFA:0009000` | — | yes |
| `ZFA:0005942` | lysosome-rich enterocyte | `ZFA:0009000` | — | yes |
| `ZFA:0009293` | M cell | `ZFA:0009000` | — | yes |
| `ZFA:0009074` | macroglial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009141` | macrophage | `ZFA:0009000` | — |  |
| `ZFA:0000541` | marginal blastomere | `ZFA:0009000` | — | yes |
| `ZFA:0009331` | mature B cell | `ZFA:0009000` | — | yes |
| `ZFA:0009338` | mature gamma-delta T cell | `ZFA:0009000` | — | yes |
| `ZFA:0009347` | mature natural killer cell | `ZFA:0009000` | — | yes |
| `ZFA:0009049` | mature neutrophil | `ZFA:0009000` | — | yes |
| `ZFA:0009149` | Mauthner neuron | `ZFA:0009000` | — |  |
| `ZFA:0005232` | MCoD | `ZFA:0009000` | — | yes |
| `ZFA:0009120` | mechanoreceptor cell | `ZFA:0009000` | — | yes |
| `ZFA:0009022` | megakaryocyte erythroid progenitor cell | `ZFA:0009000` | — | yes |
| `ZFA:0005211` | MeL | `ZFA:0009000` | — |  |
| `ZFA:0009249` | melanoblast | `ZFA:0009000` | — | yes |
| `ZFA:0009091` | melanocyte | `ZFA:0009000` | — |  |
| `ZFA:0009205` | melanocyte stimulating hormone secreting cell | `ZFA:0009000` | — |  |
| `ZFA:0005928` | melanoleucophore | `ZFA:0009000` | — | yes |
| `ZFA:0005214` | MeLc | `ZFA:0009000` | — |  |
| `ZFA:0005215` | MeLm | `ZFA:0009000` | — |  |
| `ZFA:0005213` | MeLr | `ZFA:0009000` | — |  |
| `ZFA:0005212` | MeM | `ZFA:0009000` | — |  |
| `ZFA:0005216` | MeM1 | `ZFA:0009000` | — |  |
| `ZFA:0009333` | memory B cell | `ZFA:0009000` | — | yes |
| `ZFA:0009342` | memory T cell | `ZFA:0009000` | — | yes |
| `ZFA:0009146` | Merkel cell | `ZFA:0009000` | — | yes |
| `ZFA:0009283` | mesangial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009081` | mesenchymal cell | `ZFA:0009000` | — | yes |
| `ZFA:0009394` | mesenchymal lymphangioblast | `ZFA:0009000` | — | yes |
| `ZFA:0009166` | mesenchyme condensation cell | `ZFA:0009000` | — | yes |
| `ZFA:0009388` | meso-epithelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009138` | mesodermal cell | `ZFA:0009000` | — | yes |
| `ZFA:0001674` | mesonephric podocyte | `ZFA:0009000` | — |  |
| `ZFA:0009040` | mesothelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009077` | microglial cell | `ZFA:0009000` | — | yes |
| `ZFA:0005239` | micropylar cell | `ZFA:0009000` | — |  |
| `ZFA:0009359` | microvillous olfactory receptor neuron | `ZFA:0009000` | — | yes |
| `ZFA:0005184` | MiD2cl | `ZFA:0009000` | — | yes |
| `ZFA:0005185` | MiD2cm | `ZFA:0009000` | — | yes |
| `ZFA:0005183` | MiD2i | `ZFA:0009000` | — | yes |
| `ZFA:0005195` | MiD3cl | `ZFA:0009000` | — | yes |
| `ZFA:0005196` | MiD3cm | `ZFA:0009000` | — | yes |
| `ZFA:0005197` | MiD3i | `ZFA:0009000` | — | yes |
| `ZFA:0005210` | midbrain interneuron | `ZFA:0009000` | — | yes |
| `ZFA:0007091` | migratory cranial neural crest cell | `ZFA:0009000` | — | yes |
| `ZFA:0005921` | migratory muscle precursor | `ZFA:0009000` | — | yes |
| `ZFA:0007086` | migratory neural crest cell | `ZFA:0009000` | — | yes |
| `ZFA:0001373` | migratory slow muscle precursor cell | `ZFA:0009000` | — | yes |
| `ZFA:0007095` | migratory trunk neural crest cell | `ZFA:0009000` | — | yes |
| `ZFA:0005187` | MiM1 | `ZFA:0009000` | — | yes |
| `ZFA:0005179` | MiP motor neuron | `ZFA:0009000` | — | yes |
| `ZFA:0005188` | MiR1 | `ZFA:0009000` | — | yes |
| `ZFA:0005189` | MiR2 | `ZFA:0009000` | — | yes |
| `ZFA:0005190` | MiV1 | `ZFA:0009000` | — | yes |
| `ZFA:0005191` | MiV2 | `ZFA:0009000` | — | yes |
| `ZFA:0009017` | monoblast | `ZFA:0009000` | — | yes |
| `ZFA:0009265` | monocyte | `ZFA:0009000` | — | yes |
| `ZFA:0009357` | mononuclear cell | `ZFA:0009000` | — | yes |
| `ZFA:0009330` | mononuclear odontoclast | `ZFA:0009000` | — | yes |
| `ZFA:0009329` | mononuclear osteoclast | `ZFA:0009000` | — | yes |
| `ZFA:0009064` | mononuclear phagocyte | `ZFA:0009000` | — | yes |
| `ZFA:0009136` | motile cell | `ZFA:0009000` | — | yes |
| `ZFA:0005971` | motor exit point glia | `ZFA:0009000` | — | yes |
| `ZFA:0009052` | motor neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009159` | mucus secreting cell | `ZFA:0009000` | — |  |
| `ZFA:0009280` | Muller cell | `ZFA:0009000` | — |  |
| `ZFA:0009020` | multi fate stem cell | `ZFA:0009000` | — | yes |
| `ZFA:0005242` | multi-ciliated epithelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009056` | multipolar neuron | `ZFA:0009000` | — | yes |
| `ZFA:0005944` | mural cell | `ZFA:0009000` | — |  |
| `ZFA:0009114` | muscle cell | `ZFA:0009000` | — |  |
| `ZFA:0001086` | muscle pioneer | `ZFA:0009000` | — | yes |
| `ZFA:0000043` | muscle pioneer somite 1 | `ZFA:0009000` | — | yes |
| `ZFA:0000790` | muscle pioneer somite 10 | `ZFA:0009000` | — | yes |
| `ZFA:0000915` | muscle pioneer somite 11 | `ZFA:0009000` | — | yes |
| `ZFA:0001003` | muscle pioneer somite 12 | `ZFA:0009000` | — | yes |
| `ZFA:0000791` | muscle pioneer somite 13 | `ZFA:0009000` | — | yes |
| `ZFA:0000916` | muscle pioneer somite 14 | `ZFA:0009000` | — | yes |
| `ZFA:0001004` | muscle pioneer somite 15 | `ZFA:0009000` | — | yes |
| `ZFA:0000792` | muscle pioneer somite 16 | `ZFA:0009000` | — | yes |
| `ZFA:0000917` | muscle pioneer somite 17 | `ZFA:0009000` | — | yes |
| `ZFA:0001005` | muscle pioneer somite 18 | `ZFA:0009000` | — | yes |
| `ZFA:0000793` | muscle pioneer somite 19 | `ZFA:0009000` | — | yes |
| `ZFA:0000395` | muscle pioneer somite 2 | `ZFA:0009000` | — | yes |
| `ZFA:0000918` | muscle pioneer somite 20 | `ZFA:0009000` | — | yes |
| `ZFA:0001006` | muscle pioneer somite 21 | `ZFA:0009000` | — | yes |
| `ZFA:0000794` | muscle pioneer somite 22 | `ZFA:0009000` | — | yes |
| `ZFA:0000919` | muscle pioneer somite 23 | `ZFA:0009000` | — | yes |
| `ZFA:0001007` | muscle pioneer somite 24 | `ZFA:0009000` | — | yes |
| `ZFA:0000796` | muscle pioneer somite 25 | `ZFA:0009000` | — | yes |
| `ZFA:0000920` | muscle pioneer somite 26 | `ZFA:0009000` | — | yes |
| `ZFA:0001008` | muscle pioneer somite 27 | `ZFA:0009000` | — | yes |
| `ZFA:0000797` | muscle pioneer somite 28 | `ZFA:0009000` | — | yes |
| `ZFA:0000921` | muscle pioneer somite 29 | `ZFA:0009000` | — | yes |
| `ZFA:0001009` | muscle pioneer somite 3 | `ZFA:0009000` | — | yes |
| `ZFA:0000798` | muscle pioneer somite 30 | `ZFA:0009000` | — | yes |
| `ZFA:0000922` | muscle pioneer somite 4 | `ZFA:0009000` | — | yes |
| `ZFA:0001010` | muscle pioneer somite 5 | `ZFA:0009000` | — | yes |
| `ZFA:0000799` | muscle pioneer somite 6 | `ZFA:0009000` | — | yes |
| `ZFA:0000923` | muscle pioneer somite 7 | `ZFA:0009000` | — | yes |
| `ZFA:0001011` | muscle pioneer somite 8 | `ZFA:0009000` | — | yes |
| `ZFA:0000800` | muscle pioneer somite 9 | `ZFA:0009000` | — | yes |
| `ZFA:0009291` | muscle precursor cell | `ZFA:0009000` | mesoderm | yes |
| `ZFA:0009179` | muscle stem cell | `ZFA:0009000` | — | yes |
| `ZFA:0009163` | myelin accumulating cell | `ZFA:0009000` | — | yes |
| `ZFA:0009135` | myelinating Schwann cell | `ZFA:0009000` | — |  |
| `ZFA:0009353` | myeloblast | `ZFA:0009000` | — | yes |
| `ZFA:0009324` | myeloid cell | `ZFA:0009000` | — | yes |
| `ZFA:0009326` | myeloid leukocyte | `ZFA:0009000` | — | yes |
| `ZFA:0009356` | myeloid lineage restricted progenitor cell | `ZFA:0009000` | — | yes |
| `ZFA:0009025` | myoblast | `ZFA:0009000` | — | yes |
| `ZFA:0009113` | myoepithelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009334` | naive B cell | `ZFA:0009000` | — | yes |
| `ZFA:0005326` | NaK ionocyte | `ZFA:0009000` | — | yes |
| `ZFA:0009278` | natural killer cell | `ZFA:0009000` | — | yes |
| `ZFA:0005579` | NCC ionocyte | `ZFA:0009000` | — | yes |
| `ZFA:0009187` | nephrogenic mesenchyme stem cell | `ZFA:0009000` | — | yes |
| `ZFA:0009165` | neural crest cell | `ZFA:0009000` | — | yes |
| `ZFA:0009384` | neurecto-epithelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009080` | neurectodermal cell | `ZFA:0009000` | — | yes |
| `ZFA:0009011` | neuroblast | `ZFA:0009000` | — | yes |
| `ZFA:0009168` | neuroblast (sensu Vertebrata) | `ZFA:0009000` | — | yes |
| `ZFA:0009098` | neuroendocrine cell | `ZFA:0009000` | — | yes |
| `ZFA:0009306` | neuroepithelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009299` | neuroglioform cell | `ZFA:0009000` | — | yes |
| `ZFA:0009367` | neuromast hair cell | `ZFA:0009000` | — |  |
| `ZFA:0009362` | neuromast mantle cell | `ZFA:0009000` | — |  |
| `ZFA:0009363` | neuromast support cell | `ZFA:0009000` | — |  |
| `ZFA:0005962` | neuromast-associated ionocyte | `ZFA:0009000` | — | yes |
| `ZFA:0009248` | neuron | `ZFA:0009000` | — |  |
| `ZFA:0009009` | neuron neural crest derived | `ZFA:0009000` | — | yes |
| `ZFA:0009019` | neuronal stem cell | `ZFA:0009000` | — | yes |
| `ZFA:0009012` | neuroplacodal cell | `ZFA:0009000` | — | yes |
| `ZFA:0009186` | neurosecretory neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009327` | neutrophil | `ZFA:0009000` | — | yes |
| `ZFA:0009352` | neutrophil progenitor cell | `ZFA:0009000` | — | yes |
| `ZFA:0009268` | neutrophilic metamyelocyte | `ZFA:0009000` | — | yes |
| `ZFA:0009018` | neutrophilic myeloblast | `ZFA:0009000` | — | yes |
| `ZFA:0009266` | neutrophilic myelocyte | `ZFA:0009000` | — | yes |
| `ZFA:0009257` | neutrophilic promyelocyte | `ZFA:0009000` | — | yes |
| `ZFA:0009240` | nitrergic neuron | `ZFA:0009000` | — | yes |
| `ZFA:0005873` | noradrenergic neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009214` | norepinephrine secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0005746` | notochord inner cell | `ZFA:0009000` | — | yes |
| `ZFA:0005744` | notochord outer sheath cell | `ZFA:0009000` | — | yes |
| `ZFA:0009256` | nucleate erythrocyte | `ZFA:0009000` | — | yes |
| `ZFA:0009029` | odontoblast | `ZFA:0009000` | — |  |
| `ZFA:0009270` | odontoclast | `ZFA:0009000` | — | yes |
| `ZFA:0009086` | odontocyte | `ZFA:0009000` | — | yes |
| `ZFA:0009320` | OFF-bipolar cell | `ZFA:0009000` | — | yes |
| `ZFA:0009364` | olfactory epithelial support cell | `ZFA:0009000` | — | yes |
| `ZFA:0001694` | olfactory granule cell | `ZFA:0009000` | — |  |
| `ZFA:0009125` | olfactory receptor cell | `ZFA:0009000` | — |  |
| `ZFA:0000688` | olfactory support cell | `ZFA:0009000` | — |  |
| `ZFA:0009076` | oligodendrocyte | `ZFA:0009000` | — | yes |
| `ZFA:0009319` | ON-bipolar cell | `ZFA:0009000` | — | yes |
| `ZFA:0001109` | oocyte | `ZFA:0009000` | — |  |
| `ZFA:0001567` | oocyte stage I | `ZFA:0009000` | — | yes |
| `ZFA:0001565` | oocyte stage II | `ZFA:0009000` | — | yes |
| `ZFA:0001566` | oocyte stage III | `ZFA:0009000` | — | yes |
| `ZFA:0001568` | oocyte stage IV | `ZFA:0009000` | — | yes |
| `ZFA:0001569` | oocyte stage V | `ZFA:0009000` | — | yes |
| `ZFA:0005878` | oogonia | `ZFA:0009000` | — |  |
| `ZFA:0009031` | osteoblast | `ZFA:0009000` | — | yes |
| `ZFA:0009047` | osteoclast | `ZFA:0009000` | — | yes |
| `ZFA:0009083` | osteocyte | `ZFA:0009000` | — |  |
| `ZFA:0009184` | osteoprogenitor cell | `ZFA:0009000` | — | yes |
| `ZFA:0009164` | oxygen accumulating cell | `ZFA:0009000` | — | yes |
| `ZFA:0009119` | pain receptor cell | `ZFA:0009000` | — | yes |
| `ZFA:0009104` | pancreatic A cell | `ZFA:0009000` | — |  |
| `ZFA:0005739` | pancreatic acinar cell | `ZFA:0009000` | — |  |
| `ZFA:0009102` | pancreatic B cell | `ZFA:0009000` | — |  |
| `ZFA:0005740` | pancreatic centroacinar cell | `ZFA:0009000` | — |  |
| `ZFA:0005743` | pancreatic D cell | `ZFA:0009000` | — |  |
| `ZFA:0009380` | pancreatic ductal cell | `ZFA:0009000` | — |  |
| `ZFA:0005598` | pancreatic epsilon cell | `ZFA:0009000` | — |  |
| `ZFA:0005742` | pancreatic PP cell | `ZFA:0009000` | — |  |
| `ZFA:0009233` | paracrine cell | `ZFA:0009000` | — | yes |
| `ZFA:0009260` | parafollicular cell | `ZFA:0009000` | — | yes |
| `ZFA:0005776` | parasympathetic neuron | `ZFA:0009000` | — |  |
| `ZFA:0009207` | parathyroid hormone secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0009100` | peptide hormone secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0009062` | peptidergic neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009312` | periarticular chondrocyte | `ZFA:0009000` | — | yes |
| `ZFA:0009112` | pericyte | `ZFA:0009000` | — | yes |
| `ZFA:0009041` | peridermal cell | `ZFA:0009000` | — | yes |
| `ZFA:0009296` | perijunctional fibroblast | `ZFA:0009000` | — | yes |
| `ZFA:0009237` | perineuronal satellite cell | `ZFA:0009000` | — | yes |
| `ZFA:0009063` | peripheral neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009267` | peritoneal macrophage | `ZFA:0009000` | — | yes |
| `ZFA:0009140` | phagocyte | `ZFA:0009000` | — | yes |
| `ZFA:0009220` | photopic photoreceptor cell | `ZFA:0009000` | — | yes |
| `ZFA:0009127` | photoreceptor cell | `ZFA:0009000` | — | yes |
| `ZFA:0009090` | pigment cell | `ZFA:0009000` | — | yes |
| `ZFA:0009170` | pigment cell (sensu Vertebrata) | `ZFA:0009000` | — | yes |
| `ZFA:0005331` | pigment erythroblast | `ZFA:0009000` | — | yes |
| `ZFA:0009241` | pigmented epithelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009284` | pinealocyte | `ZFA:0009000` | — |  |
| `ZFA:0009066` | pioneer neuron | `ZFA:0009000` | — |  |
| `ZFA:0009332` | plasma cell | `ZFA:0009000` | — | yes |
| `ZFA:0009285` | podocyte | `ZFA:0009000` | — |  |
| `ZFA:0005241` | polychromatophilic erythroblast | `ZFA:0009000` | — | yes |
| `ZFA:0009054` | polymodal neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009344` | precursor B cell | `ZFA:0009000` | — | yes |
| `ZFA:0007090` | premigratory cranial neural crest cell | `ZFA:0009000` | — | yes |
| `ZFA:0007084` | premigratory neural crest cell | `ZFA:0009000` | — | yes |
| `ZFA:0007094` | premigratory trunk neural crest cell | `ZFA:0009000` | — | yes |
| `ZFA:0009274` | pressoreceptor cell | `ZFA:0009000` | — | yes |
| `ZFA:0009245` | primary interneuron | `ZFA:0009000` | — | yes |
| `ZFA:0009244` | primary motor neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009242` | primary neuron | `ZFA:0009000` | — | yes |
| `ZFA:0000821` | primary neuron hindbrain | `ZFA:0009000` | — | yes |
| `ZFA:0009288` | primordial germ cell | `ZFA:0009000` | — |  |
| `ZFA:0009349` | pro-B cell | `ZFA:0009000` | — | yes |
| `ZFA:0009348` | pro-NK cell | `ZFA:0009000` | — | yes |
| `ZFA:0009350` | pro-T cell | `ZFA:0009000` | — |  |
| `ZFA:0009088` | professional antigen presenting cell | `ZFA:0009000` | — | yes |
| `ZFA:0009109` | progesterone secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0009204` | prolactin secreting cell | `ZFA:0009000` | — |  |
| `ZFA:0009253` | promonocyte | `ZFA:0009000` | — | yes |
| `ZFA:0001673` | pronephric podocyte | `ZFA:0009000` | — |  |
| `ZFA:0005968` | pseudobranch cell | `ZFA:0009000` | — | yes |
| `ZFA:0009057` | pseudounipolar neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009071` | Purkinje cell | `ZFA:0009000` | — |  |
| `ZFA:0009273` | pyramidal cell | `ZFA:0009000` | — | yes |
| `ZFA:0009292` | radial glial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009001` | receptor cell (sensu Animalia) | `ZFA:0009000` | — | yes |
| `ZFA:0009224` | red sensitive photoreceptor cell | `ZFA:0009000` | — | yes |
| `ZFA:0005246` | regeneration fibroblast | `ZFA:0009000` | — | yes |
| `ZFA:0009376` | renal alpha-intercalated cell | `ZFA:0009000` | — | yes |
| `ZFA:0009375` | renal intercalated cell | `ZFA:0009000` | — | yes |
| `ZFA:0005322` | renal principal cell | `ZFA:0009000` | — |  |
| `ZFA:0009200` | reticular cell | `ZFA:0009000` | — | yes |
| `ZFA:0009252` | reticulocyte | `ZFA:0009000` | — | yes |
| `ZFA:0005865` | reticulospinal neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009318` | retinal bipolar neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009262` | retinal cone cell | `ZFA:0009000` | — | yes |
| `ZFA:0009310` | retinal ganglion cell | `ZFA:0009000` | — |  |
| `ZFA:0009275` | retinal rod cell | `ZFA:0009000` | — | yes |
| `ZFA:0005804` | rhombencephalic efferent neurons to the lateral line | `ZFA:0009000` | — |  |
| `ZFA:0005805` | rhombencephalic octavolateral efferent neuron | `ZFA:0009000` | — |  |
| `ZFA:0009321` | rod bipolar cell | `ZFA:0009000` | — | yes |
| `ZFA:0009150` | Rohon-Beard neuron | `ZFA:0009000` | — | yes |
| `ZFA:0005192` | RoI2C | `ZFA:0009000` | — | yes |
| `ZFA:0005193` | RoI2R | `ZFA:0009000` | — | yes |
| `ZFA:0005194` | RoL1 | `ZFA:0009000` | — | yes |
| `ZFA:0005198` | RoL2 | `ZFA:0009000` | — | yes |
| `ZFA:0005200` | RoL2c | `ZFA:0009000` | — | yes |
| `ZFA:0005199` | RoL2r | `ZFA:0009000` | — | yes |
| `ZFA:0005201` | RoL3 | `ZFA:0009000` | — | yes |
| `ZFA:0005202` | RoM1c | `ZFA:0009000` | — | yes |
| `ZFA:0005203` | RoM1r | `ZFA:0009000` | — | yes |
| `ZFA:0005205` | RoM2l | `ZFA:0009000` | — | yes |
| `ZFA:0005206` | RoM2m | `ZFA:0009000` | — | yes |
| `ZFA:0005207` | RoM3l | `ZFA:0009000` | — | yes |
| `ZFA:0005208` | RoM3m | `ZFA:0009000` | — | yes |
| `ZFA:0005180` | RoP motor neuron | `ZFA:0009000` | — | yes |
| `ZFA:0005204` | RoV3 | `ZFA:0009000` | — | yes |
| `ZFA:0009174` | scleral cell | `ZFA:0009000` | — |  |
| `ZFA:0009247` | secondary motor neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009246` | secondary neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009160` | seminal fluid secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0009050` | sensory epithelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009053` | sensory neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009185` | sensory processing neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009361` | serotonergic neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009213` | serotonin secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0009133` | Sertoli cell | `ZFA:0009000` | — |  |
| `ZFA:0005946` | short double cone cell | `ZFA:0009000` | — | yes |
| `ZFA:0005948` | short single cone cell | `ZFA:0009000` | — | yes |
| `ZFA:0005152` | silver iridophore | `ZFA:0009000` | — | yes |
| `ZFA:0009089` | simple columnar epithelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0005243` | single ciliated epithelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009013` | single fate stem cell | `ZFA:0009000` | — | yes |
| `ZFA:0009115` | skeletal muscle cell | `ZFA:0009000` | — | yes |
| `ZFA:0009236` | skeletal muscle myoblast | `ZFA:0009000` | — | yes |
| `ZFA:0009272` | skeletal muscle satellite cell | `ZFA:0009000` | — | yes |
| `ZFA:0009116` | slow muscle cell | `ZFA:0009000` | — | yes |
| `ZFA:0000963` | slow muscle cell somite 1 | `ZFA:0009000` | — | yes |
| `ZFA:0001047` | slow muscle cell somite 10 | `ZFA:0009000` | — | yes |
| `ZFA:0000840` | slow muscle cell somite 11 | `ZFA:0009000` | — | yes |
| `ZFA:0000964` | slow muscle cell somite 12 | `ZFA:0009000` | — | yes |
| `ZFA:0001048` | slow muscle cell somite 13 | `ZFA:0009000` | — | yes |
| `ZFA:0000841` | slow muscle cell somite 14 | `ZFA:0009000` | — | yes |
| `ZFA:0000965` | slow muscle cell somite 15 | `ZFA:0009000` | — | yes |
| `ZFA:0001049` | slow muscle cell somite 16 | `ZFA:0009000` | — | yes |
| `ZFA:0000842` | slow muscle cell somite 17 | `ZFA:0009000` | — | yes |
| `ZFA:0000966` | slow muscle cell somite 18 | `ZFA:0009000` | — | yes |
| `ZFA:0001050` | slow muscle cell somite 19 | `ZFA:0009000` | — | yes |
| `ZFA:0000843` | slow muscle cell somite 2 | `ZFA:0009000` | — | yes |
| `ZFA:0000967` | slow muscle cell somite 20 | `ZFA:0009000` | — | yes |
| `ZFA:0000719` | slow muscle cell somite 21 | `ZFA:0009000` | — | yes |
| `ZFA:0000844` | slow muscle cell somite 22 | `ZFA:0009000` | — | yes |
| `ZFA:0000969` | slow muscle cell somite 23 | `ZFA:0009000` | — | yes |
| `ZFA:0000720` | slow muscle cell somite 24 | `ZFA:0009000` | — | yes |
| `ZFA:0000845` | slow muscle cell somite 25 | `ZFA:0009000` | — | yes |
| `ZFA:0000970` | slow muscle cell somite 26 | `ZFA:0009000` | — | yes |
| `ZFA:0000721` | slow muscle cell somite 27 | `ZFA:0009000` | — | yes |
| `ZFA:0000846` | slow muscle cell somite 28 | `ZFA:0009000` | — | yes |
| `ZFA:0000971` | slow muscle cell somite 29 | `ZFA:0009000` | — | yes |
| `ZFA:0000722` | slow muscle cell somite 3 | `ZFA:0009000` | — | yes |
| `ZFA:0000847` | slow muscle cell somite 30 | `ZFA:0009000` | — | yes |
| `ZFA:0000972` | slow muscle cell somite 4 | `ZFA:0009000` | — | yes |
| `ZFA:0000723` | slow muscle cell somite 5 | `ZFA:0009000` | — | yes |
| `ZFA:0000848` | slow muscle cell somite 6 | `ZFA:0009000` | — | yes |
| `ZFA:0000973` | slow muscle cell somite 7 | `ZFA:0009000` | — | yes |
| `ZFA:0000724` | slow muscle cell somite 8 | `ZFA:0009000` | — | yes |
| `ZFA:0000850` | slow muscle cell somite 9 | `ZFA:0009000` | — | yes |
| `ZFA:0009368` | slow muscle myoblast | `ZFA:0009000` | — | yes |
| `ZFA:0009118` | smooth muscle cell | `ZFA:0009000` | — | yes |
| `ZFA:0009235` | smooth muscle myoblast | `ZFA:0009000` | — | yes |
| `ZFA:0009386` | somatic cell | `ZFA:0009000` | — | yes |
| `ZFA:0009307` | somatic stem cell | `ZFA:0009000` | — | yes |
| `ZFA:0005733` | somatomotor neuron | `ZFA:0009000` | — |  |
| `ZFA:0009105` | somatostatin secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0009155` | somatotropin secreting cell | `ZFA:0009000` | — |  |
| `ZFA:0009006` | sperm | `ZFA:0009000` | — | yes |
| `ZFA:0005769` | spermatid | `ZFA:0009000` | — |  |
| `ZFA:0009005` | spermatocyte | `ZFA:0009000` | — |  |
| `ZFA:0009007` | spermatogonium | `ZFA:0009000` | — |  |
| `ZFA:0009311` | spinal accessory motor neuron | `ZFA:0009000` | — | yes |
| `ZFA:0000778` | spinal cord interneuron | `ZFA:0009000` | — |  |
| `ZFA:0005874` | spiral neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009039` | squamous epithelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009072` | stellate cell | `ZFA:0009000` | — | yes |
| `ZFA:0009297` | stellate interneuron | `ZFA:0009000` | — | yes |
| `ZFA:0005957` | stem cell | `ZFA:0009000` | — | yes |
| `ZFA:0009106` | steroid hormone secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0009145` | stratified cuboidal epithelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009042` | stratified epithelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009180` | stratified epithelial stem cell | `ZFA:0009000` | — | yes |
| `ZFA:0009371` | stratified keratinized epithelial stem cell | `ZFA:0009000` | — | yes |
| `ZFA:0009144` | stratified squamous epithelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009370` | stretch receptor cell | `ZFA:0009000` | — | yes |
| `ZFA:0005784` | striated muscle cell | `ZFA:0009000` | — | yes |
| `ZFA:0005965` | striolar hair cell | `ZFA:0009000` | — |  |
| `ZFA:0009226` | stromal cell | `ZFA:0009000` | — | yes |
| `ZFA:0005745` | structural cell | `ZFA:0009000` | — | yes |
| `ZFA:0009230` | substance P secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0001484` | superficial blastomere | `ZFA:0009000` | — | yes |
| `ZFA:0009387` | supportive cell | `ZFA:0009000` | — | yes |
| `ZFA:0009302` | sustentacular cell | `ZFA:0009000` | — | yes |
| `ZFA:0005777` | sympathetic neuron | `ZFA:0009000` | — |  |
| `ZFA:0009131` | synovial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009046` | T cell | `ZFA:0009000` | — | yes |
| `ZFA:0005815` | T interneuron | `ZFA:0009000` | — | yes |
| `ZFA:0009126` | taste receptor cell | `ZFA:0009000` | — |  |
| `ZFA:0009189` | tendon cell | `ZFA:0009000` | — | yes |
| `ZFA:0009298` | terminal Schwann cell | `ZFA:0009000` | — |  |
| `ZFA:0009107` | testosterone secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0005565` | tether cell | `ZFA:0009000` | — | yes |
| `ZFA:0009229` | theca cell | `ZFA:0009000` | — | yes |
| `ZFA:0009123` | thermoreceptor cell | `ZFA:0009000` | — | yes |
| `ZFA:0009351` | thromboblast | `ZFA:0009000` | — | yes |
| `ZFA:0009323` | thrombocyte | `ZFA:0009000` | — | yes |
| `ZFA:0009210` | thyroid hormone secreting cell | `ZFA:0009000` | — | yes |
| `ZFA:0009218` | thyroid stimulating hormone secreting cell | `ZFA:0009000` | — |  |
| `ZFA:0009024` | totipotent stem cell | `ZFA:0009000` | — | yes |
| `ZFA:0009148` | transitional epithelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009345` | transitional stage B cell | `ZFA:0009000` | — | yes |
| `ZFA:0005768` | trigeminal sensory neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009004` | trunk neural crest cell | `ZFA:0009000` | — | yes |
| `ZFA:0005235` | UCoD | `ZFA:0009000` | — | yes |
| `ZFA:0001570` | unfertilized egg | `ZFA:0009000` | — | yes |
| `ZFA:0009058` | unipolar neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009308` | urothelial cell | `ZFA:0009000` | — | yes |
| `ZFA:0009221` | UV sensitive photoreceptor cell | `ZFA:0009000` | — | yes |
| `ZFA:0005181` | VaP motor neuron | `ZFA:0009000` | — | yes |
| `ZFA:0009181` | vascular associated smooth muscle cell | `ZFA:0009000` | — | yes |
| `ZFA:0009395` | vascular lymphangioblast | `ZFA:0009000` | — | yes |
| `ZFA:0005177` | VeLD | `ZFA:0009000` | — | yes |
| `ZFA:0005969` | VeMe | `ZFA:0009000` | — | yes |
| `ZFA:0007121` | ventral cerebrospinal fluid contacting neuron | `ZFA:0009000` | — | yes |
| `ZFA:0005866` | vestibulospinal neuron | `ZFA:0009000` | — | yes |
| `ZFA:0005327` | vH ionocyte | `ZFA:0009000` | — | yes |
| `ZFA:0005732` | visceromotor neuron | `ZFA:0009000` | — |  |
| `ZFA:0009219` | visible light photoreceptor cell | `ZFA:0009000` | — | yes |
| `ZFA:0009171` | visual pigment cell (sensu Vertebrata) | `ZFA:0009000` | — |  |
| `ZFA:0005245` | xanthoblast | `ZFA:0009000` | — | yes |
| `ZFA:0005929` | xantholeucophore | `ZFA:0009000` | — | yes |
| `ZFA:0009198` | xanthophore | `ZFA:0009000` | — | yes |
| `ZFA:0000084` | yolk | `ZFA:0009000` | — | yes |

### `anatomical_cluster` (162)

| Id | Name | Source class | explicit_germ_layer | Stranded |
| --- | --- | --- | --- | --- |
| `ZFA:0001420` | anal fin pterygiophore | `ZFA:0001478` | — |  |
| `ZFA:0001478` | anatomical cluster | `ZFA:0001478` | — |  |
| `ZFA:0005618` | anguloarticular-retroarticular joint | `ZFA:0001478` | — |  |
| `ZFA:0001472` | anterior lateral line neuromast | `ZFA:0001478` | — |  |
| `ZFA:0005566` | anterior segment eye | `ZFA:0001478` | — |  |
| `ZFA:0005917` | anterior-posterior polarized neuromast | `ZFA:0001478` | — |  |
| `ZFA:0005920` | anterior-posterior polarized posterior lateral line neuromast | `ZFA:0001478` | — |  |
| `ZFA:0001702` | apical ectodermal ridge | `ZFA:0001478` | — |  |
| `ZFA:0000090` | apical ectodermal ridge dorsal fin | `ZFA:0001478` | — |  |
| `ZFA:0000717` | apical ectodermal ridge median fin fold | `ZFA:0001478` | — |  |
| `ZFA:0000085` | apical ectodermal ridge pectoral fin bud | `ZFA:0001478` | — |  |
| `ZFA:0001450` | apical ectodermal ridge pelvic fin | `ZFA:0001478` | — |  |
| `ZFA:0001385` | apical ectodermal ridge pelvic fin bud | `ZFA:0001478` | — |  |
| `ZFA:0005420` | autopalatine-lateral ethmoid joint | `ZFA:0001478` | — |  |
| `ZFA:0005421` | autopalatine-maxillary joint | `ZFA:0001478` | — |  |
| `ZFA:0005656` | autopalatine-preethmoid joint | `ZFA:0001478` | — |  |
| `ZFA:0005422` | autopalatine-vomer joint | `ZFA:0001478` | — |  |
| `ZFA:0005423` | basioccipital-exoccipital joint | `ZFA:0001478` | — |  |
| `ZFA:0005613` | basioccipital-prootic joint | `ZFA:0001478` | — |  |
| `ZFA:0005531` | bony shelf above orbit | `ZFA:0001478` | — |  |
| `ZFA:0005590` | capillary loop nephron | `ZFA:0001478` | — |  |
| `ZFA:0005155` | cartilaginous joint | `ZFA:0001478` | — |  |
| `ZFA:0005465` | ceratohyal-branchiostegal ray joint | `ZFA:0001478` | — |  |
| `ZFA:0005467` | ceratohyal-dorsal hypohyal joint | `ZFA:0001478` | — |  |
| `ZFA:0005859` | ceratohyal-interhyal joint | `ZFA:0001478` | — |  |
| `ZFA:0005466` | ceratohyal-ventral hypohyal joint | `ZFA:0001478` | — |  |
| `ZFA:0005870` | cerebellar plate ventral proliferative layer | `ZFA:0001478` | — |  |
| `ZFA:0001424` | chondrocranium | `ZFA:0001478` | — |  |
| `ZFA:0001289` | ciliary marginal zone | `ZFA:0001478` | — |  |
| `ZFA:0005588` | comma-shaped body | `ZFA:0001478` | — |  |
| `ZFA:0005606` | cranial vault | `ZFA:0001478` | — |  |
| `ZFA:0005464` | dentary-anguloarticular joint | `ZFA:0001478` | — |  |
| `ZFA:0000863` | dermatocranium | `ZFA:0001478` | — |  |
| `ZFA:0005584` | developing mesonephric nephron | `ZFA:0001478` | — |  |
| `ZFA:0001419` | dorsal fin pterygiophore | `ZFA:0001478` | — |  |
| `ZFA:0005364` | dorsal fin pterygiophore 1 | `ZFA:0001478` | — |  |
| `ZFA:0005365` | dorsal fin pterygiophore 2 | `ZFA:0001478` | — |  |
| `ZFA:0005366` | dorsal fin pterygiophore 3 | `ZFA:0001478` | — |  |
| `ZFA:0005367` | dorsal fin pterygiophore 4 | `ZFA:0001478` | — |  |
| `ZFA:0005368` | dorsal fin pterygiophore 5 | `ZFA:0001478` | — |  |
| `ZFA:0005369` | dorsal fin pterygiophore 6 | `ZFA:0001478` | — |  |
| `ZFA:0005370` | dorsal fin pterygiophore 7 | `ZFA:0001478` | — |  |
| `ZFA:0005371` | dorsal fin pterygiophore 8 | `ZFA:0001478` | — |  |
| `ZFA:0001401` | dorsal hyoid arch | `ZFA:0001478` | — |  |
| `ZFA:0005457` | dorsal hypohyal-urohyal joint | `ZFA:0001478` | — |  |
| `ZFA:0005458` | dorsal hypohyal-ventral hypohyal joint | `ZFA:0001478` | — |  |
| `ZFA:0005113` | dorsal lateral line neuromast | `ZFA:0001478` | — |  |
| `ZFA:0001140` | dorsal tooth row | `ZFA:0001478` | — |  |
| `ZFA:0005918` | dorsal-ventral polarized neuromast | `ZFA:0001478` | — |  |
| `ZFA:0005919` | dorsal-ventral polarized posterior lateral line neuromast | `ZFA:0001478` | — |  |
| `ZFA:0005958` | early palate | `ZFA:0001478` | — |  |
| `ZFA:0005612` | ectopterygoid-entopterygoid joint | `ZFA:0001478` | — |  |
| `ZFA:0005611` | ectopterygoid-quadrate joint | `ZFA:0001478` | — |  |
| `ZFA:0005614` | entopterygoid-metapterygoid joint | `ZFA:0001478` | — |  |
| `ZFA:0005498` | epihyal-branchiostegal ray joint | `ZFA:0001478` | — |  |
| `ZFA:0005497` | epihyal-ceratohyal joint | `ZFA:0001478` | — |  |
| `ZFA:0005891` | epiotic-parietal joint | `ZFA:0001478` | — |  |
| `ZFA:0005889` | epiotic-posttemporal joint | `ZFA:0001478` | — |  |
| `ZFA:0005872` | external granular layer of the cerebellar plate | `ZFA:0001478` | — |  |
| `ZFA:0005156` | fibrous joint | `ZFA:0001478` | — |  |
| `ZFA:0005608` | frontal-parietal joint | `ZFA:0001478` | — |  |
| `ZFA:0005468` | frontal-pterotic joint | `ZFA:0001478` | — |  |
| `ZFA:0005469` | hyomandibula-metapterygoid joint | `ZFA:0001478` | — |  |
| `ZFA:0005626` | hyomandibula-opercle joint | `ZFA:0001478` | — |  |
| `ZFA:0005627` | hyomandibula-pterotic joint | `ZFA:0001478` | — |  |
| `ZFA:0005544` | hyomandibular-otic region joint | `ZFA:0001478` | — |  |
| `ZFA:0000813` | infraorbital lateral line neuromast | `ZFA:0001478` | — |  |
| `ZFA:0001649` | infraorbital series | `ZFA:0001478` | — |  |
| `ZFA:0000217` | inner ear | `ZFA:0001478` | — |  |
| `ZFA:0005471` | inter-basipterygium joint | `ZFA:0001478` | — |  |
| `ZFA:0005470` | inter-coracoid joint | `ZFA:0001478` | — |  |
| `ZFA:0005472` | inter-frontal joint | `ZFA:0001478` | — |  |
| `ZFA:0005474` | inter-hypobranchial 3 joint | `ZFA:0001478` | — |  |
| `ZFA:0005607` | inter-parietal joint | `ZFA:0001478` | — |  |
| `ZFA:0005475` | inter-premaxillary joint | `ZFA:0001478` | — |  |
| `ZFA:0005476` | inter-ventral hypohyal joint | `ZFA:0001478` | — |  |
| `ZFA:0005473` | interhyal-epihyal joint | `ZFA:0001478` | — |  |
| `ZFA:0005860` | interhyal-hyosymplectic joint | `ZFA:0001478` | — |  |
| `ZFA:0001341` | intervening zone | `ZFA:0001478` | — |  |
| `ZFA:0001596` | joint | `ZFA:0001478` | — |  |
| `ZFA:0001627` | lagenar capsule | `ZFA:0001478` | — |  |
| `ZFA:0000531` | lateral column | `ZFA:0001478` | — |  |
| `ZFA:0005477` | lateral ethmoid-frontal joint | `ZFA:0001478` | — |  |
| `ZFA:0005617` | lateral ethmoid-supraethmoid | `ZFA:0001478` | — |  |
| `ZFA:0005634` | lepidotrichium joint | `ZFA:0001478` | — |  |
| `ZFA:0001227` | mandibular arch skeleton | `ZFA:0001478` | — |  |
| `ZFA:0000125` | mandibular lateral line neuromast | `ZFA:0001478` | — |  |
| `ZFA:0005488` | mandibular symphysis | `ZFA:0001478` | — |  |
| `ZFA:0007117` | Meckel's cartilage-palatoquadrate cartilage joint | `ZFA:0001478` | — |  |
| `ZFA:0000542` | medial column | `ZFA:0001478` | — |  |
| `ZFA:0001139` | mediodorsal tooth row | `ZFA:0001478` | — |  |
| `ZFA:0005648` | mesethmoid-lateral ethmoid joint | `ZFA:0001478` | — |  |
| `ZFA:0005649` | mesethmoid-vomer joint | `ZFA:0001478` | — |  |
| `ZFA:0005592` | mesonephric nephron | `ZFA:0001478` | — |  |
| `ZFA:0000939` | middle lateral line neuromast | `ZFA:0001478` | — |  |
| `ZFA:0000241` | midline column | `ZFA:0001478` | — |  |
| `ZFA:0005282` | nephron | `ZFA:0001478` | — |  |
| `ZFA:0001363` | neural complex | `ZFA:0001478` | — |  |
| `ZFA:0001580` | neurocranium | `ZFA:0001478` | — |  |
| `ZFA:0000243` | neuromast | `ZFA:0001478` | — |  |
| `ZFA:0001025` | occipital lateral line neuromast | `ZFA:0001478` | — |  |
| `ZFA:0001414` | occipital region | `ZFA:0001478` | — |  |
| `ZFA:0000351` | olfactory region | `ZFA:0001478` | — |  |
| `ZFA:0005861` | opercle-hyosymplectic joint | `ZFA:0001478` | — |  |
| `ZFA:0005478` | opercle-interopercle joint | `ZFA:0001478` | — |  |
| `ZFA:0000814` | opercular lateral line neuromast | `ZFA:0001478` | — |  |
| `ZFA:0000590` | oral region | `ZFA:0001478` | — |  |
| `ZFA:0001410` | orbital region | `ZFA:0001478` | — |  |
| `ZFA:0005479` | orbitosphenoid-lateral ethmoid joint | `ZFA:0001478` | — |  |
| `ZFA:0005480` | orbitosphenoid-prootic joint | `ZFA:0001478` | — |  |
| `ZFA:0000136` | otic lateral line neuromast | `ZFA:0001478` | — |  |
| `ZFA:0000189` | otic region | `ZFA:0001478` | — |  |
| `ZFA:0005509` | palate | `ZFA:0001478` | — |  |
| `ZFA:0001272` | palatoquadrate arch | `ZFA:0001478` | — |  |
| `ZFA:0005753` | pancreatic lobule | `ZFA:0001478` | — |  |
| `ZFA:0005560` | parasphenoid-basioccipital joint | `ZFA:0001478` | — |  |
| `ZFA:0005410` | pars inferior ear | `ZFA:0001478` | — |  |
| `ZFA:0005409` | pars superior ear | `ZFA:0001478` | — |  |
| `ZFA:0000407` | pectoral girdle | `ZFA:0001478` | — |  |
| `ZFA:0000565` | pelvic girdle | `ZFA:0001478` | — |  |
| `ZFA:0007115` | pericardial region | `ZFA:0001478` | — |  |
| `ZFA:0001276` | pharyngeal arch 2 skeleton | `ZFA:0001478` | — |  |
| `ZFA:0001228` | pharyngeal arch 3 skeleton | `ZFA:0001478` | — |  |
| `ZFA:0000095` | pharyngeal arch 3-7 skeleton | `ZFA:0001478` | — |  |
| `ZFA:0001231` | pharyngeal arch 4 skeleton | `ZFA:0001478` | — |  |
| `ZFA:0001232` | pharyngeal arch 5 skeleton | `ZFA:0001478` | — |  |
| `ZFA:0001230` | pharyngeal arch 6 skeleton | `ZFA:0001478` | — |  |
| `ZFA:0001229` | pharyngeal arch 7 skeleton | `ZFA:0001478` | — |  |
| `ZFA:0007116` | pleuroperitoneal region | `ZFA:0001478` | — |  |
| `ZFA:0000940` | posterior lateral line neuromast | `ZFA:0001478` | — |  |
| `ZFA:0005567` | posterior segment eye | `ZFA:0001478` | — |  |
| `ZFA:0005631` | preopercle horizontal limb-symplectic joint | `ZFA:0001478` | — |  |
| `ZFA:0005632` | preopercle vertical limb-hyomandibula joint | `ZFA:0001478` | — |  |
| `ZFA:0000098` | proliferative region | `ZFA:0001478` | — |  |
| `ZFA:0005481` | prootic-exoccipital joint | `ZFA:0001478` | — |  |
| `ZFA:0005482` | prootic-pterosphenoid joint | `ZFA:0001478` | — |  |
| `ZFA:0005227` | protoneuromast | `ZFA:0001478` | — |  |
| `ZFA:0005483` | pterosphenoid-orbitosphenoid joint | `ZFA:0001478` | — |  |
| `ZFA:0005484` | quadrate-anguloarticular joint | `ZFA:0001478` | — |  |
| `ZFA:0005616` | quadrate-entopterygoid joint | `ZFA:0001478` | — |  |
| `ZFA:0005485` | quadrate-hyomandibula joint | `ZFA:0001478` | — |  |
| `ZFA:0005486` | quadrate-metapterygoid joint | `ZFA:0001478` | — |  |
| `ZFA:0005589` | s-shaped body | `ZFA:0001478` | — |  |
| `ZFA:0000290` | sphenoid region | `ZFA:0001478` | — |  |
| `ZFA:0001216` | splanchnocranium | `ZFA:0001478` | — |  |
| `ZFA:0005609` | supraoccipital-parietal joint | `ZFA:0001478` | — |  |
| `ZFA:0001026` | supraorbital lateral line neuromast | `ZFA:0001478` | — |  |
| `ZFA:0000444` | suspensorium | `ZFA:0001478` | — |  |
| `ZFA:0005610` | synostosis | `ZFA:0001478` | — |  |
| `ZFA:0005153` | synovial joint | `ZFA:0001478` | — |  |
| `ZFA:0001642` | tooth row | `ZFA:0001478` | — |  |
| `ZFA:0001402` | ventral hyoid arch | `ZFA:0001478` | — |  |
| `ZFA:0005487` | ventral hypohyal-urohyal joint | `ZFA:0001478` | — |  |
| `ZFA:0001273` | ventral mandibular arch | `ZFA:0001478` | — |  |
| `ZFA:0001137` | ventral tooth row | `ZFA:0001478` | — |  |
| `ZFA:0001083` | ventricular zone | `ZFA:0001478` | — |  |
| `ZFA:0005504` | vertebra 4-vertebra 5 joint | `ZFA:0001478` | — |  |
| `ZFA:0005505` | vertebra 5-vertebra 6 joint | `ZFA:0001478` | — |  |
| `ZFA:0005506` | vertebra 6 - vertebra 7 joint | `ZFA:0001478` | — |  |
| `ZFA:0001559` | vertebral column | `ZFA:0001478` | — |  |
| `ZFA:0000611` | visceromotor column | `ZFA:0001478` | — |  |
| `ZFA:0001188` | Weberian apparatus | `ZFA:0001478` | — |  |

### `anatomical_group` (6)

| Id | Name | Source class | explicit_germ_layer | Stranded |
| --- | --- | --- | --- | --- |
| `ZFA:0001512` | anatomical group | `ZFA:0001512` | — |  |
| `ZFA:0005954` | cardiac lymphatic endothelial cluster | `ZFA:0001512` | — |  |
| `ZFA:0000112` | gut | `ZFA:0001512` | endoderm |  |
| `ZFA:0005955` | lymphatic endothelial cluster | `ZFA:0001512` | — |  |
| `ZFA:0001359` | pineal complex | `ZFA:0001512` | — |  |
| `ZFA:0000421` | reticular formation | `ZFA:0001512` | — |  |

### `organism_subdivision` (67)

| Id | Name | Source class | explicit_germ_layer | Stranded |
| --- | --- | --- | --- | --- |
| `ZFA:0001162` | anal fin | `ZFA:0000292` | — |  |
| `ZFA:0001427` | anterior naris | `ZFA:0000292` | — |  |
| `ZFA:0005407` | anterior nasal barbel | `ZFA:0000292` | — |  |
| `ZFA:0000092` | axis | `ZFA:0001308` | — |  |
| `ZFA:0000006` | ball | `ZFA:0001308` | — |  |
| `ZFA:0000622` | barbel | `ZFA:0000292` | — |  |
| `ZFA:0005119` | barbel primordium | `ZFA:0000292` | — |  |
| `ZFA:0005791` | breeding tubercle | `ZFA:0000292` | — |  |
| `ZFA:0001058` | caudal fin | `ZFA:0000292` | — |  |
| `ZFA:0001605` | caudal fin lower lobe | `ZFA:0000292` | — |  |
| `ZFA:0001604` | caudal fin upper lobe | `ZFA:0000292` | — |  |
| `ZFA:0000178` | caudal peduncle | `ZFA:0001308` | — |  |
| `ZFA:0001173` | dorsal fin | `ZFA:0000292` | — |  |
| `ZFA:0005221` | dorsal larval melanophore stripe | `ZFA:0000292` | — |  |
| `ZFA:0000106` | extension | `ZFA:0001308` | — |  |
| `ZFA:0000108` | fin | `ZFA:0000292` | — |  |
| `ZFA:0001383` | fin bud | `ZFA:0000292` | — |  |
| `ZFA:0001114` | head | `ZFA:0001308` | — |  |
| `ZFA:0005508` | inner mental barbel | `ZFA:0000292` | — |  |
| `ZFA:0000368` | integument | `ZFA:0000292` | — |  |
| `ZFA:0005792` | jaw flap | `ZFA:0000292` | — |  |
| `ZFA:0005799` | jaw flap breeding tubercle | `ZFA:0000292` | — |  |
| `ZFA:0005798` | jaw row breeding tubercle | `ZFA:0000292` | — |  |
| `ZFA:0005220` | larval melanophore stripe | `ZFA:0000292` | — |  |
| `ZFA:0005223` | lateral larval melanophore stripe | `ZFA:0000292` | — |  |
| `ZFA:0005530` | lateral line scale | `ZFA:0000292` | — |  |
| `ZFA:0007006` | lip | `ZFA:0000292` | — |  |
| `ZFA:0005225` | lower lip | `ZFA:0000292` | — |  |
| `ZFA:0005597` | median fin | `ZFA:0000292` | — |  |
| `ZFA:0000040` | median fin fold | `ZFA:0000292` | — |  |
| `ZFA:0001463` | melanophore stripe | `ZFA:0000292` | — |  |
| `ZFA:0005433` | mental barbel | `ZFA:0000292` | — |  |
| `ZFA:0000547` | mouth | `ZFA:0000292` | — |  |
| `ZFA:0000550` | naris | `ZFA:0000292` | — |  |
| `ZFA:0001328` | neuromere | `ZFA:0001308` | — |  |
| `ZFA:0000555` | opercular flap | `ZFA:0000292` | — |  |
| `ZFA:0001308` | organism subdivision | `ZFA:0001308` | — |  |
| `ZFA:0005596` | paired fin | `ZFA:0000292` | — |  |
| `ZFA:0001161` | pectoral fin | `ZFA:0000292` | — |  |
| `ZFA:0005797` | pectoral fin breeding tubercle | `ZFA:0000292` | — |  |
| `ZFA:0000141` | pectoral fin bud | `ZFA:0000292` | — |  |
| `ZFA:0001184` | pelvic fin | `ZFA:0000292` | — |  |
| `ZFA:0001384` | pelvic fin bud | `ZFA:0000292` | — |  |
| `ZFA:0001117` | post-vent region | `ZFA:0001308` | — |  |
| `ZFA:0001426` | posterior naris | `ZFA:0000292` | — |  |
| `ZFA:0000066` | proctodeum | `ZFA:0000292` | — |  |
| `ZFA:0001269` | regenerating fin | `ZFA:0000292` | — |  |
| `ZFA:0001064` | rhombomere | `ZFA:0001308` | — |  |
| `ZFA:0001031` | rhombomere 1 | `ZFA:0001308` | — |  |
| `ZFA:0000822` | rhombomere 2 | `ZFA:0001308` | — |  |
| `ZFA:0000948` | rhombomere 3 | `ZFA:0001308` | — |  |
| `ZFA:0001032` | rhombomere 4 | `ZFA:0001308` | — |  |
| `ZFA:0000823` | rhombomere 5 | `ZFA:0001308` | — |  |
| `ZFA:0000069` | rhombomere 6 | `ZFA:0001308` | — |  |
| `ZFA:0000949` | rhombomere 7 | `ZFA:0001308` | — |  |
| `ZFA:0000153` | rhombomere 8 | `ZFA:0001308` | — |  |
| `ZFA:0000277` | scale | `ZFA:0000292` | — |  |
| `ZFA:0005495` | skin flap | `ZFA:0000292` | — |  |
| `ZFA:0005496` | snout | `ZFA:0001308` | — |  |
| `ZFA:0001290` | stomodeum | `ZFA:0000292` | — |  |
| `ZFA:0000292` | surface structure | `ZFA:0000292` | — |  |
| `ZFA:0001115` | trunk | `ZFA:0001308` | — |  |
| `ZFA:0005226` | upper lip | `ZFA:0000292` | — |  |
| `ZFA:0001118` | urogenital papilla | `ZFA:0000292` | — |  |
| `ZFA:0000298` | vent | `ZFA:0000292` | — |  |
| `ZFA:0005222` | ventral larval melanophore stripe | `ZFA:0000292` | — |  |
| `ZFA:0005224` | yolk larval melanophore stripe | `ZFA:0000292` | — |  |

### `anatomical_space` (67)

| Id | Name | Source class | explicit_germ_layer | Stranded |
| --- | --- | --- | --- | --- |
| `ZFA:0001643` | anatomical space | `ZFA:0001643` | — |  |
| `ZFA:0005876` | anterior chamber eye | `ZFA:0001643` | — |  |
| `ZFA:0005406` | anterior myodome | `ZFA:0001643` | — |  |
| `ZFA:0005442` | articular fossa of opercle | `ZFA:0001643` | — |  |
| `ZFA:0005460` | atrium of sinus impar | `ZFA:0001643` | — |  |
| `ZFA:0005418` | auditory fenestra | `ZFA:0001643` | — |  |
| `ZFA:0005419` | auditory foramen | `ZFA:0001643` | — |  |
| `ZFA:0005453` | basicapsular fenestra | `ZFA:0001643` | — |  |
| `ZFA:0005163` | bile canaliculus | `ZFA:0001643` | — |  |
| `ZFA:0007073` | blood sinus cavity | `ZFA:0001643` | — |  |
| `ZFA:0005890` | carotid artery canal | `ZFA:0001643` | — |  |
| `ZFA:0001075` | choroidal fissure | `ZFA:0001643` | — |  |
| `ZFA:0000330` | cloacal chamber | `ZFA:0001643` | — |  |
| `ZFA:0005426` | coracoid foramen | `ZFA:0001643` | — |  |
| `ZFA:0005427` | dentary foramen | `ZFA:0001643` | — |  |
| `ZFA:0005536` | fontanel | `ZFA:0001643` | — |  |
| `ZFA:0005386` | foramen | `ZFA:0001643` | — |  |
| `ZFA:0005387` | foramen magnum | `ZFA:0001643` | — |  |
| `ZFA:0005388` | fossa | `ZFA:0001643` | — |  |
| `ZFA:0005389` | gill opening | `ZFA:0001643` | — |  |
| `ZFA:0005893` | glossopharyngeal foramen | `ZFA:0001643` | — |  |
| `ZFA:0005629` | hyomandibular foramen | `ZFA:0001643` | — |  |
| `ZFA:0005625` | hypophyseal fenestra | `ZFA:0001643` | — |  |
| `ZFA:0005960` | hypural diastema | `ZFA:0001643` | — |  |
| `ZFA:0005415` | inner ear foramen | `ZFA:0001643` | — |  |
| `ZFA:0005782` | intestinal opening | `ZFA:0001643` | — |  |
| `ZFA:0005807` | intestine lumen | `ZFA:0001643` | — |  |
| `ZFA:0000695` | labial cavity | `ZFA:0001643` | — |  |
| `ZFA:0005736` | lacuna | `ZFA:0001643` | — |  |
| `ZFA:0005735` | lacunocanalicular canal | `ZFA:0001643` | — |  |
| `ZFA:0005537` | lateral fontanel of frontal | `ZFA:0001643` | — |  |
| `ZFA:0005892` | lateral occipital foramen | `ZFA:0001643` | — |  |
| `ZFA:0000231` | lateral recess | `ZFA:0001643` | — |  |
| `ZFA:0005930` | lumen | `ZFA:0001643` | — |  |
| `ZFA:0005615` | metapterygoid-symplectic fenestra | `ZFA:0001643` | — |  |
| `ZFA:0005446` | neuromast foramen | `ZFA:0001643` | — |  |
| `ZFA:0005429` | olfactory nerve foramen | `ZFA:0001643` | — |  |
| `ZFA:0000130` | olfactory pit | `ZFA:0001643` | — |  |
| `ZFA:0001654` | opercular cavity | `ZFA:0001643` | — |  |
| `ZFA:0005428` | optic foramen | `ZFA:0001643` | — |  |
| `ZFA:0000049` | optic recess | `ZFA:0001643` | — |  |
| `ZFA:0001027` | oral cavity | `ZFA:0001643` | — |  |
| `ZFA:0005558` | orbit | `ZFA:0001643` | — |  |
| `ZFA:0005430` | orbital foramen | `ZFA:0001643` | — |  |
| `ZFA:0001655` | pericardial cavity | `ZFA:0001643` | — |  |
| `ZFA:0005459` | perilymphatic space | `ZFA:0001643` | — |  |
| `ZFA:0001656` | pleuroperitoneal cavity | `ZFA:0001643` | — |  |
| `ZFA:0005449` | pore | `ZFA:0001643` | — |  |
| `ZFA:0005338` | posterior recess | `ZFA:0001643` | — |  |
| `ZFA:0005628` | posttemporal fossa | `ZFA:0001643` | — |  |
| `ZFA:0005312` | pronephric capsular space | `ZFA:0001643` | — |  |
| `ZFA:0001055` | pronephric duct opening | `ZFA:0001643` | — |  |
| `ZFA:0005510` | prootic depression | `ZFA:0001643` | — |  |
| `ZFA:0005455` | prootic foramen | `ZFA:0001643` | — |  |
| `ZFA:0005630` | pterotic fossa | `ZFA:0001643` | — |  |
| `ZFA:0001283` | pupil | `ZFA:0001643` | — |  |
| `ZFA:0005283` | renal capsular space | `ZFA:0001643` | — |  |
| `ZFA:0005416` | sacculoagenar foramen | `ZFA:0001643` | — |  |
| `ZFA:0005431` | scapular foramen | `ZFA:0001643` | — |  |
| `ZFA:0005884` | seminiferous tubule lumen | `ZFA:0001643` | — |  |
| `ZFA:0005456` | sinus impar | `ZFA:0001643` | — |  |
| `ZFA:0005492` | sphenotic-prootic fossa | `ZFA:0001643` | — |  |
| `ZFA:0005454` | subtemporal fossa | `ZFA:0001643` | — |  |
| `ZFA:0005432` | superficial ophthalmic nerve foramen | `ZFA:0001643` | — |  |
| `ZFA:0005895` | trigeminal-facial chamber | `ZFA:0001643` | — |  |
| `ZFA:0005417` | utriculosaccular foramen | `ZFA:0001643` | — |  |
| `ZFA:0005894` | vagus foramen | `ZFA:0001643` | — |  |

### `acellular_structure` (19)

| Id | Name | Source class | explicit_germ_layer | Stranded |
| --- | --- | --- | --- | --- |
| `ZFA:0000382` | acellular anatomical structure | `ZFA:0000382` | — |  |
| `ZFA:0001485` | basal lamina | `ZFA:0000382` | — |  |
| `ZFA:0001684` | Bowman's layer | `ZFA:0000382` | — |  |
| `ZFA:0005562` | Bruch's membrane | `ZFA:0000382` | — |  |
| `ZFA:0001186` | collagenous dermal stroma | `ZFA:0000382` | — |  |
| `ZFA:0001686` | Descemet's membrane | `ZFA:0000382` | — |  |
| `ZFA:0005285` | glomerular basement membrane | `ZFA:0000382` | — |  |
| `ZFA:0000671` | horizontal myoseptum | `ZFA:0000382` | — |  |
| `ZFA:0001029` | inner limiting membrane | `ZFA:0000382` | — |  |
| `ZFA:0005286` | lamina densa | `ZFA:0000382` | — |  |
| `ZFA:0005288` | lamina rara externa | `ZFA:0000382` | — |  |
| `ZFA:0005287` | lamina rara interna | `ZFA:0000382` | — |  |
| `ZFA:0005574` | lens capsule | `ZFA:0000382` | — |  |
| `ZFA:0001089` | myoseptum | `ZFA:0000382` | — |  |
| `ZFA:0001331` | outer limiting membrane | `ZFA:0000382` | — |  |
| `ZFA:0005313` | pronephric glomerular basement membrane | `ZFA:0000382` | — |  |
| `ZFA:0005434` | tooth cusp | `ZFA:0000382` | — |  |
| `ZFA:0000610` | vertical myoseptum | `ZFA:0000382` | — |  |
| `ZFA:0001111` | zona radiata | `ZFA:0000382` | — |  |

### `organism_substance` (19)

| Id | Name | Source class | explicit_germ_layer | Stranded |
| --- | --- | --- | --- | --- |
| `ZFA:0005564` | aqueous humor | `ZFA:0001487` | — |  |
| `ZFA:0000315` | asteriscus | `ZFA:0001487` | — |  |
| `ZFA:0005857` | bile | `ZFA:0001487` | — |  |
| `ZFA:0000007` | blood | `ZFA:0001487` | — |  |
| `ZFA:0005654` | blood plasma | `ZFA:0001487` | — |  |
| `ZFA:0001626` | cerebral spinal fluid | `ZFA:0001487` | — |  |
| `ZFA:0005803` | cupula | `ZFA:0001487` | — |  |
| `ZFA:0005414` | endolymph | `ZFA:0001487` | — |  |
| `ZFA:0005800` | extracellular lipid lamellae | `ZFA:0001487` | — |  |
| `ZFA:0000530` | lapillus | `ZFA:0001487` | — |  |
| `ZFA:0005658` | lymph | `ZFA:0001487` | — |  |
| `ZFA:0001617` | otolith | `ZFA:0001487` | — |  |
| `ZFA:0005413` | perilymph | `ZFA:0001487` | — |  |
| `ZFA:0001487` | portion of organism substance | `ZFA:0001487` | — |  |
| `ZFA:0000676` | sagitta | `ZFA:0001487` | — |  |
| `ZFA:0005154` | synovial fluid | `ZFA:0001487` | — |  |
| `ZFA:0005913` | urine | `ZFA:0001487` | — |  |
| `ZFA:0005561` | vitreous | `ZFA:0001487` | — |  |
| `ZFA:0005573` | zonule | `ZFA:0001487` | — |  |

### `embryonic_structure` (86)

| Id | Name | Source class | explicit_germ_layer | Stranded |
| --- | --- | --- | --- | --- |
| `ZFA:0001316` | anterior lateral line placode | `ZFA:0001105` | — |  |
| `ZFA:0001369` | anterior pancreatic bud | `ZFA:0001105` | endoderm |  |
| `ZFA:0000091` | axial chorda mesoderm | `ZFA:0001105` | — |  |
| `ZFA:0001176` | blastoderm | `ZFA:0001105` | — |  |
| `ZFA:0001175` | blastodisc | `ZFA:0001105` | — |  |
| `ZFA:0000000` | Brachet's cleft | `ZFA:0001105` | — |  |
| `ZFA:0000711` | DEL | `ZFA:0001105` | — |  |
| `ZFA:0005582` | dorsal proneural cluster | `ZFA:0001105` | — |  |
| `ZFA:0001310` | dorsolateral placode | `ZFA:0001105` | — |  |
| `ZFA:0001105` | embryonic structure | `ZFA:0001105` | — |  |
| `ZFA:0000018` | epiblast | `ZFA:0001105` | — |  |
| `ZFA:0001294` | epibranchial placode | `ZFA:0001105` | — |  |
| `ZFA:0000086` | EVL | `ZFA:0001105` | — |  |
| `ZFA:0001295` | facial placode | `ZFA:0001105` | — |  |
| `ZFA:0000023` | forerunner cell group | `ZFA:0001105` | — |  |
| `ZFA:0000111` | germ ring | `ZFA:0001105` | — |  |
| `ZFA:0001296` | glossopharyngeal placode | `ZFA:0001105` | — |  |
| `ZFA:0000026` | hatching gland | `ZFA:0001105` | — |  |
| `ZFA:0000117` | hypoblast | `ZFA:0001105` | — |  |
| `ZFA:0000001` | Kupffer's vesicle | `ZFA:0001105` | — |  |
| `ZFA:0000124` | liver primordium | `ZFA:0001105` | endoderm |  |
| `ZFA:0000038` | margin | `ZFA:0001105` | — |  |
| `ZFA:0005121` | middle lateral line placode | `ZFA:0001105` | — |  |
| `ZFA:0001309` | neurogenic placode | `ZFA:0001105` | — |  |
| `ZFA:0000048` | olfactory placode | `ZFA:0001105` | — |  |
| `ZFA:0000138` | otic placode | `ZFA:0001105` | — |  |
| `ZFA:0000051` | otic vesicle | `ZFA:0001105` | — |  |
| `ZFA:0000254` | pancreas primordium | `ZFA:0001105` | — |  |
| `ZFA:0001390` | pancreatic bud | `ZFA:0001105` | — |  |
| `ZFA:0001453` | pectoral fin field | `ZFA:0001105` | — |  |
| `ZFA:0000058` | polster | `ZFA:0001105` | — |  |
| `ZFA:0001156` | posterior lateral line placode | `ZFA:0001105` | — |  |
| `ZFA:0001370` | posterior pancreatic bud | `ZFA:0001105` | — |  |
| `ZFA:0000568` | presumptive blood | `ZFA:0001105` | — |  |
| `ZFA:0000146` | presumptive brain | `ZFA:0001105` | — |  |
| `ZFA:0000414` | presumptive cephalic mesoderm | `ZFA:0001105` | — |  |
| `ZFA:0000574` | presumptive diencephalon | `ZFA:0001105` | — |  |
| `ZFA:0005104` | presumptive dorsal fin fold | `ZFA:0001105` | — |  |
| `ZFA:0000265` | presumptive dorsal mesoderm | `ZFA:0001105` | — |  |
| `ZFA:0001376` | presumptive ectoderm | `ZFA:0001105` | — |  |
| `ZFA:0000416` | presumptive endoderm | `ZFA:0001105` | — |  |
| `ZFA:0001334` | presumptive enteric nervous system | `ZFA:0001105` | — |  |
| `ZFA:0001218` | presumptive floor plate | `ZFA:0001105` | — |  |
| `ZFA:0000062` | presumptive forebrain | `ZFA:0001105` | — |  |
| `ZFA:0001368` | presumptive forebrain midbrain boundary | `ZFA:0001105` | — |  |
| `ZFA:0000569` | presumptive hindbrain | `ZFA:0001105` | — |  |
| `ZFA:0001217` | presumptive hypochord | `ZFA:0001105` | — |  |
| `ZFA:0001342` | presumptive intervening zone | `ZFA:0001105` | — |  |
| `ZFA:0005911` | presumptive lateral nucleus of ventral telencephalon | `ZFA:0001105` | — |  |
| `ZFA:0005102` | presumptive median fin fold | `ZFA:0001105` | — |  |
| `ZFA:0001377` | presumptive mesoderm | `ZFA:0001105` | — |  |
| `ZFA:0000148` | presumptive midbrain | `ZFA:0001105` | — |  |
| `ZFA:0001187` | presumptive midbrain hindbrain boundary | `ZFA:0001105` | — |  |
| `ZFA:0000063` | presumptive neural plate | `ZFA:0001105` | — |  |
| `ZFA:0000591` | presumptive paraxial mesoderm | `ZFA:0001105` | — |  |
| `ZFA:0005909` | presumptive preglomerular region | `ZFA:0001105` | — |  |
| `ZFA:0005908` | presumptive pretectum proliferative zone | `ZFA:0001105` | — |  |
| `ZFA:0001070` | presumptive pronephric mesoderm | `ZFA:0001105` | — |  |
| `ZFA:0001207` | presumptive rhombomere 1 | `ZFA:0001105` | — |  |
| `ZFA:0001208` | presumptive rhombomere 2 | `ZFA:0001105` | — |  |
| `ZFA:0001213` | presumptive rhombomere 3 | `ZFA:0001105` | — |  |
| `ZFA:0001212` | presumptive rhombomere 4 | `ZFA:0001105` | — |  |
| `ZFA:0001211` | presumptive rhombomere 5 | `ZFA:0001105` | — |  |
| `ZFA:0001210` | presumptive rhombomere 6 | `ZFA:0001105` | — |  |
| `ZFA:0001209` | presumptive rhombomere 7 | `ZFA:0001105` | — |  |
| `ZFA:0001214` | presumptive rhombomere 8 | `ZFA:0001105` | — |  |
| `ZFA:0000053` | presumptive segmental plate | `ZFA:0001105` | — |  |
| `ZFA:0001121` | presumptive shield | `ZFA:0001105` | — |  |
| `ZFA:0000417` | presumptive spinal cord | `ZFA:0001105` | — |  |
| `ZFA:0001116` | presumptive structure | `ZFA:0001105` | — |  |
| `ZFA:0005336` | presumptive swim bladder | `ZFA:0001105` | endoderm |  |
| `ZFA:0000571` | presumptive telencephalon | `ZFA:0001105` | — |  |
| `ZFA:0005910` | presumptive ventral entopeduncular nucleus | `ZFA:0001105` | — |  |
| `ZFA:0005103` | presumptive ventral fin fold | `ZFA:0001105` | — |  |
| `ZFA:0001714` | presumptive ventral mesoderm | `ZFA:0001105` | — |  |
| `ZFA:0000068` | proneural cluster | `ZFA:0001105` | — |  |
| `ZFA:0000071` | shield | `ZFA:0001105` | — |  |
| `ZFA:0005335` | swim bladder bud | `ZFA:0001105` | endoderm |  |
| `ZFA:0000077` | tail bud | `ZFA:0001105` | — |  |
| `ZFA:0000162` | trigeminal placode | `ZFA:0001105` | — |  |
| `ZFA:0001297` | vagal placode 1 | `ZFA:0001105` | — |  |
| `ZFA:0001298` | vagal placode 2 | `ZFA:0001105` | — |  |
| `ZFA:0001299` | vagal placode 3 | `ZFA:0001105` | — |  |
| `ZFA:0001300` | vagal placode 4 | `ZFA:0001105` | — |  |
| `ZFA:0005583` | ventral proneural cluster | `ZFA:0001105` | — |  |
| `ZFA:0000088` | yolk syncytial layer | `ZFA:0001105` | — |  |

### `extraembryonic_structure` (3)

| Id | Name | Source class | explicit_germ_layer | Stranded |
| --- | --- | --- | --- | --- |
| `ZFA:0000329` | chorion | `ZFA:0000020` | — |  |
| `ZFA:0000020` | extraembryonic structure | `ZFA:0000020` | — |  |
| `ZFA:0005943` | perivitelline fluid | `ZFA:0000020` | — |  |

### `anatomical_line` (15)

| Id | Name | Source class | explicit_germ_layer | Stranded |
| --- | --- | --- | --- | --- |
| `ZFA:0001689` | anatomical line | `ZFA:0001689` | — |  |
| `ZFA:0005570` | corneo-scleral junction | `ZFA:0001689` | — |  |
| `ZFA:0001388` | epithelial mesenchymal boundary | `ZFA:0001689` | — |  |
| `ZFA:0001367` | forebrain midbrain boundary | `ZFA:0001689` | — |  |
| `ZFA:0007027` | forebrain midbrain boundary neural keel | `ZFA:0001689` | — |  |
| `ZFA:0007020` | forebrain midbrain boundary neural plate | `ZFA:0001689` | — |  |
| `ZFA:0007033` | forebrain midbrain boundary neural rod | `ZFA:0001689` | — |  |
| `ZFA:0007040` | forebrain midbrain boundary neural tube | `ZFA:0001689` | — |  |
| `ZFA:0000042` | midbrain hindbrain boundary | `ZFA:0001689` | — |  |
| `ZFA:0007045` | midbrain hindbrain boundary neural keel | `ZFA:0001689` | — |  |
| `ZFA:0007044` | midbrain hindbrain boundary neural plate | `ZFA:0001689` | — |  |
| `ZFA:0007046` | midbrain hindbrain boundary neural rod | `ZFA:0001689` | — |  |
| `ZFA:0007047` | midbrain hindbrain boundary neural tube | `ZFA:0001689` | — |  |
| `ZFA:0001343` | telencephalon diencephalon boundary | `ZFA:0001689` | — |  |
| `ZFA:0001344` | zona limitans intrathalamica | `ZFA:0001689` | — |  |

### `anatomical_surface` (2)

| Id | Name | Source class | explicit_germ_layer | Stranded |
| --- | --- | --- | --- | --- |
| `ZFA:0005594` | anatomical surface | `ZFA:0005594` | — |  |
| `ZFA:0001462` | somite border | `ZFA:0005594` | — |  |

### `whole_organism` (3)

| Id | Name | Source class | explicit_germ_layer | Stranded |
| --- | --- | --- | --- | --- |
| `ZFA:0000303` | female organism | `ZFA:0000303` | — |  |
| `ZFA:0000242` | male organism | `ZFA:0000242` | — |  |
| `ZFA:0001094` | whole organism | `ZFA:0001094` | — |  |

### `other_unclassified_anatomical_entity` (19)

| Id | Name | Source class | explicit_germ_layer | Stranded |
| --- | --- | --- | --- | --- |
| `ZFA:0007114` | anatomical conduit | — | — |  |
| `ZFA:0000037` | anatomical structure | — | — |  |
| `ZFA:0000314` | anterior semicircular canal | — | — |  |
| `ZFA:0001640` | cephalic flexure | — | — |  |
| `ZFA:0005499` | circulus | — | — |  |
| `ZFA:0001690` | groove | — | — |  |
| `ZFA:0000220` | lateral semicircular canal | — | — |  |
| `ZFA:0005593` | neuraxis flexure | — | — |  |
| `ZFA:0001284` | optic fissure | — | — |  |
| `ZFA:0005491` | optic furrow | — | — |  |
| `ZFA:0000262` | posterior semicircular canal | — | — |  |
| `ZFA:0005899` | scale focus | — | — |  |
| `ZFA:0005900` | scale radius | — | — |  |
| `ZFA:0000431` | semicircular canal | — | — |  |
| `ZFA:0000589` | sulcus ypsiloniformis | — | — |  |
| `ZFA:0005901` | superior ocular sulcus | — | — |  |
| `ZFA:0001093` | unspecified | — | — |  |
| `ZFA:0000305` | ventral sulcus | — | — |  |
| `ZFA:0100000` | zebrafish anatomical entity | — | — |  |


