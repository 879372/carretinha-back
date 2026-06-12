from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.routers import DefaultRouter
from sessions_app.views import CompanyViewSet

router = DefaultRouter()
router.register("companies", CompanyViewSet, basename="company")

urlpatterns = [
    path("admin/", admin.site.urls),

    # Auth
    path("api/auth/login/", TokenObtainPairView.as_view(), name="token_obtain"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # API global (e.g. companies)
    path("api/", include(router.urls)),

    # Apps por empresa
    path("api/companies/<uuid:company_id>/", include("sessions_app.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
