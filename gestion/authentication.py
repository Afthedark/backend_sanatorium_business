# gestion/authentication.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Usuario

class CustomJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        try:
            user_id = validated_token['user_id']
            return Usuario.objects.get(pk=user_id)
        except Usuario.DoesNotExist:
            return None