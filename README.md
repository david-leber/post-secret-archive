# post-secret-archive
PostSecret Archive Project

# Usage
Currently not enforcing restrictions on committing to main, but all changes should be pushed to a branch which should then be merged in using a PR (at least one reviewer.)

Before merging code, ensure you:
1. `uvx ruff format`
2. `uvx ruff check`
3. `uvx pyright`
4. `uvx pytest`