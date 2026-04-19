# Code Style Rules — Multi-Environment API Test Framework

These rules govern all Python in this repository. Where they conflict with
PEP 8, these rules take precedence.

---

## 1. All Validators in `apitf/validators/` — No Inline Schema Checks

Schema validation logic must never appear inside a test file. It belongs
exclusively in a class extending `BaseValidator` in `apitf/validators/`.

## 2. Full Type Hints on Every Function Signature

```python
# CORRECT
def validate(self, data: Any) -> ValidationResult: ...

# FORBIDDEN
def validate(self, data): ...
```

Use `from __future__ import annotations` for forward references.

## 3. Catch Specific Exceptions — Never Bare `except:`

```python
# CORRECT
except requests.exceptions.Timeout as exc:
    raise FrameworkTimeoutError(url) from exc

# FORBIDDEN
except:          # bare
except Exception: # too broad
```

## 4. `HttpClient` Is the Only HTTP Entry Point in Tests

Tests must never import or call `requests` directly.

```python
# CORRECT — in test file
from apitf.http_client import HttpClient

# FORBIDDEN — in test file
import requests
response = requests.get("https://...")
```

## 5. Check `ValidationResult.passed` Before Accessing `.errors`

```python
# CORRECT
assert result.passed, result.errors

# FORBIDDEN
print(result.errors)          # .passed not checked
assert len(result.errors) == 0  # bypasses contract
```

## 6. `pathlib.Path` for All File I/O — Never `os.path`

```python
# CORRECT
from pathlib import Path
data = Path("config/environments.yaml").read_text(encoding="utf-8")

# FORBIDDEN
import os
path = os.path.join("config", "environments.yaml")
```

## 7. No `print()` in Test Files — Use Allure or pytest Logging

```python
# CORRECT
allure.attach(response.text, name="Response", attachment_type=allure.attachment_type.JSON)

# FORBIDDEN
print(response.json())
```

## 8. Constants at Module Level in SCREAMING_SNAKE_CASE

```python
# CORRECT
REQUIRED_FIELDS: tuple[str, ...] = ("name", "capital", "population")
TEMP_MIN: float = -80.0
TEMP_MAX: float = 60.0

# FORBIDDEN — magic literals buried in method bodies
if temp < -80.0: ...
```
