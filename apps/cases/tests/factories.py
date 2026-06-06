import factory
from apps.cases.models import Case, Invitation, Comment, PublishedAnswer, AmendedAnswer
from apps.accounts.tests.factories import UserFactory

class CaseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Case

    title = factory.Sequence(lambda n: f'Fake Case #{n}')
    status = 'SUBMITTED'
    version = 1
    warrior = factory.SubFactory(UserFactory, role='warrior')
    original_question = 'What are my options for fictional condition X?'

class InvitationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Invitation

    case = factory.SubFactory(CaseFactory)
    doctor = factory.SubFactory(UserFactory, role='doctor')
    invited_by = factory.SubFactory(UserFactory, role='moderator')
    status = 'ACCEPTED'

class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Comment

    case = factory.SubFactory(CaseFactory)
    author = factory.SubFactory(UserFactory, role='doctor')
    content = 'This is a fake discussion comment'
    is_anonymous = False
    is_revealed = False

class PublishedAnswerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PublishedAnswer

    case = factory.SubFactory(CaseFactory)
    content = 'This is a verified fake published answer.'
    published_by = factory.SubFactory(UserFactory, role='moderator')

class AmendedAnswerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AmendedAnswer

    published_answer = factory.SubFactory(PublishedAnswerFactory)
    version_number = 1
    content = 'This is an amended fake published answer.'
    reason = 'Correction of a typographical error.'
    amended_by = factory.SubFactory(UserFactory, role='moderator')
