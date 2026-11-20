# Contributing to N.O.V.A.L.I.S

Thank you for your interest in contributing to **N.O.V.A.L.I.S**. We engineer cross-platform applications, market intelligence platforms, and mission-critical AI systems with a focus on correctness, clarity, and real-world resilience.

## Ways to Contribute

- **Bug Reports:** Submit reproducible issues using the repository's Bug Report template.
- **Feature & Architecture Proposals:** Open a Feature Request to discuss design tradeoffs before writing large changes.
- **Code Contributions:** Submit focused, well-tested pull requests.
- **Documentation & Benchmarks:** Improve guides, API specs, evaluation suites, and examples.

## Development Workflow

1. **Fork & Branch:** Fork the target repository and create a descriptive branch from `main`:
   - `feat/<short-description>`
   - `fix/<short-description>`
   - `docs/<short-description>`
   - `refactor/<short-description>`
2. **Keep Changes Focused:** One logical change per pull request makes reviews fast and thorough.
3. **Verify Locally:** Run linting, type checks, and test suites before opening a PR.
4. **Conventional Commits:** Prefer clear commit messages (e.g., `feat(ai): add deterministic fallback router`, `fix(ui): resolve dark mode contrast`).

## Engineering Standards

- **Reliability First:** Handle failure modes explicitly (timeouts, retries, schema validation, graceful degradation).
- **Clean Architecture:** Favor modular, readable code over clever abstractions.
- **Zero Secrets in Code:** Never commit API keys, tokens, credentials, or private datasets.
- **Tests for Behavior Changes:** New features and bug fixes should include corresponding tests where applicable.

## Code of Conduct

All contributors and maintainers are expected to uphold our [Code of Conduct](CODE_OF_CONDUCT.md).
