import logging
from decimal import Decimal

from rest_framework import serializers

from core.purches.models import PurchaseRequest, RequestItem

from .request_item import RequestItemSerializer

logger = logging.getLogger(__name__)


class PurchaseRequestSerializer(serializers.ModelSerializer):
    items = RequestItemSerializer(many=True, required=False)

    class Meta:
        model = PurchaseRequest
        fields = (
            "id",
            "title",
            "description",
            "total_amount",
            "items",
            "required_approval_levels",
            "status",
            "created_at",
        )
        read_only_fields = (
            "id",
            "total_amount",
            "status",
            "created_at",
        )

    def _recalc_total(self, pr):
        total = 0
        for it in pr.items.all():
            qty = getattr(it, "quantity", 1) or 1
            unit = getattr(it, "unit_price", 0) or 0
            total += qty * unit
        pr.total_amount = total
        pr.save(update_fields=["total_amount"])

    def create(self, validated_data):
        items = validated_data.pop("items", [])
        # ensure DB non-null constraint is satisfied
        # total will be recalculated after items are created
        validated_data.setdefault("total_amount", Decimal("0.00"))
        pr = super().create(validated_data)
        for it in items:
            RequestItem.objects.create(purchase_request=pr, **it)
        self._recalc_total(pr)
        return pr

    def update(self, instance, validated_data):
        items = validated_data.pop("items", None)
        pr = super().update(instance, validated_data)
        if items is not None:
            # simple strategy: remove existing and recreate (or implement diff)
            pr.items.all().delete()
            for it in items:
                RequestItem.objects.create(purchase_request=pr, **it)
            self._recalc_total(pr)
        return pr

    def some_method_that_might_fail(self):
        try:
            # placeholder for logic; keep 'pass' so the try block is syntactically valid
            pass
        except Exception as exc:
            logger.exception("purchase_request handling failed: %s", exc)


# backward-compatible alias used by views
PurchaseRequestDetailSerializer = PurchaseRequestSerializer
