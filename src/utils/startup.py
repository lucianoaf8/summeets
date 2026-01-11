"""
Startup validation utilities.
Validates required configuration and API keys before CLI operations.
"""
import logging
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any

from .config import SETTINGS
from .exceptions import ConfigurationError

log = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Level of validation strictness."""
    WARN = "warn"  # Log warning but continue
    ERROR = "error"  # Raise error and stop


@dataclass
class ValidationResult:
    """Result of a validation check."""
    passed: bool
    message: str
    level: ValidationLevel = ValidationLevel.ERROR
    details: Optional[Dict[str, Any]] = None


@dataclass
class StartupValidationResult:
    """Aggregated results of all startup validations."""
    passed: bool
    errors: List[ValidationResult] = field(default_factory=list)
    warnings: List[ValidationResult] = field(default_factory=list)

    def add_result(self, result: ValidationResult) -> None:
        """Add a validation result."""
        if not result.passed:
            if result.level == ValidationLevel.ERROR:
                self.errors.append(result)
                self.passed = False
            else:
                self.warnings.append(result)

    def get_error_messages(self) -> List[str]:
        """Get all error messages."""
        return [r.message for r in self.errors]

    def get_warning_messages(self) -> List[str]:
        """Get all warning messages."""
        return [r.message for r in self.warnings]


def validate_openai_api_key(api_key: Optional[str]) -> ValidationResult:
    """
    Validate OpenAI API key format.

    Args:
        api_key: API key to validate

    Returns:
        ValidationResult with pass/fail status
    """
    import re

    if not api_key:
        return ValidationResult(
            passed=False,
            message="OpenAI API key not configured (OPENAI_API_KEY)",
            level=ValidationLevel.WARN
        )

    if not (api_key.startswith('sk-') or api_key.startswith('sk-proj-')):
        return ValidationResult(
            passed=False,
            message="OpenAI API key has invalid format (should start with 'sk-' or 'sk-proj-')",
            level=ValidationLevel.ERROR
        )

    if len(api_key) < 20:
        return ValidationResult(
            passed=False,
            message="OpenAI API key appears to be too short",
            level=ValidationLevel.ERROR
        )

    if not re.match(r'^[a-zA-Z0-9_-]+$', api_key):
        return ValidationResult(
            passed=False,
            message="OpenAI API key contains invalid characters",
            level=ValidationLevel.ERROR
        )

    return ValidationResult(passed=True, message="OpenAI API key validated")


def validate_anthropic_api_key(api_key: Optional[str]) -> ValidationResult:
    """
    Validate Anthropic API key format.

    Args:
        api_key: API key to validate

    Returns:
        ValidationResult with pass/fail status
    """
    import re

    if not api_key:
        return ValidationResult(
            passed=False,
            message="Anthropic API key not configured (ANTHROPIC_API_KEY)",
            level=ValidationLevel.WARN
        )

    if not api_key.startswith('sk-ant-'):
        return ValidationResult(
            passed=False,
            message="Anthropic API key has invalid format (should start with 'sk-ant-')",
            level=ValidationLevel.ERROR
        )

    if len(api_key) < 30:
        return ValidationResult(
            passed=False,
            message="Anthropic API key appears to be too short",
            level=ValidationLevel.ERROR
        )

    if not re.match(r'^[a-zA-Z0-9_-]+$', api_key):
        return ValidationResult(
            passed=False,
            message="Anthropic API key contains invalid characters",
            level=ValidationLevel.ERROR
        )

    return ValidationResult(passed=True, message="Anthropic API key validated")


def validate_replicate_api_token(api_token: Optional[str]) -> ValidationResult:
    """
    Validate Replicate API token format.

    Args:
        api_token: API token to validate

    Returns:
        ValidationResult with pass/fail status
    """
    import re

    if not api_token:
        return ValidationResult(
            passed=False,
            message="Replicate API token not configured (REPLICATE_API_TOKEN)",
            level=ValidationLevel.WARN
        )

    if not api_token.startswith('r8_'):
        return ValidationResult(
            passed=False,
            message="Replicate API token has invalid format (should start with 'r8_')",
            level=ValidationLevel.ERROR
        )

    if len(api_token) < 20:
        return ValidationResult(
            passed=False,
            message="Replicate API token appears to be too short",
            level=ValidationLevel.ERROR
        )

    if not re.match(r'^[a-zA-Z0-9_]+$', api_token):
        return ValidationResult(
            passed=False,
            message="Replicate API token contains invalid characters",
            level=ValidationLevel.ERROR
        )

    return ValidationResult(passed=True, message="Replicate API token validated")


def validate_ffmpeg_availability() -> ValidationResult:
    """
    Check if FFmpeg is available.

    Returns:
        ValidationResult with pass/fail status
    """
    ffmpeg_path = shutil.which(SETTINGS.ffmpeg_bin)
    ffprobe_path = shutil.which(SETTINGS.ffprobe_bin)

    if not ffmpeg_path:
        return ValidationResult(
            passed=False,
            message=f"FFmpeg not found in PATH ({SETTINGS.ffmpeg_bin})",
            level=ValidationLevel.WARN,
            details={"ffmpeg_bin": SETTINGS.ffmpeg_bin}
        )

    if not ffprobe_path:
        return ValidationResult(
            passed=False,
            message=f"FFprobe not found in PATH ({SETTINGS.ffprobe_bin})",
            level=ValidationLevel.WARN,
            details={"ffprobe_bin": SETTINGS.ffprobe_bin}
        )

    return ValidationResult(
        passed=True,
        message="FFmpeg available",
        details={"ffmpeg_path": ffmpeg_path, "ffprobe_path": ffprobe_path}
    )


def validate_disk_space(min_gb: float = 1.0) -> ValidationResult:
    """
    Check available disk space.

    Args:
        min_gb: Minimum required space in GB

    Returns:
        ValidationResult with pass/fail status
    """
    import os

    try:
        # Check space in data directory or current directory
        check_path = SETTINGS.data_dir if SETTINGS.data_dir.exists() else Path.cwd()

        if hasattr(os, 'statvfs'):
            # Unix
            stat = os.statvfs(check_path)
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
        else:
            # Windows
            import ctypes
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                str(check_path), None, None, ctypes.pointer(free_bytes)
            )
            free_gb = free_bytes.value / (1024 ** 3)

        if free_gb < min_gb:
            return ValidationResult(
                passed=False,
                message=f"Low disk space: {free_gb:.1f}GB available (minimum {min_gb}GB recommended)",
                level=ValidationLevel.WARN,
                details={"free_gb": free_gb, "min_gb": min_gb}
            )

        return ValidationResult(
            passed=True,
            message=f"Disk space OK: {free_gb:.1f}GB available",
            details={"free_gb": free_gb}
        )
    except Exception as e:
        return ValidationResult(
            passed=True,  # Don't fail on disk check errors
            message=f"Could not check disk space: {e}",
            level=ValidationLevel.WARN
        )


def validate_provider_for_operation(
    provider: str,
    operation: str = "summarization"
) -> ValidationResult:
    """
    Validate that the required provider is configured.

    Args:
        provider: Provider name (openai, anthropic)
        operation: Description of the operation

    Returns:
        ValidationResult with pass/fail status
    """
    provider = provider.lower()

    if provider == "openai":
        result = validate_openai_api_key(SETTINGS.openai_api_key)
        if not result.passed and result.level == ValidationLevel.WARN:
            # Upgrade to error if this provider is required
            return ValidationResult(
                passed=False,
                message=f"OpenAI API key required for {operation} but not configured",
                level=ValidationLevel.ERROR
            )
        return result

    elif provider == "anthropic":
        result = validate_anthropic_api_key(SETTINGS.anthropic_api_key)
        if not result.passed and result.level == ValidationLevel.WARN:
            return ValidationResult(
                passed=False,
                message=f"Anthropic API key required for {operation} but not configured",
                level=ValidationLevel.ERROR
            )
        return result

    else:
        return ValidationResult(
            passed=False,
            message=f"Unknown provider: {provider}. Supported: openai, anthropic",
            level=ValidationLevel.ERROR
        )


def validate_startup(
    require_transcription: bool = False,
    require_summarization: bool = False,
    provider: Optional[str] = None
) -> StartupValidationResult:
    """
    Run all startup validations.

    Args:
        require_transcription: Whether transcription capability is required
        require_summarization: Whether summarization capability is required
        provider: Specific provider to validate (uses SETTINGS.provider if not specified)

    Returns:
        StartupValidationResult with all validation results
    """
    result = StartupValidationResult(passed=True)

    # Check FFmpeg
    result.add_result(validate_ffmpeg_availability())

    # Check disk space
    result.add_result(validate_disk_space())

    # Check transcription capability if required
    if require_transcription:
        replicate_result = validate_replicate_api_token(SETTINGS.replicate_api_token)
        if not replicate_result.passed:
            # Upgrade warning to error
            result.add_result(ValidationResult(
                passed=False,
                message="Replicate API token required for transcription but not configured",
                level=ValidationLevel.ERROR
            ))
        else:
            result.add_result(replicate_result)
    else:
        # Just check format if provided
        if SETTINGS.replicate_api_token:
            result.add_result(validate_replicate_api_token(SETTINGS.replicate_api_token))

    # Check summarization capability if required
    if require_summarization:
        check_provider = provider or SETTINGS.provider
        result.add_result(validate_provider_for_operation(check_provider, "summarization"))
    else:
        # Just check format if provided
        if SETTINGS.openai_api_key:
            openai_result = validate_openai_api_key(SETTINGS.openai_api_key)
            if not openai_result.passed and openai_result.level == ValidationLevel.ERROR:
                result.add_result(openai_result)

        if SETTINGS.anthropic_api_key:
            anthropic_result = validate_anthropic_api_key(SETTINGS.anthropic_api_key)
            if not anthropic_result.passed and anthropic_result.level == ValidationLevel.ERROR:
                result.add_result(anthropic_result)

    return result


def check_startup_requirements(
    require_transcription: bool = False,
    require_summarization: bool = False,
    provider: Optional[str] = None,
    raise_on_error: bool = True
) -> StartupValidationResult:
    """
    Check startup requirements and optionally raise on errors.

    Args:
        require_transcription: Whether transcription capability is required
        require_summarization: Whether summarization capability is required
        provider: Specific provider to validate
        raise_on_error: Whether to raise ConfigurationError on validation failures

    Returns:
        StartupValidationResult with all validation results

    Raises:
        ConfigurationError: If validation fails and raise_on_error is True
    """
    result = validate_startup(
        require_transcription=require_transcription,
        require_summarization=require_summarization,
        provider=provider
    )

    # Log warnings
    for warning in result.warnings:
        log.warning(warning.message)

    # Handle errors
    if not result.passed:
        error_messages = result.get_error_messages()
        log.error("Startup validation failed: %s", "; ".join(error_messages))

        if raise_on_error:
            raise ConfigurationError(
                message="Startup validation failed",
                details={"errors": error_messages}
            )

    return result
