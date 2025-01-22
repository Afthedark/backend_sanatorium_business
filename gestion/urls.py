from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UsuarioViewSet, 
    ProyectoViewSet, 
    PermisoViewSet, 
    TareaViewSet,
    ActualizarTareaEmpleadoAPIView,
    RegistroEmpleadoAPIView,
    ListarEmpleadosPorEncargadoAPIView,
    ListarProyectosPorEncargadoAPIView,
    ListarProyectosAsignadosEmpleadoAPIView,
    ListarTareasEmpleadoAPIView,
    ListarTareasProyectoAPIView,
    ListarTareasEmpleadosEncargadoAPIView,
    ListarTareasUsuarioProyectoAPIView,
    CustomTokenObtainPairView,
)
from rest_framework_simplejwt.views import TokenRefreshView




router = DefaultRouter()
router.register('usuarios', UsuarioViewSet)
router.register('proyectos', ProyectoViewSet)
router.register('permisos', PermisoViewSet)
router.register('tareas', TareaViewSet)

# Importante: separar las URLs del router y las personalizadas
custom_urls = [
    path('tareas/actualizar/', ActualizarTareaEmpleadoAPIView.as_view(), name='actualizar-tarea'),
    path('registro-empleado/', RegistroEmpleadoAPIView.as_view(), name='registro-empleado'),
    path('empleados-por-encargado/<int:encargado_id>/', 
         ListarEmpleadosPorEncargadoAPIView.as_view(), 
         name='empleados-por-encargado'),
    path('proyectos-por-encargado/<int:encargado_id>/', 
         ListarProyectosPorEncargadoAPIView.as_view(), 
         name='proyectos-por-encargado'),
    path('proyectos-asignados-empleado/<int:empleado_id>/', 
         ListarProyectosAsignadosEmpleadoAPIView.as_view(), 
         name='proyectos-asignados-empleado'),
    path('tareas-empleado/<int:empleado_id>/', 
         ListarTareasEmpleadoAPIView.as_view(), 
         name='tareas-empleado'),
    path('tareas-proyecto/<int:proyecto_id>/', 
         ListarTareasProyectoAPIView.as_view(), 
         name='tareas-proyecto'),
    path('tareas-empleados-encargado/<int:encargado_id>/', 
         ListarTareasEmpleadosEncargadoAPIView.as_view(), 
         name='tareas-empleados-encargado'),
    path('tareas-usuario-proyecto/<int:empleado_id>/<int:proyecto_id>/', 
     ListarTareasUsuarioProyectoAPIView.as_view(), 
     name='tareas-usuario-proyecto'),


    path('auth/login/', CustomTokenObtainPairView.as_view()),
    path('auth/refresh/', TokenRefreshView.as_view()),

]

urlpatterns = custom_urls + [path('', include(router.urls))]