"""Top-level pytest configuration — environment fixture and CLI options."""

from __future__ import annotations

pytest_plugins = ["apitf.reporters.bug_reporter"]

from pathlib import Path
from typing import Any

import pytest
import yaml


# ---------------------------------------------------------------------------
# CLI option registration
# ---------------------------------------------------------------------------

def _load_env_names() -> list[str]:
    """Read environment names from config/environments.yaml."""
    config_path = Path(__file__).parent.parent / "config" / "environments.yaml"
    with config_path.open() as fh:
        data = yaml.safe_load(fh)
    return [k for k in data if k != "version"]


def pytest_addoption(parser: pytest.Parser) -> None:
    env_names = _load_env_names()
    parser.addoption(
        "--env",
        action="store",
        default=None,
        choices=env_names,
        help=f"Target environment to test. Choices: {env_names}. Omit to run all.",
    )


# ---------------------------------------------------------------------------
# Environment fixture  (session-scoped — one HTTP client per env per run)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def env_config(request: pytest.FixtureRequest) -> dict[str, Any]:
    """Load the selected environment's config from environments.yaml.

    Returns a dict with keys: base_url, thresholds (max_response_time,
    min_results_count). Tests must never read URLs or thresholds directly —
    always use this fixture.
    """
    config_path = Path(__file__).parent.parent / "config" / "environments.yaml"
    with config_path.open() as fh:
        all_envs: dict = yaml.safe_load(fh)

    env_name: str | None = request.config.getoption("--env")

    if env_name is None:
        # No --env flag: return all envs merged (used for parametrized runs)
        return all_envs

    if env_name not in all_envs:
        raise ValueError(
            f"Environment {env_name!r} not found in environments.yaml. "
            f"Available: {list(all_envs)}"
        )

    return {env_name: all_envs[env_name]}


# ---------------------------------------------------------------------------
# Skip logic — markers control which tests run under which --env
# ---------------------------------------------------------------------------

def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Skip tests whose environment marker doesn't match --env flag."""
    selected_env: str | None = config.getoption("--env")
    if selected_env is None:
        return  # no filtering — run everything

    all_env_names = set(_load_env_names())
    other_envs = all_env_names - {selected_env}

    for item in items:
        # Skip any test whose env marker doesn't match the selected --env.
        # Works for all environments without hardcoding pairwise checks.
        for other in other_envs:
            if item.get_closest_marker(other):
                item.add_marker(pytest.mark.skip(
                    reason=(
                        f"--env {selected_env} selected: {other} tests are environment-scoped "
                        f"and only run under --env {other}. "
                        f"Use `pytest` (no --env flag) to run all environments."
                    )
                ))
                break
