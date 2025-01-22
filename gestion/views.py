from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db import transaction
from django.db.models import F, Max
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.utils import extend_schema, OpenApiParameter
import logging

from .models import Usuario, Proyecto, Permiso, Tarea
from .serializers import (
    UsuarioSerializer, 
    ProyectoSerializer, 
    PermisoSerializer, 
    TareaSerializer, 
    ActualizarTareaSerializer,
    RegistroEmpleadoSerializer,
    EmpleadosPorEncargadoSerializer,
    ProyectosPorEncargadoSerializer,
    ProyectosAsignadosEmpleadoSerializer,
    TareasEmpleadoSerializer,
    TareasProyectoSerializer,
    TareasEmpleadosEncargadoSerializer,
    CustomTokenObtainPairSerializer,
)

logger = logging.getLogger(__name__)

# Authentication Views
class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = CustomTokenObtainPairSerializer

class RefreshTokenView(TokenRefreshView):
    permission_classes = [AllowAny]

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        try:
            data = {
                'id': user.id,
                'nombre': user.nombre,
                'email': user.email,
                'rol': user.rol,
                'created_at': user.created_at,
                'updated_at': user.updated_at,
            }
            
            if user.rol == 'empleado' and user.encargado:
                data['encargado'] = {
                    'id': user.encargado.id,
                    'nombre': user.encargado.nombre,
                    'email': user.encargado.email,
                    'rol': user.encargado.rol
                }
                
            return Response(data)
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



# Vistas para CRUD
class UsuarioViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer

class ProyectoViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Proyecto.objects.all()
    serializer_class = ProyectoSerializer

class PermisoViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Permiso.objects.all()
    serializer_class = PermisoSerializer



class TareaViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Tarea.objects.all()
    serializer_class = TareaSerializer

    def perform_create(self, serializer):
        with transaction.atomic():
            proyecto = serializer.validated_data.get('proyecto')
            empleado = serializer.validated_data.get('empleado')
            
            # Obtener el máximo orden actual para este empleado y estado
            max_orden = Tarea.objects.filter(
                proyecto=proyecto,
                empleado=empleado,
                estado='pendiente'
            ).aggregate(Max('orden'))['orden__max']
            
            # Asegurar que el orden comience en 1
            nuevo_orden = 1 if max_orden is None else max_orden + 1
            
            # Crear la tarea
            tarea = serializer.save(
                estado='pendiente',
                orden=nuevo_orden
            )

            # Reordenar todas las tareas para asegurar secuencia consecutiva
            tareas = Tarea.objects.filter(
                proyecto=proyecto,
                empleado=empleado,
                estado='pendiente'
            ).order_by('orden')
            
            for index, t in enumerate(tareas, 1):
                if t.orden != index:
                    t.orden = index
                    t.save(update_fields=['orden'])

    

# API personalizada para actualizar tareas
@extend_schema(tags=['Tareas'])
class ActualizarTareaEmpleadoAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        serializer = ActualizarTareaSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                data = serializer.validated_data
                tarea = Tarea.objects.select_for_update().get(id=data['id'])
                
                estado_anterior = tarea.estado
                orden_anterior = tarea.orden
                nuevo_estado = data['nuevo_estado']
                nuevo_orden = data.get('nuevo_orden')

                # Si cambia el estado
                if estado_anterior != nuevo_estado:
                    # Reordenar tareas en estado anterior del mismo empleado
                    Tarea.objects.filter(
                        proyecto=tarea.proyecto,
                        empleado=tarea.empleado,
                        estado=estado_anterior,
                        orden__gt=orden_anterior
                    ).update(orden=F('orden') - 1)

                    # Calcular nuevo orden en nuevo estado
                    if nuevo_orden is None:
                        max_orden = Tarea.objects.filter(
                            proyecto=tarea.proyecto,
                            empleado=tarea.empleado,
                            estado=nuevo_estado
                        ).aggregate(Max('orden'))['orden__max']
                        nuevo_orden = 1 if max_orden is None else max_orden + 1

                    # Hacer espacio para la nueva posición
                    Tarea.objects.filter(
                        proyecto=tarea.proyecto,
                        empleado=tarea.empleado,
                        estado=nuevo_estado,
                        orden__gte=nuevo_orden
                    ).update(orden=F('orden') + 1)

                    tarea.estado = nuevo_estado
                    tarea.orden = nuevo_orden

                # Si solo cambia el orden en el mismo estado
                elif nuevo_orden and nuevo_orden != orden_anterior:
                    if nuevo_orden > orden_anterior:
                        # Mover hacia abajo
                        Tarea.objects.filter(
                            proyecto=tarea.proyecto,
                            empleado=tarea.empleado,
                            estado=estado_anterior,
                            orden__gt=orden_anterior,
                            orden__lte=nuevo_orden
                        ).update(orden=F('orden') - 1)
                    else:
                        # Mover hacia arriba
                        Tarea.objects.filter(
                            proyecto=tarea.proyecto,
                            empleado=tarea.empleado,
                            estado=estado_anterior,
                            orden__lt=orden_anterior,
                            orden__gte=nuevo_orden
                        ).update(orden=F('orden') + 1)

                    tarea.orden = nuevo_orden

                tarea.save()

                # Reordenar para asegurar secuencia consecutiva
                tareas = Tarea.objects.filter(
                    proyecto=tarea.proyecto,
                    empleado=tarea.empleado,
                    estado=tarea.estado
                ).order_by('orden')
                
                for index, t in enumerate(tareas, 1):
                    if t.orden != index:
                        t.orden = index
                        t.save(update_fields=['orden'])

                return Response({
                    'message': 'Tarea actualizada correctamente',
                    'tarea': {
                        'id': tarea.id,
                        'estado': tarea.estado,
                        'orden': tarea.orden
                    }
                })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class RegistroEmpleadoAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        serializer = RegistroEmpleadoSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                empleado = serializer.save()
                return Response(
                    serializer.to_representation(empleado),
                    status=status.HTTP_201_CREATED
                )
            except Exception as e:
                return Response(
                    {'error': f'Error al crear empleado: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


class ListarEmpleadosPorEncargadoAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, encargado_id):
        try:
            # Verificar que el encargado existe y es un encargado
            encargado = Usuario.objects.get(id=encargado_id, rol='encargado')
            
            # Obtener todos los empleados asociados a este encargado
            empleados = Usuario.objects.filter(
                encargado=encargado,
                rol='empleado'
            ).order_by('-created_at')  # Ordenados por fecha de creación, más recientes primero
            
            # Serializar los datos
            serializer = EmpleadosPorEncargadoSerializer(empleados, many=True)
            
            return Response({
                'encargado': {
                    'id': encargado.id,
                    'nombre': encargado.nombre,
                    'email': encargado.email
                },
                'total_empleados': empleados.count(),
                'empleados': serializer.data
            })
            
        except Usuario.DoesNotExist:
            return Response(
                {'error': 'Encargado no encontrado o no tiene el rol correcto'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

class ListarProyectosPorEncargadoAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, encargado_id):
        try:
            # Verificar que el encargado existe y tiene el rol correcto
            encargado = Usuario.objects.get(id=encargado_id, rol='encargado')
            
            # Obtener todos los proyectos donde este usuario es encargado
            proyectos = Proyecto.objects.filter(
                encargado=encargado
            ).order_by('-created_at')  # Ordenar por fecha de creación, más recientes primero
            
            # Serializar los datos
            serializer = ProyectosPorEncargadoSerializer(proyectos, many=True)
            
            return Response({
                'encargado': {
                    'id': encargado.id,
                    'nombre': encargado.nombre,
                    'email': encargado.email
                },
                'total_proyectos': proyectos.count(),
                'proyectos': serializer.data
            })
            
        except Usuario.DoesNotExist:
            return Response(
                {'error': 'Encargado no encontrado o no tiene el rol correcto'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ListarProyectosAsignadosEmpleadoAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, empleado_id):
        try:
            # Verificar que el empleado existe y tiene el rol correcto
            empleado = Usuario.objects.get(id=empleado_id, rol='empleado')
            
            # Obtener todos los proyectos donde el empleado está asignado
            proyectos = Proyecto.objects.filter(
                empleados=empleado
            ).order_by('-created_at')
            
            # Serializar los datos
            serializer = ProyectosAsignadosEmpleadoSerializer(proyectos, many=True)
            
            return Response({
                'empleado': {
                    'id': empleado.id,
                    'nombre': empleado.nombre,
                    'email': empleado.email
                },
                'total_proyectos': proyectos.count(),
                'proyectos': serializer.data
            })
            
        except Usuario.DoesNotExist:
            return Response(
                {'error': 'Empleado no encontrado o no tiene el rol correcto'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class ListarTareasEmpleadoAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, empleado_id):
        try:
            empleado = Usuario.objects.get(id=empleado_id, rol='empleado')
            
            # Usamos select_related para cargar los datos del proyecto eficientemente
            tareas = Tarea.objects.filter(
                empleado=empleado
            ).select_related(
                'empleado', 
                'proyecto', 
                'proyecto__encargado'  # Para cargar también los datos del encargado del proyecto
            ).order_by('created_at')
            
            # Usar el TareaSerializer que ya incluye la información del proyecto
            serializer = TareaSerializer(tareas, many=True)
            
            return Response(serializer.data)
            
        except Usuario.DoesNotExist:
            return Response(
                {'error': 'Empleado no encontrado o no tiene el rol correcto'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        


class ListarTareasProyectoAPIView(APIView):
   permission_classes = [IsAuthenticated]
   def get(self, request, proyecto_id):
        try:
            proyecto = Proyecto.objects.get(id=proyecto_id)
            
            tareas = Tarea.objects.filter(
                proyecto=proyecto
            ).select_related('empleado', 'proyecto').order_by('estado', 'orden')  # Ordenado por estado y orden
            
            serializer = TareasProyectoSerializer(tareas, many=True)
            
            return Response({
                'proyecto': {
                    'id': proyecto.id,
                    'nombre': proyecto.nombre,
                    'descripcion': proyecto.descripcion,
                    'estado': proyecto.estado,
                    'encargado': {
                        'id': proyecto.encargado.id,
                        'nombre': proyecto.encargado.nombre,
                        'email': proyecto.encargado.email,
                        'rol': proyecto.encargado.rol
                    }
                },
                'total_tareas': tareas.count(),
                'tareas': serializer.data
            })
            
        except Proyecto.DoesNotExist:
            return Response(
                {'error': 'Proyecto no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )



# views.py
class ListarTareasEmpleadosEncargadoAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, encargado_id):
        try:
            # Verificar que el encargado existe
            encargado = Usuario.objects.get(id=encargado_id, rol='encargado')
            
            # Obtener todos los empleados del encargado
            empleados = Usuario.objects.filter(encargado=encargado, rol='empleado')
            
            # Obtener todas las tareas de estos empleados
            tareas = Tarea.objects.filter(
                empleado__in=empleados
            ).select_related('empleado', 'proyecto').order_by('created_at')
            
            # Serializar las tareas directamente
            serializer = TareasEmpleadosEncargadoSerializer(tareas, many=True)
            
            return Response(serializer.data)
            
        except Usuario.DoesNotExist:
            return Response(
                {'error': 'Encargado no encontrado o no tiene el rol correcto'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ListarTareasUsuarioProyectoAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, empleado_id, proyecto_id):
        try:
            # Verificar que tanto el empleado como el proyecto existen
            empleado = Usuario.objects.get(id=empleado_id, rol='empleado')
            proyecto = Proyecto.objects.get(id=proyecto_id)
            
            # Verificar que el empleado está asignado al proyecto
            if not proyecto.empleados.filter(id=empleado_id).exists():
                return Response(
                    {'error': 'El empleado no está asignado a este proyecto'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Obtener las tareas
            tareas = Tarea.objects.filter(
                empleado=empleado,
                proyecto=proyecto
            ).select_related('empleado', 'proyecto').order_by('estado', 'orden')
            
            # Usar el TareaSerializer existente
            serializer = TareaSerializer(tareas, many=True)
            
            return Response(serializer.data)
            
        except Usuario.DoesNotExist:
            return Response(
                {'error': 'Empleado no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Proyecto.DoesNotExist:
            return Response(
                {'error': 'Proyecto no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )