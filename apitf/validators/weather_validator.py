"""Validator for Open-Meteo API forecast responses."""

from __future__ import annotations

from typing import Any

from apitf.validators.base_validator import BaseValidator, ValidationResult

REQUIRED_FIELDS: tuple[str, ...] = ("timezone", "hourly")
TEMP_MIN: float = -80.0
TEMP_MAX: float = 60.0
HOURLY_MIN_ENTRIES: int = 1


class WeatherValidator(BaseValidator):
    def validate(self, data: Any) -> ValidationResult:
        if not isinstance(data, dict):
            self._fail("Response root must be a dict")
            return self._pass()

        for field_name in REQUIRED_FIELDS:
            if field_name not in data:
                self._fail(f"Missing required field '{field_name}'")

        if "timezone" in data:
            tz = data["timezone"]
            if not isinstance(tz, str) or not tz.strip():
                self._fail("'timezone' must be a non-empty string")

        if "hourly" in data:
            hourly = data["hourly"]
            if not isinstance(hourly, dict):
                self._fail("'hourly' must be a dict")
            else:
                if "temperature_2m" not in hourly:
                    self._fail("'hourly' missing 'temperature_2m'")
                else:
                    temps = hourly["temperature_2m"]
                    if not isinstance(temps, list):
                        self._fail("'hourly.temperature_2m' must be a list")
                    elif len(temps) < HOURLY_MIN_ENTRIES:
                        self._fail(
                            f"'hourly.temperature_2m' must have >= {HOURLY_MIN_ENTRIES} entries"
                        )
                    else:
                        for i, t in enumerate(temps):
                            if t is None:
                                continue
                            if not isinstance(t, (int, float)):
                                self._fail(f"temperature_2m[{i}] is not numeric: {t!r}")
                            elif not (TEMP_MIN <= t <= TEMP_MAX):
                                self._fail(
                                    f"temperature_2m[{i}]={t} outside valid range "
                                    f"[{TEMP_MIN}, {TEMP_MAX}]"
                                )

        return self._pass()
