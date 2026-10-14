from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.routing.ors import OrsClient

from .serializers import (
    AutocompleteQuerySerializer,
    PlaceSerializer,
    TripAnalysisSerializer,
    TripRequestSerializer,
)
from .services import TripAnalyzer


def health(_request):
    return JsonResponse({"status": "ok"})


class AnalyzeTripView(APIView):
    @extend_schema(
        request=TripRequestSerializer,
        responses=TripAnalysisSerializer,
        summary="Analyze weather risk on up to three routes",
    )
    def post(self, request):
        serializer = TripRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = TripAnalyzer().analyze(serializer.to_request())
        return Response(TripAnalysisSerializer(result).data)


class AutocompleteView(APIView):
    @extend_schema(
        parameters=[AutocompleteQuerySerializer],
        responses=PlaceSerializer(many=True),
        summary="Search U.S. place names",
    )
    def get(self, request):
        query = AutocompleteQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        places = OrsClient().autocomplete(query.validated_data["q"])
        return Response([{"label": p.label, "lat": p.lat, "lon": p.lon} for p in places])
