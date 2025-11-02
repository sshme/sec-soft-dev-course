"""Tests for secure file upload validation."""

from pathlib import Path

from app.upload import secure_save, sniff_image_type

VALID_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
VALID_JPEG = b"\xff\xd8" + b"\x00" * 100 + b"\xff\xd9"


def test_sniff_image_type_png():
    """Test PNG magic bytes detection"""
    mime = sniff_image_type(VALID_PNG)
    assert mime == "image/png"


def test_sniff_image_type_jpeg():
    """Test JPEG magic bytes detection"""
    mime = sniff_image_type(VALID_JPEG)
    assert mime == "image/jpeg"


def test_sniff_image_type_invalid():
    """Test rejection of invalid file types"""
    invalid_data = b"This is not an image file"
    mime = sniff_image_type(invalid_data)
    assert mime is None


def test_sniff_image_type_too_short():
    """Test rejection of files with insufficient data"""
    short_data = b"\x89PNG"
    mime = sniff_image_type(short_data)
    assert mime is None


def test_secure_save_rejects_large_file(tmp_path: Path, monkeypatch):
    large_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 5_000_001
    monkeypatch.setenv("TMP_DIR", str(tmp_path))
    from app.config import config

    config.tmp_dir = str(tmp_path)
    ok, reason = secure_save(large_data, use_s3=False)

    assert not ok
    assert reason == "file_too_large"


def test_secure_save_rejects_invalid_type(tmp_path: Path, monkeypatch):
    text_data = b"This is a text file, not an image"
    monkeypatch.setenv("TMP_DIR", str(tmp_path))
    from app.config import config

    config.tmp_dir = str(tmp_path)
    ok, reason = secure_save(text_data, use_s3=False)

    assert not ok
    assert reason == "invalid_file_type"


def test_secure_save_rejects_wrong_extension(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TMP_DIR", str(tmp_path))
    from app.config import config

    config.tmp_dir = str(tmp_path)
    ok, path = secure_save(VALID_PNG, use_s3=False)

    assert ok
    assert path.endswith(".png")


def test_secure_save_uses_uuid_naming(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TMP_DIR", str(tmp_path))
    from app.config import config

    config.tmp_dir = str(tmp_path)
    ok, path = secure_save(VALID_PNG, use_s3=False)

    assert ok
    filename = Path(path).name

    name_without_ext = filename.replace(".png", "")
    assert len(name_without_ext) == 36
    assert name_without_ext.count("-") == 4


def test_secure_save_prevents_path_traversal(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TMP_DIR", str(tmp_path))
    from app.config import config

    config.tmp_dir = str(tmp_path)
    ok, path = secure_save(VALID_PNG, use_s3=False)

    assert ok
    assert str(tmp_path) in path
    saved_file = Path(path)
    assert saved_file.parent == tmp_path


def test_secure_save_valid_png(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TMP_DIR", str(tmp_path))
    from app.config import config

    config.tmp_dir = str(tmp_path)
    ok, path = secure_save(VALID_PNG, use_s3=False)

    assert ok
    assert Path(path).exists()
    assert path.endswith(".png")

    with open(path, "rb") as f:
        assert f.read() == VALID_PNG


def test_secure_save_valid_jpeg(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TMP_DIR", str(tmp_path))
    from app.config import config

    config.tmp_dir = str(tmp_path)
    ok, path = secure_save(VALID_JPEG, use_s3=False)

    assert ok
    assert Path(path).exists()
    assert path.endswith(".jpg")

    with open(path, "rb") as f:
        assert f.read() == VALID_JPEG


def test_secure_save_invalid_base_directory(monkeypatch):
    monkeypatch.setenv("TMP_DIR", "/nonexistent/directory")
    from app.config import config

    config.tmp_dir = "/nonexistent/directory"
    ok, reason = secure_save(VALID_PNG, use_s3=False)

    assert not ok
    assert reason == "invalid_tmp_directory"


def test_secure_save_spoofed_jpeg():
    """Test rejection of JPEG file with invalid end marker"""
    spoofed = b"\xff\xd8" + b"\x00" * 100 + b"\xff\xff"
    mime = sniff_image_type(spoofed)
    assert mime is None


def test_secure_save_multiple_files_unique_names(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TMP_DIR", str(tmp_path))
    from app.config import config

    config.tmp_dir = str(tmp_path)
    ok1, path1 = secure_save(VALID_PNG, use_s3=False)
    ok2, path2 = secure_save(VALID_PNG, use_s3=False)

    assert ok1 and ok2
    assert path1 != path2
    assert Path(path1).exists()
    assert Path(path2).exists()
