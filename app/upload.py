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
    if len(data) < 8:
        return None

    if data.startswith(PNG_SIGNATURE):
        return "image/png"

    if data.startswith(JPEG_SOI) and data.endswith(JPEG_EOI):
        return "image/jpeg"

    return None


def secure_save(base_dir: str, filename_hint: str, data: bytes) -> Tuple[bool, str]:
    if len(data) > MAX_UPLOAD_SIZE:
        return False, "file_too_large"

    mime_type = sniff_image_type(data)
    if mime_type not in ALLOWED_TYPES:
        return False, "invalid_file_type"

    try:
        root = Path(base_dir).resolve(strict=True)
    except (OSError, RuntimeError):
        return False, "invalid_base_directory"

    ext = ".png" if mime_type == "image/png" else ".jpg"
    safe_name = f"{uuid.uuid4()}{ext}"
    target_path = (root / safe_name).resolve()

    if not str(target_path).startswith(str(root)):
        return False, "path_traversal_detected"

    try:
        for parent in target_path.parents:
            if parent.is_symlink():
                return False, "symlink_in_path"
            if parent == root:
                break
    except (OSError, PermissionError):
        return False, "path_validation_failed"

    try:
        with open(target_path, "wb") as f:
            f.write(data)
    except (OSError, IOError) as e:
        return False, f"write_failed: {type(e).__name__}"

    return True, str(target_path)
