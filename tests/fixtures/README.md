# Test fixtures

Small, **hand-written** ontology subsets that let `tests/test_data.py` exercise the
loaders offline. They are not generated and not downloaded — they are crafted to be
the minimum that covers each loader's behavior, so a reader can see the whole input
at a glance. (The real files live in the gitignored `data/ontologies/`, fetched by
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
