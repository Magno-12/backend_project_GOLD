from django.core.exceptions import ValidationError
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, AllowAny

from apps.users.models.user import User
from apps.users.models.password_reset import PasswordResetCode
from apps.users.serializers.user_serializer import UserSerializer
from apps.users.serializers.profile_serializer import UserProfileSerializer
from apps.users.serializers.password_serializers import (
    RequestPasswordResetSerializer,
    VerifyPasswordResetCodeSerializer,
    ResetPasswordSerializer
)
from apps.users.utils.validators import validate_pin
import random
import string


class UserViewSet(viewsets.GenericViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action in ['create', 'request_reset_code', 'verify_reset_code', 'reset_password']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def create(self, request):
        """Crear un nuevo usuario"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Usamos set_password para encriptar el PIN antes de guardarlo
            user.set_password(request.data['pin'])
            user.save()
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def destroy(self, request, pk=None):
        """Eliminar usuario (solo puede eliminar su propia cuenta)"""
        try:
            if str(request.user.id) != pk:
                return Response(
                    {"error": "Solo puedes eliminar tu propia cuenta"},
                    status=status.HTTP_403_FORBIDDEN
                )

            user = self.get_queryset().get(pk=pk)
            user.delete()

            return Response(status=status.HTTP_204_NO_CONTENT)
        except User.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['get'])
    def profile(self, request, pk=None):
        """
        Obtener perfil completo del usuario con toda su información.
        Solo permite ver el perfil propio.
        """
        if str(request.user.id) != pk:
            return Response(
                {'error': 'No tienes permiso para ver este perfil'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = UserProfileSerializer(request.user)
        return Response({
            'user_info': {
                'name': f"{request.user.first_name} {request.user.last_name}",
                'email': request.user.email,
                'phone': request.user.phone_number
            },
            'menu_items': [
                {
                    'title': 'Mis datos',
                    'icon': 'user',
                    'data': {
                        'identification': request.user.identification,
                        'birth_date': request.user.birth_date,
                        'document_front': bool(request.user.document_front),
                        'document_back': bool(request.user.document_back)
                    }
                },
                {
                    'title': 'Boletos registrados',
                    'icon': 'ticket',
                    'data': serializer.data['recent_bets']
                },
                {
                    'title': 'Mis transacciones',
                    'icon': 'credit-card',
                    'data': serializer.data['recent_transactions']
                },
                {
                    'title': 'Mis premios',
                    'icon': 'gift',
                    'data': serializer.data['recent_prizes']
                },
                {
                    'title': 'Ayuda',
                    'icon': 'help-circle',
                    'url': '/help'
                }
            ],
            'balance': serializer.data['balance']
        })

    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        """
        Cambiar PIN del usuario. 
        Hay dos formas:
        1. Si el usuario está autenticado, puede cambiar su PIN con el PIN actual.
        2. Si el usuario está utilizando un código de recuperación (enviado por email).
        """
        # Verificar si es un cambio de PIN con código de recuperación
        if 'code' in request.data and 'email' in request.data:
            serializer = ResetPasswordSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            user = serializer.validated_data['user']
            reset_code = serializer.validated_data['reset_code']
            new_pin = serializer.validated_data['new_pin']
            
            with transaction.atomic():
                # Cambiar contraseña - Asegurando el uso de set_password que encripta automáticamente
                user.set_password(new_pin)
                user.save()
                
                # Marcar código como usado
                reset_code.is_used = True
                reset_code.save()
                
                # Enviar correo de confirmación
                subject = 'Contraseña actualizada - GOLD Lottery'
                message = f"""
                Hola {user.first_name},
                
                Tu contraseña ha sido actualizada exitosamente.
                
                Si no realizaste este cambio, por favor contacta a nuestro equipo de soporte inmediatamente.
                
                Atentamente,
                Equipo de GOLD Lottery
                """
                
                from_email = settings.DEFAULT_FROM_EMAIL
                recipient_list = [user.email]
                
                send_mail(
                    subject,
                    message,
                    from_email,
                    recipient_list,
                    fail_silently=False,
                )
            
            return Response({'message': 'Contraseña actualizada exitosamente'})
        
        # Cambio de PIN normal (con PIN actual)
        if str(request.user.id) != pk:
            return Response(
                {'error': 'No tienes permiso para cambiar el PIN de otro usuario'},
                status=status.HTTP_403_FORBIDDEN
            )

        old_pin = request.data.get('old_pin')
        new_pin = request.data.get('new_pin')

        # check_password verifica correctamente contra el hash almacenado
        if not request.user.check_password(old_pin):
            return Response(
                {'error': 'PIN actual incorrecto'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            validate_pin(new_pin)
            # Usamos set_password para encriptar el PIN antes de guardarlo
            request.user.set_password(new_pin)
            request.user.save()
            
            # Enviar correo de confirmación
            subject = 'Cambio de PIN exitoso - GOLD Lottery'
            message = f'''
            Hola {request.user.first_name},
            
            Tu PIN ha sido actualizado exitosamente.
            
            Si no realizaste este cambio, por favor contacta a nuestro equipo de soporte inmediatamente.
            
            Atentamente,
            Equipo de GOLD Lottery
            '''
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [request.user.email]
            
            send_mail(
                subject,
                message,
                from_email,
                recipient_list,
                fail_silently=False,
            )
            
            return Response({'message': 'PIN actualizado correctamente. Se ha enviado un correo de confirmación.'})
            
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def request_reset_code(self, request):
        """
        Solicitar un código de recuperación de contraseña.
        Se envía un correo electrónico con el código.
        """
        serializer = RequestPasswordResetSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
            
            # Invalidar códigos anteriores
            PasswordResetCode.objects.filter(user=user, is_used=False).update(is_used=True)
            
            # Crear nuevo código
            reset_code = PasswordResetCode.objects.create(user=user)
            
            # Enviar correo
            subject = 'Código de recuperación de contraseña - GOLD Lottery'
            message = f"""
            Hola {user.first_name},
            
            Has solicitado un código para cambiar tu contraseña.
            
            Tu código de verificación es: {reset_code.code}
            
            Este código expirará en 5 minutos.
            
            Si no solicitaste este cambio, ignora este correo.
            
            Atentamente,
            Equipo de GOLD Lottery
            """
            
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [user.email]
            
            send_mail(
                subject,
                message,
                from_email,
                recipient_list,
                fail_silently=False,
            )
            
            return Response({
                'message': 'Se ha enviado un código de verificación a tu correo electrónico.',
                'expires_at': reset_code.expires_at
            })
            
        except User.DoesNotExist:
            # Por seguridad, no informamos si el correo existe o no
            return Response({
                'message': 'Si el correo electrónico está registrado, recibirás un código de verificación.'
            })
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def verify_reset_code(self, request):
        """Verificar el código de recuperación de contraseña"""
        serializer = VerifyPasswordResetCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        reset_code = serializer.validated_data['reset_code']
        
        return Response({
            'message': 'Código válido',
            'expires_at': reset_code.expires_at
        })

    @action(detail=True, methods=['patch'])
    def update_profile(self, request, pk=None):
        """Actualizar parcialmente el perfil del usuario. Solo permite actualizar el perfil propio."""
        if str(request.user.id) != pk:
            return Response(
                {'error': 'No tienes permiso para editar este perfil'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Campos permitidos para actualizar
            allowed_fields = [
                'first_name',
                'last_name',
                'email',
                'phone_number',
                'document_front',
                'document_back'
            ]

            # Filtrar solo los campos permitidos que vienen en la request
            update_data = {
                key: value for key, value in request.data.items() 
                if key in allowed_fields
            }

            # Actualizar usuario
            for key, value in update_data.items():
                setattr(request.user, key, value)

            request.user.save()

            return Response({
                'message': 'Perfil actualizado correctamente',
                'user': UserProfileSerializer(request.user).data
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
