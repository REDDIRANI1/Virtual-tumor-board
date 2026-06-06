from rest_framework import serializers
from .models import AuditEvent

class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = ['id', 'action', 'actor', 'timestamp', 'case', 'target_comment', 'target_user', 'metadata']
