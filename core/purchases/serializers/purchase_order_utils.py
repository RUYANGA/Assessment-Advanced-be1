from django.contrib.auth import get_user_model
from rest_framework import serializers

from core.purches.serializers.purchase_order_utils import (
    approver_approvals_map as approver_approvals_map_fn,
)
from core.purches.models import Approval

User = get_user_model()


def _get_embedded_approvals(data):
    """Return approvals list from payload (handles nested 'data')."""
    approvals = data.get("approvals")
    if isinstance(approvals, (list, tuple)):
        return approvals

    nested = data.get("data") if isinstance(data.get("data"), dict) else None
    if nested:
        approvals = nested.get("approvals")
        if isinstance(approvals, (list, tuple)):
            return approvals

    return []


def approver_from_embedded(data):
    approvals = _get_embedded_approvals(data)
    if not approvals:
        return None

    # Prefer level 2 approved
    by_level2 = [
        a for a in approvals if a.get("level") == 2 and a.get("decision") == "APPROVED"
    ]
    cand = by_level2[0] if by_level2 else None

    if not cand:
        approved = [a for a in approvals if a.get("decision") == "APPROVED"]
        if not approved:
            return None
        approved.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        cand = approved[0]

    approver_id = cand.get("approver_id") or cand.get("approver")
    if not approver_id:
        return None

    return User.objects.filter(id=approver_id).first()


def approvers_from_embedded(data):
    """
    Return a list of normalized approval dicts extracted from embedded data.
    Each item: { approver_id:int, level, decision, created_at, comment, user:User|None }
    Batch-load users to avoid N+1 queries.
    """
    raw = _get_embedded_approvals(data)
    items = []
    ids = set()

    for a in raw:
        approver_raw = a.get("approver_id") or a.get("approver") or a.get("user_id")
        try:
            approver_id = int(approver_raw) if approver_raw is not None else None
        except (TypeError, ValueError):
            approver_id = None

        if not approver_id:
            continue

        items.append(
            {
                "approver_id": approver_id,
                "level": a.get("level"),
                "decision": a.get("decision"),
                "created_at": a.get("created_at"),
                "comment": a.get("comment"),
                "raw": a,
            }
        )
        ids.add(approver_id)

    users = {u.id: u for u in User.objects.filter(id__in=ids)} if ids else {}

    for it in items:
        it["user"] = users.get(it["approver_id"])

    return items


def approver_approvals_map_local(data):
    """
    Local version renamed to avoid F811.
    Return dict: approver_id -> list[approval_dict], sorted by created_at desc.
    """
    items = approvers_from_embedded(data)
    result = {}

    for it in items:
        result.setdefault(it["approver_id"], []).append(it)

    for lst in result.values():
        lst.sort(key=lambda x: x.get("created_at") or "", reverse=True)

    return result


class MyApprovalSerializer(serializers.ModelSerializer):
    purchase_request = serializers.SerializerMethodField(read_only=True)
    my_approvals = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Approval
        fields = (
            "id",
            "purchase_request",
            "level",
            "decision",
            "comment",
            "created_at",
            "my_approvals",
        )
        read_only_fields = fields  # ✅ fixed (inside Meta)

    def get_purchase_request(self, obj):
        pr = getattr(obj, "purchase_request", None)
        if not pr:
            return None

        return {
            "id": getattr(pr, "id", None),
            "status": getattr(pr, "status", None),
            "required_approvers": getattr(pr, "required_approvers", None),
            "data": getattr(pr, "data", None),
        }

    def get_my_approvals(self, obj):
        """
        Return the list of approval entries for the current request.user extracted
        from the embedded purchase_request.data snapshot.
        """
        request = self.context.get("request")
        if not request or not getattr(obj, "purchase_request", None):
            return []

        pr = obj.purchase_request
        data = getattr(pr, "data", {}) or {}

        # Use imported function (aliased to avoid name collision)
        mapping = approver_approvals_map_fn(data) or {}
        user_entries = mapping.get(request.user.id, [])

        return [
            {
                "level": it.get("level"),
                "decision": it.get("decision"),
                "created_at": it.get("created_at"),
                "comment": it.get("comment"),
            }
            for it in user_entries
        ]
