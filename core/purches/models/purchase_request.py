from django.conf import settings
from django.db import models
from django.utils import timezone


class PurchaseRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        APPROVED = "APPROVED"
        REJECTED = "REJECTED"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="purchase_requests",
        on_delete=models.CASCADE,
    )
    required_approval_levels = models.IntegerField(default=2)
    current_approval_level = models.IntegerField(default=1, null=True, blank=True)
    proforma = models.FileField(upload_to="proformas/", null=True, blank=True)
    purchase_order = models.OneToOneField(
        "purches.PurchaseOrder", null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.status})"
