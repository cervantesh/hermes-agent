"""Track 3 classification that separates reachability from security policy."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IsolationPreflight:
    requester_task: str
    owner_task: str
    relationship: str
    visible: bool
    candidate_policy_allows: bool
    security_label: str
    is_vulnerability: bool = False


def classify_current_read(
    *,
    requester_task: str,
    owner_task: str,
    relationship: str,
    visible: bool,
) -> IsolationPreflight:
    if relationship == "declared_completed_parent":
        allowed = True
        label = "POSITIVE_CONTROL"
    elif relationship == "own_task":
        allowed = True
        label = "POSITIVE_CONTROL"
    else:
        allowed = False
        label = "POLICY_UNADJUDICATED" if visible else "NEGATIVE_CONTROL"
    return IsolationPreflight(
        requester_task=requester_task,
        owner_task=owner_task,
        relationship=relationship,
        visible=visible,
        candidate_policy_allows=allowed,
        security_label=label,
    )
