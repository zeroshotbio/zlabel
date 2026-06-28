# ZFA relationship types — what they mean and which ones zlabel uses

A plain-language map of the edges in the Zebrafish Anatomy Ontology (ZFA), because the browser labels
("has parts", "develops into", "is a type of"…) hide a simple structure — and because **which edges
zlabel walks turns out to be the single biggest lever on what it can label.**

## The five things an edge can be

ZFA is a directed graph. Every term has edges going **up** (to broader parents) and **down** (to more
specific children). The browser shows both directions of the same relation under different names:

| Browser label (up ↑ / down ↓) | OBO edge | count | zlabel walks it? | where |
|---|---|---:|:--:|---|
| "is a type of" ↑ / "has subtype" ↓ | `is_a` | 3,266 | **yes** | ancestor credit, descent, IC |
| "is part of" ↑ / "has parts" ↓ | `part_of` | 2,206 | **yes** | ancestor credit, descent, IC |
| "develops from" ↑ / "develops into" ↓ | `develops_from` | 527 | **no** | tracked, never walked |
| stage bounds | `start` / `end` | 3,106 ea. | indirect | ZFS stage plausibility only |
| overlaps, has_developmental_contribution_from, immediately_preceded_by, continuous_with | minor | <70 total | no | — |

Two of these are *identity* relations and one is a *lineage* relation:

- **`is_a` — taxonomy.** "X is a kind of Y." An endothelial cell *is a* lining cell. Walking it up
  generalises; walking it down specialises. This is what an annotation ladder is made of.
- **`part_of` — composition.** "X is a part of Y." The retina is *part of* the eye. Same idea, but
  mereological (whole/part) instead of taxonomic (kind-of).
- **`develops_from` — lineage/history.** "X develops from Y" (and inversely "Y develops into X"). The
  retina *develops from* the optic cup; mesoderm *develops into* chondroblasts. This is a *timeline*,
  not a statement about what a cell currently *is*.

zlabel's descent (`resolve.py`) seeds at a curated panel anchor and walks **down `is_a` + `part_of`
only** (`data.py:31`, `DEFAULT_ANCESTOR_EDGE_TYPES`). `develops_from` is loaded but deliberately never
walked — the documented reason is that lineage is not identity: you should not label a cell by the
thing it came from. That reasoning is sound in one direction and costly in the other, which is the
whole point below.

## Worked example 1 — retina (your example), and why ignoring lineage is *correct* here

`retina` (ZFA:0000152, tier **T2**) has these edges:

```
↑ is a type of   multi-tissue structure        [T5]   (is_a → a content-free container)
↑ is part of     posterior segment eye          [T3]   (part_of → a coarse region)
↑ develops from  optic cup                       [T1]   (develops_from → its embryonic precursor)
↓ has parts      retinal neural layer            [T1]   (part_of child — descent CAN reach)
↓ has parts      retinal pigmented epithelium    [T1]   (part_of child — descent CAN reach)
↓ has parts      ciliary marginal zone           [T1]   (part_of child — descent CAN reach)
↓ has parts      visual pigment cell (sensu Vert.)[T4]   (part_of child, but ungrounded)
```

Read it top to bottom: the `is_a` parent of retina is the **T5 junk container** "multi-tissue
structure" — proof that walking *up* `is_a` often lands on a useless term (which is fine; we never
*name* upward). The useful sub-structures (neural layer, RPE, ciliary marginal zone) hang off
`part_of` **down**, which the descent does follow — so retina resolves well today. And `develops from
optic cup` is exactly the case the exclusion is right about: a retina cluster should **not** be
labelled "optic cup" (its embryonic past). **Ignoring `develops_from` here loses nothing.**

## Worked example 2 — mesoderm (your example), and why ignoring lineage is *costly* here

`mesoderm` (ZFA:0000041, tier **T3**) tells the opposite story:

```
↑ is a type of   primary germ layer              [T3]
↑ develops from  presumptive mesoderm            [T1]   (precursor — fine to ignore)
↓ has subtype    paraxial / axial / lateral plate / pronephric / … mesoderm   [T1]   (is_a children — sub-REGIONS)
↓ has parts      presumptive segmental plate, presumptive cephalic mesoderm, mesodermal cell [T1]   (part_of children)
↓ develops into  chondroblast                    [T1]   ← a real cell type, IGNORED
↓ develops into  blood vessel endothelial cell   [T1]   ← a real cell type, IGNORED
↓ develops into  muscle precursor cell           [T2]   ← a real cell type, IGNORED
```

From the mesoderm anchor, the `is_a`/`part_of` descent can only reach **more mesoderm regions** and the
generic **"mesodermal cell."** The actual differentiated cell types a mesoderm cluster turns into —
chondroblast, blood vessel endothelial cell, muscle precursor cell — sit on the **`develops_into`
axis the descent never follows.** So a cluster of differentiating mesoderm with chondroblast markers
can, at best, be called "mesodermal cell"; the precise, useful term is one ignored edge away.

(Caveat: some of these are reachable from a *different* anchor via `is_a` — e.g. an endothelial cluster
is named through the endothelium panel. The rigorous count below is of terms reachable **only** via
`develops_from`, with no `is_a`/`part_of` path from any anchor.)

## The asymmetry that matters

`develops_from` has two directions and they are not equally safe to ignore:

- **Up (`develops from` → precursor):** "retina develops from optic cup." Walking up would label a
  cell by its history. **Correctly ignored.**
- **Down (`develops into` → derivative):** "mesoderm develops into chondroblast." Walking down reaches
  the *mature identity* a progenitor is becoming. **This is the coverage we lose** — but it crosses
  from progenitor to mature cell, so it must be gated by marker support, not followed blindly.

## What it costs, in numbers

Recomputing reachability from zlabel's 42 panel anchors (reproduce: `score_terms.py` reach helper):

| reach edges | reachable terms | useful (T1/T2) reachable |
|---|---:|---|
| `is_a` + `part_of` (today) | 2,131 | T1 647/964 · T2 344/481 |
| + `develops_from` | 2,450 (+319) | T1 703/964 · T2 390/481 |

**+102 useful (T1/T2) terms become reachable** when `develops_into` is followed — somite, otic vesicle,
endoderm, neuron (neural-crest derived), swim bladder, dermal bone, splanchnocranium, and more — none
of which the descent can reach today by any `is_a`/`part_of` path.

## Why this is the lever (and what's next)

The phase-1 audit proved the engine **never emits a useless label** (0 of 176 named Daniocell calls are
junk-tier — the `CONVERGENCE_MIN` and descent-from-curated-anchor floors already guarantee it). So the
opportunity is not in *blocking* bad terms; it is in *reaching* good ones. The descent is bounded by
**which edges it walks** and **where the panel anchors sit** — and the `develops_into` axis is the
largest unwalked slice of the anatomy→cell-type structure.

Phase 3 tests this directly: a **gated** prototype that lets the descent follow `develops_into`
(progenitor → marker-supported derivative), measured on `make gate-all` — the bar is *more correct
named calls without raising the parent-child overcall audit*, respecting the documented
attractor-selection wall (`design.md`). If it regresses, that is a real answer too.

> Edges are ZFA `releases/2026-06-02`. The minor relations (`overlaps`, `has_developmental_contribution_from`,
> `immediately_preceded_by`, `continuous_with`; <70 edges total) are too sparse to matter and are not
> walked. `start`/`end` link terms to ZFS developmental stages and feed stage plausibility, not the DAG walk.
