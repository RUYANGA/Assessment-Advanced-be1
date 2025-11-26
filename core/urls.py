from django.contrib import admin
from django.urls import include, path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework_simplejwt.views import TokenRefreshView

from core.users.auth_views import EmailTokenObtainPairView
from core.users.views import MeView, PublicUserDetailView, UserDetailView

schema_view = get_schema_view(
    openapi.Info(
        title="Assessment Advanced — Backend API",
        default_version="v1",
        description=(
            "REST API for the Assessment Advanced backend. "
            "Provides endpoints for authentication, user management, "
            "purchases and administration. Use the interactive "
            "documentation to explore available endpoints and scopes."
        ),
        terms_of_service="https://github.com/RUYANGA",
        contact=openapi.Contact(
            email="ruyangam15@gmail.com",
            url="https://assessment-advanced-fe.vercel.app",
        ),
        license=openapi.License(
            name="MIT License",
            url="https://opensource.org/licenses/MIT",
        ),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/me/", MeView.as_view(), name="me"),
    path("api/users/<int:pk>/", UserDetailView.as_view(), name="user-detail"),
    path("api/auth/", include("core.users.urls")),
    path(
        "api/users/public/<int:pk>/",
        PublicUserDetailView.as_view(),
        name="public-user-detail",
    ),
    path(
        "api/auth/token/", EmailTokenObtainPairView.as_view(), name="token_obtain_pair"
    ),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include("core.purches.urls")),
    # Swagger / OpenAPI
    re_path(
        r"^swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]
