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

        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header or 'Bearer' not in auth_header:
            request.user = None
        else:
            try:
                # Extraer token
                token = auth_header.replace('Bearer ', '')
                
                # Decodificar token
                payload = jwt.decode(
                    token, 
                    settings.SECRET_KEY, 
                    algorithms=['HS256']
                )
                
                # Asignar usuario
                request.user = Usuario.objects.get(id=payload['user_id'])
                
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Usuario.DoesNotExist):
                request.user = None

        return self.get_response(request)