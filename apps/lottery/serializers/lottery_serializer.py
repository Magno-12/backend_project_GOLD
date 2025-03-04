from rest_framework import serializers

from apps.lottery.models import LotteryResult, Lottery, Bet


class PremioSecoSerializer(serializers.Serializer):
    nombre = serializers.CharField()
    resultado = serializers.CharField()
    serie = serializers.CharField()


class LotteryResultSerializer(serializers.ModelSerializer):
    lottery_name = serializers.CharField(source='lottery.name')
    premios_secos = PremioSecoSerializer(many=True)

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
