# Lightweight compatibility shim: import the real ViewSet implementation from
# purchase_request_core so this module stays small and linters don't complain.
from .purchase_request_core import PurchaseRequestViewSet

__all__ = ["PurchaseRequestViewSet"]
