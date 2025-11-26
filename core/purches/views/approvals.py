from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.purches.models import Approval, PurchaseRequest
from core.purches.serializers import purchase_request as purchase_request_serializer

from .approvals_receipts import (
    ApprovedReceiptsView,
    ReceiptDetailView,
    ReceiptListView,
    RequestReceiptsView,
)

__all__ = [
    "MyApprovedRequestsView",
    "MyRejectedRequestsView",
    "ApprovedReceiptsView",
    "ReceiptListView",
    "ReceiptDetailView",
    "RequestReceiptsView",
]


def _build_approver_name(approval):
    approver = getattr(approval, "approver", None)
    if not approver:
        return None
    first = getattr(approver, "first_name", "")
    last = getattr(approver, "last_name", "")
    return " ".join(n for n in (first, last) if n).strip()


def _is_pr_rejected(pr):
    return getattr(pr, "status", None) == getattr(
        PurchaseRequest.Status, "REJECTED", "REJECTED"
    )


class MyApprovedRequestsView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Requests"],
        security=[{"Bearer": []}],
        responses={200: "OK"},
    )
    def get(self, request):
        user = request.user
        qs = Approval.objects.filter(
            approver=user, decision=Approval.Decision.APPROVED
        ).select_related("purchase_request")
        data = []
        for a in qs:
            pr = getattr(a, "purchase_request", None)
            if pr is not None:
                ser = purchase_request_serializer.PurchaseRequestSerializer(
                    pr, context={"request": request}
                )
                pr_data = ser.data
            else:
                pr_data = None
            data.append(
                {
                    "approval_id": getattr(a, "id", None),
                    "purchase_request_id": (
                        getattr(pr, "id", None) if pr is not None else None
                    ),
                    "level": getattr(a, "level", None),
                    "approved_at": getattr(a, "created_at", None),
                    "purchase_request_status": (
                        getattr(pr, "status", None) if pr is not None else None
                    ),
                    "purchase_request": pr_data,
                }
            )
        return Response({"approved_requests": data}, status=status.HTTP_200_OK)


class MyRejectedRequestsView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Requests"],
        security=[{"Bearer": []}],
        responses={200: "OK"},
    )
    def get(self, request):
        user = request.user
        qs = (
            Approval.objects.filter(approver=user, decision=Approval.Decision.REJECTED)
            .select_related("purchase_request", "approver")
            .order_by("-created_at")
        )
        data = []
        for a in qs:
            pr = a.purchase_request
            if pr is not None:
                ser = purchase_request_serializer.PurchaseRequestSerializer(
                    pr, context={"request": request}
                )
                pr_data = ser.data
            else:
                pr_data = None

            data.append(
                {
                    "id": a.id,
                    "level": a.level,
                    "decision": a.decision,
                    "comment": a.comment,
                    "created_at": a.created_at,
                    "approver_id": a.approver_id,
                    "purchase_request_id": a.purchase_request_id,
                    "approver_name": _build_approver_name(a),
                    "purchase_request": pr_data,
                    "purchase_request_rejected": _is_pr_rejected(pr),
                }
            )

        return Response({"rejected_requests": data}, status=status.HTTP_200_OK)
