import pytest
from rest_framework import status
from django.urls import reverse
from apps.cases.tests.factories import CaseFactory
from apps.cases.models import Case
from apps.cases.services import transition_case, StaleVersionError

pytestmark = pytest.mark.django_db

def test_stale_expected_version_on_transition(api_client, moderator):
    case = CaseFactory(status='UNDER_DISCUSSION', version=1)
    
    # Simulate another moderator transitioning the case
    case.version = 2
    case.save()

    api_client.force_authenticate(user=moderator)
    url = reverse('cases:case-transition', kwargs={'pk': case.id})
    response = api_client.post(url, {
        'new_status': 'CLOSED',
        'expected_version': 1
    }, format='json')
    
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data['error']['code'] == 'STALE_VERSION'

def test_stale_expected_version_on_structure(api_client, moderator):
    case = CaseFactory(status='SUBMITTED', version=1)
    
    case.version = 2
    case.save()

    api_client.force_authenticate(user=moderator)
    url = reverse('cases:case-structure', kwargs={'pk': case.id})
    response = api_client.post(url, {
        'structured_summary': {'test': 'test'},
        'expected_version': 1
    }, format='json')
    
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data['error']['code'] == 'STALE_VERSION'

def test_stale_expected_version_on_publish(api_client, moderator):
    case = CaseFactory(status='UNDER_DISCUSSION', version=1)
    
    case.version = 2
    case.save()

    api_client.force_authenticate(user=moderator)
    url = reverse('cases:case-publish-answer', kwargs={'pk': case.id})
    response = api_client.post(url, {
        'content': 'Final Answer',
        'expected_version': 1
    }, format='json')
    
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data['error']['code'] == 'STALE_VERSION'

def test_two_simultaneous_transitions(moderator):
    case = CaseFactory(status='UNDER_DISCUSSION', version=1)
    
    # First transition
    transition_case(case.id, 1, 'CLOSED', moderator)
    
    # Second transition fails
    with pytest.raises(StaleVersionError):
        transition_case(case.id, 1, 'IN_REVIEW', moderator)
