import requests
from datetime import time, datetime, timedelta
from django.utils import timezone
from django.conf import settings

from rest_framework import status
from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.db import transaction, models
from decimal import Decimal

from apps.lottery.models import Lottery, LotteryResult, Bet
from apps.lottery.models.prize_plan import PrizePlan
from apps.lottery.serializers.lottery_serializer import LotteryResultSerializer, BetSerializer
from apps.lottery.permissions.permissions import IsOwner, ResultsPermission
from apps.lottery.services.api_service import LotteryAPIService
from apps.lottery.services.lottery_winner_service import LotteryWinnerService
from apps.lottery.services.lottery_valid_service import LotteryValidationService
from apps.payments.models import UserBalance, Transaction
import logging

logger = logging.getLogger(__name__)


class LotteryResultViewSet(GenericViewSet):
    serializer_class = LotteryResultSerializer
    permission_classes = [IsAuthenticated, ResultsPermission]

    def get_queryset(self):
        return LotteryResult.objects.all().order_by('-fecha')

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def get_result(self, request):
        """Obtener y actualizar resultados de loterías"""
        try:
            print("Intentando obtener resultados...")
            response = requests.get(
                'https://bsorh1cl1f.execute-api.us-east-1.amazonaws.com/dev/',
                headers={'x-api-key': 'C7YHRNx2f04lI1hDWELJ1ajl48FP4ynu17oqN6v0'},
                timeout=10
            )
            print(f"Status code: {response.status_code}")
            print(f"Response content: {response.content}")

            if not response.ok:
                print(f"Error en la respuesta: {response.status_code}")
                return Response(
                    {"error": "Error al obtener resultados", "detail": response.text},
                    status=status.HTTP_400_BAD_REQUEST
                )

            results = response.json()
            print(f"Resultados obtenidos: {results}")
            saved_results = []

            for result in results:
                try:
                    print(f"Procesando resultado: {result}")
                    lottery, created = Lottery.objects.get_or_create(
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
                            'max_bet_amount': Decimal('1000000000'),
                            'number_range_start': '0000',
                            'number_range_end': '9999',
                            'max_fractions_per_combination': 1,
                            'available_series': ['000', '001', '002']
                        }
                    )
                    print(f"Lotería {'creada' if created else 'encontrada'}: {lottery.name}")

                    lottery_result, created = LotteryResult.objects.update_or_create(
                        lottery=lottery,
                        fecha=result['fecha'],
                        defaults={
                            'numero': result['resultado'],
                            'numero_serie': result['serie'],
                            'premios_secos': result.get('secos', [])
                        }
                    )
                    print(f"Resultado {'creado' if created else 'actualizado'} para {lottery.name}")

                    # Si el resultado es nuevo, procesar ganadores
                    if created:
                        try:
                            winner_service = LotteryWinnerService(lottery_result)
                            winner_service.process_results()
                            print(f"Ganadores procesados para {lottery.name}")
                        except Exception as e:
                            print(f"Error procesando ganadores de {lottery.name}: {str(e)}")

                    saved_results.append(lottery_result)

                except Exception as e:
                    print(f"Error procesando {result.get('nombre', 'lotería desconocida')}: {str(e)}")
                    import traceback
                    print(f"Traceback: {traceback.format_exc()}")
                    continue

            if not saved_results:
                return Response(
                    {"message": "No se procesaron resultados", "details": "No se encontraron resultados válidos"},
                    status=status.HTTP_404_NOT_FOUND
                )

            serializer = LotteryResultSerializer(saved_results, many=True)
            return Response({
                'message': f"Procesados {len(saved_results)} resultados",
                'processed_results': serializer.data
            })

        except requests.RequestException as e:
            print(f"Error en la petición HTTP: {str(e)}")
            return Response(
                {"error": "Error en la conexión con el servicio de resultados", "detail": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            print(f"Error inesperado: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return Response(
                {"error": "Error interno del servidor", "detail": str(e)},
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

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def lottery_info(self, request):
        """Obtener información completa de todas las loterías con sus series"""
        try:
            lotteries = Lottery.objects.filter(is_active=True)
            lottery_data = []

            days_es = {
                'MONDAY': 'Lunes',
                'TUESDAY': 'Martes',
                'WEDNESDAY': 'Miércoles',
                'THURSDAY': 'Jueves',
                'FRIDAY': 'Viernes',
                'SATURDAY': 'Sábado',
            }

            for lottery in lotteries:
                lottery_info = {
                    "name": lottery.name,
                    "amount": str(lottery.major_prize_amount),
                    "time": lottery.closing_time.strftime("%H:%M"),
                    "image": lottery.logo_url,
                    "day": days_es.get(lottery.draw_day, lottery.draw_day),
                    "fraction_value": str(lottery.fraction_price),
                    "number_fractions": str(lottery.fraction_count),
                    "sorteo": str(lottery.last_draw_number + 1),
                    "series": lottery.available_series or []  # Series definidas en el admin
                }
                lottery_data.append(lottery_info)

            return Response(lottery_data)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def prize_plans(self, request):
        """Obtener todos los planes de premios activos con sus documentos"""
        try:
            # Filtrar planes activos y ordenar por lotería
            plans = PrizePlan.objects.filter(
                is_active=True
            ).select_related('lottery').order_by('lottery__name')

            plans_data = []
            for plan in plans:
                plan_info = {
                    "id": str(plan.id),
                    "lottery_name": plan.lottery.name,
                    "lottery_code": plan.lottery.code,
                    "name": plan.name,
                    "start_date": plan.start_date,
                    "end_date": plan.end_date,
                    "sorteo_number": plan.sorteo_number,
                    "total_prize_amount": str(plan.total_prize_amount) if plan.total_prize_amount else None,
                    "plan_file_url": plan.plan_file.url if plan.plan_file else None,
                    "last_updated": plan.last_updated,
                    "prizes": {
                        "major": [],
                        "secos": [],
                        "approximations": {
                            "same_series": [],
                            "different_series": []
                        },
                        "special": []
                    }
                }

                # Obtener premios organizados por tipo
                prizes = plan.prizes.select_related('prize_type').order_by('order')
                
                for prize in prizes:
                    prize_data = {
                        "name": prize.name,
                        "amount": str(prize.amount),
                        "fraction_amount": str(prize.fraction_amount),
                        "quantity": prize.quantity
                    }

                    if prize.prize_type.code == 'MAJOR':
                        plan_info['prizes']['major'].append(prize_data)
                    elif prize.prize_type.code == 'SECO':
                        plan_info['prizes']['secos'].append(prize_data)
                    elif prize.prize_type.code == 'APPROX_SAME_SERIES':
                        plan_info['prizes']['approximations']['same_series'].append(prize_data)
                    elif prize.prize_type.code == 'APPROX_DIFF_SERIES':
                        plan_info['prizes']['approximations']['different_series'].append(prize_data)
                    elif prize.prize_type.is_special:
                        plan_info['prizes']['special'].append(prize_data)

                plans_data.append(plan_info)

            return Response({
                "count": len(plans_data),
                "results": plans_data
            })

        except Exception as e:
            return Response(
                {"error": str(e)},
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
        """Crear apuestas múltiples o individual"""
        logger.debug(f"Data recibida: {request.data}")
        
        try:
            with transaction.atomic():
                # Diccionario para llevar el conteo de fracciones por combinación
                fraction_counts = {}
                
                # Verificar si es una lista de apuestas o una sola
                if isinstance(request.data, list):
                    logger.debug("Procesando lista de apuestas")
                    # Validar el total de todas las apuestas
                    total_amount = sum(Decimal(str(bet.get('amount', 0))) for bet in request.data)
                    logger.debug(f"Monto total de apuestas: {total_amount}")
                    
                    try:
                        balance = UserBalance.objects.select_for_update().get(user=request.user)
                        logger.debug(f"Saldo disponible: {balance.balance}")
                        if balance.balance < total_amount:
                            logger.error(f"Saldo insuficiente. Requerido: {total_amount}, Disponible: {balance.balance}")
                            return Response(
                                {
                                    'error': 'Saldo insuficiente para todas las apuestas',
                                    'required': str(total_amount),
                                    'available': str(balance.balance)
                                }, 
                                status=status.HTTP_400_BAD_REQUEST
                            )
                    except UserBalance.DoesNotExist:
                        logger.error("Usuario sin saldo disponible")
                        return Response(
                            {'error': 'Usuario no tiene saldo disponible'},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    serializers = []
                    validation_errors = []
                    
                    # Preprocesamiento para validar fracciones disponibles en todo el lote
                    for bet_data in request.data:
                        try:
                            lottery = Lottery.objects.get(name=bet_data.get('lottery'))
                            next_draw_date = lottery.get_days_until_next_draw()
                            number = bet_data.get('number')
                            series = bet_data.get('series')
                            fractions = bet_data.get('fractions', 1)
                            
                            # Clave única para cada combinación número-serie-lotería-fecha
                            combination_key = f"{lottery.name}-{number}-{series}-{next_draw_date}"
                            
                            # Obtener fracciones ya utilizadas en la BD
                            # Usar select_for_update para bloquear estas filas durante la transacción
                            existing_bets = Bet.objects.filter(
                                lottery=lottery,
                                number=number,
                                series=series,
                                draw_date=next_draw_date,
                                status='PENDING'
                            ).select_for_update()
                            
                            sold_fractions = existing_bets.aggregate(
                                total=models.Sum('fractions')
                            )['total'] or 0
                            
                            # Obtener fracciones solicitadas previamente en este lote
                            current_batch_fractions = fraction_counts.get(combination_key, 0)
                            
                            # Actualizar conteo para esta combinación
                            new_total = sold_fractions + current_batch_fractions + fractions
                            
                            # Verificar que no exceda el límite
                            if new_total > lottery.fraction_count:
                                available = lottery.fraction_count - sold_fractions - current_batch_fractions
                                
                                # Si no quedan fracciones disponibles
                                if available <= 0:
                                    error_msg = f'No quedan fracciones disponibles para esta combinación'
                                else:
                                    error_msg = f'Solo quedan {available} fracciones disponibles para esta combinación'
                                    
                                validation_errors.append({
                                    'bet_data': bet_data,
                                    'errors': [error_msg]
                                })
                                continue
                            
                            # Actualizar el contador si la validación pasó
                            fraction_counts[combination_key] = current_batch_fractions + fractions
                            
                            # Log adicional para verificar el conteo
                            logger.info(f"VALIDACIÓN INICIAL: Lotería: {lottery.name}, Número: {number}, Serie: {series}")
                            logger.info(f"Fracciones vendidas en BD: {sold_fractions}, Solicitadas en este lote hasta ahora: {current_batch_fractions}")
                            logger.info(f"Fracciones pedidas en esta apuesta: {fractions}, Total después de esta apuesta: {new_total}")
                            logger.info(f"Máximo permitido: {lottery.fraction_count}")
                            
                        except Lottery.DoesNotExist:
                            validation_errors.append({
                                'bet_data': bet_data,
                                'errors': ['Lotería no encontrada']
                            })
                    
                    # Si ya hay errores después del preprocesamiento, retornar
                    if validation_errors:
                        return Response(
                            {
                                'error': 'Errores de validación en algunas apuestas',
                                'details': validation_errors
                            }, 
                            status.HTTP_400_BAD_REQUEST
                        )
                    
                    # Procesar cada apuesta después de la validación previa
                    for bet_data in request.data:
                        try:
                            logger.debug(f"Procesando apuesta: {bet_data}")
                            # Obtener la lotería 
                            lottery = Lottery.objects.get(name=bet_data.get('lottery'))
                            logger.debug(f"Lotería encontrada: {lottery.name}")
                            
                            # Inicializar el servicio de validación
                            validation_service = LotteryValidationService(lottery)

                            # Obtener la próxima fecha de sorteo
                            next_draw_date = lottery.get_days_until_next_draw()
                            logger.debug(f"Próxima fecha de sorteo: {next_draw_date}")
                            bet_data['draw_date'] = next_draw_date

                            number = bet_data.get('number')
                            series = bet_data.get('series')
                            fractions = bet_data.get('fractions', 1)
                            amount = Decimal(str(bet_data.get('amount')))
                            
                            # Logs detallados
                            logger.info(f"===== PROCESANDO APUESTA EN BATCH =====")
                            logger.info(f"Lotería: {lottery.name}, Número: {number}, Serie: {series}, Fracciones: {fractions}")
                            logger.info(f"Monto: {amount}, Fecha sorteo: {next_draw_date}")
                            
                            # Verificar nuevamente fracciones disponibles para esta apuesta (doble verificación)
                            existing_bets = Bet.objects.filter(
                                lottery=lottery,
                                number=number,
                                series=series,
                                draw_date=next_draw_date,
                                status='PENDING'
                            ).select_for_update()
                            
                            sold_fractions = existing_bets.aggregate(
                                total=models.Sum('fractions')
                            )['total'] or 0
                            manual_sum = sum(bet.fractions for bet in existing_bets)
                            available = lottery.fraction_count - sold_fractions
                            
                            logger.info(f"Doble verificación - Fracciones vendidas: {sold_fractions} (manual: {manual_sum})")
                            logger.info(f"Doble verificación - Fracciones disponibles: {available}")
                            
                            # Verificar el acumulado del batch en este punto
                            combination_key = f"{lottery.name}-{number}-{series}-{next_draw_date}"
                            batch_fractions = fraction_counts.get(combination_key, 0)
                            logger.info(f"Fracciones acumuladas en el batch hasta este punto: {batch_fractions}")
                            
                            # Validación crítica: verificar que no exceda el límite
                            total_with_batch = sold_fractions + batch_fractions
                            if total_with_batch > lottery.fraction_count:
                                logger.error(f"Error crítico: Se excedería el límite de fracciones con esta apuesta")
                                return Response(
                                    {'error': f'No quedan fracciones disponibles para esta combinación'},
                                    status=status.HTTP_400_BAD_REQUEST
                                )
                            
                            # Verificar que esta apuesta específica no exceda lo que queda disponible
                            if fractions > (lottery.fraction_count - total_with_batch):
                                logger.error(f"Error: La apuesta excede las fracciones disponibles")
                                return Response(
                                    {'error': f'No hay suficientes fracciones disponibles. Máximo disponible: {lottery.fraction_count - total_with_batch}'},
                                    status=status.HTTP_400_BAD_REQUEST
                                )

                            # Validar el resto de reglas
                            validation_result = validation_service.validate_bet_request(
                                user=request.user,
                                number=number,
                                series=series,
                                fractions=fractions,
                                amount=amount
                            )

                            if not validation_result['is_valid']:
                                validation_errors.append({
                                    'bet_data': bet_data,
                                    'errors': validation_result['errors']
                                })
                                continue

                            serializer = self.get_serializer(data=bet_data)
                            if serializer.is_valid():
                                logger.debug("Serializer válido")
                                serializers.append({
                                    'serializer': serializer,
                                    'lottery': lottery,
                                    'validation': {'is_valid': True}
                                })
                            else:
                                logger.error(f"Error en serializer: {serializer.errors}")
                                validation_errors.append({
                                    'bet_data': bet_data,
                                    'errors': serializer.errors
                                })
                        except Lottery.DoesNotExist:
                            logger.error(f"Lotería no encontrada: {bet_data.get('lottery')}")
                            validation_errors.append({
                                'bet_data': bet_data,
                                'errors': ['Lotería no encontrada']
                            })
                        except Exception as e:
                            logger.error(f"Error inesperado procesando apuesta: {str(e)}")
                            validation_errors.append({
                                'bet_data': bet_data,
                                'errors': [str(e)]
                            })

                    # Si hay errores de validación, retornarlos
                    if validation_errors:
                        logger.error(f"Errores de validación encontrados: {validation_errors}")
                        return Response(
                            {
                                'error': 'Errores de validación en algunas apuestas',
                                'details': validation_errors
                            }, 
                            status.HTTP_400_BAD_REQUEST
                        )
                        
                    # Si todas las apuestas son válidas, guardarlas
                    created_bets = []
                    logger.debug("Iniciando guardado de apuestas")
                    
                    # Actualizar saldo del usuario primero
                    balance.balance -= total_amount
                    balance.save()
                    logger.debug(f"Saldo actualizado: {balance.balance}")

                    for data in serializers:
                        bet = data['serializer'].save(
                            user=request.user,
                            lottery=data['lottery'],
                            status='PENDING'
                        )
                        created_bets.append(bet)
                        logger.debug(f"Apuesta creada: {bet.id}")
                        
                        # Verificar nuevamente el conteo total de fracciones para esta combinación
                        lottery = data['lottery']
                        number = bet.number
                        series = bet.series
                        draw_date = bet.draw_date
                        
                        # Verificación crítica final para cada apuesta guardada
                        current_total = Bet.objects.filter(
                            lottery=lottery,
                            number=number,
                            series=series,
                            draw_date=draw_date,
                            status='PENDING'
                        ).aggregate(total=models.Sum('fractions'))['total'] or 0
                        
                        logger.info(f"DESPUÉS DE GUARDAR - {lottery.name}, {number}, {series}: {current_total}/{lottery.fraction_count}")
                        
                        if current_total > lottery.fraction_count:
                            logger.error(f"⚠️ ALERTA CRÍTICA: Se ha excedido el límite de fracciones: {current_total}/{lottery.fraction_count}")
                    
                    response_serializer = self.get_serializer(created_bets, many=True)
                    logger.debug("Proceso completado exitosamente")
                    return Response(
                        {
                            'message': 'Apuestas creadas exitosamente',
                            'bets': response_serializer.data,
                            'total_amount': str(total_amount),
                            'new_balance': str(balance.balance)
                        }, 
                        status=status.HTTP_201_CREATED
                    )
                
                # Si es una sola apuesta
                else:
                    logger.debug("Procesando apuesta individual")
                    try:
                        lottery = Lottery.objects.get(name=request.data.get('lottery'))
                        logger.debug(f"Lotería encontrada: {lottery.name}")
                        
                        validation_service = LotteryValidationService(lottery)

                        bet_data = request.data.copy()
                        # Obtener la próxima fecha de sorteo
                        next_draw_date = lottery.get_days_until_next_draw()
                        bet_data['draw_date'] = next_draw_date
                        logger.debug(f"Próxima fecha de sorteo: {next_draw_date}")

                        number = bet_data.get('number')
                        series = bet_data.get('series')
                        fractions = bet_data.get('fractions', 1)
                        amount = Decimal(str(bet_data.get('amount')))

                        # Verificar las fracciones disponibles usando select_for_update para bloqueo
                        existing_bets = Bet.objects.filter(
                            lottery=lottery,
                            number=number,
                            series=series,
                            draw_date=next_draw_date,
                            status='PENDING'
                        ).select_for_update()  # Bloquea las filas durante la transacción
                        
                        # Log detallado de las apuestas existentes
                        logger.info(f"===== VERIFICACIÓN DE FRACCIONES =====")
                        logger.info(f"Lotería: {lottery.name}, Número: {number}, Serie: {series}, Fecha: {next_draw_date}")
                        logger.info(f"Total fracciones por billete: {lottery.fraction_count}")
                        logger.info(f"Fracciones solicitadas: {fractions}")
                        
                        # Log de apuestas existentes
                        logger.info(f"Apuestas existentes para esta combinación:")
                        for bet in existing_bets:
                            logger.info(f"  ID: {bet.id}, Fracciones: {bet.fractions}, Usuario: {bet.user.id}, Fecha creación: {bet.created_at}")
                        
                        # Calcular fracciones ya vendidas en la base de datos
                        sold_fractions = existing_bets.aggregate(
                            total=models.Sum('fractions')
                        )['total'] or 0
                        logger.info(f"Fracciones ya vendidas (según suma): {sold_fractions} de {lottery.fraction_count}")
                        
                        # Verificación manual del total (para comparar con el aggregate)
                        manual_sum = sum(bet.fractions for bet in existing_bets)
                        logger.info(f"Fracciones ya vendidas (suma manual): {manual_sum}")
                        
                        # Si hay discrepancia, es un problema serio
                        if manual_sum != sold_fractions:
                            logger.error(f"¡DISCREPANCIA EN LA SUMA DE FRACCIONES! Aggregate: {sold_fractions}, Manual: {manual_sum}")
                        
                        # Calcular fracciones disponibles
                        available_fractions = lottery.fraction_count - sold_fractions
                        logger.info(f"Fracciones disponibles: {available_fractions}")
                        
                        # TRIPLE VERIFICACIÓN: comprobar nuevamente si ya se alcanzó el límite
                        if sold_fractions >= lottery.fraction_count:
                            logger.error(f"¡ALERTA CRÍTICA! Se ha alcanzado o superado el límite de fracciones: {sold_fractions}/{lottery.fraction_count}")
                            return Response(
                                {'error': f'No quedan fracciones disponibles para esta combinación'},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                        
                        # Verificar si hay suficientes fracciones disponibles
                        if fractions > available_fractions:
                            logger.error(f"Fracciones insuficientes. Solicitadas: {fractions}, Disponibles: {available_fractions}")
                            return Response(
                                {'error': f'Solo quedan {available_fractions} fracciones disponibles para esta combinación'},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                        
                        # Verificar si esta compra alcanzaría o superaría el límite máximo
                        if sold_fractions + fractions >= lottery.fraction_count:
                            logger.info("⚠️ Esta compra alcanzará el límite máximo de fracciones")
                        
                        # Validar el resto de reglas
                        validation_result = validation_service.validate_bet_request(
                            user=request.user,
                            number=number,
                            series=series,
                            fractions=fractions,
                            amount=amount
                        )

                        if not validation_result['is_valid']:
                            return Response(
                                {'error': validation_result['errors'][0]},
                                status=status.HTTP_400_BAD_REQUEST
                            )

                        serializer = self.get_serializer(data=bet_data)
                        if serializer.is_valid():
                            logger.debug("Serializer válido")
                            # Validar saldo
                            balance = UserBalance.objects.select_for_update().get(user=request.user)
                            if balance.balance < amount:
                                return Response(
                                    {
                                        'error': 'Saldo insuficiente',
                                        'required': str(amount),
                                        'available': str(balance.balance)
                                    },
                                    status=status.HTTP_400_BAD_REQUEST
                                )

                            # Actualizar saldo
                            balance.balance -= amount
                            balance.save()
                            logger.debug(f"Saldo actualizado: {balance.balance}")

                            # Crear apuesta
                            bet = serializer.save(
                                user=request.user,
                                lottery=lottery,
                                status='PENDING'
                            )
                            logger.debug(f"Apuesta creada: {bet.id}")
                            
                            # Verificación crítica: comprobar si ya se alcanzó el límite después de esta compra
                            # Esta es una protección adicional para evitar exceder el límite
                            current_total = Bet.objects.filter(
                                lottery=lottery,
                                number=number,
                                series=series,
                                draw_date=next_draw_date,
                                status='PENDING'
                            ).aggregate(total=models.Sum('fractions'))['total'] or 0
                            
                            logger.info(f"DESPUÉS DE GUARDAR - Total fracciones para esta combinación: {current_total}/{lottery.fraction_count}")
                            
                            if current_total > lottery.fraction_count:
                                logger.error(f"⚠️ ALERTA CRÍTICA: Se ha excedido el límite de fracciones: {current_total}/{lottery.fraction_count}")
                            
                            return Response(
                                {
                                    'message': 'Apuesta creada exitosamente',
                                    'bet': serializer.data,
                                    'amount': str(amount),
                                    'new_balance': str(balance.balance)
                                }, 
                                status=status.HTTP_201_CREATED
                            )
                        logger.error(f"Error en serializer: {serializer.errors}")
                        return Response(
                            serializer.errors, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
                        
                    except Lottery.DoesNotExist:
                        logger.error(f"Lotería no encontrada: {request.data.get('lottery')}")
                        return Response(
                            {'error': 'Lotería no encontrada'},
                            status=status.HTTP_404_NOT_FOUND
                        )
                    except UserBalance.DoesNotExist:
                        logger.error("Usuario sin saldo disponible")
                        return Response(
                            {'error': 'Usuario no tiene saldo disponible'},
                            status=status.HTTP_400_BAD_REQUEST
                        )

        except Exception as e:
            logger.error(f"Error inesperado: {str(e)}")
            logger.error(f"Tipo de error: {type(e)}")
            import traceback
            logger.error(f"Traceback completo: {traceback.format_exc()}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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

    @action(detail=False, methods=['get'])
    def user_ganancias(self, request):
        """Endpoint para la pantalla de ganancias"""
        try:
            print("Iniciando verificación de resultados y ganancias")
            
            # Primero obtener y procesar resultados
            try:
                # Obtener resultados más recientes
                response = requests.get(
                    'https://bsorh1cl1f.execute-api.us-east-1.amazonaws.com/dev/',
                    headers={'x-api-key': 'C7YHRNx2f04lI1hDWELJ1ajl48FP4ynu17oqN6v0'}
                )

                if response.status_code == 200:
                    results = response.json()
                    print(f"Resultados obtenidos: {results}")

                    # Procesar cada resultado
                    for result in results:
                        lottery = Lottery.objects.get(name=result['nombre'])
                        lottery_result, created = LotteryResult.objects.update_or_create(
                            lottery=lottery,
                            fecha=result['fecha'],
                            defaults={
                                'numero': result['resultado'],
                                'numero_serie': result['serie'],
                                'premios_secos': result.get('secos', [])
                            }
                        )

                        # Procesar ganadores si hay resultados nuevos
                        if created:
                            winner_service = LotteryWinnerService(lottery_result)
                            winner_service.process_results()

            except Exception as e:
                print(f"Error procesando resultados: {str(e)}")

            # Ahora obtener solo las ganancias confirmadas (status = 'WON')
            start_date = timezone.now() - timedelta(days=30)
            
            winning_bets = Bet.objects.filter(
                user=request.user,
                status='WON'
            ).select_related('lottery').order_by('-created_at')[:10]

            summary = {
                'total_ganado': sum(bet.won_amount for bet in winning_bets),
                'total_apostado': Bet.objects.filter(
                    user=request.user
                ).count(),
                'ultima_actualizacion': timezone.now()
            }

            response_data = {
                'summary': summary,
                'recent_wins': [{
                    'lottery_name': bet.lottery.name,
                    'number': bet.number,
                    'amount_won': str(bet.won_amount),
                    'draw_date': bet.draw_date,
                    'prize_details': bet.winning_details.get('prizes', [])
                } for bet in winning_bets]
            }

            return Response(response_data)

        except Exception as e:
            print(f"Error en user_ganancias: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def historic_ganancias(self, request):
        """Endpoint para cargar más resultados históricos"""
        try:
            page = int(request.query_params.get('page', 1))
            page_size = 20
            
            winning_bets = Bet.objects.filter(
                user=request.user,
                status='WON'
            ).select_related(
                'lottery'
            ).order_by('-created_at')[
                (page-1)*page_size:page*page_size
            ]

            return Response({
                'results': [{
                    'lottery_name': bet.lottery.name,
                    'number': bet.number,
                    'amount_won': str(bet.won_amount),
                    'draw_date': bet.draw_date,
                    'prize_details': bet.winning_details.get('prizes', [])
                } for bet in winning_bets],
                'has_more': winning_bets.count() == page_size
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
