from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CaseViewSet, CommentViewSet, CommentRevealView, InvitationListView

app_name = 'cases'

router = DefaultRouter()
router.register(r'cases', CaseViewSet, basename='case')

urlpatterns = [
    path('', include(router.urls)),
    path('cases/<uuid:case_pk>/comments/', CommentViewSet.as_view({'get': 'list', 'post': 'create'}), name='comment-list'),
    path('comments/<uuid:pk>/reveal/', CommentRevealView.as_view(), name='comment-reveal'),
    path('invitations/', InvitationListView.as_view(), name='invitation-list'),
]
