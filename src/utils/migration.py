"""Data structure migration utilities.

Migrates from legacy (input/, out/) to new (data/video, data/audio, etc.) structure.
"""
import logging
import shutil
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

log = logging.getLogger(__name__)

# File extension mappings
VIDEO_EXTENSIONS: Set[str] = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
AUDIO_EXTENSIONS: Set[str] = {'.m4a', '.mp3', '.wav', '.flac', '.ogg', '.mka', '.aac'}
TRANSCRIPT_EXTENSIONS: Set[str] = {'.json', '.txt', '.srt'}


class MigrationResult:
    """Results from a migration operation."""

    def __init__(self):
        self.migrated: List[Dict[str, str]] = []
        self.skipped: List[Dict[str, str]] = []
        self.errors: List[Dict[str, str]] = []

    @property
    def success_count(self) -> int:
        return len(self.migrated)

    @property
    def skip_count(self) -> int:
        return len(self.skipped)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    def to_dict(self) -> Dict:
        return {
            "migrated": self.migrated,
            "skipped": self.skipped,
            "errors": self.errors,
            "summary": {
                "migrated_count": self.success_count,
                "skipped_count": self.skip_count,
                "error_count": self.error_count
            }
        }


def detect_file_category(file_path: Path) -> str:
    """Determine file category based on extension.

    Args:
        file_path: Path to file

    Returns:
        Category: 'video', 'audio', 'transcript', or 'unknown'
    """
    ext = file_path.suffix.lower()

    if ext in VIDEO_EXTENSIONS:
        return 'video'
    elif ext in AUDIO_EXTENSIONS:
        return 'audio'
    elif ext in TRANSCRIPT_EXTENSIONS:
        return 'transcript'
    else:
        return 'unknown'


def check_legacy_directories(
    legacy_input: Path = None,
    legacy_output: Path = None
) -> Dict[str, bool]:
    """Check for presence of legacy directories.

    Args:
        legacy_input: Path to legacy input directory (default: ./input)
        legacy_output: Path to legacy output directory (default: ./out)

    Returns:
        Dict with 'input_exists' and 'output_exists' booleans
    """
    legacy_input = legacy_input or Path("input")
    legacy_output = legacy_output or Path("out")

    return {
        "input_exists": legacy_input.exists() and any(legacy_input.iterdir()) if legacy_input.exists() else False,
        "output_exists": legacy_output.exists() and any(legacy_output.iterdir()) if legacy_output.exists() else False,
        "input_path": str(legacy_input),
        "output_path": str(legacy_output)
    }


def warn_legacy_directories():
    """Issue deprecation warnings if legacy directories are detected."""
    status = check_legacy_directories()

    if status["input_exists"]:
        warnings.warn(
            f"Legacy directory 'input' detected with files. "
            "Run 'summeets migrate-data' to migrate to new structure.",
            DeprecationWarning,
            stacklevel=2
        )

    if status["output_exists"]:
        warnings.warn(
            f"Legacy directory 'out' detected with files. "
            "Run 'summeets migrate-data' to migrate to new structure.",
            DeprecationWarning,
            stacklevel=2
        )


def migrate_file(
    source: Path,
    target_dir: Path,
    dry_run: bool = False,
    move: bool = False
) -> Dict[str, str]:
    """Migrate a single file to new structure.

    Args:
        source: Source file path
        target_dir: Target directory
        dry_run: If True, don't actually move/copy files
        move: If True, move instead of copy

    Returns:
        Dict with 'source', 'target', 'action' keys
    """
    target = target_dir / source.name

    # Handle name conflicts
    if target.exists():
        stem = source.stem
        suffix = source.suffix
        counter = 1
        while target.exists():
            target = target_dir / f"{stem}_{counter}{suffix}"
            counter += 1

    result = {
        "source": str(source),
        "target": str(target),
        "action": "would_move" if move else "would_copy"
    }

    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)
        if move:
            shutil.move(source, target)
            result["action"] = "moved"
        else:
            shutil.copy2(source, target)
            result["action"] = "copied"

    return result


def migrate_to_new_structure(
    legacy_input: Path = None,
    legacy_output: Path = None,
    new_base: Path = None,
    dry_run: bool = False,
    move: bool = False,
    create_backup: bool = True
) -> MigrationResult:
    """Migrate from legacy to new data structure.

    Args:
        legacy_input: Legacy input directory (default: ./input)
        legacy_output: Legacy output directory (default: ./out)
        new_base: New base directory (default: ./data)
        dry_run: If True, don't actually move/copy files
        move: If True, move files instead of copying
        create_backup: If True, create backup before migration

    Returns:
        MigrationResult with details of migrated, skipped, and failed files
    """
    legacy_input = legacy_input or Path("input")
    legacy_output = legacy_output or Path("out")
    new_base = new_base or Path("data")

    result = MigrationResult()

    # Create backup if requested
    if create_backup and not dry_run:
        backup_dir = new_base / "migration_backup" / datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir.mkdir(parents=True, exist_ok=True)
        log.info(f"Created backup directory: {backup_dir}")

    # Migrate input files
    if legacy_input.exists():
        for file in legacy_input.rglob("*"):
            if not file.is_file():
                continue

            category = detect_file_category(file)

            if category == 'unknown':
                result.skipped.append({
                    "file": str(file),
                    "reason": f"Unknown file extension: {file.suffix}"
                })
                continue

            # Determine target directory
            if category == 'video':
                target_dir = new_base / "video"
            elif category == 'audio':
                # Audio goes into subdirectory named after file stem
                target_dir = new_base / "audio" / file.stem
            else:  # transcript
                target_dir = new_base / "transcript" / file.stem

            try:
                migration_info = migrate_file(file, target_dir, dry_run, move)
                result.migrated.append(migration_info)
                log.info(f"Migrated: {file} -> {migration_info['target']}")
            except Exception as e:
                result.errors.append({
                    "file": str(file),
                    "error": str(e)
                })
                log.error(f"Failed to migrate {file}: {e}")

    # Migrate output files
    if legacy_output.exists():
        for file in legacy_output.rglob("*"):
            if not file.is_file():
                continue

            category = detect_file_category(file)

            # Determine target based on file patterns
            if category == 'transcript' or file.suffix.lower() in {'.json', '.srt'}:
                # Likely transcript output
                base_name = file.stem.replace('.summary', '').replace('.transcript', '')
                target_dir = new_base / "transcript" / base_name
            elif '.summary' in file.name.lower() or '.md' == file.suffix.lower():
                # Summary output
                base_name = file.stem.replace('.summary', '')
                target_dir = new_base / "summary" / base_name / "default"
            elif category in ('video', 'audio'):
                target_dir = new_base / category / file.stem
            else:
                result.skipped.append({
                    "file": str(file),
                    "reason": f"Unknown output type: {file.suffix}"
                })
                continue

            try:
                migration_info = migrate_file(file, target_dir, dry_run, move)
                result.migrated.append(migration_info)
                log.info(f"Migrated: {file} -> {migration_info['target']}")
            except Exception as e:
                result.errors.append({
                    "file": str(file),
                    "error": str(e)
                })
                log.error(f"Failed to migrate {file}: {e}")

    # Log summary
    log.info(
        f"Migration complete: {result.success_count} migrated, "
        f"{result.skip_count} skipped, {result.error_count} errors"
    )

    return result


def cleanup_legacy_directories(
    legacy_input: Path = None,
    legacy_output: Path = None,
    dry_run: bool = False
) -> Dict[str, bool]:
    """Remove empty legacy directories after migration.

    Args:
        legacy_input: Legacy input directory
        legacy_output: Legacy output directory
        dry_run: If True, don't actually remove directories

    Returns:
        Dict with cleanup status for each directory
    """
    legacy_input = legacy_input or Path("input")
    legacy_output = legacy_output or Path("out")

    result = {
        "input_removed": False,
        "output_removed": False
    }

    for name, path in [("input", legacy_input), ("output", legacy_output)]:
        if path.exists():
            # Check if empty
            if not any(path.iterdir()):
                if not dry_run:
                    try:
                        path.rmdir()
                        result[f"{name}_removed"] = True
                        log.info(f"Removed empty legacy directory: {path}")
                    except Exception as e:
                        log.warning(f"Failed to remove {path}: {e}")
                else:
                    result[f"{name}_removed"] = True  # Would remove
            else:
                log.warning(f"Legacy directory not empty, skipping: {path}")

    return result
