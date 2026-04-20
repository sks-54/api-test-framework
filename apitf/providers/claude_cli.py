from __future__ import annotations

import atexit
import os
import signal
import subprocess
import tempfile
import threading

from apitf.providers.base import LLMProvider, ProviderModels

# Preferred models in descending quality order.
# generate() tries each in order and falls back on model-not-found errors.
_GEN_PREFERENCES = [
    "claude-sonnet-4-6",
    "claude-3-5-sonnet-20241022",
    "claude-haiku-4-5-20251001",
    "claude-haiku-3-5",
]
_REF_PREFERENCES = [
    "claude-opus-4-7",
    "claude-opus-4-5",
    "claude-sonnet-4-6",
    "claude-3-5-sonnet-20241022",
]

_CLI_TIMEOUT = 300  # seconds — generation of a full test suite can be slow

# Substrings in CLI stderr that indicate model-not-found (not plan access errors)
_MODEL_NOT_FOUND_HINTS = [
    "model not found",
    "no model",
    "invalid model",
    "unknown model",
    "not available",
    "not supported",
]

# ---------------------------------------------------------------------------
# Process tracking — ensures claude subprocesses don't outlive the parent
# ---------------------------------------------------------------------------

_active_procs: set[subprocess.Popen[str]] = set()
_procs_lock = threading.Lock()


def _register(proc: subprocess.Popen[str]) -> None:
    with _procs_lock:
        _active_procs.add(proc)


def _unregister(proc: subprocess.Popen[str]) -> None:
    with _procs_lock:
        _active_procs.discard(proc)


def _terminate_all() -> None:
    """Terminate all tracked claude subprocesses. Safe to call from signal handlers."""
    with _procs_lock:
        procs = list(_active_procs)
    for proc in procs:
        try:
            proc.terminate()
        except Exception:
            pass


def _sigterm_handler(signum: int, frame: object) -> None:
    _terminate_all()
    # Re-raise as the default handler so the process exits with the right code.
    signal.signal(signum, signal.SIG_DFL)
    os.kill(os.getpid(), signum)


# Register cleanup on normal exit and on SIGTERM / SIGINT.
# SIGTERM is not available on Windows; guard with hasattr.
atexit.register(_terminate_all)
signal.signal(signal.SIGINT, _sigterm_handler)
if hasattr(signal, "SIGTERM"):
    signal.signal(signal.SIGTERM, _sigterm_handler)


# ---------------------------------------------------------------------------

def _is_model_unavailable(stderr: str) -> bool:
    low = stderr.lower()
    return any(hint in low for hint in _MODEL_NOT_FOUND_HINTS)


class ClaudeCLIProvider(LLMProvider):
    """Uses the authenticated `claude` CLI — zero config inside a Claude Code session.

    Model selection is lazy: defaults to the top preference and falls back to
    lesser models on the first generate() call that gets a model-not-found error.
    No subprocess probing at construction time.

    All spawned subprocesses are tracked in a module-level registry and terminated
    on SIGTERM, SIGINT, or normal process exit — preventing orphaned claude processes.
    """

    def __init__(self, explicit_key: str | None = None) -> None:
        self._gen_model = _GEN_PREFERENCES[0]
        self._ref_model = _REF_PREFERENCES[0]
        self._models = ProviderModels(
            generation=self._gen_model,
            reflection=self._ref_model,
            label=f"Claude Code CLI ({self._gen_model} / {self._ref_model})",
        )

    @classmethod
    def available(cls, explicit_key: str | None = None) -> bool:
        if os.environ.get("CLAUDECODE") != "1":
            return False
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True, text=True, timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @property
    def models(self) -> ProviderModels:
        return self._models

    def _run_with_fallback(self, prompt: str, preferences: list[str], role: str) -> tuple[str, str]:
        """Run the claude CLI, falling back through model preferences on unavailability."""
        last_stderr = ""
        for model in preferences:
            proc = subprocess.Popen(
                ["claude", "--model", model, "-p", "--allowedTools", "", "--output-format", "text", "-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=tempfile.gettempdir(),
            )
            _register(proc)
            try:
                stdout, stderr = proc.communicate(input=prompt, timeout=_CLI_TIMEOUT)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                raise RuntimeError(f"claude CLI timed out after {_CLI_TIMEOUT}s (model={model})")
            finally:
                _unregister(proc)

            last_stderr = stderr
            if proc.returncode == 0:
                return stdout.strip(), model
            if _is_model_unavailable(stderr):
                continue  # try next preference
            raise RuntimeError(f"claude CLI error: {stderr.strip()}")

        raise RuntimeError(
            f"No available Claude model for {role}. Tried: {preferences}. "
            f"Last stderr: {last_stderr.strip()}"
        )

    def generate(self, prompt: str, model: str) -> str:
        if model in _REF_PREFERENCES:
            preferences = _REF_PREFERENCES
            role = "reflection"
        else:
            preferences = _GEN_PREFERENCES
            role = "generation"

        if model in preferences:
            idx = preferences.index(model)
            ordered = [model] + preferences[idx + 1:]
        else:
            ordered = preferences

        output, resolved = self._run_with_fallback(prompt, ordered, role)

        if role == "generation" and resolved != self._gen_model:
            self._gen_model = resolved
            self._models = ProviderModels(
                generation=self._gen_model,
                reflection=self._ref_model,
                label=f"Claude Code CLI ({self._gen_model} / {self._ref_model})",
            )
        elif role == "reflection" and resolved != self._ref_model:
            self._ref_model = resolved
            self._models = ProviderModels(
                generation=self._gen_model,
                reflection=self._ref_model,
                label=f"Claude Code CLI ({self._gen_model} / {self._ref_model})",
            )

        return output
