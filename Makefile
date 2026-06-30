format:
	uv run black src/ gui/ 
	uv run ruff check --fix src/ gui/ 

lint:
	 uv run ruff check src/ gui/

check:
	uv run ruff check src/ gui/
	uv run black --check src/ gui/

test:
	uv run pytest tests/ -v

all: 
	format lint test