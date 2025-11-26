from django.contrib.auth import get_user_model

User = get_user_model()


def extract_pr_id_from_data(data):
    if not data:
        return None
    for key in ("purchase_request_id", "purchase_request", "id"):
        val = data.get(key)
        if isinstance(val, int):
            return val
    nested = data.get("data") if isinstance(data.get("data"), dict) else None
    if nested:
        for key in ("purchase_request_id", "purchase_request", "id"):
            val = nested.get(key)
            if isinstance(val, int):
                return val
    return None


def approver_from_embedded(data):
    approvals = data.get("approvals")
    if not isinstance(approvals, (list, tuple)):
        nested = data.get("data") if isinstance(data.get("data"), dict) else None
        approvals = nested.get("approvals") if nested else None
        if not isinstance(approvals, (list, tuple)):
            return None

    # prefer level 2 approved
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


# --- REPLACED: improved helpers to list/group approvers from embedded approvals data ---

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


def approvers_from_embedded(data):
    """
    Return a list of normalized approval dicts extracted from embedded data.
    Each item: { approver_id:int, level, decision, created_at, comment, user:User|None }
    This function batch-loads users to avoid N+1 queries.
    """
    raw = _get_embedded_approvals(data)
    items = []
    ids = set()
    for a in raw:
        # normalize possible keys
        approver_raw = a.get("approver_id") or a.get("approver") or a.get("user_id")
        try:
            approver_id = int(approver_raw) if approver_raw is not None else None
        except (TypeError, ValueError):
            approver_id = None
        if not approver_id:
            continue
        item = {
            "approver_id": approver_id,
            "level": a.get("level"),
            "decision": a.get("decision"),
            "created_at": a.get("created_at"),
            "comment": a.get("comment"),
            "raw": a,
        }
        items.append(item)
        ids.add(approver_id)

    users = {u.id: u for u in User.objects.filter(id__in=ids)} if ids else {}
    for it in items:
        it["user"] = users.get(it["approver_id"])
    return items


def approver_approvals_map(data):
    """
    Return dict: approver_id -> list[approval_dict], sorted by created_at descending.
    Use this to see exactly what each approver approved in the embedded payload.
    """
    items = approvers_from_embedded(data)
    m = {}
    for it in items:
        m.setdefault(it["approver_id"], []).append(it)
    # optional: sort each approver's list by created_at (descending) for readability
    for k, lst in m.items():
        lst.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return m
