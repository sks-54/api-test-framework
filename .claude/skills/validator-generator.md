# Skill: Generate Typed Validator From Sample JSON Response

## Purpose
Given a sample JSON response body, generate a complete typed `BaseValidator`
subclass in `apitf/validators/` that collects ALL errors without short-circuiting.

## Invocation Inputs (all required)
```
SAMPLE_JSON:    <paste raw JSON response body>
ENDPOINT_NAME:  <e.g. "Country Lookup">
CLASS_NAME:     <e.g. CountryValidator>
OUTPUT_MODULE:  <e.g. country_validator>
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
validate() returns ValidationResult. Use self._fail(msg) to collect errors.
Never short-circuit — always return self._pass() at the very end.

### Requirements

1. Module-level REQUIRED_FIELDS constant derived from sample keys.

2. validate(self, data: Any) -> ValidationResult:
   a. Check root type (list or dict) — _fail and return immediately if wrong
   b. For each item: check all REQUIRED_FIELDS present
   c. Per-field isinstance() type checks
   d. Numeric range checks where applicable (population > 0, temp -80..60)
   e. Non-empty checks on strings and lists
   f. Collect ALL errors — never return mid-loop
   g. return self._pass() once at the end

3. Full type hints, no I/O, no print(), stdlib + base_validator imports only.

### Pattern to follow exactly
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
                    self._fail(f"Item {idx} missing '{field}'")
            # per-field checks ...
        return self._pass()

Emit only the Python source file. No prose.
```
