import pytest
from django.urls import reverse
from rest_framework import status
from apps.cases.models import Case

pytestmark = pytest.mark.django_db

def test_warrior_can_submit_case(api_client, warrior):
    api_client.force_authenticate(user=warrior)
    url = reverse('cases:case-list')
    data = {
        'title': 'My test case',
        'original_question': 'What are the options?'
    }
    response = api_client.post(url, data)
    assert response.status_code == status.HTTP_201_CREATED
    case = Case.objects.get(id=response.data['id'])
    assert case.status == 'SUBMITTED'
    assert case.original_question == 'What are the options?'
    assert case.warrior == warrior

def test_doctor_cannot_submit_case(api_client, doctor):
    api_client.force_authenticate(user=doctor)
    url = reverse('cases:case-list')
    data = {'title': 'Doctor case', 'original_question': 'Q'}
    response = api_client.post(url, data)
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_moderator_cannot_submit_case(api_client, moderator):
    api_client.force_authenticate(user=moderator)
    url = reverse('cases:case-list')
    data = {'title': 'Mod case', 'original_question': 'Q'}
    response = api_client.post(url, data)
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_unauthenticated_cannot_submit_case(api_client):
    url = reverse('cases:case-list')
    data = {'title': 'Anon case', 'original_question': 'Q'}
    response = api_client.post(url, data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_moderator_can_structure_case(api_client, moderator):
    from apps.cases.tests.factories import CaseFactory
    case = CaseFactory(status='SUBMITTED', version=1)
    api_client.force_authenticate(user=moderator)
    url = reverse('cases:case-structure', kwargs={'pk': case.id})
    data = {
        'expected_version': 1,
        'structured_summary': {'key': 'value'}
    }
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_200_OK
    case.refresh_from_db()
    assert case.status == 'IN_REVIEW'
    import json
    assert json.loads(case.structured_summary) == {'key': 'value'}
    assert case.structured_by == moderator
    assert case.version == 2
    assert case.structured_at is not None

def test_warrior_cannot_structure_case(api_client, warrior):
    from apps.cases.tests.factories import CaseFactory
    case = CaseFactory(status='SUBMITTED')
    api_client.force_authenticate(user=warrior)
    url = reverse('cases:case-structure', kwargs={'pk': case.id})
    data = {'expected_version': 1, 'structured_summary': {}}
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_doctor_cannot_structure_case(api_client, doctor):
    from apps.cases.tests.factories import CaseFactory
    case = CaseFactory(status='SUBMITTED')
    api_client.force_authenticate(user=doctor)
    url = reverse('cases:case-structure', kwargs={'pk': case.id})
    data = {'expected_version': 1, 'structured_summary': {}}
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_stale_version_returns_409(api_client, moderator):
    from apps.cases.tests.factories import CaseFactory
    case = CaseFactory(status='SUBMITTED', version=2)
    api_client.force_authenticate(user=moderator)
    url = reverse('cases:case-structure', kwargs={'pk': case.id})
    data = {'expected_version': 1, 'structured_summary': {}}
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_409_CONFLICT
