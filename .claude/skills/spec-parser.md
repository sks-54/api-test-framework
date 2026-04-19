# Skill: Extract Endpoint Specs From a Specification Document

## Purpose
Given a spec document path, invoke the correct parser via `SpecParserRegistry`,
return `EndpointSpec` objects, update `environments.yaml`, and generate test
skeleton invocations.

## Invocation Input
```
SPEC_PATH: <path to spec document — .pdf, .md, .yaml, .json>
```

## Prompt Template

```
Extract API endpoint specs from: {SPEC_PATH}

### Step 1 — Parse via registry
    from pathlib import Path
    from apitf.spec_parser.base_parser import SpecParserRegistry
    from apitf.spec_parser.pdf_parser import PDFParser

    registry = SpecParserRegistry()
    registry.register(PDFParser())
    specs = registry.parse(Path("{SPEC_PATH}"))

    if not specs:
        raise SystemExit(f"No specs extracted from {SPEC_PATH}")

### Step 2 — Verify thresholds are empty
    for spec in specs:
        assert spec.thresholds == {}, f"Parser violation: non-empty thresholds on {spec}"

### Step 3 — Merge into environments.yaml
    import yaml
    CONFIG = Path("config/environments.yaml")
    config = yaml.safe_load(CONFIG.read_text()) or {}
    for spec in specs:
        env = config.setdefault(spec.env_name, {"base_url": spec.base_url, "thresholds": {}})
    CONFIG.write_text(yaml.dump(config, default_flow_style=False))

### Step 4 — Show test-generator invocations
    for spec in specs:
        print(f"Run test-generator: ENV={spec.env_name} PATH={spec.path} METHOD={spec.method}")

Rules:
- Never split URLs across lines
- thresholds always {} from parser — config loader populates them
- Log parse errors, never swallow them

Emit step-by-step code. No prose.
```
