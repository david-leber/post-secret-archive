.PHONY: clean

clean:
	cd image-text-mvp && uv run ruff format .
	cd image-text-mvp && uv run ruff check .
	cd image-text-mvp && uv run pyright .