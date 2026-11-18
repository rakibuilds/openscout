 <div align="center">

<img src="assets/brand/logo.svg" alt="OpenScout logo" width="112" />

# OpenScout

**Explore the web. Understand domains. Discover information.**

An open-source toolkit for web research and domain intelligence.

[Documentation](docs/README.md) · [Contributing](CONTRIBUTING.md) · [License](LICENSE)

</div>

---

## What is OpenScout?

OpenScout is an open-source project that brings useful web research and domain intelligence tools together in one place.

It helps people explore websites, understand domain information, inspect website security, and collect readable content from web pages without having to switch between multiple tools for every task.

The goal is simple: make web research more accessible, useful, and easier to build upon.

## Who is OpenScout for?

OpenScout is for anyone who wants to explore and understand the web:

- **Developers** who need practical tools for working with websites and domains.
- **Researchers** who collect and examine publicly available web information.
- **Security learners** who want to understand DNS, TLS, and website security.
- **Analysts** who need to inspect domains and website details.
- **Curious explorers** who want to learn more about how websites work.

## What can you do with OpenScout?

### Explore domains

Look up DNS records and discover domain registration information, including registrar details, nameservers, and important dates.

### Inspect websites

Bring important website information together in one inspection. Check DNS, domain registration, HTTP responses, TLS certificates, and security headers.

### Understand website security

Examine security-related HTTP headers and TLS certificate information to better understand how a website is configured.

### Fetch web pages

Retrieve website responses and inspect their status, headers, and content.

### Extract readable content

Turn web pages into readable content that is easier to research, review, and reuse.

### Work with structured results

Get inspection results in JSON format so they can be used by scripts, other tools, and automated workflows.

## Get started

Here are a few examples of what OpenScout can do:

```bash
# Inspect a domain and its website
openscout web inspect example.com

# Get machine-readable inspection results
openscout web inspect example.com --json

# Save an inspection report
openscout web inspect example.com --output report.json

# Look up DNS records
openscout web dns example.com

# Look up domain registration information
openscout web domain example.com

# Inspect website security headers
openscout web headers https://example.com

# Fetch a web page
openscout web fetch https://example.com

# Extract readable page content
openscout web scrape https://example.com
```

For installation and usage instructions, visit the [Documentation](docs/README.md).

## Open source, built together

OpenScout is developed in the open. Contributions, feedback, ideas, and improvements are welcome.

Whether you want to report a problem, improve the documentation, suggest a feature, or contribute code, you're welcome to participate.

- [Read the Contributing Guide](CONTRIBUTING.md)
- [Explore the Documentation](docs/README.md)
- [View the License](LICENSE)

## Project

**OpenScout** · Open source · Community driven

Built by [Rakibul Islam](https://github.com/rakibuilds) and contributors.

[GitHub Repository](https://github.com/rakibuilds/openscout)