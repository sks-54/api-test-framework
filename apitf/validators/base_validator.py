"""Abstract base validator — all API response validators extend this."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationResult:
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class BaseValidator(ABC):
    def __init__(self) -> None:
        self._errors: list[str] = []
        self._warnings: list[str] = []

    def _fail(self, message: str) -> None:
        self._errors.append(message)

    def _warn(self, message: str) -> None:
        self._warnings.append(message)

    def _pass(self) -> ValidationResult:
        return ValidationResult(
            passed=len(self._errors) == 0,
            errors=list(self._errors),
            warnings=list(self._warnings),
        )

    @abstractmethod
    def validate(self, data: Any) -> ValidationResult: ...
