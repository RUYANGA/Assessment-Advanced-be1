from django.utils.crypto import get_random_string
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

try:
    from core.users.utils import user_is_role
except Exception:

    def user_is_role(user, role_name):
        return (getattr(user, "role", "") or "").lower() == str(role_name).lower()


import logging

from core.purches.models import PurchaseOrder
from core.purches.serializers.purchase_order import PurchaseOrderSerializer

logger = logging.getLogger(__name__)


def _generate_po_number():
    return f"PO-{get_random_string(8).upper()}"


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """
    CRUD for PurchaseOrder
    - list/retrieve: any authenticated user
    - create/update/destroy: staff/superuser or role 'finance' only
    """

    queryset = PurchaseOrder.objects.all().order_by("-id")
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated]

    def _user_can_edit(self, user):
        return user.is_staff or user.is_superuser or user_is_role(user, "finance")

    def create(self, request, *args, **kwargs):
        if not self._user_can_edit(request.user):
            return Response(
                {"detail": "insufficient_role"}, status=status.HTTP_403_FORBIDDEN
            )
        # auto-generate po_number if client didn't provide one
        data = request.data.copy()
        if not data.get("po_number"):
            data["po_number"] = _generate_po_number()
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        if not self._user_can_edit(request.user):
            return Response(
                {"detail": "insufficient_role"}, status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not self._user_can_edit(request.user):
            return Response(
                {"detail": "insufficient_role"}, status=status.HTTP_403_FORBIDDEN
            )
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not self._user_can_edit(request.user):
            return Response(
                {"detail": "insufficient_role"}, status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)
