"""
Input validation and sanitization utilities.
Provides comprehensive validation for user inputs across the application.
"""
import os
import re
import logging
from pathlib import Path
from typing import Optional, Union, List
from urllib.parse import urlparse

# Import from centralized exceptions module
from .exceptions import ValidationError, sanitize_path

log = logging.getLogger(__name__)

# Enhanced security patterns for path traversal prevention
SUSPICIOUS_PATTERNS = [
    r'\.\.[\\/]',  # Directory traversal (../ and ..\)
    r'[\\/]\.\.[\\/]',  # Directory traversal in middle of path
    r'[\\/]\.\.$',  # Directory traversal at end
    r'\.\.%2f',  # URL encoded traversal
    r'\.\.%5c',  # URL encoded traversal (backslash)
    r'%2e%2e%2f',  # Double URL encoded traversal
    r'%252e%252e%252f',  # Triple URL encoded traversal
    r'[<>"|*?]',  # Invalid filename chars
    r'^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\.|$)',  # Windows reserved names
    r'^\s*$',  # Empty or whitespace only
    r'[\x00-\x1f]',  # Control characters
    r'[\x7f-\x9f]',  # Extended control characters
]

MAX_PATH_LENGTH = 260  # Windows MAX_PATH limit
MAX_FILENAME_LENGTH = 255
SUPPORTED_AUDIO_EXTENSIONS = {'.m4a', '.mka', '.ogg', '.mp3', '.wav', '.webm', '.flac'}
SUPPORTED_VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
SUPPORTED_TRANSCRIPT_EXTENSIONS = {'.json', '.txt', '.srt'}

# Re-export for backward compatibility
__all__ = ['ValidationError', 'validate_safe_path', 'sanitize_path_input', 'validate_audio_path',
           'validate_output_directory', 'validate_filename', 'validate_provider_name',
           'validate_positive_number', 'validate_integer_range', 'validate_transcript_file',
           'validate_output_dir', 'validate_model_name', 'validate_video_path',
           'validate_transcript_path', 'detect_file_type', 'validate_workflow_input',
           'validate_llm_provider', 'validate_summary_template', 'VALID_PROVIDERS', 'VALID_TEMPLATES']

# Valid providers and templates (single source of truth)
VALID_PROVIDERS = frozenset({'openai', 'anthropic'})
VALID_TEMPLATES = frozenset({'default', 'sop', 'decision', 'brainstorm', 'requirements'})


def validate_safe_path(path: Union[str, Path], allowed_directories: Optional[List[Path]] = None) -> Path:
    """
    Validate path is safe and within allowed directories.
    
    Args:
        path: Path to validate
        allowed_directories: List of allowed parent directories (None = allow all)
        
    Returns:
        Resolved and validated Path object
        
    Raises:
        ValidationError: If path is unsafe or outside allowed directories
    """
    if isinstance(path, str):
        path_str = sanitize_path_input(path)
        path = Path(path_str)
    
    # Resolve to absolute path to handle symlinks and relative paths
    try:
        resolved_path = path.resolve()
    except (OSError, RuntimeError) as e:
        raise ValidationError(f"Failed to resolve path: {e}")
    
    # Additional security check: ensure resolved path doesn't contain traversal
    path_str = str(resolved_path)
    for pattern in SUSPICIOUS_PATTERNS[:7]:  # Only check traversal patterns
        if re.search(pattern, path_str, re.IGNORECASE):
            raise ValidationError("Path contains directory traversal patterns")
    
    # Check against allowed directories if specified
    if allowed_directories:
        is_allowed = False
        for allowed_dir in allowed_directories:
            try:
                resolved_path.relative_to(allowed_dir.resolve())
                is_allowed = True
                break
            except ValueError:
                continue
        
        if not is_allowed:
            raise ValidationError(f"Path is outside allowed directories: {resolved_path}")
    
    return resolved_path


def sanitize_path_input(path_input: str) -> str:
    """
    Sanitize and validate path input from users.
    
    Args:
        path_input: Raw path input from user
        
    Returns:
        Cleaned path string
        
    Raises:
        ValidationError: If path is invalid or suspicious
    """
    if not path_input or not path_input.strip():
        raise ValidationError("Path cannot be empty")
    
    # Remove surrounding quotes and whitespace
    cleaned = path_input.strip().strip('"\'')
    
    if not cleaned:
        raise ValidationError("Path cannot be empty after cleaning")
    
    # Check for suspicious patterns
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, cleaned, re.IGNORECASE):
            raise ValidationError(f"Path contains invalid characters or patterns")
    
    # Check length limits
    if len(cleaned) > MAX_PATH_LENGTH:
        raise ValidationError(f"Path too long (max {MAX_PATH_LENGTH} characters)")
    
    return cleaned


def validate_audio_path(path: Union[str, Path]) -> Path:
    """
    Validate audio file or directory path.
    
    Args:
        path: Path to validate
        
    Returns:
        Validated Path object
        
    Raises:
        ValidationError: If path is invalid
        FileNotFoundError: If path doesn't exist
    """
    path = validate_safe_path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")
    
    if path.is_file():
        # Validate as audio file
        if path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
            raise ValidationError(f"Unsupported audio format: {path.suffix}")
        
        # Check file is readable
        if not os.access(path, os.R_OK):
            raise ValidationError(f"File is not readable: {path}")
    
    elif path.is_dir():
        # Check directory is readable
        if not os.access(path, os.R_OK):
            raise ValidationError(f"Directory is not readable: {path}")
        
        # Check if directory contains any audio files
        audio_files = [f for f in path.iterdir() 
                      if f.is_file() and f.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS]
        if not audio_files:
            raise ValidationError(f"No supported audio files found in directory: {path}")
    
    else:
        raise ValidationError(f"Path is neither a file nor directory: {path}")
    
    return path


def validate_output_directory(path: Union[str, Path]) -> Path:
    """
    Validate and create output directory path.
    
    Args:
        path: Output directory path
        
    Returns:
        Validated Path object
        
    Raises:
        ValidationError: If path is invalid
    """
    path = validate_safe_path(path)
    
    # Check parent directory exists and is writable
    parent = path.parent
    if not parent.exists():
        raise ValidationError(f"Parent directory does not exist: {parent}")
    
    if not os.access(parent, os.W_OK):
        raise ValidationError(f"Parent directory is not writable: {parent}")
    
    # Create directory if it doesn't exist
    if not path.exists():
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise ValidationError(f"Cannot create output directory: {e}")
    
    elif not path.is_dir():
        raise ValidationError(f"Output path exists but is not a directory: {path}")
    
    # Check directory is writable
    if not os.access(path, os.W_OK):
        raise ValidationError(f"Output directory is not writable: {path}")
    
    return path


def validate_filename(filename: str) -> str:
    """
    Validate and sanitize filename for output files.
    
    Args:
        filename: Proposed filename
        
    Returns:
        Sanitized filename
        
    Raises:
        ValidationError: If filename is invalid
    """
    if not filename or not filename.strip():
        raise ValidationError("Filename cannot be empty")
    
    cleaned = filename.strip()
    
    # Check length
    if len(cleaned) > MAX_FILENAME_LENGTH:
        raise ValidationError(f"Filename too long (max {MAX_FILENAME_LENGTH} characters)")
    
    # Remove or replace invalid characters
    # Windows invalid chars: < > : " | ? * / \
    invalid_chars = '<>:"|?*/'
    for char in invalid_chars:
        if char in cleaned:
            cleaned = cleaned.replace(char, '_')
    
    # Handle backslashes (Windows path separator)
    cleaned = cleaned.replace('\\', '_')
    
    # Check for Windows reserved names
    name_part = cleaned.split('.')[0].lower()
    reserved_names = {'con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 'com5', 
                     'com6', 'com7', 'com8', 'com9', 'lpt1', 'lpt2', 'lpt3', 'lpt4', 
                     'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9'}
    
    if name_part in reserved_names:
        cleaned = f"_{cleaned}"
    
    # Ensure filename doesn't start or end with dots or spaces
    cleaned = cleaned.strip('. ')
    
    if not cleaned:
        raise ValidationError("Filename becomes empty after sanitization")
    
    return cleaned


def validate_provider_name(provider: str) -> str:
    """
    Validate LLM provider name.
    
    Args:
        provider: Provider name to validate
        
    Returns:
        Validated provider name
        
    Raises:
        ValidationError: If provider is invalid
    """
    if not provider or not provider.strip():
        raise ValidationError("Provider name cannot be empty")
    
    provider = provider.strip().lower()
    
    # Only allow alphanumeric and underscore
    if not re.match(r'^[a-z0-9_]+$', provider):
        raise ValidationError("Provider name can only contain letters, numbers, and underscores")
    
    # Check against known providers
    valid_providers = {'openai', 'anthropic', 'replicate'}
    if provider not in valid_providers:
        log.warning(f"Unknown provider '{provider}', but allowing for extensibility")
    
    return provider


def validate_positive_number(value: Union[str, int, float], name: str = "value") -> float:
    """
    Validate that a value is a positive number.
    
    Args:
        value: Value to validate
        name: Name of the value for error messages
        
    Returns:
        Validated number as float
        
    Raises:
        ValidationError: If value is not a positive number
    """
    if isinstance(value, str):
        try:
            value = float(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{name} must be a valid number")
    
    if not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must be a number")
    
    if value <= 0:
        raise ValidationError(f"{name} must be positive")
    
    return float(value)


def validate_integer_range(value: Union[str, int], min_val: int, max_val: int, name: str = "value") -> int:
    """
    Validate that a value is an integer within a specified range.
    
    Args:
        value: Value to validate
        min_val: Minimum allowed value (inclusive)
        max_val: Maximum allowed value (inclusive)
        name: Name of the value for error messages
        
    Returns:
        Validated integer
        
    Raises:
        ValidationError: If value is not a valid integer in range
    """
    if isinstance(value, str):
        try:
            value = int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{name} must be a valid integer")
    
    if not isinstance(value, int):
        raise ValidationError(f"{name} must be an integer")
    
    if value < min_val or value > max_val:
        raise ValidationError(f"{name} must be between {min_val} and {max_val}")
    
    return value


def validate_transcript_file(path: Union[str, Path]) -> Path:
    """
    Validate transcript file path and format.
    
    Args:
        path: Path to transcript file
        
    Returns:
        Validated Path object
        
    Raises:
        ValidationError: If path is invalid
        FileNotFoundError: If file doesn't exist
    """
    path = validate_safe_path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"Transcript file does not exist: {path}")
    
    if not path.is_file():
        raise ValidationError(f"Path is not a file: {path}")
    
    # Check file extension
    if path.suffix.lower() != '.json':
        raise ValidationError(f"Transcript file must be JSON format: {path}")
    
    # Check file is readable
    if not os.access(path, os.R_OK):
        raise ValidationError(f"Transcript file is not readable: {path}")
    
    return path


def validate_output_dir(path: Union[str, Path]) -> Path:
    """Alias for validate_output_directory for backward compatibility."""
    return validate_output_directory(path)


def validate_model_name(model: str) -> str:
    """
    Validate model name for LLM providers.
    
    Args:
        model: Model name to validate
        
    Returns:
        Validated model name
        
    Raises:
        ValidationError: If model name is invalid
    """
    if not model or not model.strip():
        raise ValidationError("Model name cannot be empty")
    
    model = model.strip()
    
    # Basic validation for model name format
    # Allow alphanumeric, hyphens, underscores, dots, and slashes for model names like "gpt-3.5-turbo"
    if not re.match(r'^[a-zA-Z0-9._/-]+$', model):
        raise ValidationError("Model name can only contain letters, numbers, dots, hyphens, underscores, and slashes")
    
    if len(model) > 100:
        raise ValidationError("Model name too long (max 100 characters)")
    
    return model


def validate_video_path(path: Union[str, Path]) -> Path:
    """
    Validate video file path.
    
    Args:
        path: Path to validate
        
    Returns:
        Validated Path object
        
    Raises:
        ValidationError: If path is invalid
        FileNotFoundError: If path doesn't exist
    """
    path = validate_safe_path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"Video file does not exist: {path}")
    
    if not path.is_file():
        raise ValidationError(f"Path is not a file: {path}")
    
    # Validate as video file
    if path.suffix.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
        raise ValidationError(f"Unsupported video format: {path.suffix}")
    
    # Check file is readable
    if not os.access(path, os.R_OK):
        raise ValidationError(f"Video file is not readable: {path}")
    
    return path


def validate_transcript_path(path: Union[str, Path]) -> Path:
    """
    Validate transcript file path.
    
    Args:
        path: Path to validate
        
    Returns:
        Validated Path object
        
    Raises:
        ValidationError: If path is invalid
        FileNotFoundError: If path doesn't exist
    """
    path = validate_safe_path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"Transcript file does not exist: {path}")
    
    if not path.is_file():
        raise ValidationError(f"Path is not a file: {path}")
    
    # Check file extension
    if path.suffix.lower() not in SUPPORTED_TRANSCRIPT_EXTENSIONS:
        raise ValidationError(f"Unsupported transcript format: {path.suffix}")
    
    # Check file is readable
    if not os.access(path, os.R_OK):
        raise ValidationError(f"Transcript file is not readable: {path}")
    
    # Additional validation for JSON transcript files
    if path.suffix.lower() == '.json':
        try:
            import json
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Basic structure validation
            if isinstance(data, list):
                # Expect list of transcript segments
                if data and not isinstance(data[0], dict):
                    raise ValidationError("JSON transcript must be a list of objects")
            elif isinstance(data, dict):
                # Could be a wrapped transcript format
                if 'segments' not in data and 'transcript' not in data:
                    log.warning(f"JSON transcript format may be non-standard: {sanitize_path(path)}")
            else:
                raise ValidationError("JSON transcript must be a list or object")
                
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON format in transcript file: {e}")
    
    return path


def detect_file_type(path: Union[str, Path]) -> str:
    """
    Detect the type of file based on its extension.

    Args:
        path: Path to analyze

    Returns:
        File type string: 'video', 'audio', 'transcript', or 'unknown'

    Note:
        Returns string for backward compatibility. Use InputFileType enum
        in new code for type safety.
    """
    if isinstance(path, str):
        path = Path(path)

    extension = path.suffix.lower()

    if extension in SUPPORTED_VIDEO_EXTENSIONS:
        return 'video'
    elif extension in SUPPORTED_AUDIO_EXTENSIONS:
        return 'audio'
    elif extension in SUPPORTED_TRANSCRIPT_EXTENSIONS:
        return 'transcript'
    else:
        return 'unknown'


def detect_file_type_enum(path: Union[str, Path]):
    """
    Detect the type of file and return as InputFileType enum.

    Args:
        path: Path to analyze

    Returns:
        InputFileType enum value
    """
    from ..models import InputFileType

    file_type_str = detect_file_type(path)
    return InputFileType(file_type_str)


def validate_llm_provider(provider: str) -> str:
    """
    Validate LLM provider name against known providers.

    Args:
        provider: Provider name to validate

    Returns:
        Validated provider name (lowercase)

    Raises:
        ValidationError: If provider is not recognized
    """
    if not provider or not provider.strip():
        raise ValidationError("Provider cannot be empty")

    provider = provider.strip().lower()

    if provider not in VALID_PROVIDERS:
        raise ValidationError(
            f"Invalid provider '{provider}'. Must be one of: {', '.join(sorted(VALID_PROVIDERS))}"
        )

    return provider


def validate_summary_template(template: str) -> str:
    """
    Validate summary template name.

    Args:
        template: Template name to validate

    Returns:
        Validated template name (lowercase)

    Raises:
        ValidationError: If template is not recognized
    """
    if not template or not template.strip():
        raise ValidationError("Template cannot be empty")

    template = template.strip().lower()

    if template not in VALID_TEMPLATES:
        raise ValidationError(
            f"Invalid template '{template}'. Must be one of: {', '.join(sorted(VALID_TEMPLATES))}"
        )

    return template


def validate_workflow_input(path: Union[str, Path]) -> tuple[Path, str]:
    """
    Validate input file and determine its type for workflow processing.
    
    Args:
        path: Path to input file
        
    Returns:
        Tuple of (validated_path, file_type)
        
    Raises:
        ValidationError: If file is invalid or unsupported
    """
    path = validate_safe_path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"Input file does not exist: {path}")
    
    if not path.is_file():
        raise ValidationError(f"Input path is not a file: {path}")
    
    file_type = detect_file_type(path)
    
    if file_type == 'unknown':
        raise ValidationError(
            f"Unsupported file format: {path.suffix}. "
            f"Supported formats: {', '.join(SUPPORTED_VIDEO_EXTENSIONS | SUPPORTED_AUDIO_EXTENSIONS | SUPPORTED_TRANSCRIPT_EXTENSIONS)}"
        )
    
    # Validate according to specific type
    if file_type == 'video':
        validate_video_path(path)
    elif file_type == 'audio':
        validate_audio_path(path)
    elif file_type == 'transcript':
        validate_transcript_path(path)
    
    return path, file_type