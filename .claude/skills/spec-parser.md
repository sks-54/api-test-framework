# Skill: Extract Endpoint Specs From a Specification Document

## Purpose
Given a spec document path, invoke the correct parser via `_load_parser` dispatch,
return `EndpointSpec` objects, update `environments.yaml`, and generate test
skeleton invocations.

## Invocation Input
```
SPEC_PATH: <path to spec document — .pdf, .md, .yaml, .json>
```

## Prompt Template

```
Extract API endpoint specs from: {SPEC_PATH}

### Step 1 — Parse with correct parser (dispatch by suffix)
    from pathlib import Path
    from apitf.spec_parser.pdf_parser import PDFParser
    from apitf.spec_parser.openapi_parser import OpenAPIParser
    from apitf.spec_parser.markdown_parser import MarkdownParser

    suffix = Path("{SPEC_PATH}").suffix.lower()
    if suffix in PDFParser.supported_extensions:
        parser = PDFParser()
    elif suffix in OpenAPIParser.supported_extensions:
        parser = OpenAPIParser()
    elif suffix in MarkdownParser.supported_extensions:
        parser = MarkdownParser()
    else:
        raise SystemExit(f"No parser supports {suffix!r}. Supported: .pdf, .yaml, .json, .md")

    specs = parser.parse(Path("{SPEC_PATH}"))
    if not specs:
        raise SystemExit(f"No specs extracted from {SPEC_PATH}")

### Step 2 — Verify thresholds are empty (document-parsing.md Rule 4)
    for spec in specs:
        if spec.thresholds:
            raise ValueError(f"Parser violation: non-empty thresholds on {spec!r}")

### Step 3 — Merge into environments.yaml (includes probe_path + default thresholds)
    import yaml
    CONFIG = Path("config/environments.yaml")
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    for spec in specs:
        if spec.env_name not in config:
            config[spec.env_name] = {
                "base_url": spec.base_url,
                "probe_path": spec.path,
                "thresholds": {"max_response_time": 5},
            }
    CONFIG.write_text(
        yaml.dump(config, default_flow_style=False, allow_unicode=True, sort_keys=True),
        encoding="utf-8",
    )

### Step 4 — Show test-generator invocations
    for spec in specs:
        print(f"Run test-generator: ENV={spec.env_name} PATH={spec.path} METHOD={spec.method}")

Rules:
- Never split URLs across lines (framework-rules.md Rule 2)
- thresholds always {} from parser — config loader populates them (document-parsing.md Rule 4)
- Log parse errors at WARNING, never swallow them (document-parsing.md Rule 7)
- probe_path is required in environments.yaml — every generated test reads cfg["probe_path"]

Emit step-by-step code. No prose.
```
