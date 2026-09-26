from rest_framework.permissions import BasePermission

from .models import Profile


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_staff
            or Profile.objects.filter(user=request.user, role=Profile.Role.ADMIN).exists()
        )


class IsAnalystOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_staff
            or Profile.objects.filter(
                user=request.user,
                role__in=(Profile.Role.ADMIN, Profile.Role.ANALYST),
            ).exists()
        )
