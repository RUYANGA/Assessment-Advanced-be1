from rest_framework import serializers

from core.purches.models import Receipt


class ReceiptUploadSerializer(serializers.Serializer):
    file_url = serializers.URLField(
        required=True, allow_blank=False
    )  # must not be blank
    vendor = serializers.CharField(required=False, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True)


class ReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Receipt
        fields = (
            "id",
            "file_url",
            "vendor",
            "note",
            "uploaded_at",
            "uploaded_by",
            "purchase_request",
        )
