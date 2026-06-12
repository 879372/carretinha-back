from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SessionViewSet, ChildViewSet, PlanViewSet, PaymentMethodViewSet

router = DefaultRouter()
router.register("sessions", SessionViewSet, basename="session")
router.register("children", ChildViewSet, basename="child")
router.register("plans", PlanViewSet, basename="plan")
router.register("payment-methods", PaymentMethodViewSet, basename="paymentmethod")

urlpatterns = [
    path("", include(router.urls)),
]
