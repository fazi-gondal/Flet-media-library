# Publishing `flet-media-library` to PyPI

## Prerequisites

1. [PyPI](https://pypi.org) account (and optional TestPyPI).
2. API token: https://pypi.org/manage/account/token/
3. Tools: `uv` or `pip install build twine`

## One-time: verify metadata

```bash
cd /path/to/Flet-media-library
uv sync --group dev
# or: pip install -e ".[dev]"  # if you map dev extras later
python -c "import flet_media_library; print(flet_media_library.__version__)"
```

Confirm:

- `name = "flet-media-library"` (import: `flet_media_library`)
- `version` matches `__version__` in `src/flet_media_library/__init__.py`
- README renders on PyPI (no broken relative-only links for critical install steps)
- LICENSE is MIT

## Build

```bash
rm -rf dist build *.egg-info src/*.egg-info
uv run python -m build
# produces dist/flet_media_library-0.1.0.tar.gz and .whl
```

Check the wheel contains Flutter sources:

```bash
unzip -l dist/flet_media_library-0.1.0-py3-none-any.whl | grep flutter | head
```

You should see paths under `flutter/flet_media_library/`.

## Upload to TestPyPI (recommended first)

```bash
uv run twine upload --repository testpypi dist/*
# install test:
# pip install -i https://test.pypi.org/simple/ flet-media-library==0.1.0
```

## Upload to PyPI

```bash
uv run twine upload dist/*
```

Use a token as the password (`pypi-...`). Username can be `__token__`.

## After publish

```toml
# consumer app
dependencies = [
  "flet>=0.86.5",
  "flet-media-library>=0.1.0",
]
```

```bash
flet build apk   # Flutter plugin is pulled from the installed package
```

Tag the release:

```bash
git tag v0.1.0
git push origin v0.1.0
```

## Version bumps

1. Update `version` in `pyproject.toml`
2. Update `__version__` in `src/flet_media_library/__init__.py`
3. Update `version` in `src/flutter/flet_media_library/pubspec.yaml`
4. Add a section under CHANGELOG.md
5. Build + twine upload again
