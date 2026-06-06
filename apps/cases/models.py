import uuid
from django.db import models
from django.core.exceptions import ValidationError

class CaseStatus(models.TextChoices):
    SUBMITTED = 'SUBMITTED', 'Submitted'
    IN_REVIEW = 'IN_REVIEW', 'In Review'
    UNDER_DISCUSSION = 'UNDER_DISCUSSION', 'Under Discussion'
    ANSWERED = 'ANSWERED', 'Answered'
    CLOSED = 'CLOSED', 'Closed'
    REJECTED = 'REJECTED', 'Rejected'

class Case(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=CaseStatus.choices,
        default=CaseStatus.SUBMITTED
    )
    version = models.PositiveIntegerField(default=1)
    warrior = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='cases'
    )
    original_question = models.TextField()
    structured_summary = models.TextField(null=True, blank=True)
    structured_by = models.ForeignKey(
        'accounts.User',
        null=True,
        on_delete=models.SET_NULL,
        related_name='structured_cases'
    )
    structured_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Invitation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(
        'cases.Case',
        on_delete=models.CASCADE,
        related_name='invitations'
    )
    doctor = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='case_invitations'
    )
    invited_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='sent_invitations'
    )
    status = models.CharField(
        max_length=20,
        default='ACCEPTED',
        choices=[('ACCEPTED', 'Accepted'), ('DECLINED', 'Declined')]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['case', 'doctor'],
                name='unique_case_doctor_invitation'
            )
        ]

    def __str__(self):
        return f"Invite for {self.doctor} to case {self.case.id}"

class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(
        'cases.Case',
        on_delete=models.CASCADE,
        related_name='comments'
    )
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='replies'
    )
    author = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='comments'
    )
    content = models.TextField()
    is_anonymous = models.BooleanField(default=False)
    anonymous_number = models.PositiveIntegerField(null=True, blank=True)
    is_revealed = models.BooleanField(default=False)
    parent_display_name_snapshot = models.CharField(max_length=100, null=True, blank=True)
    quoted_comment = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='quotes'
    )
    quoted_text_snapshot = models.TextField(null=True, blank=True)
    quoted_display_name_snapshot = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_display_name(self):
        if self.is_anonymous and not self.is_revealed:
            return f"Anonymous Doctor #{self.anonymous_number}"
        return self.author.get_full_name() or self.author.username

    def save(self, *args, **kwargs):
        if self.pk is not None:
            old_comment = Comment.objects.filter(pk=self.pk).first()
            if old_comment and old_comment.case.status == CaseStatus.ANSWERED:
                # Disallow update to content (reveal is allowed)
                if old_comment.content != self.content:
                    raise ValidationError("Cannot update comment content after case is answered.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Comment {self.id} on {self.case.id}"

class PublishedAnswer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.OneToOneField(
        'cases.Case',
        on_delete=models.CASCADE,
        related_name='published_answer'
    )
    content = models.TextField()
    published_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='published_answers'
    )
    published_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk is not None and PublishedAnswer.objects.filter(pk=self.pk).exists():
            raise ValidationError("PublishedAnswer records are immutable. Create an AmendedAnswer instead.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Answer for case {self.case.id}"

class AmendedAnswer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    published_answer = models.ForeignKey(
        'cases.PublishedAnswer',
        on_delete=models.CASCADE,
        related_name='amendments'
    )
    version_number = models.PositiveIntegerField()
    content = models.TextField()
    reason = models.TextField()
    amended_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='amended_answers'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['published_answer', 'version_number'],
                name='unique_amendment_version'
            )
        ]

    def __str__(self):
        return f"Amendment {self.version_number} for {self.published_answer.id}"
