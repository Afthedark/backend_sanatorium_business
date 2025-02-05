from rest_framework import serializers
from .models import Usuario, Proyecto, Permiso, Tarea
from django.db.models import Max
from django.db import transaction

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer #para autenticación JWT
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password



class CustomTokenObtainPairSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    default_error_messages = {
        'no_active_account': 'No existe un usuario con este email.',
        'invalid_password': 'Contraseña incorrecta.'
    }

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        try:
            # Buscar el usuario
            user = Usuario.objects.get(email=email)
            
            # Verificar la contraseña
            if not check_password(password, user.password):
                raise serializers.ValidationError(
                    self.error_messages['invalid_password']
                )

            # Generar tokens
            refresh = RefreshToken.for_user(user)

            data = {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'nombre': user.nombre,
                    'email': user.email,
                    'rol': user.rol,
                    'created_at': user.created_at,
                    'updated_at': user.updated_at,
                }
            }

            if user.rol == 'empleado' and user.encargado:
                data['user']['encargado'] = {
                    'id': user.encargado.id,
                    'nombre': user.encargado.nombre,
                    'email': user.encargado.email,
                    'rol': user.encargado.rol
                }

            return data

        except Usuario.DoesNotExist:
            raise serializers.ValidationError(
                self.error_messages['no_active_account']
            )


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = '__all__'

# Nuevo serializer para proyecto simplificado
class ProyectoSimplificadoSerializer(serializers.ModelSerializer):
    encargado = serializers.SerializerMethodField()
    
    class Meta:
        model = Proyecto
        fields = ['id', 'nombre', 'descripcion', 'estado', 'encargado']
    
    def get_encargado(self, obj):
        return {
            'id': obj.encargado.id,
            'nombre': obj.encargado.nombre,
            'email': obj.encargado.email,
            'rol': obj.encargado.rol
        }

class ProyectoSerializer(serializers.ModelSerializer):
    empleados = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Usuario.objects.filter(rol='empleado')
    )

    class Meta:
        model = Proyecto
        fields = '__all__'

class PermisoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permiso
        fields = '__all__'


# Serializer para tareas crear y actualizar
class TareaSerializer(serializers.ModelSerializer):
    empleado_info = serializers.SerializerMethodField(source='empleado', read_only=True)
    proyecto_info = ProyectoSimplificadoSerializer(source='proyecto', read_only=True)

    class Meta:
        model = Tarea
        fields = [
            'id',
            'titulo',
            'descripcion',
            'proyecto',
            'fecha',
            'horas_invertidas',
            'empleado',
            'estado',
            'orden',
            'archivo',
            'empleado_info',
            'proyecto_info',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['estado', 'orden']

    def get_empleado_info(self, obj):
        return {
            'id': obj.empleado.id,
            'nombre': obj.empleado.nombre,
            'email': obj.empleado.email
        }

    def create(self, validated_data):
        validated_data['estado'] = 'pendiente'
        return super().create(validated_data)

    def to_representation(self, instance):
        # Personalizar la respuesta
        data = super().to_representation(instance)
        # Reemplazar la información básica con la información detallada
        data['empleado'] = data.pop('empleado_info')
        data['proyecto'] = data.pop('proyecto_info')
        return data
        
    
    
class ActualizarTareaSerializer(serializers.Serializer):
    """
    Serializador para actualizar el estado y orden de una tarea.
    """
    id = serializers.IntegerField(
        required=True,
        help_text="ID de la tarea a actualizar"
    )
    nuevo_estado = serializers.ChoiceField(
        choices=[
            ('pendiente', 'Pendiente'),
            ('progreso', 'En Progreso'),
            ('completada', 'Completada')
        ],
        required=True,
        help_text="Nuevo estado de la tarea"
    )
    nuevo_orden = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text="Nueva posición en la columna (opcional)"
    )

    def validate_id(self, value):
        try:
            tarea = Tarea.objects.select_related('proyecto', 'empleado').get(id=value)
            self.context['tarea'] = tarea
            return value
        except Tarea.DoesNotExist:
            raise serializers.ValidationError("Tarea no encontrada")

    def validate(self, data):
        tarea = self.context.get('tarea')
        
        # Quitamos la validación del usuario temporalmente
        # Si después quieres implementar autenticación, podremos añadirla aquí

        # Si se proporciona nuevo_orden, validar que sea válido
        if 'nuevo_orden' in data:
            total_tareas = Tarea.objects.filter(
                proyecto=tarea.proyecto,
                estado=data['nuevo_estado']
            ).count()
            
            if data['nuevo_orden'] > total_tareas + 1:
                data['nuevo_orden'] = total_tareas + 1

        return data
    

class RegistroEmpleadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'nombre', 'email', 'password', 'rol', 'encargado', 'created_at', 'updated_at']
        extra_kwargs = {
            'password': {'write_only': True},
            'rol': {'read_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
            'encargado': {'required': False}  # Hacemos el encargado opcional
        }

    def validate_encargado(self, value):
        if value and value.rol != 'encargado':
            raise serializers.ValidationError("El usuario seleccionado debe tener el rol de encargado")
        return value

    def create(self, validated_data):
        validated_data['rol'] = 'empleado'
        return Usuario.objects.create(**validated_data)

    def to_representation(self, instance):
        data = {
            'id': instance.id,
            'nombre': instance.nombre,
            'email': instance.email,
            'rol': instance.rol,
            'created_at': instance.created_at,
            'updated_at': instance.updated_at
        }
        
        if instance.encargado:
            data['encargado'] = {
                'id': instance.encargado.id,
                'nombre': instance.encargado.nombre,
                'email': instance.encargado.email,
                'rol': instance.encargado.rol
            }
        
        return data
    

class EmpleadosPorEncargadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'nombre', 'email', 'rol', 'created_at', 'updated_at']


class ProyectosPorEncargadoSerializer(serializers.ModelSerializer):
    empleados = UsuarioSerializer(many=True, read_only=True)  # Para mostrar detalles de los empleados
    
    class Meta:
        model = Proyecto
        fields = [
            'id', 
            'nombre', 
            'descripcion', 
            'fecha_inicio',
            'fecha_fin',
            'estado',
            'empleados',
            'created_at',
            'updated_at'
        ]



class ProyectosAsignadosEmpleadoSerializer(serializers.ModelSerializer):
    encargado = serializers.SerializerMethodField()
    
    class Meta:
        model = Proyecto
        fields = [
            'id', 
            'nombre', 
            'descripcion', 
            'fecha_inicio',
            'fecha_fin',
            'estado',
            'encargado',
            'created_at',
            'updated_at'
        ]
    
    def get_encargado(self, obj):
        return {
            'id': obj.encargado.id,
            'nombre': obj.encargado.nombre,
            'email': obj.encargado.email,
            'rol': obj.encargado.rol
        }
    

class TareasEmpleadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tarea
        fields = [
            'id',
            'titulo',
            'descripcion',
            'fecha',
            'horas_invertidas',
            'estado',
            'orden',
            'archivo',
            'created_at',
            'updated_at'
        ]



class TareasProyectoSerializer(serializers.ModelSerializer):
    empleado = serializers.SerializerMethodField()
    proyecto = ProyectoSimplificadoSerializer(read_only=True)
    
    class Meta:
        model = Tarea
        fields = [
            'id',
            'titulo',
            'descripcion',
            'fecha',
            'horas_invertidas',
            'estado',
            'orden',  # Añadido el campo orden
            'archivo',
            'empleado',
            'proyecto',
            'created_at',
            'updated_at'
        ]
    
    def get_empleado(self, obj):
        return {
            'id': obj.empleado.id,
            'nombre': obj.empleado.nombre,
            'email': obj.empleado.email
        }
    

class TareasEmpleadosEncargadoSerializer(serializers.ModelSerializer):
    empleado = serializers.SerializerMethodField()
    proyecto = ProyectoSimplificadoSerializer(read_only=True)
    
    class Meta:
        model = Tarea
        fields = [
            'id',
            'titulo',
            'descripcion',
            'fecha',
            'horas_invertidas',
            'estado',
            'orden',
            'archivo',
            'empleado',
            'proyecto',
            'created_at',
            'updated_at'
        ]
    
    def get_empleado(self, obj):
        return {
            'id': obj.empleado.id,
            'nombre': obj.empleado.nombre,
            'email': obj.empleado.email
        }