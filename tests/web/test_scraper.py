from openscout.web.scraper import extract_content


def test_extracts_page_title_and_content() -> None:
    html = """
    <!doctype html>
    <html>
      <head><title>OpenScout Test</title></head>
      <body>
        <main>
          <h1>Welcome to OpenScout</h1>
          <p>A local-first web intelligence toolkit.</p>
        </main>
      </body>
    </html>
    """

    result = extract_content(
        html=html,
        url="https://example.com",
        output_format="text",
    )

    assert result.title == "OpenScout Test"
    assert "Welcome to OpenScout" in result.content
    assert "local-first web intelligence toolkit" in result.content
    assert result.output_format == "text"


def test_rejects_unsupported_format() -> None:
    try:
        extract_content("<html></html>", "https://example.com", "pdf")
    except ValueError as exc:
        assert "output_format" in str(exc)
    else:
        raise AssertionError("Expected ValueError")