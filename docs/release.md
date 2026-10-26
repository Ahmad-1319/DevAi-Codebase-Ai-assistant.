# Release checklist

This document describes what must be completed before publishing a DevAI
release. A local package build does not publish the project or make it a
production service.

## Before the first public release

- [ ] Choose and add a software license that matches the intended use.
- [ ] Create or confirm the dedicated GitHub repository and ensure the complete
  project (including `app/`, tests, docs, `pyproject.toml`, and `uv.lock`) is
  tracked there.
- [ ] Confirm `.env`, API keys, and local environment files are not tracked.
- [ ] Review the README, security policy, model-provider data disclosure, and
  installation steps against the published repository.
- [ ] Run `uv lock --check`, `uv run pytest`, `uv run ruff check .`, and
  `uv build` on a clean checkout.
- [ ] Verify the GitHub Actions workflow succeeds on its operating-system and
  Python-version matrix.
- [ ] Install the built package in an isolated environment and verify the
  `devai` entry point starts from a directory outside the checkout.
- [ ] Test a real Gemini request and an approved and rejected edit using a
  disposable project and a locally configured key.
- [ ] Review dependency updates and advisories; update and retest dependencies
  before release.
- [ ] Choose whether the distribution will be GitHub-only or published to
  PyPI. For PyPI, configure trusted publishing and a release workflow; do not
  commit a publishing token.

## Each release

1. Update the version in `pyproject.toml` and regenerate `uv.lock`.
2. Run the clean-checkout validation above.
3. Review the final changes and confirm no secrets or local files are included.
4. Create a version tag such as `v0.1.1` only after the repository owner has
   approved the release.
5. Publish through the selected channel and verify the documented install
   command from a clean machine or environment.

## Current status

The project has package metadata, a `devai` console entry point, a lockfile,
tests, and a cross-platform CI workflow. The first public release is not
complete until the repository is published, the license is chosen, CI and
real-provider checks succeed, and the installed CLI is validated from outside
the source checkout. Command execution is intentionally not part of the
product.
