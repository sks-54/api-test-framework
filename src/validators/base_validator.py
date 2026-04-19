"""Abstract base class for all data validators."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationResult:
    """Outcome of a single validation run."""

    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class BaseValidator(ABC):
    """Contract that every concrete validator must fulfil."""

    @abstractmethod
    def validate(self, data: Any) -> ValidationResult:
        """Validate *data* and return a :class:`ValidationResult`.

        Implementations must collect *all* errors rather than short-circuiting
        on the first failure.
        """

    # ------------------------------------------------------------------
    # Convenience factory helpers
    # ------------------------------------------------------------------

    @classmethod
    def _pass(cls) -> ValidationResult:
        """Return a passing result with no errors or warnings."""
        return ValidationResult(passed=True)

    @classmethod
    def _fail(cls, msg: str) -> ValidationResult:
        """Return a failing result carrying a single error message."""
        return ValidationResult(passed=False, errors=[msg])
