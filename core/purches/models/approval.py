from django.conf import settings
from django.db import models
from django.utils import timezone


class Approval(models.Model):
    class Decision(models.TextChoices):
        APPROVED = "APPROVED"
        REJECTED = "REJECTED"

    purchase_request = models.ForeignKey(
        "purches.PurchaseRequest", related_name="approvals", on_delete=models.CASCADE
    )
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    level = models.PositiveSmallIntegerField()
    decision = models.CharField(max_length=10, choices=Decision.choices)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("purchase_request", "approver", "level")
