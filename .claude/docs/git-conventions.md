# Git conventions — zlabel

## Branching

- Branch from `main`: `feat/<slug>`, `fix/<slug>`, `chore/<slug>`, `docs/<slug>`,
  `refactor/<slug>`. Build phases use `feat/phaseN-<slug>`.
- **One PR per build phase.** Squash-merge to `main` for linear history.

## Commits (Conventional Commits)

```text
<type>(<scope>): <summary>

<why, not what>
```

Types: feat, fix, chore, refactor, test, docs, ci, perf.

## Before opening a PR

```bash
make verify   # lint + docstrings + types + tests
make gate     # regression wall: regenerate the baseline, fail on drift / overcall regression
```

`make gate` needs `data/ontologies`; install it once as a pre-commit hook with `make hooks` so
the overcall-audit + baseline wall runs automatically on engine/panel/benchmark changes. An
intentional behavior change regenerates the baseline (`make eval`) and commits it for review.

## Pull requests

- Title in Conventional-Commit form.
- Body: **what + why**, and a **test plan**.
- Must clear the bar in [`workflow.md`](workflow.md): understandable, simple,
  well-documented, docs current.

## Don't commit

- Ontology downloads (`data/` is gitignored) — fetched by `scripts/setup_data.sh`.
  The committed eval substrate lives under `benchmarks/`, not `data/`.
- scRNA-seq binaries (`*.h5ad`, `*.rds`, …).
- `.env` / secrets.
