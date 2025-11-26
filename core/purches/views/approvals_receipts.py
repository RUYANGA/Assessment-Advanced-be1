from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.purches.models import PurchaseRequest, Receipt
from core.purches.serializers import receipt as receipt_serializer
from core.purches.utils import user_is_role


class ApprovedReceiptsView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Receipts"], security=[{"Bearer": []}], responses={200: "OK"}
    )
    def get(self, request):
        user = request.user
        qs = (
            Receipt.objects.filter(
                purchase_request__status=PurchaseRequest.Status.APPROVED
            )
            .select_related("purchase_request", "uploaded_by")
            .order_by("-uploaded_at")
        )

        is_privileged = (
            user.is_staff or user.is_superuser or user_is_role(user, "finance")
        )
        if not is_privileged:
            qs = qs.filter(Q(uploaded_by=user) | Q(purchase_request__created_by=user))

        serializer = receipt_serializer.ReceiptSerializer(
            qs, many=True, context={"request": request}
        )
        return Response(
            {"approved_receipts": serializer.data}, status=status.HTTP_200_OK
        )


class ReceiptListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Receipts"], security=[{"Bearer": []}], responses={200: "OK"}
    )
    def get(self, request):
        user = request.user
        qs = Receipt.objects.select_related(
            "uploaded_by", "purchase_request__created_by"
        ).order_by("-uploaded_at")

        is_privileged = (
            user.is_staff or user.is_superuser or user_is_role(user, "finance")
        )
        if not is_privileged:
            qs = qs.filter(Q(uploaded_by=user) | Q(purchase_request__created_by=user))

        serializer = receipt_serializer.ReceiptSerializer(
            qs, many=True, context={"request": request}
        )
        return Response({"receipts": serializer.data}, status=status.HTTP_200_OK)


class ReceiptDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Receipts"],
        security=[{"Bearer": []}],
        responses={200: "OK", 403: "Forbidden", 404: "Not Found"},
    )
    def get(self, request, pk):
        user = request.user
        qs = Receipt.objects.select_related(
            "uploaded_by", "purchase_request__created_by"
        )
        receipt = get_object_or_404(qs, pk=pk)

        pr_owner_id = getattr(receipt.purchase_request, "created_by_id", None)
        uploader_id = getattr(receipt, "uploaded_by_id", None)

        is_privileged = (
            user.is_staff or user.is_superuser or user_is_role(user, "finance")
        )
        if not (
            is_privileged
            or uploader_id == getattr(user, "id", None)
            or pr_owner_id == getattr(user, "id", None)
        ):
            return Response({"detail": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

        out = receipt_serializer.ReceiptSerializer(
            receipt, context={"request": request}
        ).data
        return Response(out, status=status.HTTP_200_OK)


class RequestReceiptsView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Receipts"], security=[{"Bearer": []}], responses={200: "OK"}
    )
    def get(self, request, pk):
        pr = get_object_or_404(PurchaseRequest, pk=pk)
        receipts = (
            Receipt.objects.filter(purchase_request=pr)
            .select_related("uploaded_by")
            .order_by("-uploaded_at")
        )

        serializer = receipt_serializer.ReceiptSerializer(
            receipts, many=True, context={"request": request}
        )
        return Response({"receipts": serializer.data}, status=status.HTTP_200_OK)
