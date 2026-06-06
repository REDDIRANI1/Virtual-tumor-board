import uuid
from django.db import models

class AuditEvent(models.Model):
    class Action(models.TextChoices):
        CASE_TRANSITION = 'CASE_TRANSITION', 'Case Transition'
        CASE_STRUCTURED = 'CASE_STRUCTURED', 'Case Structured'
        DOCTOR_INVITED = 'DOCTOR_INVITED', 'Doctor Invited'
        COMMENT_CREATED = 'COMMENT_CREATED', 'Comment Created'
        IDENTITY_REVEALED = 'IDENTITY_REVEALED', 'Identity Revealed'
        ANSWER_PUBLISHED = 'ANSWER_PUBLISHED', 'Answer Published'
        ANSWER_AMENDED = 'ANSWER_AMENDED', 'Answer Amended'
        CASE_CLOSED = 'CASE_CLOSED', 'Case Closed'
        CASE_REJECTED = 'CASE_REJECTED', 'Case Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.CharField(max_length=30, choices=Action.choices)
    actor = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name='audit_events_as_actor')
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    case = models.ForeignKey('cases.Case', on_delete=models.PROTECT)
    target_comment = models.ForeignKey('cases.Comment', on_delete=models.SET_NULL, null=True, blank=True)
    target_user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_events_as_target')
    metadata = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=['case', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
        ]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            # Check if this is an update to an existing event.
            # In Django, if self.pk is not None, it might still be a forced insert.
            # But the requirement is to append-only and reject updates.
            # The safest way is to prevent save if it already exists in the database.
            try:
                if AuditEvent.objects.filter(pk=self.pk).exists():
                    raise NotImplementedError("Audit events are append-only and cannot be updated.")
            except Exception as e:
                if isinstance(e, NotImplementedError):
                    raise
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise NotImplementedError("Audit events cannot be deleted.")
