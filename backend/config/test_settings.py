"""Settings for the test-suite: in-memory cache, no real provider keys."""

import os

os.environ.setdefault("DJANGO_DEBUG", "true")

from .settings import *  # noqa: E402, F403

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
ORS_API_KEY = "test-key"
ORS_BASE_URL = "https://ors.test"
OPEN_METEO_URL = "https://meteo.test/v1/forecast"
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_CLASSES": []}  # noqa: F405
