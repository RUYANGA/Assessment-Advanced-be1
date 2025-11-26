from rest_framework import serializers
from core.purches.models import Approval


class MyApprovalSerializer(serializers.ModelSerializer):
    purchase_request = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Approval
        fields = ("id", "purchase_request", "level", "decision", "comment", "created_at")
        read_only_fields = fields

    def get_purchase_request(self, obj):
        pr = getattr(obj, "purchase_request", None)
        if not pr:
            return None
        return {
            "id": getattr(pr, "id", None),
            "status": getattr(pr, "status", None),
            "required_approvers": getattr(pr, "required_approvers", None),
            "data": getattr(pr, "data", None),
        }