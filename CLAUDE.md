# CLAUDE.md — Claude-Code notes for zlabel

The canonical agent doc is [`AGENTS.md`](AGENTS.md): a self-contained project
overview, architecture, commands, and rules. This file is a thin shell that
imports it and adds Claude-Code harness wiring.

@AGENTS.md

## Auto-loaded context

@.claude/docs/domain.md
@.claude/docs/workflow.md
@.claude/docs/git-conventions.md

## How we build zlabel

zlabel is built in **7 phases, one PR per phase**
([`.claude/docs/workflow.md`](.claude/docs/workflow.md)). After each phase: stop,
self-review the diff, make sure it is simple and well-documented, update the docs,
open a PR, and **wait for human review**. A PR fails review if it is hard to
understand, overcomplicated, or poorly documented. "Documented" means the *right*
words — not verbose prose.

## Harness wiring

- [`.claude/settings.json`](.claude/settings.json) — pre-approved tools (`uv`,
  `git`, `gh`, `make`) and an `.env` read/write deny.

## Authoritative design

[`docs/design.md`](docs/design.md) is the design of record (what zlabel is, the
loop, the structure, the build order, and the rationale).
