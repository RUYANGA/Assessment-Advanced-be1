from django.urls import path

from .views import CustomRegisterView, VerifyEmailView, VerifyLandingView

app_name = "users"

urlpatterns = [
    path("register/", CustomRegisterView.as_view(), name="register"),
    # landing page with a button the user clicks to confirm
    path(
        "verify/<str:uidb64>/<str:token>/",
        VerifyLandingView.as_view(),
        name="verify-landing",
    ),
    # actual activation endpoint
    path(
        "verify-email/<str:uidb64>/<str:token>/",
        VerifyEmailView.as_view(),
        name="verify-email",
    ),
]
