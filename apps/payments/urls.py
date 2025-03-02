from django.urls import path, include

from rest_framework.routers import DefaultRouter

from apps.payments.views.payment_view import PaymentViewSet

router = DefaultRouter()
router.register(r'', PaymentViewSet, basename='payments')

urlpatterns = [
    path('', include(router.urls)),
]
