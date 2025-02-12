from rest_framework import status
from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction
import uuid
from decimal import Decimal
from datetime import timedelta

from apps.payments.models.transaction import Transaction, UserBalance
from apps.payments.models.withdrawal import PrizeWithdrawal
from apps.payments.models.bank_account import BankDestinationAccount
from apps.lottery.models.prize import Prize
from apps.payments.serializers.payment_serializers import (
    TransactionSerializer,
    UserBalanceSerializer,
    CardTokenizationSerializer,
    PrizeWithdrawalSerializer
)
from apps.payments.services.wompi_service import WompiService
from apps.payments.config import WOMPI_SETTINGS


class PaymentViewSet(GenericViewSet):
    """ViewSet para manejar pagos y transacciones"""
    permission_classes = [IsAuthenticated]
    wompi_service = WompiService()

    def get_serializer_class(self):
        if self.action == 'tokenize_card':
            return CardTokenizationSerializer
        return TransactionSerializer

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def tokenize_card(self, request):
        """Tokenizar tarjeta de crédito"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        response = self.wompi_service.tokenize_card(serializer.validated_data)
        if not response.get('data', {}).get('id'):
            return Response(
                {'error': 'Error tokenizando tarjeta'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(response['data'])

    @action(detail=False, methods=['post'])
    def create_transaction(self, request):
        """Crear nueva transacción"""
        serializer = TransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Generar referencia única
        reference = f"TEST-{uuid.uuid4().hex[:8]}"

        # Preparar datos para Wompi
        transaction_data = {
            'amount_in_cents': int(serializer.validated_data['amount'] * 100),
            'currency': WOMPI_SETTINGS['CURRENCY'],
            'customer_email': request.user.email,
            'reference': reference
        }

        # Configurar método de pago
        if serializer.validated_data['payment_method'] == 'CARD':
            transaction_data['payment_method'] = {
                'type': 'CARD',
                'token': serializer.validated_data.get('card_token'),
                'installments': serializer.validated_data.get('installments', 1)
            }

        # Agregar acceptance token si viene
        if serializer.validated_data.get('acceptance_token'):
            transaction_data['acceptance_token'] = serializer.validated_data['acceptance_token']

        response = self.wompi_service.create_transaction(transaction_data)
        if not response.get('data', {}).get('id'):
            return Response(
                {'error': 'Error creando transacción'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Crear transacción
        transaction = Transaction.objects.create(
            user=request.user,
            amount=serializer.validated_data['amount'],
            reference=reference,
            wompi_id=response['data']['id'],
            payment_method=serializer.validated_data['payment_method'],
            payment_data=response['data']
        )

        return Response(TransactionSerializer(transaction).data)

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Obtener historial de transacciones"""
        transactions = self.get_queryset()
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def balance(self, request):
        """Obtener saldo del usuario"""
        balance, _ = UserBalance.objects.get_or_create(user=request.user)
        serializer = UserBalanceSerializer(balance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def process_response(self, request, pk=None):
        """Procesar respuesta del widget de Wompi"""
        try:
            transaction = get_object_or_404(self.get_queryset(), pk=pk)
            
            # Actualizar estado según la respuesta
            wompi_status = request.data.get('status')
            if wompi_status:
                transaction.status = wompi_status
                transaction.wompi_id = request.data.get('id')
                transaction.status_detail = request.data
                transaction.save()

                # Si es aprobada, actualizar saldo
                if wompi_status == 'APPROVED':
                    with transaction.atomic():
                        balance, _ = UserBalance.objects.get_or_create(
                            user=transaction.user
                        )
                        balance.balance += transaction.amount
                        balance.last_transaction = transaction
                        balance.save()

            return Response(TransactionSerializer(transaction).data)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def winnings_summary(self, request):
        """Obtener resumen de ganancias del usuario"""
        balance, _ = UserBalance.objects.get_or_create(user=request.user)
        winning_transactions = Transaction.objects.filter(
            user=request.user,
            payment_method='PRIZE',
            status='COMPLETED'
        )

        total_winnings = sum(t.amount for t in winning_transactions)
        recent_wins = winning_transactions.order_by('-created_at')[:5]

        return Response({
            'current_balance': str(balance.balance),
            'total_winnings': str(total_winnings),
            'winning_count': winning_transactions.count(),
            'recent_wins': TransactionSerializer(recent_wins, many=True).data
        })

    @action(detail=False, methods=['get'])
    def balance(self, request):
        """Obtener saldo del usuario"""
        try:
            balance, created = UserBalance.objects.get_or_create(
                user=request.user,
                defaults={'balance': Decimal('0')}
            )

            last_transaction = Transaction.objects.filter(
                user=request.user,
                status='COMPLETED'
            ).order_by('-created_at').first()

            response_data = {
                'balance': str(balance.balance),
                'last_transaction_date': last_transaction.created_at if last_transaction else None,
                'transactions_summary': {
                    'total_transactions': Transaction.objects.filter(
                        user=request.user,
                        status='COMPLETED'
                    ).count(),
                    'pending_transactions': Transaction.objects.filter(
                        user=request.user,
                        status='PENDING'
                    ).count()
                },
                'last_transaction': {
                    'id': str(last_transaction.id),
                    'amount': str(last_transaction.amount),
                    'type': last_transaction.payment_method,
                    'reference': last_transaction.reference
                } if last_transaction else None
            }

            return Response(response_data)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Obtener historial de transacciones"""
        try:
            transactions = self.get_queryset().order_by('-created_at')
            serializer = TransactionSerializer(transactions, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def init_transaction(self, request):
        """Iniciar una transacción para el widget de Wompi"""
        try:
            # Validar datos de entrada
            amount = Decimal(request.data.get('monto', 0))
            transaction_type = request.data.get('tipo', 'RECHARGE')

            if amount <= 0:
                return Response(
                    {'error': 'Monto inválido'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Generar referencia única
            reference = self.wompi_service.generate_reference()
            
            # Generar firma
            amount_in_cents = int(amount * 100)
            signature = self.wompi_service.generate_signature(
                reference=reference,
                amount_in_cents=amount_in_cents
            )

            # Crear transacción en estado pendiente
            transaction = Transaction.objects.create(
                user=request.user,
                amount=amount,
                reference=reference,
                signature=signature,
                status='PENDING',
                transaction_type=transaction_type,
                payment_data={
                    'amount_in_cents': amount_in_cents,
                    'currency': WOMPI_SETTINGS['CURRENCY']
                }
            )

            return Response({
                'reference': reference,
                'signature': signature,
                'amount_in_cents': amount_in_cents,
                'currency': WOMPI_SETTINGS['CURRENCY'],
                'transaction_id': str(transaction.id)
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verificar estado de una transacción"""
        try:
            # Intentar buscar por UUID
            try:
                transaction_obj = get_object_or_404(self.get_queryset(), pk=pk)
            except ValidationError:
                try:
                    transaction_obj = get_object_or_404(self.get_queryset(), wompi_id=pk)
                except:
                    transaction_obj = get_object_or_404(self.get_queryset(), reference=pk)
            
            # Obtener estado de Wompi
            if transaction_obj.wompi_id:
                response = self.wompi_service.get_transaction(transaction_obj.wompi_id)
            else:
                response = self.wompi_service.get_transaction_by_reference(transaction_obj.reference)
            
            if response.get('data'):
                with transaction.atomic():
                    # Actualizar el wompi_id si no lo teníamos
                    if not transaction_obj.wompi_id and response['data'].get('id'):
                        transaction_obj.wompi_id = response['data']['id']
                    
                    transaction_obj.status = response['data']['status']
                    transaction_obj.status_detail = response['data']
                    
                    # Actualizar el método de pago desde la respuesta de Wompi
                    if response['data'].get('payment_method_type'):
                        transaction_obj.payment_method = response['data']['payment_method_type']
                    
                    transaction_obj.save()

                    # Solo actualizar balance si es RECARGA y está APROBADA
                    if transaction_obj.status == 'APPROVED' and transaction_obj.transaction_type == 'RECHARGE':
                        balance, _ = UserBalance.objects.get_or_create(user=transaction_obj.user)
                        balance.balance += transaction_obj.amount
                        balance.last_transaction = transaction_obj
                        balance.save()

            return Response(TransactionSerializer(transaction_obj).data)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def request_withdrawal(self, request):
        """Solicitar retiro de premio"""
        try:
            serializer = PrizeWithdrawalSerializer(
                data=request.data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)

            amount = serializer.validated_data['amount']

            # Validar monto mínimo
            if amount < 50000:
                return Response({
                    'error': 'El monto mínimo de retiro es de $50.000'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validar monto máximo
            if amount > 10000000:
                return Response({
                    'warning': 'El monto excede el límite de retiro automático.',
                    'support_contact': {
                        'email': 'soporte@gold.com(provisional)',
                        'phone': '+57xxxxxxxxxx',
                        'hours': 'Lun-Vie 8am-6pm'
                    }
                }, status=status.HTTP_200_OK)

            # Verificar si tiene saldo suficiente
            balance = UserBalance.objects.get(user=request.user)
            if balance.balance < amount:
                return Response({
                    'error': 'Saldo insuficiente para realizar el retiro'
                }, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                # Crear o actualizar la cuenta destino
                destination_account = BankDestinationAccount.objects.create(
                    bank=serializer.validated_data['bank'],
                    account_type=serializer.validated_data['account_type'],
                    account_number=serializer.validated_data['account_number'],
                    account_owner=f"{request.user.first_name} {request.user.last_name}",
                    identification_type='CC',
                    identification_number=request.user.identification,
                    description=f"Cuenta para retiro {serializer.validated_data['bank']}"
                )

                # Crear la solicitud de retiro
                withdrawal = PrizeWithdrawal.objects.create(
                    user=request.user,
                    amount=amount,
                    bank=serializer.validated_data['bank'],
                    account_type=serializer.validated_data['account_type'],
                    account_number=serializer.validated_data['account_number'],
                    destination_account=destination_account,
                    status='PENDING'
                )

                # Descontar el saldo inmediatamente
                balance.balance -= amount
                balance.save()

            return Response({
                'message': 'Solicitud de retiro creada exitosamente. Pendiente de aprobación.',
                'data': {
                    'withdrawal_code': withdrawal.withdrawal_code,
                    'amount': str(amount),
                    'expiration_date': withdrawal.expiration_date,
                    'status': 'PENDING',
                    'new_balance': str(balance.balance)
                }
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def withdrawal_history(self, request):
        """Obtener historial de retiros del usuario"""
        try:
            withdrawals = PrizeWithdrawal.objects.filter(user=request.user)
            serializer = PrizeWithdrawalSerializer(withdrawals, many=True)

            # Agrupar por estado
            status_summary = {
                'pending': 0,
                'approved': 0,
                'rejected': 0,
                'total_amount': Decimal('0')
            }

            for withdrawal in withdrawals:
                if withdrawal.status == 'PENDING':
                    status_summary['pending'] += 1
                elif withdrawal.status == 'APPROVED':
                    status_summary['approved'] += 1
                    status_summary['total_amount'] += withdrawal.amount
                elif withdrawal.status == 'REJECTED':
                    status_summary['rejected'] += 1

            return Response({
                'withdrawals': serializer.data,
                'summary': status_summary
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def withdrawal_status(self, request, pk=None):
        """Consultar estado de un retiro específico"""
        try:
            withdrawal = PrizeWithdrawal.objects.get(
                withdrawal_code=pk,
                user=request.user
            )
            
            # Verificar si debe revertirse
            if withdrawal.should_revert:
                withdrawal.revert_balance()
            
            serializer = PrizeWithdrawalSerializer(withdrawal)
            
            response_data = {
                'status': withdrawal.status,
                'status_display': withdrawal.get_status_display(),
                'details': serializer.data
            }

            # Si está pendiente, agregar información del tiempo restante
            if withdrawal.status == 'PENDING':
                time_elapsed = timezone.now() - withdrawal.created_at
                hours_remaining = 48 - (time_elapsed.total_seconds() / 3600)
                
                response_data['time_info'] = {
                    'created_at': withdrawal.created_at,
                    'hours_remaining': round(max(0, hours_remaining), 1),
                    'will_revert_at': withdrawal.created_at + timedelta(hours=48),
                    'current_time': timezone.now()
                }

            return Response(response_data)

        except PrizeWithdrawal.DoesNotExist:
            return Response(
                {'error': 'Retiro no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

    @action(detail=True, methods=['get'])
    def withdrawal_detail(self, request, pk=None):
        """
        Obtener detalle completo de un retiro específico.
        El pk puede ser el ID del retiro o el código de retiro (withdrawal_code)
        """
        try:
            # Intentar buscar por withdrawal_code primero
            withdrawal = PrizeWithdrawal.objects.filter(
                Q(withdrawal_code=pk) | Q(id=pk),
                user=request.user
            ).first()

            if not withdrawal:
                return Response(
                    {'error': 'Retiro no encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )

            serializer = PrizeWithdrawalSerializer(withdrawal)
            
            # Calcular información adicional
            time_elapsed = timezone.now() - withdrawal.created_at
            hours_elapsed = time_elapsed.total_seconds() / 3600

            response_data = {
                'withdrawal_info': {
                    **serializer.data,
                    'status_display': withdrawal.get_status_display(),
                    'bank_display': withdrawal.get_bank_display(),
                    'account_type_display': withdrawal.get_account_type_display()
                },
                'timing_info': {
                    'created_at': withdrawal.created_at,
                    'processed_date': withdrawal.processed_date,
                    'hours_elapsed': round(hours_elapsed, 1),
                    'expiration_date': withdrawal.expiration_date
                },
                'status_info': {
                    'is_expired': withdrawal.should_revert,
                    'can_be_cancelled': withdrawal.status == 'PENDING' and not withdrawal.should_revert
                }
            }

            # Si está pendiente, agregar información del tiempo restante
            if withdrawal.status == 'PENDING':
                hours_remaining = 48 - hours_elapsed
                response_data['timing_info']['hours_remaining'] = round(max(0, hours_remaining), 1)

            # Si fue procesado, agregar información del procesamiento
            if withdrawal.status in ['APPROVED', 'REJECTED', 'REVERSED']:
                response_data['processing_info'] = {
                    'processed_at': withdrawal.processed_date,
                    'processing_time': (
                        withdrawal.processed_date - withdrawal.created_at
                    ).total_seconds() / 3600 if withdrawal.processed_date else None,
                    'admin_notes': withdrawal.admin_notes if withdrawal.admin_notes else None
                }

            return Response(response_data)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
