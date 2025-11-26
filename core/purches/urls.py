from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.purches.views.approvals import (
    ApprovedReceiptsView,
    MyApprovedRequestsView,
    MyRejectedRequestsView,
    ReceiptDetailView,
    ReceiptListView,
    RequestReceiptsView,
)
from core.purches.views.purchase_order import PurchaseOrderViewSet  # added import
from core.purches.views.purchase_request import PurchaseRequestViewSet

router = DefaultRouter()
# register viewset under /api/purchases/requests/
router.register(
    r"purchases/requests", PurchaseRequestViewSet, basename="purchase-requests"
)
router.register(
    r"purchases/purchase-orders", PurchaseOrderViewSet, basename="purchaseorder"
)  # new route

urlpatterns = [
    path("", include(router.urls)),
    # endpoint for approver to fetch requests they rejected
    path(
        "approvals/mine/rejected/",
        MyRejectedRequestsView.as_view(),
        name="my-rejected-requests",
    ),
    # endpoint for approver to fetch requests they approved
    path(
        "approvals/mine/", MyApprovedRequestsView.as_view(), name="my-approved-requests"
    ),
    path(
        "receipts/approved/", ApprovedReceiptsView.as_view(), name="approved-receipts"
    ),
    path("receipts/", ReceiptListView.as_view(), name="receipt-list"),
    path("receipts/<int:pk>/", ReceiptDetailView.as_view(), name="receipt-detail"),
    path(
        "purchases/requests/<int:pk>/receipts/",
        RequestReceiptsView.as_view(),
        name="request-receipts",
    ),
]
