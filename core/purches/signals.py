import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Approval, PurchaseOrder, PurchaseRequest

logger = logging.getLogger(__name__)


@receiver(post_save, sender=PurchaseRequest)
def create_po_on_approved(sender, instance, created, **kwargs):
    if created:
        return

    approved_value = getattr(PurchaseRequest.Status, "APPROVED", "APPROVED")
    if getattr(instance, "status", None) != approved_value:
        return

    if getattr(instance, "purchase_order_id", None):
        return

    approval = (
        Approval.objects.filter(
            purchase_request=instance, decision=Approval.Decision.APPROVED
        )
        .order_by("-created_at")
        .first()
    )
    if not approval:
        return

    required_levels = int(getattr(instance, "required_approval_levels", 2) or 2)
    if getattr(approval, "level", None) != required_levels:
        return

    if PurchaseOrder.objects.filter(data__purchase_request_id=instance.id).exists():
        return

    try:
        from core.purches.po import create_purchase_order_for_request

        po = create_purchase_order_for_request(
            instance, created_by=getattr(approval, "approver", None)
        )
        if po:
            try:
                instance.purchase_order = po
                instance.save(update_fields=["purchase_order"])
            except Exception:
                pass
    except Exception as exc:
        logger.exception(
            "Failed to create PO for PR %s after final approval: %s",
            getattr(instance, "id", None),
            exc,
        )
