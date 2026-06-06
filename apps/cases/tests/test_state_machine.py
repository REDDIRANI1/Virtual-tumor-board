import pytest
from rest_framework import status
from django.urls import reverse
from apps.cases.tests.factories import CaseFactory
from apps.cases.models import Case
from apps.cases.services import transition_case, StaleVersionError, InvalidTransitionError

pytestmark = pytest.mark.django_db

def test_valid_lifecycle(moderator):
    case = CaseFactory(status='SUBMITTED')
    
    # SUBMITTED -> IN_REVIEW via structure (already tested, here we mock state change)
    case.status = 'IN_REVIEW'
    case.structured_summary = {'test': 'test'}
    case.save()
    
    # IN_REVIEW -> UNDER_DISCUSSION
    case = transition_case(case.id, case.version, 'UNDER_DISCUSSION', moderator)
    assert case.status == 'UNDER_DISCUSSION'
    
    # UNDER_DISCUSSION -> ANSWERED (simulate publish)
    case = transition_case(case.id, case.version, 'ANSWERED', moderator)
    assert case.status == 'ANSWERED'
    
    # ANSWERED -> CLOSED
    case = transition_case(case.id, case.version, 'CLOSED', moderator)
    assert case.status == 'CLOSED'

def test_closed_rejected_from_allowed_states(moderator):
    # Any allowed state to CLOSED/REJECTED
    for state in ['SUBMITTED', 'IN_REVIEW', 'UNDER_DISCUSSION', 'ANSWERED']:
        if state == 'ANSWERED':
            # only CLOSED from ANSWERED
            case = CaseFactory(status=state)
            case = transition_case(case.id, case.version, 'CLOSED', moderator)
            assert case.status == 'CLOSED'
        elif state == 'UNDER_DISCUSSION':
            case = CaseFactory(status=state)
            case = transition_case(case.id, case.version, 'CLOSED', moderator)
            assert case.status == 'CLOSED'
        else:
            case1 = CaseFactory(status=state)
            case1 = transition_case(case1.id, case1.version, 'CLOSED', moderator)
            assert case1.status == 'CLOSED'
            
            case2 = CaseFactory(status=state)
            case2 = transition_case(case2.id, case2.version, 'REJECTED', moderator)
            assert case2.status == 'REJECTED'

def test_invalid_transitions(moderator):
    case = CaseFactory(status='SUBMITTED')
    with pytest.raises(InvalidTransitionError):
        transition_case(case.id, case.version, 'ANSWERED', moderator)
        
    case = CaseFactory(status='ANSWERED')
    with pytest.raises(InvalidTransitionError):
        transition_case(case.id, case.version, 'UNDER_DISCUSSION', moderator)

    case = CaseFactory(status='CLOSED')
    with pytest.raises(InvalidTransitionError):
        transition_case(case.id, case.version, 'ANSWERED', moderator)

    case = CaseFactory(status='REJECTED')
    with pytest.raises(InvalidTransitionError):
        transition_case(case.id, case.version, 'SUBMITTED', moderator)

def test_submitted_to_in_review_via_endpoint_fails(api_client, moderator):
    case = CaseFactory(status='SUBMITTED')
    api_client.force_authenticate(user=moderator)
    url = reverse('cases:case-transition', kwargs={'pk': case.id})
    response = api_client.post(url, {
        'new_status': 'IN_REVIEW',
        'expected_version': case.version
    }, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data['error']['code'] == 'INVALID_TRANSITION'
