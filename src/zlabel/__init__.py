"""zlabel — label one whole-organism zebrafish scRNA-seq cluster from its markers."""

from zlabel.data import (
    ALL_RELATION_EDGE_TYPES,
    DEFAULT_ANCESTOR_EDGE_TYPES,
    ZfinExpressionRecord,
    ancestors,
    children,
    get_term,
    load_gene_synonym_map,
    load_zfa,
    load_zfin_expression,
    term_name,
)
from zlabel.genes import (
    STATUS_AMBIGUOUS,
    STATUS_RESOLVED,
    STATUS_UNRESOLVED,
    NormalizedSymbol,
    drop_uninformative,
    is_uninformative,
    normalize_markers,
    normalize_symbol,
)
from zlabel.label import Labeler
from zlabel.models import Confidence, Label
from zlabel.panels import (
    KIND_IDENTITY,
    KIND_STATE,
    BucketScore,
    MatchedMarker,
    Panel,
    load_panels,
    score_markers,
)

__version__ = "0.1.0"

__all__ = [
    # data
    "ALL_RELATION_EDGE_TYPES",
    "DEFAULT_ANCESTOR_EDGE_TYPES",
    "ZfinExpressionRecord",
    "__version__",
    "ancestors",
    "children",
    "get_term",
    "load_gene_synonym_map",
    "load_zfa",
    "load_zfin_expression",
    "term_name",
    # genes
    "STATUS_AMBIGUOUS",
    "STATUS_RESOLVED",
    "STATUS_UNRESOLVED",
    "NormalizedSymbol",
    "drop_uninformative",
    "is_uninformative",
    "normalize_markers",
    "normalize_symbol",
    # label (the entry point; decide() + grounding helpers stay on submodules)
    "Labeler",
    # models (the return packet + its tier type; ExprHit/tier names on zlabel.models)
    "Confidence",
    "Label",
    # panels
    "KIND_IDENTITY",
    "KIND_STATE",
    "BucketScore",
    "MatchedMarker",
    "Panel",
    "load_panels",
    "score_markers",
]
