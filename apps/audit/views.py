from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import AuditEvent
from .serializers import AuditEventSerializer
from apps.accounts.permissions import IsModerator

class AuditEventListView(generics.ListAPIView):
    serializer_class = AuditEventSerializer
    permission_classes = [IsAuthenticated, IsModerator]

    def get_queryset(self):
        case_id = self.kwargs.get('pk')
        return AuditEvent.objects.filter(case_id=case_id).order_by('-timestamp')
