# Cross-atlas marker broadening — research record

How `panels.yaml` was widened from a Daniocell-tuned starter set into a cross-atlas-generalizable
one, and the evidence that it worked without trading precision. This is the durable record behind the
[`panels_and_markers_reference.md`](panels_and_markers_reference.md) provenance tables and the
[`docs/design.md`](../design.md) Validation section.

## 1. The problem — recall, not taxonomy

zlabel scores a cluster's markers against 33 curated panels, then descends the ZFA ontology from the
winning panel's anchor. The panels were curated and validated almost entirely against **Daniocell**.
Run on a second atlas (**ZSCAPE / Trapnell**), zlabel kept its accuracy but abstained far more —
**21.9% coverage** vs Daniocell's 37%. The cause was measured directly:

- The panel marker vocabulary was **~196 unique symbols**.
- The **median ZSCAPE cluster had only ~6%** of its markers in that vocabulary — ~94% of a typical
  cluster's canonical markers were invisible to the panels.
- The missing genes were **textbook identity markers, not noise**: muscle lacked the mature
  sarcomere set (`ttn.1`, `neb`, `smyhc1`), endothelium lacked `egfl7`/`flt4`, neurons lacked
  subtype genes (`nova2`, `elavl4`), the kidney tubule lacked its transporters.

Nearly every atlas tissue already had a bucket and a ZFA anchor — the taxonomy was complete. The
failure was **recall**: the engine couldn't see canonical markers written in a vocabulary it didn't
carry. So the fix is a **marker-vocabulary broadening, not a rebuild** — and it is the principled
alternative to forcing a guess on a low-coverage cluster (see §5, the forcing frontier).

## 2. The anti-bias firewall

The danger in widening panels against more atlases is trading Daniocell-bias for
Daniocell+ZSCAPE-bias. The firewall is a strict separation of roles:

- **Tier 1 — justification (what makes a marker legitimate).** ZFIN curated wildtype expression
  grounding under the panel's ZFA anchor, plus primary literature. This is **non-circular against the
  atlases**: ZFIN does not curate scRNA into its gene→anatomy records (those records derive
  from curated experimental literature — ISH/IHC — not scRNA DE lists), so grounding a marker in ZFIN
  cannot memorize a benchmark.
- **Tier 2 — seeds (candidate generation only).** Atlas DE marker lists nominate genes to research.
  A gene is added because Tier 1 confirms it, **never because it appears in an atlas's DE**. The
  `cite` rule in `panels.yaml` forbids sourcing from any benchmark's computed markers.
- **Validation — held-out atlases, leave-one-atlas-out.** Daniocell is the hard byte-gate; ZSCAPE
  and Zebrahub are held-out directional walls. A marker is accepted only if it improves an atlas and
  **does not regress the others** — both move the right way, or one improves and the rest hold, never
  a trade. (This is what rejected `cdh16`; see §4.)

**Reliability** of a marker = canonical-ness (literature) × ZFIN grounding × specificity tier ×
cross-source recurrence. A gene cited by ZFIN and literature and recurring across atlases is the most
generalizable; a single-atlas DE gene is the most bias-prone and is never added on that basis alone.

**Specificity is the load-bearing constraint.** The documented attractor wall (§6) shows that broad
panels over-attract *because their markers are promiscuous*, not because they are large. So every
addition is specificity-checked at curation time (`scripts/audit_panels.py`): adding a *sharp* marker
raises a panel's mean specificity and mitigates its attractor tendency; adding a *promiscuous* one
worsens it. The audit fails an attractor panel that gains a promiscuous marker.

## 3. Resource map (verified June 2026)

| Resource | Role | Access / license | Circularity |
|---|---|---|---|
| **ZFIN wildtype expression** | Tier 1 — the grounding gate | bulk TSV; research/education only | None — no scRNA curated in |
| **ZFIN GAF synonyms / aliases** | symbol normalization | bulk TSV | n/a |
| **Primary literature** | Tier 1 — canonical citation | per-marker | None |
| **Daniocell** | Tier 2 seed + hard validation | committed `benchmarks/` CSV | Seed only; gold-blind grading |
| **ZSCAPE** | Tier 2 seed + held-out validation | committed `benchmarks/` CSV | Seed only |
| **Zebrahub** | Tier 2 seed + held-out validation (ZFA-native obs) | figshare CC-BY | Independent lab/design |
| **ZCL** | candidate seed (deferred) | GEO/figshare CC-BY | Independent |
| **CZI Dev atlas** | secondary validation (deferred) | Discover REST API, CC-BY | ZSCAPE-sibling (same lab/method) |
| **CellMarker 2.0 / PanglaoDB** | cross-species seed (deferred) | CC-BY / free | Mammal-only; usable only via ortholog→ZFIN-grounding |
| **ZFAP.org** | ❌ NO-GO | web-only, no API/license | Text-mined PubMed abstracts frozen ~2012; ZFIN dominates it |

License flag: ZFIN is research/education-only without written permission. zlabel complies (`data/` is
gitignored, fetched not redistributed); for any **commercial** deployment this clause is a real flag.

## 4. What shipped — per-lineage additions

Seven lineages were broadened; the rest are walls (§6). Every added marker is a current ZFIN symbol
that grounds under its panel anchor. Full provenance is in
[`panels_and_markers_reference.md`](panels_and_markers_reference.md); the `cite` strings in
`panels.yaml` carry the ZFIN/literature attribution.

| Lineage | Added (spine) | Held out, and why |
|---|---|---|
| neural | `nova2`, `elavl4`, `srrm4`, `rbfox3a` (sharp subtype/differentiation) | `rbfox1` (promiscuous) |
| muscle | `ttn.1`, `neb`, `smyhc1`, `actc1b`, `ryr1a` (mature sarcomere) | cardiac `ttn.2`/`actc1a`/`tpm1` (wrong lineage) |
| endothelium | `egfl7`, `stab2`, `flt4` (sharp; raise mean specificity 0.30→0.38) | `esama` (promiscuous — trips the attractor guard) |
| pronephros | `aqp8b`, `slc26a1` (tubule transporters) | `cdh16` (KSP-cadherin: over-called the ZSCAPE thyroid cluster, which shares `pax2a`) |
| ionocyte | `clcn2c`, `slc4a4b`, `atp1a1a.1` (ion-transport effectors) | — (canonical but promiscuous; allowed only because ionocyte is not an attractor) |
| interrenal | `cyp21a2` (steroid 21-hydroxylase) | — |
| notochord | `matn3a`, `matn3b`, `chad` (sheath ECM) | — |

The held-out column is the firewall working: `esama` would inflate the endothelium attractor;
`cdh16` would buy a Daniocell call at the cost of a ZSCAPE over-call — a trade we decline.

## 5. Results — before / after

The committed baselines just before the broadening arc (commit `b91f75e`) vs current. The neural PR
bundled a glia crosswalk correction with its markers; the rest of the delta is the marker broadening.

| Atlas | Coverage | Accuracy | Overcalls |
|---|---|---|---|
| Daniocell (hard gate) | 37.2% → **42.7%** | 71.8% (107/149) → **76.1% (134/176)** | 5 → 5 |
| ZSCAPE (held-out) | 21.9% → **47.9%** | 88.9% (16/18) → 87.5% (35/40) | 0 → 0 |
| Zebrahub (held-out, N=3) | 22.2% → **33.3%** | 100% (2/2) → 100% (3/3) | 0 → 0 |

Coverage rose on every atlas — **ZSCAPE more than doubled** — while accuracy **improved on Daniocell**
(71.8 → 76.1%) and **held on the held-out atlases**: ZSCAPE within ~1 point on a larger, more stable N
(18 → 40 calls), and Zebrahub's 3/3 is too small to read as accuracy evidence. Thin-support overcalls
stayed flat (5 / 0 / 0). No precision was traded for the recall. (Median vocab-hit-rate, the leading
indicator, rose on ZSCAPE 6% → 8%; Daniocell held at 12%.)

### The forcing frontier

The numbers above are **no-forcing**: zlabel scores its calls as-is and abstains honestly. Forcing is
a *caller-side* option the `Label` enables (it surfaces `candidates` + an `ood` trust flag); the eval
never applies it. **Soft-set** forcing commits the top candidate only on the force-able (`ood ==
in_set`) abstentions. The broadening sharpens the high-precision no-forcing regime most. (Here
**before** is the *intermediate* state — after neural/muscle/endothelium, before the final four
lineages — the increment over which the forcing analysis was run, so this baseline differs from §5's
pre-arc one.)

| Atlas | Mode | Accuracy (before → after) | Coverage (before → after) |
|---|---|---|---|
| Daniocell | no-forcing | 74.0% → **76.1%** | 42.1% → 42.7% |
| Daniocell | soft-set | 59.8% → 60.7% | 78.3% → 77.9% |
| ZSCAPE | no-forcing | 87.2% → 87.5% | 46.9% → **47.9%** |
| ZSCAPE | soft-set | 67.7% → 68.2% | 74.0% → 75.0% |

Soft-set roughly doubles coverage but costs ~15–20 points of accuracy — the selection wall (§7): the
gate vetoes those near-ties for good reason. The broadening's real win is **converting forced guesses
into confident named calls** rather than chasing coverage by forcing. The head-to-head benchmark
in the sibling `zlabel-bench` repo (computed there, not graded in this repo) reports the payoff against
off-the-shelf annotators: zlabel's honest 76% vs forced frontier LLMs at 31–49% agreement, with even
zlabel-forced ahead of both.

## 6. How the lineages were chosen — the systematic sweep

After the high-traffic lineages were broadened, a **deterministic sweep** checked every remaining
lineage so no marginal win was missed. For each: seed candidates from the markers of its *recoverable*
clusters (abstain/rollup/wrong) across all three atlases, gate each by ZFIN grounding under the anchor
+ specificity, then **measure the real flip count** by re-labeling all three atlases. Only the four
clean lineages in §4 (pronephros, ionocyte, interrenal, notochord) produced biologically-canonical,
zero-regression wins.

**The trap the sweep exposed — "broad-gold gaming."** Several lineages showed large *apparent*
Daniocell wins that were off-lineage markers satisfying a coarse single-atlas gold:
`blood_erythroid` "gained" 11 calls by adding *myeloid* markers (the clusters still ground under the
broad `hema` gold); `lateral_line` gained by adding *neural/glial* markers under the nervous-system
gold; `fin` by stealing muscle clusters. The **held-out atlases and curated canonical subsets expose
these as false** — they evaporate to net-zero. This is exactly why validation is multi-atlas and
gold-blind, and why the sweep measures canonical subsets, not maximal marker dumps.

**The NO-GOs are design-validation, not gaps:**

- **pigment / eye** — net-negative. Eye markers (`trpm1a`, `rbp4l`) over-attract pigment cells
  (iridophore/xanthophore → retina) and dilution breaks unrelated correct calls. A before/after
  flip analysis confirmed the misannotation is *genuinely harmful markers, not wrong ground-truth*
  (the ZSCAPE gold is right: iridophores **are** pigment). The one real subtlety — RPE is genuinely
  pigment∩eye — is a future special-case, not a broadening.
- **connective / mesenchyme** — the attractor wall itself. Every discriminative connective marker is
  promiscuous (all fibrillar collagens, plus `pdgfra`/`lum`/`twist1b`/…), so the attractor guard
  blocks them; the one addable marker (`fbln1`) appears in zero recoverable clusters (measured
  byte-identical scorecard). Connective identity *is* shared ECM by biology — there is no sharp
  anchor to add.

## 7. Relation to the documented Known limit

`docs/design.md` records a measured **attractor-selection wall**: on a low-resolution cluster with
promiscuous markers, a broad attractor panel (epidermis, endothelium, mesenchyme, neural) out-scores
the true lineage. This broadening attacks a **different** failure mode — coverage gaps and input noise,
not promiscuity-based misselection. The two interact in our favor: the attractor panels are the *most
promiscuous*, not the largest, so adding **sharp** markers raises their mean specificity and mitigates
the attractor tendency while also closing the recall gap. Adding promiscuous markers would worsen both
— which is why the curation-time specificity guard is the constraint the whole effort turns on, and
why connective (all-promiscuous candidates) stays walled.

A complementary, eval-side correction lives in the gold crosswalk overlay
([`benchmarks/daniocell_crosswalk_overlay.yaml`](../../benchmarks/daniocell_crosswalk_overlay.yaml)):
where the benchmark gold is coarser or structurally disconnected from biology (periderm is the
superficial epidermis but ZFA lacks the is_a link; hema bundles blood + vasculature), the evaluator
reports an overlay-corrected agreement beside the strict one (Daniocell 76.1% to 87.5%) so the engine
is not blamed for gold coarseness — without relaxing the strict metric. See `docs/design.md` (the
fallible-key caveat) and the germ-layer-coherence forcing-flag NO-GO recorded there.

## Appendix — reproduce

```bash
make scorecard        # the multi-atlas accuracy + coverage + overcall + vocab-hit table
make audit            # per-panel grounding + mean specificity + promiscuity guard
make gate-all         # Daniocell hard byte-gate + ZSCAPE/Zebrahub held-out walls
```

The before/after and forcing-frontier numbers are computed from the committed substrate; the
head-to-head comparison against off-the-shelf annotators lives in the sibling `zlabel-bench` repo,
which reads this repo's panels and scorer in place.
