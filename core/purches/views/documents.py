from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.purches import services as prs_services
from core.purches.serializers.document import ProformaUploadSerializer


class ProformaUploadView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=ProformaUploadSerializer, tags=["Documents"])
    def post(self, request):
        serializer = ProformaUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        f = serializer.validated_data["file"]
        auto = serializer.validated_data.get("auto_create_po", False)

        # process (sync or async)
        extracted = prs_services.process_proforma_file(
            f
        )  # returns dict with vendor, items, total, invoice_no, date
        result = {"extracted": extracted}

        if auto:
            po = prs_services.create_purchase_order_from_proforma(
                extracted, created_by=request.user
            )
            result["purchase_order_id"] = po.id
        return Response(result, status=status.HTTP_201_CREATED)
