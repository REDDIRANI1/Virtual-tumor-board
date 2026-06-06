import pytest
from django.urls import reverse
from rest_framework import status
from apps.cases.tests.factories import CaseFactory, InvitationFactory
from apps.accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

def test_moderator_can_invite_doctor(api_client, moderator):
    case = CaseFactory()
    doctor = UserFactory(role='doctor')
    api_client.force_authenticate(user=moderator)
    url = reverse('cases:case-invite-doctor', kwargs={'pk': case.id})
    response = api_client.post(url, {'doctor_id': doctor.id})
    assert response.status_code == status.HTTP_201_CREATED
    assert case.invitations.filter(doctor=doctor).exists()

def test_duplicate_invite_returns_400(api_client, moderator):
    case = CaseFactory()
    doctor = UserFactory(role='doctor')
    InvitationFactory(case=case, doctor=doctor)
    api_client.force_authenticate(user=moderator)
    url = reverse('cases:case-invite-doctor', kwargs={'pk': case.id})
    response = api_client.post(url, {'doctor_id': doctor.id})
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_invited_doctor_can_access_discussion(api_client, doctor):
    case = CaseFactory(status='UNDER_DISCUSSION')
    InvitationFactory(case=case, doctor=doctor)
    api_client.force_authenticate(user=doctor)
    url = reverse('cases:comment-list', kwargs={'case_pk': case.id})
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK

def test_non_invited_doctor_gets_403(api_client, doctor):
    case = CaseFactory(status='UNDER_DISCUSSION')
    api_client.force_authenticate(user=doctor)
    url = reverse('cases:comment-list', kwargs={'case_pk': case.id})
    response = api_client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_warrior_gets_403_on_comments_endpoint(api_client, warrior):
    case = CaseFactory(status='UNDER_DISCUSSION', warrior=warrior)
    api_client.force_authenticate(user=warrior)
    url = reverse('cases:comment-list', kwargs={'case_pk': case.id})
    response = api_client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_invited_doctor_cannot_invite_other_doctors(api_client, doctor):
    case = CaseFactory()
    InvitationFactory(case=case, doctor=doctor)
    other_doctor = UserFactory(role='doctor')
    api_client.force_authenticate(user=doctor)
    url = reverse('cases:case-invite-doctor', kwargs={'pk': case.id})
    response = api_client.post(url, {'doctor_id': other_doctor.id})
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_get_invitations_list(api_client, doctor):
    invitation = InvitationFactory(doctor=doctor)
    api_client.force_authenticate(user=doctor)
    url = reverse('cases:invitation-list')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]['id'] == str(invitation.id)
    assert 'case' in response.data[0]

def test_warrior_moderator_get_403_on_invitations(api_client, warrior, moderator):
    url = reverse('cases:invitation-list')
    api_client.force_authenticate(user=warrior)
    response = api_client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    api_client.force_authenticate(user=moderator)
    response = api_client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN
