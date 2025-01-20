# gestion/middleware/auth.py
import jwt
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
from gestion.models import Usuario

class JWTAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # No validar token para la ruta de login
        if request.path == '/api/login/':
            return self.get_response(request)

        try:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                # Cortar el string después del espacio
                token = auth_header.split(' ')[1]
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                request.user = Usuario.objects.get(id=payload['user_id'])
            else:
                request.user = None
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Usuario.DoesNotExist):
            request.user = None

        response = self.get_response(request)
        return response