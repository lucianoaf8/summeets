# REMEDIATION PLAN: SUMMEETS

**Date**: 2026-02-06
**Source**: MASTER_CODEBASE_REVIEW.md
**Scope**: All 8 CRITICAL and 14 HIGH severity findings
**Estimated Total Effort**: ~17 developer-days

---

## TABLE OF CONTENTS

1. [Execution Phases Overview](#execution-phases-overview)
2. [Phase 1: Immediate / Zero-Dependency Fixes](#phase-1-immediate--zero-dependency-fixes)
3. [Phase 2: Core Code Fixes](#phase-2-core-code-fixes)
4. [Phase 3: Test Coverage](#phase-3-test-coverage)
5. [Phase 4: Documentation and Infrastructure](#phase-4-documentation-and-infrastructure)
6. [Dependency Graph](#dependency-graph)
7. [Verification Checklist](#verification-checklist)

---

## EXECUTION PHASES OVERVIEW

| Phase | Items | Parallelizable | Effort | Focus |
|-------|-------|---------------|--------|-------|
| 1 | CR-01, CR-08, HI-09, HI-05 | All parallel | ~3 hours | Quick wins, legal, security |
| 2 | CR-02, CR-03, CR-04, CR-05, CR-06, HI-01, HI-03, HI-04, HI-06, HI-07 | Mostly parallel | ~4 days | Code correctness |
| 3 | CR-07, HI-12, HI-13, HI-14 | Partially parallel | ~8 days | Test coverage, CI/CD |
| 4 | HI-02, HI-08, HI-10, HI-11 | All parallel | ~5 days | Docs, supply chain |

---

## PHASE 1: IMMEDIATE / ZERO-DEPENDENCY FIXES

These items have no code dependencies and can all be executed in parallel.

---

### CR-01: Live API Keys in Plaintext `.env` File

**Severity**: CRITICAL
**OWASP**: A07:2021 | **CWE**: CWE-798, CWE-312

#### Current State

File: `.env` (lines 1-6)

Live full-length API keys for Replicate, OpenAI, and Anthropic sit as plaintext on disk. While `.gitignore` blocks committing (confirmed: `.env` is listed at line 128 and 204 of `.gitignore`), any local malware, backup tool, or cloud sync would expose all three keys.

The codebase already has a `SecureConfigManager` class at `src/utils/secure_config.py` with a `migrate_to_keyring()` method and full keyring integration. It is currently unused in the main configuration flow.

#### Target State

- All three API keys rotated at their respective provider dashboards.
- Keys stored in OS keyring via `SecureConfigManager`.
- `.env` file contains only non-sensitive configuration (provider names, model names, directory paths).
- `Settings` class in `config.py` checks keyring before falling back to environment variables.

#### Implementation Steps

1. **Rotate all API keys immediately** via provider dashboards:
   - OpenAI: https://platform.openai.com/api-keys
   - Anthropic: https://console.anthropic.com/settings/keys
   - Replicate: https://replicate.com/account/api-tokens

2. **Store new keys in keyring** using the existing programmatic approach:
   ```python
   from src.utils.secure_config import SecureConfigManager
   mgr = SecureConfigManager()
   mgr.set_api_key("OPENAI_API_KEY", "sk-new-key-here")
   mgr.set_api_key("ANTHROPIC_API_KEY", "sk-ant-new-key-here")
   mgr.set_api_key("REPLICATE_API_TOKEN", "r8_new-token-here")
   ```

3. **Wire keyring into Settings initialization** in `src/utils/config.py`:
   - After line 189 (`SETTINGS = Settings()`), add a post-init step that attempts to load keys from keyring if env vars are empty.
   - Modify the `Settings` class to include a `model_post_init` method that calls `SecureConfigManager.get_api_key()` for each secure key when the environment variable is `None`.

4. **Remove plaintext keys from `.env`**:
   - Replace key values with empty strings or comments indicating keyring usage.
   - Keep the variable names as documentation of required keys.

5. **Create `.env.example`** file with placeholder values for documentation.

#### Files to Modify

- `.env` -- remove plaintext keys
- `src/utils/config.py` -- add keyring fallback in Settings (around line 189)
- Create `.env.example` -- template with placeholders

#### Success Criteria

- `grep -E "sk-|r8_" .env` returns 0 matches (no real keys in .env).
- `python -c "from src.utils.config import SETTINGS; print(bool(SETTINGS.openai_api_key))"` returns `True` (keys loaded from keyring).
- Old API keys return authentication errors when used directly.

#### Testing Gate

- **Existing tests**: `python -m pytest tests/` -- all tests must still pass.
- **Manual verification**: Run `summeets health` and confirm all API key checks show green.
- **Negative test**: Temporarily remove keyring entry, confirm graceful fallback to env var with warning log.

#### Estimated Effort

2 hours (including key rotation time with provider dashboards).

#### Dependencies

None.

#### Risk Assessment

- **Medium risk**: Key rotation may briefly disrupt any running processes using old keys.
- **Mitigation**: Rotate keys during a maintenance window. Verify new keys work before removing old `.env` values.

---

### CR-08: No LICENSE File Despite README Claiming MIT

**Severity**: CRITICAL

#### Current State

File: `README.md:297` contains:
```
MIT License - see LICENSE file for details.
```

No `LICENSE` file exists in the repository root. Confirmed via glob search returning no results for `LICENSE*`.

The `pyproject.toml` does not declare a `license` field either.

#### Target State

- `LICENSE` file exists at repository root with standard MIT license text.
- `pyproject.toml` includes `license = {text = "MIT"}`.

#### Implementation Steps

1. Create `LICENSE` at repository root with standard MIT license text. Use current year and "Summeets Contributors" as the copyright holder.

2. Add `license` field to `pyproject.toml` under `[project]` (after `requires-python` at line 10):
   ```toml
   license = {text = "MIT"}
   ```

#### Files to Modify

- Create `LICENSE`
- `pyproject.toml` -- add license field (line ~11)

#### Success Criteria

- File `LICENSE` exists and contains "MIT License".
- `pyproject.toml` contains `license` entry.
- README reference at line 297 resolves correctly.

#### Testing Gate

- No code tests required. Manual file verification only.

#### Estimated Effort

15 minutes.

#### Dependencies

None.

#### Risk Assessment

Low risk. Pure file creation with no code impact.

---

### HI-09: No CHANGELOG.md Exists

**Severity**: HIGH

#### Current State

No `CHANGELOG.md` exists anywhere in the project. Project is at version `0.1.0` per `pyproject.toml:7`.

#### Target State

`CHANGELOG.md` exists at repository root with initial `0.1.0` entry documenting existing functionality.

#### Implementation Steps

1. Create `CHANGELOG.md` at repository root following Keep a Changelog format with an initial `[0.1.0]` entry covering:
   - CLI interface commands (transcribe, summarize, process, config, health, templates, tui)
   - TUI interface via Textual
   - Audio processing pipeline with FFmpeg
   - Transcription via Replicate (Whisper v3 + Pyannote)
   - Summarization with OpenAI and Anthropic providers
   - Five summary templates (default, SOP, decision, brainstorm, requirements)
   - Pydantic-based configuration
   - Structured logging with API key sanitization
   - Workflow engine and job management

#### Files to Modify

- Create `CHANGELOG.md`

#### Success Criteria

- File `CHANGELOG.md` exists at repository root.
- Contains valid Keep a Changelog structure with `[0.1.0]` entry.

#### Testing Gate

- No code tests required.

#### Estimated Effort

30 minutes.

#### Dependencies

None.

#### Risk Assessment

Low risk. Pure documentation.

---

### HI-05: `safe_operation` Decorator Missing `functools.wraps`

**Severity**: HIGH

#### Current State

File: `src/utils/exceptions.py:343-351`

```python
def safe_operation(
    operation_name: str,
    logger: logging.Logger,
    reraise_as: type = SummeetsError
):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_and_reraise(logger, e, operation_name, reraise_as)
        return wrapper
    return decorator
```

The `wrapper` function does not use `@functools.wraps(func)`. This means any function decorated with `@safe_operation(...)` loses its `__name__`, `__doc__`, `__module__`, and `__qualname__` attributes. This breaks introspection, debugging, Sphinx autodoc, and any code that inspects function metadata.

Note: `functools` is **not** currently imported in this file. The file imports only `logging`, `traceback`, `typing`, and `pathlib`.

#### Target State

```python
import functools  # added to imports at top of file

def safe_operation(
    operation_name: str,
    logger: logging.Logger,
    reraise_as: type = SummeetsError
):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_and_reraise(logger, e, operation_name, reraise_as)
        return wrapper
    return decorator
```

#### Implementation Steps

1. Add `import functools` to the imports section of `src/utils/exceptions.py` (after the `import traceback` line at line 6).
2. Add `@functools.wraps(func)` decorator on the `wrapper` function inside `safe_operation`, immediately before line 344 (`def wrapper(*args, **kwargs):`).

#### Files to Modify

- `src/utils/exceptions.py` -- add import (line ~7) and decorator (line ~344)

#### Success Criteria

- `grep -n "functools.wraps" src/utils/exceptions.py` returns a match.
- Decorating a function with `@safe_operation("test", logger)` preserves `__name__` and `__doc__`.

#### Testing Gate

- **Existing tests**: All tests in `tests/unit/test_error_handling.py` must pass.
- **New test**: Add a test to `tests/unit/test_error_handling.py`:
  ```python
  def test_safe_operation_preserves_function_metadata():
      @safe_operation("test_op", logging.getLogger("test"))
      def my_function():
          """My docstring."""
          pass
      assert my_function.__name__ == "my_function"
      assert my_function.__doc__ == "My docstring."
  ```

#### Estimated Effort

15 minutes.

#### Dependencies

None.

#### Risk Assessment

Low risk. Additive change that preserves existing behavior while fixing metadata propagation.

---

## PHASE 2: CORE CODE FIXES

These items fix code-level bugs and anti-patterns. Items within this phase can mostly be done in parallel, except where noted.

---

### CR-02: Duplicate `SummaryTemplate` Enum Creates Silent Type Mismatch

**Severity**: CRITICAL

#### Current State

Two independent `SummaryTemplate` enums exist:

1. `src/models.py:57-64`:
   ```python
   class SummaryTemplate(str, Enum):
       DEFAULT = "default"
       SOP = "sop"
       DECISION = "decision"
       BRAINSTORM = "brainstorm"
       REQUIREMENTS = "requirements"
   ```

2. `src/summarize/templates.py:7-13`:
   ```python
   class SummaryTemplate(str, Enum):
       DEFAULT = "default"
       SOP = "sop"
       DECISION = "decision"
       BRAINSTORM = "brainstorm"
       REQUIREMENTS = "requirements"
   ```

Because these are different Python types, `models.SummaryTemplate.DEFAULT is not templates.SummaryTemplate.DEFAULT` evaluates to `True`. The `get_template()` method in `SummaryTemplates` class at `templates.py:217-226` uses the local `SummaryTemplate` as dictionary keys, while `cli/app.py:13` imports from `models.py` and creates `SummaryTemplate(template)` at line 169. When the `models.py` enum is passed to `get_template()`, the dictionary lookup uses `templates.py` enum keys -- this works only because both are `str` subclasses and string comparison is used, but `is`/`isinstance` checks would fail.

#### Target State

Single `SummaryTemplate` enum defined in `src/models.py`. All other files import from `src.models`.

#### Implementation Steps

1. **Delete** the `SummaryTemplate` class definition from `src/summarize/templates.py` (lines 7-13).

2. **Replace** with import at the top of `src/summarize/templates.py`:
   ```python
   from ..models import SummaryTemplate
   ```
   This must go after the existing `from enum import Enum` import (which can be removed if SummaryTemplate was the only Enum in the file). The `Enum` import at line 2 is used only by `SummaryTemplate`, so remove it after confirming.

3. **Verify** all usages of `SummaryTemplate` in `templates.py` still work:
   - `get_template()` at line 217-226: Uses `SummaryTemplate.DEFAULT`, etc. as dict keys -- will work with import.
   - `list_templates()` at line 229-237: Same pattern.
   - `detect_meeting_type()` at line 268-324: Returns `SummaryTemplate` members -- will work.

4. **Search all other files** that import `SummaryTemplate` from `templates.py`:
   ```bash
   grep -rn "from.*templates.*import.*SummaryTemplate" src/ cli/
   ```
   If any exist, update them to import from `src.models` instead.

#### Files to Modify

- `src/summarize/templates.py` -- remove duplicate class (lines 7-13), remove `Enum` import (line 2), add import from models

#### Success Criteria

- `grep -rn "class SummaryTemplate" src/` returns exactly 1 result (in `models.py`).
- `python -c "from src.models import SummaryTemplate as A; from src.summarize.templates import SummaryTemplate as B; assert A is B"` succeeds (same object).

#### Testing Gate

- **Existing tests**: All tests in `tests/test_templates.py` must pass.
- **Existing tests**: All tests in `tests/unit/test_models.py` must pass.
- **Manual verification**: Run `summeets templates` command and confirm output is identical to pre-change.

#### Estimated Effort

30 minutes.

#### Dependencies

None.

#### Risk Assessment

Low risk. Both enums have identical string values, so string comparisons continue to work. Only identity (`is`) checks were broken, and fixing this can only improve behavior.

---

### CR-03: Duplicate Exception Classes Break Exception Hierarchy

**Severity**: CRITICAL

#### Current State

Three pairs of duplicate exception/utility classes exist:

**Pair 1 -- TranscriptionError**:
- `src/utils/exceptions.py:78-80`: inherits from `SummeetsError`
  ```python
  class TranscriptionError(SummeetsError):
      """Raised when transcription operations fail."""
      pass
  ```
- `src/transcribe/replicate_api.py:42-43`: inherits from `Exception`
  ```python
  class TranscriptionError(Exception):
      """Raised when transcription fails."""
      pass
  ```
  The `replicate_api.py` version is used locally in `transcribe()` at line 146 and `_poll_prediction()` at line 183. Since it inherits from `Exception` (not `SummeetsError`), any `except SummeetsError` catch in the call chain will miss it.

**Pair 2 -- CompressionError**:
- `src/utils/exceptions.py:73-75`: `AudioCompressionError` inheriting from `AudioProcessingError(SummeetsError)`
- `src/audio/compression.py:21-22`: inherits from `Exception`
  ```python
  class CompressionError(Exception):
      """Raised when audio compression fails."""
      pass
  ```
  Used locally at lines 82 and 122. Same hierarchy problem.

**Pair 3 -- ErrorContext**:
- `src/utils/exceptions.py:355-387`: Takes `reraise_as` parameter, calls `log_and_reraise()`, suppresses=False
- `src/utils/error_handling.py:250-287`: Takes `**context_vars`, adds context to error message, converts non-SummeetsError exceptions. Different API and semantics.

#### Target State

- Single `TranscriptionError` in `src/utils/exceptions.py` (inheriting from `SummeetsError`).
- `CompressionError` alias for `AudioCompressionError` in `src/utils/exceptions.py`.
- Single `ErrorContext` in `src/utils/exceptions.py`.
- All modules import from `src/utils/exceptions.py`.

#### Implementation Steps

1. **Fix TranscriptionError in replicate_api.py**:
   - Remove the `TranscriptionError` class definition at lines 42-43.
   - Add import at top of file: `from ..utils.exceptions import TranscriptionError`
   - Verify all `raise TranscriptionError(...)` calls in the file still work. The centralized version accepts a positional `message` string, matching the current usage pattern: `raise TranscriptionError("Failed to transcribe audio: ...")`.

2. **Fix CompressionError in compression.py**:
   - Remove the `CompressionError` class definition at lines 21-22.
   - Add import at top of file: `from ..utils.exceptions import AudioCompressionError as CompressionError`
   - Alternatively, add a `CompressionError` alias to `exceptions.py` and import that.

3. **Add CompressionError alias** to `src/utils/exceptions.py` (after line 75):
   ```python
   # Alias for backward compatibility
   CompressionError = AudioCompressionError
   ```
   Add `'CompressionError'` to the `__all__` list at line 10-17.

4. **Consolidate ErrorContext**:
   - Keep the version in `src/utils/exceptions.py` as the canonical implementation (it has `reraise_as` support which is more flexible).
   - In `src/utils/error_handling.py`, remove the `ErrorContext` class (lines 250-287).
   - Add import at top of `error_handling.py`: `from .exceptions import ErrorContext`
   - This re-export maintains backward compatibility for any code importing from `error_handling`.

#### Files to Modify

- `src/transcribe/replicate_api.py` -- remove local TranscriptionError (lines 42-43), add import (after line 9)
- `src/audio/compression.py` -- remove local CompressionError (lines 21-22), add import (after line 11)
- `src/utils/exceptions.py` -- add `CompressionError = AudioCompressionError` alias (after line 75), update `__all__` (line 10-17)
- `src/utils/error_handling.py` -- remove local ErrorContext (lines 250-287), add import from exceptions

#### Success Criteria

- `grep -rn "class TranscriptionError" src/` returns exactly 1 result (in `exceptions.py`).
- `grep -rn "class CompressionError" src/` returns exactly 0 results (it is an alias, not a class definition).
- `grep -rn "class ErrorContext" src/` returns exactly 1 result (in `exceptions.py`).
- `python -c "from src.transcribe.replicate_api import TranscriptionError; from src.utils.exceptions import TranscriptionError as T2; assert TranscriptionError is T2"` succeeds.

#### Testing Gate

- **Existing tests**: `tests/unit/test_error_handling.py` must pass.
- **Existing tests**: `tests/unit/test_compression.py` must pass.
- **New test**: Verify `isinstance(TranscriptionError("test"), SummeetsError)` is `True`.
- **New test**: Verify `isinstance(CompressionError("test"), AudioProcessingError)` is `True`.

#### Estimated Effort

2 hours.

#### Dependencies

None.

#### Risk Assessment

- **Medium risk**: Any code that catches `Exception` but then checks `isinstance(e, TranscriptionError)` using the wrong import will now see different behavior. After the fix, catches of `SummeetsError` will **also** catch `TranscriptionError`, which is the **correct** behavior.
- **Mitigation**: Search for all `except TranscriptionError` and `except CompressionError` catches and verify they still work correctly. Run full test suite.

---

### CR-04: Signal Handler Calls `sys.exit()` -- Risk of Deadlock

**Severity**: CRITICAL

#### Current State

File: `src/utils/shutdown.py:109-129`

```python
def _signal_handler(signum: int, frame) -> None:
    signal_name = signal.Signals(signum).name if hasattr(signal, 'Signals') else str(signum)
    log.info(f"Received {signal_name}, initiating graceful shutdown...")

    # Set shutdown flag
    request_shutdown()

    # Run cleanup
    _run_cleanup_handlers()
    _cleanup_temp_files()

    log.info("Cleanup complete, exiting...")

    # Exit cleanly
    sys.exit(0)
```

Problems:
1. `sys.exit(0)` raises `SystemExit`, which triggers `atexit` handlers. The `_atexit_cleanup` function at line 177-180 calls `_run_cleanup_handlers()` and `_cleanup_temp_files()` **again** -- double cleanup.
2. If the signal arrives during I/O or while holding a lock, `sys.exit()` can deadlock because it tries to unwind the stack through any acquired locks.
3. Logging inside a signal handler is unsafe (could deadlock if the logging lock is held).

The `_atexit_cleanup` handler is already registered at line 184:
```python
atexit.register(_atexit_cleanup)
```

#### Target State

Signal handler only sets the shutdown flag. Cleanup runs exactly once via `atexit` or the main thread's natural exit path.

#### Implementation Steps

1. **Replace the `_signal_handler` function body** (lines 109-129) to only set the flag:
   ```python
   def _signal_handler(signum: int, frame) -> None:
       """Handle shutdown signals (SIGINT, SIGTERM).

       Only sets the shutdown flag. Cleanup is handled by atexit handlers
       and the main thread's natural exit path. This avoids:
       - Double cleanup (signal handler + atexit)
       - Deadlocks from sys.exit() during I/O or lock acquisition
       - Unsafe logging inside signal handlers

       Args:
           signum: Signal number
           frame: Current stack frame
       """
       _shutdown_requested.set()
   ```

2. **Add an idempotency guard** to `_atexit_cleanup` to prevent any possibility of double execution:
   ```python
   _cleanup_done = False

   def _atexit_cleanup() -> None:
       """Cleanup handler called at interpreter exit."""
       global _cleanup_done
       if _cleanup_done:
           return
       _cleanup_done = True
       _run_cleanup_handlers()
       _cleanup_temp_files()
   ```
   Add `_cleanup_done = False` near the other module-level state variables (around line 20).

3. **Remove `import sys`** from line 8 if no other code in the file uses it. Verify with `grep "sys\." src/utils/shutdown.py`.

#### Files to Modify

- `src/utils/shutdown.py` -- replace `_signal_handler` body (lines 109-129), add `_cleanup_done` guard

#### Success Criteria

- `grep "sys.exit" src/utils/shutdown.py` returns 0 matches.
- `_signal_handler` function body is at most 5 lines (flag set + docstring).
- `_atexit_cleanup` is idempotent (calling it twice does not double-execute cleanup).

#### Testing Gate

- **Existing tests**: `tests/unit/test_shutdown.py` must pass.
- **New test**: Call `_signal_handler(signal.SIGINT, None)` and verify `is_shutdown_requested()` is `True` but no cleanup functions were called.
- **New test**: Call `_atexit_cleanup()` twice in sequence and verify cleanup handlers execute exactly once.

#### Estimated Effort

1 hour.

#### Dependencies

None.

#### Risk Assessment

- **Low risk**: Cleanup now happens slightly later (at process exit via atexit instead of immediately in the signal handler). This is the standard, correct pattern for Python signal handlers.
- **Consideration**: If the process is killed with SIGKILL after SIGINT, cleanup will not run. This is already the case and is inherent to SIGKILL.

---

### CR-05: `stream_json_array` Loads Entire File Into Memory

**Severity**: CRITICAL

#### Current State

File: `src/utils/streaming.py:62-81`

```python
def stream_json_array(file_path: Path) -> Iterator[Dict[str, Any]]:
    """Stream JSON array elements without loading entire file.
    ...
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()  # <-- Loads ENTIRE file into memory

    data = json.loads(content)  # <-- Creates SECOND copy in memory
    if isinstance(data, list):
        for item in data:
            yield item
    ...
```

The function name and docstring promise streaming behavior, but `f.read()` loads the entire file and `json.loads()` creates a second in-memory copy (2-3x file size total).

The only internal caller is `process_large_transcript()` at line 243 in the same file.

#### Target State

**Recommended**: Rename function to `load_json_array` and update docstring to accurately describe non-streaming behavior. This is the simplest fix. If true streaming is needed later, `ijson` can be added.

#### Implementation Steps

1. **Rename** `stream_json_array` to `load_json_array` at line 47 of `src/utils/streaming.py`.

2. **Update docstring** to be accurate:
   ```python
   def load_json_array(file_path: Path) -> Iterator[Dict[str, Any]]:
       """Load JSON file and yield array elements one at a time.

       Note: This loads the entire file into memory during parsing.
       For files larger than available RAM, implement incremental
       parsing with the ijson library.

       Args:
           file_path: Path to JSON file containing array

       Yields:
           Individual array elements
       """
   ```

3. **Update the internal caller** at line 243:
   ```python
   segments = list(load_json_array(file_path))
   ```

4. **Search for external callers** and update:
   ```bash
   grep -rn "stream_json_array" src/ cli/ tests/
   ```

#### Files to Modify

- `src/utils/streaming.py` -- rename function (line 47), update docstring, update internal caller (line 243)
- Any external callers found by grep

#### Success Criteria

- `grep -rn "stream_json_array" src/` returns 0 matches.
- `grep -rn "load_json_array" src/utils/streaming.py` returns matches.
- Docstring does not claim streaming behavior.

#### Testing Gate

- **Existing tests**: All tests must pass after rename.
- **New test**: Create a test JSON array file, call `load_json_array()`, verify all elements are yielded correctly.
- **New test**: Create a JSON dict with `segments` key, verify fallback path works.

#### Estimated Effort

1 hour.

#### Dependencies

None.

#### Risk Assessment

Low risk. Pure rename with no behavioral change. All existing callers get the same behavior with a more honest name.

---

### CR-06: `ServiceContainer` Uses Class-Level Mutable State

**Severity**: CRITICAL

#### Current State

File: `src/services/container.py:28-30`

```python
class ServiceContainer:
    _services: Dict[Type, Any] = {}
    _factories: Dict[Type, Callable[[], Any]] = {}
    _singletons: Dict[Type, Any] = {}
```

These class-level mutable dictionaries are shared across all instances and across tests. State from one test leaks into the next unless `ServiceContainer.reset()` is explicitly called. Creating `ServiceContainer()` does **not** give a fresh container -- it shares state with every other reference.

All methods are `@classmethod`, so there is no instance-level isolation at all.

#### Target State

Instance-level attributes initialized in `__init__`, with a module-level default instance for convenience. All `@classmethod` decorators converted to regular methods.

#### Implementation Steps

1. **Move class-level dicts to `__init__`**:
   ```python
   class ServiceContainer:
       def __init__(self):
           self._services: Dict[Type, Any] = {}
           self._factories: Dict[Type, Callable[[], Any]] = {}
           self._singletons: Dict[Type, Any] = {}
   ```

2. **Remove `@classmethod` decorators** from all methods. Change `cls` parameter to `self` for:
   - `register` (line 32)
   - `register_instance` (line 53)
   - `register_factory` (line 65)
   - `resolve` (line 81)
   - `get_audio_processor` (line 115)
   - `get_transcriber` (line 120)
   - `get_summarizer` (line 125)
   - `reset` (line 130)
   - `is_registered` (line 137)

3. **Create module-level default instance** at the bottom of the file:
   ```python
   # Default container instance for application use
   default_container = ServiceContainer()
   ```

4. **Search for all usages** of `ServiceContainer.method_name(...)`:
   ```bash
   grep -rn "ServiceContainer\." src/ cli/ tests/
   ```
   Update each call site to use `default_container.method_name(...)` or accept a container as a parameter.

5. **Update test fixtures** in `tests/conftest.py` and any test files that use `ServiceContainer.reset()`:
   - Replace `ServiceContainer.reset()` with either creating a fresh `ServiceContainer()` or calling `default_container.reset()`.

#### Files to Modify

- `src/services/container.py` -- refactor to instance-level state, add `default_container`
- All files that reference `ServiceContainer.` directly (search results from step 4)
- `tests/conftest.py` and test files -- update fixtures

#### Success Criteria

- No class-level mutable attributes remain in `ServiceContainer`.
- `grep "= {}" src/services/container.py` matches only within `__init__` method.
- `ServiceContainer()` creates an independent instance with empty registrations.
- `grep "@classmethod" src/services/container.py` returns 0 matches.

#### Testing Gate

- **Existing tests**: All existing tests must pass (may need fixture updates).
- **New test**: Create two `ServiceContainer` instances, register different services in each, verify they are independent.
- **New test**: Verify `reset()` clears only the target instance.

#### Estimated Effort

2 hours.

#### Dependencies

None. But HI-12 (services tests) should account for this change.

#### Risk Assessment

- **Medium risk**: Any code that relies on `ServiceContainer.register(...)` (class-level call) will need updating.
- **Mitigation**: Provide `default_container` module-level instance and update all call sites. Run full test suite.

---

### HI-01: API Key Masking Reveals Prefix and Suffix

**Severity**: HIGH | **OWASP**: A07:2021

#### Current State

Two masking functions expose first 4 and last 4 characters:

1. `src/utils/config.py:192-208`:
   ```python
   def mask_api_key(api_key: str | None) -> str:
       if not api_key:
           return "Not configured"
       if len(api_key) <= 8:
           return "*" * len(api_key)
       return api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
   ```

2. `src/utils/secure_config.py:342-347`:
   ```python
   @staticmethod
   def _mask_value(value: str) -> str:
       if len(value) <= 8:
           return "*" * len(value)
       return value[:4] + "*" * (len(value) - 8) + value[-4:]
   ```

Exposing prefix+suffix reduces brute-force search space.

#### Target State

Both functions show only the provider prefix (e.g., `sk-***configured***`).

#### Implementation Steps

1. **Update `mask_api_key`** in `src/utils/config.py` (replace lines 192-208):
   ```python
   def mask_api_key(api_key: str | None) -> str:
       """Mask an API key for safe display, showing only provider prefix."""
       if not api_key:
           return "Not configured"
       if api_key.startswith("sk-ant-"):
           return "sk-ant-***configured***"
       elif api_key.startswith("sk-proj-"):
           return "sk-proj-***configured***"
       elif api_key.startswith("sk-"):
           return "sk-***configured***"
       elif api_key.startswith("r8_"):
           return "r8_***configured***"
       return "***configured***"
   ```

2. **Update `_mask_value`** in `src/utils/secure_config.py` (replace lines 342-347) to call the centralized `mask_api_key` or use the same prefix-only logic.

#### Files to Modify

- `src/utils/config.py` -- replace `mask_api_key` body (lines 192-208)
- `src/utils/secure_config.py` -- replace `_mask_value` body (lines 343-347)

#### Success Criteria

- `python -c "from src.utils.config import mask_api_key; print(mask_api_key('sk-abc123def456ghi789'))"` outputs `sk-***configured***` (no suffix visible).
- No masking function reveals more than the provider prefix.

#### Testing Gate

- **Existing tests**: All tests must pass.
- **New test**: Verify each provider prefix is correctly identified.
- **New test**: Verify suffixes are never exposed for keys of various lengths.
- **Manual verification**: Run `summeets config` and inspect masked key output.

#### Estimated Effort

30 minutes.

#### Dependencies

None.

#### Risk Assessment

Low risk. Display-only change with no functional impact.

---

### HI-03: Provider Clients Use Global Mutable State -- Not Thread-Safe

**Severity**: HIGH

#### Current State

Both provider files use identical patterns with module-level globals:

`src/providers/openai_client.py:21-22`:
```python
_client: Optional[OpenAI] = None
_last_api_key: Optional[str] = None
```

`src/providers/anthropic_client.py:20-21`:
```python
_client: Optional[Anthropic] = None
_last_api_key: Optional[str] = None
```

The TUI runs workflows in background threads via `@work(thread=True)`. Multiple threads can read/write `_client` and `_last_api_key` simultaneously without locking.

A `ClientCache` class already exists in `src/providers/common.py:77-109` but is unused. It has the right structure but lacks thread safety (no lock).

#### Target State

`ClientCache` in `common.py` enhanced with `threading.Lock`, used by both provider modules.

#### Implementation Steps

1. **Add `threading.Lock` to `ClientCache`** in `src/providers/common.py`:
   ```python
   import threading  # add to imports

   class ClientCache:
       def __init__(self, client_factory, key_getter):
           self._client = None
           self._last_key = None
           self._factory = client_factory
           self._key_getter = key_getter
           self._lock = threading.Lock()

       def get(self):
           current_key = self._key_getter()
           with self._lock:
               if self._client is None or self._last_key != current_key:
                   self._client = self._factory(current_key)
                   self._last_key = current_key
               return self._client

       def reset(self):
           with self._lock:
               self._client = None
               self._last_key = None
   ```

2. **In `openai_client.py`**, replace globals with `ClientCache`:
   - Remove lines 21-22 (`_client` and `_last_api_key` globals).
   - Add import: `from .common import ClientCache`
   - Create module-level cache:
     ```python
     _cache = ClientCache(
         client_factory=lambda key: OpenAI(api_key=key),
         key_getter=lambda: SETTINGS.openai_api_key
     )
     ```
   - Update `client()` function (lines 49-68):
     ```python
     def client() -> OpenAI:
         current_api_key = SETTINGS.openai_api_key
         if not _validate_api_key(current_api_key):
             raise OpenAIError("Invalid or missing OpenAI API key")
         return _cache.get()
     ```
   - Update `reset_client()` (lines 71-75):
     ```python
     def reset_client() -> None:
         _cache.reset()
     ```

3. **Apply the same pattern in `anthropic_client.py`**:
   - Remove lines 20-21 (`_client` and `_last_api_key` globals).
   - Add `ClientCache` usage with `Anthropic` client factory.
   - Update `client()` and `reset_client()` functions.

#### Files to Modify

- `src/providers/common.py` -- add `threading` import, add `Lock` to `ClientCache`
- `src/providers/openai_client.py` -- replace globals with `ClientCache`
- `src/providers/anthropic_client.py` -- replace globals with `ClientCache`

#### Success Criteria

- `grep "_client: Optional" src/providers/openai_client.py src/providers/anthropic_client.py` returns 0 matches.
- `grep "threading.Lock" src/providers/common.py` returns a match.
- `ClientCache` is used in both provider files.

#### Testing Gate

- **Existing tests**: `tests/unit/test_providers.py` must pass.
- **New test**: Verify thread safety by spawning two threads that simultaneously call `client()` -- no race condition should occur.
- **New test**: Verify `reset_client()` properly clears the cache.

#### Estimated Effort

3 hours.

#### Dependencies

None.

#### Risk Assessment

- **Medium risk**: Changing the client initialization pattern could affect lazy-loading behavior if any code depends on the global variable directly (not through the `client()` function).
- **Mitigation**: The `ClientCache.get()` method has identical semantics to the current global pattern, just with locking. Search for direct `_client` references: `grep "_client" src/providers/`.

---

### HI-04: `cli/app.py` `for/else` Logic Bug

**Severity**: HIGH

#### Current State

File: `cli/app.py:78-125`

```python
        if file_type == "video":
            # ... create workflow config (lines 83-93) ...
            results = execute_workflow(config, progress_callback)

            for step_name, step_results in results.items():        # line 102
                if step_name == "transcribe" and isinstance(step_results, dict):
                    if "transcript_file" in step_results:
                        # ... display results (lines 108-114) ...
                        break                                       # line 115
        else:                                                       # line 116
            # Direct transcription for audio files
            json_path, srt_path, audit_path = transcribe_audio(...)
```

The `else` clause at line 116 is attached to the `for` loop at line 102 (Python `for/else` semantics), **not** to the `if file_type == "video"` check at line 79. The `else` block executes when the `for` loop completes **without** hitting `break`. This means if the video workflow results don't contain a "transcribe" key, the code falls through and calls `transcribe_audio()` on a video file.

#### Target State

Explicit `if/elif` structure that clearly handles video vs audio paths.

#### Implementation Steps

1. **Restructure** the `cmd_transcribe` function (lines 78-125). Replace the `for/else` with explicit branching:

   ```python
   if file_type == "video":
       console.print("[yellow]Video file detected - extracting audio first...[/yellow]")
       config = WorkflowConfig(
           input_file=input_file,
           output_dir=output_dir,
           extract_audio=True,
           process_audio=True,
           transcribe=True,
           summarize=False,
           audio_format="m4a",
           audio_quality="high",
           normalize_audio=True
       )

       def progress_callback(step: int, total: int, step_name: str, status: str) -> None:
           console.print(f"[yellow]Step {step}/{total}:[/yellow] {status}")

       results = execute_workflow(config, progress_callback)

       # Extract transcript file path from results
       transcript_found = False
       for step_name, step_results in results.items():
           if step_name == "transcribe" and isinstance(step_results, dict):
               if "transcript_file" in step_results:
                   json_path = Path(step_results["transcript_file"])
                   srt_path = json_path.with_suffix('.srt')
                   audit_path = json_path.with_suffix('.audit.json')
                   console.print(f"[green]OK[/green] Transcription complete:")
                   console.print(f"  JSON: [cyan]{json_path}[/cyan]")
                   if srt_path.exists():
                       console.print(f"  SRT: [cyan]{srt_path}[/cyan]")
                   if audit_path.exists():
                       console.print(f"  Audit: [cyan]{audit_path}[/cyan]")
                   transcript_found = True
                   break

       if not transcript_found:
           console.print("[yellow]Warning: Transcription step did not produce output[/yellow]")

   else:
       # Direct transcription for audio files
       json_path, srt_path, audit_path = transcribe_audio(
           audio_path=input_file,
           output_dir=output_dir
       )
       console.print(f"[green]OK[/green] Transcription complete:")
       console.print(f"  JSON: [cyan]{json_path}[/cyan]")
       console.print(f"  SRT: [cyan]{srt_path}[/cyan]")
       console.print(f"  Audit: [cyan]{audit_path}[/cyan]")
   ```

   The key change: the `else` at the bottom is now clearly attached to `if file_type == "video"` via proper indentation, not to the `for` loop. The `for` loop uses a `transcript_found` flag instead of `for/else`.

#### Files to Modify

- `cli/app.py` -- restructure lines 78-125

#### Success Criteria

- The `for/else` pattern is eliminated.
- `grep -n "^        else:" cli/app.py` in the `cmd_transcribe` function shows the `else` is at the same indent level as `if file_type == "video"`.

#### Testing Gate

- **Existing tests**: `tests/e2e/test_cli_interface.py` must pass.
- **New test**: Mock a video workflow that returns results without a "transcribe" key -- verify `transcribe_audio` is NOT called on the video file.
- **New test**: Verify audio file path correctly calls `transcribe_audio` directly.

#### Estimated Effort

1 hour.

#### Dependencies

None.

#### Risk Assessment

Low risk. The fix makes the existing intent explicit. The `for/else` behavior was a bug, not a feature.

---

### HI-06: `get_data_manager` Ignores `base_dir` on Subsequent Calls

**Severity**: HIGH

#### Current State

File: `src/utils/fsio.py:253-260`

```python
_data_manager: Optional[DataManager] = None

def get_data_manager(base_dir: Path = None) -> DataManager:
    """Get global data manager instance."""
    global _data_manager
    if _data_manager is None:
        _data_manager = DataManager(base_dir)
    return _data_manager
```

After the first call creates the singleton, any subsequent call with a different `base_dir` silently ignores the new value and returns the original instance. This can cause data to be written to the wrong directory.

#### Target State

Function validates that the requested `base_dir` matches the existing instance, or raises `ValueError` on mismatch. A `reset_data_manager()` function enables re-initialization for testing.

#### Implementation Steps

1. **Update `get_data_manager`** (replace lines 255-260):
   ```python
   def get_data_manager(base_dir: Path = None) -> DataManager:
       """Get global data manager instance.

       Args:
           base_dir: Base directory for data storage. Must match existing
                     instance if one exists, or ValueError is raised.

       Returns:
           DataManager singleton instance

       Raises:
           ValueError: If base_dir conflicts with existing instance
       """
       global _data_manager
       if _data_manager is None:
           _data_manager = DataManager(base_dir)
       elif base_dir is not None and base_dir != _data_manager.base_dir:
           raise ValueError(
               f"DataManager already initialized with base_dir='{_data_manager.base_dir}', "
               f"cannot re-initialize with base_dir='{base_dir}'. "
               f"Call reset_data_manager() first if you need a different base directory."
           )
       return _data_manager
   ```

2. **Add `reset_data_manager`** function (after line 260):
   ```python
   def reset_data_manager() -> None:
       """Reset the global data manager instance.

       Intended for testing. Production code should not need to call this.
       """
       global _data_manager
       _data_manager = None
   ```

#### Files to Modify

- `src/utils/fsio.py` -- update `get_data_manager` (lines 255-260), add `reset_data_manager`

#### Success Criteria

- Calling `get_data_manager(Path("a"))` then `get_data_manager(Path("b"))` raises `ValueError`.
- Calling `get_data_manager(Path("a"))` then `get_data_manager(Path("a"))` succeeds.
- Calling `get_data_manager(Path("a"))` then `get_data_manager()` (no arg) succeeds.

#### Testing Gate

- **Existing tests**: `tests/unit/test_fsio.py` must pass (may need `reset_data_manager()` in fixtures).
- **New test**: Verify `ValueError` raised on mismatched `base_dir`.
- **New test**: Verify `reset_data_manager()` enables re-initialization.

#### Estimated Effort

1 hour.

#### Dependencies

None.

#### Risk Assessment

- **Low risk**: Any existing code that passes different `base_dir` values was already silently broken. The fix surfaces the error.
- **Action**: Test fixtures that use `get_data_manager` may need to call `reset_data_manager()` in teardown.

---

### HI-07: `SanitizingFormatter` Mutates `LogRecord` In-Place

**Severity**: HIGH

#### Current State

File: `src/utils/logging.py:45-55`

```python
class SanitizingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if record.msg:
            record.msg = sanitize_log_message(str(record.msg))
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: sanitize_log_message(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(sanitize_log_message(str(arg)) for arg in record.args)
        return super().format(record)
```

`LogRecord` objects are shared across all handlers. Mutating `record.msg` and `record.args` in-place means any subsequent handler (e.g., a debug file handler without sanitization) receives already-sanitized (masked) values, losing original debug information.

#### Target State

Work on a shallow copy of the record to avoid affecting other handlers.

#### Implementation Steps

1. **Add `import copy`** to the imports section of `src/utils/logging.py` (after line 2, near existing imports).

2. **Update the `format` method** (lines 45-55):
   ```python
   def format(self, record: logging.LogRecord) -> str:
       record = copy.copy(record)  # shallow copy to avoid mutating shared state
       if record.msg:
           record.msg = sanitize_log_message(str(record.msg))
       if record.args:
           if isinstance(record.args, dict):
               record.args = {k: sanitize_log_message(str(v)) for k, v in record.args.items()}
           elif isinstance(record.args, tuple):
               record.args = tuple(sanitize_log_message(str(arg)) for arg in record.args)
       return super().format(record)
   ```

#### Files to Modify

- `src/utils/logging.py` -- add `import copy` (line ~3), add `copy.copy(record)` (line ~46)

#### Success Criteria

- `grep "copy.copy(record)" src/utils/logging.py` returns a match.
- `grep "import copy" src/utils/logging.py` returns a match.
- Original `LogRecord` is unmodified after `SanitizingFormatter.format()` call.

#### Testing Gate

- **Existing tests**: `tests/unit/test_sanitization.py` must pass.
- **New test**: Create a LogRecord with an API key in the message, format with `SanitizingFormatter`, then verify the original record's `msg` still contains the original (unsanitized) value.

#### Estimated Effort

30 minutes.

#### Dependencies

None.

#### Risk Assessment

Low risk. `copy.copy()` is a shallow copy, sufficient since `msg` and `args` are replaced (not mutated in-place). Performance impact is negligible -- `LogRecord` is a small object.

---

## PHASE 3: TEST COVERAGE

These items require writing new test files. CR-07 and HI-12 can be done in parallel. HI-13 can be done in parallel with the others. HI-14 should be done last in this phase since it validates the test infrastructure.

---

### CR-07: Zero Test Coverage for Workflow Components

**Severity**: CRITICAL

#### Current State

File: `src/workflow_components.py` (222 lines)

Three classes with zero test coverage:
- `WorkflowValidator` (lines 15-56): Validates config, detects file type, checks file size, ensures output dir.
- `WorkflowStepFactory` (lines 59-158): Creates workflow steps with settings, filters executable steps by file type.
- `WorkflowExecutor` (lines 161-221): Executes steps sequentially with progress callbacks, handles errors.

Existing tests:
- `tests/unit/test_workflow_engine.py` -- covers `WorkflowEngine` in `src/workflow.py`
- `tests/unit/test_workflow_pipeline.py` -- covers pipeline integration

Neither covers these SRP-refactored components.

#### Target State

New test file `tests/unit/test_workflow_components.py` with comprehensive coverage of all three classes.

#### Implementation Steps

1. Create `tests/unit/test_workflow_components.py`.

2. **WorkflowValidator tests** (mock `validate_workflow_input` and `validate_file_size`):
   - `test_validate_video_file` -- valid video returns (path, "video")
   - `test_validate_audio_file` -- valid audio returns (path, "audio")
   - `test_validate_transcript_file` -- transcript skips file size validation
   - `test_validate_nonexistent_file_raises` -- SummeetsError on missing file
   - `test_validate_file_exceeding_size_raises` -- SummeetsError on oversized file
   - `test_validate_creates_output_dir` -- output_dir.mkdir called

3. **WorkflowStepFactory tests** (mock engine step functions):
   - `test_create_steps_video_input` -- creates 4 steps with correct names
   - `test_create_steps_audio_input` -- extract_audio disabled
   - `test_create_steps_transcript_input` -- only summarize enabled
   - `test_step_settings_passed_through` -- verify settings dict contents
   - `test_filter_executable_steps_video` -- all 4 steps executable for video
   - `test_filter_executable_steps_transcript` -- only summarize executable

4. **WorkflowExecutor tests** (mock step functions):
   - `test_execute_all_steps_success` -- returns results dict
   - `test_execute_progress_callback_called` -- callback receives (step, total, name, status)
   - `test_execute_step_failure_raises` -- SummeetsError with step name
   - `test_execute_empty_steps` -- returns empty dict
   - `test_execute_completion_callback` -- final callback with "complete" status

5. Use `unittest.mock.MagicMock` and `unittest.mock.patch` for all external dependencies.

#### Files to Modify

- Create `tests/unit/test_workflow_components.py`

#### Success Criteria

- `python -m pytest tests/unit/test_workflow_components.py -v` passes all tests.
- At minimum 15 test functions covering the three classes.
- Each class has at least 4 test functions.

#### Testing Gate

- All new tests pass.
- All existing tests in `tests/unit/test_workflow_engine.py` still pass.
- `python -m pytest tests/ -v` shows no regressions.

#### Estimated Effort

2 days.

#### Dependencies

None (tests mock all dependencies).

#### Risk Assessment

Low risk. Pure test addition with no production code changes.

---

### HI-12: Zero Test Coverage for Services Module

**Severity**: HIGH

#### Current State

Files with zero test coverage:
- `src/services/container.py` -- DI container with register/resolve/reset (145 lines)
- `src/services/interfaces.py` -- 3 ABC interfaces (149 lines)
- `src/services/implementations.py` -- 3 concrete implementations (~100 lines)

Mock services exist in `tests/fixtures/mock_services.py` but no tests exercise the actual container or implementations.

#### Target State

New test file `tests/unit/test_services.py` covering registration, resolution, implementation delegation, and interface conformance.

#### Implementation Steps

1. Create `tests/unit/test_services.py`.

2. **ServiceContainer tests**:
   - `test_register_and_resolve_singleton` -- same instance on repeated resolve
   - `test_register_and_resolve_transient` -- different instance each time
   - `test_register_instance` -- pre-created instance returned
   - `test_register_factory` -- factory called on resolve
   - `test_resolve_unregistered_raises_key_error` -- KeyError
   - `test_reset_clears_all` -- resolve fails after reset
   - `test_is_registered_true` -- returns True for registered
   - `test_is_registered_false` -- returns False for unregistered
   - `test_convenience_methods` -- get_audio_processor, get_transcriber, get_summarizer

3. **Interface conformance tests**:
   - `test_ffmpeg_processor_implements_interface` -- all abstract methods present
   - `test_replicate_transcriber_implements_interface` -- all abstract methods
   - `test_summarizer_implements_interface` -- all abstract methods

4. **Implementation delegation tests** (with mocked FFmpeg/API):
   - `test_ffmpeg_processor_probe_delegates` -- calls ffmpeg_ops.probe
   - `test_ffmpeg_processor_extract_audio_with_codec` -- calls extract_audio_reencode
   - `test_ffmpeg_processor_extract_audio_without_codec` -- calls extract_audio_copy

   Note: After CR-06 is fixed, tests should create fresh `ServiceContainer()` instances. If done before CR-06, use `ServiceContainer.reset()` in a fixture.

#### Files to Modify

- Create `tests/unit/test_services.py`

#### Success Criteria

- `python -m pytest tests/unit/test_services.py -v` passes all tests.
- At minimum 12 test functions.
- ServiceContainer registration/resolution behavior fully covered.

#### Testing Gate

- All new tests pass.
- `python -m pytest tests/ -v` shows no regressions.

#### Estimated Effort

1 day.

#### Dependencies

- **Recommended**: CR-06 completed first so tests use instance-level state. If done in parallel, add `ServiceContainer.reset()` to test fixtures.

#### Risk Assessment

Low risk. Pure test addition.

---

### HI-13: Summarization Components Insufficiently Tested

**Severity**: HIGH

#### Current State

Files with minimal or no test coverage:
- `src/summarize/chunking.py` -- time-based chunking logic for transcript segments
- `src/summarize/strategies.py` -- strategy patterns for different summarization approaches
- `src/summarize/refiners.py` -- Chain-of-Density refinement logic

Existing `tests/integration/test_summarization_pipeline.py` tests the high-level pipeline but not these individual components. Incorrect chunking is a functional risk: too-large chunks cause LLM context overflow; too-small chunks lose context.

#### Target State

Three new test files covering chunking boundary conditions, strategy execution, and refinement logic.

#### Implementation Steps

1. **Create `tests/unit/test_chunking.py`**:
   - `test_single_segment_one_chunk` -- single segment produces one chunk
   - `test_segments_shorter_than_limit` -- all segments fit in one chunk
   - `test_segments_at_exact_boundary` -- chunk split at exactly chunk_seconds
   - `test_segments_spanning_multiple_chunks` -- correct number of chunks
   - `test_empty_segments` -- empty input returns empty/single chunk
   - `test_chunk_text_formatting` -- segments formatted as "Speaker: text"
   - `test_chunk_boundary_speaker_alignment` -- chunks don't split mid-speaker-turn
   - `test_large_segment_exceeds_chunk` -- single large segment handled
   Use `tests/fixtures/transcript_samples.py` for realistic test data.

2. **Create `tests/unit/test_strategies.py`**:
   - `test_default_strategy_selection` -- default template uses default strategy
   - `test_sop_strategy_selection` -- SOP template uses SOP strategy
   - `test_strategy_execution_with_mock_llm` -- mocked LLM returns expected format
   - `test_strategy_error_handling` -- LLM failure raises appropriate error
   - `test_strategy_output_format` -- output conforms to expected structure

3. **Create `tests/unit/test_refiners.py`**:
   - `test_cod_zero_passes` -- 0 passes returns input unchanged
   - `test_cod_one_pass` -- single pass calls LLM once
   - `test_cod_multiple_passes` -- N passes calls LLM N times with iterative input
   - `test_cod_error_midpass` -- LLM failure on pass 2 of 3 raises error
   - `test_cod_empty_input` -- empty string handled gracefully

#### Files to Modify

- Create `tests/unit/test_chunking.py`
- Create `tests/unit/test_strategies.py`
- Create `tests/unit/test_refiners.py`

#### Success Criteria

- All three test files pass independently.
- At minimum 20 test functions total across the three files.
- Chunking boundary conditions are thoroughly tested (especially the context-overflow risk).

#### Testing Gate

- All new tests pass.
- `tests/integration/test_summarization_pipeline.py` still passes.
- `python -m pytest tests/ -v` shows no regressions.

#### Estimated Effort

3 days.

#### Dependencies

None (tests mock LLM calls).

#### Risk Assessment

Low risk. Pure test addition.

---

### HI-14: No CI/CD Configuration for Unit/Integration Tests

**Severity**: HIGH

#### Current State

A CI workflow exists at `.github/workflows/playwright-gui-tests.yml` but only runs Playwright GUI tests (triggered on push to main/develop, PR to main). No CI for:
- Unit tests (`tests/unit/`)
- Integration tests (`tests/integration/`)
- Linting (ruff)
- Type checking (mypy)
- Coverage reporting

`pyproject.toml` already has `[project.optional-dependencies] test` with `pytest`, `pytest-asyncio`, and `pytest-cov`.

#### Target State

GitHub Actions workflow running unit tests, integration tests, linting, and type checking on every push and PR.

#### Implementation Steps

1. **Create `.github/workflows/ci.yml`**:
   ```yaml
   name: CI

   on:
     push:
       branches: [main, develop]
     pull_request:
       branches: [main]

   jobs:
     lint:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-python@v5
           with:
             python-version: "3.11"
         - run: pip install ruff
         - run: ruff check .

     typecheck:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-python@v5
           with:
             python-version: "3.11"
         - run: pip install -e ".[dev]"
         - run: mypy src/ cli/ --ignore-missing-imports

     test:
       runs-on: ${{ matrix.os }}
       strategy:
         matrix:
           os: [ubuntu-latest, windows-latest]
           python-version: ["3.11", "3.12"]
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-python@v5
           with:
             python-version: ${{ matrix.python-version }}
         - run: pip install -e ".[test]"
         - run: python -m pytest tests/unit/ tests/integration/ -v --tb=short
           env:
             OPENAI_API_KEY: ""
             ANTHROPIC_API_KEY: ""
             REPLICATE_API_TOKEN: ""

     coverage:
       runs-on: ubuntu-latest
       needs: test
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-python@v5
           with:
             python-version: "3.11"
         - run: pip install -e ".[test]"
         - run: python -m pytest tests/unit/ --cov=src --cov-report=xml --cov-report=term-missing
           env:
             OPENAI_API_KEY: ""
             ANTHROPIC_API_KEY: ""
             REPLICATE_API_TOKEN: ""
         - uses: codecov/codecov-action@v4
           if: always()
   ```

2. **Verify** unit tests can run without actual API keys (they should mock all API calls).

3. **Add FFmpeg installation step** if any tests require it:
   ```yaml
   - name: Install FFmpeg
     uses: FedericoCarboni/setup-ffmpeg@v3
   ```

#### Files to Modify

- Create `.github/workflows/ci.yml`

#### Success Criteria

- GitHub Actions workflow runs successfully on push to main.
- All jobs (lint, typecheck, test, coverage) complete.
- Test matrix runs on both Ubuntu and Windows.

#### Testing Gate

- Push a branch and verify the workflow runs.
- All unit tests pass in CI.
- Document any known failures as pre-existing issues.

#### Estimated Effort

1 day (including debugging CI-specific issues like path differences, missing FFmpeg, etc.).

#### Dependencies

- **Best after**: CR-07, HI-12, HI-13 so CI runs meaningful test coverage.
- **Can be done in parallel** if CI is set up to run whatever tests currently exist.

#### Risk Assessment

- **Low risk**: CI configuration does not change production code.
- **Known issue**: Tests that depend on FFmpeg binary may fail in CI if FFmpeg is not installed. Add conditional skips or install FFmpeg in the workflow.

---

## PHASE 4: DOCUMENTATION AND INFRASTRUCTURE

These items can all be done in parallel.

---

### HI-02: No Dependency Lock File

**Severity**: HIGH | **OWASP**: A06:2021, A08:2021

#### Current State

`pyproject.toml` uses range specifiers:
```toml
dependencies = [
  "typer>=0.12,<1.0",
  "pydantic>=2.7,<3.0",
  "openai>=1.40.0,<2.0",
  ...
]
```

No lock file with pinned versions. No hash verification. A compromised version within the allowed range would be installed automatically. Supply chain attack vector.

#### Target State

- Pinned lock file with hash verification generated by `pip-compile`.
- `pip-audit` integrated into CI for vulnerability scanning.

#### Implementation Steps

1. **Install pip-tools**:
   ```bash
   pip install pip-tools
   ```

2. **Generate lock file with hashes**:
   ```bash
   pip-compile --generate-hashes pyproject.toml -o requirements.lock
   ```

3. **Generate dev/test lock file**:
   ```bash
   pip-compile --generate-hashes --extra dev --extra test pyproject.toml -o requirements-dev.lock
   ```

4. **Add lock files to version control** (git add).

5. **Add `pip-audit` job to CI** (in `.github/workflows/ci.yml`):
   ```yaml
   security:
     runs-on: ubuntu-latest
     steps:
       - uses: actions/checkout@v4
       - uses: actions/setup-python@v5
         with:
           python-version: "3.11"
       - run: pip install pip-audit
       - run: pip-audit -r requirements.lock
   ```

6. **Document** in README: "For reproducible installs, use `pip install -r requirements.lock`."

#### Files to Modify

- Create `requirements.lock`
- Create `requirements-dev.lock`
- Update `.github/workflows/ci.yml` -- add security audit job

#### Success Criteria

- `requirements.lock` exists with exact version pins and `--hash` lines.
- `pip install -r requirements.lock` installs reproducible environment.
- `pip-audit -r requirements.lock` reports no known vulnerabilities (or documents accepted risks).

#### Testing Gate

- `pip install -r requirements.lock` succeeds in a fresh virtualenv.
- Full test suite passes with locked dependencies.

#### Estimated Effort

2 hours.

#### Dependencies

- HI-14 (CI/CD) should exist first to add the security audit job.

#### Risk Assessment

Low risk. Lock files are additive. Existing `pip install -e .` workflow continues to work.

---

### HI-08: README Architecture Diagram References Wrong Directory

**Severity**: HIGH

#### Current State

File: `README.md:172-203`

The architecture diagram references `core/` throughout:
```
summeets/
|-- core/                    # Shared processing core
|   |-- models.py
|   |-- config.py
...
```

The actual directory is `src/`, not `core/`. Additionally references non-existent files:
- `core/utils/file_utils.py` -- does not exist (actual: `src/utils/fsio.py`)
- `core/utils/text_utils.py` -- does not exist
- Missing: `src/services/`, `src/summarize/` sub-modules, `src/workflow_components.py`

#### Target State

README architecture diagram matches the actual `src/` directory structure. All referenced files exist.

#### Implementation Steps

1. **Replace** the architecture section (lines 172-203) with the actual structure. Use the CLAUDE.md architecture section as the authoritative source, but verify against actual file listing.

2. **Update all `core/` references** in the entire README:
   ```bash
   grep -n "core/" README.md
   ```
   Replace each with `src/`.

3. **Verify every file** listed in the new diagram exists:
   ```bash
   # For each listed file path, check existence
   ls src/models.py src/workflow.py src/audio/ffmpeg_ops.py ...
   ```

#### Files to Modify

- `README.md` -- replace architecture section, update all `core/` references

#### Success Criteria

- `grep "core/" README.md` returns 0 matches.
- Architecture diagram references `src/` throughout.
- Spot-check: at least 5 randomly selected files from the diagram exist at the listed paths.

#### Testing Gate

- No code tests required.
- Manual verification: compare README diagram to `ls -R src/`.

#### Estimated Effort

1 hour.

#### Dependencies

None.

#### Risk Assessment

Low risk. Documentation-only change.

---

### HI-10: No Generated API Reference Documentation

**Severity**: HIGH

#### Current State

Docstrings exist at ~91% module coverage and ~85% public function coverage, but are only accessible by reading source code. No Sphinx, mkdocs, or similar documentation generator is configured.

#### Target State

mkdocs with mkdocstrings configured to generate browsable API reference from existing docstrings.

#### Implementation Steps

1. **Add documentation dependencies** to `pyproject.toml`:
   ```toml
   [project.optional-dependencies]
   docs = [
     "mkdocs>=1.5.0",
     "mkdocstrings[python]>=0.24.0",
     "mkdocs-material>=9.5.0",
   ]
   ```

2. **Create `mkdocs.yml`** at repository root with site configuration, material theme, mkdocstrings plugin, and nav structure covering all public modules.

3. **Create `docs/` directory** with:
   - `index.md` -- overview (can reference README content)
   - `api/models.md` containing `::: src.models`
   - `api/workflow.md` containing `::: src.workflow`
   - `api/audio.md` containing `::: src.audio`
   - `api/transcribe.md` containing `::: src.transcribe`
   - `api/summarize.md` containing `::: src.summarize`
   - `api/providers.md` containing `::: src.providers`
   - `api/utils.md` containing `::: src.utils`
   - `api/services.md` containing `::: src.services`

4. **Verify docs build**: `mkdocs build`.

5. **Add docs build** to CI (optional, in `.github/workflows/ci.yml`):
   ```yaml
   docs:
     runs-on: ubuntu-latest
     steps:
       - uses: actions/checkout@v4
       - uses: actions/setup-python@v5
       - run: pip install -e ".[docs]"
       - run: mkdocs build --strict
   ```

#### Files to Modify

- `pyproject.toml` -- add `[project.optional-dependencies] docs`
- Create `mkdocs.yml`
- Create `docs/` directory with index and API reference pages

#### Success Criteria

- `pip install -e ".[docs]" && mkdocs build` completes without errors.
- Generated site contains navigable API reference for all public modules.
- Docstrings render correctly in the generated HTML.

#### Testing Gate

- `mkdocs build --strict` passes (warnings treated as errors).

#### Estimated Effort

2 days.

#### Dependencies

None.

#### Risk Assessment

Low risk. Pure documentation infrastructure, no production code changes.

---

### HI-11: No Architecture Decision Records (ADRs)

**Severity**: HIGH

#### Current State

Key design decisions are undocumented:
- Why map-reduce + Chain-of-Density for summarization
- Why Pydantic settings over configparser/environ
- Why composition over inheritance in workflow engine
- Why dual CLI/TUI architecture sharing a core
- Why Replicate for transcription instead of local Whisper

#### Target State

`docs/adr/` directory with initial ADRs documenting key architectural decisions.

#### Implementation Steps

1. **Create `docs/adr/` directory**.

2. **Create initial ADRs** using the Michael Nygard format (Title, Status, Context, Decision, Consequences):

   - `0001-use-map-reduce-summarization.md`:
     Context: Long transcripts exceed LLM context windows.
     Decision: Time-based chunking + map-reduce + Chain-of-Density refinement.
     Consequences: Handles arbitrary length transcripts; possible coherence loss at chunk boundaries.

   - `0002-use-pydantic-settings.md`:
     Context: Configuration from multiple sources (env vars, .env file, defaults).
     Decision: Pydantic BaseSettings with environment variable loading.
     Consequences: Type-safe config, automatic validation, easy testing.

   - `0003-composition-based-workflow-engine.md`:
     Context: Pipeline varies by input type (video/audio/transcript).
     Decision: WorkflowConfig + conditional step execution via composition.
     Consequences: Flexible pipelines without subclassing; single engine handles all input types.

   - `0004-dual-cli-tui-architecture.md`:
     Context: Need both quick CLI for automation and interactive TUI for manual use.
     Decision: Shared `src/` core with separate `cli/app.py` (Typer) and `cli/tui/` (Textual).
     Consequences: Business logic tested once, two presentation layers.

   - `0005-use-replicate-for-transcription.md`:
     Context: Whisper transcription requires GPU resources.
     Decision: Use Replicate API (hosted Whisper v3 + Pyannote diarization).
     Consequences: No local GPU needed; adds API dependency; higher latency for short files.

#### Files to Modify

- Create `docs/adr/` directory
- Create 5 ADR files

#### Success Criteria

- At least 5 ADR files exist in `docs/adr/`.
- Each ADR follows the standard format (Title, Status, Context, Decision, Consequences).
- Content accurately reflects the codebase's actual architecture.

#### Testing Gate

- No code tests required.
- Review each ADR for accuracy against codebase evidence.

#### Estimated Effort

1 day.

#### Dependencies

None.

#### Risk Assessment

Low risk. Pure documentation.

---

## DEPENDENCY GRAPH

```
Phase 1 (All parallel -- no dependencies):
  CR-01 (API key rotation)
  CR-08 (LICENSE file)
  HI-09 (CHANGELOG)
  HI-05 (functools.wraps)

Phase 2 (All items parallel with each other):
  CR-02 (duplicate SummaryTemplate enum)
  CR-03 (duplicate exception classes)
  CR-04 (signal handler sys.exit)
  CR-05 (stream_json_array rename)
  CR-06 (ServiceContainer class-level state)
  HI-01 (API key masking)
  HI-03 (provider thread safety)
  HI-04 (for/else logic bug)
  HI-06 (get_data_manager singleton)
  HI-07 (SanitizingFormatter mutation)

Phase 3 (Partially parallel):
  CR-07 (workflow component tests)     -- no deps
  HI-12 (services tests)              -- best after CR-06
  HI-13 (summarization tests)         -- no deps
  HI-14 (CI/CD)                       -- best after CR-07, HI-12, HI-13

Phase 4 (All parallel):
  HI-02 (dependency lock file)        -- best after HI-14
  HI-08 (README architecture)         -- no deps
  HI-10 (API docs with mkdocs)        -- no deps
  HI-11 (ADRs)                        -- no deps
```

### Critical Path

```
Phase 1 (~3 hours) --> Phase 2 (~4 days) --> Phase 3 (~8 days) --> Phase 4 (~5 days)
```

With parallelization (2 developers):
- Phase 1: 3 hours (all parallel)
- Phase 2: ~2 days (all 10 items parallel across 2 devs)
- Phase 3: ~4 days (test writing is mostly independent)
- Phase 4: ~3 days (all parallel across 2 devs)

**Realistic timeline with 2 developers**: ~10 working days (2 sprints).
**Realistic timeline with 1 developer**: ~17 working days (3-4 sprints).

---

## VERIFICATION CHECKLIST

Run this full verification sequence after all remediations are complete.

### Code Quality Checks

```bash
# CR-02: Single SummaryTemplate enum
grep -rn "class SummaryTemplate" src/
# Expected: exactly 1 result (src/models.py)

# CR-03: No duplicate exceptions
grep -rn "class TranscriptionError" src/
# Expected: exactly 1 result (src/utils/exceptions.py)

grep -rn "class CompressionError" src/
# Expected: 0 results (it is an alias now)

grep -rn "class ErrorContext" src/
# Expected: exactly 1 result (src/utils/exceptions.py)

# CR-04: No sys.exit in signal handler
grep "sys.exit" src/utils/shutdown.py
# Expected: 0 matches

# CR-05: No misleading function names
grep -rn "stream_json_array" src/
# Expected: 0 matches

# CR-06: No class-level mutable state in ServiceContainer
grep "@classmethod" src/services/container.py
# Expected: 0 matches

# HI-03: No module-level client globals
grep "_client: Optional" src/providers/openai_client.py src/providers/anthropic_client.py
# Expected: 0 matches

# HI-05: functools.wraps present
grep "functools.wraps" src/utils/exceptions.py
# Expected: 1 match

# HI-07: copy.copy used in formatter
grep "copy.copy(record)" src/utils/logging.py
# Expected: 1 match
```

### Security Checks

```bash
# CR-01: No plaintext API keys
grep -E "sk-[a-zA-Z0-9]{10}|r8_[a-zA-Z0-9]{10}" .env
# Expected: 0 matches

# HI-01: Masking shows only prefix
python -c "from src.utils.config import mask_api_key; result = mask_api_key('sk-abc123def456ghi789jkl'); assert result.endswith('***configured***'), f'Got: {result}'"
# Expected: no assertion error

# HI-02: Lock file exists
test -f requirements.lock && echo "OK" || echo "MISSING"
# Expected: OK
```

### Documentation Checks

```bash
# CR-08: LICENSE exists
test -f LICENSE && echo "OK" || echo "MISSING"
# Expected: OK

# HI-08: No core/ references in README
grep "core/" README.md
# Expected: 0 matches

# HI-09: CHANGELOG exists
test -f CHANGELOG.md && echo "OK" || echo "MISSING"
# Expected: OK

# HI-10: mkdocs builds
mkdocs build --strict 2>&1 | tail -1
# Expected: no errors

# HI-11: ADRs exist
ls docs/adr/*.md | wc -l
# Expected: >= 5
```

### Test Checks

```bash
# Full test suite
python -m pytest tests/ -v
# Expected: all pass

# New test files exist
python -m pytest tests/unit/test_workflow_components.py -v  # CR-07
python -m pytest tests/unit/test_services.py -v             # HI-12
python -m pytest tests/unit/test_chunking.py -v             # HI-13
python -m pytest tests/unit/test_strategies.py -v           # HI-13
python -m pytest tests/unit/test_refiners.py -v             # HI-13
# Expected: all pass

# HI-14: CI workflow exists
test -f .github/workflows/ci.yml && echo "OK" || echo "MISSING"
# Expected: OK
```

### Integration Verification

```bash
# End-to-end CLI checks
summeets health        # All systems operational
summeets config        # Masked keys show prefix only
summeets templates     # Lists all 5 templates correctly
```

---

*Generated from MASTER_CODEBASE_REVIEW.md findings on 2026-02-06.*
*Covers 8 CRITICAL + 14 HIGH severity items across 4 execution phases.*
