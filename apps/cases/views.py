from rest_framework import viewsets, mixins, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Case, Comment, Invitation
from .serializers import (
    CaseCreateSerializer,
    CaseListSerializer,
    CaseDetailSerializer,
    CaseStructureSerializer,
    CommentPeerSerializer,
    CommentAccountabilitySerializer,
    CommentCreateSerializer,
    InvitationSerializer,
    InviteCreateSerializer
)
from .services import structure_case, invite_doctor, create_comment, reveal_comment_identity
from apps.accounts.permissions import IsWarrior, IsModerator, IsDoctor

class CaseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'warrior':
            return Case.objects.filter(warrior=user)
        elif user.role == 'doctor':
            return Case.objects.filter(invitations__doctor=user, invitations__status='ACCEPTED').distinct()
        elif user.role == 'moderator':
            return Case.objects.all()
        return Case.objects.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return CaseCreateSerializer
        elif self.action == 'list':
            return CaseListSerializer
        elif self.action == 'structure':
            return CaseStructureSerializer
        elif self.action == 'invite_doctor':
            return InviteCreateSerializer
        return CaseDetailSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsWarrior()]
        elif self.action == 'structure' or self.action == 'invite_doctor':
            return [IsAuthenticated(), IsModerator()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(warrior=self.request.user, status='SUBMITTED')

    @action(detail=True, methods=['post'])
    def structure(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        case = structure_case(
            case_id=pk,
            expected_version=serializer.validated_data['expected_version'],
            structured_summary=serializer.validated_data['structured_summary'],
            actor=request.user
        )
        
        # Return updated case using detail serializer
        return Response(CaseDetailSerializer(case, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='invite-doctor')
    def invite_doctor(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        invitation = invite_doctor(
            case_id=pk,
            doctor_id=serializer.validated_data['doctor_id'],
            actor=request.user
        )
        
        return Response(InvitationSerializer(invitation).data, status=status.HTTP_201_CREATED)

class CommentViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request, case_pk=None):
        case = Case.objects.filter(id=case_pk).first()
        if not case:
            return Response({"error": "Case not found"}, status=status.HTTP_404_NOT_FOUND)
            
        user = request.user
        if user.role == 'warrior':
            return Response(status=status.HTTP_403_FORBIDDEN)
        elif user.role == 'doctor':
            if not Invitation.objects.filter(case=case, doctor=user, status='ACCEPTED').exists():
                return Response(status=status.HTTP_403_FORBIDDEN)
                
        comments = Comment.objects.filter(case=case).order_by('created_at')
        
        if user.role == 'moderator':
            serializer = CommentAccountabilitySerializer(comments, many=True)
        else:
            serializer = CommentPeerSerializer(comments, many=True)
            
        return Response(serializer.data)

    def create(self, request, case_pk=None):
        case = Case.objects.filter(id=case_pk).first()
        if not case:
            return Response({"error": "Case not found"}, status=status.HTTP_404_NOT_FOUND)
            
        user = request.user
        if user.role == 'warrior':
            return Response(status=status.HTTP_403_FORBIDDEN)
            
        serializer = CommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        comment = create_comment(
            case_id=case_pk,
            author=user,
            content=serializer.validated_data['content'],
            is_anonymous=serializer.validated_data.get('is_anonymous', False),
            parent_id=serializer.validated_data.get('parent_id'),
            quoted_comment_id=serializer.validated_data.get('quoted_comment_id')
        )
        
        return Response(CommentPeerSerializer(comment).data, status=status.HTTP_201_CREATED)

class CommentRevealView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk=None):
        comment = reveal_comment_identity(comment_id=pk, requesting_user=request.user)
        return Response(CommentPeerSerializer(comment).data)

class InvitationListView(generics.ListAPIView):
    serializer_class = InvitationSerializer
    permission_classes = [IsAuthenticated, IsDoctor]

    def get_queryset(self):
        return Invitation.objects.filter(doctor=self.request.user)
