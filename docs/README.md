# OpenScout Documentation

Welcome to the OpenScout documentation.

OpenScout is an open-source toolkit for web research and domain intelligence. These documents help you understand the project, get started, and use its available features.

## Getting started

If you're new to OpenScout, begin with the [main README](../README.md) to understand what the project does, who it is for, and what you can do with it.

## Available features

| Feature | What it helps you do |
|---|---|
| DNS lookup | Discover a domain's DNS records |
| Domain lookup | Explore registration information |
| Website headers | Examine HTTP security headers |
| Web fetch | Retrieve website responses |
| Web scraping | Extract readable page content |
| Domain inspection | Bring domain, DNS, HTTP, TLS, and security-header information together |

## Domain inspection

The unified inspection command is a convenient way to examine a domain:

```bash
openscout web inspect example.com
```

For structured output:

```bash
openscout web inspect example.com --json
```

To save a report:

```bash
openscout web inspect example.com --output report.json
```

Individual tools are also available when you only need one type of information.

## Get involved

OpenScout is an open-source project, and contributions are welcome.

- [Contributing Guide](../CONTRIBUTING.md)
- [Project License](../LICENSE)
- [OpenScout on GitHub](https://github.com/rakibuilds/openscout)

## Documentation improvements

Documentation is an ongoing part of the project. If you notice missing information, unclear instructions, or something that could be explained better, contributions are welcome.