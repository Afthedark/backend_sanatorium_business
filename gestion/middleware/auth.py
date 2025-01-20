# gestion/middleware/auth.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings
from django.http import JsonResponse
from gestion.models import Usuario

class CustomJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        try:
            user_id = validated_token['user_id']
            return Usuario.objects.get(id=user_id)
        except Usuario.DoesNotExist:
            return None

# La clase anterior JWTAuthenticationMiddleware ya no es necesaria y puede ser eliminada