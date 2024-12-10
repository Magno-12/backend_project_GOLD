from rest_framework import status
from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
import uuid

from ..models.transaction import Transaction, UserBalance
from ..serializers.payment_serializers import (
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
        reference = f"REF-{uuid.uuid4().hex[:8]}"

        transaction_data = {
            'amount_in_cents': int(serializer.validated_data['amount'] * 100),
            'currency': WOMPI_SETTINGS['CURRENCY'],
            'reference': reference,
            'payment_method': serializer.validated_data['payment_method'],
            'redirect_url': WOMPI_SETTINGS['REDIRECT_URL']
        }

        response = self.wompi_service.create_transaction(transaction_data)
        if not response.get('data', {}).get('id'):
            return Response(
                {'error': 'Error creando transacción'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Guardar transacción
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
    def verify(self, request, pk=None):
        """Verificar estado de una transacción"""
        transaction = get_object_or_404(self.get_queryset(), pk=pk)
        
        response = self.wompi_service.get_transaction(transaction.wompi_id)
        if response.get('data'):
            transaction.status = response['data']['status']
            transaction.status_detail = response['data']
            transaction.save()

            # Actualizar saldo si la transacción fue exitosa
            if transaction.status == 'APPROVED':
                balance, _ = UserBalance.objects.get_or_create(user=request.user)
                balance.balance += transaction.amount
                balance.last_transaction = transaction
                balance.save()

        return Response(TransactionSerializer(transaction).data)
