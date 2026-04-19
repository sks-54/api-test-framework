"""OpenAPI 3.x / Swagger 2.x spec parser — YAML and JSON formats."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from urllib.parse import urlparse

import yaml

from apitf.spec_parser.base_parser import BaseSpecParser, EndpointSpec

logger = logging.getLogger(__name__)

# HTTP methods that carry response schemas worth validating
_RESPONSE_METHODS = {"get", "post", "put", "patch"}


class OpenAPIParser(BaseSpecParser):
    """Parse OpenAPI 3.x / Swagger 2.x YAML or JSON specs into EndpointSpec objects.

    Reads `servers[0].url` as the base_url and iterates every path × method
    combination. Response field names are extracted from the first 200-response
    schema (properties keys or items.properties keys for arrays).
    Thresholds are always left as {} — injected later from environments.yaml.
    """

    supported_extensions: tuple[str, ...] = (".yaml", ".yml", ".json")

    def parse(self, source: Path) -> list[EndpointSpec]:
        raw = source.read_text(encoding="utf-8")
        try:
            doc = yaml.safe_load(raw) if source.suffix in (".yaml", ".yml") else json.loads(raw)
        except Exception as exc:
            logger.warning("Failed to parse %s: %s", source, exc)
            return []

        base_url = self._base_url(doc, source)
        env_name = self._env_name(base_url)
        specs: list[EndpointSpec] = []

        for path, path_item in (doc.get("paths") or {}).items():
            if not isinstance(path_item, dict):
                continue
            for method, operation in path_item.items():
                if method.lower() not in _RESPONSE_METHODS:
                    continue
                if not isinstance(operation, dict):
                    continue
                fields = self._response_fields(operation, doc)
                description = operation.get("summary") or operation.get("description") or ""
                specs.append(EndpointSpec(
                    env_name=env_name,
                    base_url=base_url,
                    path=path,
                    method=method.upper(),
                    response_fields=fields,
                    thresholds={},
                    description=description,
                ))
                logger.debug("Extracted: %s %s %s", env_name, method.upper(), path)

        if not specs:
            logger.warning("No endpoints extracted from %s", source)
        return specs

    # ------------------------------------------------------------------

    def _base_url(self, doc: dict, source: Path) -> str:
        # OpenAPI 3.x
        servers = doc.get("servers") or []
        if servers and isinstance(servers[0], dict):
            url = servers[0].get("url", "")
            if url.startswith("http"):
                return url.rstrip("/")
        # Swagger 2.x
        host = doc.get("host", "")
        scheme = (doc.get("schemes") or ["https"])[0]
        base_path = doc.get("basePath", "/")
        if host:
            return f"{scheme}://{host}{base_path}".rstrip("/")
        logger.warning("Could not determine base_url from %s — using placeholder", source.name)
        return "https://api.example.com"

    def _env_name(self, base_url: str) -> str:
        try:
            host = urlparse(base_url).hostname or ""
            # e.g. api.example.com → example
            parts = host.split(".")
            return parts[-2] if len(parts) >= 2 else parts[0]
        except Exception:
            return "api"

    def _response_fields(self, operation: dict, doc: dict) -> list[str]:
        responses = operation.get("responses") or {}
        schema = None
        for code in ("200", "201", "default"):
            resp = responses.get(code)
            if not resp:
                continue
            # OpenAPI 3.x content → application/json → schema
            content = resp.get("content") or {}
            for media_type in content.values():
                schema = media_type.get("schema")
                if schema:
                    break
            # Swagger 2.x inline schema
            if not schema:
                schema = resp.get("schema")
            if schema:
                break

        if not schema:
            return []
        return self._fields_from_schema(schema, doc)

    def _fields_from_schema(self, schema: dict, doc: dict) -> list[str]:
        schema = self._resolve_ref(schema, doc)
        if not isinstance(schema, dict):
            return []
        # Array — look inside items
        if schema.get("type") == "array":
            items = self._resolve_ref(schema.get("items") or {}, doc)
            schema = items if isinstance(items, dict) else {}
        props = schema.get("properties") or {}
        return list(props.keys())

    def _resolve_ref(self, schema: dict, doc: dict) -> dict:
        ref = schema.get("$ref", "")
        if not ref.startswith("#/"):
            return schema
        parts = ref.lstrip("#/").split("/")
        node = doc
        for part in parts:
            node = node.get(part, {})
        return node if isinstance(node, dict) else {}
