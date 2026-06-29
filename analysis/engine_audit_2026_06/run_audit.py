"""Read-only engine audit reproducer (2026-06-29). NO engine code or behaviour changed.

Builds a per-cluster audit table (cluster_outcomes plus the Label fields it drops) and runs every analysis
behind REPORT.md: calibration plus recalibration, abstain triage, the grounding-lever NO-GOs (support-floor
probe plus targeted marker injection), and the ZSCAPE fine-naming validation plus region-cap simulation.

Faithful: reuses the public loaders plus cluster_outcomes plus _label_row unchanged; the aggregate
reproduces the committed baselines. The CONVERGENCE_MIN probe monkeypatches the module global in memory and
restores it. Needs data/ontologies (not in CI, like the other analysis scripts).

Run: cd ~/PycharmProjects/zlabel && uv run python analysis/engine_audit_2026_06/run_audit.py
"""

from __future__ import annotations

import bisect
import copy
import csv
import itertools
import statistics
from collections import Counter
from dataclasses import replace
from pathlib import Path

import zlabel.resolve as R
from zlabel.data import ZfinExpressionRecord, term_name
from zlabel.evaluate import (
    ABSTAIN,
    FALLBACK,
    NAMED,
    ROLLUP,
    Resources,
    _label_row,
    cluster_outcomes,
    extend_crosswalk,
    load_benchmark,
    load_crosswalk,
    load_resources,
    overlay_for,
)
from zlabel.genes import normalize_markers, resolved_symbols
from zlabel.ground import grounds_under
from zlabel.panels import KIND_IDENTITY
from zlabel.resolve import build_information_content, build_marker_specificity

HERE = Path(__file__).resolve().parent
ZROOT = Path(__file__).resolve().parents[2]
DATA = ZROOT / "data/ontologies"

Row = dict[str, object]
Pair = tuple[float, int]


def load_engine() -> Resources:
    """Load all engine data once (ontology, expression, panels, IC, specificity)."""
    return load_resources(
        zfa_path=DATA / "zfa.obo",
        expr_path=DATA / "zfin_wildtype_expression.txt",
        gaf_path=DATA / "zfin.gaf",
        panels_path=ZROOT / "src/zlabel/panels.yaml",
    )


def atlas_paths(name: str) -> tuple[Path, Path]:
    """Return (eval CSV, tissue crosswalk) paths for an atlas."""
    return ZROOT / f"benchmarks/{name}_eval.csv", ZROOT / f"benchmarks/{name}_tissue_crosswalk.yaml"


def build_table(name: str, res: Resources) -> list[Row]:
    """Build and write the per-cluster audit table; print the faithfulness aggregate."""
    eval_csv, cw_path = atlas_paths(name)
    bench = load_benchmark(eval_csv)
    base = load_crosswalk(cw_path)
    overlay = overlay_for(cw_path)
    ext = extend_crosswalk(base, overlay) if overlay else base
    out_s = cluster_outcomes(bench, base, res)
    out_o = cluster_outcomes(bench, ext, res) if overlay else out_s
    labels = [_label_row(row, res)[0] for row in bench]
    rows: list[Row] = []
    for o, oo, lab in zip(out_s, out_o, labels, strict=True):
        rows.append({
            "cluster_id": o.cluster_id, "gold": o.gold_tissue, "tissue_name": o.tissue_name,
            "stage_hpf": o.stage_hpf if o.stage_hpf is not None else "", "kind": o.kind,
            "scored": int(o.scored), "agrees": "" if o.agrees is None else int(o.agrees),
            "agrees_overlay": "" if oo.agrees is None else int(oo.agrees), "confidence": o.confidence or "",
            "confidence_score": "" if lab.confidence_score is None else round(lab.confidence_score, 4),
            "margin": round(lab.margin, 4), "ood": lab.ood, "abstain_reason": o.abstain_reason or "",
            "n_resolved": o.n_resolved, "n_markers": len(o.markers), "vocab_hit_rate": round(o.vocab_hit_rate, 4),
            "depth": o.depth, "zfa_id": o.zfa_id or "", "bucket": o.bucket, "panel_bucket": o.panel_bucket,
            "convergent_genes": ";".join(o.convergent_genes),
            "attractor_groundings": ";".join(o.attractor_groundings),
            "thin_overcall": "" if o.audit is None else int(o.audit.thin_support_overcall),
            "support_fraction": "" if o.audit is None else round(o.audit.support_fraction, 3),
            "n_candidates": len(lab.candidates),
        })
    with (HERE / f"audit_table_{name}.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    scored = [r for r in rows if r["scored"] == 1]
    named = sum(1 for r in scored if r["kind"] == NAMED)
    fallback = sum(1 for r in scored if r["kind"] == FALLBACK)
    rollup = sum(1 for r in scored if r["kind"] == ROLLUP)
    cov = named + fallback + rollup
    asg = [r for r in scored if r["kind"] in (NAMED, FALLBACK)]
    ag = sum(1 for r in asg if r["agrees"] == 1)
    ago = sum(1 for r in asg if r["agrees_overlay"] == 1)
    print(
        f"[{name}] scored={len(scored)} cov={cov}/{len(scored)}={100 * cov / len(scored):.1f}% "
        f"agree={ag}/{len(asg)}={100 * ag / len(asg):.1f}% overlay={ago}/{len(asg)}={100 * ago / len(asg):.1f}%"
    )
    return rows


def _brier(pairs: list[Pair]) -> float:
    return sum((p - y) ** 2 for p, y in pairs) / len(pairs)


def _pav(xy: list[Pair]) -> list[float]:
    ys = [y for _, y in sorted(xy)]
    blocks = [[float(y), 1] for y in ys]
    i = 0
    while i < len(blocks) - 1:
        if blocks[i][0] / blocks[i][1] > blocks[i + 1][0] / blocks[i + 1][1]:
            blocks[i][0] += blocks[i + 1][0]
            blocks[i][1] += blocks[i + 1][1]
            del blocks[i + 1]
            i = max(0, i - 1)
        else:
            i += 1
    out: list[float] = []
    for s, c in blocks:
        out += [s / c] * int(c)
    return out


def _cv_isotonic(pairs: list[Pair]) -> float:
    folds = [pairs[i::5] for i in range(5)]
    sq = n = 0.0
    for k in range(5):
        train = sorted(itertools.chain.from_iterable(folds[j] for j in range(5) if j != k))
        xs, fit = [s for s, _ in train], _pav(train)
        for x, y in folds[k]:
            if x <= xs[0]:
                p = fit[0]
            elif x >= xs[-1]:
                p = fit[-1]
            else:
                p = fit[max(0, min(bisect.bisect_right(xs, x) - 1, len(fit) - 1))]
            sq += (p - y) ** 2
            n += 1
    return sq / n


def _kept(asg: list[Row], key: str, t: float) -> str:
    kept = [r for r in asg if float(r[key]) >= t]  # type: ignore[arg-type]
    if not kept:
        return "0(n/a)"
    acc = sum(1 for r in kept if r["agrees"] == 1) / len(kept)
    return f"{len(kept)}@{acc:.2f}"


def calibration(rows: list[Row]) -> None:
    """Brier, reliability curve, recalibration, and risk-coverage operating points."""
    asg = [r for r in rows if r["scored"] == 1 and r["kind"] in (NAMED, FALLBACK) and r["confidence_score"] != ""]
    pairs: list[Pair] = [
        (float(r["confidence_score"]), int(r["agrees"]))  # type: ignore[arg-type]
        for r in asg
        if r["agrees"] != ""
    ]
    base = sum(y for _, y in pairs) / len(pairs)
    print(f"\n# CALIBRATION (n={len(pairs)})")
    print(
        f"  raw Brier={_brier(pairs):.4f}  base-rate-constant={base * (1 - base):.4f}  "
        f"CV-isotonic={_cv_isotonic(pairs):.4f}"
    )
    print("  reliability (mean_conf -> emp_acc):")
    for lo, hi in [(0.0, 0.5), (0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.01)]:
        b = [(c, y) for c, y in pairs if lo <= c < hi]
        if b:
            conf = sum(c for c, _ in b) / len(b)
            acc = sum(y for _, y in b) / len(b)
            print(f"    [{lo:.2f},{hi:.2f}) n={len(b):>3} conf={conf:.3f} acc={acc:.3f}")
    margin_rc = "  ".join(f"m>={t}:{_kept(asg, 'margin', t)}" for t in (0.0, 0.1, 0.2, 0.3))
    conf_rc = "  ".join(f"c>={t}:{_kept(asg, 'confidence_score', t)}" for t in (0.0, 0.6, 0.8))
    print("  risk-coverage by margin: " + margin_rc)
    print("  risk-coverage by conf:   " + conf_rc)


def abstain_triage(name: str, rows: list[Row]) -> None:
    """Split the abstains into recoverable (marker-vocab gap) vs structural."""
    abst = [r for r in rows if r["scored"] == 1 and r["kind"] == ABSTAIN]
    rec = [r for r in abst if r["abstain_reason"] == "weak_signal" or r["ood"] == "in_set"]
    struc = len(abst) - len(rec)
    rp, sp = 100 * len(rec) / len(abst), 100 * struc / len(abst)
    print(f"\n# ABSTAINS [{name}] n={len(abst)}: recoverable={len(rec)} ({rp:.0f}%) structural={struc} ({sp:.0f}%)")
    reasons = dict(Counter(r["abstain_reason"] for r in abst))
    oods = dict(Counter(r["ood"] for r in abst))
    print(f"    by reason {reasons}  by ood {oods}")


def floor_probe(res: Resources) -> None:
    """Grounding NO-GO #1: lowering CONVERGENCE_MIN recovers no abstaining clusters."""
    print("\n# GROUNDING LEVER NO-GO #1: support-floor probe")
    eval_csv, cw_path = atlas_paths("daniocell")
    bench, base = load_benchmark(eval_csv), load_crosswalk(cw_path)
    orig = R.CONVERGENCE_MIN
    try:
        base3 = {o.cluster_id: o for o in cluster_outcomes(bench, base, res)}
        named3 = sum(1 for o in base3.values() if o.scored and o.kind == NAMED)
        for floor in (2, 1):
            R.CONVERGENCE_MIN = floor
            now = {o.cluster_id: o for o in cluster_outcomes(bench, base, res)}
            flips = sum(
                1 for cid, b in base3.items()
                if b.scored and b.kind in (ABSTAIN, ROLLUP) and now[cid].kind == NAMED
            )
            named = sum(1 for o in now.values() if o.scored and o.kind == NAMED)
            print(f"    floor={floor}: named {named3}->{named}  abstain/rollup->named flips={flips}")
    finally:
        R.CONVERGENCE_MIN = orig


def injection(res: Resources) -> None:
    """Grounding NO-GO #2: injecting the proposed near-bar markers flips no clusters."""
    print("\n# GROUNDING LEVER NO-GO #2: targeted marker injection")
    inject = [
        ("grm2", "ZFA:0009069", "Golgi cell"), ("ddc", "ZFA:0009061", "adrenergic neuron"),
        ("gngt2a", "ZFA:0009221", "UV cone"), ("gnat2", "ZFA:0009222", "blue cone"),
        ("glra1", "ZFA:0009396", "glycinergic neuron"), ("cpa5", "ZFA:0005739", "pancreatic acinar cell"),
    ]
    eval_csv, cw_path = atlas_paths("daniocell")
    bench, base = load_benchmark(eval_csv), load_crosswalk(cw_path)
    norm = {row.cluster_id: set(resolved_symbols(normalize_markers(row.markers, res.synonyms))) for row in bench}
    for gene, _tid, tname in inject:
        n = sum(1 for s in norm.values() if gene in s)
        print(f"    {gene:<8} ({tname}) carried by {n} clusters")
    expr2 = copy.deepcopy(res.expression_map)
    for gene, tid, tname in inject:
        expr2.setdefault(gene, []).append(
            ZfinExpressionRecord(zfa_id=tid, zfa_name=tname, start_stage="Zygote:1-cell", end_stage="Adult")
        )
    ident = [p.ontology_anchor for p in res.panels if p.kind == KIND_IDENTITY]
    res2 = replace(
        res,
        expression_map=expr2,
        information_content=build_information_content(expr2, res.zfa_ontology),
        marker_specificity=build_marker_specificity(expr2, ident, res.zfa_ontology),
    )
    b = {o.cluster_id: o for o in cluster_outcomes(bench, base, res)}
    n2 = {o.cluster_id: o for o in cluster_outcomes(bench, base, res2)}
    changed = sum(1 for cid in b if b[cid].bucket != n2[cid].bucket)
    print(f"    after injecting all 6 markers: clusters changed = {changed}")


GOLD_MAP = {
    "adrenal gland": "interrenal gland",
    "basal cell": "basal cell",
    "dorsal spinal cord neuron": "spinal cord",
    "endothelium (dorsal aorta)": "dorsal aorta",
    "eye, optic cup": "retina",
    "fin fold": "fin fold",
    "hair cell": "hair cell",
    "hatching gland": "hatching gland",
    "hypophysis/locus coeruleus": "pituitary gland",
    "lens": "lens",
    "mature fast muscle": "fast muscle cell",
    "motor neuron": "motor neuron",
    "neural progenitor (hindbrain)": "hindbrain",
    "neural progenitor (hindbrain R7/8)": "hindbrain",
    "neural progenitor (MHB)": "midbrain hindbrain boundary",
    "neural progenitor (telencephalon/diencephalon)": "diencephalon",
    "neuron (+ spinal cord)": "spinal cord",
    "neuron (cranial ganglion)": "ganglion",
    "neuron (dopaminergic)": "diencephalon",
    "neuron (telencephalon, glutamatergic)": "telencephalon",
    "periderm": "periderm",
    "posterior spinal cord progenitors": "spinal cord",
    "primordial germ cell": "primordial germ cell",
    "pronephric podocyte": "podocyte",
    "red blood cell": "erythrocyte",
    "retinal neuron": "retina",
    "retinal pigmented epithelium (late)": "retinal pigmented epithelium",
    "support cells/otic vesicle": "otic vesicle",
    "xanthophore": "xanthophore",
    "endothelium (f8+, clic2+)": "blood vessel endothelial cell",
    "endothelium (vein + early artery)": "blood vessel endothelial cell",
    "fin bud mesoderm (pectoral)": "pectoral fin bud",
}
ALIASES = {
    "fast muscle cell": ["fast muscle cell", "myotome", "skeletal muscle cell"],
    "pituitary gland": ["pituitary gland", "adenohypophysis", "hypophysis"],
    "ganglion": ["cranial ganglion", "ganglion"],
    "midbrain hindbrain boundary": ["midbrain hindbrain boundary", "midbrain-hindbrain boundary"],
    "blood vessel endothelial cell": ["blood vessel endothelial cell", "endothelial cell"],
    "pectoral fin bud": ["pectoral fin bud", "pectoral fin"],
    "erythrocyte": ["erythrocyte", "red blood cell"],
    "basal cell": ["basal cell", "basal cell of epidermis"],
}


def fine_naming(res: Resources) -> None:
    """Fine-naming validation on ZSCAPE cell_type_broad gold, plus the region-cap simulation."""
    print("\n# FINE-NAMING VALIDATION (ZSCAPE cell_type_broad gold) + region-cap simulation")
    onto = res.zfa_ontology
    name2id: dict[str, str] = {}
    for node in onto.nodes:
        nm = term_name(onto, node)
        if nm:
            name2id.setdefault(nm.strip().lower(), node)

    def resolve(nm: str) -> str | None:
        for cand in ALIASES.get(nm, [nm]):
            if cand.lower() in name2id:
                return name2id[cand.lower()]
        return None

    bench = load_benchmark(ZROOT / "benchmarks/zscape_eval.csv")
    recs: list[tuple[str, str, float]] = []  # (verdict, pred zfa_id, margin)
    for row in bench:
        lab, _ = _label_row(row, res)
        assigned = lab.convergent_genes or (not lab.abstained and lab.ambiguity_flag != "underclustered")
        if not assigned:
            continue
        gold_name = GOLD_MAP.get(row.tissue_name.strip())
        gid = resolve(gold_name) if gold_name else None
        if gid is None or lab.zfa_id is None:
            continue
        if lab.zfa_id == gid or grounds_under(onto, lab.zfa_id, frozenset({gid})):
            verdict = "fine_correct"
        elif grounds_under(onto, gid, frozenset({lab.zfa_id})):
            verdict = "too_broad"
        else:
            verdict = "fine_wrong"
        recs.append((verdict, lab.zfa_id, lab.margin))
    m = len(recs)
    for verdict in ("fine_correct", "too_broad", "fine_wrong"):
        k = sum(1 for v, _, _ in recs if v == verdict)
        print(f"    {verdict:<12} {k}/{m} = {100 * k / m:.0f}%")
    fc = [mg for v, _, mg in recs if v == "fine_correct"]
    fw = [mg for v, _, mg in recs if v == "fine_wrong"]
    print(
        f"    margin-gated governor NO-GO: fine_correct median margin={statistics.median(fc):.3f} "
        f"vs fine_wrong={statistics.median(fw):.3f} (inverted -> margin cannot gate)"
    )
    nanchor = res.anchors.get("neural", frozenset())
    nrec = [(v, p, mg) for v, p, mg in recs if grounds_under(onto, p, nanchor)]
    fix = sum(1 for v, _, _ in nrec if v == "fine_wrong")
    cost = sum(1 for v, _, _ in nrec if v == "fine_correct")
    print(
        f"    region-cap (neural anchor {set(nanchor)}): would fix {fix} fine_wrong but COST {cost} "
        f"fine_correct (anchor bundles lens/RPE/pituitary) -> NO-GO as a blunt rule"
    )


def main() -> None:
    """Run the full read-only audit and regenerate the audit tables."""
    res = load_engine()
    print("=== faithfulness (must match committed baselines) ===")
    dani = build_table("daniocell", res)
    build_table("zscape", res)
    calibration(dani)
    abstain_triage("daniocell", dani)
    floor_probe(res)
    injection(res)
    fine_naming(res)


if __name__ == "__main__":
    main()
