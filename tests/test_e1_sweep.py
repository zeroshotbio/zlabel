"""Unit tests for the E1 specificity-sweep harm aggregator (scripts/e1_specificity_sweep.py).

Data-free: the harm-table logic is pure functions over ClusterOutcome lists, so it is
tested with hand-built outcomes -- no ontologies, no benchmark CSV.
"""

import e1_specificity_sweep as sweep

from zlabel.evaluate import ClusterOutcome


def _outcome(
    cluster_id: str, gold: str, panel_bucket: str, agrees: bool | None, *, scored: bool = True, kind: str = "named"
) -> ClusterOutcome:
    return ClusterOutcome(
        cluster_id=cluster_id,
        gold_tissue=gold,
        tissue_name="",
        stage_hpf=None,
        markers=[],
        n_resolved=0,
        kind=kind,
        bucket=panel_bucket,
        panel_bucket=panel_bucket,
        zfa_id=None,
        depth=1,
        scored=scored,
        agrees=agrees,
        confidence=None,
        convergent_genes=(),
        abstain_reason=None,
        audit=None,
    )


def test_attractor_win_is_scored_wrong_attractor_call():
    # A scored call that named an attractor panel and disagrees with gold.
    win = _outcome("c1", "axia", "epidermis", agrees=False)
    right_attractor = _outcome("c2", "epi", "epidermis", agrees=True)  # attractor but correct -> not a win
    unscored = _outcome("c3", "axia", "epidermis", agrees=False, scored=False)
    assert sweep.is_attractor_win(win)
    assert not sweep.is_attractor_win(right_attractor)
    assert not sweep.is_attractor_win(unscored)


def test_correct_winner_is_scored_right_promiscuous_call():
    # A scored call that named a promiscuous-but-correct lineage and agrees with gold.
    winner = _outcome("c1", "noto", "notochord", agrees=True)
    wrong = _outcome("c2", "noto", "notochord", agrees=False)
    non_promiscuous = _outcome("c3", "musc", "muscle", agrees=True)
    assert sweep.is_correct_winner(winner)
    assert not sweep.is_correct_winner(wrong)
    assert not sweep.is_correct_winner(non_promiscuous)


def test_correct_winner_demotions_counts_lost_winners_only():
    # cartilage was a correct winner at alpha=0; the blend flips it to a wrong epidermis
    # call -> one demotion. notochord stays correct -> not counted. This is the harm the
    # N0b finding predicts: demoting promiscuous markers can demote correct winners too.
    base = [
        _outcome("c1", "noto", "notochord", agrees=True),
        _outcome("c2", "cart", "cartilage", agrees=True),
    ]
    after = [
        _outcome("c1", "noto", "notochord", agrees=True),
        _outcome("c2", "cart", "epidermis", agrees=False),
    ]
    assert sweep.correct_winner_demotions(base, after) == 1
    assert sweep.correct_winner_demotions(base, base) == 0


def test_agreement_coverage_excludes_unscored_and_unscoreable():
    outcomes = [
        _outcome("c1", "musc", "muscle", agrees=True),
        _outcome("c2", "noto", "notochord", agrees=False),
        _outcome("c3", "x", "mixed", agrees=None, kind="abstain"),  # scored but not scoreable
        _outcome("c4", "z", "muscle", agrees=True, scored=False),  # not scored at all
    ]
    agreement, coverage = sweep.agreement_coverage(outcomes)
    # scored = c1,c2,c3; scoreable (agrees not None) = c1,c2; agree = c1 -> agreement 1/2.
    assert agreement == 0.5
    # coverage = scoreable / scored = 2/3.
    assert abs(coverage - 2 / 3) < 1e-9
