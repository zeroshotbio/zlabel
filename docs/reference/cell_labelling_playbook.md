# **Zebrafish scRNA-seq Cell Labeling Playbook**

End-to-end scientific workflow and agentic automation blueprint

*Scope: whole-organism Danio rerio single-cell RNA-seq datasets, Leiden clusters, broad labels first, iterative subclustering later*

| Primary audience | Zebrafish scientists, computational biologists, atlas curators, and engineers building annotation agents. |
| :---- | :---- |
| **Primary question** | How do we assign the deepest defensible label to a cluster without overcalling? |
| **Core principle** | Cell labels should be evidence packets: marker genes \+ ZFIN/ZFA/ZFS grounding \+ reference-atlas support \+ confidence. |
| **Primary authorities** | ZFIN gene nomenclature and expression context; ZFA/ZFS for zebrafish anatomy and stages; CL/Uberon for interoperability; zebrafish-native atlases for expression-based evidence. |
| **What this is not** | It is not a promise of fully automatic perfect annotation. The goal is a reproducible, reviewable workflow that makes uncertainty explicit. |

# **1\. Executive summary**

**The useful unit of annotation is not a free-text label; it is an evidence-backed decision.** For a low-resolution whole-organism zebrafish scRNA-seq dataset, the first pass should usually assign clusters to broad compartments such as neural, epidermal, muscle, endoderm, blood/immune, endothelium, mesenchyme, notochord, pigment, germline, proliferative, or unresolved/mixed. Fine-grained cell types should be handled after subclustering within those broad compartments unless the markers already converge on a more specific zebrafish-native ontology term.

*Rule of thumb: call broad labels early; call precise labels only when marker coherence, ZFIN/ZFA grounding, developmental timing, and atlas context all agree.*

* **Use zebrafish-native resources first.** ZFIN, ZFA, ZFS, ZCL, Daniocell, and Zebrahub should be privileged over human/mouse marker databases for final labels.  
* **Separate identity from state.** A cluster enriched for cell-cycle, heat-shock, hypoxia, interferon, ribosomal, mitochondrial, or stress programs may represent a state within many lineages, not a standalone cell type.  
* **Record stage and anatomy separately.** A zebrafish label is often best represented as cell identity \+ anatomical context \+ developmental stage, not as a single flat label.  
* **Never depend on one marker.** Require a positive marker set, negative controls, reference-atlas support, and a confidence tier.  
* **Let depth come from evidence.** A fixed hierarchy is an output schema and review scaffold, not the source of truth for the final name. If markers converge on a specific ZFA term, use it; if they converge only on a parent, keep the parent; if they conflict, abstain or mark mixed.
* **Make uncertainty machine-readable.** Use labels such as provisional\_neural, mixed\_endoderm\_epithelial, or cycling\_mesoderm when evidence does not support a sharper label.

For a deeper split of deterministic steps, agentic judgment, and human review checkpoints, see [Human and Agentic Cluster Annotation](human_agentic_cluster_annotation.md). For future adaptive recursion and split/stop criteria above zlabel, see [Recursive Subclustering Controller](recursive_subclustering_controller.md).

# **2\. Resource stack: what each system contributes**

**The zebrafish annotation ecosystem works as a stack.** No single resource labels every cell perfectly. Separate the official grounding resources used for deterministic naming from atlas references used for benchmarking, triangulation, and review. The workflow should combine nomenclature, ontologies, atlas-derived expression evidence, scoring methods, and human review.

| Resource | Provides | Use during annotation | Caution / authority |
| :---- | :---- | :---- | :---- |
| ZFIN | Official zebrafish gene names, aliases, gene expression records, phenotypes, orthology, publications, downloads. | Gene-symbol harmonization; expression-context validation; manually curated orthology; source of ZFA/ZFS-backed evidence. | Primary authority for zebrafish nomenclature and curated zebrafish context. \[R1, R2\] |
| ZFA | Zebrafish anatomy and development ontology. | Primary vocabulary for tissue/anatomy labels and anatomical constraints. | Use for zebrafish-specific anatomical labels. \[R3\] |
| ZFS | Zebrafish developmental stage ontology. | Stage plausibility and stage-specific label interpretation. | Use with hpf/dpf metadata to avoid overcalling stage-inappropriate labels. \[R4\] |
| CL | Animal cell-type ontology. | Interoperable cell type identifiers when the cluster matches a cross-species cell type. | Use with ZFA, not as a replacement for ZFA anatomy. \[R5\] |
| Uberon | Cross-species anatomy ontology. | Interoperability between zebrafish-specific anatomy and comparative vertebrate anatomy. | Useful for cross-species outputs and ontology bridges. \[R6, R7\] |
| GO | Molecular function, biological process, and cellular component ontology. | State/process interpretation: cell cycle, cilia, immune response, metabolism, etc. | Do not use GO as the final cell-type name. \[R8\] |
| ZECO | Zebrafish experimental conditions ontology. | Represent injury, exposure, diet, infection, or perturbation context. | Important for condition-driven states that mimic identity shifts. \[R9\] |
| ZCL | Zebrafish Cell Landscape / Cell Development Landscape. | Reference marker lists, organism-level cluster context, and scZCL correlation-based query matching. | Strong broad-tissue reference; watch stage/tissue mismatch. \[R10\] |
| Daniocell | Whole-embryo/larval wild-type zebrafish scRNA-seq time course. | Developmental and early-larval reference labels; broad tissue types and marker exploration. | Especially useful for 3.3-120 hpf embryo/larva datasets. \[R11\] |
| Zebrahub | Multimodal developmental atlas combining scRNA-seq and live light-sheet imaging. | Developmental timing, lineage trajectory context, and spatial/temporal plausibility. | Strong for embryonic development and lineage-aware review. \[R12\] |
| ZSCAPE | Hierarchically annotated zebrafish developmental reference and perturbation atlas. | Benchmark broad accuracy, depth choice, and stage robustness; compare against a large hierarchical reference. | Strong validation resource, not a sole naming oracle. \[R19, R20\] |
| MSigDB/msigdbr | Gene sets for pathways and programs, including model-organism mappings. | Score states and programs such as hypoxia, cell cycle, interferon, metabolism. | Supportive, not a primary cell-name authority. \[R13\] |
| AUCell / module scoring | Algorithms for scoring signatures per cell or cluster. | Quantify enrichment of curated marker panels and biological programs. | Scores are evidence, not final labels. \[R14, R16\] |
| Seurat / SingleR | Reference mapping and label transfer frameworks. | Transfer atlas labels, get prediction scores, project query cells onto reference structure. | Only as good as the reference labels and gene mapping. \[R15, R17\] |
| Ensembl Compara / orthology | Gene trees and homology relationships. | Map human/mouse gene sets to zebrafish when zebrafish-native panels are sparse. | Paralogy needs explicit handling. \[R18\] |

# **3\. Conceptual model: label broad, then refine**

**Use hierarchy as an output contract, not a rigid name tree.** Low-resolution Leiden clustering should usually be interpreted at the level of major lineage or tissue systems. Later, each broad compartment can be reclustered to resolve fine subtypes, maturation states, or spatially defined populations. When a cluster's markers already converge on a specific ZFA anatomy term, the resolved depth can be deeper; when evidence is broad or mixed, the label should roll up or abstain.

| Level | Typical label examples | Evidence threshold | Recommended timing |
| :---- | :---- | :---- | :---- |
| Level 0: technical / QC | low quality, doublet-enriched, ambient RNA, mitochondrial/stress-dominated | QC metrics and lack of coherent lineage markers | Before biological annotation |
| Level 1: compartment | neural, muscle, epidermis, endoderm, blood/immune, endothelial, mesenchyme | Multiple coherent marker genes \+ broad signature score | First pass |
| Level 2: tissue / lineage | myotome, erythroid, neural crest, gut epithelium, macrophage, notochord | Reference atlas support \+ stage compatibility | First pass if clear; otherwise after subclustering |
| Level 3: cell type | slow muscle fiber, macrophage, enterocyte, endothelial cell, radial glia-like cell | Specific markers \+ atlas agreement \+ ontology term | Usually after subclustering |
| Level 4: state | cycling, stress, interferon-responsive, regenerating, hypoxic | State program score independent of identity markers | Always store separately from identity |

*Best-practice label format: broad\_identity \+ optional refined\_identity \+ anatomy \+ stage \+ condition \+ confidence. For example: "mesoderm \> skeletal muscle lineage; ZFA muscle; 48 hpf; wild type; high confidence."*

# **4\. End-to-end workflow for labeling one broad cluster**

1\.   **Ingest the dataset and metadata.** Require genome build, gene identifier type, developmental stage or hpf/dpf, tissue/whole organism, condition, batch, sex if relevant, and clustering resolution.

2\.   **Run QC and technical-state detection.** Flag doublet-enriched clusters, low-quality clusters, ambient-RNA artifacts, and stress/cell-cycle dominated clusters before assigning biological identity.

3\.   **Normalize gene identifiers.** Map each gene to official ZFIN symbol and stable identifiers. Preserve aliases and previous IDs for traceability.

4\.   **Extract cluster markers.** Compute top positive and negative markers using differential expression, percent expressed, and average expression.

5\.   **Score high-level signatures.** Use curated broad zebrafish marker panels; score with AUCell, AddModuleScore, scanpy score\_genes, or equivalent.

6\.   **Run zebrafish-native grounding.** Use ZFIN expression records and the ZFA/ZFS ontologies to ask where the positive identity markers converge in vivo. Aggregate by distinct genes, roll evidence through the ZFA graph, downweight generic terms, and keep stage plausibility explicit.

7\.   **Map against references.** Run label transfer/correlation against context-appropriate references such as ZCL, Daniocell, Zebrahub, ZSCAPE, or a tissue-specific atlas.

8\.   **Check stage and condition plausibility.** Use ZFS/stage metadata and ZECO/condition metadata to downweight labels that make no developmental or experimental sense.

9\.   **Map to interoperability ontologies.** Keep ZFA/ZFS as the zebrafish-native grounding terms; add CL and Uberon terms when appropriate for export.

10\.   **Synthesize evidence and confidence.** Generate a label plus a machine-readable evidence packet.

11\.   **Human review and iteration.** Produce dot plots, violin plots, UMAP overlays, and evidence tables for review; then revise marker panels and labels as needed.

| `High-level process flowRaw / processed object  -> QC + metadata validation  -> ZFIN gene-symbol resolver  -> cluster marker extraction  -> signature scoring against broad zebrafish panels  -> ZFIN/ZFA/ZFS convergence grounding  -> reference atlas mapping: ZCL / Daniocell / Zebrahub / ZSCAPE / specialized atlas  -> interoperability mapping: CL / Uberon when appropriate  -> evidence synthesis: label, confidence, disagreements, next action  -> scientist review  -> final cluster metadata + provenance + report` |
| :---- |

# **5\. The cluster annotation loop in detail**

## **5.1 Generate the evidence packet**

For each Leiden cluster, create a compact evidence packet before attempting a final label. The evidence packet should be saved even if the cluster remains unresolved.

| `cluster_id: Leiden_4n_cells: 12847sample_context:  organism: Danio rerio  stage: 48 hpf  tissue_scope: whole organism  condition: wild typemarker_evidence:  top_positive_markers: [mylz2, mylpfa, acta1b, tnnt3a, myod1, myog, ckma]  high_pct_in_cluster: [mylz2, acta1b, tnnt3a]  low_pct_outside_cluster: [mylz2, tnnt3a]signature_scores:  muscle: 0.91  paraxial_mesoderm: 0.52  neural: 0.18  blood_erythroid: 0.05reference_hits:  ZCL: skeletal muscle / muscle, score 0.83  Daniocell: muscle, score 0.88  Zebrahub: myotome / muscle lineage, score 0.81candidate_label: skeletal muscle lineageconfidence: highnext_action: subcluster to separate myoblasts, fast/slow muscle, mature myofibers` |
| :---- |

## **5.2 Decide whether the cluster is technical, state-driven, mixed, or biological**

| Question | Signals | Action |
| :---- | :---- | :---- |
| Is the cluster low quality? | High mitochondrial/ribosomal content, low genes/cell, many ambient markers, no coherent tissue markers. | Label as low\_quality\_or\_ambient; do not force a cell identity. |
| Is it doublet-enriched? | Two incompatible marker programs coexpressed in the same cells, high nUMI, doublet-score enrichment. | Label as probable\_doublet or mixed; inspect before using in biological conclusions. |
| Is it a state cluster? | Cell-cycle, heat-shock, interferon, hypoxia, stress, apoptosis, or ribosomal genes dominate. | Store state separately; do not replace identity with state unless identity is impossible. |
| Is it a broad biological compartment? | Coherent lineage/tissue marker set, reference support, stage-compatible. | Assign Level 1 or Level 2 label. |
| Is it over-resolved or under-resolved? | A cluster contains multiple related subprograms or a lineage continuum. | Assign broad label now; subcluster later. |

## **5.3 Use positive and negative evidence**

**Positive markers say what the cluster might be; negative evidence says what it is probably not.** For broad whole-organism labels, negative evidence is especially useful because many developmental markers are reused across related lineages.

| Evidence type | Example for a muscle candidate | Interpretation |
| :---- | :---- | :---- |
| Positive structural markers | mylz2, acta1b, tnnt3a, tnnc2 | Supports differentiated muscle program. |
| Positive regulatory markers | myod1, myog | Supports myogenic lineage/differentiation. |
| Negative neural markers | elavl3, neurod1, sox3 low | Argues against neural identity. |
| Negative blood markers | gata1a, hbae1.1, hbbe1.1 low | Argues against erythroid/blood identity. |
| Negative endothelial markers | kdrl, fli1a, cdh5 low | Argues against vascular/endothelial identity. |

## **5.4 Use deterministic ZFIN/ZFA convergence naming**

For zebrafish-native labels, the preferred deterministic naming layer should ground positive identity markers in ZFIN expression data and the ZFA/ZFS ontologies. This is not a raw mention-count lookup. ZFIN expression records are curated by gene, anatomy, stage, assay, publication, fish, and reagent context; raw record counts can be biased by famous genes, repeated figures, generic parent terms, and stage mismatch.

The minimum defensible convergence-namer is:

1\.   Normalize marker symbols to official ZFIN symbols before looking up evidence.

2\.   Use positive identity markers for the anatomy vote; score cell-cycle, stress, interferon, hypoxia, and ambient programs separately as states.

3\.   For each marker, retrieve wild-type ZFIN expression records, map records to ZFA terms, and credit the term plus its `is_a` / `part_of` ancestors.

4\.   Aggregate by distinct genes, not raw records, so one heavily curated marker cannot dominate the vote.

5\.   Prefer specific terms with information content or another specificity weight, while blocking ultra-generic stoplist terms such as whole organism or broad administrative roots.

6\.   Check stage plausibility with ZFS and sample hpf/dpf metadata.

7\.   Return the deepest defensible term when markers converge; return a parent term or unresolved/mixed status when evidence is broad, incompatible, or state-dominated.

Panels and reference atlases still matter, but their role changes. Curated panels provide a coarse prior and review scaffold; atlas references provide triangulation and benchmarks. The ZFIN/ZFA convergence vote is the zebrafish-native grounding layer that decides how deep the label is allowed to go.

The following additions are useful but should be treated as experimental until benchmarked: publication-debias weights beyond distinct-gene aggregation, assay-specific weights, context/environment weights, tuned numeric thresholds, and calibrated probability scores.

# **6\. Gene identifier normalization and paralog handling**

**Gene harmonization must happen before scoring.** Zebrafish scRNA-seq data may arrive with Ensembl IDs, current ZFIN symbols, previous symbols, aliases, or mixed naming. If this layer is wrong, the rest of the annotation workflow silently loses marker genes.

| Input problem | Example | Resolution strategy |
| :---- | :---- | :---- |
| Previous or alias symbol | old symbol or publication-specific alias | Map through ZFIN marker downloads and previous-ID/alias tables; preserve original input. |
| Ensembl ID only | ENSDARG... IDs | Map to current ZFIN symbol and retain Ensembl ID as stable cross-reference. |
| Teleost paralogs | genea / geneb pairs, or multiple zebrafish orthologs for one human gene | Keep all validated zebrafish paralogs in exploratory panels; later downweight paralogs that are not expressed in the relevant tissue/stage. |
| Human/mouse marker panel | human marker converted to zebrafish orthologs | Use Ensembl Compara/ZFIN orthology; treat as hypothesis-generating until validated in zebrafish-native atlases. |
| Ambiguous one-to-many mapping | one human gene maps to several zebrafish genes | Store mapping multiplicity; never collapse to one paralog without evidence. |

| `Recommended gene-map tableoriginal_id | original_symbol | zfin_gene_id | official_zfin_symbol | ensembl_gene_id | aliases | previous_ids | orthology_group | mapping_status----------- | --------------- | ------------ | -------------------- | --------------- | ------- | ------------ | --------------- | --------------...         | ...             | ...          | ...                  | ...             | ...     | ...          | ...             | exact / alias / deprecated / one_to_many / unresolved` |
| :---- |

# **7\. Starter broad-label dictionary for whole-organism zebrafish data**

*These are starter panels for first-pass annotation. They must be versioned and adapted to stage, genome build, sequencing chemistry, and atlas source. Do not treat this table as a final marker authority.*

| Broad label | Starter positive markers | Ontology anchor | Subclustering notes |
| :---- | :---- | :---- | :---- |
| Neural / neuroectoderm | elavl3, neurod1, tubb5, sox3, sox2, her4.1, ascl1a | CL neuron/neural progenitor when specific; ZFA nervous system terms | Subcluster into progenitors, neurons, glia, sensory neurons, brain regions. |
| Epidermis / epithelial surface | krt4, krt5, tp63, cldne, epcam-like epithelial genes | ZFA epidermis/epithelium terms; CL epithelial cell if appropriate | Separate periderm, basal epidermis, ionocytes, mucous/secretory cells later. |
| Muscle / myogenic lineage | myod1, myog, mylz2, mylpfa, acta1b, tnnt3a, tnnc2, ckma | ZFA muscle / myotome terms; CL muscle cell if cell-level evidence is strong | Subcluster into myoblasts, fast/slow muscle, mature fibers. |
| Blood / erythroid | gata1a, hbae1.1, hbbe1.1, alas2, klf1a, hemgn | ZFA blood; CL erythroid cell if specific | Separate primitive erythroid, erythroblast, mature erythroid depending on stage. |
| Immune / myeloid | lcp1, mpeg1.1, coro1a, spi1b, mfap4, lyz, csf1ra | CL macrophage/leukocyte when specific; ZFA immune system context | Macrophage, neutrophil, dendritic-like, lymphoid require finer review. |
| Endothelium / vasculature | kdrl, fli1a, etv2, cdh5, pecam1, flt1 | CL endothelial cell; ZFA blood vessel / vascular terms | Separate arterial, venous, lymphatic, hemogenic endothelium later. |
| Endoderm / gut-liver-pancreas lineage | sox17, foxa2, gata5, gata6, sox32, hhex, pdx1 depending on stage | ZFA endoderm/gut/liver/pancreas terms | Stage matters strongly; early endoderm versus organ epithelium should not be conflated. |
| Mesenchyme / fibroblast-like / connective tissue | col1a1a, col1a2, dcn, twist1a, prrx1a, osr2, fn1 | ZFA mesenchyme/connective tissue terms; CL fibroblast when specific | Often broad and heterogeneous; subcluster required. |
| Cartilage / chondrogenic | sox9a, sox9b, col2a1a, acana, matn1, runx2b | ZFA cartilage/skeleton terms; CL chondrocyte if specific | Separate neural crest-derived cartilage, chondrocytes, osteogenic states later. |
| Notochord | tbxta/ntl, shha, col2a1a, col8a1a, noto-related markers | ZFA notochord | Stage-dependent and sometimes overlaps with axial mesoderm markers. |
| Pigment / neural crest derivatives | mitfa, dct, tyrp1b, pmela, xdh, gch2 depending on subtype | ZFA pigment cell terms; CL melanocyte/xanthophore/iridophore when specific | Subcluster pigment lineages carefully; markers differ by subtype. |
| Germline | ddx4/vasa, nanos3, dazl, piwil1, tdrd genes | CL germ cell; ZFA germline/gonad context if relevant | Often rare; validate against stage and sample preparation. |
| Proliferative / cycling state | mki67, pcna, top2a, hmgb2, stmn1, histone genes | GO cell-cycle terms; not a final cell identity | Keep as state overlay; infer identity from non-cell-cycle markers. |
| Stress / injury / interferon state | hsp genes, fos/jun, interferon-stimulated genes, inflammatory genes | GO/ZECO state/condition annotations | Do not label as a cell type unless identity markers also support it. |

# **8\. Selecting and weighting reference atlases**

Reference mapping is powerful only if the reference resembles the query. For each atlas, record why it was used and how much to trust it for the query context.

| Scenario | Preferred reference choices | Reasoning |
| :---- | :---- | :---- |
| Whole embryo or early larva, wild type | Daniocell, Zebrahub, ZCL developmental data | Best stage and whole-organism match. |
| Embryonic lineage timing or spatial trajectory | Zebrahub plus Daniocell | Zebrahub adds lineage/time context; Daniocell provides dense developmental coverage. |
| Broad organism-level adult/juvenile tissue context | ZCL plus tissue-specific atlases | ZCL has broad tissue coverage; specialized atlases refine labels. |
| Perturbation, injury, regeneration, exposure | Wild-type reference \+ perturbation-aware references \+ ZECO/condition metadata | Separate identity shifts from condition-induced state. |
| Human/mouse comparison | ZFIN/Ensembl orthology \+ CL/Uberon \+ zebrafish atlas validation | Orthology is a bridge, not final evidence. |

| `Reference weighting heuristicreference_weight = biological_context_match * technical_context_match * annotation_quality * gene_overlapbiological_context_match: stage, tissue, condition, genotypetechnical_context_match: chemistry, species build, dissociation method, count depthannotation_quality: ontology-backed labels, curated markers, publication supportgene_overlap: number of usable genes after ZFIN harmonization` |
| :---- |

# **9\. Scoring and mapping approaches**

## **9.1 Marker/module scoring**

Use marker scoring to ask whether a cluster expresses a coherent program. For broad labels, score high-level tissue signatures across all cells and summarize by cluster.

| `R-style pseudocode: AUCell for broad marker panelslibrary(AUCell)# expr_matrix: genes x cells, with official ZFIN symbols as row names# gene_sets: named list of zebrafish marker panels, e.g. muscle, neural, endodermrankings <- AUCell_buildRankings(expr_matrix, nCores = 4, plotStats = FALSE)auc <- AUCell_calcAUC(gene_sets, rankings)cluster_scores <- summarize_auc_by_cluster(auc, leiden_cluster)# Interpretation: high score supports a candidate identity, but final labels require# marker inspection, reference mapping, stage compatibility, and ontology mapping.` |
| :---- |
| `Python-style pseudocode: scanpy score_genes for broad panelsimport scanpy as scfor label, genes in broad_marker_panels.items():    usable = [g for g in genes if g in adata.var_names]    sc.tl.score_genes(adata, gene_list=usable, score_name=f'{label}_score')cluster_score_table = adata.obs.groupby('leiden')[[c for c in adata.obs.columns if c.endswith('_score')]].mean()` |

## **9.2 Reference mapping**

Reference mapping asks whether each query cell or cluster resembles annotated reference cells. In Seurat, this can be done with anchors and TransferData/MapQuery; in SingleR-like workflows, reference expression profiles are used to infer labels. For zebrafish, the critical dependency is a well-chosen and well-harmonized reference.

| `R-style pseudocode: reference label transfer# reference_obj has curated zebrafish labels and ZFIN-normalized gene symbolsanchors <- FindTransferAnchors(reference = reference_obj, query = query_obj,                               dims = 1:30, reference.reduction = 'pca')pred <- TransferData(anchorset = anchors,                     refdata = reference_obj$label_broad,                     dims = 1:30)query_obj <- AddMetaData(query_obj, metadata = pred)# Then summarize predicted labels and prediction scores by Leiden cluster.# Do not accept a transferred label automatically; compare to markers and ontology constraints.` |
| :---- |

## **9.3 Benchmark the convergence namer**

A convergence-namer should be validated as a depth-aware decision system, not only as a flat label matcher. Use ZSCAPE, Daniocell, ZCL, Zebrahub, and legacy developmental atlases as complementary benchmarks when available. Report broad-compartment accuracy, ancestor-aware precision/recall/F1, overcall versus undercall depth error, calibration, abstention quality, marker-ablation robustness, and leave-one-atlas-out generalization.

Treat these as explicit research questions until measured: whether IC weighting improves over distinct-gene counts, whether publication-debias weights help beyond distinct-gene aggregation, and whether assay/context weights improve labels enough to justify the added complexity.

# **10\. Decision logic and confidence tiers**

| Condition | Recommended label behavior | Confidence |
| :---- | :---- | :---- |
| Positive markers, high signature score, ZFIN/ZFA convergence, top atlas hits agree, stage-compatible, ontology term exists | Assign the deepest convergent label and record evidence. | High |
| Positive markers and signature score agree, but atlas hits are weak or stage-mismatched | Assign broad parent label; flag reference mismatch. | Medium |
| Positive markers converge only on a parent ZFA term | Assign the parent term rather than forcing a fine label. | Medium |
| Markers support two related compartments, such as endoderm/epithelium or neural/neural crest | Use compound or parent label; subcluster. | Medium-low |
| State program dominates and identity markers are weak | Label state separately; identity unresolved. | Low for identity; high for state |
| Incompatible markers from unrelated compartments in same cluster | Mixed/doublet/underclustered; subcluster or filter. | Low |
| Reference transfer provides precise label but marker evidence does not support it | Reject or downgrade transferred label; keep candidate only. | Low to medium |

| `Confidence scoring exampleconfidence_score =  0.30 * marker_coherence +  0.20 * high_level_signature_margin +  0.20 * ZFIN_ZFA_grounding +  0.15 * reference_agreement +  0.10 * stage_plausibility +  0.05 * reviewer_consensusSuggested tiers:  >= 0.80 high  0.60-0.79 medium  0.40-0.59 low / provisional  < 0.40 unresolved` |
| :---- |

# **11\. Worked examples of first-pass cluster labels**

| Scenario | Top markers | First-pass label | Confidence | Review note |
| :---- | :---- | :---- | :---- | :---- |
| Muscle cluster | mylz2, mylpfa, acta1b, tnnt3a, myod1, myog, ckma | muscle / skeletal muscle lineage | High | Do not call fast/slow/mature until subclustering supports it. |
| Erythroid cluster | gata1a, hbae1.1, hbbe1.1, alas2, klf1a, hemgn | blood / erythroid lineage | High | Primitive versus definitive erythroid requires stage-aware refinement. |
| Neural cluster | elavl3, neurod1, tubb5, sox3, her4.1, ascl1a | neural / neuroectoderm | Medium-high | May contain neural progenitors, neurons, glia, or brain-region substructure. |
| Endoderm/epithelium cluster | foxa2, sox17, gata6, claudins, epcam-like genes | endoderm / epithelial lineage | Medium | Use stage and atlas context to decide early endoderm versus organ epithelium. |
| Cycling cluster | mki67, pcna, top2a, hmgb2, histone genes | cycling state; identity unresolved or parent lineage if markers exist | Low for identity | Overlay cell-cycle state onto broad lineage after excluding doublets. |
| Mixed cluster | gata1a \+ kdrl \+ elavl3 or other incompatible programs | mixed / probable doublet / underclustered | Low | Subcluster, check doublet scores, and inspect per-cell coexpression. |

# **12\. Standard output schema**

The annotation output should be versioned and machine-readable. Keep the final label, supporting evidence, and disagreements together.

| `cluster_annotation_record:  dataset_id: string  analysis_version: string  cluster_id: string  clustering_method: Leiden  clustering_resolution: float  n_cells: integer  labels:    label_level_1: broad compartment    label_level_2: tissue / lineage    label_level_3: optional refined cell type    identity_label: final display label    state_labels: [cycling, stress, interferon, hypoxia, regenerating]    ambiguity_flag: none | mixed | doublet_enriched | underclustered | provisional  ontology:    zfa_label: string    zfa_id: string    zfs_stage_label: string    zfs_id: string    cl_label: string|null    cl_id: string|null    uberon_label: string|null    uberon_id: string|null    zeco_condition_label: string|null    zeco_id: string|null  evidence:    top_positive_markers: [gene]    top_negative_markers: [gene]    signature_scores: {signature: score}    reference_hits:      - resource: ZCL        label: string        score: float        gene_overlap: integer      - resource: Daniocell        label: string        score: float        gene_overlap: integer    marker_plots: [file_or_uri]    notes: string  confidence:    tier: high | medium | low | unresolved    numeric_score: float    reasons: [string]    reviewer: string    review_date: YYYY-MM-DD  provenance:    gene_map_version: string    ontology_versions: {ZFA: version, ZFS: version, CL: version, Uberon: version}    reference_versions: {ZCL: version, Daniocell: version, Zebrahub: version}    code_commit: string    environment: string` |
| :---- |

# **13\. Scientist review package for each cluster**

A scientist should not have to inspect raw matrices to review a label. The workflow should generate a compact review page per cluster.

* UMAP colored by cluster and candidate broad labels.  
* Dot plot of broad marker panels across all clusters.  
* Violin plots for top candidate markers and top exclusion markers.  
* Heatmap of signature scores by cluster.  
* Reference atlas hit table with scores and gene overlap.  
* ZFIN links for top marker genes and ZFA/ZFS/CL links for proposed labels.  
* Confidence reasons and disagreement flags.  
* Recommended next action: accept, relabel, subcluster, filter, or request new marker panel.

# **14\. Agentic workflow blueprint**

**The same process can be implemented as an agentic workflow if the system is designed around auditable, typed artifacts.** The agent should not merely answer with labels; it should produce structured evidence records, visualization requests, and review tasks.

| Agent / module | Inputs | Actions | Outputs |
| :---- | :---- | :---- | :---- |
| Orchestrator | Dataset object, config, metadata | Runs workflow, tracks task states, manages retries and review gates. | Run manifest; provenance log. |
| Data Intake Agent | h5ad/RDS/Seurat/SCE, cluster metadata | Validates species, stage, gene IDs, cluster assignments, QC fields. | Validated data contract; missing metadata warnings. |
| Gene Resolver Agent | Gene list, ZFIN/Ensembl/ZFIN alias caches | Maps IDs to official ZFIN symbols; flags aliases, deprecated IDs, paralogs. | Gene-map table; unresolved gene report. |
| Marker Miner Agent | Expression matrix \+ cluster labels | Computes DE markers, pct expressed, logFC, specificity, cluster summaries. | Marker tables and ranked marker evidence. |
| Signature Scoring Agent | Marker panels \+ expression matrix | Runs broad panel scoring and state scoring. | Cluster-by-signature matrix; score margins. |
| Reference Mapper Agent | Query matrix \+ reference atlases | Runs correlation/label transfer to ZCL/Daniocell/Zebrahub/specialized refs. | Reference hit tables with confidence and gene overlap. |
| Ontology Mapper Agent | Candidate labels | Maps terms to ZFA, ZFS, CL, Uberon, ZECO where appropriate. | Ontology record and unmapped-term warnings. |
| Evidence Synthesizer | Markers, scores, references, ontology, metadata | Applies decision logic and confidence model. | Candidate label record and reasons. |
| Reviewer Interface Agent | Candidate records and plots | Generates scientist-facing report and review queue. | Accept/revise/subcluster/filter tasks. |
| Provenance Agent | All intermediate artifacts | Versions resources, code, references, parameters, and review outcomes. | Reproducible annotation package. |

| `Agentic state machine for one clusterSTART  -> validate_cluster(cluster_id)  -> resolve_gene_symbols(cluster_markers)  -> build_marker_evidence(cluster_id)  -> score_broad_signatures(cluster_id)  -> map_to_references(cluster_id)  -> check_stage_condition_plausibility(cluster_id)  -> map_candidate_to_ontologies(cluster_id)  -> synthesize_label_and_confidence(cluster_id)  -> generate_review_packet(cluster_id)  -> if reviewer_accepts: finalize_label     else if reviewer_requests_subcluster: enqueue_subclustering     else if evidence_conflict: label_provisional_or_unresolvedEND` |
| :---- |
| `Core agent prompt templateYou are annotating a single zebrafish scRNA-seq Leiden cluster.Use only the supplied evidence artifacts: marker table, signature score table,reference mapping table, sample metadata, gene-map table, and ontology candidates.Return JSON with:  1. final broad label  2. optional refined label  3. state labels  4. ZFA/ZFS/CL/Uberon/ZECO mappings where justified  5. confidence tier  6. top evidence for and against  7. conflicts or ambiguity  8. recommended next actionDo not invent markers or ontology IDs. If evidence is weak, label provisional or unresolved.` |

# **15\. Suggested implementation folder structure**

| `zebrafish_annotation_project/  config/    project.yaml    broad_marker_panels.yaml    reference_weights.yaml  resources/    zfin_gene_map.tsv    zfin_expression_by_stage_anatomy.tsv    zfa.obo    zfs.obo    cl.obo    uberon.obo    zeco.obo    zcl_reference/    daniocell_reference/    zebrahub_reference/  input/    query.h5ad or query.rds    sample_metadata.tsv  intermediate/    qc_report.tsv    gene_map_report.tsv    cluster_markers.tsv    signature_scores.tsv    reference_mapping.tsv  outputs/    cluster_annotations.yaml    cell_metadata_with_labels.tsv    annotation_review_report.docx or html    figures/  provenance/    resource_versions.json    code_commit.txt    environment.yml    reviewer_decisions.tsv` |
| :---- |

# **16\. Quality gates and common pitfalls**

| Pitfall | Why it matters | Preventive gate |
| :---- | :---- | :---- |
| Calling a precise cell type too early | Low-resolution Leiden clusters often combine related subtypes. | First-pass labels should usually stop at broad tissue/lineage. |
| Using MSigDB as a cell-type authority | MSigDB mostly describes pathways/programs, not zebrafish-native cell names. | Use MSigDB for state scoring only. |
| Ignoring paralogs | Human-to-zebrafish mapping can split one marker into multiple paralogs. | Keep one-to-many mappings explicit and validate expression. |
| Ignoring developmental stage | Markers and tissues change meaning across hpf/dpf. | Require ZFS stage context and stage-compatible reference weighting. |
| Accepting label transfer blindly | Reference mapping can be wrong when stage, tissue, or chemistry differs. | Require marker coherence and reference agreement. |
| Counting raw ZFIN expression records | Famous genes and repeated curation events can dominate a flat count. | Aggregate by distinct marker genes and record the evidence. |
| Treating a fixed hierarchy as the naming authority | Low-resolution clusters and evolving atlas labels do not always fit a prewritten tree. | Use hierarchy as output schema; let ZFIN/ZFA evidence determine resolved depth. |
| Conflating state with identity | Cycling/stress clusters can span many cell types. | Store state\_labels separately from identity\_label. |
| Not versioning resources | Ontologies, gene symbols, and atlas labels change. | Record resource versions and download dates. |

* **Minimum evidence to accept a broad label:** at least three coherent positive markers, a high broad-signature score, low scores for incompatible lineages, and either atlas support or strong ZFIN/ZFA biological plausibility.  
* **Minimum evidence to accept a fine label:** specific markers, ZFIN/ZFA convergence on a specific term, stage plausibility, and atlas support at similar stage/tissue or agreement after subclustering.
* **When in doubt:** use a parent label and mark the record provisional. A conservative parent label is more useful than a false precise label.

# **17\. Reproducibility requirements**

| Record | Why it is required |
| :---- | :---- |
| Genome assembly and annotation source | Gene models and symbols change; marker overlap depends on annotation. |
| ZFIN download date and version | Gene names, aliases, expression records, and orthology files are updated. |
| Ontology versions / PURLs | ZFA, ZFS, CL, Uberon, and ZECO terms can be added or revised. |
| Reference atlas version and label set | Atlas labels and downloads may change across releases. |
| Marker-panel version | Panels are curated artifacts and should be reviewable. |
| Scoring and mapping parameters | AUC thresholds, score margins, DE thresholds, and label-transfer parameters affect labels. |
| Reviewer decisions | Human curation is part of the evidence chain. |

# **18\. Minimum viable workflow for a lab**

A lab can start without a full agentic system. The practical minimum is:

1\.   Normalize all genes to official ZFIN symbols and retain original IDs.

2\.   Create broad marker panels for 10-15 major zebrafish tissue/lineage compartments.

3\.   Score every cell and summarize scores by Leiden cluster.

4\.   Extract top markers per cluster with percent expressed inside and outside the cluster.

5\.   Compare clusters against at least one zebrafish-native atlas appropriate to stage and tissue.

6\.   Assign Level 1 broad labels with confidence tiers.

7\.   Generate review plots and evidence records.

8\.   Subcluster each broad compartment and repeat the workflow for refined labels.

| `Minimum cluster decision templateCluster: ________Stage/context: ________Top markers: ________Best broad signature: ________Reference hits: ________Excluded identities: ________Candidate ZFA/ZFS/CL terms: ________Final broad label: ________Confidence: high / medium / low / unresolvedReason for confidence: ________Next action: accept / subcluster / filter / revise marker panel / seek expert review` |
| :---- |

# **19\. Quick-reference checklist**

* **\[ \]** Do I know the sample stage, genotype/condition, and whole-organism/tissue context?  
* **\[ \]** Are the gene identifiers normalized to official ZFIN symbols?  
* **\[ \]** Have aliases, deprecated IDs, and duplicated paralogs been handled explicitly?  
* **\[ \]** Does the cluster have coherent positive markers?  
* **\[ \]** Are incompatible lineage markers absent or low?  
* **\[ \]** Do broad marker scores support the candidate label?  
* **\[ \]** Do positive identity markers converge on a ZFA term by distinct-gene support rather than raw record count?
* **\[ \]** Do zebrafish-native references agree, or is there a stage/tissue mismatch?  
* **\[ \]** Is the proposed label plausible for this developmental stage?  
* **\[ \]** Can the label be mapped to ZFA and ZFS? Can CL/Uberon be added appropriately?  
* **\[ \]** Is any major state program being confused for identity?  
* **\[ \]** Have confidence tier, disagreements, and next action been recorded?

# **20\. Selected primary references and source resources**

**\[R1\] ZFIN data downloads.** Downloadable ZFIN reports including anatomy terms, stage terms, expression data, marker data, and orthology files. [https://zfin.org/downloads](https://zfin.org/downloads)

**\[R2\] ZFIN zebrafish nomenclature conventions.** Official naming guidance, including lowercase zebrafish symbols and duplicate gene conventions. [https://zfin.atlassian.net/wiki/display/general/ZFIN%2BZebrafish%2BNomenclature%2BConventions](https://zfin.atlassian.net/wiki/display/general/ZFIN%2BZebrafish%2BNomenclature%2BConventions)

**\[R3\] Zebrafish anatomy and development ontology (ZFA).** OBO Foundry entry for ZFA. [https://obofoundry.org/ontology/zfa.html](https://obofoundry.org/ontology/zfa.html)

**\[R4\] Zebrafish developmental stages ontology (ZFS).** OBO Foundry entry for ZFS. [https://obofoundry.org/ontology/zfs.html](https://obofoundry.org/ontology/zfs.html)

**\[R5\] Cell Ontology (CL).** Animal cell-type ontology used for interoperable cell labels. [https://cell-ontology.github.io/](https://cell-ontology.github.io/)

**\[R6\] Uberon multi-species anatomy ontology.** Cross-species anatomy ontology. [https://obofoundry.org/ontology/uberon.html](https://obofoundry.org/ontology/uberon.html)

**\[R7\] Uberon bridge files.** Bridge files for cross-species and species-specific anatomy mappings. [https://obophenotype.github.io/uberon/bridges/](https://obophenotype.github.io/uberon/bridges/)

**\[R8\] Gene Ontology documentation.** Structured vocabulary for molecular function, biological process, and cellular component. [https://geneontology.org/docs/ontology-documentation/](https://geneontology.org/docs/ontology-documentation/)

**\[R9\] Zebrafish Experimental Conditions Ontology (ZECO).** Ontology for zebrafish experimental conditions. [https://obofoundry.org/ontology/zeco.html](https://obofoundry.org/ontology/zeco.html)

**\[R10\] Zebrafish Cell Landscape (ZCL).** Zebrafish atlas portal with marker lists, downloads, and scZCL query matching. [https://bis.zju.edu.cn/ZCL/](https://bis.zju.edu.cn/ZCL/)

**\[R11\] Daniocell.** Whole-animal wild-type zebrafish embryo and larva scRNA-seq resource. [https://daniocell.nichd.nih.gov/](https://daniocell.nichd.nih.gov/)

**\[R12\] Zebrahub.** Multimodal atlas of zebrafish embryonic development. [https://zebrahub.sf.czbiohub.org/](https://zebrahub.sf.czbiohub.org/)

**\[R13\] msigdbr introduction.** R package for MSigDB gene sets across model organisms including zebrafish mappings. [https://igordot.github.io/msigdbr/articles/msigdbr-intro.html](https://igordot.github.io/msigdbr/articles/msigdbr-intro.html)

**\[R14\] AUCell Bioconductor package.** Gene-set activity scoring in single-cell RNA-seq data. [https://bioconductor.org/packages/release/bioc/html/AUCell.html](https://bioconductor.org/packages/release/bioc/html/AUCell.html)

**\[R15\] Seurat reference mapping vignette.** Reference mapping and label transfer workflow. [https://satijalab.org/seurat/articles/integration\_mapping.html](https://satijalab.org/seurat/articles/integration_mapping.html)

**\[R16\] Seurat AddModuleScore reference.** Module scoring for feature programs. [https://satijalab.org/seurat/reference/addmodulescore](https://satijalab.org/seurat/reference/addmodulescore)

**\[R17\] SingleR Bioconductor package.** Reference-based single-cell label assignment. [https://bioconductor.org/packages/release/bioc/html/SingleR.html](https://bioconductor.org/packages/release/bioc/html/SingleR.html)

**\[R18\] Ensembl comparative genomics.** Gene trees and homology relationships for orthology/paralogy workflows. [https://www.ensembl.org/info/genome/compara/index.html](https://www.ensembl.org/info/genome/compara/index.html)

**\[R19\] ZSCAPE / perturbed embryo atlas article.** Embryo-scale perturbation atlas useful for distinguishing developmental identity from perturbation effects. [https://www.nature.com/articles/s41586-023-06720-2](https://www.nature.com/articles/s41586-023-06720-2)

**\[R20\] ZSCAPE project overview and downloads.** Zebrafish single-cell atlas resources for reference and perturbation datasets. [https://cole-trapnell-lab.github.io/zscape/](https://cole-trapnell-lab.github.io/zscape/)

# **Appendix A. One-page operational summary**

| `For every cluster:1. Validate metadata: stage, tissue scope, condition, genome build.2. Normalize genes to official ZFIN symbols; preserve aliases and paralogs.3. Compute markers: logFC, pct_in, pct_out, specificity.4. Score broad panels: neural, epidermis, muscle, blood, immune, endothelium,   endoderm, mesenchyme, cartilage, notochord, pigment, germline, cycling, stress.5. Ground positive identity markers with ZFIN expression and ZFA/ZFS convergence.6. Map to references: ZCL, Daniocell, Zebrahub, ZSCAPE, specialized atlas if relevant.7. Check stage plausibility using ZFS and anatomy plausibility using ZFA.8. Separate cell identity from state.9. Assign the deepest defensible label + confidence + ontology terms.10. Generate plots and evidence record.11. Subcluster broad compartments and repeat for finer labels.` |
| :---- |

*Default answer when evidence is incomplete: use a parent label and write down why. A conservative, evidence-backed label is better than a precise but unsupported label.*
