# gestion/middleware/auth.py
import jwt
from django.conf import settings
from django.http import JsonResponse
from gestion.models import Usuario

class JWTAuthenticationMiddleware:
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Rutas públicas que no necesitan token
        public_paths = ['/api/login/', '/api/token/refresh/', '/api/docs/', '/api/schema/']
        if request.path in public_paths:
            return self.get_response(request)

        try:
            auth_header = request.headers.get('Authorization', '')
            
            if not auth_header or not auth_header.startswith('Bearer '):
                return JsonResponse(
                    {'error': 'Token no proporcionado o formato inválido'}, 
                    status=401
                )

            token = auth_header.replace('Bearer ', '')
            
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                request.user = Usuario.objects.get(id=payload['user_id'])
            except jwt.ExpiredSignatureError:
                return JsonResponse({'error': 'Token expirado'}, status=401)
            except jwt.InvalidTokenError:
                return JsonResponse({'error': 'Token inválido'}, status=401)
            except Usuario.DoesNotExist:
                return JsonResponse({'error': 'Usuario no encontrado'}, status=401)

            response = self.get_response(request)
            return response

        except Exception as e:
            print(f"Error en middleware: {str(e)}")
            return JsonResponse(
                {'error': 'Error de autenticación'}, 
                status=401
            )