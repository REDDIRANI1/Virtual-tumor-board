from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import F
from .models import Case, CaseStatus

class StaleVersionError(Exception):
    pass

class InvalidTransitionError(Exception):
    pass

VALID_TRANSITIONS = {
    CaseStatus.SUBMITTED.value: [
        CaseStatus.CLOSED.value,
        CaseStatus.REJECTED.value,
    ],
    CaseStatus.IN_REVIEW.value: [
        CaseStatus.UNDER_DISCUSSION.value,
        CaseStatus.CLOSED.value,
        CaseStatus.REJECTED.value,
    ],
    CaseStatus.UNDER_DISCUSSION.value: [
        CaseStatus.ANSWERED.value,
        CaseStatus.CLOSED.value,
    ],
    CaseStatus.ANSWERED.value: [
        CaseStatus.CLOSED.value,
    ],
    CaseStatus.CLOSED.value: [],
    CaseStatus.REJECTED.value: [],
}

def validate_transition(from_status, to_status):
    allowed = VALID_TRANSITIONS.get(from_status, [])
    if to_status not in allowed:
        raise InvalidTransitionError(f"Invalid transition from {from_status} to {to_status}")

def transition_case(case_id, expected_version, new_status, actor):
    """
    Transitions a case to a new status safely using optimistic locking.
    """
    case = Case.objects.filter(id=case_id).first()
    if not case:
        raise ValidationError(f"Case {case_id} not found.")

    validate_transition(case.status, new_status)

    with transaction.atomic():
        updated_rows = Case.objects.filter(
            id=case_id,
            version=expected_version
        ).update(
            status=new_status,
            version=F('version') + 1,
            updated_at=timezone.now()
        )

        if updated_rows == 0:
            raise StaleVersionError(f"Stale version for case {case_id}. Expected {expected_version}.")
        
        old_status = case.status
        case.refresh_from_db()
        
        from apps.audit.services import create_audit_event
        from apps.audit.models import AuditEvent
        
        action = AuditEvent.Action.CASE_TRANSITION
        if new_status == CaseStatus.CLOSED.value:
            action = AuditEvent.Action.CASE_CLOSED
        elif new_status == CaseStatus.REJECTED.value:
            action = AuditEvent.Action.CASE_REJECTED
            
        create_audit_event(
            action=action,
            actor=actor,
            case=case,
            metadata={"from_status": old_status, "to_status": new_status, "version": case.version}
        )
        
        return case

import json
from rest_framework.exceptions import PermissionDenied

def structure_case(case_id, expected_version, structured_summary, actor):
    if actor.role != 'moderator':
        raise PermissionDenied("Only a moderator can structure cases.")
        
    case = Case.objects.filter(id=case_id).first()
    if not case:
        raise ValidationError(f"Case {case_id} not found.")

    if case.status != CaseStatus.SUBMITTED.value:
        raise InvalidTransitionError("Only SUBMITTED cases can be structured.")

    with transaction.atomic():
        updated_rows = Case.objects.filter(
            id=case_id,
            version=expected_version
        ).update(
            status=CaseStatus.IN_REVIEW.value,
            version=F('version') + 1,
            structured_summary=json.dumps(structured_summary),
            structured_by=actor,
            structured_at=timezone.now(),
            updated_at=timezone.now()
        )

        if updated_rows == 0:
            raise StaleVersionError(f"Stale version for case {case_id}. Expected {expected_version}.")
            
        case.refresh_from_db()
        
        from apps.audit.services import create_audit_event
        from apps.audit.models import AuditEvent
        
        create_audit_event(
            action=AuditEvent.Action.CASE_STRUCTURED,
            actor=actor,
            case=case,
            metadata={"version": case.version}
        )
        
        return case
