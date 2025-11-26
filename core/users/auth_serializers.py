from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "email"

    def validate(self, attrs):
        request = self.context.get("request")
        username = attrs.get("email") or attrs.get("username")
        password = attrs.get("password")

        user = authenticate(request=request, username=username, password=password)
        if user is None:
            raise AuthenticationFailed("Email or password incorrect")

        if not getattr(user, "is_active", False):
            raise AuthenticationFailed(
                "Account is inactive. Please verify your email or contact support."
            )

        return super().validate({self.username_field: username, "password": password})
