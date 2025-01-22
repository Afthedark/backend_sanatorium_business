from django.db import models

# Create your models here.

from django.db import models

class Usuario(models.Model):
    ROLES = [
        ('administrador', 'Administrador'),
        ('encargado', 'Encargado'),
        ('empleado', 'Empleado'),
    ]

    nombre = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    rol = models.CharField(max_length=20, choices=ROLES)

    encargado = models.ForeignKey(
        'self',  # Relación con el mismo modelo
        on_delete=models.SET_NULL,  # Si se elimina el encargado, el campo queda null
        null=True,  # Permitir valores nulos
        blank=True,  # Permitir valores vacíos en formularios
        related_name='empleados',  # Para acceder desde el encargado a sus empleados
        limit_choices_to={'rol': 'encargado'}  # Solo permitir seleccionar encargados
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre

class Proyecto(models.Model):
    ESTADOS = [
        ('completado', 'Completado'),
        ('progreso', 'En Progreso'),
        ('pendiente', 'Pendiente'),
    ]

    nombre = models.CharField(max_length=150)
    descripcion = models.TextField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS)
    encargado = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='proyectos')
    empleados = models.ManyToManyField(Usuario, related_name='proyectos_asignados', limit_choices_to={'rol': 'empleado'})  # Relación directa con empleados
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre

class Permiso(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE)
    puede_ver = models.BooleanField(default=False)
    puede_editar = models.BooleanField(default=False)
    puede_eliminar = models.BooleanField(default=False)

class Tarea(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('progreso', 'En Progreso'),
        ('completada', 'Completada'),
    ]

    titulo = models.CharField(max_length=150)
    descripcion = models.TextField()
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='tareas')
    fecha = models.DateField()
    horas_invertidas = models.PositiveSmallIntegerField()
    empleado = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='tareas')
    estado = models.CharField(max_length=20, choices=ESTADOS)
    archivo = models.CharField(max_length=255, null=True, blank=True)
    orden = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.titulo
    

    
