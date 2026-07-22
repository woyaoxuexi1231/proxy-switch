.PHONY: dev build clean install uninstall test

# ── Development ─────────────────────────────────────────────────────────

dev:
	@echo "=== Proxy-Switch Development ==="
	@echo ""
	@echo "Available commands:"
	@echo "  make install     - Install dependencies"
	@echo "  make build       - Build executable with PyInstaller"
	@echo "  make run         - Run the app in development mode"
	@echo "  make clean       - Clean build artifacts"
	@echo "  make test        - Run unit tests"
	@echo "  make lint        - Run basic syntax check"

install:
	pip install -r requirements.txt

run:
	python app.py

# ── Build ───────────────────────────────────────────────────────────────

build:
	pyinstaller build.spec
	@echo ""
	@echo "Build complete! Executable: dist/proxy-switch.exe"

# ── Clean ───────────────────────────────────────────────────────────────

clean:
	rm -rf build/ dist/ *.spec
	rm -rf __pycache__ */__pycache__ */*/__pycache__
	rm -rf .eggs *.egg-info
	@echo "Cleaned."

# ── Testing ─────────────────────────────────────────────────────────────

test:
	python -m pytest tests/ -v --tb=short || python -m unittest discover -s tests/ -v

lint:
	python -m py_compile app.py
	python -m py_compile proxy_switch/*.py
	python -m py_compile proxy_switch/**/*.py
	@echo "Syntax check passed."

# ── Installation ────────────────────────────────────────────────────────

install-cli:
	pip install -e .
	@echo "CLI installed. Run: proxy-switch --help"

uninstall:
	pip uninstall proxy-switch -y
	rm -f ~/.local/bin/proxy-switch
	@echo "Uninstalled."
