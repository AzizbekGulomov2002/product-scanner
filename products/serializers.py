from rest_framework import serializers

from products.models import Product, ProductImage


class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ("id", "image", "image_url", "is_primary")

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url if obj.image else ""


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ("id", "external_id", "name", "barcode", "images")


class ProductCreateSerializer(serializers.Serializer):
    external_id = serializers.CharField(max_length=100)
    name = serializers.CharField(max_length=255)
    barcode = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
