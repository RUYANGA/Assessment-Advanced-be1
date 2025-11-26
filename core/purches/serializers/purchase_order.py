from django.contrib.auth import get_user_model
from rest_framework import serializers

from core.purches.models import Approval, PurchaseOrder

from .purchase_order_utils import approver_from_embedded, extract_pr_id_from_data

User = get_user_model()


class PurchaseOrderSerializer(serializers.ModelSerializer):
    approver = serializers.SerializerMethodField(read_only=True)
    # purchase_request removed to avoid embedding the full PR in PO responses

    class Meta:
        model = PurchaseOrder
        fields = ("id", "po_number", "data", "generated_at", "approver")
        read_only_fields = ("id", "generated_at", "po_number", "approver")

    def get_approver(self, obj):
        pr_id = None
        try:
            pr_id = extract_pr_id_from_data(obj.data or {})
        except Exception:
            pr_id = None

        if pr_id:
            approval = (
                Approval.objects.filter(
                    purchase_request_id=pr_id,
                    decision=Approval.Decision.APPROVED,
                    level=2,
                )
                .order_by("-created_at")
                .first()
            )
            if not approval:
                approval = (
                    Approval.objects.filter(
                        purchase_request_id=pr_id,
                        decision=Approval.Decision.APPROVED,
                    )
                    .order_by("-created_at")
                    .first()
                )
            if approval and getattr(approval, "approver", None):
                approver = approval.approver
                first = getattr(approver, "first_name", "")
                last = getattr(approver, "last_name", "")
                full_name = " ".join(n for n in (first, last) if n).strip()
                return {
                    "id": getattr(approver, "id", None),
                    "first_name": first,
                    "last_name": last,
                    "full_name": full_name,
                }

        try:
            approver_user = approver_from_embedded(obj.data or {})
            if approver_user:
                first = getattr(approver_user, "first_name", "")
                last = getattr(approver_user, "last_name", "")
                full_name = " ".join(n for n in (first, last) if n).strip()
                return {
                    "id": getattr(approver_user, "id", None),
                    "first_name": first,
                    "last_name": last,
                    "full_name": full_name,
                }
        except Exception:
            pass

        return None
