"""Structured API errors shared by every endpoint."""

from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler


class ServiceError(APIException):
    """Domain error with a stable machine-readable `code`."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "bad_request"
    default_detail = "The request could not be processed."


class GeocodingError(ServiceError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = "location_not_found"


class RoutingError(ServiceError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = "route_not_found"


class UpstreamError(ServiceError):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_code = "upstream_unavailable"
    default_detail = "An upstream data provider is unavailable. Please retry shortly."


class ForecastRangeError(ServiceError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = "forecast_out_of_range"


def api_exception_handler(exc, context):
    """Render every error as {"error": {"code", "message", "details"?}}."""
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, ValidationError):
        body = {"code": "validation_error", "message": "Invalid request.", "details": response.data}
    else:
        codes = exc.get_codes() if isinstance(exc, APIException) else "error"
        body = {"code": codes if isinstance(codes, str) else "error", "message": str(exc.detail)}
    return Response({"error": body}, status=response.status_code, headers=dict(response.items()))
