from rest_framework import status
from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from apps.lottery.models import Lottery, LotteryResult, Bet
from apps.lottery.serializers.lottery_serializer import LotteryResultSerializer, BetSerializer
from apps.lottery.permissions.permissions import IsOwner, ResultsPermission
from apps.lottery.services.api_service import LotteryAPIService


class LotteryResultViewSet(GenericViewSet):
    serializer_class = LotteryResultSerializer
    permission_classes = [IsAuthenticated, ResultsPermission]

    def get_queryset(self):
        return LotteryResult.objects.all().order_by('-fecha')

    def list(self, request):
        """Listar todos los resultados"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """Obtener un resultado específico"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def sync_results(self, request):
        """Sincronizar resultados con la API externa"""
        results = LotteryAPIService.get_lottery_results()
        saved_results = []

        for result in results:
            try:
                lottery = Lottery.objects.get(name=result['nombre_loteria'])
                lottery_result, created = LotteryResult.objects.update_or_create(
                    lottery=lottery,
                    fecha=result['fecha'],
                    defaults={
                        'numero': result['numero'],
                        'numero_serie': result['numero_serie'],
                        'premios_secos': result['premios_secos']
                    }
                )
                saved_results.append(lottery_result)
            except Lottery.DoesNotExist:
                continue

        serializer = self.get_serializer(saved_results, many=True)
        return Response(serializer.data)


class BetViewSet(GenericViewSet):
    serializer_class = BetSerializer
    permission_classes = [IsAuthenticated, IsOwner]

    def get_queryset(self):
        return Bet.objects.filter(user=self.request.user).order_by('-created_at')

    def list(self, request):
        """Listar apuestas del usuario"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        """Crear nueva apuesta"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                user=request.user,
                status='PENDING'
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        """Ver detalle de una apuesta"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Ver historial de apuestas con filtros"""
        queryset = self.get_queryset()

        # Aplicar filtros
        status_param = request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        lottery_id = request.query_params.get('lottery')
        if lottery_id:
            queryset = queryset.filter(lottery_id=lottery_id)

        start_date = request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(draw_date__gte=start_date)

        end_date = request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(draw_date__lte=end_date)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
