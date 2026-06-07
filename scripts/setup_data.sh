#!/usr/bin/env bash
# scripts/setup_data.sh
#
# Download the three ontology files zlabel grounds against into data/ontologies/.
# Idempotent: skips files that already exist. Delete a file to force a re-download.
# (data/ is gitignored; tests use the small fixtures under tests/fixtures/ instead.)
#
# Usage:
#   bash scripts/setup_data.sh
#
# Outputs:
#   data/ontologies/zfa.obo                       ZFA anatomy ontology
#   data/ontologies/zfin.gaf                      ZFIN GO annotations — the gene-synonym authority
#   data/ontologies/zfin_wildtype_expression.txt  ZFIN in-vivo expression (gene -> ZFA + ZFS)

set -euo pipefail

DEST="data/ontologies"
ZFA_URL="https://purl.obolibrary.org/obo/zfa.obo"
GAF_URL="https://current.geneontology.org/annotations/zfin.gaf.gz"
ZFIN_EXPR_URL="https://zfin.org/downloads/wildtype-expression_fish.txt"

mkdir -p "$DEST"

# Download into a scratch dir on the SAME filesystem as $DEST, then `mv` (an
# atomic rename) into place only once the file is fully written. A partial
# download from an interrupted curl/gunzip can then never leave a truncated file
# at the final path — which the idempotency checks below would otherwise treat as
# "already present" and silently skip, feeding a corrupt ontology into the loader.
# The trap removes the scratch dir on any exit (success, failure, or Ctrl-C).
TMP_DIR="$(mktemp -d "${DEST}/.tmp.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

# --- ZFA OBO -----------------------------------------------------------------
ZFA_PATH="$DEST/zfa.obo"
if [[ -f "$ZFA_PATH" ]]; then
    echo "zfa.obo already present — skipping (delete to re-download)"
else
    echo "Downloading ZFA OBO from $ZFA_URL ..."
    curl -fsSL "$ZFA_URL" -o "$TMP_DIR/zfa.obo"
    mv "$TMP_DIR/zfa.obo" "$ZFA_PATH"
    echo "  -> $ZFA_PATH ($(wc -l < "$ZFA_PATH") lines)"
fi

# --- ZFIN GO GAF (gene-synonym authority) ------------------------------------
GAF_PATH="$DEST/zfin.gaf"
if [[ -f "$GAF_PATH" ]]; then
    echo "zfin.gaf already present — skipping (delete to re-download)"
else
    echo "Downloading zebrafish GO GAF from $GAF_URL ..."
    curl -fsSL "$GAF_URL" | gunzip > "$TMP_DIR/zfin.gaf"
    mv "$TMP_DIR/zfin.gaf" "$GAF_PATH"
    echo "  -> $GAF_PATH ($(wc -l < "$GAF_PATH") lines)"
fi

# --- ZFIN wildtype expression ------------------------------------------------
ZFIN_EXPR_PATH="$DEST/zfin_wildtype_expression.txt"
if [[ -f "$ZFIN_EXPR_PATH" ]]; then
    echo "zfin_wildtype_expression.txt already present — skipping (delete to re-download)"
else
    echo "Downloading ZFIN wildtype expression from $ZFIN_EXPR_URL ..."
    curl -fsSL "$ZFIN_EXPR_URL" -o "$TMP_DIR/zfin_wildtype_expression.txt"
    mv "$TMP_DIR/zfin_wildtype_expression.txt" "$ZFIN_EXPR_PATH"
    echo "  -> $ZFIN_EXPR_PATH ($(wc -l < "$ZFIN_EXPR_PATH") lines)"
fi

echo "Ontologies ready in $DEST/"
