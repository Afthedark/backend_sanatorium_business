# gestion/tokens.py
from rest_framework_simplejwt.tokens import Token
from rest_framework_simplejwt.models import TokenUser

class CustomTokenUser(TokenUser):
    @classmethod
    def for_user(cls, user):
        token_user = cls()
        token_user.id = user.id
        token_user.email = user.email
        token_user.rol = user.rol
        return token_user

class CustomToken(Token):
    token_type = 'access'
    user_class = CustomTokenUser

class CustomRefreshToken(CustomToken):
    token_type = 'refresh'