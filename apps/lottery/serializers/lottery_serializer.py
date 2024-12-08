from rest_framework import serializers
from apps.lottery.models import LotteryResult, Lottery, Bet

class PremioSecoSerializer(serializers.Serializer):
    premio = serializers.CharField()
    numero = serializers.CharField()
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
            'result'
        ]
        read_only_fields = ['status']

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
        if data['amount'] < data['lottery'].min_bet_amount:
            raise serializers.ValidationError(
                f"La apuesta mínima es {data['lottery'].min_bet_amount}"
            )
        
        if data['amount'] > data['lottery'].max_bet_amount:
            raise serializers.ValidationError(
                f"La apuesta máxima es {data['lottery'].max_bet_amount}"
            )

        if not data.get('number', '').isdigit() or len(data.get('number', '')) != 4:
            raise serializers.ValidationError(
                "El número debe ser de exactamente 4 dígitos"
            )

        return data
