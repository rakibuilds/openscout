"""OpenScout: local-first web intelligence and processing toolkit."""

__version__ = "0.1.0"


def main() -> None:
    """Run the OpenScout command-line application."""
    from openscout.cli.app import app

    app()