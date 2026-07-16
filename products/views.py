from django.db.models import Q
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from products.models import Product, ProductImage
from products.serializers import ProductCreateSerializer, ProductSerializer


class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.prefetch_related("images")
    serializer_class = ProductSerializer

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "request": self.request}


class ProductLookupView(APIView):
    """Search product by external_id (exact) or name (partial)."""

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"error": "q parameter required"}, status=status.HTTP_400_BAD_REQUEST)

        product = Product.objects.filter(external_id=query).prefetch_related("images").first()
        if not product:
            product = (
                Product.objects.filter(Q(name__icontains=query) | Q(barcode=query))
                .prefetch_related("images")
                .first()
            )

        if not product:
            return Response({"found": False, "products": []})

        serializer = ProductSerializer(product, context={"request": request})
        return Response({"found": True, "products": [serializer.data]})


class ProductCreateView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        images = request.FILES.getlist("images")
        if not images:
            return Response({"error": "At least one image required"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ProductCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if Product.objects.filter(external_id=data["external_id"]).exists():
            return Response(
                {"error": f"Product with ID '{data['external_id']}' already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        product = Product.objects.create(
            external_id=data["external_id"],
            name=data["name"],
            barcode=data.get("barcode", ""),
        )

        for idx, image in enumerate(images):
            ProductImage.objects.create(
                product=product,
                image=image,
                is_primary=(idx == 0),
            )

        result = ProductSerializer(product, context={"request": request})
        return Response({"success": True, "product": result.data}, status=status.HTTP_201_CREATED)
