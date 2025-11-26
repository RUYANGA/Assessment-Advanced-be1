from typing import Any


def user_is_role(user: Any, role_name: str) -> bool:
    """
    Return True if user has the given role.

    Prefer a project-level helper if available (core.users.utils.user_is_role).
    Otherwise fall back to a simple role string comparison.
    """
    try:
        import importlib

        mod = importlib.import_module("core.users.utils")
        project_fn = getattr(mod, "user_is_role", None)
        if callable(project_fn):
            return project_fn(user, role_name)
    except Exception:
        # runtime import failed (module missing) — fall back to simple check
        pass

    role_val = getattr(user, "role", "") or ""
    return role_val.lower() == str(role_name).lower()
