from rest_framework.exceptions import APIException, AuthenticationFailed
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .auth_serializers import EmailTokenObtainPairSerializer


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except AuthenticationFailed:
            # return a clear, consistent message for wrong credentials
            return Response(
                {
                    "detail": "Email or password incorrect",
                    "code": "authentication_failed",
                },
                status=401,
            )
        except APIException as exc:
            status_code = getattr(exc, "status_code", 400)
            data = {
                "detail": str(exc),
                "code": getattr(exc, "default_code", ""),
            }
            if getattr(exc, "default_code", "") == "email_not_verified":
                data["verification_required"] = True
                data["message"] = (
                    "Email address is not verified. Please check your email for "
                    "a confirmation link before logging in."
                )
            return Response(data, status=status_code)
