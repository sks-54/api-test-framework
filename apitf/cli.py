"""
apitf CLI — entry points registered in pyproject.toml.

Commands
--------
apitf-parse  <spec_file> [--json]
    Parse a spec file (PDF, OpenAPI YAML/JSON, Markdown) and print the
    extracted EndpointSpec objects.  Use --json for machine-readable output.

apitf-scaffold <spec_file> --env <env_name> [--out <dir>]
    Parse the spec then emit three ready-to-use artefacts:
      1. YAML snippet  — paste into config/environments.yaml
      2. Validator stub — apitf/validators/<env>_validator.py
      3. Test stub     — tests/test_<env>.py (5 tests, no key required)

    Optional flags:
      --sample        Hit probe_path on the live API to auto-discover fields.
      --ai-generate   Call Claude via ANTHROPIC_API_KEY to generate a full
                      test suite (boundary, equivalence, negative, perf,
                      security, state-based).  Falls back to the 5-test stub
                      if no key is set.
    Prints to stdout by default; --out writes files directly.
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_parser(source: Path):
    """Return the right BaseSpecParser subclass for *source*."""
    from apitf.spec_parser.pdf_parser import PDFParser
    from apitf.spec_parser.openapi_parser import OpenAPIParser
    from apitf.spec_parser.markdown_parser import MarkdownParser

    suffix = source.suffix.lower()
    if suffix in PDFParser.supported_extensions:
        return PDFParser()
    if suffix in OpenAPIParser.supported_extensions:
        return OpenAPIParser()
    if suffix in MarkdownParser.supported_extensions:
        return MarkdownParser()
    print(f"[apitf] Unsupported file type: {suffix}", file=sys.stderr)
    sys.exit(1)


def _specs_from(source: Path):
    parser = _load_parser(source)
    specs = parser.parse(source)
    if not specs:
        print(f"[apitf] No endpoints extracted from {source}", file=sys.stderr)
        sys.exit(1)
    return specs


# ---------------------------------------------------------------------------
# apitf-parse
# ---------------------------------------------------------------------------

def cmd_parse(argv: list[str] | None = None) -> None:
    """Entry point: apitf-parse"""
    p = argparse.ArgumentParser(
        prog="apitf-parse",
        description="Parse a spec file and print the extracted endpoints.",
    )
    p.add_argument("spec_file", type=Path, help="Path to spec file (.pdf, .yaml, .json, .md)")
    p.add_argument("--json", action="store_true", dest="as_json",
                   help="Emit machine-readable JSON (one object per line)")
    args = p.parse_args(argv)

    source = args.spec_file.resolve()
    if not source.exists():
        print(f"[apitf] File not found: {source}", file=sys.stderr)
        sys.exit(1)

    specs = _specs_from(source)

    if args.as_json:
        for s in specs:
            print(json.dumps({
                "env_name": s.env_name,
                "base_url": s.base_url,
                "path": s.path,
                "method": s.method,
                "response_fields": s.response_fields,
                "thresholds": s.thresholds,
                "description": s.description,
            }))
    else:
        print(f"\nExtracted {len(specs)} endpoint(s) from {source.name}\n")
        print(f"{'#':<4} {'METHOD':<8} {'PATH':<40} FIELDS")
        print("-" * 80)
        for i, s in enumerate(specs, 1):
            fields = ", ".join(s.response_fields[:5])
            if len(s.response_fields) > 5:
                fields += f" … (+{len(s.response_fields) - 5} more)"
            print(f"{i:<4} {s.method:<8} {s.path:<40} {fields}")
        print()
        # Warn when all endpoints share the same base URL — common sign that a
        # multi-API PDF's table structure was flattened and base URLs may be wrong.
        unique_bases = {s.base_url for s in specs}
        if len(unique_bases) == 1:
            print(f"Base URL : {specs[0].base_url}")
            print(f"Env name : {specs[0].env_name}")
            if len(specs) > 1:
                print()
                print("[!] All endpoints share one base URL.")
                print("    If this PDF defines multiple APIs, verify the base URL is correct")
                print("    before scaffolding — use --env and set base_url in environments.yaml.")
        else:
            for base in sorted(unique_bases):
                matching = [s for s in specs if s.base_url == base]
                print(f"Base URL : {base}  ({len(matching)} endpoint(s))")
        print()
        print("Next step:")
        print(f"  apitf-scaffold {source} --env <env_name> --sample")


# ---------------------------------------------------------------------------
# apitf-scaffold
# ---------------------------------------------------------------------------

_YAML_SNIPPET = """\
# ── Add this block to config/environments.yaml ──────────────────────────────
{env_name}:
  base_url: {base_url}
  probe_path: {probe_path}
  thresholds:
    max_response_time: 5   # seconds — adjust to your SLA
"""

_VALIDATOR_STUB = '''\
"""Validator for the {env_name} API — generated by apitf-scaffold."""
from __future__ import annotations

from typing import Any

from apitf.validators.base_validator import BaseValidator, ValidationResult

REQUIRED_FIELDS: tuple[str, ...] = ({fields_repr})


class {class_name}(BaseValidator):
    """Validates a single {env_name} API response object."""

    def validate(self, data: Any) -> ValidationResult:
        for field in REQUIRED_FIELDS:
            if field not in data:
                self._fail(f"Missing required field: {{field!r}}")
            elif data[field] is None:
                self._fail(f"Field {{field!r}} must not be null")
        return self._pass()
'''

_TEST_STUB = '''\
"""Tests for the {env_name} API — generated by apitf-scaffold.

Techniques covered by this stub (auto-generated, no AI required):
  TC-001  Positive     — probe_path returns 200
  TC-002  Performance  — response_time_ms < max_response_time (from env_config)
  TC-003  Schema       — response body passes {class_name} contract
  TC-004  Security     — HttpClient rejects http:// base URLs
  TC-005  Negative 404 — unknown resource path returns 4xx

Extend with boundary, state-based, and equivalence tests using the
Claude Code skill:  /test-generator ENV_NAME={env_name} ...
Run with:  pytest --env {env_name} -v
"""
from __future__ import annotations

from typing import Any

import allure
import pytest

from apitf.http_client import HttpClient
from apitf.validators.{module_name}_validator import {class_name}

pytestmark = [pytest.mark.{env_name}, allure.suite("{env_name}")]


@allure.title("TC-001: {env_name} probe_path returns 200")
@pytest.mark.equivalence
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_{env_name}_positive_baseline(env_config: dict[str, Any]) -> None:
    cfg = env_config["{env_name}"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get(cfg["probe_path"])
    assert resp.status_code == 200, f"Expected 200, got {{resp.status_code}}"


@allure.title("TC-002: {env_name} response time < max_response_time SLA")
@pytest.mark.performance
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_{env_name}_performance(env_config: dict[str, Any]) -> None:
    cfg = env_config["{env_name}"]
    max_ms = cfg["thresholds"]["max_response_time"] * 1000
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get(cfg["probe_path"])
    assert resp.status_code == 200
    assert resp.response_time_ms < max_ms, (
        f"SLA breach: {{resp.response_time_ms:.0f}}ms > {{max_ms:.0f}}ms"
    )


@allure.title("TC-003: {env_name} response body passes {class_name} schema")
@pytest.mark.equivalence
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_{env_name}_schema(env_config: dict[str, Any]) -> None:
    cfg = env_config["{env_name}"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get(cfg["probe_path"])
    assert resp.status_code == 200
    body = resp.json_body
    item = body[0] if isinstance(body, list) else body
    result = {class_name}().validate(item)
    assert result.passed, result.errors


@allure.title("TC-004: {env_name} HttpClient rejects http:// (HTTPS enforced)")
@pytest.mark.security
def test_{env_name}_https_enforced() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        HttpClient("http://{base_host}")


@allure.title("TC-005: {env_name} unknown path returns 4xx")
@pytest.mark.negative
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_{env_name}_not_found(env_config: dict[str, Any]) -> None:
    cfg = env_config["{env_name}"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/__apitf_nonexistent_path__")
    assert resp.status_code in (400, 404, 405), (
        f"Expected 4xx for unknown path, got {{resp.status_code}}"
    )
'''


def _sample_fields(base_url: str, probe_path: str, existing: list[str]) -> list[str]:
    """Hit the live API and return top-level field names from the first response object."""
    try:
        from apitf.http_client import HttpClient
        print(f"[apitf] Sampling live API: {base_url}{probe_path} …")
        with HttpClient(base_url) as client:
            resp = client.get(probe_path)
        body = resp.json_body
        item = body[0] if isinstance(body, list) and body else body
        if isinstance(item, dict):
            discovered = list(item.keys())
            # Live sample is the ground truth for the probe endpoint.
            # Spec fields from *other* endpoints in a multi-endpoint PDF would
            # corrupt REQUIRED_FIELDS — discard them when sampling succeeds.
            print(f"[apitf] Discovered fields: {', '.join(discovered)}")
            return discovered
    except Exception as exc:
        print(f"[apitf] --sample failed ({exc}), using spec fields only", file=sys.stderr)
    return existing


def _ai_generate_tests(
    env: str,
    class_name: str,
    module_name: str,
    base_url: str,
    probe_path: str,
    all_fields: list[str],
    specs: list,
    model: str = "claude-sonnet-4-6",
    api_key: str | None = None,
) -> str | None:
    """Call Claude to generate a full 7-technique test suite.

    Key resolution priority (auto-detect first):
      1. Explicit api_key argument (from --api-key flag)
      2. ANTHROPIC_API_KEY environment variable (auto-detected)
      3. Neither found → returns None, caller falls back to 5-test stub
    """
    from apitf.eval_loop import detect_ai_mode
    resolved_key, key_source = detect_ai_mode(api_key)

    if not resolved_key:
        print(
            "[apitf] AI generation: no key found "
            "(checked --api-key flag and ANTHROPIC_API_KEY env var).\n"
            "        Falling back to 5-test stub. "
            "Set ANTHROPIC_API_KEY or pass --api-key to enable full suite.",
            flush=True,
        )
        return None

    source_label = {
        "claude_cli": "Claude Code session",
        "explicit": "explicit --api-key",
        "env": "ANTHROPIC_API_KEY env var",
        "dotenv": ".env file",
    }.get(key_source, key_source)
    print(f"[apitf] AI generation: {source_label} → calling {model} …", flush=True)

    try:
        import anthropic
    except ImportError:
        print(
            "[apitf] AI generation: 'anthropic' package not installed — pip install anthropic.\n"
            "        Falling back to 5-test stub.",
            flush=True,
        )
        return None

    endpoints_summary = "\n".join(
        f"  {s.method} {s.path}  fields: {', '.join(s.response_fields) or '(use REQUIRED_FIELDS)'}"
        for s in specs
    )

    prompt = f"""Generate a complete pytest test file for this API.

Environment : {env}
Base URL    : {base_url}
Probe path  : {probe_path}
Validator   : {class_name} (from apitf/validators/{module_name}_validator.py)
Fields      : {', '.join(all_fields[:15])}

Endpoints extracted from spec:
{endpoints_summary}

Framework rules (non-negotiable):
- pytestmark = [pytest.mark.{env}, allure.suite("{env}")]
- @allure.title("TC-XXX: ...") on every test
- HttpClient from apitf.http_client — never raw requests

env_config is a PYTEST FIXTURE injected by conftest.py — NEVER import it from a module.
Each test function receives it as a parameter:
    def test_foo(env_config: dict) -> None:
        cfg = env_config["{env}"]
        with HttpClient(cfg["base_url"]) as client:
            resp = client.get("{probe_path}")

- All thresholds from cfg["thresholds"]["max_response_time"] — zero hardcoded numbers
- @pytest.mark.flaky(reruns=2, reruns_delay=2) on every live HTTP call
- No @pytest.mark.flaky on xfail tests or HTTPS-enforcement tests (those don't make a real request)
- from apitf.sla_exceptions import SLA_FAILURE_EXCEPTIONS for all xfail raises=
- xfail must use strict=True ONLY for confirmed API bugs with a filed issue
  Do NOT add xfail to performance tests — write a plain assertion against the SLA threshold
- Full type hints, -> None return type on every function
- No print(), no prose comments in code
- Negative tests assert the EXACT expected status code (never >= 400 or ranges)
- Validator: result = {class_name}().validate(resp.json_body); assert result.passed, result.errors
  (NEVER: {class_name}(data).validate() — data goes into validate(), NOT __init__)
- HttpClient is used as a context manager: with HttpClient(cfg["base_url"]) as client:

HttpResponse attributes (use ONLY these — do NOT use .json() or .elapsed):
- resp.status_code      -> int
- resp.json_body        -> dict | list  (parsed JSON)
- resp.response_time_ms -> float        (milliseconds)
- resp.headers          -> dict

For the HTTPS security test (no live request):
    import pytest
    from apitf.http_client import HttpClient
    with pytest.raises(ValueError, match="HTTPS"):
        HttpClient(cfg["base_url"].replace("https://", "http://"))

Do NOT reference cfg["boundaries"] or cfg["insecure_base_url"] — those keys do not exist.
Use literal integers for edge IDs: id=1 (minimum), id=9999 (out-of-range beyond max).

Techniques to cover (at least one test each):
1. Equivalence partitioning — valid input values
2. Boundary — edge case inputs (empty, min/max values)
3. Positive — valid request returns 200 + schema valid via {class_name}
4. Negative — invalid input returns exact 4xx status code
5. Performance — response_time_ms < cfg["thresholds"]["max_response_time"] * 1000
6. Security — HttpClient("http://...") raises ValueError matching "HTTPS"
7. State-based — response structure reflects expected state

Output ONLY the Python source for tests/test_{module_name}.py. No prose, no markdown fences."""

    try:
        from apitf.eval_loop import _claude_cli_call
        if key_source == "claude_cli":
            src = _claude_cli_call(prompt, model)
        else:
            import anthropic
            client = anthropic.Anthropic(api_key=resolved_key)
            message = client.messages.create(
                model=model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            src = message.content[0].text.strip()
        from apitf.eval_loop import _strip_fences
        src = _strip_fences(src)
        print("[apitf] AI generation: full 7-technique test suite generated.", flush=True)
        return src
    except Exception as exc:
        print(
            f"[apitf] AI generation: call failed ({exc}) — falling back to 5-test stub.",
            flush=True,
        )
        return None


def cmd_scaffold(argv: list[str] | None = None) -> None:
    """Entry point: apitf-scaffold"""
    p = argparse.ArgumentParser(
        prog="apitf-scaffold",
        description="Parse a spec and emit a YAML snippet, validator, and test stub.",
    )
    p.add_argument("spec_file", type=Path, help="Path to spec file")
    p.add_argument("--env", required=True, metavar="ENV_NAME",
                   help="Environment key to use (e.g. 'myapi')")
    p.add_argument("--out", type=Path, default=None, metavar="DIR",
                   help="Write files to DIR instead of printing to stdout")
    p.add_argument("--sample", action="store_true",
                   help="Hit probe_path on the live API to auto-discover response fields")
    p.add_argument("--base-url", default=None, metavar="URL",
                   help="Override the base URL detected from the spec (useful when PDF "
                        "parser picks the wrong URL in a multi-API document)")
    p.add_argument("--probe-path", default=None, metavar="PATH",
                   help="Override the probe path used for --sample (default: first extracted path)")
    p.add_argument("--ai-generate", action="store_true",
                   help="Attempt AI-powered full test suite (auto-detects ANTHROPIC_API_KEY; "
                        "falls back to 5-test stub if no key found). Explicit key via --api-key.")
    p.add_argument("--api-key", default=None, metavar="KEY",
                   help="Anthropic API key. If omitted, ANTHROPIC_API_KEY env var is used automatically.")
    p.add_argument("--model", default="claude-sonnet-4-6", metavar="MODEL_ID",
                   help="Claude model for AI generation (default: claude-sonnet-4-6). "
                        "Examples: claude-opus-4-7, claude-haiku-4-5-20251001")
    args = p.parse_args(argv)

    source = args.spec_file.resolve()
    if not source.exists():
        print(f"[apitf] File not found: {source}", file=sys.stderr)
        sys.exit(1)

    env = args.env
    specs = _specs_from(source)

    # Derive names
    class_name = "".join(w.title() for w in env.replace("-", "_").split("_")) + "Validator"
    module_name = env.replace("-", "_")
    base_url = args.base_url or specs[0].base_url
    probe_path = args.probe_path or (specs[0].path if specs else "/")
    if args.base_url:
        print(f"[apitf] Using override base URL: {base_url}")

    # Collect fields: from spec first, then optionally from live API
    all_fields: list[str] = []
    for s in specs:
        for f in s.response_fields:
            if f not in all_fields:
                all_fields.append(f)

    if args.sample:
        all_fields = _sample_fields(base_url, probe_path, all_fields)

    fields_repr = ", ".join(f'"{f}"' for f in all_fields[:10])
    if all_fields:
        fields_repr += ","  # trailing comma for tuple

    yaml_block = _YAML_SNIPPET.format(
        env_name=env, base_url=base_url, probe_path=probe_path,
    )
    validator_src = _VALIDATOR_STUB.format(
        env_name=env, class_name=class_name, fields_repr=fields_repr,
    )
    base_host = base_url.replace("https://", "").split("/")[0]
    test_src = _TEST_STUB.format(
        env_name=env, class_name=class_name, module_name=module_name,
        base_host=base_host,
    )
    if args.ai_generate:
        ai_src = _ai_generate_tests(
            env, class_name, module_name, base_url, probe_path, all_fields, specs,
            args.model, api_key=args.api_key,
        )
        if ai_src:
            test_src = ai_src

    if args.out:
        out = args.out.resolve()
        out.mkdir(parents=True, exist_ok=True)

        val_path = out / f"{module_name}_validator.py"
        test_path = out / f"test_{module_name}.py"
        yaml_path = out / f"{env}_yaml_snippet.txt"

        val_path.write_text(validator_src, encoding="utf-8")
        test_path.write_text(test_src, encoding="utf-8")
        yaml_path.write_text(yaml_block, encoding="utf-8")

        print(f"[apitf] Written to {out}/")
        print(f"  {val_path.name}  →  copy to apitf/validators/")
        print(f"  {test_path.name}  →  copy to tests/")
        print(f"  {yaml_path.name}  →  paste into config/environments.yaml")
    else:
        _section("1. Paste into config/environments.yaml", yaml_block)
        _section(f"2. Save as apitf/validators/{module_name}_validator.py", validator_src)
        _section(f"3. Save as tests/test_{module_name}.py", test_src)
        print("Then run:  pytest --env", env, "-v")


def _section(title: str, body: str) -> None:
    bar = "─" * 70
    print(f"\n{bar}")
    print(f"  {title}")
    print(bar)
    print(textwrap.indent(body.strip(), "  "))
    print()


def _generate_test_plan(
    env: str,
    base_url: str,
    probe_path: str,
    all_fields: list[str],
    specs: list,
    project_root: Path,
) -> Path:
    """Write a TEST_PLAN.md-style document to test_plans/<env>_test_plan.md.

    Covers 10 techniques with per-endpoint TC generation, P1/P2/P3 priority,
    risk & mitigations, and acceptance criteria — matching the gold standard.
    """
    plan_dir = project_root / "test_plans"
    plan_dir.mkdir(exist_ok=True)
    plan_path = plan_dir / f"{env}_test_plan.md"

    prefix = env[:3].upper()
    validator_class = f"{env.replace('_', ' ').title().replace(' ', '')}Validator"
    fields_list = ", ".join(f"`{f}`" for f in all_fields[:10]) or "_(sampled at scaffold time)_"

    # --- Section 1: Scope ---
    in_scope_rows = "\n".join(
        f"| `{s.method}` | `{s.path}` "
        f"| {', '.join(f'`{f}`' for f in s.response_fields[:5]) or '—'} |"
        for s in specs
    )

    # --- Section 2: Approach matrix ---
    approach_rows = (
        f"| Positive (happy path)      | P1 | 1 per endpoint | Valid request → HTTP 200 + JSON |\n"
        f"| Schema validation          | P1 | 1 per endpoint | `{validator_class}().validate()` passes |\n"
        f"| Equivalence partitioning   | P2 | 1 per endpoint | Representative valid input → 200 |\n"
        f"| Boundary value analysis    | P2 | 2 per endpoint | Min/max identifier edge cases |\n"
        f"| Negative / error paths     | P1 | 2 fixed        | Unknown path 404, bad params 400 |\n"
        f"| Error handling             | P2 | 1 fixed        | Malformed input → 4xx, not 5xx |\n"
        f"| Performance / SLA          | P1 | 1 fixed        | `{probe_path}` < `max_response_time` (YAML) |\n"
        f"| Reliability                | P2 | 1 fixed        | `@pytest.mark.flaky(reruns=2)` |\n"
        f"| Security                   | P1 | 2 fixed        | HTTPS enforcement + OWASP headers |\n"
        f"| Compatibility              | P3 | 1 fixed        | Python 3.9 + 3.12 matrix |"
    )

    # --- Section 3: Test Cases table ---
    tc_rows: list[str] = []
    tc_num = 1

    for s in specs:
        endpoint = f"`{s.method} {s.path}`"
        fields_str = (
            ", ".join(f"`{f}`" for f in s.response_fields[:4])
            or "_(sampled)_"
        )

        tc_rows.append(
            f"| TC-{prefix}-{tc_num:03d} | {endpoint} | Positive | "
            f"Valid request returns 200 and JSON body | Standard params | "
            f"HTTP 200, `Content-Type: application/json` | P1 |"
        )
        tc_num += 1

        tc_rows.append(
            f"| TC-{prefix}-{tc_num:03d} | {endpoint} | Schema | "
            f"Response fields {fields_str} present and typed | Valid request | "
            f"`{validator_class}().validate()` passes | P1 |"
        )
        tc_num += 1

        tc_rows.append(
            f"| TC-{prefix}-{tc_num:03d} | {endpoint} | Equivalence | "
            f"Representative valid input class | Nominal params | HTTP 200 | P2 |"
        )
        tc_num += 1

        tc_rows.append(
            f"| TC-{prefix}-{tc_num:03d} | {endpoint} | Boundary | "
            f"Minimum identifier value | edge-case id=1 or equivalent | "
            f"HTTP 200 or 404, not 500 | P2 |"
        )
        tc_num += 1

        tc_rows.append(
            f"| TC-{prefix}-{tc_num:03d} | {endpoint} | Boundary | "
            f"Empty / maximum identifier | `''` or out-of-range id | "
            f"HTTP 4xx, not 500 | P2 |"
        )
        tc_num += 1

    # Fixed TCs — shared across all envs
    base_ep = f"`GET {probe_path}`"
    tc_rows.append(
        f"| TC-{prefix}-{tc_num:03d} | `GET /__apitf_nonexistent__` | Negative | "
        f"Unknown path returns 404 | Invalid path | HTTP 404 exactly | P1 |"
    )
    tc_num += 1

    tc_rows.append(
        f"| TC-{prefix}-{tc_num:03d} | {base_ep} | Negative | "
        f"Missing required params returns 400 | Omit required param | HTTP 400 or 422 | P1 |"
    )
    tc_num += 1

    tc_rows.append(
        f"| TC-{prefix}-{tc_num:03d} | {base_ep} | Error Handling | "
        f"Malformed request does not trigger 5xx | Malformed query | HTTP 4xx, not 5xx | P2 |"
    )
    tc_num += 1

    tc_rows.append(
        f"| TC-{prefix}-{tc_num:03d} | {base_ep} | Performance | "
        f"Response within SLA threshold | Standard params | "
        f"< `max_response_time` × 1000 ms (YAML, never hardcoded) | P1 |"
    )
    tc_num += 1

    tc_rows.append(
        f"| TC-{prefix}-{tc_num:03d} | {base_ep} | Reliability | "
        f"Transient failure retried and recovered | Network blip | "
        f"Pass on retry ≤ 2; `@pytest.mark.flaky(reruns=2)` | P2 |"
    )
    tc_num += 1

    tc_rows.append(
        f"| TC-{prefix}-{tc_num:03d} | `HttpClient('http://...')` | Security | "
        f"HTTP (not HTTPS) is rejected at construction | Plain-HTTP base URL | "
        f"`ValueError` raised, message contains `'HTTPS'` | P1 |"
    )
    tc_num += 1

    tc_rows.append(
        f"| TC-{prefix}-{tc_num:03d} | {base_ep} | Security | "
        f"OWASP security headers present in response | Standard request | "
        f"`Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options` present | P1 |"
    )
    tc_num += 1

    tc_rows.append(
        f"| TC-{prefix}-{tc_num:03d} | _(matrix)_ | Compatibility | "
        f"Framework runs cleanly on Python 3.9 and 3.12 | CI matrix | "
        f"All tests pass on ubuntu/3.9 + ubuntu/3.12 (Rule 26) | P3 |"
    )

    tc_table = "\n".join(tc_rows)
    total_tcs = tc_num  # last tc_num value (1-indexed count)

    # --- Section 6: Acceptance criteria ---
    accept_rows = (
        "| Positive        | All endpoints return HTTP 200 with `Content-Type: application/json` |\n"
        "| Schema          | `{vc}().validate()` returns `passed=True` for every endpoint |\n"
        "| Equivalence     | Representative valid input returns HTTP 200 |\n"
        "| Boundary        | Edge identifiers return 200/404 — never 500 |\n"
        "| Negative        | Exact 4xx status asserted (no ranges, no `>= 400`) |\n"
        "| Error Handling  | Malformed requests produce 4xx, never 5xx |\n"
        "| Performance     | Response time < YAML threshold on every run (Rule 1 — never hardcoded) |\n"
        "| Reliability     | All live-API tests decorated `@pytest.mark.flaky(reruns=2)` |\n"
        "| Security        | HTTPS guard raises `ValueError`; OWASP headers confirmed present |\n"
        "| Compatibility   | CI gate green on Python 3.9 + 3.12 (Rule 26) |"
    ).replace("{vc}", validator_class)

    content = f"""# Test Plan — `{env}` environment

**Base URL:** `{base_url}`
**Probe path:** `{probe_path}`
**Generated:** `apitf-run` scaffold step
**Framework rules:** testing-standards.md, framework-rules.md

---

## Table of Contents

1. [Scope](#1-scope)
2. [Approach & Techniques](#2-approach--techniques)
3. [Test Cases](#3-test-cases)
4. [Test Data & Configuration](#4-test-data--configuration)
5. [Environment & Infrastructure](#5-environment--infrastructure)
6. [Acceptance Criteria](#6-acceptance-criteria)
7. [Risk & Mitigations](#7-risk--mitigations)

---

## 1. Scope

### In Scope

| Method | Path | Sampled response fields |
|--------|------|-------------------------|
{in_scope_rows}

**All sampled fields:** {fields_list}

### Out of Scope

- Write operations (POST / PUT / PATCH / DELETE) unless the spec requires them
- Authentication flows (API keys, OAuth) — covered by the security technique only at the HTTP layer
- Third-party downstream systems beyond `{base_url}`
- Load / stress testing (> 1 concurrent request)

---

## 2. Approach & Techniques

| Technique | Priority | TC count | Rationale |
|-----------|----------|----------|-----------|
{approach_rows}

---

## 3. Test Cases

### {env} API Test Cases

| ID | Endpoint | Technique | Description | Input | Expected | Priority |
|----|----------|-----------|-------------|-------|----------|----------|
{tc_table}

**Total: {total_tcs} test cases**

---

## 4. Test Data & Configuration

- **Thresholds:** all numeric limits read from `config/environments.yaml` via `env_config` fixture — never hardcoded (Rule 1)
- **Coordinates / identifiers:** loaded from `test_data/` JSON files — never inline literals (Testing Standard 1)
- **Base URL:** `{base_url}` (single source: `config/environments.yaml`)
- **Probe path:** `{probe_path}`
- **Sampled fields:** `{fields_list}`

---

## 5. Environment & Infrastructure

| Item | Value |
|------|-------|
| Target API | `{base_url}` |
| Python versions | 3.9, 3.11, 3.12 |
| CI runners | ubuntu-latest (smoke + versions), windows-latest, macos-latest (platform) |
| Report format | Allure HTML (`allure serve allure-results`) |
| Retry policy | `@pytest.mark.flaky(reruns=2, reruns_delay=2)` on all live-HTTP tests |
| SLA threshold | `env_config["thresholds"]["max_response_time"]` seconds |

```bash
# Run all tests for this environment
pytest --env {env} -v --alluredir=allure-results

# Run by technique
pytest --env {env} -m security -v
pytest --env {env} -m performance -v
pytest --env {env} -m compatibility -v
```

---

## 6. Acceptance Criteria

| Technique | Pass condition |
|-----------|---------------|
{accept_rows}

Zero `STRUCTURAL_FAILURE` or `QUALITY_FAILURE` categories in the eval loop final report.

---

## 7. Risk & Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | Live API unavailable during CI | Medium | High | `@pytest.mark.flaky(reruns=2)` — classify as `ENV_FAILURE` after 2 retries; do not consume iteration budget (Rule 10) |
| R2 | SLA threshold exceeded consistently | Low | Medium | Classify as `SLA_VIOLATION`; file GitHub issue; mark `xfail(strict=True)` — never raise YAML threshold (Rule 21) |
| R3 | Schema change breaks `{validator_class}` | Low | High | Schema validation TC (P1) surfaces mismatch immediately; file `QUALITY_FAILURE` bug |
| R4 | OWASP headers removed by API operator | Low | High | Security TC (P1) fails; file bug; `xfail(strict=True)` until resolved |
| R5 | Python version incompatibility | Low | Medium | Compatibility TC (P3) in CI matrix (ubuntu/3.9 + ubuntu/3.12); fails gate before merge (Rule 26) |
"""
    plan_path.write_text(content, encoding="utf-8")
    return plan_path


def _wire_environments_yaml(env: str, base_url: str, probe_path: str, project_root: Path) -> None:
    """Add env block to environments.yaml if not already present."""
    import yaml
    yaml_path = project_root / "config" / "environments.yaml"
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    if env in data:
        print(f"[apitf-run] environments.yaml: '{env}' already present — skipping")
        return
    data[env] = {
        "base_url": base_url,
        "probe_path": probe_path,
        "thresholds": {"max_response_time": 5},
    }
    yaml_path.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=True),
        encoding="utf-8",
    )
    print(f"[apitf-run] environments.yaml: added '{env}'")


def _wire_pytest_ini_marker(env: str, project_root: Path) -> None:
    """Add env marker to pytest.ini markers block if not already present."""
    ini_path = project_root / "pytest.ini"
    content = ini_path.read_text(encoding="utf-8")
    if f"\n    {env}:" in content or f"\n    {env} " in content:
        print(f"[apitf-run] pytest.ini: marker '{env}' already present — skipping")
        return
    lines = content.splitlines()
    new_lines: list[str] = []
    in_markers = False
    inserted = False
    for line in lines:
        if line.startswith("markers"):
            in_markers = True
        elif in_markers and line.strip() and not line.startswith(" ") and not line.startswith("\t"):
            if not inserted:
                new_lines.append(f"    {env}: environment-scoped tests for the {env} API")
                inserted = True
            in_markers = False
        new_lines.append(line)
    if in_markers and not inserted:
        new_lines.append(f"    {env}: environment-scoped tests for the {env} API")
    ini_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"[apitf-run] pytest.ini: added marker '{env}'")


# ---------------------------------------------------------------------------
# apitf-run  (full workflow: parse → scaffold → eval loop → reflector)
# ---------------------------------------------------------------------------

def cmd_run(argv: list[str] | None = None) -> None:
    """Entry point: apitf-run — parse → scaffold → eval loop → Opus reflector."""
    p = argparse.ArgumentParser(
        prog="apitf-run",
        description=(
            "Full automated workflow:\n"
            "  1. Parse spec file\n"
            "  2. Generate validator + test file (AI-powered if ANTHROPIC_API_KEY set)\n"
            "  3. Run eval loop (auto-fix structural errors, up to --max-iter rounds)\n"
            "  4. Opus reflector review (scores the final test file)\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("spec_file", type=Path, help="Path to spec file (.pdf, .yaml, .md)")
    p.add_argument("--env", required=True, metavar="ENV_NAME",
                   help="Environment key — used in YAML, validator, and test filenames")
    p.add_argument("--base-url", default=None, metavar="URL",
                   help="Override base URL detected from spec")
    p.add_argument("--probe-path", default=None, metavar="PATH",
                   help="Override probe path for live sampling")
    p.add_argument("--sample", action="store_true",
                   help="Hit live API to auto-discover response fields")
    p.add_argument("--api-key", default=None, metavar="KEY",
                   help="Anthropic API key. Auto-detected from ANTHROPIC_API_KEY if not provided. "
                        "Without a key: 5-test stub is generated and reflector is skipped.")
    p.add_argument("--model", default="claude-sonnet-4-6", metavar="MODEL_ID",
                   help="Model for test generation and structural fixes (default: claude-sonnet-4-6)")
    p.add_argument("--reflector-model", default="claude-opus-4-7", metavar="MODEL_ID",
                   help="Model for Opus reflector review (default: claude-opus-4-7)")
    p.add_argument("--max-iter", type=int, default=3, metavar="N",
                   help="Max eval-loop iterations (default: 3)")
    args = p.parse_args(argv)

    source = args.spec_file.resolve()
    if not source.exists():
        print(f"[apitf-run] File not found: {source}", file=sys.stderr)
        sys.exit(1)

    env = args.env
    project_root = Path(__file__).parent.parent

    # ── AI mode detection (upfront, before any steps) ──────────────────────
    from apitf.eval_loop import detect_ai_mode
    resolved_key, key_source = detect_ai_mode(args.api_key)
    if resolved_key:
        ai_label = {
            "claude_cli": "Claude Code session (auto-detected via CLAUDECODE + claude CLI)",
            "explicit": "explicit --api-key",
            "env": "ANTHROPIC_API_KEY env var (auto-detected)",
            "dotenv": ".env file in project root (auto-detected)",
        }.get(key_source, key_source)
        print(f"[apitf-run] AI mode   : {ai_label}", flush=True)
        print(f"[apitf-run] Gen model : {args.model}", flush=True)
        print(f"[apitf-run] Reflector : {args.reflector_model}", flush=True)
    else:
        print("[apitf-run] AI mode   : none — no key found", flush=True)
        print("[apitf-run]             Checked: --api-key flag, ANTHROPIC_API_KEY env var, .env file", flush=True)
        print("[apitf-run]             Test stub: 5-test baseline. Reflector: skipped.", flush=True)
        print("[apitf-run]             To enable: export ANTHROPIC_API_KEY=sk-ant-... OR add to .env", flush=True)

    # ── Step 1: Parse ──────────────────────────────────────────────────────
    print(f"\n{'='*60}", flush=True)
    print(f"[apitf-run] Step 1/4 — Parse: {source.name}", flush=True)
    print(f"{'='*60}", flush=True)
    specs = _specs_from(source)
    print(f"[apitf-run] Extracted {len(specs)} endpoint(s)", flush=True)

    # ── Step 2: Scaffold ───────────────────────────────────────────────────
    print(f"\n{'='*60}", flush=True)
    print(f"[apitf-run] Step 2/4 — Scaffold: env='{env}'", flush=True)
    print(f"{'='*60}", flush=True)

    class_name = "".join(w.title() for w in env.replace("-", "_").split("_")) + "Validator"
    module_name = env.replace("-", "_")
    base_url = args.base_url or specs[0].base_url
    probe_path = args.probe_path or (specs[0].path if specs else "/")

    if args.base_url:
        print(f"[apitf-run] Using override base URL: {base_url}", flush=True)

    all_fields: list[str] = []
    for s in specs:
        for f in s.response_fields:
            if f not in all_fields:
                all_fields.append(f)

    if args.sample:
        all_fields = _sample_fields(base_url, probe_path, all_fields)

    fields_repr = ", ".join(f'"{f}"' for f in all_fields[:10])
    if all_fields:
        fields_repr += ","

    validator_src = _VALIDATOR_STUB.format(
        env_name=env, class_name=class_name, fields_repr=fields_repr,
    )
    base_host = base_url.replace("https://", "").split("/")[0]

    # Always attempt AI-generate first; fall back to stub if no key
    test_src = _ai_generate_tests(
        env, class_name, module_name, base_url, probe_path, all_fields, specs,
        args.model, api_key=resolved_key,
    )
    if test_src is None:
        test_src = _TEST_STUB.format(
            env_name=env, class_name=class_name, module_name=module_name,
            base_host=base_host,
        )

    # Write files into project dirs
    validator_path = project_root / "apitf" / "validators" / f"{module_name}_validator.py"
    test_path = project_root / "tests" / f"test_{module_name}.py"

    validator_path.write_text(validator_src, encoding="utf-8")
    test_path.write_text(test_src, encoding="utf-8")
    print(f"[apitf-run] Validator : {validator_path.relative_to(project_root)}")
    print(f"[apitf-run] Test file : {test_path.relative_to(project_root)}")

    plan_path = _generate_test_plan(env, base_url, probe_path, all_fields, specs, project_root)
    print(f"[apitf-run] Test plan : {plan_path.relative_to(project_root)}")

    from apitf.eval_loop import reflect_test_plan_loop
    reflect_test_plan_loop(
        env=env,
        plan_path=plan_path,
        model=args.model,
        reflector_model=args.reflector_model,
        api_key=resolved_key,
    )

    _wire_environments_yaml(env, base_url, probe_path, project_root)
    _wire_pytest_ini_marker(env, project_root)

    # ── Step 3 + 4: Eval loop + Reflector ─────────────────────────────────
    print(f"\n{'='*60}")
    print(f"[apitf-run] Step 3/4 — Eval loop (max {args.max_iter} iterations)")
    print(f"{'='*60}")

    from apitf.eval_loop import eval_loop
    results = eval_loop(
        env=env,
        test_file=test_path,
        max_iter=args.max_iter,
        model=args.model,
        reflector_model=args.reflector_model,
        api_key=resolved_key,
    )

    # ── Final report ───────────────────────────────────────────────────────
    final = results[-1]
    print(f"\n{'='*60}")
    print(f"[apitf-run] Step 4/4 — Final Report  (env: {env})")
    print(f"{'='*60}")
    print(f"  Iterations run : {len(results)}")
    print(f"  Final state    : {'CLEAN ✓' if final.clean else 'FAILURES REMAIN ✗'}")
    print(f"  Tests passed   : {final.passed}")
    print(f"  Tests failed   : {final.failed}")
    print(f"  xfailed        : {final.xfailed}")
    if not final.clean and final.failures:
        print("\n  Remaining failures:")
        for f in final.failures:
            print(f"    [{f.category}] {f.test_name}")
    print(f"\n  Validator : apitf/validators/{module_name}_validator.py")
    print(f"  Tests     : tests/test_{module_name}.py")
    print(f"\n  Manually re-run: pytest --env {env} -v")

    sys.exit(0 if final.clean else 1)
