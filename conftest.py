import pytest
from rest_framework.test import APIClient

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def warrior(db):
    from apps.accounts.tests.factories import UserFactory
    return UserFactory(role='warrior')

@pytest.fixture
def moderator(db):
    from apps.accounts.tests.factories import UserFactory
    return UserFactory(role='moderator')

@pytest.fixture
def doctor(db):
    from apps.accounts.tests.factories import UserFactory
    return UserFactory(role='doctor')

@pytest.fixture
def authenticated_client(api_client):
    def _client(user):
        api_client.force_authenticate(user=user)
        return api_client
    return _client
