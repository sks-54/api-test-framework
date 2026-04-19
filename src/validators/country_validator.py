"""Validator for a single country object returned by the REST Countries API."""

from __future__ import annotations

from typing import Any

from .base_validator import BaseValidator, ValidationResult


class CountryValidator(BaseValidator):
    """Validates the structure and content of a REST Countries API country object.

    All errors are collected before returning; validation never short-circuits.
    """

    # Fields that must exist at the top level of the country object.
    _REQUIRED_FIELDS = ("name", "capital", "population", "currencies", "languages")

    def validate(self, data: Any) -> ValidationResult:
        """Validate a single country dict.

        Parameters
        ----------
        data:
            A deserialized country object (expected to be a ``dict``).

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
                errors=[f"Expected a dict for country data, got {type(data).__name__!r}."],
            )

        # --- Required fields presence ---
        for field in self._REQUIRED_FIELDS:
            if field not in data:
                errors.append(f"Missing required field: '{field}'.")

        # --- Per-field structural checks (only when field is present) ---

        # name: dict with a 'common' key that is a non-empty string
        if "name" in data:
            name = data["name"]
            if not isinstance(name, dict):
                errors.append(
                    f"'name' must be a dict, got {type(name).__name__!r}."
                )
            else:
                if "common" not in name:
                    errors.append("'name' dict is missing the 'common' key.")
                elif not isinstance(name["common"], str):
                    errors.append(
                        f"'name.common' must be a string, got {type(name['common']).__name__!r}."
                    )
                elif not name["common"].strip():
                    errors.append("'name.common' must not be an empty string.")

        # capital: non-empty list
        if "capital" in data:
            capital = data["capital"]
            if not isinstance(capital, list):
                errors.append(
                    f"'capital' must be a list, got {type(capital).__name__!r}."
                )
            elif len(capital) == 0:
                errors.append("'capital' must be a non-empty list.")

        # population: int > 0
        if "population" in data:
            population = data["population"]
            # bool is a subclass of int in Python; exclude it explicitly.
            if not isinstance(population, int) or isinstance(population, bool):
                errors.append(
                    f"'population' must be an int, got {type(population).__name__!r}."
                )
            elif population <= 0:
                errors.append(
                    f"'population' must be > 0, got {population}."
                )

        # currencies: non-empty dict
        if "currencies" in data:
            currencies = data["currencies"]
            if not isinstance(currencies, dict):
                errors.append(
                    f"'currencies' must be a dict, got {type(currencies).__name__!r}."
                )
            elif len(currencies) == 0:
                errors.append("'currencies' must be a non-empty dict.")

        # languages: non-empty dict
        if "languages" in data:
            languages = data["languages"]
            if not isinstance(languages, dict):
                errors.append(
                    f"'languages' must be a dict, got {type(languages).__name__!r}."
                )
            elif len(languages) == 0:
                errors.append("'languages' must be a non-empty dict.")

        return ValidationResult(passed=len(errors) == 0, errors=errors)
