from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction
from django.db.models import F
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
)

from django.db.models import Max
import logging

logger = logging.getLogger(__name__)

# Vistas para CRUD
class UsuarioViewSet(ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer

class ProyectoViewSet(ModelViewSet):
    queryset = Proyecto.objects.all()
    serializer_class = ProyectoSerializer

class PermisoViewSet(ModelViewSet):
    queryset = Permiso.objects.all()
    serializer_class = PermisoSerializer



class TareaViewSet(ModelViewSet):
    queryset = Tarea.objects.all()
    serializer_class = TareaSerializer

    def perform_create(self, serializer):
        """
        Al crear una tarea:
        - Se asigna estado 'pendiente'
        - Se calcula el siguiente orden para el empleado específico
        """
        with transaction.atomic():
            proyecto = serializer.validated_data.get('proyecto')
            empleado = serializer.validated_data.get('empleado')
            
            # Obtener el último orden para este empleado específico en este proyecto
            max_orden = Tarea.objects.filter(
                proyecto=proyecto,
                empleado=empleado,  # Filtrar por empleado específico
                estado='pendiente'
            ).aggregate(Max('orden'))['orden__max']
            
            # Si no hay tareas previas para este empleado, empezar desde 1
            nuevo_orden = 1 if max_orden is None else max_orden + 1
            
            # Crear la tarea con estado pendiente y el nuevo orden
            serializer.save(estado='pendiente', orden=nuevo_orden)

    

# API personalizada para actualizar tareas
@method_decorator(csrf_exempt, name='dispatch')
class ActualizarTareaEmpleadoAPIView(APIView):
    permission_classes = [AllowAny]  # Cambia esto según tus necesidades de autenticación

    def post(self, request, *args, **kwargs):
        serializer = ActualizarTareaSerializer(
            data=request.data,
            context={'request': request}
        )

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

                # Si cambia de estado
                if estado_anterior != nuevo_estado:
                    # Reordenar tareas en la columna anterior
                    Tarea.objects.filter(
                        proyecto=tarea.proyecto,
                        estado=estado_anterior,
                        orden__gt=orden_anterior
                    ).update(orden=F('orden') - 1)

                    # Calcular nuevo orden en la nueva columna
                    if nuevo_orden is None:
                        nuevo_orden = Tarea.objects.filter(
                            proyecto=tarea.proyecto,
                            estado=nuevo_estado
                        ).count() + 1
                    
                    # Hacer espacio en la nueva posición
                    Tarea.objects.filter(
                        proyecto=tarea.proyecto,
                        estado=nuevo_estado,
                        orden__gte=nuevo_orden
                    ).update(orden=F('orden') + 1)

                # Si solo cambia de posición en la misma columna
                elif nuevo_orden and nuevo_orden != orden_anterior:
                    if nuevo_orden > orden_anterior:
                        # Mover hacia abajo
                        Tarea.objects.filter(
                            proyecto=tarea.proyecto,
                            estado=estado_anterior,
                            orden__gt=orden_anterior,
                            orden__lte=nuevo_orden
                        ).update(orden=F('orden') - 1)
                    else:
                        # Mover hacia arriba
                        Tarea.objects.filter(
                            proyecto=tarea.proyecto,
                            estado=estado_anterior,
                            orden__lt=orden_anterior,
                            orden__gte=nuevo_orden
                        ).update(orden=F('orden') + 1)

                # Actualizar la tarea
                tarea.estado = nuevo_estado
                tarea.orden = nuevo_orden
                tarea.save()

                # Reordenar todas las tareas de la columna para asegurar orden consecutivo
                tareas_columna = list(Tarea.objects.filter(
                    proyecto=tarea.proyecto,
                    estado=nuevo_estado
                ).order_by('orden'))

                for idx, t in enumerate(tareas_columna, 1):
                    t.orden = idx
                
                Tarea.objects.bulk_update(tareas_columna, ['orden'])

                return Response({
                    'message': 'Tarea actualizada exitosamente',
                    'tarea': {
                        'id': tarea.id,
                        'estado': tarea.estado,
                        'orden': tarea.orden,
                        'titulo': tarea.titulo
                    },
                    'total_tareas_columna': len(tareas_columna)
                })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get(self, request, *args, **kwargs):
        """
        Endpoint de prueba para verificar que la API está funcionando
        """
        return Response({
            'message': 'API de actualización de tareas está activa',
            'estados_disponibles': [estado[0] for estado in Tarea.ESTADOS]
        })



class RegistroEmpleadoAPIView(APIView):
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
    def get(self, request, empleado_id):
        try:
            # Verificar que el empleado existe
            empleado = Usuario.objects.get(id=empleado_id, rol='empleado')
            
            # Obtener todas las tareas del empleado
            tareas = Tarea.objects.filter(
                empleado=empleado
            ).order_by('proyecto', 'estado', 'orden')
            
            serializer = TareasEmpleadoSerializer(tareas, many=True)
            
            # Agrupar tareas por proyecto
            tareas_por_proyecto = {}
            
            for tarea in tareas:
                proyecto_id = tarea.proyecto.id
                if proyecto_id not in tareas_por_proyecto:
                    tareas_por_proyecto[proyecto_id] = {
                        'proyecto': {
                            'id': tarea.proyecto.id,
                            'nombre': tarea.proyecto.nombre,
                        },
                        'tareas': {
                            'pendiente': [],
                            'progreso': [],
                            'completada': []
                        }
                    }
                
                # Serializar la tarea
                tarea_data = TareasEmpleadoSerializer(tarea).data
                tareas_por_proyecto[proyecto_id]['tareas'][tarea.estado].append(tarea_data)
            
            return Response({
                'empleado': {
                    'id': empleado.id,
                    'nombre': empleado.nombre,
                    'email': empleado.email
                },
                'total_tareas': tareas.count(),
                'proyectos': list(tareas_por_proyecto.values())
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
        


class ListarTareasProyectoAPIView(APIView):
    def get(self, request, proyecto_id):
        try:
            proyecto = Proyecto.objects.get(id=proyecto_id)
            
            tareas = Tarea.objects.filter(
                proyecto=proyecto
            ).order_by('-created_at')
            
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
