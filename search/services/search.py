import logging

from django.conf import settings
from django.db.models import F
from pgvector.django import CosineDistance

from products.models import Product, ProductImage
from search.models import ImageEmbedding, SearchHistory
from search.services.image_utils import crop_center_for_scan
from search.services.barcode import BarcodeService, normalize_barcode
from search.services.embedding import get_embedding_service

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.barcode_service = BarcodeService()

    def search_by_image(
        self,
        image_input,
        source="api",
        telegram_user_id="",
        telegram_username="",
        save_history=True,
        query_image_file=None,
        strict=None,
    ) -> dict:
        barcode = self.barcode_service.decode_first(image_input)
        if barcode:
            barcode_result = self.search_by_barcode(
                barcode,
                source=source,
                telegram_user_id=telegram_user_id,
                telegram_username=telegram_username,
                save_history=False,
            )
            if barcode_result["status"] != "not_found":
                if save_history:
                    self._save_history(
                        query_image_file=query_image_file,
                        detected_barcode=barcode,
                        result=barcode_result,
                        source=source,
                        telegram_user_id=telegram_user_id,
                        telegram_username=telegram_username,
                    )
                barcode_result["detected_barcode"] = barcode
                barcode_result["method"] = "barcode"
                return barcode_result

        embedding = self.embedding_service.embed_image(image_input)
        results = self._vector_search(embedding)

        if strict is None:
            strict = source not in ("admin",)

        response = self._build_response(results, method="image_embedding", strict=strict)
        response["detected_barcode"] = barcode or ""

        if save_history:
            self._save_history(
                query_image_file=query_image_file,
                detected_barcode=barcode or "",
                result=response,
                source=source,
                telegram_user_id=telegram_user_id,
                telegram_username=telegram_username,
            )

        return response

    def search_by_barcode(
        self,
        barcode: str,
        source="api",
        telegram_user_id="",
        telegram_username="",
        save_history=True,
    ) -> dict:
        barcode = barcode.strip()
        product = Product.objects.filter(barcode=barcode).first()

        if not product:
            normalized = normalize_barcode(barcode)
            if normalized:
                product = Product.objects.filter(barcode=normalized).first()
                if not product:
                    for candidate in Product.objects.exclude(barcode="").only("id", "barcode"):
                        if normalize_barcode(candidate.barcode) == normalized:
                            product = Product.objects.filter(pk=candidate.pk).first()
                            break

        if not product:
            product = Product.objects.filter(external_id=barcode).first()

        if not product and normalize_barcode(barcode):
            product = Product.objects.filter(external_id=normalize_barcode(barcode)).first()

        if product:
            result = {
                "status": "found",
                "status_label": "Product Found",
                "confidence": 1.0,
                "confidence_percent": 100,
                "method": "barcode",
                "matches": [self._product_to_match(product, 1.0)],
            }
        else:
            result = {
                "status": "not_found",
                "status_label": "Product Not Found",
                "confidence": 0.0,
                "confidence_percent": 0,
                "method": "barcode",
                "matches": [],
            }

        if save_history:
            self._save_history(
                detected_barcode=barcode,
                result=result,
                source=source,
                telegram_user_id=telegram_user_id,
                telegram_username=telegram_username,
            )

        return result

    def search_realtime_frame(self, image_input, hint_barcode: str | None = None) -> dict:
        barcode = (hint_barcode or "").strip() or self.barcode_service.decode_first(image_input)
        if barcode:
            result = self.search_by_barcode(barcode, save_history=False)
            result["detected_barcode"] = barcode
            result["method"] = "barcode"
            return result

        product_votes: dict[int, dict] = {}
        for ratio in (0.5, 0.65):
            cropped = crop_center_for_scan(image_input, ratio=ratio)
            embedding = self.embedding_service.embed_image(cropped)
            for hit in self._vector_search_products(embedding):
                pid = hit["product"].id
                entry = product_votes.setdefault(pid, {
                    "product": hit["product"],
                    "scores": [],
                })
                entry["scores"].append(hit["similarity"])

        ranked = []
        for entry in product_votes.values():
            scores = entry["scores"]
            ranked.append({
                "product": entry["product"],
                "similarity": sum(scores) / len(scores),
            })
        ranked.sort(key=lambda item: item["similarity"], reverse=True)

        response = self._build_realtime_response(ranked)
        response["detected_barcode"] = barcode or ""
        return response

    def _build_realtime_response(self, results) -> dict:
        if not results:
            return self._realtime_not_found(0.0)

        best = results[0]
        confidence = best["similarity"]

        if confidence < settings.REALTIME_CONFIDENCE_MIN:
            return self._realtime_not_found(confidence)

        if len(results) >= 2:
            gap = confidence - results[1]["similarity"]
            if gap < settings.REALTIME_CONFIDENCE_MIN_GAP:
                return self._realtime_not_found(confidence)

        status = "found" if confidence >= settings.REALTIME_CONFIDENCE_HIGH else "probable"
        match = self._product_to_match(best["product"], confidence)
        return {
            "status": status,
            "status_label": "Product Found" if status == "found" else "Probable Match",
            "confidence": confidence,
            "confidence_percent": round(confidence * 100, 1),
            "method": "image_embedding",
            "matches": [match],
        }

    def _realtime_not_found(self, confidence: float) -> dict:
        return {
            "status": "not_found",
            "status_label": "Product Not Found",
            "confidence": confidence,
            "confidence_percent": round(confidence * 100, 1),
            "method": "image_embedding",
            "matches": [],
        }

    def _vector_search_products(self, embedding, top_k=None):
        top_k = top_k or settings.SEARCH_TOP_K
        raw_k = max(top_k * 6, 20)

        qs = (
            ImageEmbedding.objects
            .annotate(distance=CosineDistance("embedding", embedding.tolist()))
            .annotate(similarity=1 - F("distance"))
            .select_related("product_image__product")
            .order_by("distance")[:raw_k]
        )

        by_product: dict[int, dict] = {}
        for emb in qs:
            product = emb.product_image.product
            sim = float(emb.similarity)
            current = by_product.get(product.id)
            if current is None or sim > current["similarity"]:
                by_product[product.id] = {"product": product, "similarity": sim}

        ranked = sorted(by_product.values(), key=lambda item: item["similarity"], reverse=True)
        return ranked[:top_k]

    def _vector_search(self, embedding, top_k=None):
        top_k = top_k or settings.SEARCH_TOP_K

        qs = (
            ImageEmbedding.objects
            .annotate(distance=CosineDistance("embedding", embedding.tolist()))
            .annotate(similarity=1 - F("distance"))
            .select_related("product_image__product")
            .order_by("distance")[:top_k]
        )

        results = []
        seen_products = set()
        for emb in qs:
            product = emb.product_image.product
            if product.id in seen_products:
                continue
            seen_products.add(product.id)
            results.append({
                "product": product,
                "similarity": float(emb.similarity),
                "image_id": emb.product_image_id,
            })
        return results

    def _evaluate_status(self, results) -> tuple[str, float]:
        if not results:
            return "not_found", 0.0

        best_sim = results[0]["similarity"]

        if best_sim < settings.CONFIDENCE_MEDIUM:
            return "not_found", best_sim

        if len(results) >= 2:
            gap = best_sim - results[1]["similarity"]
            if gap < settings.CONFIDENCE_MIN_GAP:
                return "not_found", best_sim

        if best_sim >= settings.CONFIDENCE_HIGH:
            return "found", best_sim

        return "probable", best_sim

    def _build_response(self, results, method="image_embedding", strict=False) -> dict:
        status, confidence = self._evaluate_status(results)

        status_labels = {
            "found": "Product Found",
            "probable": "Probable Match",
            "not_found": "Product Not Found",
        }

        matches = [
            self._product_to_match(r["product"], r["similarity"])
            for r in results
            if r["similarity"] >= settings.CONFIDENCE_MEDIUM
        ]

        if strict and status != "found":
            return {
                "status": "not_found",
                "status_label": "Product Not Found",
                "confidence": confidence,
                "confidence_percent": round(confidence * 100, 1),
                "method": method,
                "matches": [],
            }

        if status == "not_found":
            return {
                "status": "not_found",
                "status_label": status_labels["not_found"],
                "confidence": confidence,
                "confidence_percent": round(confidence * 100, 1),
                "method": method,
                "matches": [],
            }

        return {
            "status": status,
            "status_label": status_labels[status],
            "confidence": confidence,
            "confidence_percent": round(confidence * 100, 1),
            "method": method,
            "matches": matches,
        }

    def _product_to_match(self, product: Product, similarity: float) -> dict:
        primary = product.images.filter(is_primary=True).first() or product.images.first()
        image_url = primary.image.url if primary else ""
        return {
            "id": product.id,
            "external_id": product.external_id,
            "name": product.name,
            "barcode": product.barcode,
            "similarity": similarity,
            "similarity_percent": round(similarity * 100, 1),
            "image_url": image_url,
        }

    def _save_history(self, result, source, telegram_user_id="", telegram_username="",
                      query_image_file=None, detected_barcode=""):
        top_match = result.get("matches", [{}])[0] if result.get("matches") else {}
        product_id = top_match.get("id")

        SearchHistory.objects.create(
            query_image=query_image_file,
            detected_barcode=detected_barcode,
            matched_product_id=product_id,
            confidence=result.get("confidence"),
            result_status=result.get("status", "not_found"),
            source=source,
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_username,
            raw_response=result,
        )
