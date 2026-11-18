
"""Tests for the OpenScout search CLI."""

from typer.testing import CliRunner

from openscout.cli.app import app

runner = CliRunner()


def test_search_help() -> None:
    result = runner.invoke(app, ["search", "--help"])

    assert result.exit_code == 0
    assert "build" in result.output
    assert "operators" in result.output
    assert "templates" in result.output
    assert "explain" in result.output


def test_list_search_operators() -> None:
    result = runner.invoke(app, ["search", "operators"])

    assert result.exit_code == 0
    assert "site" in result.output
    assert "filetype" in result.output
    assert "intitle" in result.output


def test_filter_search_operators() -> None:
    result = runner.invoke(
        app,
        ["search", "operators", "--category", "date"],
    )

    assert result.exit_code == 0
    assert "before" in result.output
    assert "after" in result.output
    assert "site" not in result.output


def test_list_search_templates() -> None:
    result = runner.invoke(app, ["search", "templates"])

    assert result.exit_code == 0
    assert "research-papers" in result.output
    assert "github-projects" in result.output
    assert "public-datasets" in result.output


def test_build_basic_query() -> None:
    result = runner.invoke(
        app,
        ["search", "build", "AI agents"],
    )

    assert result.exit_code == 0
    assert '"AI agents"' in result.output


def test_build_query_with_site() -> None:
    result = runner.invoke(
        app,
        ["search", "build", "AI agents", "--site", "github.com"],
    )

    assert result.exit_code == 0
    assert '"AI agents" site:github.com' in result.output


def test_build_query_with_filetype_and_date() -> None:
    result = runner.invoke(
        app,
        [
            "search",
            "build",
            "Assamese NLP",
            "--filetype",
            "pdf",
            "--after",
            "2023-01-01",
        ],
    )

    assert result.exit_code == 0
    assert '"Assamese NLP"' in result.output
    assert "filetype:pdf" in result.output
    assert "after:2023-01-01" in result.output


def test_build_query_with_title_and_exclusion() -> None:
    result = runner.invoke(
        app,
        [
            "search",
            "build",
            "web automation",
            "--intitle",
            "documentation",
            "--exclude",
            "jobs",
        ],
    )

    assert result.exit_code == 0
    assert "intitle:documentation" in result.output
    assert "-jobs" in result.output


def test_build_query_with_template() -> None:
    result = runner.invoke(
        app,
        [
            "search",
            "build",
            "AI agents",
            "--template",
            "github-projects",
        ],
    )

    assert result.exit_code == 0
    assert "site:github.com" in result.output


def test_template_options_can_be_overridden() -> None:
    result = runner.invoke(
        app,
        [
            "search",
            "build",
            "AI agents",
            "--template",
            "github-projects",
            "--filetype",
            "md",
        ],
    )

    assert result.exit_code == 0
    assert "site:github.com" in result.output
    assert "filetype:md" in result.output


def test_build_query_with_repeated_options() -> None:
    result = runner.invoke(
        app,
        [
            "search",
            "build",
            "machine learning",
            "--exact",
            "large language models",
            "--exclude",
            "jobs",
            "--exclude",
            "salary",
            "--any-of",
            "robotics",
            "--any-of",
            "computer vision",
        ],
    )

    assert result.exit_code == 0
    assert '"large language models"' in result.output
    assert "-jobs" in result.output
    assert "-salary" in result.output
    assert "robotics OR" in result.output
    assert '"computer vision"' in result.output


def test_unknown_template_returns_error() -> None:
    result = runner.invoke(
        app,
        [
            "search",
            "build",
            "AI agents",
            "--template",
            "unknown-template",
        ],
    )

    assert result.exit_code == 2
    assert "Error:" in result.output


def test_single_any_of_returns_error() -> None:
    result = runner.invoke(
        app,
        [
            "search",
            "build",
            "machine learning",
            "--any-of",
            "robotics",
        ],
    )

    assert result.exit_code == 2
    assert "at least two alternatives" in result.output


def test_explain_search_query() -> None:
    result = runner.invoke(
        app,
        [
            "search",
            "explain",
            "site:github.com filetype:pdf AI",
        ],
    )

    assert result.exit_code == 0
    assert "Search query explanation" in result.output
    assert "site:github.com" in result.output
    assert "filetype:pdf" in result.output
