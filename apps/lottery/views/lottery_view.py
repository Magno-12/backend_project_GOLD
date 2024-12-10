from rest_framework import status
from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
from decimal import Decimal

from apps.lottery.models import Lottery, LotteryResult, Bet
from apps.lottery.serializers.lottery_serializer import LotteryResultSerializer, BetSerializer
from apps.lottery.permissions.permissions import IsOwner, ResultsPermission
from apps.lottery.services.api_service import LotteryAPIService
from apps.lottery.services.lottery_winner_service import LotteryWinnerService
from apps.payments.models import UserBalance, Transaction


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
    @transaction.atomic
    def sync_results(self, request):
        """Sincronizar resultados con la API externa y procesar ganadores"""
        results = LotteryAPIService.get_lottery_results()
        saved_results = []
        processed_results = []

        for result in results:
            try:
                lottery = Lottery.objects.get(name=result['nombre_loteria'])
                lottery_result, created = LotteryResult.objects.update_or_create(
                    lottery=lottery,
                    fecha=result['fecha'],
                    defaults={
                        'numero': result['numero'],
                        'numero_serie': result['numero_serie'],
                        'premios_secos': result.get('premios_secos', {})
                    }
                )
                saved_results.append(lottery_result)

                # Procesar ganadores si el resultado es nuevo
                if created:
                    winner_service = LotteryWinnerService(lottery_result)
                    winner_service.process_results()
                    self._process_winners_payments(lottery_result)
                    
                processed_results.append({
                    'lottery': lottery.name,
                    'result': lottery_result,
                    'processed': 'new' if created else 'existing'
                })

            except Lottery.DoesNotExist:
                continue

        serializer = self.get_serializer(saved_results, many=True)
        return Response({
            'results': serializer.data,
            'processing_details': processed_results
        })

    def _process_winners_payments(self, lottery_result):
        """Procesa los pagos para los ganadores de un sorteo"""
        winning_bets = Bet.objects.filter(
            lottery=lottery_result.lottery,
            draw_date=lottery_result.fecha,
            status='WON'
        ).select_related('user')

        for bet in winning_bets:
            # Crear transacción de pago
            transaction = Transaction.objects.create(
                user=bet.user,
                amount=bet.won_amount,
                reference=f"WIN-{bet.lottery.code}-{bet.id}",
                payment_method='PRIZE',
                status='COMPLETED',
                payment_data={
                    'bet_id': str(bet.id),
                    'lottery': bet.lottery.name,
                    'winning_details': bet.winning_details
                }
            )

            # Actualizar saldo del usuario
            user_balance, _ = UserBalance.objects.get_or_create(
                user=bet.user,
                defaults={'balance': Decimal('0')}
            )
            user_balance.balance += bet.won_amount
            user_balance.last_transaction = transaction
            user_balance.save()

    @action(detail=True, methods=['get'])
    def winners(self, request, pk=None):
        """Ver ganadores de un sorteo específico"""
        result = self.get_object()
        winners = Bet.objects.filter(
            lottery=result.lottery,
            draw_date=result.fecha,
            status='WON'
        ).select_related('user')

        winners_data = []
        for bet in winners:
            winners_data.append({
                'user': bet.user.get_full_name(),
                'number': bet.number,
                'series': bet.series,
                'amount_won': str(bet.won_amount),
                'prizes': bet.winning_details.get('prizes', [])
            })

        return Response({
            'lottery': result.lottery.name,
            'draw_date': result.fecha,
            'winning_number': result.numero,
            'winning_series': result.numero_serie,
            'total_winners': len(winners_data),
            'winners': winners_data
        })


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

    @action(detail=False, methods=['get'])
    def winnings_summary(self, request):
        """Obtener resumen de ganancias del usuario"""
        user = request.user
        
        # Obtener apuestas ganadoras
        winning_bets = self.get_queryset().filter(status='WON')
        
        # Calcular totales
        total_won = sum(bet.won_amount for bet in winning_bets)
        total_bets = self.get_queryset().count()
        total_won_bets = winning_bets.count()
        
        # Obtener saldo actual
        current_balance = UserBalance.objects.get(user=user).balance

        # Obtener últimas 5 ganancias
        recent_wins = winning_bets.order_by('-created_at')[:5]
        recent_wins_data = [{
            'lottery': bet.lottery.name,
            'number': bet.number,
            'series': bet.series,
            'amount_won': str(bet.won_amount),
            'draw_date': bet.draw_date,
            'prizes': bet.winning_details.get('prizes', [])
        } for bet in recent_wins]

        return Response({
            'current_balance': str(current_balance),
            'total_won': str(total_won),
            'total_bets': total_bets,
            'winning_bets': total_won_bets,
            'win_rate': f"{(total_won_bets/total_bets*100):.2f}%" if total_bets > 0 else "0%",
            'recent_wins': recent_wins_data
        })
