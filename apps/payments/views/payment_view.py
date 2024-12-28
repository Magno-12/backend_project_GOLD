from rest_framework import status
from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid
from decimal import Decimal

from apps.payments.models.transaction import Transaction, UserBalance
from apps.payments.serializers.payment_serializers import (
    TransactionSerializer,
    UserBalanceSerializer,
    CardTokenizationSerializer
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
                payment_data={
                    'cliente_id': str(request.user.id),
                    'fecha_transaccion': timezone.now().isoformat(),
                    'monto': str(amount),
                    'moneda': 'COP',
                    'descripcion': request.data.get('descripcion', 'Compra o recarga'),
                    'estado': 'pendiente'
                }
            )

            # Retornar datos necesarios para el widget
            return Response({
                'reference': reference,
                'signature': signature,
                'amount_in_cents': amount_in_cents,
                'currency': 'COP',
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
            # Primero intentar buscar por UUID
            try:
                transaction = get_object_or_404(self.get_queryset(), pk=pk)
            except ValidationError:
                # Si no es UUID, buscar por wompi_id
                transaction = get_object_or_404(self.get_queryset(), wompi_id=pk)

            # Obtener estado actual de Wompi
            response = self.wompi_service.get_transaction(transaction.wompi_id)

            if response.get('data'):
                with transaction.atomic():
                    # Actualizar estado de la transacción
                    transaction.status = response['data']['status']
                    transaction.status_detail = response['data']
                    transaction.save()

                    # Si la transacción fue exitosa, actualizar saldo
                    if transaction.status == 'APPROVED':
                        balance, _ = UserBalance.objects.get_or_create(user=request.user)
                        balance.balance += transaction.amount
                        balance.last_transaction = transaction
                        balance.save()

            return Response(TransactionSerializer(transaction).data)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
