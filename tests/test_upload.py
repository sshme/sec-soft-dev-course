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


def test_secure_save_rejects_large_file(tmp_path: Path):
    """Test rejection of files exceeding size limit"""
    large_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 5_000_001
    ok, reason = secure_save(str(tmp_path), "test.png", large_data)

    assert not ok
    assert reason == "file_too_large"


def test_secure_save_rejects_invalid_type(tmp_path: Path):
    """Test rejection of non-image files"""
    text_data = b"This is a text file, not an image"
    ok, reason = secure_save(str(tmp_path), "test.txt", text_data)

    assert not ok
    assert reason == "invalid_file_type"


def test_secure_save_rejects_wrong_extension(tmp_path: Path):
    """Test magic bytes validation ignores filename extension"""
    ok, path = secure_save(str(tmp_path), "fake.jpg", VALID_PNG)

    assert ok
    assert path.endswith(".png")


def test_secure_save_uses_uuid_naming(tmp_path: Path):
    """Test that uploaded files get UUID-based names"""
    ok, path = secure_save(str(tmp_path), "original_name.png", VALID_PNG)

    assert ok
    filename = Path(path).name

    name_without_ext = filename.replace(".png", "")
    assert len(name_without_ext) == 36
    assert name_without_ext.count("-") == 4


def test_secure_save_prevents_path_traversal(tmp_path: Path):
    """Test prevention of path traversal attacks"""
    ok, path = secure_save(str(tmp_path), "../../etc/passwd", VALID_PNG)

    assert ok
    assert str(tmp_path) in path
    saved_file = Path(path)
    assert saved_file.parent == tmp_path


def test_secure_save_valid_png(tmp_path: Path):
    """Test successful save of valid PNG file"""
    ok, path = secure_save(str(tmp_path), "image.png", VALID_PNG)

    assert ok
    assert Path(path).exists()
    assert path.endswith(".png")

    with open(path, "rb") as f:
        assert f.read() == VALID_PNG


def test_secure_save_valid_jpeg(tmp_path: Path):
    """Test successful save of valid JPEG file"""
    ok, path = secure_save(str(tmp_path), "image.jpg", VALID_JPEG)

    assert ok
    assert Path(path).exists()
    assert path.endswith(".jpg")

    with open(path, "rb") as f:
        assert f.read() == VALID_JPEG


def test_secure_save_invalid_base_directory():
    """Test handling of non-existent base directory"""
    ok, reason = secure_save("/nonexistent/directory", "test.png", VALID_PNG)

    assert not ok
    assert reason == "invalid_base_directory"


def test_secure_save_spoofed_jpeg():
    """Test rejection of JPEG file with invalid end marker"""
    spoofed = b"\xff\xd8" + b"\x00" * 100 + b"\xff\xff"
    mime = sniff_image_type(spoofed)
    assert mime is None


def test_secure_save_multiple_files_unique_names(tmp_path: Path):
    """Test that multiple uploads get unique UUID names"""
    ok1, path1 = secure_save(str(tmp_path), "file.png", VALID_PNG)
    ok2, path2 = secure_save(str(tmp_path), "file.png", VALID_PNG)

    assert ok1 and ok2
    assert path1 != path2
    assert Path(path1).exists()
    assert Path(path2).exists()
