import pytest
from rest_framework import status
from django.urls import reverse
from django.core.exceptions import ValidationError
from apps.cases.tests.factories import CaseFactory, CommentFactory, PublishedAnswerFactory
from apps.cases.models import Comment, PublishedAnswer

pytestmark = pytest.mark.django_db

def test_publish_creates_answer_and_transitions(api_client, moderator):
    case = CaseFactory(status='UNDER_DISCUSSION', version=1)
    
    api_client.force_authenticate(user=moderator)
    url = reverse('cases:case-publish-answer', kwargs={'pk': case.id})
    response = api_client.post(url, {
        'content': 'This is the final answer.',
        'expected_version': 1
    }, format='json')
    
    assert response.status_code == status.HTTP_201_CREATED
    case.refresh_from_db()
    assert case.status == 'ANSWERED'
    assert case.version == 2
    assert hasattr(case, 'published_answer')
    assert case.published_answer.content == 'This is the final answer.'

def test_publish_duplicate_fails(api_client, moderator):
    case = CaseFactory(status='ANSWERED', version=1)
    PublishedAnswerFactory(case=case)
    
    api_client.force_authenticate(user=moderator)
    url = reverse('cases:case-publish-answer', kwargs={'pk': case.id})
    response = api_client.post(url, {
        'content': 'New answer',
        'expected_version': 1
    }, format='json')
    
    assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT]

def test_amend_creates_new_version(api_client, moderator):
    case = CaseFactory(status='ANSWERED', version=1)
    answer = PublishedAnswerFactory(case=case, content='Original Answer')
    
    api_client.force_authenticate(user=moderator)
    url = reverse('cases:case-amend-answer', kwargs={'pk': case.id})
    response = api_client.post(url, {
        'content': 'Amended Answer',
        'reason': 'Correction',
        'expected_version': 1
    }, format='json')
    
    assert response.status_code == status.HTTP_201_CREATED
    case.refresh_from_db()
    assert case.version == 2
    assert answer.amendments.count() == 1
    amend = answer.amendments.first()
    assert amend.content == 'Amended Answer'
    assert amend.reason == 'Correction'
    assert amend.version_number == 1

def test_invited_doctor_cannot_publish_answer(api_client, doctor):
    case = CaseFactory(status='UNDER_DISCUSSION', version=1)
    
    api_client.force_authenticate(user=doctor)
    url = reverse('cases:case-publish-answer', kwargs={'pk': case.id})
    response = api_client.post(url, {
        'content': 'Doctor final answer',
        'expected_version': 1
    }, format='json')
    
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_post_answer_immutability(api_client, doctor, moderator):
    case = CaseFactory(status='ANSWERED')
    answer = PublishedAnswerFactory(case=case, content='Answer text')
    
    # POST comment returns 400/403
    api_client.force_authenticate(user=doctor)
    url = reverse('cases:comment-list', kwargs={'case_pk': case.id})
    response = api_client.post(url, {'content': 'Late comment'}, format='json')
    assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN]
    
    # Comment content update via model save() raises error
    comment = CommentFactory(case=case, content='Early comment')
    with pytest.raises(ValidationError):
        comment.content = 'Edited comment'
        comment.save()

    # PublishedAnswer content update raises error
    with pytest.raises(ValidationError):
        answer.content = 'Silent overwrite'
        answer.save()
