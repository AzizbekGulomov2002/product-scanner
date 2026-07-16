import base64
import io

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from PIL import Image
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from search.services.search import SearchService
from search.views_pages import (
    AddProductView,
    DashboardView,
    RealtimeScannerView,
    SearchView,
)

__all__ = [
    "DashboardView",
    "SearchView",
    "AddProductView",
    "RealtimeScannerView",
    "ImageSearchView",
    "BarcodeSearchView",
    "RealtimeFrameSearchView",
    "AdminSearchTestView",
    "DashboardStatsView",
]


class ImageSearchView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        image = request.FILES.get("image")
        if not image:
            return Response({"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST)

        service = SearchService()
        result = service.search_by_image(
            image,
            source=request.data.get("source", "api"),
            telegram_user_id=request.data.get("telegram_user_id", ""),
            telegram_username=request.data.get("telegram_username", ""),
            query_image_file=image,
        )
        return Response(result)


class BarcodeSearchView(APIView):
    def post(self, request):
        barcode = request.data.get("barcode", "").strip()
        if not barcode:
            return Response({"error": "No barcode provided"}, status=status.HTTP_400_BAD_REQUEST)

        service = SearchService()
        result = service.search_by_barcode(
            barcode,
            source=request.data.get("source", "api"),
            telegram_user_id=request.data.get("telegram_user_id", ""),
            telegram_username=request.data.get("telegram_username", ""),
        )
        return Response(result)


@method_decorator(csrf_exempt, name="dispatch")
class RealtimeFrameSearchView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        frame_data = request.data.get("frame", "")
        if not frame_data:
            return Response({"error": "No frame provided"}, status=status.HTTP_400_BAD_REQUEST)

        if "," in frame_data:
            frame_data = frame_data.split(",", 1)[1]

        try:
            image_bytes = base64.b64decode(frame_data)
            image = Image.open(io.BytesIO(image_bytes))
        except Exception:
            return Response({"error": "Invalid frame data"}, status=status.HTTP_400_BAD_REQUEST)

        service = SearchService()
        hint_barcode = request.data.get("barcode", "").strip()
        result = service.search_realtime_frame(image, hint_barcode=hint_barcode or None)
        return Response(result)


class AdminSearchTestView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        image = request.FILES.get("image")
        if not image:
            return Response({"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST)

        service = SearchService()
        result = service.search_by_image(
            image,
            source="admin",
            query_image_file=image,
            strict=False,
        )
        return Response(result)


class DashboardStatsView(APIView):
    def get(self, request):
        from search.admin import get_dashboard_stats

        return Response(get_dashboard_stats())
