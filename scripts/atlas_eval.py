"""Atlas-parameterized harness for the held-out generalization walls (ZSCAPE, Zebrahub, ...).

zlabel's hard gate is Daniocell (scripts/check_baseline.py): a byte-identical baseline + an overcall
audit. The held-out atlases are different in kind -- the engine and thresholds are never tuned on
them, and their gold keys are fallible -- so they get a softer, directional ratchet instead. This one
harness drives all of them from a small registry: adding an atlas is a registry entry + a committed
benchmark/crosswalk/report, not a new pair of run/check scripts.

  run    regenerate <atlas>'s report and write/print it (make eval-<atlas>).
  check  regenerate in-memory and compare to the committed report (make gate-<atlas>): fail on any
         drift -- so a change is regenerated and reviewed deliberately -- but print a DIRECTIONAL read
         (coverage, abstain, agreement, overcall) so a reviewer can tell an improvement from a
         regression. Agreement is a guard band (small named-N); coverage/abstain/overcall are flagged
         on any move in the wrong direction.

Both subcommands need data/ontologies (the gitignored ZFIN/ZFA downloads); check SKIPS (exit 0) when
that data is absent, so a machine without the corpus is never blocked.

Run:
    uv run python scripts/atlas_eval.py run   --atlas zscape
    uv run python scripts/atlas_eval.py check --atlas zebrahub
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from zlabel.evaluate import evaluate, load_benchmark, load_crosswalk, load_resources, render_report

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data" / "ontologies"
PANELS = REPO / "src" / "zlabel" / "panels.yaml"
BENCH = REPO / "benchmarks"


@dataclass(frozen=True)
class AtlasConfig:
    """One held-out atlas's eval wiring.

    Attributes:
        name (str): The atlas key used on the command line and in make targets.
        benchmark (Path): The committed per-cluster eval CSV.
        crosswalk (Path): The committed gold-side tissue/class -> ZFA anchor crosswalk.
        report (Path): The committed baseline report this atlas regenerates / is checked against.
        title (str): The report's H1 heading (also the byte-identity key for the check).
        agreement_tolerance_pct (float): An agreement drop smaller than this (percentage points) is
            small-N noise, not a flagged regression. Coverage/abstain/overcall use no tolerance.
    """

    name: str
    benchmark: Path
    crosswalk: Path
    report: Path
    title: str
    agreement_tolerance_pct: float = 5.0


ATLASES: dict[str, AtlasConfig] = {
    "zscape": AtlasConfig(
        name="zscape",
        benchmark=BENCH / "zscape_eval.csv",
        crosswalk=BENCH / "zscape_tissue_crosswalk.yaml",
        report=BENCH / "zscape_baseline_report.md",
        title="ZSCAPE 2nd-atlas baseline report (anchor-rooted descent engine)",
    ),
    "zebrahub": AtlasConfig(
        name="zebrahub",
        benchmark=BENCH / "zebrahub_eval.csv",
        crosswalk=BENCH / "zebrahub_tissue_crosswalk.yaml",
        report=BENCH / "zebrahub_baseline_report.md",
        title="Zebrahub 3rd-atlas baseline report (anchor-rooted descent engine)",
    ),
}

# Each metric's headline line in a rendered report: name -> (percent-capturing regex, better direction).
_METRICS = {
    "coverage": (re.compile(r"coverage \(non-abstain\): ([\d.]+)%"), "up"),
    "abstain": (re.compile(r"- abstain: ([\d.]+)%"), "down"),
    "agreement": (re.compile(r"- agreement: ([\d.]+)%"), "up"),
}
_OVERCALL_LINE = re.compile(r"thin-support overcalls.*\((\d+)/\d+\)")


def _data_present() -> bool:
    """Whether the ZFIN/ZFA corpus needed to score is present."""
    required = [DATA / "zfa.obo", DATA / "zfin_wildtype_expression.txt", DATA / "zfin.gaf"]
    return all(path.exists() for path in required)


def _render(cfg: AtlasConfig) -> str:
    """Score zlabel on an atlas's committed benchmark and render its report text."""
    resources = load_resources(
        zfa_path=DATA / "zfa.obo",
        expr_path=DATA / "zfin_wildtype_expression.txt",
        gaf_path=DATA / "zfin.gaf",
        panels_path=PANELS,
    )
    report = evaluate(load_benchmark(cfg.benchmark), load_crosswalk(cfg.crosswalk), resources)
    return render_report(report, title=cfg.title)


def _metric(text: str, pattern: re.Pattern[str]) -> float | None:
    """The percentage captured by pattern in a rendered report, or None when the line is absent."""
    match = pattern.search(text)
    return float(match.group(1)) if match else None


def _overcalls(text: str) -> int | None:
    """The thin-support overcall numerator in a rendered report, or None when the line is absent."""
    match = _OVERCALL_LINE.search(text)
    return int(match.group(1)) if match else None


def directional_read(committed: str, fresh: str, tolerance_pct: float) -> list[str]:
    """Lines describing how each held-out metric moved committed -> fresh, flagging regressions.

    Args:
        committed (str): The committed report text.
        fresh (str): The freshly regenerated report text.
        tolerance_pct (float): Agreement guard band (percentage points); other metrics use 0.

    Returns:
        list[str]: One human-readable line per metric (coverage, abstain, agreement, overcall),
        each marked REGRESSION, improved, or flat, for a reviewer to judge the drift.
    """
    lines: list[str] = []
    for name, (pattern, direction) in _METRICS.items():
        was, now = _metric(committed, pattern), _metric(fresh, pattern)
        if was is None or now is None:
            continue
        delta = now - was
        tolerance = tolerance_pct if name == "agreement" else 0.0
        worsened = -delta > tolerance if direction == "up" else delta > tolerance
        mark = "REGRESSION" if worsened else ("improved" if delta else "flat")
        lines.append(f"  {name}: {was:.1f}% -> {now:.1f}% ({delta:+.1f} pts) [{mark}]")

    was_oc, now_oc = _overcalls(committed), _overcalls(fresh)
    if was_oc is not None and now_oc is not None:
        mark = "REGRESSION" if now_oc > was_oc else ("improved" if now_oc < was_oc else "flat")
        lines.append(f"  overcalls: {was_oc} -> {now_oc} [{mark}]")
    return lines


def run(cfg: AtlasConfig) -> int:
    """Regenerate an atlas's report and write/print it. Returns 0, or 1 if data is absent."""
    if not _data_present():
        print(f"run {cfg.name}: cannot regenerate, data/ontologies absent (run scripts/setup_data.sh).")
        return 1
    rendered = _render(cfg)
    cfg.report.write_text(rendered, encoding="utf-8")
    print(rendered)
    print(f"\nWrote {cfg.report}")
    return 0


def check(cfg: AtlasConfig) -> int:
    """Compare a regenerated report to the committed one. Returns 0 on skip/match, 1 on drift."""
    if not _data_present():
        print(f"SKIP check {cfg.name}: data/ontologies absent; cannot verify (run scripts/setup_data.sh).")
        return 0
    fresh = _render(cfg)
    committed = cfg.report.read_text(encoding="utf-8")
    if fresh == committed:
        print(f"check {cfg.name} OK: held-out report matches.")
        return 0

    print(f"FAIL check {cfg.name}: the regenerated report differs from the committed one.")
    print("  Held-out generalization read (commit a regenerated report only if these are improvements):")
    for line in directional_read(committed, fresh, cfg.agreement_tolerance_pct):
        print(line)
    print(f"  If intentional, run `make eval-{cfg.name}` to regenerate the report and review before committing.")
    print("  Unified diff (committed -> fresh):")
    diff = difflib.unified_diff(
        committed.splitlines(keepends=True),
        fresh.splitlines(keepends=True),
        fromfile="committed",
        tofile="fresh",
    )
    sys.stdout.writelines(diff)
    return 1


def main() -> int:
    """Dispatch run/check for the named atlas."""
    parser = argparse.ArgumentParser(description="Held-out atlas eval harness (run | check).")
    parser.add_argument("mode", choices=["run", "check"], help="regenerate the report, or check it for drift")
    parser.add_argument("--atlas", required=True, choices=sorted(ATLASES), help="which held-out atlas")
    args = parser.parse_args()
    cfg = ATLASES[args.atlas]
    return run(cfg) if args.mode == "run" else check(cfg)


if __name__ == "__main__":
    sys.exit(main())
