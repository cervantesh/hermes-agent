"""Frozen paired sign-test analysis for Lane R."""

from __future__ import annotations

from dataclasses import dataclass

from scipy.stats import binomtest


@dataclass(frozen=True)
class WinAnalysis:
    original_wins: int
    ablated_wins: int
    draws: int
    total_pairs: int
    non_draw_pairs: int
    original_rate: float | None
    confidence_low: float | None
    confidence_high: float | None
    two_sided_p_value: float | None
    disposition: str


def analyze_wins(
    *, original_wins: int, ablated_wins: int, draws: int, alpha: float = 0.05
) -> WinAnalysis:
    if min(original_wins, ablated_wins, draws) < 0:
        raise ValueError("win counts cannot be negative")
    non_draw_pairs = original_wins + ablated_wins
    total_pairs = non_draw_pairs + draws
    if non_draw_pairs == 0:
        return WinAnalysis(
            original_wins,
            ablated_wins,
            draws,
            total_pairs,
            non_draw_pairs,
            None,
            None,
            None,
            None,
            "NON_CONFIRMATORY",
        )

    test = binomtest(original_wins, non_draw_pairs, p=0.5, alternative="two-sided")
    interval = test.proportion_ci(confidence_level=1 - alpha, method="exact")
    if test.pvalue < alpha and original_wins > ablated_wins:
        disposition = "DIRECTIONALLY_COMPATIBLE"
    elif test.pvalue < alpha and ablated_wins > original_wins:
        disposition = "CONTRARY"
    else:
        disposition = "NON_CONFIRMATORY"
    return WinAnalysis(
        original_wins=original_wins,
        ablated_wins=ablated_wins,
        draws=draws,
        total_pairs=total_pairs,
        non_draw_pairs=non_draw_pairs,
        original_rate=original_wins / non_draw_pairs,
        confidence_low=interval.low,
        confidence_high=interval.high,
        two_sided_p_value=test.pvalue,
        disposition=disposition,
    )
