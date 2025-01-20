# gestion/permissions.py
from rest_framework.permissions import BasePermission

class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        try:
            return request.user and request.user.rol == 'administrador'
        except AttributeError:
            return False

class IsManagerUser(BasePermission):
    def has_permission(self, request, view):
        try:
            return request.user and request.user.rol == 'encargado'
        except AttributeError:
            return False

class IsEmployeeUser(BasePermission):
    def has_permission(self, request, view):
        try:
            return request.user and request.user.rol == 'empleado'
        except AttributeError:
            return False

class IsManagerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        try:
            return request.user and request.user.rol in ['encargado', 'administrador']
        except AttributeError:
            return False