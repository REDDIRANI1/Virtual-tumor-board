from django.db import transaction, models
from rest_framework.exceptions import ValidationError
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

def invite_doctor(case_id, doctor_id, actor):
    from .models import Invitation
    from apps.accounts.models import User
    
    if actor.role != 'moderator':
        raise PermissionDenied("Only a moderator can invite doctors.")
        
    case = Case.objects.filter(id=case_id).first()
    if not case:
        raise ValidationError(f"Case {case_id} not found.")

    doctor = User.objects.filter(id=doctor_id, role='doctor').first()
    if not doctor:
        raise ValidationError(f"User {doctor_id} is not a valid doctor.")
        
    if Invitation.objects.filter(case=case, doctor=doctor).exists():
        raise ValidationError(f"Doctor {doctor.id} is already invited to case {case_id}.")
        
    invitation = Invitation.objects.create(
        case=case,
        doctor=doctor,
        invited_by=actor,
        status='ACCEPTED'
    )
    
    from apps.audit.services import create_audit_event
    from apps.audit.models import AuditEvent
    
    create_audit_event(
        action=AuditEvent.Action.DOCTOR_INVITED,
        actor=actor,
        case=case,
        target_user=doctor,
    )
    
    return invitation

def create_comment(case_id, author, content, is_anonymous=False, parent_id=None, quoted_comment_id=None):
    from .models import Comment, Invitation
    
    with transaction.atomic():
        case = Case.objects.select_for_update().filter(id=case_id).first()
        if not case:
            raise ValidationError(f"Case {case_id} not found.")
            
        if case.status != CaseStatus.UNDER_DISCUSSION.value:
            raise ValidationError("Comments can only be added when case is UNDER_DISCUSSION.")
            
        if not Invitation.objects.filter(case=case, doctor=author, status='ACCEPTED').exists():
            raise PermissionDenied("Only invited doctors can comment on this case.")
            
        parent = None
        if parent_id:
            parent = Comment.objects.filter(id=parent_id, case=case).first()
            if not parent:
                raise ValidationError("Parent comment not found in this case.")
                
        quoted_comment = None
        if quoted_comment_id:
            quoted_comment = Comment.objects.filter(id=quoted_comment_id, case=case).first()
            if not quoted_comment:
                raise ValidationError("Quoted comment not found in this case.")

        anonymous_number = None
        if is_anonymous:
            existing_comment = Comment.objects.filter(case=case, author=author, is_anonymous=True).first()
            if existing_comment:
                anonymous_number = existing_comment.anonymous_number
            else:
                max_anon = Comment.objects.filter(case=case, is_anonymous=True).aggregate(models.Max('anonymous_number'))['anonymous_number__max']
                anonymous_number = (max_anon or 0) + 1

        parent_display_name_snapshot = parent.get_display_name() if parent else None
        quoted_text_snapshot = quoted_comment.content if quoted_comment else None
        quoted_display_name_snapshot = quoted_comment.get_display_name() if quoted_comment else None
        
        comment = Comment.objects.create(
            case=case,
            author=author,
            content=content,
            is_anonymous=is_anonymous,
            anonymous_number=anonymous_number,
            parent=parent,
            parent_display_name_snapshot=parent_display_name_snapshot,
            quoted_comment=quoted_comment,
            quoted_text_snapshot=quoted_text_snapshot,
            quoted_display_name_snapshot=quoted_display_name_snapshot,
        )
        
        from apps.audit.services import create_audit_event
        from apps.audit.models import AuditEvent
        
        create_audit_event(
            action=AuditEvent.Action.COMMENT_CREATED,
            actor=author,
            case=case,
            target_comment=comment,
        )
        
        return comment

def reveal_comment_identity(comment_id, requesting_user):
    from .models import Comment
    
    comment = Comment.objects.filter(id=comment_id).first()
    if not comment:
        raise ValidationError(f"Comment {comment_id} not found.")
        
    if comment.author != requesting_user:
        raise PermissionDenied("Only the author can reveal their identity.")
        
    if not comment.is_anonymous:
        raise ValidationError("Comment is not anonymous.")
        
    if comment.is_revealed:
        raise ValidationError("Identity is already revealed.")
        
    comment.is_revealed = True
    comment.save(update_fields=['is_revealed'])
    
    from apps.audit.services import create_audit_event
    from apps.audit.models import AuditEvent
    
    create_audit_event(
        action=AuditEvent.Action.IDENTITY_REVEALED,
        actor=requesting_user,
        case=comment.case,
        target_comment=comment,
    )
    
    return comment
