# Contributing

1. Create a focused branch.
2. Keep raw data and model binaries out of Git.
3. Add or update tests for statistical or modeling changes.
4. Run `pytest` and `ruff check src tests scripts app`.
5. Explain any metric-definition change in the pull request.

Statistical changes must preserve the intent-to-treat population and may not use
post-treatment features as adjustment covariates.
