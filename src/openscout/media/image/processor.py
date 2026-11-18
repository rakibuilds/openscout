
"""Local image inspection and processing operations."""

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from openscout.core.exceptions import MediaProcessingError

SUPPORTED_FORMATS = {
    "jpeg": "JPEG",
    "jpg": "JPEG",
    "png": "PNG",
    "webp": "WEBP",
    "bmp": "BMP",
    "tiff": "TIFF",
    "tif": "TIFF",
    "gif": "GIF",
}

FORMAT_EXTENSIONS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
    "BMP": ".bmp",
    "TIFF": ".tiff",
    "GIF": ".gif",
}


@dataclass(slots=True)
class ImageInfo:
    """Metadata describing an image file."""

    path: str
    filename: str
    format: str
    mode: str
    width: int
    height: int
    file_size: int
    has_transparency: bool
    frame_count: int


@dataclass(slots=True)
class ImageOperationResult:
    """Result of a completed image operation."""

    input_path: str
    output_path: str
    operation: str
    input_size: int
    output_size: int

    @property
    def bytes_saved(self) -> int:
        return self.input_size - self.output_size

    @property
    def reduction_percent(self) -> float:
        if self.input_size == 0:
            return 0.0
        return (self.bytes_saved / self.input_size) * 100


def _validate_input(path: Path) -> Path:
    """Validate an input image path."""
    path = path.expanduser()

    if not path.exists():
        raise MediaProcessingError(f"Input file does not exist: {path}")

    if not path.is_file():
        raise MediaProcessingError(f"Input path is not a file: {path}")

    return path.resolve()


def _open_image(path: Path) -> Image.Image:
    """Open and fully load an image."""
    try:
        with Image.open(path) as source:
            source.load()
            return source.copy()
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
    ) as exc:
        raise MediaProcessingError(
            f"Unable to read image '{path}': {exc}"
        ) from exc


def _resolve_format(value: str) -> str:
    """Resolve a user-facing format name to a Pillow format."""
    normalized = value.strip().lower()

    if normalized not in SUPPORTED_FORMATS:
        supported = ", ".join(sorted(SUPPORTED_FORMATS))
        raise MediaProcessingError(
            f"Unsupported image format '{value}'. Supported formats: {supported}"
        )

    return SUPPORTED_FORMATS[normalized]



def _prepare_output(
    source: Path,
    output: Path | None,
    suffix: str,
    output_format: str | None = None,
) -> tuple[Path, str]:
    """Resolve an output path without silently overwriting files."""
    image_format = (
        _resolve_format(output_format)
        if output_format
        else _resolve_format(source.suffix.lstrip("."))
    )

    extension = FORMAT_EXTENSIONS[image_format]

    if output is None:
        destination = source.with_name(f"{source.stem}-{suffix}{extension}")
    else:
        destination = output.expanduser()

        if not destination.suffix:
            destination = destination.with_suffix(extension)

    destination = destination.resolve()

    if destination.suffix:
        output_extension = destination.suffix.lstrip(".").lower()
        requested_format = SUPPORTED_FORMATS.get(output_extension)

        if requested_format is None:
            raise MediaProcessingError(
                f"Unsupported output extension: {destination.suffix}"
            )

        if requested_format != image_format:
            raise MediaProcessingError(
                f"Output extension '{destination.suffix}' does not match "
                f"the selected format '{image_format}'."
            )

    if destination == source:
        raise MediaProcessingError(
            "Output path must be different from the input path."
        )

    if destination.exists():
        raise MediaProcessingError(
            f"Output file already exists: {destination}. "
            "Choose another output path."
        )

    destination.parent.mkdir(parents=True, exist_ok=True)

    return destination, image_format


def _save_image(
    image: Image.Image,
    destination: Path,
    image_format: str,
    quality: int = 85,
    preserve_metadata: bool = False,
) -> None:
    """Save an image using format-appropriate settings."""
    save_image = image.copy()
    options: dict[str, object] = {}

    if image_format in {"JPEG", "WEBP"}:
        if save_image.mode not in {"RGB", "L"}:
            if save_image.mode in {"RGBA", "LA"}:
                rgba = save_image.convert("RGBA")
                background = Image.new("RGB", rgba.size, "white")
                background.paste(rgba, mask=rgba.getchannel("A"))
                save_image = background
            else:
                save_image = save_image.convert("RGB")

        options["quality"] = quality

    if image_format == "PNG":
        options["optimize"] = True

    if image_format == "WEBP":
        options["method"] = 6

    if preserve_metadata:
        exif = image.getexif()
        if exif:
            options["exif"] = exif.tobytes()

    try:
        save_image.save(destination, format=image_format, **options)
    except (OSError, ValueError) as exc:
        destination.unlink(missing_ok=True)
        raise MediaProcessingError(
            f"Unable to save image '{destination}': {exc}"
        ) from exc
    finally:
        save_image.close()


def _result(
    source: Path,
    destination: Path,
    operation: str,
) -> ImageOperationResult:
    """Build a processing result."""
    return ImageOperationResult(
        input_path=str(source),
        output_path=str(destination),
        operation=operation,
        input_size=source.stat().st_size,
        output_size=destination.stat().st_size,
    )


def inspect_image(path: str | Path) -> ImageInfo:
    """Inspect image dimensions, format, mode, size, and frame count."""
    source = _validate_input(Path(path))

    try:
        with Image.open(source) as image:
            image_format = image.format or "UNKNOWN"
            has_transparency = (
                "A" in image.getbands()
                or "transparency" in image.info
            )

            return ImageInfo(
                path=str(source),
                filename=source.name,
                format=image_format,
                mode=image.mode,
                width=image.width,
                height=image.height,
                file_size=source.stat().st_size,
                has_transparency=has_transparency,
                frame_count=getattr(image, "n_frames", 1),
            )
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
    ) as exc:
        raise MediaProcessingError(
            f"Unable to inspect image '{source}': {exc}"
        ) from exc


def convert_image(
    path: str | Path,
    output_format: str,
    output: str | Path | None = None,
    quality: int = 85,
    preserve_metadata: bool = False,
) -> ImageOperationResult:
    """Convert an image to another supported format."""
    source = _validate_input(Path(path))
    destination, image_format = _prepare_output(
        source, Path(output) if output else None,
        "converted", output_format,
    )

    if not 1 <= quality <= 100:
        raise MediaProcessingError("Quality must be between 1 and 100.")

    image = _open_image(source)
    try:
        _save_image(
            image, destination, image_format, quality, preserve_metadata
        )
    finally:
        image.close()

    return _result(source, destination, "convert")


def compress_image(
    path: str | Path,
    output: str | Path | None = None,
    quality: int = 80,
    preserve_metadata: bool = False,
) -> ImageOperationResult:
    """Compress an image using format-appropriate optimization."""
    source = _validate_input(Path(path))

    if not 1 <= quality <= 100:
        raise MediaProcessingError("Quality must be between 1 and 100.")

    image = _open_image(source)
    image_format = image.format or _resolve_format(source.suffix.lstrip("."))

    if image_format not in {"JPEG", "PNG", "WEBP"}:
        image.close()
        raise MediaProcessingError(
            "Compression currently supports JPEG, PNG, and WebP images."
        )

    destination, _ = _prepare_output(
        source,
        Path(output) if output else None,
        "compressed",
    )

    try:
        _save_image(
            image, destination, image_format, quality, preserve_metadata
        )
    finally:
        image.close()

    return _result(source, destination, "compress")


def resize_image(
    path: str | Path,
    width: int | None = None,
    height: int | None = None,
    output: str | Path | None = None,
    preserve_metadata: bool = False,
) -> ImageOperationResult:
    """Resize an image while preserving its aspect ratio."""
    source = _validate_input(Path(path))

    if width is None and height is None:
        raise MediaProcessingError("Specify at least a width or height.")

    if (width is not None and width <= 0) or (
        height is not None and height <= 0
    ):
        raise MediaProcessingError("Width and height must be positive.")

    image = _open_image(source)
    image_format = image.format or _resolve_format(source.suffix.lstrip("."))

    if image_format not in FORMAT_EXTENSIONS:
        image.close()
        raise MediaProcessingError(f"Unsupported image format: {image_format}")

    if width is None:
        width = max(1, round(image.width * height / image.height))
    elif height is None:
        height = max(1, round(image.height * width / image.width))

    destination, _ = _prepare_output(
        source, Path(output) if output else None, "resized"
    )

    try:
        resized = ImageOps.contain(
            image,
            (width, height),
            method=Image.Resampling.LANCZOS,
        )
        try:
            _save_image(
                resized, destination, image_format,
                preserve_metadata=preserve_metadata,
            )
        finally:
            resized.close()
    finally:
        image.close()

    return _result(source, destination, "resize")


def crop_image(
    path: str | Path,
    x: int,
    y: int,
    width: int,
    height: int,
    output: str | Path | None = None,
    preserve_metadata: bool = False,
) -> ImageOperationResult:
    """Crop an image using a top-left coordinate and dimensions."""
    source = _validate_input(Path(path))

    if x < 0 or y < 0 or width <= 0 or height <= 0:
        raise MediaProcessingError(
            "Crop coordinates must be non-negative and dimensions positive."
        )

    image = _open_image(source)
    image_format = image.format or _resolve_format(source.suffix.lstrip("."))

    if x + width > image.width or y + height > image.height:
        image.close()
        raise MediaProcessingError(
            "Crop area extends beyond the image boundaries."
        )

    destination, _ = _prepare_output(
        source, Path(output) if output else None, "cropped"
    )

    try:
        cropped = image.crop((x, y, x + width, y + height))
        try:
            _save_image(
                cropped, destination, image_format,
                preserve_metadata=preserve_metadata,
            )
        finally:
            cropped.close()
    finally:
        image.close()

    return _result(source, destination, "crop")


def create_thumbnail(
    path: str | Path,
    size: int = 256,
    output: str | Path | None = None,
) -> ImageOperationResult:
    """Create a square-bounded thumbnail without changing the source."""
    source = _validate_input(Path(path))

    if size <= 0:
        raise MediaProcessingError("Thumbnail size must be positive.")

    image = _open_image(source)
    image_format = image.format or _resolve_format(source.suffix.lstrip("."))

    destination, _ = _prepare_output(
        source, Path(output) if output else None, "thumbnail"
    )

    try:
        thumbnail = ImageOps.contain(
            image,
            (size, size),
            method=Image.Resampling.LANCZOS,
        )
        try:
            _save_image(thumbnail, destination, image_format)
        finally:
            thumbnail.close()
    finally:
        image.close()

    return _result(source, destination, "thumbnail")


def strip_image_metadata(
    path: str | Path,
    output: str | Path | None = None,
) -> ImageOperationResult:
    """Write a copy of an image without carrying over EXIF metadata."""
    source = _validate_input(Path(path))
    image = _open_image(source)
    image_format = image.format or _resolve_format(source.suffix.lstrip("."))

    destination, _ = _prepare_output(
        source, Path(output) if output else None, "clean"
    )

    try:
        _save_image(
            image,
            destination,
            image_format,
            preserve_metadata=False,
        )
    finally:
        image.close()

    return _result(source, destination, "strip-metadata")
