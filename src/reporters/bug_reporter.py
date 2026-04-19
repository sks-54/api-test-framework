"""pytest plugin — auto-generates structured markdown bug reports on test failure."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

import allure
import pytest
from _pytest.nodes import Item
from _pytest.reports import TestReport
from _pytest.runner import CallInfo

_LOCK = threading.Lock()

_ENV_FAILURE_TYPES = frozenset({
    "ConnectionError", "Timeout", "ConnectTimeout", "ReadTimeout",
})
_STRUCTURAL_FAILURE_TYPES = frozenset({
    "ImportError", "ModuleNotFoundError", "AttributeError",
    "FixtureLookupError", "FixtureError",
})


def _sanitize_node_id(node_id: str) -> str:
    return (
        node_id.replace("/", "_").replace("\\", "_")
        .replace("::", "__").replace("[", "(").replace("]", ")")
        .replace(" ", "_")
    )


def _categorize_failure(report: TestReport) -> str:
    longrepr = report.longrepr
    exc_type_name: str = ""
    if hasattr(longrepr, "reprcrash"):
        exc_type_name = (longrepr.reprcrash.message or "").split(":")[0].strip()
    elif isinstance(longrepr, tuple) and len(longrepr) >= 2:
        exc_type_name = str(longrepr[1]).split(":")[0].strip()
    elif isinstance(longrepr, str):
        exc_type_name = longrepr.split(":")[0].strip()

    status_code: int | None = getattr(report, "_response_status_code", None)
    if status_code is not None and 500 <= status_code < 600:
        return "ENV_FAILURE"
    if exc_type_name in _ENV_FAILURE_TYPES:
        return "ENV_FAILURE"
    if exc_type_name in _STRUCTURAL_FAILURE_TYPES:
        return "STRUCTURAL_FAILURE"
    return "QUALITY_FAILURE"


def _extract_short_description(report: TestReport) -> str:
    longrepr = report.longrepr
    if hasattr(longrepr, "reprcrash"):
        msg = longrepr.reprcrash.message or ""
        return msg.splitlines()[0][:120] if msg else "unknown failure"
    if isinstance(longrepr, str):
        return longrepr.splitlines()[0][:120]
    if isinstance(longrepr, tuple) and len(longrepr) >= 2:
        return str(longrepr[1]).splitlines()[0][:120]
    return "unknown failure"


def _extract_assertion_parts(report: TestReport) -> tuple[str, str]:
    expected = actual = "See traceback above"
    longrepr = report.longrepr
    full_text = ""
    if hasattr(longrepr, "reprcrash"):
        full_text = longrepr.reprcrash.message or ""
    elif isinstance(longrepr, str):
        full_text = longrepr
    for line in full_text.splitlines():
        s = line.strip()
        if s.startswith("assert "):
            expected = s[len("assert "):]
        if "where " in s:
            actual = s.split("where ", 1)[-1]
    return expected, actual


def _request_metadata(item: Item) -> dict[str, str]:
    return {
        "method": getattr(item, "_request_method", "N/A"),
        "url": getattr(item, "_request_url", "N/A"),
        "params": str(getattr(item, "_request_params", {})),
        "status_code": str(getattr(item, "_status_code", "N/A")),
        "response_time_ms": str(getattr(item, "_response_time_ms", "N/A")),
        "response_body": str(getattr(item, "_response_body", ""))[:500],
    }


def _build_markdown(
    *,
    test_name: str,
    short_description: str,
    timestamp: str,
    env_name: str,
    category: str,
    node_id: str,
    meta: dict[str, str],
    expected: str,
    actual: str,
) -> str:
    return (
        f"# [FAIL] {test_name} — {short_description}\n\n"
        f"**Date:** {timestamp} UTC\n"
        f"**Environment:** {env_name}\n"
        f"**Category:** {category}\n\n"
        "## Steps to Reproduce\n"
        f"1. Command: `pytest {node_id}`\n"
        f"2. Request: {meta['method']} {meta['url']}\n"
        f"3. Params: {meta['params']}\n\n"
        "## Expected Result\n"
        f"{expected}\n\n"
        "## Actual Result\n"
        f"{actual}\n\n"
        "## Data\n"
        f"- **Request URL:** {meta['url']}\n"
        f"- **Status Code:** {meta['status_code']}\n"
        f"- **Response Time (ms):** {meta['response_time_ms']}\n"
        f"- **Response Snippet:** {meta['response_body']}\n"
    )


class BugReporterPlugin:
    """pytest plugin: writes structured markdown bug reports on test failure."""

    def __init__(self, bugs_dir: Path, env_name: str) -> None:
        self._bugs_dir = bugs_dir
        self._env_name = env_name
        self._bugs_dir.mkdir(parents=True, exist_ok=True)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(
        self, item: Item, call: CallInfo
    ) -> Generator[None, None, None]:
        outcome = yield
        report: TestReport = outcome.get_result()
        if report.when != "call" or not report.failed:
            return
        self._handle_failure(item=item, report=report)

    def _handle_failure(self, *, item: Item, report: TestReport) -> None:
        now_utc = datetime.now(tz=timezone.utc)
        timestamp = now_utc.strftime("%Y-%m-%d %H:%M:%S")
        file_ts = now_utc.strftime("%Y-%m-%d_%H-%M-%S")
        sanitized = _sanitize_node_id(item.nodeid)
        markdown_content = _build_markdown(
            test_name=item.name,
            short_description=_extract_short_description(report),
            timestamp=timestamp,
            env_name=self._env_name,
            category=_categorize_failure(report),
            node_id=item.nodeid,
            meta=_request_metadata(item),
            expected=_extract_assertion_parts(report)[0],
            actual=_extract_assertion_parts(report)[1],
        )
        report_path = self._bugs_dir / f"{file_ts}_{sanitized}.md"
        with _LOCK:
            report_path.write_text(markdown_content, encoding="utf-8")
        allure.attach(
            body=markdown_content,
            name=f"Bug Report — {item.name}",
            attachment_type=allure.attachment_type.MARKDOWN,
        )


def pytest_configure(config: pytest.Config) -> None:
    bugs_dir = Path(config.rootdir) / "bugs"
    env_name: str = config.getoption("--env", default="all")  # type: ignore[assignment]
    config.pluginmanager.register(
        BugReporterPlugin(bugs_dir=bugs_dir, env_name=env_name),
        name="bug_reporter",
    )
