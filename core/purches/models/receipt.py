from django.contrib.auth import get_user_model
from django.db import models

from core.purches.models import PurchaseRequest

User = get_user_model()


class Receipt(models.Model):
    file_url = models.URLField(
        max_length=500, blank=True, null=True
    )  # <-- allow blank/null for migration
    vendor = models.CharField(max_length=255, blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    purchase_request = models.ForeignKey(
        PurchaseRequest, on_delete=models.CASCADE, related_name="receipts"
    )
    uploaded_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="uploaded_receipts"
    )

    def __str__(self):
        return f"Receipt {self.id} for PR {self.purchase_request_id}"
