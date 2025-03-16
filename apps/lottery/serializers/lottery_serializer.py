from rest_framework import serializers
from django.utils import timezone

from apps.lottery.models import LotteryResult, Lottery, Bet


class PremioSecoSerializer(serializers.Serializer):
    nombre = serializers.CharField()
    resultado = serializers.CharField()
    serie = serializers.CharField()


class LotteryResultSerializer(serializers.ModelSerializer):
    lottery_name = serializers.CharField(source='lottery.name')
    premios_secos = PremioSecoSerializer(many=True)

    # Campos adicionales para la factura
    fraction_price = serializers.SerializerMethodField()
    total_fractions = serializers.SerializerMethodField()
    draw_number = serializers.SerializerMethodField()
    transaction_date = serializers.SerializerMethodField()
    transaction_reference = serializers.SerializerMethodField()
    buyer_id = serializers.SerializerMethodField()
    lottery_logo = serializers.SerializerMethodField()
    distributor = serializers.SerializerMethodField()
    location = serializers.CharField(default="Medellin, ANT.", read_only=True)

    class Meta:
        model = LotteryResult
        fields = [
            'id',
            'lottery_name',
            'numero',
            'numero_serie',
            'fecha',
            'premios_secos',
            'created_at'
        ]


class BetSerializer(serializers.ModelSerializer):
    lottery = serializers.CharField(write_only=True)  # Cambio aquí
    lottery_name = serializers.CharField(source='lottery.name', read_only=True)
    result = serializers.SerializerMethodField()

    class Meta:
        model = Bet
        fields = [
            'id',
            'lottery',
            'lottery_name',
            'number',
            'series',
            'amount',
            'draw_date',
            'status',
            'created_at',
            'result',
            'fractions'
            # Campos adicionales para la factura
            'fraction_price',
            'total_fractions',
            'draw_number',
            'transaction_date',
            'transaction_reference',
            'buyer_id',
            'lottery_logo',
            'distributor',
            'location'
        ]
        read_only_fields = ['status', 'lottery_name']

    def validate_lottery(self, value):  # Nuevo método
        """Valida y obtiene la lotería por nombre"""
        try:
            return Lottery.objects.get(name=value)
        except Lottery.DoesNotExist:
            raise serializers.ValidationError(f"Lotería '{value}' no encontrada")

    def get_result(self, obj):
        """Obtiene el resultado de la lotería si existe"""
        try:
            result = LotteryResult.objects.get(
                lottery=obj.lottery,
                fecha=obj.draw_date
            )
            return LotteryResultSerializer(result).data
        except LotteryResult.DoesNotExist:
            return None

    def validate(self, data):
        """Validaciones de la apuesta"""
        lottery = data['lottery']  # Ahora lottery ya es una instancia de Lottery
        
        if data['amount'] < lottery.min_bet_amount:
            raise serializers.ValidationError(
                f"La apuesta mínima es {lottery.min_bet_amount}"
            )
        
        if data['amount'] > lottery.max_bet_amount:
            raise serializers.ValidationError(
                f"La apuesta máxima es {lottery.max_bet_amount}"
            )

        if not data.get('number', '').isdigit() or len(data.get('number', '')) != 4:
            raise serializers.ValidationError(
                "El número debe ser de exactamente 4 dígitos"
            )

        return data
    
    def get_fraction_price(self, obj):
        """Obtiene el precio de una fracción"""
        return str(obj.lottery.fraction_price)
        
    def get_total_fractions(self, obj):
        """Obtiene el total de fracciones del billete completo"""
        return obj.lottery.fraction_count
        
    def get_draw_number(self, obj):
        """Obtiene el número del sorteo"""
        # Si el sorteo ya pasó, ajustar el número de sorteo
        today = timezone.now().date()
        if obj.draw_date < today:
            # Para sorteos pasados, el número es el last_draw_number (ya que ya se incrementó)
            return obj.lottery.last_draw_number
        else:
            # Para sorteos futuros o del día actual, es el próximo sorteo
            return obj.lottery.last_draw_number + 1
    
    def get_transaction_date(self, obj):
        """Obtiene la fecha y hora de la transacción"""
        return obj.created_at.strftime("%d/%m/%Y %I:%M %p")
    
    def get_transaction_reference(self, obj):
        """Obtiene la referencia de la transacción"""
        # Generar una referencia basada en el ID
        return f"{obj.id.hex[:7]}"
    
    def get_buyer_id(self, obj):
        """Obtiene el ID del comprador"""
        return str(obj.user.id)
    
    def get_lottery_logo(self, obj):
        """Obtiene el logo de la lotería"""
        return obj.lottery.logo_url
    
    def get_distributor(self, obj):
        """Obtiene el nombre del distribuidor"""
        return "Coinjuegos LOTERÍA:19"
