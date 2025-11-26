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
