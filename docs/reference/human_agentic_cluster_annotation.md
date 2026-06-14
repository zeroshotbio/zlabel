# Human and Agentic Cluster Annotation

How zebrafish scRNA-seq clusters are realistically labeled, and which parts should
be deterministic versus agentic.

## Bottom line

Human curators do not literally annotate by running one formula over marker genes.
They annotate by triangulating evidence: marker coherence, negative evidence,
developmental stage, reference atlases, known biology, ontology fit, and plots. The
best software version of that workflow is therefore not a single classifier. It is a
pipeline with deterministic evidence builders and a small number of judgment points.

For zlabel, the ZFIN/ZFA convergence namer is a good deterministic grounding layer.
It captures one central curator move: ask where several positive marker genes
express in zebrafish, roll that evidence through zebrafish anatomy, prefer specific
terms only when multiple genes agree, and abstain when evidence conflicts. It should
not replace QC, reference mapping, plots, state detection, subclustering, or expert
review.

## What humans actually do

Across manual and semi-automated single-cell annotation workflows, the recurring
pattern is:

1. Cluster or otherwise group similar cells.
2. Find positive markers and check whether they form a coherent biological program.
3. Check negative markers to rule out incompatible lineages and doublets.
4. Compare the cluster to known marker panels and reference atlases.
5. Use metadata such as organism, tissue, stage, condition, chemistry, and genotype.
6. Assign a broad parent label first, then subcluster when finer resolution is needed.
7. Map the accepted label to standard ontology terms.
8. Record confidence, evidence, uncertainty, and the next review action.

This is consistent with general single-cell guidance: automated annotation can help,
but reliable workflows still combine automatic annotation, manual marker inspection,
and verification. Reference-based tools such as SingleR and Seurat label transfer
are also framed as evidence that needs marker diagnostics, not as unquestioned truth.
Zebrafish atlas practice follows the same shape: Zebrahub describes cluster
annotation from enriched genes, literature search, ZFIN database queries, existing
published atlases, and ZFA controlled vocabulary.

## Design principle

Use deterministic code for evidence extraction, normalization, scoring, and
reproducibility. Use an LLM or agentic layer only where the task is genuinely
interpretive: choosing among plausible hypotheses, noticing conflicts, planning
follow-up checks, and writing a readable evidence summary.

The agent must never invent markers, ontology IDs, atlas support, or stage facts.
Every claim it makes should cite a structured artifact produced by deterministic
steps or a retrieved source.

## Resource-backed evidence surface

The zebrafish resource stack is rich enough to support deterministic grounding
without inventing a new biological authority.

- ZFIN exposes machine-joinable downloads for wild-type expression, expression by
  stage and anatomy, anatomy terms, anatomy relationships, anatomy synonyms, stage
  series, previous gene IDs, marker relationships, GAF synonyms, and curated
  orthology. These are the right substrate for reproducible symbol resolution and
  expression grounding.
- ZFA and ZFS are graph and stage structures, not just display vocabularies. ZFA
  supports anatomy roll-up through relationships such as `is_a` and `part_of`; ZFS
  supports stage plausibility and stage-aware filtering.
- CL and Uberon are interoperability targets. They help export accepted labels into
  cross-species analysis, but they should not replace ZFA as the primary
  zebrafish-native grounding vocabulary.
- GO and ZECO are overlays for process, state, cellular component, and experimental
  condition. They are useful for states such as cycling, interferon response,
  hypoxia, injury, or exposure, but they are not final cell-identity labels.
- ZMAP, ZCL/ZCDL, Daniocell, Zebrahub, ZSCAPE, and legacy developmental atlases are
  reference and benchmark surfaces. They provide transcriptomic context,
  transferred labels, consensus markers, and failure review targets, not infallible
  naming truth.

The practical conclusion is that the deterministic layer should build typed
evidence first; the agentic layer should reason over that evidence second.

## Proposed mixed pipeline

### 1. Ingest and validate metadata

Deterministic:

- Validate species, genome build, tissue scope, stage or hpf/dpf, condition,
  genotype, chemistry, batch, and cluster identifiers.
- Reject or flag missing metadata needed for stage-aware or context-aware labeling.
- Record resource versions for ZFIN, ZFA, ZFS, panels, and reference atlases.

Agentic:

- Decide whether missing metadata blocks labeling or only downgrades confidence.
- Summarize metadata risks for the reviewer.

### 2. QC and technical-state triage

Deterministic:

- Compute cluster-level QC summaries: n cells, genes/cell, UMIs/cell,
  mitochondrial/ribosomal load, ambient markers, doublet scores, and stress or
  cell-cycle signatures.
- Flag probable low-quality, ambient, doublet-like, state-dominated, or
  underclustered clusters.

Agentic:

- Explain whether the cluster should be biologically labeled now, subclustered,
  filtered, or reviewed as a technical artifact.
- Compare state signals against identity evidence without collapsing state into
  identity.

### 3. Gene normalization

Deterministic:

- Normalize input markers to official ZFIN symbols.
- Preserve original symbols, aliases, previous IDs, Ensembl IDs, mapping status,
  and paralog fan-out.
- Mark unresolved or ambiguous symbols.

Agentic:

- Decide whether a marker list is too degraded by unresolved or ambiguous mappings
  to support a confident label.
- Explain paralog ambiguity in plain language.

### 4. Marker extraction and weighting

Deterministic:

- Compute positive and negative cluster markers with rank, log fold change,
  percent in cluster, percent out of cluster, and specificity.
- Build a weighted marker list for identity evidence.
- Score orthogonal state programs separately.

Agentic:

- Decide whether top markers look like an identity program, a state program, a
  mixed program, or mostly generic housekeeping/stress signal.
- Pick which markers deserve explanation in the evidence packet.

### 5. Broad panel scoring

Deterministic:

- Score broad curated panels for tissue, lineage, and state.
- Report score margins and matched markers.
- Treat panels as coarse priors and review scaffolds, not final naming authority.

Agentic:

- Interpret near ties, weak margins, and conflicts between panel hits.
- Suggest whether to roll up, abstain, or subcluster.

### 6. ZFIN/ZFA/ZFS convergence grounding

Deterministic:

- For each normalized positive identity marker, retrieve ZFIN wild-type expression
  records.
- Map expression records to ZFA terms and walk `is_a` / `part_of` ancestors.
- Aggregate by distinct genes, not raw expression records.
- Compute term specificity, such as information content, from the expression corpus.
- Apply generic-term stoplists and stage plausibility checks.
- Emit ranked candidate ZFA terms, support genes, convergent genes, grounding counts,
  stage evidence, and abstention reasons.

Agentic:

- Explain the winning term and alternatives.
- Decide whether a technically winning term is biologically too specific for a
  low-resolution cluster.
- Notice when the convergence vote and panel prior disagree in a meaningful way.

### 7. Reference atlas mapping

Deterministic:

- Run appropriate reference mapping or correlation methods when reference data are
  available.
- Include zebrafish-native references such as ZMAP, ZCL/ZCDL, Daniocell, Zebrahub,
  ZSCAPE, and specialized atlases when relevant.
- Aggregate per-cell or per-neighbor predictions to cluster-level labels with
  confidence, margins, and disagreement rates.

Agentic:

- Decide whether a reference is stage-matched, tissue-matched, and technically
  comparable enough to trust.
- Reconcile disagreements between references and marker/ZFIN evidence.
- Propose additional references when the selected atlas is a poor match.

### 8. Ontology mapping and depth choice

Deterministic:

- Map accepted zebrafish anatomy labels to ZFA and ZFS.
- Add CL and Uberon terms only when they are appropriate interoperability targets.
- Compute ancestor-aware relationships among candidate labels.

Agentic:

- Choose whether to keep a specific term, roll up to a parent, use a compound label,
  or abstain.
- Explain why a parent label is more honest than a precise but unsupported leaf.

### 9. Decision assembly

Deterministic:

- Combine marker coherence, panel margin, ZFIN/ZFA grounding, reference agreement,
  stage plausibility, state burden, and ambiguity flags into a reproducible evidence
  packet.
- Apply hard invariants: no high-confidence label with contradictory grounding; no
  identity replacement by state; no fine label without specific evidence.

Agentic:

- Make the final first-pass recommendation from the evidence packet.
- Generate competing hypotheses and test them against the structured evidence.
- Write a concise rationale, unresolved questions, and next action.

### 10. Review packet and iteration

Deterministic:

- Produce dot plots, marker heatmaps, UMAP overlays, score tables, reference-hit
  tables, ontology links, and provenance.
- Track reviewer decisions.

Agentic:

- Summarize the review packet for humans.
- Highlight the smallest set of plots needed to resolve the uncertainty.
- Turn reviewer feedback into concrete next actions: subcluster, filter, revise
  panel, add reference, or accept.

## Evidence contracts

The system should pass structured artifacts between stages. This keeps the agent
from guessing and makes the final label auditable.

| Contract | Deterministic contents | Used for |
| :---- | :---- | :---- |
| Normalized marker table | Raw feature, resolved ZFIN symbol, stable IDs, aliases, previous IDs, Ensembl IDs, mapping status, paralog fan-out | Symbol provenance and marker usability |
| Marker evidence packet | Positive markers, negative markers, ranks, log fold change, percent in, percent out, specificity, state-program scores | Identity versus state reasoning |
| ZFIN convergence candidates | Candidate ZFA terms, support genes, convergent genes, IC or specificity score, stage evidence, stoplist decisions, rejected ancestors | Zebrafish-native naming depth |
| Atlas support table | Reference name, candidate label, score type, score, stage/tissue match, mapping confidence, disagreement flags | External validation and mismatch detection |
| Decision packet | Accepted label, panel prior, ZFA/ZFS IDs, optional CL/Uberon IDs, confidence components, ambiguity flag, next step | Final machine-readable output |
| Rejection and abstention record | Rejected labels, reason codes, conflicting branches, state burden, missing metadata, unresolved markers | Reviewer triage and benchmark failure analysis |

The final answer should be a small projection of these artifacts, not a new source
of facts.

## What should stay deterministic

- File parsing, schema validation, and resource versioning.
- Gene normalization and mapping-status assignment.
- Marker ranking, panel scoring, and module scoring.
- ZFIN expression lookup and ZFA/ZFS graph traversal.
- Distinct-gene aggregation and term ranking.
- Reference mapping computations.
- Ontology ID lookup and ancestor calculations.
- Confidence components and invariant checks.
- Serialization of evidence packets and provenance.

These steps should be testable, reproducible, and inspectable without an LLM.

## What an LLM or agent can help with

- Selecting the most plausible interpretation when deterministic signals disagree.
- Explaining why the pipeline should roll up, abstain, or subcluster.
- Deciding which references are appropriate for the sample context.
- Proposing follow-up checks or plots.
- Summarizing evidence for a human reviewer.
- Translating structured evidence into clean prose.
- Detecting documentation or label-name inconsistencies across clusters.
- Helping curate marker panels from retrieved literature, with human review.

The agent should operate over structured artifacts. It should not be the source of
truth for marker expression, ontology membership, or atlas support.

## Anti-patterns

- Using the LLM as a free-text label generator from marker names alone.
- Accepting reference transfer without marker diagnostics.
- Counting raw ZFIN expression records as if repeated publications were independent
  support.
- Treating a fixed hierarchy as a biological truth rather than an output schema.
- Treating a state program as a cell identity.
- Forcing every cluster to a leaf label.
- Hiding uncertainty because the top score is numerically highest.

## Failure modes

| Failure mode | Typical signal | Best handler |
| :---- | :---- | :---- |
| Broad-term domination | Only generic anatomy parents score well, or a root-like term wins by gene count | Deterministic stoplist, IC weighting, and parent/child audit |
| Stage mismatch | Marker evidence points to a term implausible for the sample hpf/dpf | Deterministic stage penalty plus human review if biology is surprising |
| Paralog confusion | A human or historical marker maps to several zebrafish genes | Deterministic mapping-status retention; agent explains ambiguity |
| State-over-identity | Cycling, stress, interferon, hypoxia, or ambient programs dominate top markers | Deterministic state overlay; agent recommends unresolved or parent identity |
| Mixed or doublet cluster | Incompatible lineage markers or atlas branches co-occur | Deterministic mixed flag; human decides filter, subcluster, or retain |
| Atlas mismatch | Reference mapping disagrees with marker and ZFIN/ZFA evidence | Evidence packet preserves disagreement; agent explains likely cause |
| Ontology gap | Strong biological evidence lacks a clean ZFA/CL term | Agent can draft a curation question; human approves any ontology workaround |
| False lineage claim | Transcriptional continuity is mistaken for lineage history | Human review and lineage evidence are required |

The most dangerous failure is false precision: a system that always returns a deep
label can look impressive while being less useful than a conservative parent label.

## Proposed agent architecture

| Layer | Deterministic tools | Agentic role | Output |
| :---- | :---- | :---- | :---- |
| Intake | Metadata validators, schema checks | Assess whether missing context blocks labeling | Validated dataset context |
| QC | QC metrics, state scores, doublet scores | Decide labelable vs technical/state/mixed | Triage flags |
| Gene mapping | ZFIN/GAF/Ensembl/orthology maps | Explain ambiguity and paralogs | Normalized marker table |
| Marker evidence | DE and specificity statistics | Pick salient positive/negative evidence | Cluster marker packet |
| Panel prior | Curated panels and score margins | Interpret panel conflicts | Broad prior and states |
| Grounding | ZFIN expression, ZFA/ZFS graph, IC ranking | Explain convergence and contradictions | ZFA candidates and support genes |
| Reference mapping | ZMAP/ZCL/Daniocell/Zebrahub/ZSCAPE mapping | Judge reference fit and disagreements | Reference evidence table |
| Decision | Confidence rubric and invariants | Choose rollup, abstain, or accept | Label evidence packet |
| Review | Plots, links, provenance | Summarize and request next action | Human review package |

## Benchmarks and calibration

Evaluate the mixed pipeline as a depth-aware decision system, not only as a flat
label matcher.

| Benchmark surface | What it tests | Useful metrics |
| :---- | :---- | :---- |
| Daniocell | Broad developmental coverage and tissue-specific reanalysis | Broad accuracy, stage consistency, abstention rate |
| Zebrahub | Coarse-to-fine annotation and ZFA-backed vocabulary | Hierarchy consistency, overcall rate |
| ZMAP or ZCL/ZCDL | Consensus markers and reference-transfer behavior | Top-1 broad accuracy, branch rank, score margin |
| ZSCAPE | Hierarchical depth and dense developmental reference labels | Ancestor-aware F1, depth error, calibration |
| Synthetic mixtures | Mixed, doublet-like, and incompatible-branch behavior | Mixed detection AUROC, false precise-label rate |
| Marker ablations | Robustness to marker dropout or noisy marker injection | Label stability, confidence degradation |

Core questions:

- Does deterministic grounding improve over raw marker panels and raw ZFIN counts?
- Does the agent improve ambiguous decisions without inventing unsupported labels?
- Does the system roll up rather than overcall when fine evidence is weak?
- Does it abstain on synthetic mixtures and state-dominated clusters?
- Are confidence tiers calibrated against held-out atlas labels?
- Can reviewers trace every final label to markers, ontology terms, references, and
  stage context?

Useful metrics include broad accuracy, ancestor-aware F1, overcall/undercall depth
error, risk-coverage curves, calibration, marker-ablation robustness, and
leave-one-atlas-out generalization.

Confidence should start as component evidence, not a global probability. Report
marker coherence, panel margin, ZFIN/ZFA grounding, atlas agreement, stage
plausibility, negative-marker exclusion, and state burden separately. Fit calibrated
probabilities only after held-out benchmark splits show that a numeric confidence is
reliable across stage and depth regimes.

Treat these as research questions until benchmarked:

- Whether IC weighting improves over distinct-gene counts.
- Whether publication-debias weights help beyond distinct-gene aggregation.
- Whether assay or condition weights improve labels enough to justify complexity.
- Whether one global confidence model works across broad and fine labels.
- Whether orthology expansion helps more than it hurts in zebrafish-native data.

## Source notes

- General single-cell annotation guidance commonly recommends a combination of
  automatic annotation, manual marker inspection, and verification:
  [Nature Protocols tutorial](https://www.nature.com/articles/s41596-021-00534-0),
  [Single-cell best practices annotation chapter](https://www.sc-best-practices.org/cellular_structure/annotation.html),
  and [OSCA cell type annotation](https://bioconductor.org/books/release/OSCA.basic/cell-type-annotation.html).
- Reference-based annotation tools are designed to propagate expert labels, but they
  still encourage diagnostics and marker review:
  [SingleR vignette](https://bioconductor.org/packages/release/bioc/vignettes/SingleR/inst/doc/SingleR.html)
  and [SingleR diagnostics](https://bioconductor.org/books/release/SingleRBook/annotation-diagnostics.html).
- Zebrafish-specific atlas annotation uses enriched genes, ZFIN queries, published
  references, and ZFA vocabulary:
  [Zebrahub transcriptomics](https://zebrahub.ds.czbiohub.org/transcriptomics).
- Zebrafish reference mapping and consensus marker resources are emerging around
  harmonized atlas references:
  [ZMAP](https://wagnerlabucsf.github.io/zmap/) and
  [zmap-tools](https://github.com/WagnerLabUCSF/zmap-tools).
- ZFIN provides the official downloadable expression, anatomy, stage, marker, and
  orthology resources used by the deterministic grounding layer:
  [ZFIN downloads](https://zfin.org/downloads).
- Multi-agent annotation systems are promising because they explicitly split
  annotation, validation, formatting, scoring, reporting, retrieval, and ontology
  reasoning, but they still need structured evidence and guardrails:
  [CASSIA](https://www.nature.com/articles/s41467-025-67084-x).
