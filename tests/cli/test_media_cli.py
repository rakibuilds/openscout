
"""Tests for OpenScout media CLI commands."""

from PIL import Image
from typer.testing import CliRunner

from openscout.cli.app import app

runner = CliRunner()


def test_media_help():
    result = runner.invoke(app, ["media", "--help"])

    assert result.exit_code == 0
    assert "image" in result.stdout


def test_image_help():
    result = runner.invoke(app, ["media", "image", "--help"])

    assert result.exit_code == 0
    assert "inspect" in result.stdout
    assert "convert" in result.stdout
    assert "compress" in result.stdout
    assert "resize" in result.stdout
    assert "crop" in result.stdout
    assert "thumbnail" in result.stdout


def test_image_inspect(tmp_path):
    path = tmp_path / "sample.png"
    Image.new("RGB", (320, 240), "blue").save(path)

    result = runner.invoke(
        app,
        ["media", "image", "inspect", str(path)],
    )

    assert result.exit_code == 0
    assert "320 × 240" in result.stdout
    assert "PNG" in result.stdout


def test_image_convert(tmp_path):
    path = tmp_path / "sample.png"
    Image.new("RGB", (320, 240), "blue").save(path)

    result = runner.invoke(
        app,
        [
            "media", "image", "convert", str(path),
            "--format", "webp",
        ],
    )

    assert result.exit_code == 0
    assert (tmp_path / "sample-converted.webp").exists()


def test_image_resize(tmp_path):
    path = tmp_path / "sample.png"
    Image.new("RGB", (800, 600), "blue").save(path)

    result = runner.invoke(
        app,
        [
            "media", "image", "resize", str(path),
            "--width", "400",
        ],
    )

    assert result.exit_code == 0

    with Image.open(tmp_path / "sample-resized.png") as image:
        assert image.size == (400, 300)


def test_image_missing_file():
    result = runner.invoke(
        app,
        ["media", "image", "inspect", "missing-image.png"],
    )

    assert result.exit_code == 2
    assert "does not exist" in result.stdout
