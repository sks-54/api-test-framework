"""Validator for a weather forecast response from the Open-Meteo API."""

from __future__ import annotations

from typing import Any, Union

from .base_validator import BaseValidator, ValidationResult

# Physical plausibility bounds for surface air temperature (degrees Celsius).
# Sourced from WMO world records with a small margin.
_TEMP_MIN: float = -80.0
_TEMP_MAX: float = 60.0


class WeatherValidator(BaseValidator):
    """Validates the structure and content of an Open-Meteo forecast response.

    All errors are collected before returning; validation never short-circuits.
    """

    def validate(self, data: Any) -> ValidationResult:
        """Validate a single Open-Meteo forecast response dict.

        Parameters
        ----------
        data:
            A deserialized forecast response (expected to be a ``dict``).

        Returns
        -------
        ValidationResult
            ``passed=True`` when no errors were found; ``passed=False``
            otherwise, with every issue captured in ``errors``.
        """
        errors: list[str] = []

        if not isinstance(data, dict):
            return ValidationResult(
                passed=False,
                errors=[
                    f"Expected a dict for weather data, got {type(data).__name__!r}."
                ],
            )

        # --- timezone ---
        if "timezone" not in data:
            errors.append("Missing required field: 'timezone'.")
        else:
            timezone = data["timezone"]
            if not isinstance(timezone, str):
                errors.append(
                    f"'timezone' must be a string, got {type(timezone).__name__!r}."
                )
            elif not timezone.strip():
                errors.append("'timezone' must not be an empty string.")

        # --- hourly ---
        if "hourly" not in data:
            errors.append("Missing required field: 'hourly'.")
        else:
            hourly = data["hourly"]
            if not isinstance(hourly, dict):
                errors.append(
                    f"'hourly' must be a dict, got {type(hourly).__name__!r}."
                )
            else:
                # --- hourly.temperature_2m ---
                if "temperature_2m" not in hourly:
                    errors.append(
                        "Missing required field: 'hourly.temperature_2m'."
                    )
                else:
                    temps = hourly["temperature_2m"]
                    if not isinstance(temps, list):
                        errors.append(
                            f"'hourly.temperature_2m' must be a list, "
                            f"got {type(temps).__name__!r}."
                        )
                    elif len(temps) == 0:
                        errors.append(
                            "'hourly.temperature_2m' must contain at least one entry."
                        )
                    else:
                        for idx, temp in enumerate(temps):
                            if not isinstance(temp, (int, float)) or isinstance(
                                temp, bool
                            ):
                                errors.append(
                                    f"'hourly.temperature_2m[{idx}]' must be a "
                                    f"float or int, got {type(temp).__name__!r}."
                                )
                            elif not (_TEMP_MIN <= temp <= _TEMP_MAX):
                                errors.append(
                                    f"'hourly.temperature_2m[{idx}]' value {temp} is "
                                    f"out of range [{_TEMP_MIN}, {_TEMP_MAX}]."
                                )

        return ValidationResult(passed=len(errors) == 0, errors=errors)
