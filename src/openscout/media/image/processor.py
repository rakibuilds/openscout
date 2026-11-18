
"""Local image inspection and processing operations."""

import os
import tempfile
import warnings
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

COMPRESSIBLE_FORMATS = {"JPEG", "PNG", "WEBP"}


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
    """Validate and resolve an input image path."""
    path = path.expanduser()

    if not path.exists():
        raise MediaProcessingError(f"Input file does not exist: {path}")

    if not path.is_file():
        raise MediaProcessingError(f"Input path is not a file: {path}")

    return path.resolve()


def _validate_quality(quality: int) -> None:
    """Validate a lossy image quality value."""
    if not 1 <= quality <= 100:
        raise MediaProcessingError("Quality must be between 1 and 100.")


def _resolve_format(value: str) -> str:
    """Resolve a user-facing format name to a Pillow format."""
    normalized = value.strip().lower()

    if normalized not in SUPPORTED_FORMATS:
        supported = ", ".join(sorted(SUPPORTED_FORMATS))
        raise MediaProcessingError(
            f"Unsupported image format '{value}'. "
            f"Supported formats: {supported}"
        )

    return SUPPORTED_FORMATS[normalized]


def _get_image_format(image: Image.Image, source: Path) -> str:
    """Get the detected image format, falling back to its extension."""
    if image.format:
        image_format = image.format
        if image_format in FORMAT_EXTENSIONS:
            return image_format

        raise MediaProcessingError(
            f"Unsupported image format: {image_format}"
        )

    return _resolve_format(source.suffix.lstrip("."))


def _open_image(path: Path) -> Image.Image:
    """Open, validate, orient, and fully load a static image."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)

            with Image.open(path) as source:
                frame_count = getattr(source, "n_frames", 1)

                if frame_count > 1:
                    raise MediaProcessingError(
                        "Animated images are not supported by this operation. "
                        "Use a static image instead."
                    )

                source.load()

                oriented = ImageOps.exif_transpose(source)

                try:
                    oriented.load()
                    result = oriented.copy()
                    result.format = source.format
                    return result
                finally:
                    if oriented is not source:
                        oriented.close()

    except MediaProcessingError:
        raise
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise MediaProcessingError(
            f"Unable to read image '{path}': {exc}"
        ) from exc


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
        destination = source.with_name(
            f"{source.stem}-{suffix}{extension}"
        )
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

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise MediaProcessingError(
            f"Unable to create output directory "
            f"'{destination.parent}': {exc}"
        ) from exc

    return destination, image_format



def _save_image(
    image: Image.Image,
    destination: Path,
    image_format: str,
    quality: int = 85,
    preserve_metadata: bool = False,
) -> None:
    """Save an image atomically without overwriting an existing file."""
    save_image = image.copy()
    temporary_path: Path | None = None

    if not preserve_metadata:
        save_image.info.pop("icc_profile", None)
        save_image.info.pop("exif", None)

    try:
        options: dict[str, object] = {}

        if image_format in {"JPEG", "WEBP"}:
            if save_image.mode not in {"RGB", "L"}:
                if save_image.mode in {"RGBA", "LA"}:
                    rgba = save_image.convert("RGBA")

                    try:
                        background = Image.new(
                            "RGB",
                            rgba.size,
                            "white",
                        )

                        try:
                            alpha = rgba.getchannel("A")
                            try:
                                background.paste(rgba, mask=alpha)
                            finally:
                                alpha.close()
                        except Exception:
                            background.close()
                            raise
                    finally:
                        rgba.close()

                    save_image.close()
                    save_image = background
                else:
                    converted = save_image.convert("RGB")
                    save_image.close()
                    save_image = converted

            options["quality"] = quality

        if image_format == "PNG":
            options["optimize"] = True

        if image_format == "WEBP":
            options["method"] = 6

        if preserve_metadata:
            exif = image.getexif()
            if exif:
                options["exif"] = exif.tobytes()

            icc_profile = image.info.get("icc_profile")
            if icc_profile:
                options["icc_profile"] = icc_profile

        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.stem}-",
            suffix=destination.suffix,
            dir=destination.parent,
        )
        os.close(file_descriptor)
        temporary_path = Path(temporary_name)

        save_image.save(
            temporary_path,
            format=image_format,
            **options,
        )

        # Atomically create the destination without overwriting it.
        try:
            os.link(temporary_path, destination)
        except FileExistsError as exc:
            raise MediaProcessingError(
                f"Output file already exists: {destination}. "
                "Choose another output path."
            ) from exc

    except MediaProcessingError:
        raise
    except (OSError, ValueError) as exc:
        raise MediaProcessingError(
            f"Unable to save image '{destination}': {exc}"
        ) from exc
    finally:
        save_image.close()

        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError as exc:
                warnings.warn(
                    f"Unable to remove temporary image file "
                    f"'{temporary_path}': {exc}",
                    RuntimeWarning,
                    stacklevel=2,
                )



def _result(
    source: Path,
    destination: Path,
    operation: str,
) -> ImageOperationResult:
    """Build a processing result from the completed output."""
    try:
        return ImageOperationResult(
            input_path=str(source),
            output_path=str(destination),
            operation=operation,
            input_size=source.stat().st_size,
            output_size=destination.stat().st_size,
        )
    except OSError as exc:
        raise MediaProcessingError(
            f"Unable to read processing result file information: {exc}"
        ) from exc


def inspect_image(path: str | Path) -> ImageInfo:
    """Inspect image dimensions, format, mode, size, and frame count."""
    source = _validate_input(Path(path))

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)

            with Image.open(source) as image:
                image_format = image.format or "UNKNOWN"
                has_transparency = (
                    "A" in image.getbands()
                    or image.info.get("transparency") is not None
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
        Image.DecompressionBombWarning,
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
    image_format = _resolve_format(output_format)
    _validate_quality(quality)

    destination, _ = _prepare_output(
        source,
        Path(output) if output is not None else None,
        "converted",
        image_format,
    )

    image = _open_image(source)
    try:
        _save_image(
            image,
            destination,
            image_format,
            quality,
            preserve_metadata,
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
    """Compress a JPEG, PNG, or WebP image."""
    source = _validate_input(Path(path))
    _validate_quality(quality)

    image = _open_image(source)
    try:
        image_format = _get_image_format(image, source)

        if image_format not in COMPRESSIBLE_FORMATS:
            raise MediaProcessingError(
                "Compression currently supports JPEG, PNG, and WebP images."
            )

        destination, _ = _prepare_output(
            source,
            Path(output) if output is not None else None,
            "compressed",
            image_format,
        )

        _save_image(
            image,
            destination,
            image_format,
            quality,
            preserve_metadata,
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
    try:
        image_format = _get_image_format(image, source)

        if width is None:
            width = max(1, round(image.width * height / image.height))
        elif height is None:
            height = max(1, round(image.height * width / image.width))

        destination, _ = _prepare_output(
            source,
            Path(output) if output is not None else None,
            "resized",
            image_format,
        )

        resized = ImageOps.contain(
            image,
            (width, height),
            method=Image.Resampling.LANCZOS,
        )
        try:
            _save_image(
                resized,
                destination,
                image_format,
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
    try:
        image_format = _get_image_format(image, source)

        if x + width > image.width or y + height > image.height:
            raise MediaProcessingError(
                "Crop area extends beyond the image boundaries."
            )

        destination, _ = _prepare_output(
            source,
            Path(output) if output is not None else None,
            "cropped",
            image_format,
        )

        cropped = image.crop((x, y, x + width, y + height))
        try:
            _save_image(
                cropped,
                destination,
                image_format,
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
    try:
        image_format = _get_image_format(image, source)

        destination, _ = _prepare_output(
            source,
            Path(output) if output is not None else None,
            "thumbnail",
            image_format,
        )

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
    """Write a copy of an image without carrying over EXIF or ICC metadata."""
    source = _validate_input(Path(path))

    image = _open_image(source)
    try:
        image_format = _get_image_format(image, source)

        destination, _ = _prepare_output(
            source,
            Path(output) if output is not None else None,
            "clean",
            image_format,
        )

        _save_image(
            image,
            destination,
            image_format,
            preserve_metadata=False,
        )
    finally:
        image.close()

    return _result(source, destination, "strip-metadata")
