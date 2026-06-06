from django.urls import path
from .views import AuditEventListView

app_name = 'audit'

urlpatterns = [
    path('cases/<uuid:pk>/audit/', AuditEventListView.as_view(), name='case-audit'),
]
