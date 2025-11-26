from rest_framework import serializers


class ApprovalActionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[("APPROVED", "Approved"), ("REJECTED", "Rejected")]
    )
