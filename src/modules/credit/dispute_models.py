"""Dispute lifecycle types and status transitions."""

from __future__ import annotations

from enum import StrEnum


class DisputeStatus(StrEnum):
    """Status of a dispute record through its lifecycle."""

    DRAFT = "draft"
    SENT = "sent"
    IN_REVIEW = "in_review"
    RESPONDED = "responded"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


# Valid status transitions: current_status -> set of allowed next statuses
VALID_TRANSITIONS: dict[DisputeStatus, set[DisputeStatus]] = {
    DisputeStatus.DRAFT: {DisputeStatus.SENT},
    DisputeStatus.SENT: {DisputeStatus.IN_REVIEW},
    DisputeStatus.IN_REVIEW: {DisputeStatus.RESPONDED},
    DisputeStatus.RESPONDED: {DisputeStatus.RESOLVED, DisputeStatus.ESCALATED},
    DisputeStatus.ESCALATED: {DisputeStatus.SENT},
    DisputeStatus.RESOLVED: set(),
}

# FCRA response deadlines (days from sent_at)
STANDARD_DEADLINE_DAYS = 30
IDENTITY_THEFT_DEADLINE_DAYS = 45
