
"""Tests for local image processing."""

import pytest
from PIL import Image, ImageCms

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
    image.close()
    return path


def test_inspect_image(sample_image):
    info = inspect_image(sample_image)

    assert info.filename == "sample.png"
    assert info.format == "PNG"
    assert info.width == 800
    assert info.height == 600
    assert info.mode == "RGB"
    assert info.file_size > 0
    assert info.frame_count == 1


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


def test_thumbnail_does_not_modify_source(sample_image):
    original_size = sample_image.stat().st_size

    result = create_thumbnail(sample_image, size=128)

    assert sample_image.exists()
    assert sample_image.stat().st_size == original_size
    assert result.input_path == str(sample_image.resolve())


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


def test_resize_applies_exif_orientation(tmp_path):
    """Resize should use the visually oriented dimensions."""
    path = tmp_path / "oriented.jpg"

    image = Image.new("RGB", (400, 300), "red")
    try:
        exif = image.getexif()
        exif[274] = 6
        image.save(path, exif=exif)
    finally:
        image.close()

    result = resize_image(path, width=150)

    with Image.open(result.output_path) as output:
        assert output.size == (150, 200)


def test_convert_rejects_animated_gif(tmp_path):
    """Animated input must not silently lose its additional frames."""
    path = tmp_path / "animated.gif"

    first = Image.new("RGB", (100, 100), "red")
    second = Image.new("RGB", (100, 100), "blue")

    try:
        first.save(
            path,
            save_all=True,
            append_images=[second],
            duration=100,
            loop=0,
        )
    finally:
        first.close()
        second.close()

    with pytest.raises(MediaProcessingError, match="Animated images"):
        convert_image(path, "png")


def test_resize_closes_image_when_output_validation_fails(
    sample_image,
    monkeypatch,
):
    """The opened image must be closed if output preparation fails."""
    from openscout.media.image import processor

    opened_images = []
    close_calls = []
    original_open_image = processor._open_image

    def tracked_open_image(path):
        image = original_open_image(path)
        original_close = image.close

        def tracked_close():
            close_calls.append(True)
            original_close()

        monkeypatch.setattr(image, "close", tracked_close)
        opened_images.append(image)
        return image

    def fail_prepare_output(*args, **kwargs):
        raise MediaProcessingError("Simulated output validation failure")

    monkeypatch.setattr(processor, "_open_image", tracked_open_image)
    monkeypatch.setattr(processor, "_prepare_output", fail_prepare_output)

    with pytest.raises(MediaProcessingError, match="Simulated"):
        resize_image(sample_image, width=400)

    assert len(opened_images) == 1
    assert close_calls == [True]



def test_resize_preserves_transparency(tmp_path):
    """Resizing a PNG should preserve transparent and opaque regions."""
    path = tmp_path / "transparent.png"

    image = Image.new("RGBA", (200, 100), (255, 0, 0, 0))
    try:
        image.paste(
            (255, 0, 0, 255),
            (40, 20, 120, 80),
        )
        image.save(path)
    finally:
        image.close()

    result = resize_image(path, width=100)

    with Image.open(result.output_path) as output:
        assert output.mode == "RGBA"
        assert output.size == (100, 50)

        # Sample well inside the opaque region.
        assert output.getpixel((40, 25))[3] == 255

        # Sample outside the opaque region.
        assert output.getpixel((5, 5))[3] == 0


def test_convert_preserves_icc_profile_when_requested(tmp_path):
    """Conversion should retain the ICC profile when requested."""
    path = tmp_path / "profiled.png"
    output = tmp_path / "profiled-converted.png"

    profile = ImageCms.ImageCmsProfile(
        ImageCms.createProfile("sRGB")
    ).tobytes()

    image = Image.new("RGB", (100, 100), "red")
    try:
        image.save(path, icc_profile=profile)
    finally:
        image.close()

    convert_image(
        path,
        "png",
        output,
        preserve_metadata=True,
    )

    with Image.open(output) as result:
        assert result.info.get("icc_profile") == profile


def test_convert_does_not_preserve_icc_profile_by_default(tmp_path):
    """Conversion should not retain the ICC profile by default."""
    path = tmp_path / "profiled.png"
    output = tmp_path / "converted.png"

    profile = ImageCms.ImageCmsProfile(
        ImageCms.createProfile("sRGB")
    ).tobytes()

    image = Image.new("RGB", (100, 100), "red")
    try:
        image.save(path, icc_profile=profile)
    finally:
        image.close()

    convert_image(path, "png", output)

    with Image.open(output) as result:
        assert result.info.get("icc_profile") is None


def test_strip_metadata_removes_exif_and_icc(tmp_path):
    """Metadata stripping should remove both EXIF and ICC data."""
    path = tmp_path / "profiled.png"

    profile = ImageCms.ImageCmsProfile(
        ImageCms.createProfile("sRGB")
    ).tobytes()

    image = Image.new("RGB", (100, 100), "red")
    try:
        exif = image.getexif()
        exif[270] = "OpenScout metadata test"

        image.save(
            path,
            exif=exif.tobytes(),
            icc_profile=profile,
        )
    finally:
        image.close()

    result = strip_image_metadata(path)

    with Image.open(result.output_path) as output:
        assert not output.getexif()
        assert output.info.get("icc_profile") is None


def test_convert_transparent_png_to_jpeg_uses_white_background(tmp_path):
    """Transparent pixels should become white when converting to JPEG."""
    path = tmp_path / "transparent.png"
    output = tmp_path / "transparent.jpg"

    image = Image.new("RGBA", (100, 100), (255, 0, 0, 0))
    try:
        image.paste(
            (255, 0, 0, 255),
            (40, 40, 60, 60),
        )
        image.save(path)
    finally:
        image.close()

    convert_image(path, "jpeg", output, quality=100)

    with Image.open(output) as result:
        assert result.mode == "RGB"

        red, green, blue = result.getpixel((5, 5))
        assert red > 245
        assert green > 245
        assert blue > 245


def test_failed_save_removes_temporary_file(
    sample_image,
    tmp_path,
    monkeypatch,
):
    """A failed save should not leave temporary output files."""
    output = tmp_path / "converted.webp"

    def fail_save(self, *args, **kwargs):
        raise OSError("Simulated disk write failure")

    monkeypatch.setattr(Image.Image, "save", fail_save)

    with pytest.raises(MediaProcessingError, match="Unable to save image"):
        convert_image(sample_image, "webp", output)

    assert not output.exists()
    assert not list(tmp_path.glob(".converted-*"))
