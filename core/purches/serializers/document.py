from rest_framework import serializers


class ProformaUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    auto_create_po = serializers.BooleanField(required=False, default=False)
