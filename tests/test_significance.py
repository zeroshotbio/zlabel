"""Unit tests for zlabel.significance -- the pure-stdlib hypergeometric survival function.

The engine core stays dependency-free (no scipy), so hypergeom_sf is hand-rolled with math.comb.
These tests pin it to scipy.stats.hypergeom.sf (available via the [eval] extra) so the stdlib
implementation is provably correct.
"""

import math

import pytest

from zlabel.significance import hypergeom_sf


def test_hypergeom_sf_matches_scipy():
    # hypergeom_sf(k, M, K, n) = P(X >= k); scipy's sf(x) = P(X > x), so sf(k-1) = P(X >= k).
    stats = pytest.importorskip("scipy.stats")
    cases = [(3, 50, 10, 8), (1, 100, 30, 20), (5, 200, 25, 25), (2, 30, 6, 12), (4, 500, 31, 24)]
    for k, M, K, n in cases:
        expected = float(stats.hypergeom.sf(k - 1, M, K, n))
        assert math.isclose(hypergeom_sf(k, M, K, n), expected, rel_tol=1e-9, abs_tol=1e-12)


def test_hypergeom_sf_edge_cases():
    # P(X >= 0) is always 1; drawing more successes than exist is impossible.
    assert hypergeom_sf(0, 10, 3, 4) == 1.0
    assert hypergeom_sf(4, 10, 3, 4) == 0.0  # only 3 successes in the population
    assert hypergeom_sf(1, 10, 0, 4) == 0.0  # no successes in the population


def test_hypergeom_sf_monotone_in_k():
    # The survival function is non-increasing in k: requiring more hits is never more likely.
    values = [hypergeom_sf(k, 200, 25, 25) for k in range(0, 8)]
    assert all(earlier >= later for earlier, later in zip(values, values[1:], strict=False))
