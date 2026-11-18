
"""OpenScout media processing commands."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

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

app = typer.Typer(
    name="media",
    help="Inspect and process local media files.",
    no_args_is_help=True,
)

image_app = typer.Typer(
    name="image",
    help="Inspect and process images.",
    no_args_is_help=True,
)

app.add_typer(image_app, name="image")

console = Console()


def _run_operation(operation) -> None:
    """Run an image operation and display its result."""
    try:
        result = operation()
    except MediaProcessingError as exc:
        console.print(f"[red]Image processing error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    table = Table(title="Image processing complete")
    table.add_column("Property", style="cyan")
    table.add_column("Value")

    table.add_row("Operation", result.operation)
    table.add_row("Input", result.input_path)
    table.add_row("Output", result.output_path)
    table.add_row("Original size", f"{result.input_size:,} bytes")
    table.add_row("Output size", f"{result.output_size:,} bytes")
    table.add_row("Bytes saved", f"{result.bytes_saved:,}")
    table.add_row("Size reduction", f"{result.reduction_percent:.2f}%")

    console.print(table)


@image_app.command("inspect")
def image_inspect(
    path: Path = typer.Argument(..., help="Path to the image file."),
) -> None:
    """Inspect image properties and metadata."""
    try:
        info = inspect_image(path)
    except MediaProcessingError as exc:
        console.print(f"[red]Image inspection error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    table = Table(title="Image information")
    table.add_column("Property", style="cyan")
    table.add_column("Value")

    table.add_row("Filename", info.filename)
    table.add_row("Path", info.path)
    table.add_row("Format", info.format)
    table.add_row("Dimensions", f"{info.width} × {info.height}")
    table.add_row("Color mode", info.mode)
    table.add_row("File size", f"{info.file_size:,} bytes")
    table.add_row("Transparency", "Yes" if info.has_transparency else "No")
    table.add_row("Frames", str(info.frame_count))

    console.print(table)


@image_app.command("convert")
def image_convert(
    path: Path = typer.Argument(..., help="Path to the source image."),
    output_format: str = typer.Option(
        ...,
        "--format",
        "-f",
        help="Target format: jpeg, png, webp, bmp, tiff, or gif.",
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output file path."
    ),
    quality: int = typer.Option(
        85, "--quality", min=1, max=100, help="Output quality (1-100)."
    ),
    preserve_metadata: bool = typer.Option(
        False, "--preserve-metadata", help="Preserve EXIF metadata when possible."
    ),
) -> None:
    """Convert an image to another format."""
    _run_operation(
        lambda: convert_image(
            path, output_format, output, quality, preserve_metadata
        )
    )


@image_app.command("compress")
def image_compress(
    path: Path = typer.Argument(..., help="Path to the source image."),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output file path."
    ),
    quality: int = typer.Option(
        80, "--quality", min=1, max=100, help="Compression quality (1-100)."
    ),
    preserve_metadata: bool = typer.Option(
        False, "--preserve-metadata", help="Preserve EXIF metadata when possible."
    ),
) -> None:
    """Compress a JPEG, PNG, or WebP image."""
    _run_operation(
        lambda: compress_image(
            path, output, quality, preserve_metadata
        )
    )


@image_app.command("resize")
def image_resize(
    path: Path = typer.Argument(..., help="Path to the source image."),
    width: int | None = typer.Option(
        None, "--width", "-w", min=1, help="Target width in pixels."
    ),
    height: int | None = typer.Option(
        None, "--height", min=1, help="Target height in pixels."
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output file path."
    ),
    preserve_metadata: bool = typer.Option(
        False, "--preserve-metadata", help="Preserve EXIF metadata when possible."
    ),
) -> None:
    """Resize an image while preserving its aspect ratio."""
    _run_operation(
        lambda: resize_image(
            path, width, height, output, preserve_metadata
        )
    )


@image_app.command("crop")
def image_crop(
    path: Path = typer.Argument(..., help="Path to the source image."),
    x: int = typer.Option(..., "--x", min=0, help="Left crop coordinate."),
    y: int = typer.Option(..., "--y", min=0, help="Top crop coordinate."),
    width: int = typer.Option(..., "--width", min=1, help="Crop width."),
    height: int = typer.Option(..., "--height", min=1, help="Crop height."),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output file path."
    ),
    preserve_metadata: bool = typer.Option(
        False, "--preserve-metadata", help="Preserve EXIF metadata when possible."
    ),
) -> None:
    """Crop an image using pixel coordinates."""
    _run_operation(
        lambda: crop_image(
            path, x, y, width, height, output, preserve_metadata
        )
    )


@image_app.command("thumbnail")
def image_thumbnail(
    path: Path = typer.Argument(..., help="Path to the source image."),
    size: int = typer.Option(
        256, "--size", "-s", min=1, help="Maximum thumbnail dimension."
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output file path."
    ),
) -> None:
    """Create a thumbnail while preserving the image aspect ratio."""
    _run_operation(lambda: create_thumbnail(path, size, output))


@image_app.command("strip-metadata")
def image_strip_metadata(
    path: Path = typer.Argument(..., help="Path to the source image."),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output file path."
    ),
) -> None:
    """Create a copy of an image without EXIF metadata."""
    _run_operation(lambda: strip_image_metadata(path, output))
