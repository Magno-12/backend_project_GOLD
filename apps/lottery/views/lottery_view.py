import requests
from datetime import time, datetime

from rest_framework import status
from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
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

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def get_result(self, request):
        """Obtener y actualizar resultados de loterías"""
        try:
            response = requests.get(
                'https://bsorh1cl1f.execute-api.us-east-1.amazonaws.com/dev/',
                headers={'x-api-key': 'C7YHRNx2f04lI1hDWELJ1ajl48FP4ynu17oqN6v0'}
            )

            if response.status_code == 200:
                results = response.json()
                saved_results = []

                for result in results:
                    try:
                        lottery, _ = Lottery.objects.get_or_create(
                            name=result['nombre'],
                            defaults={
                                'code': result['nombre'].replace(' ', '_').upper(),
                                'draw_day': 'MONDAY',
                                'draw_time': time(22, 30),
                                'fraction_count': 3,
                                'fraction_price': Decimal('5000'),
                                'is_active': True,
                                'major_prize_amount': Decimal('1000000000'),
                                'min_bet_amount': Decimal('5000'),
                                'max_bet_amount': Decimal('1000000000')
                            }
                        )

                        lottery_result, created = LotteryResult.objects.update_or_create(
                            lottery=lottery,
                            fecha=result['fecha'],
                            defaults={
                                'numero': result['resultado'],
                                'numero_serie': result['serie'],
                                'premios_secos': result.get('secos', [])  # JSON directo
                            }
                        )

                        saved_results.append(lottery_result)

                    except Exception as e:
                        print(f"Error procesando {result['nombre']}: {str(e)}")
                        continue

                serializer = LotteryResultSerializer(saved_results, many=True)
                return Response({
                    'message': f"Procesados {len(saved_results)} resultados",
                    'processed_results': serializer.data
                })

            return Response(
                {"error": "No se pudieron obtener los resultados"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    def retrieve(self, request, pk=None):
        """Obtener un resultado específico"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    # @action(detail=False, methods=['get'])
    # @transaction.atomic
    # def sync_results(self, request):
    #     """Sincronizar resultados con la API externa y procesar ganadores"""
    #     # Verificar autorización del endpoint
    #     if not request.auth:
    #         return Response({
    #             'error': 'No autorizado'
    #         }, status=status.HTTP_401_UNAUTHORIZED)

    #     results = LotteryAPIService.get_lottery_results()
    #     if not results:
    #         return Response({
    #             'message': 'No se encontraron resultados',
    #             'results': [],
    #             'processing_details': []
    #         })

    #     saved_results = []
    #     processed_results = []

    #     for result in results:
    #         try:
    #             lottery = Lottery.objects.get(name=result['nombre'])
    #             lottery_result, created = LotteryResult.objects.update_or_create(
    #                 lottery=lottery,
    #                 fecha=result['fecha'],
    #                 defaults={
    #                     'numero': result['numero'],
    #                     'numero_serie': result['serie'],
    #                     'premios_secos': result.get('premios_secos', {})
    #                 }
    #             )
    #             saved_results.append(lottery_result)

    #             # Procesar ganadores si el resultado es nuevo
    #             if created:
    #                 winner_service = LotteryWinnerService(lottery_result)
    #                 winner_service.process_results()
    #                 self._process_winners_payments(lottery_result)

    #             processed_results.append({
    #                 'lottery': lottery.name,
    #                 'result': lottery_result,
    #                 'processed': 'new' if created else 'existing'
    #             })

    #         except Lottery.DoesNotExist:
    #             continue

    #     serializer = self.get_serializer(saved_results, many=True)
    #     return Response({
    #         'results': serializer.data,
    #         'processing_details': processed_results
    #     })

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

    @action(detail=False, methods=['get'])
    def user_prizes(self, request):
        """Ver detalle completo de premios ganados por el usuario"""
        try:
            winning_bets = Bet.objects.filter(
                user=request.user,
                status='WON'
            ).select_related('lottery').order_by('-draw_date')

            prizes_detail = []
            for bet in winning_bets:
                prize_info = {
                    'bet_id': str(bet.id),
                    'lottery': bet.lottery.name,
                    'draw_date': bet.draw_date,
                    'number_played': bet.number,
                    'series_played': bet.series,
                    'amount_bet': str(bet.amount),
                    'total_won': str(bet.won_amount),
                    'winning_details': {
                        'winning_number': bet.winning_details.get('number'),
                        'winning_series': bet.winning_details.get('series'),
                        'prizes': []
                    }
                }

                # Detallar cada premio ganado
                for prize in bet.winning_details.get('prizes', []):
                    prize_info['winning_details']['prizes'].append({
                        'type': prize.get('type'),
                        'name': prize.get('name'),
                        'amount': prize.get('amount'),
                        'match_type': prize.get('match_type'),
                        'details': prize.get('details', {})
                    })

                prizes_detail.append(prize_info)

            return Response({
                'total_winning_bets': len(prizes_detail),
                'total_won': str(sum(bet.won_amount for bet in winning_bets)),
                'prizes': prizes_detail
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def create_bet(self, request):
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
