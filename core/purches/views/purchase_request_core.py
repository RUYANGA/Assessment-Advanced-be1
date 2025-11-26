import logging

from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.purches import services as prs_services
from core.purches.models import PurchaseRequest, Receipt
from core.purches.serializers.purchase_request import (
    PurchaseRequestDetailSerializer,
    PurchaseRequestSerializer,
)
from core.purches.serializers.receipt import ReceiptSerializer, ReceiptUploadSerializer
from core.purches.utils import user_is_role

logger = logging.getLogger(__name__)


class PurchaseRequestViewSet(viewsets.ModelViewSet):
    queryset = PurchaseRequest.objects.all().select_related(
        "created_by", "purchase_order"
    )
    serializer_class = PurchaseRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if getattr(self, "action", None) == "retrieve":
            return PurchaseRequestDetailSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        user = self.request.user
        qs = self.queryset
        role = (getattr(user, "role", "") or "").lower()
        if role == "staff":
            return qs.filter(created_by=user).order_by("-created_at")
        if role in ("approver1", "approver2"):
            return qs.filter(status=PurchaseRequest.Status.PENDING).order_by(
                "-created_at"
            )
        if role == "finance":
            return qs.filter(status=PurchaseRequest.Status.APPROVED).order_by(
                "-created_at"
            )
        if user.is_superuser:
            return qs.order_by("-created_at")
        return qs.none()

    def perform_create(self, serializer):
        pending_value = getattr(PurchaseRequest.Status, "PENDING", "PENDING")
        serializer.save(created_by=self.request.user, status=pending_value)

    def perform_update(self, serializer):
        pr = self.get_object()
        if not (
            self.request.user == getattr(pr, "created_by", None)
            or self.request.user.is_superuser
        ):
            raise ValidationError(
                "Only the request creator may update this purchase request."
            )
        pending_value = getattr(PurchaseRequest.Status, "PENDING", "PENDING")
        if getattr(pr, "status", None) != pending_value:
            raise ValidationError({"status": "Only PENDING requests may be updated."})
        serializer.save()

    @swagger_auto_schema(tags=["Requests"], security=[{"Bearer": []}])
    @action(detail=True, methods=["patch"])
    def approve(self, request, pk=None):
        user = request.user
        # determine role/level (roles are stored in lowercase)
        required_roles = ("approver1", "approver2", "finance")
        user_level = next((r for r in required_roles if user_is_role(user, r)), None)
        if not user_level:
            return Response({"error": "insufficient_role"}, status=403)
        role_map = {"approver1": 1, "approver2": 2, "finance": 3}
        level_value = role_map.get(user_level)

        pr = prs_services.get_purchase_request_for_action(self, pk)
        self.check_object_permissions(request, pr)

        try:
            payload, status_code = prs_services.approve_purchase_request(
                user, pr, level_value
            )
            return Response(payload, status=status_code)
        except Exception:
            logger.exception(
                "approve view failed for pr=%s user=%s level=%s",
                getattr(pr, "id", None),
                getattr(user, "id", None),
                level_value,
            )
            return Response(
                {"detail": "server_error", "error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @swagger_auto_schema(tags=["Requests"], security=[{"Bearer": []}])
    @action(detail=True, methods=["patch"])
    def reject(self, request, pk=None):
        user = request.user
        # roles are stored in lowercase; check for any approver/finance role
        if not any(
            user_is_role(user, r) for r in ("approver1", "approver2", "finance")
        ):
            return Response({"detail": "insufficient_role"}, status=403)
        pr = get_object_or_404(PurchaseRequest, pk=pk)
        payload, status_code = prs_services.reject_purchase_request(user, pr)
        return Response(payload, status=status_code)

    @swagger_auto_schema(tags=["Requests"], security=[{"Bearer": []}])
    @action(detail=True, methods=["post"], url_path="submit-receipt")
    def submit_receipt(self, request, pk=None):
        pr = prs_services.get_purchase_request_for_action(self, pk)
        serializer = ReceiptUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file_url = serializer.validated_data["file_url"]
        vendor = serializer.validated_data.get("vendor")
        note = serializer.validated_data.get("note")

        receipt = Receipt.objects.create(
            purchase_request=pr,
            file_url=file_url,
            vendor=vendor,
            note=note,
            uploaded_by=request.user,
        )

        out = ReceiptSerializer(receipt, context={"request": request}).data
        return Response(out, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(tags=["Requests"], security=[{"Bearer": []}])
    @action(detail=False, methods=["get"], url_path="pending")
    def pending(self, request):
        user = request.user
        if not any(
            user_is_role(user, r) for r in ("approver1", "approver2", "finance")
        ):
            return Response({"detail": "insufficient_role"}, status=403)

        role_map = {"approver1": 1, "approver2": 2, "finance": 3}
        user_role = next((r for r in role_map if user_is_role(user, r)), None)
        level_value = role_map.get(user_role) if user_role else None

        qs = self.queryset.filter(status=PurchaseRequest.Status.PENDING).order_by(
            "-created_at"
        )
        if level_value is not None and hasattr(
            PurchaseRequest, "current_approval_level"
        ):
            qs = qs.filter(current_approval_level=level_value)
        qs = qs.exclude(approvals__approver=user).distinct()

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data, status=200)

    @swagger_auto_schema(tags=["Requests"], security=[{"Bearer": []}])
    @action(detail=True, methods=["get"], url_path="approvals")
    def approvals(self, request, pk=None):
        pr = get_object_or_404(PurchaseRequest, pk=pk)
        self.check_object_permissions(request, pr)

        pr_data = PurchaseRequestSerializer(pr, context={"request": request}).data

        qs = pr.approvals.all().select_related("approver")
        result = []
        for a in qs:
            approver = getattr(a, "approver", None)
            approver_name = None
            if approver is not None:
                first = getattr(approver, "first_name", "") or ""
                last = getattr(approver, "last_name", "") or ""
                username = getattr(approver, "username", None)
                approver_name = f"{first} {last}".strip() or username

            result.append(
                {
                    "id": getattr(a, "id", None),
                    "level": getattr(a, "level", None),
                    "decision": getattr(a, "decision", None),
                    "comment": getattr(a, "comment", None),
                    "created_at": getattr(a, "created_at", None),
                    "approver_id": getattr(
                        a, "approver_id", getattr(approver, "id", None)
                    ),
                    "purchase_request_id": getattr(
                        a, "purchase_request_id", getattr(pr, "id", None)
                    ),
                    "approver_name": approver_name,
                    "purchase_request": pr_data,
                }
            )

        return Response({"approvals": result}, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        user = request.user
        pr = self.get_object()
        approved_value = getattr(pr.__class__.Status, "APPROVED", "APPROVED")

        if getattr(pr, "status", None) == approved_value:
            if not user_is_role(user, "finance"):
                return Response(
                    {"detail": "insufficient_role_to_delete_approved_request"},
                    status=status.HTTP_403_FORBIDDEN,
                )

        return super().destroy(request, *args, **kwargs)
