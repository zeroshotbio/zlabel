# Test fixtures

Small, **hand-written** data files that let `tests/` exercise the loaders and scorer
offline. They are not generated and not downloaded — they are crafted to be the
minimum that covers each module's behavior, so a reader can see the whole input at a
glance. (The real data files live in the gitignored `data/ontologies/`, fetched by
`scripts/setup_data.sh`.)

## `zfa_test.obo`

A 7-term ZFA subset in OBO format, shaped as a small DAG of endothelial anatomy:

```
whole organism
└─ cardiovascular system        (is_a)
   └─ endothelial cell ─────────(part_of)→ cardiovascular system
      ├─ arterial endothelial cell   (is_a; also develops_from endothelial cell)
      └─ venous endothelial cell     (is_a; also develops_from endothelial cell)
cell                              (is_a parent of endothelial cell)
ZFA:0000001                       (a name-less stub term)
```

It deliberately contains all three edge types (`is_a`, `part_of`, `develops_from`)
plus the matching `[Typedef]` stanzas, so the `ancestors` tests can prove edge-type
filtering, and one name-less term so `term_name` can be shown returning `None`. IDs
and names mirror real ZFA terms but the file is a fixture, not a ZFA export.

## `zfin_go_test.gaf`

Seven rows in GAF 2.2 format (plus the `!`-prefixed header lines) for four real
zebrafish genes (`kdrl`, `cdh5`, `gata1a`, `dll4`). The synonym column (column 11)
carries `kdr|flk1` for `kdrl`, which `test_synonym_loads_committed_fixture` resolves.
Rows use the full 15-field GAF layout to mirror the real file; the loader only reads
through column 11. Hand-written, not a ZFIN export.

Both fixtures were adapted from the predecessor project's equivalent test files.
Synonym fan-out across paralogs (one previous-name → several current symbols) is
tested separately with inline rows in `tests/test_data.py`, not from these files.

## `panels_test.yaml`

A four-bucket panel subset in the `panels.yaml` schema, used by `tests/test_panels.py`
to exercise `load_panels` and `score_markers` offline:

- `muscle` (identity) — 5 markers: `mylz2, acta1b, tnnt3a, myod1, myog`; includes a
  `myoblast` subpanel to test subpanel loading without scoring.
- `blood_erythroid` (identity) — 3 markers: `gata1a, hbae1.1, hbbe1.1`.
- `endothelium` (identity) — 3 markers: `kdrl, fli1a, cdh5`.
- `cycling` (state) — 3 markers: `mki67, pcna, top2a`.

The muscle + blood + endothelium combination drives the keystone scorer trace:
`["mylz2","acta1b","tnnt3a","myod1","myog","hbae1.1","kdrl"]` should score muscle
≈ 0.81, blood_erythroid ≈ 0.098, endothelium ≈ 0.092, cycling = 0.0.
