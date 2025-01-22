from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta

class CustomRefreshToken(RefreshToken):
    @property
    def access_token(self):
        access = self._access_token
        access.set_exp(lifetime=timedelta(hours=1))
        return access

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_exp(lifetime=timedelta(days=7))

    @classmethod
    def for_user(cls, user):
        token = super().for_user(user)
        
        # Add custom claims
        token['user_id'] = user.id
        token['email'] = user.email
        token['rol'] = user.rol
        
        # Add custom claims to access token
        token.access_token['user_id'] = user.id
        token.access_token['email'] = user.email
        token.access_token['rol'] = user.rol
        
        return token