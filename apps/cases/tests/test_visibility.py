import pytest
from django.urls import reverse
from rest_framework import status
from apps.cases.tests.factories import CaseFactory, InvitationFactory
from apps.accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

def test_warrior_sees_only_own_cases(api_client, warrior):
    other_warrior = UserFactory(role='warrior')
    case1 = CaseFactory(warrior=warrior)
    case2 = CaseFactory(warrior=other_warrior)
    
    api_client.force_authenticate(user=warrior)
    url = reverse('cases:case-list')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]['id'] == str(case1.id)

def test_doctor_sees_only_invited_cases(api_client, doctor):
    case1 = CaseFactory()
    case2 = CaseFactory()
    InvitationFactory(case=case1, doctor=doctor)
    
    api_client.force_authenticate(user=doctor)
    url = reverse('cases:case-list')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]['id'] == str(case1.id)

def test_moderator_sees_all_cases(api_client, moderator):
    CaseFactory.create_batch(3)
    
    api_client.force_authenticate(user=moderator)
    url = reverse('cases:case-list')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 3

def test_non_invited_doctor_sees_empty_list(api_client):
    CaseFactory.create_batch(2)
    other_doctor = UserFactory(role='doctor')
    
    api_client.force_authenticate(user=other_doctor)
    url = reverse('cases:case-list')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 0

def test_warrior_safe_view(api_client, warrior):
    case = CaseFactory(
        warrior=warrior,
        status='IN_REVIEW',
        structured_summary={'hidden': 'secret'}
    )
    
    api_client.force_authenticate(user=warrior)
    url = reverse('cases:case-detail', kwargs={'pk': case.id})
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    
    data = response.data
    assert data['id'] == str(case.id)
    assert data['status'] == 'IN_REVIEW'
    assert data['original_question'] == case.original_question
    assert 'structured_summary' not in data
    assert 'comments' not in data
    assert 'published_answer' not in data

def test_warrior_viewing_closed_or_rejected_case_safe_view(api_client, warrior):
    case = CaseFactory(
        warrior=warrior,
        status='CLOSED',
        structured_summary={'hidden': 'secret'}
    )
    api_client.force_authenticate(user=warrior)
    url = reverse('cases:case-detail', kwargs={'pk': case.id})
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    
    data = response.data
    assert data['id'] == str(case.id)
    assert data['status'] == 'CLOSED'
    assert 'structured_summary' not in data
    assert 'comments' not in data

from apps.cases.tests.factories import PublishedAnswerFactory

def test_warrior_visibility_final_answer(api_client, warrior):
    case = CaseFactory(status='ANSWERED', warrior=warrior)
    answer = PublishedAnswerFactory(case=case, content='The final published answer')
    
    api_client.force_authenticate(user=warrior)
    url = reverse('cases:case-detail', kwargs={'pk': case.id})
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    
    data = response.data
    assert data['status'] == 'ANSWERED'
    assert 'published_answer' in data
    assert data['published_answer']['content'] == 'The final published answer'
    assert 'amendments' in data['published_answer']
    
    assert 'structured_summary' not in data
    assert 'comments' not in data
