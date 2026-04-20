"""Validator for the weather API — Open-Meteo /forecast endpoint."""
from __future__ import annotations

from typing import Any

from apitf.validators.base_validator import BaseValidator, ValidationResult

REQUIRED_FIELDS: tuple[str, ...] = (
    "latitude",
    "longitude",
    "generationtime_ms",
    "utc_offset_seconds",
    "timezone",
    "timezone_abbreviation",
    "elevation",
)

TEMP_MIN: float = -80.0
TEMP_MAX: float = 60.0


class WeatherValidator(BaseValidator):
    """Validates a single Open-Meteo /forecast response object."""

    def validate(self, data: Any) -> ValidationResult:
        if not isinstance(data, dict):
            self._fail("Response root must be a dict")
            return self._pass()
        for field in REQUIRED_FIELDS:
            if field not in data:
                self._fail(f"Missing required field: {field!r}")
            elif data[field] is None:
                self._fail(f"Field {field!r} must not be null")
        # Spec: temperature range -80 to 60°C, hourly entry count > 0
        if "hourly" in data and isinstance(data["hourly"], dict):
            temps = data["hourly"].get("temperature_2m", [])
            if isinstance(temps, list):
                if len(temps) == 0:
                    self._fail("hourly.temperature_2m must not be empty when hourly key is present")
                for t in temps:
                    if isinstance(t, (int, float)) and not (TEMP_MIN <= t <= TEMP_MAX):
                        self._fail(
                            f"temperature_2m value {t} outside valid range "
                            f"[{TEMP_MIN}, {TEMP_MAX}]°C"
                        )
        return self._pass()
