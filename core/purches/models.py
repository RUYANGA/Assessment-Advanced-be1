from django.db import models


class PurchaseRequest(models.Model):
    # Fields for PurchaseRequest
    pass


class PurchaseOrder(models.Model):
    # ...existing fields...
    purchase_request = models.ForeignKey(
        PurchaseRequest,
        null=True,
        blank=True,
        on_delete=models.CASCADE,  # cascade delete when PR is removed
        related_name="purchase_orders",
    )
    # ...existing code...
