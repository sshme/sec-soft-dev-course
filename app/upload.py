"""Secure file upload with validation (magic bytes, size, path canonicalization)."""

import uuid
from pathlib import Path
from typing import Tuple

# Security limits
MAX_UPLOAD_SIZE = 5_000_000  # 5 MB
ALLOWED_TYPES = {"image/png", "image/jpeg"}

# Magic bytes signatures
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SOI = b"\xff\xd8"  # Start of Image
JPEG_EOI = b"\xff\xd9"  # End of Image


def sniff_image_type(data: bytes) -> str | None:
    """
    Detect image type by magic bytes.

    Args:
        data: File content as bytes

    Returns:
        MIME type string or None if not recognized
    """
    if len(data) < 8:
        return None

    if data.startswith(PNG_SIGNATURE):
        return "image/png"

    if data.startswith(JPEG_SOI) and data.endswith(JPEG_EOI):
        return "image/jpeg"

    return None


def secure_save(base_dir: str, filename_hint: str, data: bytes) -> Tuple[bool, str]:
    """
    Securely save uploaded file with validation.

    Security checks:
    - Size limit (MAX_UPLOAD_SIZE)
    - Magic bytes validation
    - Path canonicalization (prevent traversal)
    - Symlink prevention
    - UUID-based naming (ignore client filename)

    Args:
        base_dir: Base directory for uploads
        filename_hint: Original filename (unused, for logging only)
        data: File content as bytes

    Returns:
        Tuple of (success: bool, result: str)
        - On success: (True, absolute_path)
        - On failure: (False, error_code)
    """
    # Size check
    if len(data) > MAX_UPLOAD_SIZE:
        return False, "file_too_large"

    # Magic bytes validation
    mime_type = sniff_image_type(data)
    if mime_type not in ALLOWED_TYPES:
        return False, "invalid_file_type"

    # Prepare paths
    try:
        root = Path(base_dir).resolve(strict=True)
    except (OSError, RuntimeError):
        return False, "invalid_base_directory"

    # Generate UUID-based filename with correct extension
    ext = ".png" if mime_type == "image/png" else ".jpg"
    safe_name = f"{uuid.uuid4()}{ext}"
    target_path = (root / safe_name).resolve()

    # Path traversal check
    if not str(target_path).startswith(str(root)):
        return False, "path_traversal_detected"

    # Symlink prevention (check all parents)
    try:
        for parent in target_path.parents:
            if parent.is_symlink():
                return False, "symlink_in_path"
            # Stop at root to avoid checking system directories
            if parent == root:
                break
    except (OSError, PermissionError):
        return False, "path_validation_failed"

    # Write file
    try:
        with open(target_path, "wb") as f:
            f.write(data)
    except (OSError, IOError) as e:
        return False, f"write_failed: {type(e).__name__}"

    return True, str(target_path)
