import logging

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.crypto import get_random_string

from core.purches.models import PurchaseOrder, PurchaseRequest

logger = logging.getLogger(__name__)


def _generate_po_number(pr: PurchaseRequest | None = None) -> str:
    ts = timezone.now().strftime("%Y%m%d%H%M%S")
    base = f"PO-{ts}"
    if pr is not None and getattr(pr, "id", None) is not None:
        base = f"PO-{pr.id}-{ts}"
    rand = get_random_string(6).upper()
    return f"{base}-{rand}"


def _serialize_pr(pr: PurchaseRequest) -> dict:
    data = {
        "purchase_request_id": getattr(pr, "id", None),
        "title": getattr(pr, "title", None),
        "description": getattr(pr, "description", None),
        "total_amount": (
            str(getattr(pr, "total_amount", None))
            if getattr(pr, "total_amount", None) is not None
            else None
        ),
        "created_at": (
            getattr(pr, "created_at", None).isoformat()
            if getattr(pr, "created_at", None)
            else None
        ),
        "items": [],
    }

    # gather items from explicit manager or any one-to-many relation
    qs = None
    if hasattr(pr, "items"):
        qs = pr.items.all()
    else:
        for f in pr._meta.get_fields():
            if getattr(f, "one_to_many", False) and f.auto_created:
                mgr = getattr(pr, f.get_accessor_name(), None)
                if mgr is None:
                    continue
                try:
                    cand = mgr.all()
                except Exception:
                    continue
                if cand.exists():
                    qs = cand
                    break

    if qs is not None:
        for it in qs:
            data["items"].append(
                {
                    "name": getattr(it, "name", None)
                    or getattr(it, "description", None),
                    "quantity": getattr(it, "quantity", None),
                    "unit_price": (
                        str(getattr(it, "unit_price", None))
                        if getattr(it, "unit_price", None) is not None
                        else None
                    ),
                }
            )

    return data


def create_purchase_order_for_request(
    pr: PurchaseRequest, created_by=None
) -> PurchaseOrder:
    """
    Create and return a PurchaseOrder for the given PurchaseRequest.
    Always returns the created PurchaseOrder or raises.
    """
    logger.debug(
        "create_purchase_order_for_request called for pr=%s by=%s",
        getattr(pr, "id", None),
        getattr(created_by, "id", None),
    )
    data = _serialize_pr(pr)

    # embed approver info into data (like title) when available
    approver_user = None
    if created_by is not None:
        approver_user = created_by
    else:
        # fallback: try to read latest APPROVED approval for this PR
        try:
            from core.purches.models import Approval

            approval = (
                Approval.objects.filter(
                    purchase_request=pr, decision=Approval.Decision.APPROVED
                )
                .order_by("-level", "-created_at")
                .first()
            )
            if approval:
                approver_user = getattr(approval, "approver", None)
        except Exception:
            approver_user = None

    if approver_user:
        approver_info = {
            "id": getattr(approver_user, "id", None),
            "first_name": getattr(approver_user, "first_name", "") or "",
            "last_name": getattr(approver_user, "last_name", "") or "",
        }
        approver_info["full_name"] = (
            f"{approver_info['first_name']} {approver_info['last_name']}".strip()
        )
        data["approver"] = approver_info

    # try multiple times to avoid po_number collision
    last_exc = None
    for _ in range(5):
        po_number = _generate_po_number(pr)
        try:
            with transaction.atomic():
                # try to attach FK if model has purchase_request field
                try:
                    po = PurchaseOrder.objects.create(
                        po_number=po_number,
                        data=data,
                        generated_at=timezone.now(),
                        purchase_request=pr,
                    )
                except TypeError:
                    po = PurchaseOrder.objects.create(
                        po_number=po_number,
                        data=data,
                        generated_at=timezone.now(),
                    )
                logger.info(
                    "PurchaseOrder created id=%s po_number=%s for pr=%s",
                    po.id,
                    po.po_number,
                    getattr(pr, "id", None),
                )
                return po
        except IntegrityError as e:
            logger.warning(
                "PO number collision retrying po_number=%s (%s)", po_number, e
            )
            last_exc = e
        except Exception as e:
            logger.exception(
                "Unexpected error creating PO for pr=%s: %s", getattr(pr, "id", None), e
            )
            last_exc = e
            break

    if last_exc:
        logger.error(
            "Failed to create PurchaseOrder for pr=%s after retries: %s",
            getattr(pr, "id", None),
            last_exc,
        )
        raise last_exc

    raise RuntimeError("Failed to create PurchaseOrder for unknown reason")
