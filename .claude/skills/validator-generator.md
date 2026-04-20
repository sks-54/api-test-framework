# Skill: Generate Typed Validator From Sample JSON Response

## Purpose
Given a sample JSON response body, generate a complete typed `BaseValidator`
subclass in `apitf/validators/` that collects ALL errors without short-circuiting.

## Invocation Inputs (all required)
```
SAMPLE_JSON:    <paste raw JSON response body>
ENDPOINT_NAME:  <e.g. "Country Lookup">
CLASS_NAME:     <e.g. CountriesValidator>
OUTPUT_MODULE:  <e.g. countries_validator>
```

## Prompt Template

```
Generate a typed validator class for this API response.

  Endpoint:    {ENDPOINT_NAME}
  Class name:  {CLASS_NAME}
  Module:      apitf/validators/{OUTPUT_MODULE}.py
  Sample JSON: {SAMPLE_JSON}

### BaseValidator contract
Extend BaseValidator from apitf/validators/base_validator.py.
validate(self, data: Any) -> ValidationResult.
Use self._fail(msg) to collect errors — NEVER short-circuit inside a loop.
Always return self._pass() once at the very end.

### Requirements

1. Module-level REQUIRED_FIELDS constant (tuple[str, ...]) derived from sample keys.

2. validate(self, data: Any) -> ValidationResult:
   a. If root type is wrong (expected dict but got list, or vice versa):
      self._fail(...) and return self._pass() immediately — before any loop
   b. Iterate REQUIRED_FIELDS: _fail for missing or null fields
   c. Per-field isinstance() type checks for known fields (str, int, dict, list, bool)
   d. Non-empty checks on strings, dicts, and lists where domain requires it
   e. Domain-specific numeric range checks only where spec mandates them
      (e.g. temperature -80..60°C for weather; do NOT invent ranges for other fields)
   f. Collect ALL errors inside each loop — never return mid-loop
   g. return self._pass() exactly once, at the end

3. Full type hints, no I/O, no print(), stdlib + base_validator imports only.

### Pattern to follow exactly (single-dict response — most common case)

    REQUIRED_FIELDS: tuple[str, ...] = ("field_a", "field_b", "field_c")

    class {CLASS_NAME}(BaseValidator):
        def validate(self, data: Any) -> ValidationResult:
            if not isinstance(data, dict):
                self._fail("Response root must be a dict")
                return self._pass()
            for field in REQUIRED_FIELDS:
                if field not in data:
                    self._fail(f"Missing required field: {field!r}")
                elif data[field] is None:
                    self._fail(f"Field {field!r} must not be null")
            # per-field type and domain checks:
            some_str = data.get("field_a")
            if some_str is not None and not isinstance(some_str, str):
                self._fail(f"'field_a' must be str, got {type(some_str).__name__}")
            return self._pass()

### Pattern for list-root responses (e.g. REST Countries /region)

    class {CLASS_NAME}(BaseValidator):
        def validate(self, data: Any) -> ValidationResult:
            if not isinstance(data, list):
                self._fail("Response root must be a list")
                return self._pass()
            for idx, item in enumerate(data):
                if not isinstance(item, dict):
                    self._fail(f"Item {idx} is not a dict")
                    continue
                for field in REQUIRED_FIELDS:
                    if field not in item:
                        self._fail(f"Item {idx} missing {field!r}")
            return self._pass()

Emit only the Python source file. No prose.
```
