from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Case
from .serializers import (
    CaseCreateSerializer,
    CaseListSerializer,
    CaseDetailSerializer,
    CaseStructureSerializer
)
from .services import structure_case
from apps.accounts.permissions import IsWarrior, IsModerator

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
        return CaseDetailSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsWarrior()]
        elif self.action == 'structure':
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
