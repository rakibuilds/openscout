
"""Tests for local image processing."""

import pytest
from PIL import Image

from openscout.core.exceptions import MediaProcessingError
from openscout.media.image.processor import (
    compress_image,
    convert_image,
    create_thumbnail,
    crop_image,
    inspect_image,
    resize_image,
    strip_image_metadata,
)


@pytest.fixture
def sample_image(tmp_path):
    """Create a test image."""
    path = tmp_path / "sample.png"
    image = Image.new("RGB", (800, 600), "red")
    image.save(path)
    return path


def test_inspect_image(sample_image):
    info = inspect_image(sample_image)

    assert info.filename == "sample.png"
    assert info.format == "PNG"
    assert info.width == 800
    assert info.height == 600
    assert info.mode == "RGB"
    assert info.file_size > 0


def test_convert_image(sample_image, tmp_path):
    result = convert_image(sample_image, "webp")

    output = tmp_path / "sample-converted.webp"

    assert result.operation == "convert"
    assert output.exists()

    with Image.open(output) as image:
        assert image.format == "WEBP"
        assert image.size == (800, 600)


def test_convert_image_custom_output(sample_image, tmp_path):
    output = tmp_path / "converted.webp"

    result = convert_image(sample_image, "webp", output)

    assert result.output_path == str(output.resolve())
    assert output.exists()


def test_convert_rejects_mismatched_extension(sample_image, tmp_path):
    output = tmp_path / "wrong.png"

    with pytest.raises(MediaProcessingError, match="does not match"):
        convert_image(sample_image, "webp", output)


def test_compress_image(sample_image):
    result = compress_image(sample_image)

    assert result.operation == "compress"
    assert (sample_image.parent / "sample-compressed.png").exists()


def test_resize_preserves_aspect_ratio(sample_image):
    result = resize_image(sample_image, width=400)

    with Image.open(result.output_path) as image:
        assert image.size == (400, 300)


def test_resize_with_both_dimensions(sample_image):
    result = resize_image(sample_image, width=400, height=400)

    with Image.open(result.output_path) as image:
        assert image.size == (400, 300)


def test_resize_requires_dimensions(sample_image):
    with pytest.raises(MediaProcessingError, match="at least a width or height"):
        resize_image(sample_image)


def test_crop_image(sample_image):
    result = crop_image(
        sample_image,
        x=100,
        y=50,
        width=300,
        height=200,
    )

    with Image.open(result.output_path) as image:
        assert image.size == (300, 200)


def test_crop_rejects_out_of_bounds(sample_image):
    with pytest.raises(MediaProcessingError, match="boundaries"):
        crop_image(
            sample_image,
            x=700,
            y=500,
            width=200,
            height=200,
        )


def test_create_thumbnail(sample_image):
    result = create_thumbnail(sample_image, size=128)

    with Image.open(result.output_path) as image:
        assert image.width <= 128
        assert image.height <= 128


def test_strip_metadata(sample_image):
    result = strip_image_metadata(sample_image)

    with Image.open(result.output_path) as image:
        assert not image.getexif()


def test_rejects_missing_file(tmp_path):
    with pytest.raises(MediaProcessingError, match="does not exist"):
        inspect_image(tmp_path / "missing.png")


def test_rejects_existing_output(sample_image):
    output = sample_image.parent / "sample-compressed.png"
    output.write_bytes(b"existing")

    with pytest.raises(MediaProcessingError, match="already exists"):
        compress_image(sample_image)


def test_never_overwrites_input(sample_image):
    with pytest.raises(MediaProcessingError, match="different from the input"):
        convert_image(sample_image, "png", sample_image)


def test_rejects_unsupported_format(sample_image):
    with pytest.raises(MediaProcessingError, match="Unsupported image format"):
        convert_image(sample_image, "unsupported")
