from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CaseViewSet

app_name = 'cases'

router = DefaultRouter()
router.register(r'', CaseViewSet, basename='case')

urlpatterns = [
    path('', include(router.urls)),
]
