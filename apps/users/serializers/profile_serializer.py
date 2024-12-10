from rest_framework import serializers

from apps.users.models import User
from apps.payments.models import UserBalance, Transaction
from apps.lottery.models import Bet


class UserProfileSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()
    recent_transactions = serializers.SerializerMethodField()
    recent_bets = serializers.SerializerMethodField()
    recent_prizes = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'email',
            'phone_number', 'identification', 'birth_date',
            'balance', 'recent_transactions', 'recent_bets',
            'recent_prizes'
        ]

    def get_balance(self, obj):
        balance = UserBalance.objects.filter(user=obj).first()
        if balance:
            return {
                'amount': str(balance.balance),
                'last_transaction_date': balance.last_transaction.created_at if balance.last_transaction else None
            }
        return {'amount': '0', 'last_transaction_date': None}

    def get_recent_transactions(self, obj):
        transactions = Transaction.objects.filter(
            user=obj,
            status='COMPLETED'
        ).exclude(
            payment_method='PRIZE'
        ).order_by('-created_at')[:5]
        
        return [{
            'id': str(t.id),
            'amount': str(t.amount),
            'type': t.payment_method,
            'date': t.created_at,
            'reference': t.reference
        } for t in transactions]

    def get_recent_bets(self, obj):
        bets = Bet.objects.filter(
            user=obj
        ).order_by('-created_at')[:5]
        
        return [{
            'id': str(bet.id),
            'lottery': bet.lottery.name,
            'number': bet.number,
            'series': bet.series,
            'amount': str(bet.amount),
            'status': bet.status,
            'draw_date': bet.draw_date
        } for bet in bets]

    def get_recent_prizes(self, obj):
        winning_bets = Bet.objects.filter(
            user=obj,
            status='WON'
        ).order_by('-created_at')[:5]
        
        return [{
            'id': str(bet.id),
            'lottery': bet.lottery.name,
            'number': bet.number,
            'amount_won': str(bet.won_amount),
            'draw_date': bet.draw_date,
            'prize_details': bet.winning_details.get('prizes', [])
        } for bet in winning_bets]
