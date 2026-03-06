"""Score history types and source attribution."""

from __future__ import annotations

from enum import StrEnum


class ScoreSource(StrEnum):
    """Source of a recorded score entry."""

    ASSESSMENT = "assessment"
    MANUAL = "manual"
    EXTERNAL = "external"
