from rest_framework import permissions

class IsWarrior(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'warrior')

class IsDoctor(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'doctor')

class IsModerator(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'moderator')

class IsInvitedDoctor(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated and request.user.role == 'doctor'):
            return False
        
        # Resolve case object (obj itself could be a Case, or it could have a 'case' attribute)
        case = getattr(obj, 'case', obj)
        
        if hasattr(case, 'invitations'):
            return case.invitations.filter(doctor=request.user, status='ACCEPTED').exists()
        return False
