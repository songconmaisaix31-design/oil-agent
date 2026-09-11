"""Advisory material-change classification; C owns history, revisions and recipients."""

from oil_agent.contracts.dto import (
    AssertionStatus,
    EventAssessment,
    EvidenceStatus,
    NotificationKind,
    Severity,
)


def suggest_notification(
    previous: EventAssessment | None,
    current: EventAssessment,
    *,
    allow_first_report: bool = False,
) -> NotificationKind | None:
    """Never sends or grants permission. Call only AFTER C has matched durable history.

    A correction is advisory for the original recipient/revision scope even if
    severity falls; it must not be suppressed by first-report severity/cooldown.
    """
    if previous is None:
        reliable = current.evidence_status in {
            EvidenceStatus.CREDIBLE_SINGLE_SOURCE,
            EvidenceStatus.PUBLISHER_STATEMENT,
            EvidenceStatus.INDEPENDENT_MULTI_SOURCE,
        }
        if (
            allow_first_report
            and reliable
            and current.assertion_status == AssertionStatus.OCCURRED
            and current.severity in {Severity.IMPORTANT, Severity.URGENT}
        ):
            return NotificationKind.FIRST_REPORT
        return None
    if previous.event_id != current.event_id:
        raise ValueError("History must be explicitly matched before comparing event candidates")
    if _signature(previous) == _signature(current):
        return None
    if current.evidence_status == EvidenceStatus.WITHDRAWN:
        return NotificationKind.WITHDRAWAL
    if current.evidence_status in {EvidenceStatus.CORRECTED, EvidenceStatus.CONFLICTING} or (
        previous.assertion_status == AssertionStatus.OCCURRED
        and current.assertion_status != AssertionStatus.OCCURRED
    ):
        return NotificationKind.CORRECTION
    return NotificationKind.UPDATE


def _signature(event: EventAssessment) -> tuple:
    publishers = {
        rid: group.origin_publisher.strip().casefold()
        for group in event.origin_groups
        for rid in group.record_ids
    }
    # Same-origin mirror IDs and processing timestamps do not make a material update.
    quotes = frozenset((publishers[ref.record_id], ref.excerpt) for ref in event.evidence)
    return event.assertion_status, event.evidence_status, event.severity, quotes
