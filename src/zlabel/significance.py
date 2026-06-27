"""Hypergeometric significance for panel overlap, in pure stdlib (no scipy in the engine core).

The panel scorer asks how much of a cluster's marker weight fell on each panel. A complementary,
parameter-free question is whether that overlap is more than chance: if a cluster has n markers drawn
from a gene universe of size M that contains a panel of K genes, how surprising is it that k of them
landed on the panel? That is the upper tail of a hypergeometric distribution. This module computes it
exactly with math.comb so the dependency-free core can use it; tests/test_significance.py pins it to
scipy.stats.hypergeom.sf.
"""

from __future__ import annotations

from math import comb


def hypergeom_sf(k: int, M: int, K: int, n: int) -> float:
    """Upper-tail hypergeometric probability P(X >= k): the chance of k-or-more panel hits.

    X is the number of a panel's genes among n genes drawn without replacement from a universe of M
    genes containing K panel genes. P(X >= k) is the exact overlap p-value: small means the cluster's
    panel overlap is unlikely under random marker draws. Matches scipy.stats.hypergeom.sf(k - 1, M, K, n).

    Args:
        k (int): Observed panel hits (markers that landed on the panel). P(X >= k) is returned.
        M (int): Population size (the gene universe the scorer can match against).
        K (int): Panel genes present in the universe (the successes in the population).
        n (int): Draws (the cluster's tested markers present in the universe).

    Returns:
        float: P(X >= k) in 0..1. Returns 1.0 for k <= 0 (the trivial tail) and 0.0 when k exceeds
        the most hits attainable (min(K, n)) or the universe is empty.
    """
    if k <= 0:
        return 1.0
    upper = min(K, n)
    if k > upper:
        return 0.0
    denominator = comb(M, n)
    if denominator == 0:
        return 0.0
    numerator = sum(comb(K, hits) * comb(M - K, n - hits) for hits in range(k, upper + 1))
    return numerator / denominator
