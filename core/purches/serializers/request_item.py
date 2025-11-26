from rest_framework import serializers

from core.purches.models import RequestItem


class RequestItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestItem
        fields = ("id", "name", "quantity", "unit_price")
        read_only_fields = ("id",)
