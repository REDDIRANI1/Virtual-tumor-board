import pytest
from django.urls import reverse
from rest_framework import status
from apps.audit.models import AuditEvent
from apps.cases.tests.factories import CaseFactory, InvitationFactory, CommentFactory

pytestmark = pytest.mark.django_db

def test_audit_event_update_delete_raises_errors(moderator):
    case = CaseFactory()
    event = AuditEvent.objects.create(
        action=AuditEvent.Action.CASE_TRANSITION,
        actor=moderator,
        case=case
    )
    
    with pytest.raises(NotImplementedError):
        event.metadata = {'new': 'data'}
        event.save()
        
    with pytest.raises(NotImplementedError):
        event.delete()

def test_audit_endpoint_moderator_access(api_client, moderator):
    case = CaseFactory()
    AuditEvent.objects.create(
        action=AuditEvent.Action.CASE_STRUCTURED,
        actor=moderator,
        case=case
    )
    api_client.force_authenticate(user=moderator)
    url = reverse('audit:case-audit', kwargs={'pk': case.id})
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1

def test_audit_endpoint_doctor_access(api_client, doctor):
    case = CaseFactory()
    api_client.force_authenticate(user=doctor)
    url = reverse('audit:case-audit', kwargs={'pk': case.id})
    response = api_client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_audit_endpoint_warrior_access(api_client, warrior):
    case = CaseFactory()
    api_client.force_authenticate(user=warrior)
    url = reverse('audit:case-audit', kwargs={'pk': case.id})
    response = api_client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_structure_creates_audit_event(api_client, moderator):
    case = CaseFactory(status='SUBMITTED', version=1)
    api_client.force_authenticate(user=moderator)
    url = reverse('cases:case-structure', kwargs={'pk': case.id})
    api_client.post(url, {'expected_version': 1, 'structured_summary': {}}, format='json')
    assert AuditEvent.objects.filter(case=case, action=AuditEvent.Action.CASE_STRUCTURED).exists()

def test_transition_creates_audit_event(api_client, moderator):
    case = CaseFactory(status='IN_REVIEW', version=1)
    api_client.force_authenticate(user=moderator)
    url = reverse('cases:case-transition', kwargs={'pk': case.id})
    api_client.post(url, {'expected_version': 1, 'new_status': 'UNDER_DISCUSSION'}, format='json')
    assert AuditEvent.objects.filter(case=case, action=AuditEvent.Action.CASE_TRANSITION).exists()

def test_invite_creates_audit_event(api_client, moderator, doctor):
    case = CaseFactory(status='UNDER_DISCUSSION', version=1)
    api_client.force_authenticate(user=moderator)
    url = reverse('cases:case-invite-doctor', kwargs={'pk': case.id})
    api_client.post(url, {'doctor_id': doctor.id}, format='json')
    assert AuditEvent.objects.filter(case=case, action=AuditEvent.Action.DOCTOR_INVITED, target_user=doctor).exists()

def test_comment_creates_audit_event(api_client, doctor):
    case = CaseFactory(status='UNDER_DISCUSSION', version=1)
    InvitationFactory(case=case, doctor=doctor)
    api_client.force_authenticate(user=doctor)
    url = reverse('cases:comment-list', kwargs={'case_pk': case.id})
    api_client.post(url, {'content': 'Test', 'is_anonymous': False}, format='json')
    assert AuditEvent.objects.filter(case=case, action=AuditEvent.Action.COMMENT_CREATED).exists()

def test_reveal_creates_audit_event(api_client, doctor):
    case = CaseFactory(status='UNDER_DISCUSSION', version=1)
    InvitationFactory(case=case, doctor=doctor)
    comment = CommentFactory(case=case, author=doctor, is_anonymous=True)
    api_client.force_authenticate(user=doctor)
    url = reverse('cases:comment-reveal', kwargs={'pk': comment.id})
    api_client.post(url)
    assert AuditEvent.objects.filter(case=case, action=AuditEvent.Action.IDENTITY_REVEALED, target_comment=comment).exists()

def test_publish_creates_audit_event(api_client, moderator):
    case = CaseFactory(status='UNDER_DISCUSSION', version=1)
    api_client.force_authenticate(user=moderator)
    url = reverse('cases:case-publish-answer', kwargs={'pk': case.id})
    api_client.post(url, {'expected_version': 1, 'content': 'Ans'}, format='json')
    assert AuditEvent.objects.filter(case=case, action=AuditEvent.Action.ANSWER_PUBLISHED).exists()

def test_amend_creates_audit_event(api_client, moderator):
    from apps.cases.tests.factories import PublishedAnswerFactory
    case = CaseFactory(status='ANSWERED', version=1)
    PublishedAnswerFactory(case=case)
    api_client.force_authenticate(user=moderator)
    url = reverse('cases:case-amend-answer', kwargs={'pk': case.id})
    api_client.post(url, {'expected_version': 1, 'content': 'Amended', 'reason': 'fix'}, format='json')
    assert AuditEvent.objects.filter(case=case, action=AuditEvent.Action.ANSWER_AMENDED).exists()

def test_ordinary_get_does_not_create_audit_event(api_client, moderator):
    case = CaseFactory(status='SUBMITTED', version=1)
    api_client.force_authenticate(user=moderator)
    url = reverse('cases:case-detail', kwargs={'pk': case.id})
    count_before = AuditEvent.objects.count()
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert AuditEvent.objects.count() == count_before
