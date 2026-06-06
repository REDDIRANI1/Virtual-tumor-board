import pytest
from django.urls import reverse
from rest_framework import status
from apps.cases.tests.factories import CaseFactory
import json

pytestmark = pytest.mark.django_db

def test_validation_error_format(api_client, warrior):
    # Missing required title field
    api_client.force_authenticate(user=warrior)
    url = reverse('cases:case-list')
    data = {'original_question': 'Q'}
    response = api_client.post(url, data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'error' in response.data
    assert response.data['error']['code'] == 'VALIDATION_ERROR'
    assert 'title' in response.data['error']['detail']

def test_permission_denied_format(api_client, doctor):
    # Doctor trying to create a case
    api_client.force_authenticate(user=doctor)
    url = reverse('cases:case-list')
    data = {'title': 'T', 'original_question': 'Q'}
    response = api_client.post(url, data)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert 'error' in response.data
    assert response.data['error']['code'] == 'PERMISSION_DENIED'

def test_stale_version_format(api_client, moderator):
    case = CaseFactory(status='SUBMITTED', version=2)
    api_client.force_authenticate(user=moderator)
    url = reverse('cases:case-structure', kwargs={'pk': case.id})
    data = {'expected_version': 1, 'structured_summary': {}}
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_409_CONFLICT
    assert 'error' in response.data
    assert response.data['error']['code'] == 'STALE_VERSION'

def test_invalid_transition_format(api_client, moderator):
    case = CaseFactory(status='SUBMITTED', version=1)
    api_client.force_authenticate(user=moderator)
    url = reverse('cases:case-transition', kwargs={'pk': case.id})
    data = {'expected_version': 1, 'new_status': 'ANSWERED'}
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'error' in response.data
    assert response.data['error']['code'] == 'INVALID_TRANSITION'

def test_error_bodies_do_not_contain_author_id(api_client, doctor, moderator):
    # Try to reveal a comment that doesn't belong to the user
    # to check if the error reveals true author id.
    from apps.cases.tests.factories import CommentFactory, InvitationFactory
    case = CaseFactory(status='UNDER_DISCUSSION', version=1)
    InvitationFactory(case=case, doctor=doctor)
    comment = CommentFactory(case=case, author=doctor, is_anonymous=True)
    
    api_client.force_authenticate(user=moderator)
    url = reverse('cases:comment-reveal', kwargs={'pk': comment.id})
    response = api_client.post(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    
    error_str = json.dumps(response.data)
    assert str(doctor.id) not in error_str
    assert doctor.username not in error_str
