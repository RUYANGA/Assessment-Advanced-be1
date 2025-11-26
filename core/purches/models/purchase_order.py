from django.db import models
from django.utils import timezone


class PurchaseOrder(models.Model):
    po_number = models.CharField(max_length=80, unique=True)
    data = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.po_number
