from django.core.exceptions import ValidationError
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, AllowAny

from apps.users.models.user import User
from apps.users.serializers.user_serializer import UserSerializer
from apps.users.serializers.profile_serializer import UserProfileSerializer
from apps.users.utils.validators import validate_pin


class UserViewSet(viewsets.GenericViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def create(self, request):
        """Crear un nuevo usuario"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
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
        """Cambiar PIN del usuario. Solo permite cambiar el PIN propio."""
        if str(request.user.id) != pk:
            return Response(
                {'error': 'No tienes permiso para cambiar el PIN de otro usuario'},
                status=status.HTTP_403_FORBIDDEN
            )

        old_pin = request.data.get('old_pin')
        new_pin = request.data.get('new_pin')

        if not request.user.check_password(old_pin):
            return Response(
                {'error': 'PIN actual incorrecto'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            validate_pin(new_pin)
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
