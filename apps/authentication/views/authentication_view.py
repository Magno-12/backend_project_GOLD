from django.contrib.auth.hashers import check_password
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.users.models import User
from apps.authentication.serializers.authentication_serializer import (
    AuthenticationSerializer,
    LogoutSerializer,
    UserAuthResponseSerializer
)


class AuthenticationViewSet(GenericViewSet):
    """
    ViewSet para manejar la autenticación de usuarios en el sistema de loterías.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'login':
            return AuthenticationSerializer
        return LogoutSerializer

    @swagger_auto_schema(
        operation_description="Inicia sesión de usuario con número de teléfono y PIN",
        request_body=AuthenticationSerializer,
        responses={
            200: openapi.Response(
                description="Login exitoso",
                schema=UserAuthResponseSerializer
            ),
            401: "Credenciales inválidas"
        }
    )
    @action(detail=False, methods=['post'])
    def login(self, request):
        """
        Maneja el inicio de sesión de usuarios y proporciona tokens JWT.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_data = serializer.validated_data

        try:
            user = User.objects.get(phone_number=user_data['phone_number'])
        except User.DoesNotExist:
            raise AuthenticationFailed(
                "El usuario con este número de teléfono no existe"
            )

        if not check_password(user_data['pin'], user.password):
            raise AuthenticationFailed("PIN incorrecto")

        if not user.is_active:
            raise AuthenticationFailed("Esta cuenta ha sido desactivada")

        # Generar tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            "user": UserAuthResponseSerializer(user).data
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Cierra la sesión del usuario",
        request_body=LogoutSerializer,
        responses={
            200: "Sesión cerrada exitosamente",
            400: "Token inválido"
        }
    )
    @action(detail=False, methods=['post'])
    def logout(self, request):
        """
        Cierra la sesión del usuario y añade el token de refresco a la lista negra.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh_token = serializer.validated_data['refresh_token']

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response(
                {"error": "Token inválido o expirado"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {"message": "Sesión cerrada exitosamente"},
            status=status.HTTP_200_OK
        )
