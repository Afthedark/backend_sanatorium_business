# Para PDF
from datetime import date
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

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
    TareasEmpleadosEncargadoSerializer,
    CustomTokenObtainPairSerializer,
)

from django.db.models import Max
import logging
from drf_spectacular.utils import extend_schema, OpenApiParameter

#JWT
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

#JWT
# Añade las nuevas vistas de autenticación
class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            return Response(serializer.validated_data)
        except serializer.ValidationError as e:
            return Response(
                {'error': e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
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
#JWT


logger = logging.getLogger(__name__)

# Vistas para CRUD
class UsuarioViewSet(ModelViewSet):
    permission_classes = [AllowAny] #Unlock temporal api usuarios
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
    #permission_classes = [IsAuthenticated]
    permission_classes = [AllowAny]
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
    #permission_classes = [IsAuthenticated]
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
    #permission_classes = [IsAuthenticated]
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
    #permission_classes = [IsAuthenticated]
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
    #permission_classes = [IsAuthenticated]
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
   #permission_classes = [IsAuthenticated]
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
    #permission_classes = [IsAuthenticated]
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
    #permission_classes = [IsAuthenticated]
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
        




#REPORTES PDF 
class GenerateTasksReportBaseAPIView(APIView):
    """
    Clase base para generar reportes PDF de tareas.
    """
    def generate_pdf(self, proyecto, tareas, filename_prefix):
        # Crear una respuesta HTTP con tipo de contenido PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename_prefix}_{proyecto.id}.pdf"'

        # Crear un objeto PDF
        p = canvas.Canvas(response, pagesize=letter)
        width, height = letter

        # Configurar estilos y agregar contenido al PDF
        p.setFont("Helvetica-Bold", 16)
        p.drawString(inch, height - inch, f"Informe de Tareas del Proyecto: {proyecto.nombre}")

        p.setFont("Helvetica", 12)
        p.drawString(inch, height - 1.5 * inch, f"Descripción: {proyecto.descripcion}")
        p.drawString(inch, height - 2 * inch, f"Fecha de Inicio: {proyecto.fecha_inicio}")
        p.drawString(inch, height - 2.5 * inch, f"Fecha de Fin: {proyecto.fecha_fin or 'No especificada'}")
        p.drawString(inch, height - 3 * inch, f"Estado: {proyecto.estado}")
        p.drawString(inch, height - 3.5 * inch, f"Encargado: {proyecto.encargado.nombre}")

        # Listar tareas del proyecto
        if not tareas.exists():
            p.setFont("Helvetica-Bold", 14)
            p.drawString(inch, height - 4 * inch, "No se encontraron tareas.")
        else:
            p.setFont("Helvetica-Bold", 14)
            p.drawString(inch, height - 4 * inch, "Tareas:")
            task_height = height - 4.5 * inch
            for task in tareas:
                p.setFont("Helvetica", 12)
                p.drawString(inch, task_height, f"Empleado: {task.empleado.nombre}")
                p.drawString(inch, task_height - 0.25 * inch, f"Título: {task.titulo}")
                p.drawString(inch, task_height - 0.5 * inch, f"Descripción: {task.descripcion}")
                p.drawString(inch, task_height - 0.75 * inch, f"Proyecto: {task.proyecto.nombre}")
                p.drawString(inch, task_height - 1 * inch, f"Fecha: {task.fecha}")
                p.drawString(inch, task_height - 1.25 * inch, f"Horas dedicadas: {task.horas_invertidas}")
                p.drawString(inch, task_height - 1.5 * inch, f"Estado: {task.estado}")
                task_height -= 1.75 * inch

                # Añadir una nueva página si se llega al final de la página actual
                if task_height < 1 * inch:
                    p.showPage()
                    task_height = height - 0.5 * inch

        # Finalizar el PDF
        p.showPage()
        p.save()
        return response


class GenerateTasksReportAdminAPIView(GenerateTasksReportBaseAPIView):
    """
    Genera un reporte PDF de tareas para administradores.
    Los administradores pueden ver cualquier proyecto y empleado.
    """
    def get(self, request):
        # Obtener parámetros de filtro
        proyecto_id = request.query_params.get('proyecto_id')
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')
        estado_proyecto = request.query_params.get('estado')

        # Validar que se haya proporcionado un proyecto_id
        if not proyecto_id:
            return Response(
                {'error': 'Debe proporcionar un proyecto_id'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Convertir fechas a objetos date
        try:
            fecha_inicio = date.fromisoformat(fecha_inicio) if fecha_inicio else None
            fecha_fin = date.fromisoformat(fecha_fin) if fecha_fin else None
        except ValueError:
            return Response(
                {'error': 'Formato de fecha incorrecto. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Filtrar el proyecto
        proyecto = get_object_or_404(Proyecto, id=proyecto_id)

        # Filtrar tareas según los parámetros
        tareas = Tarea.objects.filter(
            proyecto=proyecto,
            fecha__range=(fecha_inicio, fecha_fin) if fecha_inicio and fecha_fin else Q(),
            proyecto__estado=estado_proyecto if estado_proyecto else Q()
        ).select_related('empleado', 'proyecto')

        # Generar el PDF
        return self.generate_pdf(proyecto, tareas, "reporte_tareas_admin")


class GenerateTasksReportEncargadoAPIView(GenerateTasksReportBaseAPIView):
    """
    Genera un reporte PDF de tareas para encargados.
    Los encargados solo pueden ver sus empleados y proyectos asignados.
    """
    def get(self, request):
        # Obtener parámetros de filtro
        proyecto_id = request.query_params.get('proyecto_id')
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')
        estado_proyecto = request.query_params.get('estado')

        # Validar que se haya proporcionado un proyecto_id
        if not proyecto_id:
            return Response(
                {'error': 'Debe proporcionar un proyecto_id'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Convertir fechas a objetos date
        try:
            fecha_inicio = date.fromisoformat(fecha_inicio) if fecha_inicio else None
            fecha_fin = date.fromisoformat(fecha_fin) if fecha_fin else None
        except ValueError:
            return Response(
                {'error': 'Formato de fecha incorrecto. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Filtrar el proyecto
        proyecto = get_object_or_404(Proyecto, id=proyecto_id)

        # Verificar que el usuario sea el encargado del proyecto o que esté asignado al proyecto
        if proyecto.encargado != request.user and not proyecto.empleados.filter(id=request.user.id).exists():
            return Response(
                {'error': 'No tiene permiso para ver este proyecto'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Filtrar tareas según los parámetros
        tareas = Tarea.objects.filter(
            proyecto=proyecto,
            fecha__range=(fecha_inicio, fecha_fin) if fecha_inicio and fecha_fin else Q(),
            proyecto__estado=estado_proyecto if estado_proyecto else Q()
        ).select_related('empleado', 'proyecto')

        # Generar el PDF
        return self.generate_pdf(proyecto, tareas, "reporte_tareas_encargado")
