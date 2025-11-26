import logging
import re
from decimal import Decimal

import pdfplumber
import pytesseract
from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import IntegrityError
from django.db import models as django_models
from django.db import transaction
from PIL import Image
from rest_framework import status
from rest_framework.exceptions import NotFound

from core.purches.models import Approval, PurchaseOrder, PurchaseRequest

from .po import create_purchase_order_for_request

logger = logging.getLogger(__name__)


def get_purchase_request_for_action(view, lookup_value):
    lookup_field = getattr(view, "lookup_field", "pk")
    try:
        return PurchaseRequest.objects.get(**{lookup_field: lookup_value})
    except PurchaseRequest.DoesNotExist:
        raise NotFound(detail="No PurchaseRequest matches the given query.")


def approve_purchase_request(
    user, pr: PurchaseRequest, level: int, comment: str = None
):
    po = None
    current_level = getattr(pr, "current_approval_level", 1)
    msg = (
        "approve_purchase_request called: pr=%s user=%s role=%s "
        "level=%s current_level=%s"
    )
    logger.info(
        msg,
        getattr(pr, "id", None),
        getattr(user, "id", None),
        getattr(user, "role", None),
        level,
        current_level,
    )

    PENDING = getattr(PurchaseRequest.Status, "PENDING", "PENDING")
    APPROVED = getattr(PurchaseRequest.Status, "APPROVED", "APPROVED")

    if getattr(pr, "status", None) != PENDING:
        return (
            {"detail": "only_pending_requests_can_be_approved"},
            status.HTTP_400_BAD_REQUEST,
        )

    required_levels = int(getattr(pr, "required_approval_levels", 2) or 2)
    if current_level is None:
        return ({"detail": "approval_already_finalized"}, status.HTTP_400_BAD_REQUEST)

    if int(level) != int(current_level):
        return (
            {
                "detail": "not_your_turn",
                "expected_level": current_level,
                "your_level": level,
            },
            status.HTTP_403_FORBIDDEN,
        )

    if Approval.objects.filter(
        purchase_request=pr,
        level=level,
        approver=user,
        decision=Approval.Decision.APPROVED,
    ).exists():
        return ({"detail": "already_approved_by_you"}, status.HTTP_400_BAD_REQUEST)

    try:
        with transaction.atomic():
            Approval.objects.create(
                purchase_request=pr,
                approver=user,
                level=level,
                decision=Approval.Decision.APPROVED,
                comment=comment or "",
            )

            is_final = int(level) == int(required_levels)
            logger.debug(
                "PR=%s required=%s current=%s acting=%s is_final=%s",
                getattr(pr, "id", None),
                required_levels,
                current_level,
                level,
                is_final,
            )
            if is_final:
                pr.status = APPROVED
                pr.current_approval_level = None

                if not getattr(pr, "purchase_order_id", None):
                    try:
                        try:
                            po = create_purchase_order_for_request(pr, created_by=user)
                        except TypeError:
                            po = create_purchase_order_for_request(pr)
                        if po:
                            try:
                                pr.purchase_order = po
                            except Exception:
                                pass
                    except Exception as po_exc:
                        logger.exception(
                            "create_purchase_order_for_request failed for pr=%s: %s",
                            getattr(pr, "id", None),
                            po_exc,
                        )
            else:
                pr.current_approval_level = int(level) + 1

            update_fields = ["status", "current_approval_level"]
            if po is not None or getattr(pr, "purchase_order_id", None):
                update_fields.append("purchase_order")
            pr.save(update_fields=update_fields)

            approved_levels = (
                Approval.objects.filter(
                    purchase_request=pr, decision=Approval.Decision.APPROVED
                )
                .values_list("level", flat=True)
                .distinct()
            )
            approved_levels_set = {
                int(lvl) for lvl in approved_levels if lvl is not None
            }

            payload = {
                "detail": "approved",
                "purchase_request_id": pr.id,
                "approved_level": level,
                "approved_levels": sorted(list(approved_levels_set)),
                "current_approval_level": pr.current_approval_level,
                "status": pr.status,
                "purchase_request": _serialize_pr_min(pr),
                **(
                    {"purchase_order_id": getattr(po, "id", None)}
                    if po is not None
                    else {}
                ),
            }
            return (payload, status.HTTP_200_OK)

    except Exception as exc:
        logger.exception(
            "approve_purchase_request unexpected error for pr=%s user=%s level=%s",
            getattr(pr, "id", None),
            getattr(user, "id", None),
            level,
        )
        return (
            {"detail": "failed_create_approval", "error": str(exc)},
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    payload = {
        "detail": "approval_recorded",
        "purchase_request_id": pr.id,
        "approved_level": level,
        "approved_levels": sorted(list(approved_levels_set)),
        "status": pr.status,
    }
    return (payload, status.HTTP_200_OK)


def reject_purchase_request(user, pr):
    if pr.status != PurchaseRequest.Status.PENDING:
        return {"detail": "Cannot reject, request not pending"}, 400

    level = getattr(pr, "current_approval_level", None)
    try:
        with transaction.atomic():
            approval, created = Approval.objects.update_or_create(
                purchase_request=pr,
                approver=user,
                level=level,
                defaults={"decision": Approval.Decision.REJECTED},
            )
    except IntegrityError:
        approval = Approval.objects.filter(
            purchase_request=pr, approver=user, level=level
        ).first()
        created = False

    if not created and approval is not None:
        if approval.decision == Approval.Decision.REJECTED:
            return {"detail": "already_rejected"}, 200
        approval.decision = Approval.Decision.REJECTED
        approval.level = level
        approval.save(update_fields=["decision", "level"])

    pr.status = PurchaseRequest.Status.REJECTED
    pr.save(update_fields=["status"])
    return {"detail": "Rejected"}, 200


def submit_receipt_for_request(
    user, pr, uploaded_file, vendor=None, note=None, ReceiptModel=None
):
    if getattr(pr, "created_by", None) != user and not user.is_superuser:
        raise PermissionDenied("Only the request creator may submit receipts.")
    if getattr(pr, "status", None) == getattr(
        PurchaseRequest.Status, "REJECTED", "REJECTED"
    ):
        raise ValueError("Cannot submit a receipt for a rejected request.")

    field_map = {f.name: f for f in ReceiptModel._meta.get_fields()}

    file_field_name = None
    file_field_obj = None
    for candidate in (
        "file",
        "document",
        "attachment",
        "receipt_file",
        "uploaded_file",
    ):
        if candidate in field_map:
            file_field_name = candidate
            file_field_obj = field_map[candidate]
            break

    kwargs = {}

    if file_field_name and isinstance(
        getattr(file_field_obj, "field", file_field_obj), django_models.FileField
    ):
        kwargs[file_field_name] = uploaded_file
    elif file_field_name:
        name = getattr(uploaded_file, "name", "upload")
        content = (
            uploaded_file.read() if hasattr(uploaded_file, "read") else uploaded_file
        )
        saved_path = default_storage.save(f"receipts/{name}", ContentFile(content))
        kwargs[file_field_name] = saved_path

    for fk in ("purchase_request", "purchaserequest", "request"):
        if fk in field_map:
            kwargs[fk] = pr
            break

    if "uploaded_by" in field_map:
        kwargs["uploaded_by"] = user
    elif "uploaded_by_id" in field_map:
        kwargs["uploaded_by_id"] = getattr(user, "id", None)
    elif "created_by" in field_map:
        kwargs["created_by"] = user
    elif "user" in field_map:
        kwargs["user"] = user
    if vendor and "vendor" in field_map:
        kwargs["vendor"] = vendor
    if note and "note" in field_map:
        kwargs["note"] = note

    try:
        with transaction.atomic():
            receipt = ReceiptModel.objects.create(**kwargs)
    except Exception as e:
        raise RuntimeError(f"failed_create_receipt: {e}") from e

    return receipt


def _extract_text_from_pdf_fileobj(file_obj):
    try:
        file_obj.seek(0)
        with pdfplumber.open(file_obj) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            tables = []
            for page in pdf.pages:
                t = page.extract_table()
                if t:
                    tables.append(t)
        return {"text": text, "tables": tables}
    except Exception:
        file_obj.seek(0)
        img = Image.open(file_obj)
        return {"text": pytesseract.image_to_string(img), "tables": []}


def process_proforma_file(file_obj):
    """
    Return a dict with keys:
      vendor, invoice_no, date, total_amount (Decimal), items (list of dicts)
    """
    data = _extract_text_from_pdf_fileobj(file_obj)
    text = data.get("text", "")
    tables = data.get("tables", [])

    extracted = {}

    m = re.search(r"Invoice\s*No[:\s]*([A-Za-z0-9\-\/]+)", text, re.I)
    if m:
        extracted["invoice_no"] = m.group(1).strip()
    m = re.search(r"Total\s*[:\s]*\$?([\d,\.]+)", text, re.I)
    if m:
        extracted["total_amount"] = Decimal(m.group(1).replace(",", ""))

    items = []
    for t in tables:
        headers = [c.strip().lower() if c else "" for c in t[0]]
        for row in t[1:]:
            name = None
            qty = 1
            unit = None
            for idx, h in enumerate(headers):
                cell = row[idx] if idx < len(row) else ""
                if "description" in h or "item" in h or "name" in h:
                    name = cell
                if "qty" in h or "quantity" in h:
                    try:
                        qty = int(cell)
                    except (ValueError, TypeError):
                        qty = 1
                if "price" in h or "unit" in h:
                    try:
                        unit = Decimal(cell.replace(",", "").replace("$", ""))
                    except (ValueError, TypeError):
                        unit = None
            if name:
                items.append({"name": name, "quantity": qty, "unit_price": unit})
        if items:
            break

    extracted.setdefault("items", items)
    extracted.setdefault("vendor", None)
    return extracted


def create_purchase_order_from_proforma(extracted, created_by):
    po = PurchaseOrder.objects.create(
        vendor=extracted.get("vendor") or "Unknown",
        total_amount=extracted.get("total_amount") or 0,
        created_by=created_by,
        raw_data=extracted,
    )
    for it in extracted.get("items", []):
        po.items.create(
            name=it.get("name"),
            quantity=it.get("quantity") or 1,
            unit_price=it.get("unit_price") or 0,
        )
    return po


def validate_receipt_against_pr(receipt_file, purchase_request):
    extracted = process_proforma_file(receipt_file)
    discrepancies = []
    rec_total = extracted.get("total_amount")
    pr_total = purchase_request.total_amount
    if rec_total is not None and Decimal(rec_total) != Decimal(pr_total):
        discrepancies.append(
            {
                "field": "total_amount",
                "expected": str(pr_total),
                "found": str(rec_total),
            }
        )
    return {
        "valid": len(discrepancies) == 0,
        "discrepancies": discrepancies,
        "extracted": extracted,
    }


def _serialize_pr_min(pr: PurchaseRequest) -> dict:
    data = {
        "id": getattr(pr, "id", None),
        "title": getattr(pr, "title", None),
        "description": getattr(pr, "description", None),
        "total_amount": (
            str(getattr(pr, "total_amount", None))
            if getattr(pr, "total_amount", None) is not None
            else None
        ),
        "status": getattr(pr, "status", None),
        "created_at": (
            getattr(pr, "created_at", None).isoformat()
            if getattr(pr, "created_at", None)
            else None
        ),
        "required_approval_levels": getattr(pr, "required_approval_levels", None),
        "current_approval_level": getattr(pr, "current_approval_level", None),
        "items": [],
    }
    if hasattr(pr, "items"):
        try:
            for it in pr.items.all():
                data["items"].append(
                    {
                        "id": getattr(it, "id", None),
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
        except Exception:
            # be defensive: ignore relation access errors
            pass
    return data
