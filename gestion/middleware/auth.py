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
        # Rutas que no necesitan validación
        public_paths = ['/api/login/', '/api/token/refresh/']
        if request.path in public_paths:
            return self.get_response(request)

        try:
            auth_header = request.headers.get('Authorization', '')
            
            # Validar formato Bearer
            if not auth_header or not auth_header.startswith('Bearer '):
                request.user = None
                return self.get_response(request)

            # Extraer y validar token
            token = auth_header.split(' ')[1]
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            
            # Asignar usuario
            request.user = Usuario.objects.get(id=payload['user_id'])

        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Usuario.DoesNotExist):
            request.user = None

        return self.get_response(request)