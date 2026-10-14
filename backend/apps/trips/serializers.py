from __future__ import annotations

from datetime import UTC

from rest_framework import serializers

from apps.routing.sampling import ALLOWED_INTERVALS_MI

from .schemas import PlaceInput, TripRequest

MAX_LOAD_LB = 120_000
LEVELS = ["low", "moderate", "high", "severe", "no_travel"]


class PlaceInputSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=200, trim_whitespace=True)
    lat = serializers.FloatField(required=False, min_value=-90, max_value=90)
    lon = serializers.FloatField(required=False, min_value=-180, max_value=180)

    def validate(self, attrs):
        if ("lat" in attrs) != ("lon" in attrs):
            raise serializers.ValidationError("Provide both lat and lon, or neither.")
        return attrs


class TripRequestSerializer(serializers.Serializer):
    origin = PlaceInputSerializer()
    destination = PlaceInputSerializer()
    departure = serializers.DateTimeField(
        help_text="ISO 8601. Values without a timezone are interpreted as UTC."
    )
    load_lb = serializers.FloatField(
        min_value=0, max_value=MAX_LOAD_LB, help_text="Load weight in pounds."
    )
    interval_mi = serializers.ChoiceField(
        choices=ALLOWED_INTERVALS_MI, default=25, help_text="Weather sampling interval in miles."
    )

    def validate_departure(self, value):
        return value.astimezone(UTC)

    def to_request(self) -> TripRequest:
        d = self.validated_data
        return TripRequest(
            origin=PlaceInput(**d["origin"]),
            destination=PlaceInput(**d["destination"]),
            departure=d["departure"],
            load_lb=d["load_lb"],
            interval_mi=d["interval_mi"],
        )


# --- response shapes (used for OpenAPI documentation and output rendering) ---------
class PlaceSerializer(serializers.Serializer):
    label = serializers.CharField()
    lat = serializers.FloatField()
    lon = serializers.FloatField()


class WeatherSerializer(serializers.Serializer):
    wind_mph = serializers.FloatField()
    rain_in_hr = serializers.FloatField()
    snow_in_hr = serializers.FloatField()


class CheckpointSerializer(serializers.Serializer):
    index = serializers.IntegerField()
    mile = serializers.FloatField()
    lat = serializers.FloatField()
    lon = serializers.FloatField()
    eta = serializers.DateTimeField()
    weather = WeatherSerializer(allow_null=True)
    risk = serializers.ChoiceField(choices=LEVELS, allow_null=True)
    risk_value = serializers.IntegerField(help_text="0-4, or -1 when weather is unavailable.")
    drivers = serializers.ListField(child=serializers.CharField())
    load_adjusted = serializers.BooleanField()


class RouteMetricsSerializer(serializers.Serializer):
    miles_by_level = serializers.DictField(child=serializers.FloatField())
    unknown_miles = serializers.FloatField()
    avg_risk = serializers.FloatField(help_text="Mileage-weighted mean risk, 0 (low) to 4.")
    worst_level = serializers.ChoiceField(choices=LEVELS, allow_null=True)


class RouteSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    summary = serializers.CharField(allow_blank=True)
    distance_mi = serializers.FloatField()
    duration_s = serializers.IntegerField()
    arrival = serializers.DateTimeField()
    rank = serializers.IntegerField(help_text="1 = best by the recommendation rules.")
    recommended = serializers.BooleanField()
    geometry = serializers.ListField(child=serializers.ListField(child=serializers.FloatField()))
    metrics = RouteMetricsSerializer()
    checkpoints = CheckpointSerializer(many=True)


class RecommendationSerializer(serializers.Serializer):
    route_index = serializers.IntegerField()
    route_id = serializers.CharField()
    reason = serializers.CharField()
    all_blocked = serializers.BooleanField()


class HeatmapPointSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lon = serializers.FloatField()
    levels = serializers.ListField(
        child=serializers.IntegerField(), help_text="Risk 0-4 per forecast hour; -1 = unknown."
    )


class HeatmapSerializer(serializers.Serializer):
    start = serializers.DateTimeField(help_text="Forecast hour 0 (departure, floored to the hour).")
    hours = serializers.IntegerField()
    points = HeatmapPointSerializer(many=True)


class TripAnalysisSerializer(serializers.Serializer):
    origin = PlaceSerializer()
    destination = PlaceSerializer()
    departure = serializers.DateTimeField()
    load_lb = serializers.FloatField()
    interval_mi = serializers.IntegerField()
    recommendation = RecommendationSerializer()
    routes = RouteSerializer(many=True)
    heatmap = HeatmapSerializer()


class AutocompleteQuerySerializer(serializers.Serializer):
    q = serializers.CharField(min_length=2, max_length=200)
