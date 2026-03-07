"""Shared scoring utilities for Baby INERTIA agents."""

from __future__ import annotations

_BAND_THRESHOLDS: list[tuple[int, str]] = [
    (499, "300-499"),
    (549, "500-549"),
    (599, "550-599"),
    (649, "600-649"),
    (699, "650-699"),
    (749, "700-749"),
    (850, "750-850"),
]


def score_to_band(score: int) -> str:
    """Map a numeric FICO score to the config band key (e.g. '550-599')."""
    for upper, label in _BAND_THRESHOLDS:
        if score <= upper:
            return label
    return "750-850"
