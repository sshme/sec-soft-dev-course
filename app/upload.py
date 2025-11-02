import uuid
from pathlib import Path
from typing import Optional, Tuple

from app.config import config

MAX_UPLOAD_SIZE = 5_000_000
ALLOWED_TYPES = {"image/png", "image/jpeg"}
UPLOAD_TIMEOUT = 30

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SOI = b"\xff\xd8"
JPEG_EOI = b"\xff\xd9"

try:
    import boto3
    from botocore.exceptions import ClientError

    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False


def sniff_image_type(data: bytes) -> str | None:
    if len(data) < 8:
        return None

    if data.startswith(PNG_SIGNATURE):
        return "image/png"

    if data.startswith(JPEG_SOI) and data.endswith(JPEG_EOI):
        return "image/jpeg"

    return None


def _validate_and_save_temp(
    data: bytes, tmp_dir: str
) -> Tuple[bool, str, Optional[str]]:
    if len(data) > MAX_UPLOAD_SIZE:
        return False, "file_too_large", None

    mime_type = sniff_image_type(data)
    if mime_type not in ALLOWED_TYPES:
        return False, "invalid_file_type", None

    try:
        root = Path(tmp_dir).resolve(strict=True)
    except (OSError, RuntimeError):
        return False, "invalid_tmp_directory", None

    ext = ".png" if mime_type == "image/png" else ".jpg"
    safe_name = f"{uuid.uuid4()}{ext}"
    target_path = (root / safe_name).resolve()

    if not str(target_path).startswith(str(root)):
        return False, "path_traversal_detected", None

    try:
        for parent in target_path.parents:
            if parent.is_symlink():
                return False, "symlink_in_path", None
            if parent == root:
                break
    except (OSError, PermissionError):
        return False, "path_validation_failed", None

    try:
        with open(target_path, "wb") as f:
            f.write(data)
    except (OSError, IOError) as e:
        return False, f"write_failed: {type(e).__name__}", None

    return True, str(target_path), mime_type


def _upload_to_s3(file_path: str, mime_type: str) -> Tuple[bool, str]:
    if not S3_AVAILABLE:
        return False, "s3_not_available"

    if not config.s3_bucket:
        return False, "s3_not_configured"

    try:
        s3_client = boto3.client(
            "s3",
            endpoint_url=config.s3_endpoint,
            aws_access_key_id=config.s3_access_key,
            aws_secret_access_key=config.s3_secret_key,
        )

        key = f"{uuid.uuid4()}{Path(file_path).suffix}"

        with open(file_path, "rb") as f:
            s3_client.put_object(
                Bucket=config.s3_bucket,
                Key=key,
                Body=f,
                ContentType=mime_type,
                ServerSideEncryption="AES256",
            )

        return True, f"s3://{config.s3_bucket}/{key}"
    except ClientError as e:
        return False, f"s3_upload_failed: {e}"
    except Exception as e:
        return False, f"upload_error: {type(e).__name__}"


def secure_save(data: bytes, use_s3: bool = True) -> Tuple[bool, str]:
    tmp_dir = config.tmp_dir

    success, result, mime_type = _validate_and_save_temp(data, tmp_dir)
    if not success:
        return False, result

    temp_file_path = result

    if use_s3 and S3_AVAILABLE and config.s3_bucket:
        s3_success, s3_result = _upload_to_s3(temp_file_path, mime_type)

        try:
            Path(temp_file_path).unlink()
        except Exception:
            pass

        if not s3_success:
            return False, s3_result

        return True, s3_result
    else:
        return True, temp_file_path
