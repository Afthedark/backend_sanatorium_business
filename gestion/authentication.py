# gestion/authentication.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import Token
from django.utils.translation import gettext_lazy as _
from .models import Usuario

class CustomJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        """
        Intenta obtener el usuario usando el ID del token validado.
        """
        try:
            user_id = validated_token[self.user_id_claim]
        except KeyError:
            raise InvalidToken(_('Token contained no recognizable user identification'))

        try:
            user = Usuario.objects.get(id=user_id)
        except Usuario.DoesNotExist:
            raise InvalidToken(_('User not found'))

        return user