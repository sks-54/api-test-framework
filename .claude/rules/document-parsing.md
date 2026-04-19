# Document Parsing Rules — Spec Parser Subsystem

These rules govern all code in `apitf/spec_parser/`. Violations corrupt
`EndpointSpec` objects and produce silent test-generation failures.

---

## 1. URLs Are Atomic — Parser Implementation of framework-rules.md Rule 2

The framework-wide URL atomicity rule (framework-rules.md Rule 2) applies
here. For parsers specifically, the implementation pattern is regex group(0):

```python
# CORRECT — full URL captured atomically
_URL_PATTERN = re.compile(r"https://[^\s]+")
full_url = match.group(0)  # complete, unmodified

# FORBIDDEN — split and reassembled
pattern = re.compile(r"(https://)([^\s/]+)(/[^\s]*)")
url = m.group(1) + m.group(2) + m.group(3)
```

## 2. Never Split Document Text at Arbitrary Byte Boundaries

```python
# CORRECT — whitespace boundary preserves tokens
tokens = raw_text.split()

# FORBIDDEN — fixed-width chunking may bisect a URL
chunks = [raw_text[i:i+512] for i in range(0, len(raw_text), 512)]
```

## 3. Page Joins Must Use Newline Separator

```python
# CORRECT
full_text = "\n".join(pages)

# FORBIDDEN — empty join fuses tokens across page boundaries
full_text = "".join(pages)
```

## 4. `EndpointSpec.thresholds` Must Always Be `{}` From the Parser

Parsers extract structure only. SLA thresholds are injected later by the
config loader from `config/environments.yaml`.

```python
# CORRECT
EndpointSpec(..., thresholds={})

# FORBIDDEN
EndpointSpec(..., thresholds={"max_response_time": 5.0})
```

## 5. `env_name` Inferred From Hostname — Never Hardcoded

```python
# CORRECT
sld = hostname.split(".")[0].lower()
env_name = _HOSTNAME_ENV_MAP.get(sld, sld)

# FORBIDDEN
EndpointSpec(env_name="countries", ...)  # hardcoded
```

## 6. Supported Extensions Are a Class Attribute — Not Inline

```python
# CORRECT
class PDFParser(BaseSpecParser):
    supported_extensions: tuple[str, ...] = (".pdf", ".PDF")

# FORBIDDEN
def parse(self, source):
    if source.suffix == ".pdf": ...  # inline check; registry can't introspect
```

## 7. Parse Errors Must Be Logged — Never Silently Swallowed

Use `logger = logging.getLogger(__name__)` at module level (see framework-rules.md
Rule 15 for logging standards). Log parse errors at WARNING or ERROR level.

```python
# CORRECT
import logging
logger = logging.getLogger(__name__)

except ValueError as exc:
    logger.warning("Failed line %d: %r — %s", lineno, line, exc)
    continue

# FORBIDDEN
except ValueError:
    continue  # silent — impossible to debug
```
