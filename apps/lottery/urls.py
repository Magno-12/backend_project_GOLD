from django.urls import path, include

from rest_framework.routers import DefaultRouter

from apps.lottery.views.lottery_view import LotteryResultViewSet, BetViewSet

router = DefaultRouter()
router.register(r'results', LotteryResultViewSet, basename='lottery-results')
router.register(r'bets', BetViewSet, basename='bets')

urlpatterns = [
    path('', include(router.urls)),
]
