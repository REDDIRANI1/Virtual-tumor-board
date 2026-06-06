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
    published_answer = serializers.SerializerMethodField()

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

    def get_published_answer(self, obj):
        if hasattr(obj, 'published_answer'):
            return PublishedAnswerReadSerializer(obj.published_answer).data
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
            if instance.status != 'ANSWERED':
                representation.pop('published_answer', None)
            
        return representation

class CaseStructureSerializer(serializers.Serializer):
    structured_summary = serializers.JSONField()
    expected_version = serializers.IntegerField()

from .models import Comment, Invitation

class CommentPeerSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(source='get_display_name', read_only=True)
    
    class Meta:
        model = Comment
        fields = [
            'id', 'case', 'parent', 'content', 'display_name', 
            'is_anonymous', 'parent_display_name_snapshot', 
            'quoted_text_snapshot', 'quoted_display_name_snapshot', 
            'created_at'
        ]

class CommentAccountabilitySerializer(CommentPeerSerializer):
    author = serializers.PrimaryKeyRelatedField(read_only=True)
    author_username = serializers.CharField(source='author.username', read_only=True)
    
    class Meta(CommentPeerSerializer.Meta):
        fields = CommentPeerSerializer.Meta.fields + ['author', 'author_username']

class CommentCreateSerializer(serializers.Serializer):
    content = serializers.CharField()
    parent_id = serializers.UUIDField(required=False, allow_null=True)
    quoted_comment_id = serializers.UUIDField(required=False, allow_null=True)
    is_anonymous = serializers.BooleanField(default=False)

class InvitationSerializer(serializers.ModelSerializer):
    case = CaseListSerializer(read_only=True)
    
    class Meta:
        model = Invitation
        fields = ['id', 'case', 'status', 'created_at']

class InviteCreateSerializer(serializers.Serializer):
    doctor_id = serializers.UUIDField()

from .models import PublishedAnswer, AmendedAnswer

class AmendedAnswerReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmendedAnswer
        fields = ['id', 'version_number', 'content', 'reason', 'amended_by', 'created_at']

class PublishedAnswerReadSerializer(serializers.ModelSerializer):
    amendments = AmendedAnswerReadSerializer(many=True, read_only=True)
    
    class Meta:
        model = PublishedAnswer
        fields = ['id', 'content', 'published_by', 'published_at', 'amendments']

class PublishAnswerSerializer(serializers.Serializer):
    content = serializers.CharField()
    expected_version = serializers.IntegerField()

class AmendAnswerSerializer(serializers.Serializer):
    content = serializers.CharField()
    reason = serializers.CharField()
    expected_version = serializers.IntegerField()

class TransitionSerializer(serializers.Serializer):
    new_status = serializers.CharField()
    expected_version = serializers.IntegerField()
