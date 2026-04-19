"""Validator for REST Countries API responses."""

from __future__ import annotations

from typing import Any

from src.validators.base_validator import BaseValidator, ValidationResult

REQUIRED_FIELDS: tuple[str, ...] = ("name", "capital", "population", "currencies", "languages")
POPULATION_MIN: int = 1


class CountryValidator(BaseValidator):
    def validate(self, data: Any) -> ValidationResult:
        if not isinstance(data, list):
            self._fail("Response root must be a list")
            return self._pass()

        for idx, item in enumerate(data):
            if not isinstance(item, dict):
                self._fail(f"Item {idx} is not a dict")
                continue

            for field_name in REQUIRED_FIELDS:
                if field_name not in item:
                    self._fail(f"Item {idx} missing required field '{field_name}'")

            if "name" in item:
                name = item["name"]
                if not isinstance(name, dict):
                    self._fail(f"Item {idx}: 'name' must be a dict")
                elif "common" not in name:
                    self._fail(f"Item {idx}: 'name' missing 'common' key")
                elif not isinstance(name["common"], str) or not name["common"].strip():
                    self._fail(f"Item {idx}: 'name.common' must be a non-empty string")

            if "capital" in item:
                capital = item["capital"]
                if not isinstance(capital, list):
                    self._fail(f"Item {idx}: 'capital' must be a list")
                elif len(capital) == 0:
                    self._fail(f"Item {idx}: 'capital' must not be empty")

            if "population" in item:
                pop = item["population"]
                if isinstance(pop, bool) or not isinstance(pop, int):
                    self._fail(f"Item {idx}: 'population' must be an integer")
                elif pop < POPULATION_MIN:
                    self._fail(f"Item {idx}: 'population' must be >= {POPULATION_MIN}, got {pop}")

            if "currencies" in item:
                currencies = item["currencies"]
                if not isinstance(currencies, dict):
                    self._fail(f"Item {idx}: 'currencies' must be a dict")
                elif len(currencies) == 0:
                    self._fail(f"Item {idx}: 'currencies' must not be empty")

            if "languages" in item:
                languages = item["languages"]
                if not isinstance(languages, dict):
                    self._fail(f"Item {idx}: 'languages' must be a dict")
                elif len(languages) == 0:
                    self._fail(f"Item {idx}: 'languages' must not be empty")

        return self._pass()
