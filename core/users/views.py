from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import get_object_or_404, render
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.generic import TemplateView
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status
from rest_framework.exceptions import AuthenticationFailed, NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import CustomRegisterSerializer

User = get_user_model()


class CustomRegisterView(generics.CreateAPIView):
    serializer_class = CustomRegisterSerializer
    permission_classes = [AllowAny]

    def create_jwt(self, user):
        refresh = RefreshToken.for_user(user)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}

    def send_verification_email(self, request, user):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        path = reverse("users:verify-landing", kwargs={"uidb64": uid, "token": token})
        activation_link = request.build_absolute_uri(path)

        subject = "Verify your email"
        context = {"user": user, "activation_link": activation_link}

        try:
            text_message = render_to_string("users/verification_email.txt", context)
        except TemplateDoesNotExist:
            text_message = (
                f"Hello {user.first_name or user.email},\n\n"
                "Please click the link below to verify your email address and "
                "activate your account:\n\n"
                f"{activation_link}\n\n"
                "If you didn't request this, please ignore this email."
            )

        try:
            html_message = render_to_string("users/verification_email.html", context)
        except TemplateDoesNotExist:
            html_message = text_message.replace("\n", "<br>")

        from_email = (
            getattr(settings, "DEFAULT_FROM_EMAIL", None)
            or settings.EMAIL_HOST_USER
            or "no-reply@example.com"
        )
        to = [user.email]

        msg = EmailMultiAlternatives(subject, text_message, from_email, to)
        msg.attach_alternative(html_message, "text/html")
        msg.send(fail_silently=False)

    @swagger_auto_schema(request_body=CustomRegisterSerializer)
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # check email existence and return 409 Conflict if already taken
        email = (serializer.validated_data.get("email") or "").strip()
        if User.objects.filter(email__iexact=email).exists():
            return Response(
                {"email": ["A user with that email already exists."]},
                status=status.HTTP_409_CONFLICT,
            )

        user = serializer.save()

        user.is_active = False
        user.save(update_fields=["is_active"])

        try:
            self.send_verification_email(request, user)
        except Exception:
            return Response(
                {
                    "detail": (
                        "Registration created but verification email failed to send."
                    ),
                    "user_id": getattr(user, "id", None),
                    "email": getattr(user, "email", None),
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {
                "detail": "Registration successful. Check your email for "
                "verification link.",
                "user_id": getattr(user, "id", None),
                "email": getattr(user, "email", None),
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, uidb64, token, *args, **kwargs):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = get_object_or_404(User, pk=uid)
        except Exception:
            return render(
                request,
                "users/verification_failed.html",
                {"reason": "Invalid activation link."},
                status=400,
            )

        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save(update_fields=["is_active"])
            return render(request, "users/verification_success.html", {"user": user})
        return render(
            request,
            "users/verification_failed.html",
            {"reason": "Invalid or expired token."},
            status=400,
        )


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        identifier_field = getattr(self, "username_field", "username")
        identifier = (
            attrs.get(identifier_field) or attrs.get("email") or attrs.get("username")
        )

        user = None
        if identifier:
            try:
                user = User.objects.get(**{identifier_field: identifier})
            except User.DoesNotExist:
                if identifier_field != "email":
                    try:
                        user = User.objects.get(email=identifier)
                    except User.DoesNotExist:
                        user = None

        if user is not None and not getattr(user, "is_active", True):
            raise AuthenticationFailed(
                "Email not verified. Please verify your email before logging in."
            )

        data = super().validate(attrs)
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class VerifyLandingView(TemplateView):
    template_name = "users/verification_landing.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        uidb64 = self.kwargs.get("uidb64")
        token = self.kwargs.get("token")
        # build activation url that will perform verification
        activation_path = reverse(
            "users:verify-email",
            kwargs={"uidb64": uidb64, "token": token},
        )
        context["activation_link"] = self.request.build_absolute_uri(activation_path)
        context["user_email"] = None
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.filter(pk=uid).first()
            if user:
                context["user_email"] = user.email
        except Exception:
            context["user_email"] = None
        return context


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            {
                "id": getattr(user, "id", None),
                "email": getattr(user, "email", None),
                "first_name": getattr(user, "first_name", None),
                "last_name": getattr(user, "last_name", None),
                "role": getattr(user, "role", None),
                "is_superuser": getattr(user, "is_superuser", False),
                "is_staff": getattr(user, "is_staff", False),
            }
        )


class PublicUserDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            raise NotFound(detail="User not found")

        return Response(
            {
                "id": user.id,
                "first_name": getattr(user, "first_name", None),
                "last_name": getattr(user, "last_name", None),
                "role": getattr(user, "role", None),
                "is_active": getattr(user, "is_active", False),
            }
        )


UserDetailView = PublicUserDetailView
