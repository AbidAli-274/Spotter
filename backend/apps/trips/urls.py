from django.urls import path

from .views import AnalyzeTripView, AutocompleteView

urlpatterns = [
    path("geocode/autocomplete/", AutocompleteView.as_view(), name="autocomplete"),
    path("trips/analyze/", AnalyzeTripView.as_view(), name="analyze-trip"),
]
