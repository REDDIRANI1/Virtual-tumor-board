from .models import AuditEvent

def create_audit_event(action, actor, case, target_comment=None, target_user=None, metadata=None):
    if metadata is None:
        metadata = {}
        
    event = AuditEvent(
        action=action,
        actor=actor,
        case=case,
        target_comment=target_comment,
        target_user=target_user,
        metadata=metadata
    )
    event.save()
    return event
