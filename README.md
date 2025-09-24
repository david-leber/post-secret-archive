# post-secret-archive
PostSecret Archive Project

# Usage
Currently not enforcing restrictions on committing to main, but all changes should be pushed to a branch which should then be merged in using a PR (at least one reviewer.)

Before merging code, ensure you:
1. `uv run ruff format`
2. `uv run ruff check`
3. `uv run pyright`
4. `uv run pytest`