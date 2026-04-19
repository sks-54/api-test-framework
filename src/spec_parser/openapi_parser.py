"""OpenAPI 3.x spec parser — STUB, planned for v1.1.

Full implementation planned for v1.1. Will parse OpenAPI 3.x specs.
REST Countries OpenAPI available at https://restcountries.com/v3.1 — see ENHANCEMENTS.md E-01.
"""

from __future__ import annotations

from pathlib import Path

from .base_parser import BaseSpecParser, EndpointSpec


class OpenAPIParser(BaseSpecParser):
    """Parse OpenAPI 3.x specification files (YAML or JSON).

    Full implementation planned for v1.1 — see ENHANCEMENTS.md E-01.

    Planned implementation outline:
    1. Load spec with pyyaml (YAML) or json (JSON).
    2. Read ``servers[*].url`` — each is an atomic URL, never split.
    3. Iterate ``paths`` mapping: each key is an endpoint path.
    4. For each path iterate HTTP-method sub-keys (get/post/put/delete/patch).
    5. Read operationId, summary, description for metadata.
    6. Walk responses → content → schema → properties for response_fields.
    7. Construct one EndpointSpec per (server, path, method) triple.

    Key document keys: openapi, info.title, servers[*].url, paths,
    paths.<p>.<method>.operationId, paths.<p>.<method>.responses,
    components.schemas ($ref expansion).
    """

    supported_extensions: tuple[str, ...] = (".yaml", ".yml", ".json")

    def parse(self, source: Path) -> list[EndpointSpec]:
        # TODO (E-01): implement full OpenAPI 3.x parsing.
        #
        # Skeleton for v1.1 implementer (do NOT remove):
        #
        #   raw = yaml.safe_load(source.read_text()) or json.loads(source.read_text())
        #   assert raw.get("openapi", "").startswith("3.")
        #
        #   servers = [s["url"] for s in raw.get("servers", [])]
        #   # Each s["url"] is an atomic URL — never split or concatenate.
        #
        #   specs = []
        #   for path_str, path_item in raw.get("paths", {}).items():
        #       for method in ("get", "post", "put", "delete", "patch"):
        #           operation = path_item.get(method)
        #           if not operation:
        #               continue
        #           fields = _extract_response_fields(operation, raw)
        #           for base_url in servers:
        #               specs.append(EndpointSpec(
        #                   env_name=_infer_env_name(base_url),
        #                   base_url=base_url,
        #                   path=path_str,
        #                   method=method.upper(),
        #                   response_fields=fields,
        #                   thresholds={},  # resolve against config/environments.yaml
        #                   description=operation.get("summary", ""),
        #               ))
        #   return specs

        raise NotImplementedError(
            "OpenAPIParser is not yet implemented. "
            "See ENHANCEMENTS.md E-01 for the full implementation plan."
        )
