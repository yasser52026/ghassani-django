from rest_framework.permissions import BasePermission

from .models import ROLE_ADMIN, ROLE_GESTIONNAIRE, ROLE_CHEF_SERVICE, ROLE_DIRECTEUR


def role_requis(*roles_autorises):
    class RoleRequis(BasePermission):
        def has_permission(self, request, view):
            return bool(
                request.user and request.user.is_authenticated
                and request.user.role in roles_autorises
            )
    return RoleRequis


def acces_service_autorise(user, service_id):
    if user.role in (ROLE_ADMIN, ROLE_GESTIONNAIRE, ROLE_DIRECTEUR):
        return True
    if user.role == ROLE_CHEF_SERVICE:
        return user.service_id == service_id
    return False
