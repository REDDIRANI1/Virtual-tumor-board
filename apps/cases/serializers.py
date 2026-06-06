import json
from rest_framework import serializers
from .models import Case

class CaseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Case
        fields = ['id', 'title', 'original_question']

class CaseListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Case
        fields = ['id', 'title', 'status', 'created_at']

class CaseDetailSerializer(serializers.ModelSerializer):
    structured_summary = serializers.SerializerMethodField()

    class Meta:
        model = Case
        fields = '__all__'
        
    def get_structured_summary(self, obj):
        if obj.structured_summary:
            try:
                return json.loads(obj.structured_summary)
            except (ValueError, TypeError):
                return obj.structured_summary
        return None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        
        # Warrior gets safe fields only
        if request and request.user.role == 'warrior':
            unsafe_fields = [
                'structured_summary', 'structured_by', 'structured_at',
            ]
            for field in unsafe_fields:
                representation.pop(field, None)
            representation.pop('comments', None)
            representation.pop('published_answer', None)
            
        return representation

class CaseStructureSerializer(serializers.Serializer):
    structured_summary = serializers.JSONField()
    expected_version = serializers.IntegerField()
