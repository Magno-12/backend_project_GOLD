from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    Permiso personalizado para permitir que los usuarios
    solo puedan ver sus propias apuestas.
    """

    def has_object_permission(self, request, view, obj):
        # Solo permitir acceso si la apuesta pertenece al usuario
        return obj.user == request.user

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permiso que permite solo a los administradores hacer modificaciones,
    mientras que usuarios autenticados pueden ver.
    """

    def has_permission(self, request, view):
        # Permitir GET, HEAD u OPTIONS a usuarios autenticados
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated

        # Permitir modificaciones solo a admin
        return request.user and request.user.is_staff


class CustomLotteryPermission(permissions.BasePermission):
    """
    Permiso personalizado para diferentes acciones en la API de loterías.
    - Administradores tienen acceso completo
    - Usuarios autenticados pueden ver resultados y crear apuestas
    - Solo el dueño de una apuesta puede verla
    """

    def has_permission(self, request, view):
        # Verificar si el usuario está autenticado
        if not request.user or not request.user.is_authenticated:
            return False

        # Administradores tienen acceso completo
        if request.user.is_staff:
            return True

        # Para vistas de resultados (LotteryResultViewSet)
        if view.__class__.__name__ == 'LotteryResultViewSet':
            # Solo permitir lectura de resultados
            return request.method in permissions.SAFE_METHODS

        # Para vistas de apuestas (BetViewSet)
        if view.__class__.__name__ == 'BetViewSet':
            # Permitir crear apuestas y ver las propias
            return True

        return False

    def has_object_permission(self, request, view, obj):
        # Administradores tienen acceso completo
        if request.user.is_staff:
            return True

        # Para resultados de lotería, permitir lectura a usuarios autenticados
        if isinstance(obj, view.get_serializer().Meta.model):
            return request.method in permissions.SAFE_METHODS

        # Para apuestas, solo permitir acceso al dueño
        if hasattr(obj, 'user'):
            return obj.user == request.user

        return False


class ResultsPermission(permissions.BasePermission):
    """
    Permiso específico para los resultados de lotería:
    - Administradores pueden sincronizar resultados
    - Usuarios autenticados pueden ver resultados
    """

    def has_permission(self, request, view):
        # Debe estar autenticado
        if not request.user or not request.user.is_authenticated:
            return False

        # Para sincronización de resultados, solo admin
        if view.action == 'sync_results':
            return request.user.is_staff

        # Para ver resultados, cualquier usuario autenticado
        return request.method in permissions.SAFE_METHODS
