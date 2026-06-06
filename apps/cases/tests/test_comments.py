import pytest
from django.urls import reverse
from rest_framework import status
from apps.cases.tests.factories import CaseFactory, InvitationFactory, CommentFactory
from apps.cases.models import Comment

pytestmark = pytest.mark.django_db

def test_doctor_posts_top_level_comment(api_client, doctor):
    case = CaseFactory(status='UNDER_DISCUSSION')
    InvitationFactory(case=case, doctor=doctor)
    api_client.force_authenticate(user=doctor)
    url = reverse('cases:comment-list', kwargs={'case_pk': case.id})
    response = api_client.post(url, {'content': 'My thoughts', 'is_anonymous': False})
    assert response.status_code == status.HTTP_201_CREATED
    assert Comment.objects.filter(id=response.data['id']).exists()

def test_doctor_posts_reply(api_client, doctor):
    case = CaseFactory(status='UNDER_DISCUSSION')
    InvitationFactory(case=case, doctor=doctor)
    parent_comment = CommentFactory(case=case)
    api_client.force_authenticate(user=doctor)
    url = reverse('cases:comment-list', kwargs={'case_pk': case.id})
    response = api_client.post(url, {'content': 'I agree', 'parent_id': parent_comment.id, 'is_anonymous': False})
    assert response.status_code == status.HTTP_201_CREATED
    assert str(response.data['parent']) == str(parent_comment.id)
    assert response.data['parent_display_name_snapshot'] == parent_comment.get_display_name()

def test_doctor_posts_reply_to_reply(api_client, doctor):
    case = CaseFactory(status='UNDER_DISCUSSION')
    InvitationFactory(case=case, doctor=doctor)
    parent = CommentFactory(case=case)
    reply = CommentFactory(case=case, parent=parent)
    api_client.force_authenticate(user=doctor)
    url = reverse('cases:comment-list', kwargs={'case_pk': case.id})
    response = api_client.post(url, {'content': 'I also agree', 'parent_id': reply.id, 'is_anonymous': False})
    assert response.status_code == status.HTTP_201_CREATED
    assert str(response.data['parent']) == str(reply.id)

def test_comment_ordering(api_client, doctor):
    case = CaseFactory(status='UNDER_DISCUSSION')
    InvitationFactory(case=case, doctor=doctor)
    c1 = CommentFactory(case=case)
    c2 = CommentFactory(case=case)
    api_client.force_authenticate(user=doctor)
    url = reverse('cases:comment-list', kwargs={'case_pk': case.id})
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert [c['id'] for c in response.data] == [str(c1.id), str(c2.id)]

def test_anonymous_comment_presentation(api_client, doctor):
    case = CaseFactory(status='UNDER_DISCUSSION')
    InvitationFactory(case=case, doctor=doctor)
    comment = CommentFactory(case=case, author=doctor, is_anonymous=True, anonymous_number=1)
    api_client.force_authenticate(user=doctor)
    url = reverse('cases:comment-list', kwargs={'case_pk': case.id})
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    data = response.data[0]
    assert data['display_name'] == 'Anonymous Doctor #1'
    assert 'author' not in data
    assert 'author_id' not in data
    assert 'author_username' not in data
    assert 'email' not in data

def test_same_doctor_reuses_anonymous_number(api_client, doctor):
    case = CaseFactory(status='UNDER_DISCUSSION')
    InvitationFactory(case=case, doctor=doctor)
    api_client.force_authenticate(user=doctor)
    url = reverse('cases:comment-list', kwargs={'case_pk': case.id})
    r1 = api_client.post(url, {'content': 'First anon', 'is_anonymous': True})
    r2 = api_client.post(url, {'content': 'Second anon', 'is_anonymous': True})
    assert r1.status_code == status.HTTP_201_CREATED
    assert r2.status_code == status.HTTP_201_CREATED
    c1 = Comment.objects.get(id=r1.data['id'])
    c2 = Comment.objects.get(id=r2.data['id'])
    assert c1.anonymous_number == c2.anonymous_number

def test_moderator_accountability_view_includes_author(api_client, moderator, doctor):
    case = CaseFactory(status='UNDER_DISCUSSION')
    InvitationFactory(case=case, doctor=doctor)
    comment = CommentFactory(case=case, author=doctor, is_anonymous=True, anonymous_number=1)
    api_client.force_authenticate(user=moderator)
    url = reverse('cases:comment-list', kwargs={'case_pk': case.id})
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    data = response.data[0]
    assert 'author' in data
    assert 'author_username' in data
    assert str(data['author']) == str(doctor.id)

def test_reveal_identity(api_client, doctor):
    case = CaseFactory(status='UNDER_DISCUSSION')
    InvitationFactory(case=case, doctor=doctor)
    comment = CommentFactory(case=case, author=doctor, is_anonymous=True, anonymous_number=1)
    reply = CommentFactory(case=case, parent=comment, parent_display_name_snapshot='Anonymous Doctor #1')
    
    api_client.force_authenticate(user=doctor)
    url = reverse('cases:comment-reveal', kwargs={'pk': comment.id})
    response = api_client.post(url)
    assert response.status_code == status.HTTP_200_OK
    
    comment.refresh_from_db()
    assert comment.is_anonymous is True
    assert comment.is_revealed is True
    
    reply.refresh_from_db()
    assert reply.parent_display_name_snapshot == 'Anonymous Doctor #1'

def test_non_author_cannot_reveal(api_client, doctor, moderator):
    case = CaseFactory(status='UNDER_DISCUSSION')
    InvitationFactory(case=case, doctor=doctor)
    comment = CommentFactory(case=case, author=doctor, is_anonymous=True, anonymous_number=1)
    api_client.force_authenticate(user=moderator)
    url = reverse('cases:comment-reveal', kwargs={'pk': comment.id})
    response = api_client.post(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_already_revealed_returns_400(api_client, doctor):
    case = CaseFactory(status='UNDER_DISCUSSION')
    InvitationFactory(case=case, doctor=doctor)
    comment = CommentFactory(case=case, author=doctor, is_anonymous=True, is_revealed=True, anonymous_number=1)
    api_client.force_authenticate(user=doctor)
    url = reverse('cases:comment-reveal', kwargs={'pk': comment.id})
    response = api_client.post(url)
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_reveal_allowed_after_case_answered(api_client, doctor):
    case = CaseFactory(status='ANSWERED')
    InvitationFactory(case=case, doctor=doctor)
    comment = CommentFactory(case=case, author=doctor, is_anonymous=True, anonymous_number=1)
    api_client.force_authenticate(user=doctor)
    url = reverse('cases:comment-reveal', kwargs={'pk': comment.id})
    response = api_client.post(url)
    assert response.status_code == status.HTTP_200_OK
