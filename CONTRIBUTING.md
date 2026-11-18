# Contributing to OpenScout

Thank you for your interest in contributing to OpenScout!

OpenScout is an open-source project for web research and domain intelligence. We welcome contributions from developers, researchers, security learners, documentation writers, and anyone who wants to help make the project better.

You don't need to be an expert to contribute. Every thoughtful improvement matters.

## Ways to contribute

There are several ways to get involved:

- **Report bugs:** Help identify problems and unexpected behavior.
- **Suggest features:** Share ideas that could make OpenScout more useful.
- **Improve documentation:** Fix unclear explanations, add examples, and improve guides.
- **Contribute code:** Fix bugs, improve existing functionality, or build useful features.
- **Review changes:** Help review pull requests and provide constructive feedback.
- **Spread the word:** Share OpenScout with people who might find it useful.

## Before you start

Before working on a change:

1. Check the existing issues to see whether the problem or idea has already been discussed.
2. For significant changes, open an issue first so the direction can be discussed.
3. Keep contributions focused and avoid combining unrelated changes.
4. Make sure your changes fit the project's purpose and existing behavior.

## Reporting bugs

When reporting a bug, include as much useful information as possible:

- A clear description of the problem.
- Steps to reproduce it.
- The command or workflow you used.
- What you expected to happen.
- What actually happened.
- Relevant error messages or terminal output.
- Your operating system and Python version, when relevant.

Please avoid including passwords, API keys, private data, or other sensitive information in issue reports.

## Suggesting features

Feature suggestions are welcome.

When proposing an idea, explain:

- The problem you are trying to solve.
- Why the feature would be useful.
- How you imagine it working.
- Any relevant examples or use cases.

Ideas that improve usability, reliability, accessibility, and the overall research experience are especially valuable.

## Contributing code

### 1. Fork the repository

Create your own fork of the repository:

https://github.com/rakibuilds/openscout

### 2. Clone your fork

```bash
git clone https://github.com/YOUR_USERNAME/openscout.git
cd openscout
```

Replace `YOUR_USERNAME` with your GitHub username.

### 3. Set up the project

Install the project dependencies using the existing project configuration:

```bash
uv sync --dev
```

### 4. Create a branch

Use a descriptive branch name:

```bash
git switch -c fix/short-description
```

Examples:

- `fix/dns-lookup-error`
- `feat/domain-inspection`
- `docs/improve-getting-started`

### 5. Make your changes

Keep your changes focused, readable, and consistent with the existing project.

When appropriate:

- Add tests for new behavior.
- Update documentation when functionality changes.
- Preserve existing command behavior unless a change is intentional.
- Handle errors clearly.
- Avoid introducing unnecessary dependencies.

### 6. Run the checks

Before submitting your changes, run:

```bash
uv run pytest -q
uv run ruff check .
git diff --check
```

Make sure the relevant tests pass and there are no linting or whitespace errors.

### 7. Commit your changes

Use a clear commit message that describes what changed.

Examples:

```bash
git commit -m "fix(web): handle DNS lookup errors"
git commit -m "feat(web): improve domain inspection"
git commit -m "docs: improve getting started guide"
```

### 8. Submit a pull request

Push your branch:

```bash
git push origin fix/short-description
```

Then open a pull request against the `main` branch of the original repository:

https://github.com/rakibuilds/openscout/compare

In your pull request, explain:

- What you changed.
- Why the change is needed.
- How you tested it.
- Any relevant issue numbers.

Keep pull requests focused and provide screenshots or terminal output when they help explain the change.

## Documentation contributions

Documentation improvements are just as valuable as code contributions.

You can help by:

- Improving installation and usage instructions.
- Adding examples for existing commands.
- Fixing spelling and formatting.
- Explaining confusing features.
- Improving the project's README and guides.

Please make sure documentation accurately reflects the current behavior of OpenScout.

## Contribution guidelines

We ask every contributor to:

- Be respectful and constructive.
- Welcome different levels of experience.
- Keep discussions focused on improving the project.
- Provide useful feedback rather than personal criticism.
- Respect the work and contributions of others.
- Avoid submitting misleading claims, fabricated results, or untested functionality.

## License

By contributing to OpenScout, you agree that your contributions will be distributed under the project's existing license.

Please review the [LICENSE](LICENSE) file before contributing.

## Thank you

Every contribution helps OpenScout grow.

Whether you submit a small documentation fix, report a bug, suggest an idea, or contribute a major feature, thank you for being part of the project.

**Explore the web. Understand domains. Discover information.**

[OpenScout on GitHub](https://github.com/rakibuilds/openscout)