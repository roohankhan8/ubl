from django.db.models import Count, Q
from rest_framework.response import Response
from rest_framework.views import APIView

from imports.models import ImportBatch
from imports.serializers import ImportBatchSerializer
from reconciliation.models import ReconciliationResult, ReconciliationRun
from transactions.models import Transaction


class DashboardSummaryView(APIView):
    def get(self, request):
        result_counts = ReconciliationResult.objects.aggregate(
            total=Count("id"),
            matched=Count("id", filter=Q(status=ReconciliationResult.Status.MATCHED)),
            mismatched=Count("id", filter=Q(status__endswith="MISMATCH")),
            missing=Count("id", filter=Q(status__startswith="MISSING_")),
        )
        total = result_counts["total"] or 0
        matched = result_counts["matched"] or 0
        return Response({
            "transactions": Transaction.objects.count(),
            "imports": ImportBatch.objects.count(),
            "reconciliation_runs": ReconciliationRun.objects.count(),
            "matched": matched,
            "mismatched": result_counts["mismatched"] or 0,
            "missing": result_counts["missing"] or 0,
            "match_rate": f"{(matched * 100 / total):.2f}" if total else "0.00",
            "recent_imports": ImportBatchSerializer(
                ImportBatch.objects.select_related("data_source", "uploaded_by")[:5],
                many=True,
            ).data,
        })
